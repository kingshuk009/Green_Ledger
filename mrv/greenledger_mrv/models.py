from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

@dataclass
class ModelPrediction:
    farm_id: str
    model_name: str
    model_version: str
    target: str
    prediction_tC_ha: float
    lower_tC_ha: Optional[float] = None
    upper_tC_ha: Optional[float] = None
    spatial_neighbor_count: int = 0
    nearest_neighbor_km: Optional[float] = None
    spatial_weighted_tC_ha: Optional[float] = None
    created_at: str = ""
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
    def to_dict(self): return asdict(self)

@dataclass
class MRVResult:
    farm_id: str
    methodology_id: str
    methodology_version: str
    area_ha: float
    baseline_soc_tC_ha: Optional[float]
    project_soc_tC_ha: Optional[float]
    soc_change_tC_ha: Optional[float]
    estimated_removal_tCO2e: Optional[float]
    uncertainty_pct: Optional[float]
    conservative_removal_tCO2e: Optional[float]
    status: str
    limitations: List[str]
    created_at: str = ""
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
    def to_dict(self): return asdict(self)
