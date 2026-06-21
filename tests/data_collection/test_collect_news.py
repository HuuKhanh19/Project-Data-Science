import sys
import types
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from tests.support import install_loguru_stub, install_requests_stub


def _load_collect_news_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "data_collection" / "collect_news.py"
    module_name = "_collect_news_under_test"

    database_package = types.ModuleType("database")
    database_connection_module = types.ModuleType("database.connection")
    database_connection_module.get_connection = lambda *args, **kwargs: None
    database_connection_module.write_table = lambda *args, **kwargs: None

    config_package = types.ModuleType("config")
    settings_module = types.ModuleType("config.settings")
    settings_module.SYMBOL = "TCB"
    settings_module.DATA_START_DATE = "2022-01-01"
    settings_module.DATA_END_DATE = "2025-03-12"

    temporary_modules = {
        "database": database_package,
        "database.connection": database_connection_module,
        "config": config_package,
        "config.settings": settings_module,
    }

    previous_modules = {name: sys.modules.get(name) for name in temporary_modules}
    install_requests_stub()
    install_loguru_stub()

    try:
        sys.modules.update(temporary_modules)
        spec = spec_from_file_location(module_name, module_path)
        module = module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


collect_news_module = _load_collect_news_module()

dedupe_news_records = collect_news_module.dedupe_news_records
is_within_date_range = collect_news_module.is_within_date_range
normalize_date_text = collect_news_module.normalize_date_text


class CollectNewsHelperTests(unittest.TestCase):
    def test_normalize_date_text_keeps_iso_date(self):
        self.assertEqual(normalize_date_text("2024-11-05"), "2024-11-05")

    def test_normalize_date_text_converts_dmy_date(self):
        self.assertEqual(normalize_date_text("05/11/2024"), "2024-11-05")

    def test_normalize_date_text_rejects_blank_and_invalid_text(self):
        self.assertIsNone(normalize_date_text(""))
        self.assertIsNone(normalize_date_text("not-a-date"))

    def test_normalize_date_text_accepts_timestamp_input(self):
        self.assertEqual(normalize_date_text("2024-11-05 14:30:00"), "2024-11-05")

    def test_is_within_date_range_accepts_in_range_date(self):
        self.assertTrue(is_within_date_range("2024-11-05"))

    def test_is_within_date_range_rejects_out_of_range_date(self):
        self.assertFalse(is_within_date_range("2021-12-31"))

    def test_is_within_date_range_accepts_inclusive_start_boundary(self):
        self.assertTrue(is_within_date_range(collect_news_module.DATA_START_DATE))

    def test_is_within_date_range_accepts_inclusive_end_boundary(self):
        self.assertTrue(is_within_date_range(collect_news_module.DATA_END_DATE))

    def test_is_within_date_range_rejects_blank_and_invalid_date_text(self):
        self.assertFalse(is_within_date_range(""))
        self.assertFalse(is_within_date_range("not-a-date"))

    def test_is_within_date_range_raises_for_invalid_start_config(self):
        original_start = collect_news_module.DATA_START_DATE
        try:
            collect_news_module.DATA_START_DATE = "bad-date"
            with self.assertRaises(ValueError):
                collect_news_module.is_within_date_range("2024-11-05")
        finally:
            collect_news_module.DATA_START_DATE = original_start

    def test_is_within_date_range_raises_for_invalid_end_config(self):
        original_end = collect_news_module.DATA_END_DATE
        try:
            collect_news_module.DATA_END_DATE = "bad-date"
            with self.assertRaises(ValueError):
                collect_news_module.is_within_date_range("2024-11-05")
        finally:
            collect_news_module.DATA_END_DATE = original_end

    def test_dedupe_news_records_keeps_latest_record_for_duplicate_url(self):
        records = [
            {"url": "https://example.com/a", "title": "old"},
            {"url": "https://example.com/b", "title": "keep"},
            {"url": "https://example.com/a", "title": "new"},
        ]

        self.assertEqual(
            dedupe_news_records(records),
            [
                {"url": "https://example.com/b", "title": "keep"},
                {"url": "https://example.com/a", "title": "new"},
            ],
        )

    def test_dedupe_news_records_preserves_order_of_last_seen_records(self):
        records = [
            {"url": "https://example.com/a", "title": "first a"},
            {"url": "https://example.com/b", "title": "first b"},
            {"url": "https://example.com/a", "title": "latest a"},
            {"url": "https://example.com/c", "title": "only c"},
            {"url": "https://example.com/b", "title": "latest b"},
            {"url": "https://example.com/d", "title": "only d"},
        ]

        self.assertEqual(
            dedupe_news_records(records),
            [
                {"url": "https://example.com/a", "title": "latest a"},
                {"url": "https://example.com/c", "title": "only c"},
                {"url": "https://example.com/b", "title": "latest b"},
                {"url": "https://example.com/d", "title": "only d"},
            ],
        )


