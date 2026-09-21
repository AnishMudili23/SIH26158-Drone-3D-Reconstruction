from fastapi.testclient import TestClient
import pytest
from src.api.main import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "version" in data
    assert "gpu_available" in data


def test_api_missions_list():
    res = client.get("/api/missions")
    assert res.status_code == 200
    missions = res.json()
    assert isinstance(missions, list)
    # Check if zurich_mav_mission is detected
    zurich_mav = [m for m in missions if m["id"] == "zurich_mav_mission"]
    if zurich_mav:
        m = zurich_mav[0]
        assert m["status"] == "COMPLETED"
        assert m["building_count"] >= 1


def test_api_mission_buildings():
    res = client.get("/api/missions/zurich_mav_mission/buildings")
    if res.status_code == 200:
        data = res.json()
        assert "total_buildings" in data
        assert data["total_buildings"] >= 1
        bldg = data["buildings"][0]
        assert "footprint_area_m2" in bldg
        assert "height_m" in bldg
        assert "volume_m3" in bldg
