import sys
import types
import unittest
from unittest.mock import patch

import pandas as pd

import scripts.run_pipeline as run_pipeline_module


class RunPipelineTests(unittest.TestCase):
    def test_pipeline_collects_and_processes_news_when_not_skipped(self):
        calls = []

        def recorder(name, result=None):
            def _wrapped(*args, **kwargs):
                calls.append(name)
                return result

            return _wrapped

        fake_modules = {
            "database.schema": types.SimpleNamespace(create_all_tables=recorder("create_all_tables")),
            "database.connection": types.SimpleNamespace(
                table_exists=lambda *_args, **_kwargs: False,
                table_row_count=lambda *_args, **_kwargs: 0,
            ),
            "data_collection.collect_prices": types.SimpleNamespace(collect_prices=recorder("collect_prices")),
            "preprocessing.process_prices": types.SimpleNamespace(process_prices=recorder("process_prices")),
            "data_collection.collect_finance": types.SimpleNamespace(crawl_ratio_api=recorder("crawl_ratio_api", pd.DataFrame([{"ok": 1}]))),
            "preprocessing.process_finance": types.SimpleNamespace(process_finance=recorder("process_finance")),
            "data_collection.collect_news": types.SimpleNamespace(collect_news=recorder("collect_news", 1)),
            "preprocessing.process_news": types.SimpleNamespace(process_news=recorder("process_news")),
            "preprocessing.merge_features": types.SimpleNamespace(
                merge_features=recorder("merge_features", pd.DataFrame([{"date": "2024-01-01", "close": 10.0, "target": 11.0}]))
            ),
        }

        completed_process = types.SimpleNamespace(returncode=0)

        with patch.dict(sys.modules, fake_modules, clear=False), patch.object(
            sys, "argv", ["run_pipeline.py"]
        ), patch.object(run_pipeline_module.subprocess, "run", return_value=completed_process):
            run_pipeline_module.main()

        self.assertIn("collect_news", calls)
        self.assertIn("process_news", calls)
        self.assertLess(calls.index("collect_news"), calls.index("process_news"))


if __name__ == "__main__":
    unittest.main()
