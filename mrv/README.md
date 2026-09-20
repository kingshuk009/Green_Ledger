# GreenLedger — Standards-Aligned MRV Extension

This package adds the downstream standards/MRV layer to the existing GreenLedger Module 0 and Module 1. It does **not** regenerate or replace those modules.

## What you get
- Model prediction object with uncertainty fields.
- Spatial neighbor evidence using centroid only as a reference.
- SOC stock calculation.
- Methodology registry scaffold for India CCTS and Verra VM0042 v2.2.
- Baseline/additionality/evidence/leakage/permanence readiness gates.
- Conservative uncertainty calculation scaffold.
- Audit-event hashing.
- Module 0 API adapter.
- MRV report generation.

## Important scientific rule
Do not train on the old prototype Carbon Score. The production/research target should be a measured/observed SOC quantity such as `SOC_Stock_0_30cm_tC_ha`, with appropriate field/lab provenance.

## Important legal/methodology rule
This software does not issue carbon credits. A model prediction or MRV estimate is not an official credit. Official issuance requires the applicable program, approved methodology, validation/verification and registry process.

## Current reference basis
- India CCTS Offset Mechanism and BEE procedures.
- Verra VCS VM0042 v2.2, active since 21 Oct 2025, with June 11 2026 Corrections and Clarifications.

## Install
```bat
cd /d D:\GL
pip install -r GreenLedger_Standards_MRV\requirements.txt
```

## Example
```bat
python GreenLedger_Standards_MRV\predict_new_farm.py --farm-id FARM_ID
```

## Training
```bat
python GreenLedger_Standards_MRV\train_spatial_soc.py --csv GreenLedger_Standards_MRV\examples\observed_soc.csv --out GreenLedger_Standards_MRV\models\spatial_soc.cbm
```
The example CSV is only a schema/example, not a scientifically sufficient training dataset.
