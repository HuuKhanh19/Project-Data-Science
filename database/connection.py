"""
Kết nối database dùng chung cho toàn bộ project.
"""
from pathlib import Path
import sqlite3

import pandas as pd
from utils.logger import logger

from config.settings import DB_PATH


logger.add("logs/database.log", rotation="1 week")


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    target = db_path or DB_PATH
    if str(target) == ":memory:":
        conn = sqlite3.connect(":memory:")
    else:
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(target_path))

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    result = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return result is not None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]


def read_table(table_name: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        if not _table_exists(conn, table_name):
            logger.error(f"Table '{table_name}' does not exist")
            raise ValueError(f"Table '{table_name}' not found in database")

        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        logger.info(f"Loaded {len(df)} rows from table '{table_name}'")
        return df
    finally:
        conn.close()


def write_table(df: pd.DataFrame, table_name: str, if_exists: str = "replace"):
    conn = get_connection()
    try:
        from database.schema import MANAGED_TABLE_SQL, ensure_managed_table_schema

        if table_name in MANAGED_TABLE_SQL:
            ensure_managed_table_schema(conn, table_name)

            if if_exists not in {"replace", "append"}:
                raise ValueError(f"Unsupported if_exists='{if_exists}' for managed table '{table_name}'")

            if if_exists == "replace":
                conn.execute(f"DELETE FROM {table_name}")

            if not df.empty:
                table_columns = _table_columns(conn, table_name)
                write_columns = [
                    column
                    for column in df.columns
                    if column in table_columns and column not in {"id", "created_at"}
                ]
                if not write_columns:
                    raise ValueError(f"No writable columns found for managed table '{table_name}'")

                df[write_columns].to_sql(table_name, conn, if_exists="append", index=False)

            conn.commit()
            logger.info(
                f"Wrote {len(df)} rows to managed table '{table_name}' "
                f"(if_exists={if_exists}, schema preserved)"
            )
            return

        df.to_sql(table_name, conn, if_exists=if_exists, index=False)
        conn.commit()
        logger.info(f"Wrote {len(df)} rows to table '{table_name}' (if_exists={if_exists})")
    finally:
        conn.close()


def table_exists(table_name: str) -> bool:
    conn = get_connection()
    try:
        return _table_exists(conn, table_name)
    finally:
        conn.close()


def table_row_count(table_name: str) -> int:
    conn = get_connection()
    try:
        if not _table_exists(conn, table_name):
            return 0
        result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0]
    finally:
        conn.close()


def list_tables() -> list[str]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Database contains {len(tables)} tables: {tables}")
        return tables
    finally:
        conn.close()


def get_table_info(table_name: str) -> dict | None:
    conn = get_connection()
    try:
        if not _table_exists(conn, table_name):
            return None

        columns = [(row[1], row[2]) for row in conn.execute(f"PRAGMA table_info({table_name})")]
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

        return {
            "name": table_name,
            "columns": columns,
            "row_count": row_count,
        }
    finally:
        conn.close()
