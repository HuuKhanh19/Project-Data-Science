"""
Tiền xử lý báo cáo tài chính + tính Financial Ratios.
═════════════════════════════════════════════════════
Phụ trách: Thành viên B
Branch: feature/process-finance
Chạy: python -m preprocessing.process_finance

Input:  raw_finance table
Output: clean_finance table (có financial ratios)
"""
import pandas as pd
from loguru import logger
from database.connection import read_table, write_table

logger.add("logs/process_finance.log", rotation="1 week")


def process_finance():
    """
    Đọc raw_finance → tính financial ratios → lưu clean_finance.

    Financial ratios cần tính (quan trọng cho ngân hàng TCB):
    - ROE (Return on Equity)
    - ROA (Return on Assets)
    - NIM (Net Interest Margin) — đặc trưng ngân hàng
    - P/E ratio
    - P/B ratio
    - Debt to Equity
    - NPL ratio (Non-performing loans) — đặc trưng ngân hàng
    - Cost to Income ratio
    - Revenue growth (YoY)
    - Profit growth (YoY)
    """
    logger.info("Tiền xử lý báo cáo tài chính...")

    df = read_table("raw_finance")
    logger.info(f"Loaded {len(df)} rows từ raw_finance")

    # Step 1: Pivot to Wide Format
    # Assuming raw_finance is in long format with columns: ticker, quarter, metric_name, value
    clean_finance = df.pivot_table(
        index=['ticker', 'quarter'],
        columns='metric_name',
        values='value',
        aggfunc='first'
    ).reset_index()
    logger.info(f"Pivoted to wide format: {len(clean_finance)} rows, {len(clean_finance.columns)} columns")

    # Step 2: Sort chronologically by quarter (important for YoY growth calculation)
    clean_finance = clean_finance.sort_values(['ticker', 'quarter']).reset_index(drop=True)

    # Step 3: Calculate Core Ratios (with safe division handling)
    # ROE = Net Income / Equity
    clean_finance['ROE'] = clean_finance['Net Income'] / clean_finance['Equity']
    
    # ROA = Net Income / Total Assets
    clean_finance['ROA'] = clean_finance['Net Income'] / clean_finance['Total Assets']
    
    logger.info("Calculated core ratios (ROE, ROA)")

    # Step 4: Calculate Banking-Specific Ratios (safe division with NaN handling)
    # NIM = Net Interest Income / Total Assets
    # Division by zero/NaN → automatically becomes NaN (good for non-bank stocks)
    if 'Net Interest Income' in clean_finance.columns and 'Total Assets' in clean_finance.columns:
        clean_finance['NIM'] = clean_finance['Net Interest Income'] / clean_finance['Total Assets']
    else:
        clean_finance['NIM'] = pd.NA
    
    # NPL = Bad Debt / Total Loans (NaN for non-bank stocks or if data missing)
    if 'Bad Debt' in clean_finance.columns and 'Total Loans' in clean_finance.columns:
        clean_finance['NPL'] = clean_finance['Bad Debt'] / clean_finance['Total Loans']
    else:
        clean_finance['NPL'] = pd.NA
    
    logger.info("Calculated banking-specific ratios (NIM, NPL)")

    # Step 5: Calculate YoY Growth Rates
    # Get numeric columns (excluding ticker and quarter)
    numeric_cols = clean_finance.select_dtypes(include=['number']).columns.tolist()
    
    # Calculate YoY growth (4 quarters back = 1 year for quarterly data)
    for col in numeric_cols:
        growth_col_name = f"{col}_YoY_Growth"
        clean_finance[growth_col_name] = clean_finance.groupby('ticker')[col].pct_change(periods=4, fill_method=None)
    
    logger.info("Calculated YoY growth rates for all numeric columns")

    # Step 6: Handle Missing Values (forward-fill max 1 quarter per ticker)
    # Get all numeric columns again (now includes new growth columns)
    numeric_cols = clean_finance.select_dtypes(include=['number']).columns.tolist()
    
    for col in numeric_cols:
        clean_finance[col] = clean_finance.groupby('ticker')[col].ffill(limit=1)
    
    logger.info("Forward-filled missing values (limit=1 per ticker)")

    # Step 7: Final Output - Reset index
    clean_finance = clean_finance.reset_index(drop=True)

    # Save to database and CSV
    write_table(clean_finance, "clean_finance")
    
    # Save CSV với xử lý lỗi
    try:
        clean_finance.to_csv("clean_finance.csv", index=False)
        logger.info("Saved clean_finance.csv")
    except PermissionError:
        logger.warning("Could not save to clean_finance.csv (file is locked). Saving to clean_finance_temp.csv instead")
        clean_finance.to_csv("clean_finance_temp.csv", index=False)
    
    logger.info(f"Successfully saved clean_finance: {len(clean_finance)} rows, {len(clean_finance.columns)} columns")
    
    return clean_finance


if __name__ == "__main__":
    process_finance()
