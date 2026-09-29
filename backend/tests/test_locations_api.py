import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.persistence.base import Base, get_db
from src.main import app


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_create_and_get_location_config():
    payload = {
        "location_name": "North Wing",
        "zones": [
            {"name": "Zone A", "moisture_threshold_low": 0.2, "moisture_threshold_high": 0.7, "schedule": {"mode": "auto"}},
            {"name": "Zone B", "moisture_threshold_low": 0.3, "moisture_threshold_high": 0.8},
        ],
    }

    response = client.post("/api/locations", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["location"]["name"] == "North Wing"
    assert len(body["zones"]) == 2
    assert body["zones"][0]["location_id"] == body["location"]["id"]

    list_response = client.get("/api/locations")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    config_response = client.get(f"/api/locations/{body['location']['id']}/config")
    assert config_response.status_code == 200
    assert len(config_response.json()["zones"]) == 2


def test_invalid_zone_update_returns_400():
    payload = {
        "location_name": "South Wing",
        "zones": [{"name": "Zone A", "moisture_threshold_low": 0.2, "moisture_threshold_high": 0.8}],
    }
    created = client.post("/api/locations", json=payload).json()
    zone_id = created["zones"][0]["id"]

    patch_response = client.patch(
        f"/api/locations/{created['location']['id']}/zones/{zone_id}",
        json={"name": "Zone A", "moisture_threshold_low": 0.9, "moisture_threshold_high": 0.2, "schedule": {}},
    )
    assert patch_response.status_code == 400


def test_provisioned_devices_can_be_listed_with_cors():
    origin = "http://localhost:5173"
    provision_response = client.post(
        "/api/devices/provision?family=simulation",
        headers={"Origin": origin},
    )
    assert provision_response.status_code == 201, provision_response.text

    response = client.get(
        "/api/devices?family=simulation",
        headers={"Origin": origin},
    )
    assert response.status_code == 200, response.text
    assert response.headers["access-control-allow-origin"] == origin

    devices = response.json()
    assert len(devices) == 4
    assert all(device["zone_id"] is None for device in devices)
    assert all(device["location_id"] is None for device in devices)
