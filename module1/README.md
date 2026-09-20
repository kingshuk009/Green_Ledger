# GreenLedger Module 1 — Work Ready

## What Module 1 does

1. Reads registered farms from **Module 0's database-backed API**.
2. Uses each saved farm polygon as the satellite area of interest.
3. Authenticates to Copernicus Data Space with your OAuth client credentials.
4. Searches the Catalog API for the newest suitable **Sentinel-2 L2A** observation after the last processed observation.
5. Uses the Process API to download B02, B03, B04 and B08 plus SCL at 10 m.
6. Loads those bands into the existing SILVIA pipeline.
7. Uses the existing SAM model for inference and then filtering/voting.
8. Calculates true NDVI from B08 and B04.
9. Calculates vegetation area and coverage.
10. Saves the dated observation back into Module 0's `observations` table.
11. The scheduler repeats the check automatically.

## What you need before running

- Module 0 running at `http://127.0.0.1:8000`
- Copernicus Data Space OAuth `client_id` and `client_secret`
- SAM ViT-H checkpoint at `models/sam_vit_h_4b8939.pth`
- Python dependencies installed
- Network access

You do **not** need to download a large Sentinel-2 training dataset for the production observation workflow. Module 1 obtains the current observation directly from Copernicus Data Space.

## Environment variables

Copy `.env.example` to a secure local configuration mechanism or set the variables in PowerShell/CMD. Never commit the client secret to GitHub.

### PowerShell

```powershell
$env:GREENLEDGER_FARM_API="http://127.0.0.1:8000"
$env:CDSE_CLIENT_ID="YOUR_CLIENT_ID"
$env:CDSE_CLIENT_SECRET="YOUR_CLIENT_SECRET"
$env:SAM_CHECKPOINT="D:/green_ledger/models/sam_vit_h_4b8939.pth"
```

## Run

Start Module 0 first.

Then, in another terminal:

```powershell
cd module1
pip install -r requirements.txt
python module1.py
```

For a notebook workflow:

```powershell
jupyter notebook GreenLedger_Module1_WorkReady.ipynb
```

In the notebook:

```python
farm_registry.list_farms()
```

Then process one farm:

```python
result = check_farm("FARM_...")
```

Or run all registered farms continuously:

```python
run_scheduler(crop_name="Rice")
```

## Automation behavior

The scheduler checks every 24 hours by default. For each farm it:

- gets the farm polygon from Module 0,
- looks for newer Sentinel-2 L2A scenes with cloud cover <= 20%,
- downloads the newest suitable observation,
- runs SAM/SILVIA inference,
- calculates the dated Carbon Score,
- stores the observation in Module 0, and
- records the last processed scene so the same scene is not processed again.

Cloudy observations are filtered by the catalog query. The download also includes Sentinel-2 SCL so cloud/shadow/snow classes can be excluded from the vegetation-area calculation.

## Important methodological note

The existing project Carbon Engine uses the configured vegetation-rate score system. That score should be described as a **satellite-derived Carbon Score** until it is validated against an accepted carbon-accounting methodology and field measurements. It is not automatically a certified carbon-credit quantity.


## Updated observation selection
- `S2_MAX_CLOUD_COVER` controls the maximum scene-level cloud percentage (recommended: 20 for production).
- `S2_INITIAL_LOOKBACK_DAYS` controls the initial search window (default 90 days).
- `S2_MIN_IMAGE_PIXELS` enforces a minimum retrieval raster size (default 64 x 64 at the native 10 m resolution), giving SAM more spatial context without upscaling pixels.
- The catalog results are sorted newest-first after the cloud filter, so the selected scene is the newest usable observation, not simply the newest scene regardless of cloud cover.
