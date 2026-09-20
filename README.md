# GreenLedger — Work-Ready Module 0 + Module 1

## Production architecture

Farmer → OpenFreeMap farm boundary → Module 0 database → Module 1 → Copernicus Sentinel-2 → SAM/SILVIA → NDVI/Vegetation Area → Carbon Score → Observation history

### Module 0

- OpenFreeMap + MapLibre interactive map
- Farmer draws field boundary
- Boundary stored as GeoJSON geometry in SQLite
- Farm ID generated automatically
- Area calculated geodesically in hectares
- Observation history stored in the same database

### Module 1

- Reads farms from Module 0's API/database
- Automatically searches Sentinel-2 L2A
- Fetches B02/B03/B04/B08 + SCL
- Uses the existing SAM model in inference mode
- Runs SILVIA filtering/voting
- Computes real NDVI from Red + NIR
- Computes vegetation area
- Computes the project's existing Carbon Score
- Stores each observation by farm/date/scene
- Can monitor all registered farms on a recurring schedule

## First-run checklist

1. No map API key is required for OpenFreeMap.
2. Start Module 0 and register a farm.
3. Create the Copernicus Data Space OAuth client.
4. Set `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET`.
5. Put `sam_vit_h_4b8939.pth` under `module1/models/` or set `SAM_CHECKPOINT`.
6. Start Module 1.
7. Run one farm check manually before enabling the 24-hour scheduler.

## No large dataset is required for production observation retrieval

The automated path queries Copernicus Data Space directly. Historical/training datasets may still be useful for research and benchmarking, but they are not required for fetching the latest Sentinel-2 observation for a registered farm.
