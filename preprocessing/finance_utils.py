"""Utilities for quarter-based finance dates and timing rules."""
from datetime import date, timedelta

from config.settings import FINANCE_REPORT_LAG_DAYS


def parse_quarter_code(quarter_code: str) -> tuple[int, int]:
    text = str(quarter_code).strip().upper().replace(" ", "")
    if "-Q" in text:
        year_text, quarter_text = text.split("-Q", maxsplit=1)
    elif "Q" in text:
        year_text, quarter_text = text.split("Q", maxsplit=1)
    else:
        raise ValueError(f"Invalid quarter code: {quarter_code}")

    year = int(year_text)
    quarter = int(quarter_text)
    if quarter not in {1, 2, 3, 4}:
        raise ValueError(f"Invalid quarter number in code: {quarter_code}")
    return year, quarter


def normalize_quarter_code(quarter_code: str) -> str:
    year, quarter = parse_quarter_code(quarter_code)
    return f"{year}-Q{quarter}"


def quarter_period_end_date(quarter_code: str) -> date:
    year, quarter = parse_quarter_code(quarter_code)
    quarter_end = {
        1: date(year, 3, 31),
        2: date(year, 6, 30),
        3: date(year, 9, 30),
        4: date(year, 12, 31),
    }
    return quarter_end[quarter]


def quarter_effective_date(quarter_code: str, lag_days_map=None) -> date:
    lag_days_map = lag_days_map or FINANCE_REPORT_LAG_DAYS
    _, quarter = parse_quarter_code(quarter_code)
    period_end = quarter_period_end_date(quarter_code)
    lag_days = lag_days_map[f"Q{quarter}"]
    return period_end + timedelta(days=int(lag_days))
