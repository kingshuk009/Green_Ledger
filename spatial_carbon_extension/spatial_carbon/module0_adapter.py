import requests

def get_farm(base_url, farm_id):
    r = requests.get(f"{base_url.rstrip('/')}/api/farms/{farm_id}", timeout=30)
    r.raise_for_status(); return r.json()

def get_project(base_url, farm_id):
    r = requests.get(f"{base_url.rstrip('/')}/api/farms/{farm_id}/project", timeout=30)
    r.raise_for_status(); return r.json()

def get_management(base_url, farm_id):
    r = requests.get(f"{base_url.rstrip('/')}/api/farms/{farm_id}/management", timeout=30)
    r.raise_for_status(); return r.json()