class CollectNewsParserTests(unittest.TestCase):
    def test_parse_cafef_search_page_extracts_expected_record(self):
        html = """
        <div class="tlitem">
            <a href="https://cafef.vn/sample-1.chn" title="TCB tang truong manh">TCB tang truong manh</a>
            <span class="time">05/11/2024</span>
            <p class="sapo">Techcombank ghi nhan tang truong tin dung.</p>
        </div>
        """

        self.assertEqual(
            collect_news_module.parse_cafef_search_page(html),
            [
                {
                    "date": "2024-11-05",
                    "title": "TCB tang truong manh",
                    "content": "Techcombank ghi nhan tang truong tin dung.",
                    "url": "https://cafef.vn/sample-1.chn",
                    "source": "cafef",
                }
            ],
        )

    def test_parse_cafef_search_page_cleans_nested_inline_markup(self):
        html = """
        <div class="tlitem">
            <a href="https://cafef.vn/sample-nested.chn"><strong>TCB</strong> tang truong <em>manh</em></a>
            <span class="time"><span>05/11/2024</span></span>
            <p class="sapo">Techcombank <strong>ghi nhan</strong> nhu cau <em>tin dung</em> tang.</p>
        </div>
        """

        self.assertEqual(
            collect_news_module.parse_cafef_search_page(html),
            [
                {
                    "date": "2024-11-05",
                    "title": "TCB tang truong manh",
                    "content": "Techcombank ghi nhan nhu cau tin dung tang.",
                    "url": "https://cafef.vn/sample-nested.chn",
                    "source": "cafef",
                }
            ],
        )

    def test_parse_cafef_search_page_skips_incomplete_items(self):
        html = """
        <div class="tlitem">
            <a title="Missing url">Missing url</a>
            <span class="time">05/11/2024</span>
            <p class="sapo">Should be skipped.</p>
        </div>
        <div class="tlitem">
            <a href="https://cafef.vn/missing-date.chn" title="Missing date">Missing date</a>
            <p class="sapo">Should also be skipped.</p>
        </div>
        <div class="tlitem">
            <a href="https://cafef.vn/valid-item.chn" title="Valid item">Valid item</a>
            <span class="time">05/11/2024</span>
            <p class="sapo">This one should remain.</p>
        </div>
        """

        self.assertEqual(
            collect_news_module.parse_cafef_search_page(html),
            [
                {
                    "date": "2024-11-05",
                    "title": "Valid item",
                    "content": "This one should remain.",
                    "url": "https://cafef.vn/valid-item.chn",
                    "source": "cafef",
                }
            ],
        )

    def test_parse_cafef_search_page_handles_multiple_items(self):
        html = """
        <div class="tlitem">
            <a href="https://cafef.vn/item-1.chn" title="Item 1">Item 1</a>
            <span class="time">05/11/2024</span>
            <p class="sapo">First summary.</p>
        </div>
        <div class="tlitem">
            <a href="https://cafef.vn/item-2.chn" title="Item 2">Item 2</a>
            <span class="time">06/11/2024</span>
            <p class="sapo">Second summary.</p>
        </div>
        """

        self.assertEqual(
            collect_news_module.parse_cafef_search_page(html),
            [
                {
                    "date": "2024-11-05",
                    "title": "Item 1",
                    "content": "First summary.",
                    "url": "https://cafef.vn/item-1.chn",
                    "source": "cafef",
                },
                {
                    "date": "2024-11-06",
                    "title": "Item 2",
                    "content": "Second summary.",
                    "url": "https://cafef.vn/item-2.chn",
                    "source": "cafef",
                },
            ],
        )

    def test_parse_vnexpress_search_page_extracts_expected_record(self):
        html = """
        <article class="item-news">
            <h3 class="title-news"><a href="https://vnexpress.net/sample-2.html">Techcombank mo rong tin dung</a></h3>
            <p class="description">Ngan hang ghi nhan nhu cau von cai thien.</p>
            <span class="date">05/11/2024</span>
        </article>
        """

        self.assertEqual(
            collect_news_module.parse_vnexpress_search_page(html),
            [
                {
                    "date": "2024-11-05",
                    "title": "Techcombank mo rong tin dung",
                    "content": "Ngan hang ghi nhan nhu cau von cai thien.",
                    "url": "https://vnexpress.net/sample-2.html",
                    "source": "vnexpress",
                }
            ],
        )

    def test_parse_vnexpress_search_page_cleans_nested_inline_markup(self):
        html = """
        <article class="item-news">
            <h3 class="title-news">
                <a href="https://vnexpress.net/sample-nested.html"><span>Techcombank</span> mo rong <em>tin dung</em></a>
            </h3>
            <p class="description"><strong>Nhu cau</strong> von <span>cai thien</span>.</p>
            <span class="date"><time>05/11/2024</time></span>
        </article>
        """

        self.assertEqual(
            collect_news_module.parse_vnexpress_search_page(html),
            [
                {
                    "date": "2024-11-05",
                    "title": "Techcombank mo rong tin dung",
                    "content": "Nhu cau von cai thien.",
                    "url": "https://vnexpress.net/sample-nested.html",
                    "source": "vnexpress",
                }
            ],
        )

    def test_parse_vnexpress_search_page_skips_incomplete_items(self):
        html = """
        <article class="item-news">
            <h3 class="title-news"><a>Missing url</a></h3>
            <p class="description">Should be skipped.</p>
            <span class="date">05/11/2024</span>
        </article>
        <article class="item-news">
            <h3 class="title-news"><a href="https://vnexpress.net/missing-date.html">Missing date</a></h3>
            <p class="description">Should also be skipped.</p>
        </article>
        <article class="item-news">
            <h3 class="title-news"><a href="https://vnexpress.net/valid-item.html">Valid item</a></h3>
            <p class="description">This one should remain.</p>
            <span class="date">05/11/2024</span>
        </article>
        """

        self.assertEqual(
            collect_news_module.parse_vnexpress_search_page(html),
            [
                {
                    "date": "2024-11-05",
                    "title": "Valid item",
                    "content": "This one should remain.",
                    "url": "https://vnexpress.net/valid-item.html",
                    "source": "vnexpress",
                }
            ],
        )

    def test_parse_vnexpress_search_page_handles_multiple_items(self):
        html = """
        <article class="item-news">
            <h3 class="title-news"><a href="https://vnexpress.net/item-1.html">Item 1</a></h3>
            <p class="description">First summary.</p>
            <span class="date">05/11/2024</span>
        </article>
        <article class="item-news">
            <h3 class="title-news"><a href="https://vnexpress.net/item-2.html">Item 2</a></h3>
            <p class="description">Second summary.</p>
            <span class="date">06/11/2024</span>
        </article>
        """

        self.assertEqual(
            collect_news_module.parse_vnexpress_search_page(html),
            [
                {
                    "date": "2024-11-05",
                    "title": "Item 1",
                    "content": "First summary.",
                    "url": "https://vnexpress.net/item-1.html",
                    "source": "vnexpress",
                },
                {
                    "date": "2024-11-06",
                    "title": "Item 2",
                    "content": "Second summary.",
                    "url": "https://vnexpress.net/item-2.html",
                    "source": "vnexpress",
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
