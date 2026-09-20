# GreenLedger Spatial Carbon MRV Extension

Downstream extension only. Module 0 and Module 1 are NOT regenerated.

Design:
- Registered polygon is the primary land unit.
- Polygon is used for area and polygon-level satellite features.
- Centroid is used ONLY as a spatial reference.
- Nearby observed soil points provide contextual evidence; their SOC is never copied directly.
- Research target: SOC_Stock_0_30cm_tC_ha.
- This package estimates MRV research values; it does not issue certified carbon credits.

Install:
  pip install -r requirements.txt

Train:
  python train_spatial_soc.py --csv data/training_features.csv

Predict:
  python predict_new_farm.py --model-dir models/spatial_soc --observations data/example_observed_soc.csv --polygon-json data/example_new_polygon.json --owner-json data/example_owner.json --satellite-json data/example_satellite.json
