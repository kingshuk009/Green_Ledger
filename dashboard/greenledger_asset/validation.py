from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def evaluate_soc_csv(csv_path: str | Path):
    df = pd.read_csv(csv_path)
    required = {"actual_soc_tC_ha", "predicted_soc_tC_ha"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    y = df["actual_soc_tC_ha"].astype(float)
    p = df["predicted_soc_tC_ha"].astype(float)
    rmse = mean_squared_error(y, p) ** 0.5
    return {
        "rows": int(len(df)),
        "mae_tC_ha": float(mean_absolute_error(y, p)),
        "rmse_tC_ha": float(rmse),
        "r2": float(r2_score(y, p)),
        "columns": ["actual_soc_tC_ha", "predicted_soc_tC_ha"],
    }


def save_metrics(csv_path, out_path):
    metrics = evaluate_soc_csv(csv_path)
    Path(out_path).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
