import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from .model import SpatialSOCModel

def make_spatial_groups(df, cell_deg=0.5):
    a = np.floor(df["Latitude"] / cell_deg).astype(int)
    b = np.floor(df["Longitude"] / cell_deg).astype(int)
    return a.astype(str) + "_" + b.astype(str)

def spatial_group_cv(df, features, target, categorical=None, n_splits=5, cell_deg=0.5):
    groups = make_spatial_groups(df, cell_deg)
    splitter = GroupKFold(n_splits=n_splits)

    results = []
    predictions = []

    for fold, (tr, va) in enumerate(
        splitter.split(df, df[target], groups), 1
    ):
        model = SpatialSOCModel().fit(
            df.iloc[tr][features],
            df.iloc[tr][target],
            cat_features=categorical or []
        )

        X_val = df.iloc[va][features]
        y_val = df.iloc[va][target]

        pred = model.predict(X_val)

        # Fold metrics
        s = model.evaluate(X_val, y_val)
        s.update({
            "fold": fold,
            "train_n": len(tr),
            "valid_n": len(va)
        })
        results.append(s)

        # Out-of-fold predictions for dashboard
        farm_ids = (
            df.iloc[va]["Farm_ID"].astype(str).tolist()
            if "Farm_ID" in df.columns
            else df.iloc[va].index.astype(str).tolist()
        )

        for farm_id, actual, predicted in zip(
            farm_ids,
            y_val.tolist(),
            pred.tolist()
        ):
            predictions.append({
                "farm_id": farm_id,
                "actual_soc_tC_ha": float(actual),
                "predicted_soc_tC_ha": float(predicted),
                "fold": fold
            })

    return pd.DataFrame(results), pd.DataFrame(predictions)