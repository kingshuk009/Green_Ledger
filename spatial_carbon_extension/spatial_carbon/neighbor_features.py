import numpy as np
import pandas as pd
from .geo import haversine_km

def build_neighbor_features(lat, lon, observations, target_col,
                            radius_km=50.0, max_neighbors=10, power=2.0):
    required = {"latitude", "longitude", target_col}
    missing = required - set(observations.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    rows = observations.dropna(subset=["latitude", "longitude", target_col]).copy()
    if rows.empty:
        return {
            "neighbor_count": 0, "nearest_distance_km": np.nan,
            "neighbor_soc_weighted_mean": np.nan, "neighbor_soc_mean": np.nan,
            "neighbor_soc_std": np.nan, "neighbor_soc_min": np.nan,
            "neighbor_soc_max": np.nan
        }
    rows["_distance_km"] = rows.apply(
        lambda r: haversine_km(lat, lon, r.latitude, r.longitude), axis=1)
    rows = rows[rows["_distance_km"] <= radius_km].sort_values("_distance_km").head(max_neighbors)
    if rows.empty:
        return {
            "neighbor_count": 0, "nearest_distance_km": np.nan,
            "neighbor_soc_weighted_mean": np.nan, "neighbor_soc_mean": np.nan,
            "neighbor_soc_std": np.nan, "neighbor_soc_min": np.nan,
            "neighbor_soc_max": np.nan
        }
    v = rows[target_col].astype(float).to_numpy()
    d = rows["_distance_km"].astype(float).to_numpy()
    w = 1.0 / np.maximum(d, 1e-6) ** power
    return {
        "neighbor_count": int(len(rows)),
        "nearest_distance_km": float(d.min()),
        "neighbor_soc_weighted_mean": float((w*v).sum()/w.sum()),
        "neighbor_soc_mean": float(v.mean()),
        "neighbor_soc_std": float(v.std()),
        "neighbor_soc_min": float(v.min()),
        "neighbor_soc_max": float(v.max())
    }

def add_spatial_features(df, observations, target_col,
                         radius_km=50, max_neighbors=10, power=2):
    feats = [
        build_neighbor_features(r.latitude, r.longitude, observations, target_col,
                                 radius_km, max_neighbors, power)
        for _, r in df.iterrows()
    ]
    return pd.concat([df.copy(), pd.DataFrame(feats, index=df.index)], axis=1)
