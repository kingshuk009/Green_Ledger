from __future__ import annotations
from typing import Any, Dict, Optional
from .models import ModelPrediction

class SpatialSOCModel:
    """Production adapter for a trained CatBoost SOC model.

    The model itself is intentionally loaded from a user-trained artifact.
    This package never invents a trained model or training accuracy.
    """
    def __init__(self, model=None, model_name='Spatial CatBoost', model_version='untrained'):
        self.model=model; self.model_name=model_name; self.model_version=model_version

    def predict(self, farm_id: str, features: Dict[str, Any], spatial_features: Dict[str, Any], interval: Optional[tuple[float,float]]=None):
        if self.model is None:
            raise RuntimeError('No trained SOC model loaded. Train and provide the model artifact before prediction.')
        row=dict(features); row.update({k:v for k,v in spatial_features.items() if k not in {'neighbor_soc_mean'}})
        value=float(self.model.predict([row])[0])
        lo,hi=(interval if interval else (None,None))
        return ModelPrediction(farm_id,self.model_name,self.model_version,'SOC_Stock_0_30cm_tC_ha',value,lo,hi,
            int(spatial_features.get('neighbor_count',0)),spatial_features.get('nearest_distance_km'),spatial_features.get('weighted_soc_tC_ha'))
