import sys
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pandas as pd


def _load_collect_finance_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "data_collection" / "collect_finance.py"
    module_name = "_collect_finance_under_test"

    spec = spec_from_file_location(module_name, module_path)
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


collect_finance = _load_collect_finance_module()


class CollectFinanceTests(unittest.TestCase):
    def test_build_mock_ratio_data_returns_wide_rows_with_timing_columns(self):
        df = collect_finance.build_mock_ratio_data()

        required_columns = {
            "symbol",
            "date",
            "period_end_date",
            "effective_date",
            "roe",
            "roa",
            "debt_to_equity",
            "pe_ratio",
            "pb_ratio",
            "eps_vnd",
            "bvps_vnd",
        }

        self.assertTrue(required_columns.issubset(df.columns))
        self.assertGreater(len(df), 0)

        period_end = pd.to_datetime(df["period_end_date"])
        effective = pd.to_datetime(df["effective_date"])
        self.assertTrue((effective >= period_end).all())

    def test_build_records_from_ratio_df_outputs_single_wide_record_per_quarter(self):
        raw_df = pd.DataFrame(
            [
                {
                    "date": "2024-Q1",
                    "meta_ticker": "TCB",
                    "meta_yearreport": 2024,
                    "meta_lengthreport": 1,
                    "roe": 16.5,
                    "roa": 1.8,
                    "debt/equity": 1.2,
                    "p/e": 8.9,
                    "p/b": 1.3,
                    "eps": 3200,
                    "bvps": 25800,
                }
            ]
        )

        records = collect_finance.build_records_from_ratio_df(raw_df)

        self.assertEqual(len(records), 1)
        self.assertNotIn("metric_name", records.columns)
        self.assertNotIn("value", records.columns)
        self.assertEqual(records.loc[0, "date"], "2024-Q1")
        self.assertEqual(records.loc[0, "symbol"], "TCB")
        self.assertAlmostEqual(records.loc[0, "roe"], 16.5)
        self.assertAlmostEqual(records.loc[0, "debt_to_equity"], 1.2)
        self.assertEqual(records.loc[0, "period_end_date"], "2024-03-31")
        self.assertEqual(records.loc[0, "effective_date"], "2024-04-30")


if __name__ == "__main__":
    unittest.main()
