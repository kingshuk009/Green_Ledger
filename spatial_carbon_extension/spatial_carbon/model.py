from pathlib import Path
import json
import numpy as np
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

class SpatialSOCModel:
    def __init__(self, model=None, feature_columns=None, categorical_columns=None, metadata=None):
        self.model = model
        self.feature_columns = feature_columns or []
        self.categorical_columns = categorical_columns or []
        self.metadata = metadata or {}

    def fit(self, X, y, cat_features=None):
        self.feature_columns = list(X.columns)
        self.categorical_columns = list(cat_features or [])
        idx = [X.columns.get_loc(c) for c in self.categorical_columns if c in X.columns]
        self.model = CatBoostRegressor(
            loss_function="RMSE", eval_metric="RMSE", iterations=1200,
            depth=7, learning_rate=0.03, l2_leaf_reg=5,
            random_seed=42, verbose=False)
        self.model.fit(X, y, cat_features=idx)
        return self

    def predict(self, X):
        if self.model is None:
            raise RuntimeError("Model not loaded/trained")
        return np.asarray(self.model.predict(X), dtype=float)

    def evaluate(self, X, y):
        p = self.predict(X)
        return {
            "MAE_tC_ha": float(mean_absolute_error(y,p)),
            "RMSE_tC_ha": float(mean_squared_error(y,p)**0.5),
            "R2": float(r2_score(y,p))
        }

    def save(self, directory):
        d = Path(directory); d.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(d/"spatial_soc_catboost.cbm"))
        (d/"metadata.json").write_text(json.dumps({
            "feature_columns": self.feature_columns,
            "categorical_columns": self.categorical_columns,
            "metadata": self.metadata
        }, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, directory):
        d = Path(directory)
        m = CatBoostRegressor()
        m.load_model(str(d/"spatial_soc_catboost.cbm"))
        meta = json.loads((d/"metadata.json").read_text(encoding="utf-8"))
        return cls(m, meta["feature_columns"], meta.get("categorical_columns", []),
                   meta.get("metadata", {}))
