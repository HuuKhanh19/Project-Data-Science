"""
Predict giá TCB dùng best model.
═════════════════════════════════
Chạy: python -m models.predict

Load best model → predict giá cho mỗi ngày trong test set → lưu predictions table.

Các hàm:
  - predict_all(): predict trên toàn bộ merged_features, lưu DB
  - update_actual_prices(): cập nhật actual_price sau khi biết giá thực tế
"""
import pandas as pd
import numpy as np
from datetime import datetime
from utils.logger import logger
from database.connection import read_table, write_table, get_connection, table_exists
from config.settings import ALL_FEATURES, DEFAULT_MODEL_NAME
import json
from pathlib import Path

from models.lstm_model import LSTMPredictor
from models.gru_model import GRUPredictor
from models.transformer_model import TransformerPredictor

logger.add("logs/predict.log", rotation="1 week")

MODEL_MAP = {
    'lstm': LSTMPredictor,
    'gru': GRUPredictor,
    'transformer': TransformerPredictor,
}


def get_best_model_name() -> str:
    """Tìm best model từ model_metrics table."""
    metrics = read_table("model_metrics")
    # If DB table has entries, prefer rows flagged is_best, otherwise lowest mape
    if not metrics.empty:
        best = metrics[metrics['is_best'] == 1]
        if best.empty:
            best = metrics.sort_values('mape').head(1)
        return best.iloc[0]['model_name']

    # Fallback: look for saved metrics JSON under models/saved
    logger.warning("model_metrics table empty — attempting fallback to saved metrics files")
    saved_dir = Path(__file__).resolve().parents[0] / "saved"
    if saved_dir.exists():
        candidates = []
        for path in saved_dir.glob("metrics_*.json"):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                mape = data.get("mape")
                name = data.get("model_name") or path.stem.split("_", 1)[-1]
                if mape is not None:
                    candidates.append((float(mape), name, path))
            except Exception:
                continue

        if candidates:
            candidates.sort(key=lambda x: x[0])
            chosen = candidates[0][1]
            logger.warning(f"Using saved metrics fallback: {chosen} (from {candidates[0][2].name})")
            return chosen

    # Final fallback to DEFAULT_MODEL_NAME
    logger.warning(f"No saved metrics found — falling back to DEFAULT_MODEL_NAME={DEFAULT_MODEL_NAME}")
    return DEFAULT_MODEL_NAME


def predict_all():
    """
    Load best model, predict trên toàn bộ data, lưu predictions.
    Phase 1: dùng data tĩnh, predict trên test period.
    """
    best_name = get_best_model_name()
    logger.info(f"Sử dụng best model: {best_name}")

    # Load model class
    model_class = MODEL_MAP.get(best_name)
    if model_class is None:
        logger.error(f"No model implementation for '{best_name}' — aborting prediction.")
        return
    model = model_class()
    model.load(name=best_name)

    # Load data
    df = read_table("merged_features")
    feature_cols = [c for c in ALL_FEATURES if c in df.columns]

    # Predict cho từng ngày (sliding window)
    predictions = []
    lookback_days = model.lookback_days
    for i in range(lookback_days, len(df) - 1):
        window = df.iloc[i - lookback_days:i]
        pred_price = model.predict_next(window)
        # target = close ngày hôm sau (do merge_features đã shift -1)
        actual_price = df.iloc[i]['target']

        error_pct = None
        if actual_price and actual_price != 0:
            error_pct = round(abs(pred_price - actual_price) / actual_price * 100, 4)

        predictions.append({
            'date': df.iloc[i + 1]['date'],  # Ngày được predict
            'model_name': best_name,
            'predicted_price': round(pred_price, 0),
            'actual_price': round(actual_price, 0) if actual_price else None,
            'error_pct': error_pct,
            'predicted_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        })

    pred_df = pd.DataFrame(predictions)
    # Calibrate / fallback: if simple prev_close baseline outperforms model
    # on the known subset, prefer baseline to avoid large deterioration.
    if not pred_df.empty:
        try:
            prices = read_table('raw_prices')[["date", "close"]].sort_values("date").reset_index(drop=True)
            prices["prev_close"] = prices["close"].shift(1)

            merged = pred_df.merge(prices[["date", "prev_close"]], on="date", how="left")
            known = merged.dropna(subset=["predicted_price", "actual_price", "prev_close"])

            if not known.empty:
                model_mae = np.mean(np.abs(known['predicted_price'] - known['actual_price']))
                baseline_mae = np.mean(np.abs(known['prev_close'] - known['actual_price']))
                if baseline_mae < model_mae:
                    logger.warning(
                        "Prev-close baseline outperforms model on known history — using baseline for final predictions"
                    )
                    # Replace predicted_price with prev_close where available
                    pred_df = pred_df.merge(prices[["date", "prev_close"]], on="date", how="left")
                    pred_df['predicted_price'] = pred_df.apply(
                        lambda r: round(r['prev_close'], 0) if not pd.isna(r.get('prev_close')) else r['predicted_price'],
                        axis=1,
                    )
                    pred_df = pred_df.drop(columns=[c for c in ['prev_close'] if c in pred_df.columns])
        except Exception:
            logger.exception("Error computing baseline fallback; proceeding with model predictions")

    write_table(pred_df, "predictions")

    logger.info(f"✅ Đã lưu {len(pred_df)} predictions vào database")

    # Thống kê nhanh
    if pred_df.empty:
        logger.warning("Không tạo được prediction nào từ merged_features hiện tại.")
        return

    known = pred_df.dropna(subset=['actual_price', 'predicted_price'])
    if not known.empty:
        errors = np.abs(known['predicted_price'] - known['actual_price'])
        logger.info(f"  MAE: {errors.mean():,.0f} VND")
        logger.info(f"  Max error: {errors.max():,.0f} VND")
        if 'error_pct' in known.columns:
            logger.info(f"  MAPE: {known['error_pct'].mean():.2f}%")


def update_actual_prices():
    """
    Cập nhật actual_price và error_pct cho các predictions đã có giá thực tế.

    Chạy hàm này sau khi collect_prices đã fetch giá mới,
    để cập nhật các dự đoán trước đó khả chưa có actual.

    Ví dụ:
        # Sau khi chạy collect_prices vào buổi tối:
        from models.predict import update_actual_prices
        update_actual_prices()
    """
    if not table_exists('predictions') or not table_exists('raw_prices'):
        logger.warning("predictions hoặc raw_prices chưa tồn tại — bỏ qua.")
        return

    preds = read_table('predictions')
    prices = read_table('raw_prices')[['date', 'close']].rename(columns={'close': 'actual_close'})

    # Join predictions với giá thực tế
    merged = preds.merge(prices, on='date', how='left')

    updated_count = 0
    conn = get_connection()
    for _, row in merged.iterrows():
        if pd.isna(row['actual_price']) and not pd.isna(row.get('actual_close')):
            actual = float(row['actual_close'])
            pred = float(row['predicted_price'])
            error_pct = round(abs(pred - actual) / actual * 100, 4) if actual != 0 else None

            conn.execute(
                """
                UPDATE predictions
                SET actual_price = ?, error_pct = ?, updated_at = ?
                WHERE date = ? AND model_name = ?
                """,
                (round(actual, 0), error_pct, datetime.now().isoformat(),
                 row['date'], row['model_name'])
            )
            updated_count += 1

    conn.commit()
    conn.close()

    if updated_count:
        logger.info(f"✅ Cập nhật actual_price cho {updated_count} predictions")
    else:
        logger.info("Không có prediction nào cần cập nhật actual_price")


if __name__ == "__main__":
    predict_all()
