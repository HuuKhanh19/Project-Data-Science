"""Load saved model and predict next-day close using recent rows."""
import argparse
import logging
import sqlite3
from pathlib import Path

import pandas as pd

from config import settings
from models.lstm_model import LSTMPredictor


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(settings.DB_PATH))
    parser.add_argument("--table", default=settings.TABLE_MERGED_FEATURES)
    parser.add_argument("--name", default=settings.DEFAULT_MODEL_NAME)
    return parser


def load_merged_features(db_path: Path, table_name: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn, parse_dates=["date"])
    finally:
        conn.close()
    return df


def main():
    args = build_parser().parse_args()

    df = load_merged_features(Path(args.db), args.table)
    df = df.sort_values("date").reset_index(drop=True) if "date" in df.columns else df

    model = LSTMPredictor()
    model.load(name=args.name)

    for column in model.feature_cols:
        if column not in df.columns:
            raise RuntimeError(f"Required feature missing in data: {column}")

    recent = df.tail(model.lookback_days)
    pred = model.predict_next(recent)
    logger.info(f"Predicted next close: {pred:,.2f}")


if __name__ == "__main__":
    main()
