from __future__ import annotations
import json
from .models import ModelPrediction, MRVResult

def build_report(prediction: ModelPrediction, mrv: MRVResult, checks: dict):
    return {
        'greenledger_result_type':'MRV_CARBON_ASSESSMENT',
        'model_prediction':prediction.to_dict(),
        'mrv_result':mrv.to_dict(),
        'readiness_checks':checks,
        'official_credit_status':'NOT_ISSUED_BY_GREENLEDGER',
        'disclaimer':'Model predictions and MRV estimates are not official carbon credits. Official issuance requires the applicable program, methodology, validation/verification and registry process.'
    }

def save_report(path, report):
    with open(path,'w',encoding='utf-8') as f: json.dump(report,f,indent=2)
