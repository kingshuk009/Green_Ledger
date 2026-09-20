from __future__ import annotations
from typing import Dict

REQUIRED_CHECKS = ['project_eligibility','polygon','satellite_mrv','soil_data','baseline','additionality','ghg_accounting','leakage','permanence','uncertainty','qa_qc','evidence','independent_verification','registry_issuance']

def readiness(checks: Dict[str,bool]):
    return {k: bool(checks.get(k,False)) for k in REQUIRED_CHECKS}

def credit_claim_allowed(checks: Dict[str,bool]) -> bool:
    # Software must not claim official credit issuance. This only indicates readiness for external verification.
    return False
