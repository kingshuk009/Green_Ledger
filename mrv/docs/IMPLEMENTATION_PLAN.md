# Integration Plan

1. Copy `greenledger_mrv` into `D:\GL` without modifying Module 0/1.
2. Start Module 0 as currently configured.
3. Point the adapter to Module 0 API.
4. Keep Module 1's satellite observation history unchanged.
5. Add a new SOC-observation ingestion pipeline using measured/observed data such as WoSIS profiles.
6. Train a CatBoost model only when a defensible observed SOC target exists.
7. Validate with spatially separated folds to reduce geographic leakage.
8. For a new farm, derive polygon features first; derive centroid only for spatial-neighbor lookup.
9. Display raw model prediction separately from MRV quantification.
10. Add methodology-specific baseline/additionality/leakage/permanence rules before presenting a result as a crediting assessment.
11. Generate an auditable MRV report.
12. Mark official credit issuance as external/pending until the applicable program's requirements are satisfied.
