# Minimum Data Model

## Farm
- farm_id
- polygon GeoJSON
- geodesic area_ha
- project_type
- methodology_id/version

## Observation
- satellite scene id/date
- cloud cover
- SCL quality
- polygon-clipped NDVI/statistics
- segmentation evidence
- historical/current status

## Soil Observation
- lat/lon
- SOC%
- bulk density
- depth
- coarse fragments
- analytical method
- source
- observation date

## Model Prediction
- target
- prediction
- prediction interval
- model/version/hash
- spatial neighbor count
- nearest distance
- weighted neighbor evidence

## MRV Result
- baseline
- project SOC
- SOC change
- GHG emissions/removals
- uncertainty
- leakage
- permanence
- evidence status
- methodology/version

## Audit
Every calculation should retain a timestamp, methodology version, model version and hashes of key input/output payloads.
