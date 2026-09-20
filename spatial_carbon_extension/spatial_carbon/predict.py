import pandas as pd
from .geo import polygon_area_ha, polygon_centroid_latlon
from .neighbor_features import build_neighbor_features

def prepare_new_polygon_features(polygon, owner_features, satellite_features,
                                 observed, target="SOC_Stock_0_30cm_tC_ha"):
    lat, lon = polygon_centroid_latlon(polygon)
    row = {**owner_features, **satellite_features,
           "latitude": lat, "longitude": lon,
           "polygon_area_ha": polygon_area_ha(polygon)}
    n = build_neighbor_features(lat, lon, observed, target)
    row.update(n)
    return pd.DataFrame([row]), {"centroid_latitude":lat,
                                 "centroid_longitude":lon,
                                 "polygon_area_ha":row["polygon_area_ha"]}, n

def predict_new_polygon(model, polygon, owner_features, satellite_features, observed):
    X, spatial, neighbors = prepare_new_polygon_features(
        polygon, owner_features, satellite_features, observed)
    X = X.reindex(columns=model.feature_columns, fill_value=None)
    pred = float(model.predict(X)[0])
    return {
        "soc_prediction_tC_ha": pred,
        **spatial,
        "spatial_reference": "centroid_only",
        "neighbor_evidence": neighbors,
        "note": "Nearby observations are contextual evidence, not copied parcel values."
    }
