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


def test_api_mission_trajectory():
    res = client.get("/api/missions/zurich_mav_mission/trajectory")
    if res.status_code == 200:
        data = res.json()
        assert "trajectory" in data
        assert len(data["trajectory"]) > 0
        point0 = data["trajectory"][0]
        assert "lat" in point0
        assert "lon" in point0
        assert "alt" in point0


def test_api_create_and_analyze_mission():
    res = client.post("/api/missions", json={"name": "Test UAV Survey", "mode": "single_pass"})
    assert res.status_code == 200
    mission = res.json()
    assert "id" in mission
    assert mission["name"] == "Test UAV Survey"

    # Analyze
    ares = client.post(f"/api/missions/{mission['id']}/analyze")
    assert ares.status_code == 200
    diag = ares.json()
    assert "readiness_score" in diag
    assert "video" in diag
    assert "gps" in diag
    assert "expected_coverage_pct" in diag


def test_api_reconstruct_job_flow():
    cres = client.post("/api/missions", json={"name": "Job Flow Test", "mode": "single_pass"})
    mid = cres.json()["id"]

    rres = client.post(f"/api/missions/{mid}/reconstruct", json={"adaptive_keyframes": True})
    assert rres.status_code == 200
    job_info = rres.json()
    assert "job_id" in job_info

    # Poll status
    jres = client.get(f"/api/jobs/{job_info['job_id']}")
    assert jres.status_code == 200
    jdata = jres.json()
    assert jdata["status"] in ("QUEUED", "RUNNING", "COMPLETED")
    assert "stage" in jdata


def test_api_provenance():
    res = client.get("/api/missions/zurich_mav_mission/provenance")
    assert res.status_code == 200
    data = res.json()
    assert "mission_id" in data
    assert "structures" in data
    if data["structures"]:
        s0 = data["structures"][0]
        assert "contributing_frames" in s0
        assert "best_observation_frame" in s0
        assert "depth_agreement_pct" in s0


def test_api_report_html():
    res = client.get("/api/missions/zurich_mav_mission/report")
    assert res.status_code == 200
    assert "AeroMesh Mission Report" in res.text
    assert "NTRO VERIFIED" in res.text


def test_api_export_package():
    res = client.get("/api/missions/zurich_mav_mission/export")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"

