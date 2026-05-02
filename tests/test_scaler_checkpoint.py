import os
import numpy as np
from pathlib import Path

from models.lstm_model import LSTMPredictor


def test_scaler_checkpoint_roundtrip(tmp_path):
    # Prepare small synthetic dataset to fit scalers
    X = np.array([
        [1.0, 10.0, 100.0],
        [2.0, 11.0, 110.0],
        [3.0, 12.0, 120.0],
        [4.0, 13.0, 130.0],
        [5.0, 14.0, 140.0],
    ])
    y = np.array([10.0, 11.0, 12.0, 13.0, 14.0])

    pred = LSTMPredictor()
    # ensure model exists so save() can serialize state_dict
    pred.model = pred.build_model(input_size=X.shape[1])
    # ensure feature_cols is set so load() can rebuild model correctly
    pred.feature_cols = [f"f{i}" for i in range(X.shape[1])]

    # Fit scalers
    pred.feature_scaler.fit(X)
    pred.target_scaler.fit(y.reshape(-1, 1))

    # Save checkpoint under a test name
    test_name = "unit_test_scaler"
    pred.save(name=test_name)

    saved_path = Path("models") / "saved" / f"tcb_{test_name}.pt"
    assert saved_path.exists(), "Checkpoint file not written"

    # Load into a fresh predictor
    new_pred = LSTMPredictor()
    new_pred.load(name=test_name)

    # Compare scaler attributes
    assert hasattr(new_pred.feature_scaler, "scale_"), "feature_scaler missing scale_"
    assert hasattr(new_pred.target_scaler, "scale_"), "target_scaler missing scale_"

    np.testing.assert_allclose(new_pred.feature_scaler.scale_, pred.feature_scaler.scale_)
    np.testing.assert_allclose(new_pred.target_scaler.scale_, pred.target_scaler.scale_)

    # Cleanup
    try:
        saved_path.unlink()
    except Exception:
        pass
