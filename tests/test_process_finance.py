import unittest
from unittest.mock import patch

import pandas as pd

from tests.support import install_loguru_stub

install_loguru_stub()

import preprocessing.process_finance as process_finance_module


class ProcessFinanceTests(unittest.TestCase):
    def test_process_finance_keeps_leading_yoy_missing_and_adds_effective_date(self):
        raw_df = pd.DataFrame(
            [
                {"symbol": "TCB", "date": "2023-Q4", "roe": 10.0, "roa": 1.0, "debt_to_equity": 1.0, "net_profit_margin": 20.0, "financial_leverage": 8.0},
                {"symbol": "TCB", "date": "2024-Q1", "roe": 11.0, "roa": 1.1, "debt_to_equity": 1.1, "net_profit_margin": 21.0, "financial_leverage": 8.1},
                {"symbol": "TCB", "date": "2024-Q2", "roe": 12.0, "roa": 1.2, "debt_to_equity": 1.2, "net_profit_margin": 22.0, "financial_leverage": 8.2},
                {"symbol": "TCB", "date": "2024-Q3", "roe": 13.0, "roa": 1.3, "debt_to_equity": 1.3, "net_profit_margin": 23.0, "financial_leverage": 8.3},
                {"symbol": "TCB", "date": "2024-Q4", "roe": 14.0, "roa": 1.4, "debt_to_equity": 1.4, "net_profit_margin": 24.0, "financial_leverage": 8.4},
            ]
        )

        with patch.object(process_finance_module, "load_raw_from_database", return_value=raw_df), patch.object(
            process_finance_module, "save_features_to_database"
        ):
            result = process_finance_module.process_and_engineer_finance()

        self.assertIn("effective_date", result.columns)
        self.assertTrue(pd.isna(result.loc[result["date"] == "2024-Q1", "roe_yoy"]).iloc[0])
        self.assertTrue(pd.isna(result.loc[result["date"] == "2024-Q1", "roe_lag4"]).iloc[0])


if __name__ == "__main__":
    unittest.main()
