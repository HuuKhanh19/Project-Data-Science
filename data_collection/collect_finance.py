"""
Thu thập báo cáo tài chính TCB (3 năm, theo quý).
═══════════════════════════════════════════════════
Phụ trách: Thành viên B
Branch: feature/collect-finance
Chạy: python -m data_collection.collect_finance

Output: raw_finance table trong SQLite
"""
from vnstock import Vnstock
from loguru import logger
from database.connection import get_connection, write_table
from config.settings import SYMBOL, DATA_SOURCE

logger.add("logs/collect_finance.log", rotation="1 week")


def collect_finance():
    """
    Lấy báo cáo tài chính TCB (income, balance sheet, cash flow) và lưu vào raw_finance.

    Cần lấy 3 loại báo cáo:
    - Income Statement (Kết quả kinh doanh)
    - Balance Sheet (Bảng cân đối kế toán)
    - Cash Flow Statement (Lưu chuyển tiền tệ)

    Mỗi báo cáo lấy theo quý, 12 quý gần nhất (3 năm).
    """
    logger.info(f"Thu thập báo cáo tài chính {SYMBOL}...")
    try:
        # Lấy báo cáo tài chính TCB (income, balance sheet, cash flow) và lưu vào raw_finance
        stock = Vnstock().stock(symbol=SYMBOL, source=DATA_SOURCE)
        logger.info("Bắt đầu lấy income statement...")
        income_df = stock.finance.income_statement(period='quarter', count=12)
        logger.info(f"Income statement: {income_df.shape if hasattr(income_df, 'shape') else type(income_df)}")
        logger.info("Bắt đầu lấy balance sheet...")
        balance_df = stock.finance.balance_sheet(period='quarter', count=12)
        logger.info(f"Balance sheet: {balance_df.shape if hasattr(balance_df, 'shape') else type(balance_df)}")
        logger.info("Bắt đầu lấy cash flow statement...")
        cashflow_df = stock.finance.cash_flow(period='quarter', count=12)
        logger.info(f"Cash flow statement: {cashflow_df.shape if hasattr(cashflow_df, 'shape') else type(cashflow_df)}")

        # Gộp các báo cáo vào một DataFrame
        import pandas as pd
        df = pd.concat([income_df, balance_df, cashflow_df], ignore_index=True)
        logger.info(f"Tổng số dòng sau khi gộp: {df.shape[0]}")

        # Chuyển đổi format nếu cần (tuỳ schema raw_finance)
        # Ví dụ: df = df.rename(columns={...})

        # Lưu vào bảng raw_finance
        logger.info("Bắt đầu ghi vào bảng raw_finance...")
        write_table(df, "raw_finance")
        logger.success("Đã ghi dữ liệu vào bảng raw_finance thành công!")
    except Exception as e:
        logger.error(f"Lỗi khi thu thập hoặc ghi dữ liệu: {e}")


if __name__ == "__main__":
    collect_finance()
