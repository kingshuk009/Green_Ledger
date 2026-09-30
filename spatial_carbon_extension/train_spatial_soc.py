import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from spatial_carbon.model import SpatialSOCModel
from spatial_carbon.validation import spatial_group_cv

CAT = [
    "Crop",
    "Irrigation_Type",
    "Soil_Type",
    "Season"
]
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--target", default="SOC_Stock(tC/ha)")
    p.add_argument("--model-dir", default="models/spatial_soc")
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--cell-deg", type=float, default=0.5)

    a = p.parse_args()

    df = pd.read_csv(a.csv)

    # Convert CSV numeric fields to numeric values
    percent_columns = [
        "Nitrogen - High",
        "Nitrogen - Medium",
        "Nitrogen - Low",
        "Phosphorous - High",
        "Phosphorous - Medium",
        "Phosphorous - Low",
        "Potassium - High",
        "Potassium - Medium",
        "Potassium - Low",
        "pH - Acidic",
        "pH - Neutral",
        "pH - Alkaline",
    ]

    numeric_columns = [
        "Latitude",
        "Longitude",
        "Fertilizer_Used(tons)",
        "Pesticide_Used(kg)",
        "Yield(tons)",
        "Water_Usage(cubic meters)",
        "SOC(%)",
        "Bulk_Density(g/cm³)",
        "Depth(cm)",
        "Coarse_Fragment(%)",
        "SOC_Stock(tC/ha)",
    ]

    for col in percent_columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace("%", "", regex=False)
            .astype(float)
        )

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Latitude", "Longitude", a.target])

    need = {"Latitude", "Longitude", a.target}
    miss = need - set(df.columns)

    if miss:
        raise SystemExit(
            f"Missing required columns: {sorted(miss)}"
        )

    features = [
        "Latitude",
        "Longitude",
        "Crop",
        "Nitrogen - High",
        "Nitrogen - Medium",
        "Nitrogen - Low",
        "Phosphorous - High",
        "Phosphorous - Medium",
        "Phosphorous - Low",
        "Potassium - High",
        "Potassium - Medium",
        "Potassium - Low",
        "pH - Acidic",
        "pH - Neutral",
        "pH - Alkaline",
        "Irrigation_Type",
        "Fertilizer_Used(tons)",
        "Pesticide_Used(kg)",
        "Yield(tons)",
        "Soil_Type",
        "Season",
        "Water_Usage(cubic meters)"
    ]
    cat = CAT    
    scores, predictions = spatial_group_cv(df,features,a.target,cat,a.folds,a.cell_deg)
    out=Path(a.model_dir); out.mkdir(parents=True,exist_ok=True)
   # Save out-of-fold predictions for the dashboard
    dashboard_validation = (
    Path(__file__).resolve().parents[1]
    / "dashboard"
    / "data"
    / "validation"
)
    dashboard_validation.mkdir(parents=True, exist_ok=True)

    predictions.to_csv(
    dashboard_validation / "soc_validation.csv",
    index=False
)

# Calculate overall validation metrics from all out-of-fold predictions
    y_true = predictions["actual_soc_tC_ha"]
    y_pred = predictions["predicted_soc_tC_ha"]

    metrics = {
    "available": True,
    "rows": int(len(predictions)),
    "mae_tC_ha": float(mean_absolute_error(y_true, y_pred)),
    "rmse_tC_ha": float(mean_squared_error(y_true, y_pred) ** 0.5),
    "r2": float(r2_score(y_true, y_pred))
}

    (dashboard_validation / "metrics.json").write_text(
    json.dumps(metrics, indent=2),
    encoding="utf-8"
    )

    scores.to_csv(out/"spatial_cv_results.csv",index=False)
    print(scores)
    model=SpatialSOCModel().fit(df[features],df[a.target],cat)
    model.metadata={"target":a.target,"validation":"spatial GroupKFold",
                    "cell_deg":a.cell_deg,"categorical_columns":cat}
    model.save(out)
    print("Saved:",out)

if __name__=="__main__": main()
