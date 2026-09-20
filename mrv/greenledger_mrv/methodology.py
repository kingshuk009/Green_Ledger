from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from .soc import soc_change_tC_ha, carbon_to_co2e
from .models import MRVResult, ModelPrediction

@dataclass
class Methodology:
    id: str
    version: str
    name: str
    jurisdiction: str
    status: str
    notes: str = ''

VM0042_V22 = Methodology('VCS-VM0042','2.2','Improved Agricultural Land Management','International','active','Use with the June 11, 2026 Corrections and Clarifications. This package is an implementation scaffold, not certification.')
INDIA_CCTS = Methodology('IND-CCTS-OFFSET','current','Indian Carbon Credit Trading Scheme Offset Mechanism','India','active','Must use an applicable BEE-approved methodology for official Indian CCC issuance.')

class MRVEngine:
    def __init__(self, methodology: Methodology): self.methodology=methodology

    def quantify(self, farm_id: str, area_ha: float, baseline_soc: Optional[float], prediction: ModelPrediction,
                 uncertainty_pct: Optional[float]=None, eligibility: bool=False, baseline_ok: bool=False,
                 additionality_ok: bool=False, evidence_ok: bool=False, leakage_ok: bool=False, permanence_ok: bool=False) -> MRVResult:
        limitations=[]
        if not eligibility: limitations.append('Methodology eligibility has not been demonstrated.')
        if baseline_soc is None or not baseline_ok: limitations.append('Baseline SOC/scenario is not established for crediting.')
        if not additionality_ok: limitations.append('Additionality evidence is not established.')
        if not evidence_ok: limitations.append('Required measurement/evidence package is incomplete.')
        if not leakage_ok: limitations.append('Leakage assessment is incomplete.')
        if not permanence_ok: limitations.append('Permanence/risk assessment is incomplete.')
        project=prediction.prediction_tC_ha
        change=None if baseline_soc is None else soc_change_tC_ha(project,baseline_soc)
        removal=None if change is None else carbon_to_co2e(change*area_ha)
        conservative=None
        if removal is not None and uncertainty_pct is not None:
            conservative=removal*max(0.0,1.0-uncertainty_pct/100.0)
        status='READY_FOR_INTERNAL_MRV_REVIEW' if not limitations else 'ESTIMATE_ONLY'
        return MRVResult(farm_id,self.methodology.id,self.methodology.version,area_ha,baseline_soc,project,change,removal,uncertainty_pct,conservative,status,limitations)
