import requests

def get_latest_observation(base_url, farm_id):
    r = requests.get(f"{base_url.rstrip('/')}/api/farms/{farm_id}/observations/latest", timeout=30)
    r.raise_for_status(); return r.json()

def extract_polygon_satellite_features(obs):
    # These must be polygon-clipped Module 1 statistics.
    keys = ["ndvi_mean","ndvi_median","ndvi_std","ndvi_min","ndvi_max",
            "veg_area_ha","veg_coverage_pct","image_quality_score",
            "cloud_cover","valid_pixel_pct"]
    return {k:obs[k] for k in keys if k in obs}
