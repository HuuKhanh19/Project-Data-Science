import unittest

import pandas as pd

from tests.support import install_loguru_stub, install_ta_stub

install_loguru_stub()
install_ta_stub()

import preprocessing.process_prices as process_prices_module


class ProcessPricesTests(unittest.TestCase):
    def test_clean_raw_prices_drops_missing_ohlcv_rows_instead_of_filling_them(self):
        raw_df = pd.DataFrame(
            [
                {"date": "2024-01-01", "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0, "volume": 1000},
                {"date": "2024-01-02", "open": None, "high": 12.0, "low": 10.0, "close": 11.0, "volume": 1100},
                {"date": "2024-01-03", "open": 12.0, "high": 13.0, "low": 11.0, "close": 12.0, "volume": 1200},
            ]
        )

        cleaned = process_prices_module.clean_raw_prices(raw_df)

        self.assertEqual(cleaned["date"].dt.strftime("%Y-%m-%d").tolist(), ["2024-01-01", "2024-01-03"])


if __name__ == "__main__":
    unittest.main()
