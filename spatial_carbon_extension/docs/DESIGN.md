# Design

## Polygon-first
The registered polygon is the primary land object. Use it for geodesic area,
satellite clipping, NDVI statistics, vegetation area/coverage, and future MRV.

## Centroid-only spatial reference
The centroid is derived from the polygon only for latitude/longitude-based spatial
search, distance calculation, spatial grouping, and human-readable location.
It is never the farm geometry and never replaces polygon satellite analysis.

## Spatially informed model
New polygon -> polygon-level owner + satellite features -> centroid spatial reference
-> nearby observed soil points -> neighbor statistics -> CatBoost SOC prediction.

Neighbor evidence includes count, nearest distance, weighted SOC mean, mean, standard
deviation, minimum and maximum.

## Leakage control
Use spatial GroupKFold rather than a simple random split. Nearby observations in
train and validation can otherwise make performance look unrealistically strong.

## Target
Use observed SOC stock for 0-30 cm when the required SOC concentration, bulk density,
depth and coarse-fragment information are available. Do not manufacture SOC labels
from yield, N/P/K/pH, NDVI, or the old heuristic Carbon Score.

## Status
Research/MRV estimation layer only. Certified credit issuance requires a methodology,
required measurements, uncertainty/baseline/additionality/permanence/leakage treatment,
validation/verification and registry process.
