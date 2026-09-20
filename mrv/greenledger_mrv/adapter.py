from __future__ import annotations
import requests

def get_farm(module0_url: str, farm_id: str):
    r=requests.get(f'{module0_url.rstrip("/")}/api/farms/{farm_id}',timeout=30); r.raise_for_status(); return r.json()

def get_observations(module0_url: str, farm_id: str):
    r=requests.get(f'{module0_url.rstrip("/")}/api/farms/{farm_id}/observations',timeout=30); r.raise_for_status(); return r.json()

def get_project(module0_url: str, farm_id: str):
    r=requests.get(f'{module0_url.rstrip("/")}/api/farms/{farm_id}/project',timeout=30); r.raise_for_status(); return r.json()

def get_management(module0_url: str, farm_id: str):
    r=requests.get(f'{module0_url.rstrip("/")}/api/farms/{farm_id}/management',timeout=30); r.raise_for_status(); return r.json()
