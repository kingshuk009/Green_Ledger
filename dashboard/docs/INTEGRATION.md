# Integration with existing GreenLedger

## Module 0

No changes are required. The dashboard calls:

- `GET /api/farms/{farm_id}`
- `GET /api/farms/{farm_id}/observations`

The registered polygon remains the primary land unit. The dashboard never substitutes the centroid for the polygon.

## Module 1

No changes are required. The dashboard consumes Module 1 observation fields already persisted through Module 0, including:

- `mean_ndvi`
- `vegetation_area_ha`
- `vegetation_coverage_pct`
- `vegetation_health`
- `cloud_cover_pct`
- `scene_id`
- `observation_date`

If Module 1 exposes a real polygon-clipped NDVI raster as `.npy`, place it under the farm data directory as `ndvi.npy` for the spatial heatmap.

## Carbon model

The dashboard intentionally does not silently train a model. A real trained SOC model and a real held-out validation set must be supplied. This prevents the presentation layer from inventing accuracy.
