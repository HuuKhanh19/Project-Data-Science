import sqlite3
import unittest
from pathlib import Path

import pandas as pd

from tests.support import install_loguru_stub

install_loguru_stub()

import database.connection as connection_module
import database.schema as schema_module


class ManagedWriteTableTests(unittest.TestCase):
    def setUp(self):
        self.temp_db = Path("database") / "test_managed_write_table.db"
        self.original_db_path = connection_module.DB_PATH
        if self.temp_db.exists():
            self.temp_db.unlink()
        connection_module.DB_PATH = self.temp_db
        schema_module.create_all_tables()

    def tearDown(self):
        connection_module.DB_PATH = self.original_db_path
        if self.temp_db.exists():
            self.temp_db.unlink()

    def test_replace_preserves_managed_table_schema(self):
        df = pd.DataFrame(
            [
                {
                    "date": "2024-01-01",
                    "title": "News item",
                    "content": "Body",
                    "url": "https://example.com/1",
                    "source": "unit-test",
                }
            ]
        )

        connection_module.write_table(df, "raw_news", if_exists="replace")

        conn = sqlite3.connect(self.temp_db)
        try:
            columns = {
                row[1]: row[2]
                for row in conn.execute("PRAGMA table_info(raw_news)").fetchall()
            }
        finally:
            conn.close()

        self.assertIn("id", columns)
        self.assertIn("symbol", columns)
        self.assertIn("created_at", columns)
        self.assertEqual(columns["date"], "TEXT")


if __name__ == "__main__":
    unittest.main()
