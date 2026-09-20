import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from .model import SpatialSOCModel

def make_spatial_groups(df, cell_deg=0.5):
    a = np.floor(df.latitude/cell_deg).astype(int)
    b = np.floor(df.longitude/cell_deg).astype(int)
    return a.astype(str) + "_" + b.astype(str)

def spatial_group_cv(df, features, target, categorical=None, n_splits=5, cell_deg=0.5):
    groups = make_spatial_groups(df, cell_deg)
    splitter = GroupKFold(n_splits=n_splits)
    results = []
    for fold, (tr, va) in enumerate(splitter.split(df, df[target], groups), 1):
        model = SpatialSOCModel().fit(
            df.iloc[tr][features], df.iloc[tr][target],
            cat_features=categorical or [])
        s = model.evaluate(df.iloc[va][features], df.iloc[va][target])
        s.update({"fold": fold, "train_n": len(tr), "valid_n": len(va)})
        results.append(s)
    return pd.DataFrame(results)
