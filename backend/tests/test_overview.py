from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.domain.devices.entity import Device
from src.domain.sensors.reading import Reading
from src.infrastructure.persistence.base import Base, get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository
from src.main import app

T0 = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def session():
    s = TestingSession()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client():
    def override_get_db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


def seed_device(session, *, device_type, role, name, zone_id=None, location_id=None):
    return DeviceRepository(session).save_device(
        Device(
            id=uuid4(),
            device_type=device_type,
            role=role,
            device_family="simulation",
            display_name=name,
            default_config={"protocol": "simulation"},
            zone_id=UUID(zone_id) if zone_id else None,
            location_id=UUID(location_id) if location_id else None,
            sampling_interval_seconds=300,
            tracking_enabled=True,
        )
    )


def test_overview_returns_strategy_and_readings(client, session):
    # Unknown location -> 404
    assert client.get(f"/api/locations/{uuid4()}/overview").status_code == 404

    # Seed: one location, two zones
    resp = client.post(
        "/api/locations",
        json={
            "location_name": "Lab Site A",
            "zones": [
                {"name": "Bench 1", "moisture_threshold_low": 0.25, "moisture_threshold_high": 0.45},
                {"name": "Bench 2", "moisture_threshold_low": 0.30, "moisture_threshold_high": 0.60},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    location_id = body["location"]["id"]
    zone_ids = {z["name"]: z["id"] for z in body["zones"]}

    # Assigned sensor with a reading, in Bench 1
    sensor = seed_device(
        session, device_type="moisture_sensor", role="sensor", name="Bench moisture",
        zone_id=zone_ids["Bench 1"], location_id=location_id,
    )
    ReadingRepository(session).insert(
        Reading(device_id=sensor.id, value=0.31, unit="vwc", source="simulation", recorded_at=T0)
    )
    # Unassigned devices: no zone at all, and location_id without zone_id
    stray = seed_device(session, device_type="moisture_sensor", role="sensor", name="stray")
    half = seed_device(session, device_type="moisture_sensor", role="sensor", name="half", location_id=location_id)
    ReadingRepository(session).insert(
        Reading(device_id=stray.id, value=0.05, unit="vwc", source="simulation", recorded_at=T0)
    )

    # 200, name matches, no key saved -> both strategy fields null
    res = client.get(f"/api/locations/{location_id}/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["location"]["name"] == "Lab Site A"
    assert data["strategy_key"] is None
    assert data["last_recommendation"] is None

    # Assigned devices only
    assert data["device_counts"] == {"sensor": 1, "actuator": 0}
    assert len(data["zones"]) == 2
    all_device_ids = {d["id"] for z in data["zones"] for d in z["devices"]}
    assert all_device_ids == {str(sensor.id)}
    assert str(stray.id) not in all_device_ids
    assert str(half.id) not in all_device_ids

    zones = {z["name"]: z for z in data["zones"]}
    reading = zones["Bench 1"]["latest_readings"][0]
    assert reading["device_id"] == str(sensor.id)
    assert reading["value"] == pytest.approx(0.31)
    assert reading["unit"] == "vwc"
    assert reading["tracking_enabled"] is True
    assert reading["sampling_interval_seconds"] == 300
    assert str(stray.id) not in {r["device_id"] for z in data["zones"] for r in z["latest_readings"]}

    # Empty zone is still listed
    assert zones["Bench 2"]["devices"] == []
    assert zones["Bench 2"]["latest_readings"] == []

    # Save a key -> recommendation matches evaluate for the same location
    assert client.put(
        f"/api/locations/{location_id}/automation", json={"strategy_key": "aggressive"}
    ).status_code == 200
    evaluated = client.post(f"/api/locations/{location_id}/automation/evaluate").json()
    after = client.get(f"/api/locations/{location_id}/overview").json()
    assert after["strategy_key"] == "aggressive"
    assert after["last_recommendation"]["action"] == evaluated["action"]
    assert after["last_recommendation"]["reason"] == evaluated["reason"]