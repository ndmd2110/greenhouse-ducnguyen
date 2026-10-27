import inspect
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.domain.automation import context as context_module
from src.domain.automation import strategy as strategy_module
from src.domain.automation.context import LocationAutomationContext
from src.domain.automation.errors import UnknownStrategyError
from src.domain.automation.strategy import (
    AggressiveMoistureStrategy,
    ConservativeMoistureStrategy,
    get_strategy,
)
from src.domain.devices.entity import Device
from src.domain.sensors.reading import Reading
from src.infrastructure.persistence.base import Base, get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.models import AutomationRuleRow
from src.infrastructure.persistence.reading_repository import ReadingRepository
from src.main import app

T0 = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)

# ---------- unit tests: fake context, no DB ----------


def ctx(moisture, low=0.25, high=0.45):
    return LocationAutomationContext(location_id=uuid4(), zone_id=uuid4(), low=low, high=high, moisture=moisture)


def test_conservative_waits_when_within_band():
    rec = ConservativeMoistureStrategy().decide(ctx(0.40))
    assert rec.action == "wait"
    assert rec.reason == "Moisture 0.40 is within 0.25\u20130.45"


def test_conservative_irrigates_below_low():
    rec = ConservativeMoistureStrategy().decide(ctx(0.10))
    assert rec.action == "irrigate"
    assert rec.score is not None and 0 < rec.score <= 1


def test_aggressive_differs_on_same_context():
    same = ctx(0.30)  # inside the band, but in its lower 75%
    conservative = get_strategy("conservative").decide(same)
    aggressive = get_strategy("aggressive").decide(same)
    assert conservative.action == "wait"
    assert aggressive.action == "irrigate"
    assert conservative.reason != aggressive.reason


def test_aggressive_waits_near_top_of_band():
    assert AggressiveMoistureStrategy().decide(ctx(0.44)).action == "wait"


@pytest.mark.parametrize("key", ["conservative", "aggressive"])
def test_no_moisture_means_wait(key):
    rec = get_strategy(key).decide(ctx(None))
    assert rec.action == "wait"
    assert "no moisture" in rec.reason.lower()


def test_unknown_strategy_key_rejected_before_decide():
    with pytest.raises(UnknownStrategyError):
        get_strategy("yolo")


def test_domain_has_no_sqlalchemy():
    for module in (strategy_module, context_module):
        assert "sqlalchemy" not in inspect.getsource(module).lower()


# ---------- integration tests: seeded zones + readings ----------

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


def make_location(client, low=0.25, high=0.45, zone_name="Bed A"):
    resp = client.post(
        "/api/locations",
        json={
            "location_name": "Test greenhouse",
            "zones": [{"name": zone_name, "moisture_threshold_low": low, "moisture_threshold_high": high}],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["location"]["id"], body["zones"][0]["id"]


def add_sensor(session, device_type="moisture_sensor", zone_id=None, location_id=None):
    return DeviceRepository(session).save_device(
        Device(
            id=uuid4(),
            device_type=device_type,
            role="sensor",
            device_family="simulation",
            display_name="seed",
            default_config={"protocol": "simulation"},
            zone_id=UUID(zone_id) if zone_id else None,
            location_id=UUID(location_id) if location_id else None,
        )
    )


def add_reading(session, device, value, at=T0, unit="vwc"):
    ReadingRepository(session).insert(Reading(device_id=device.id, value=value, unit=unit, source="simulation", recorded_at=at))


def test_put_then_evaluate_uses_persisted_key(client, session):
    location_id, zone_id = make_location(client)
    sensor = add_sensor(session, zone_id=zone_id, location_id=location_id)
    add_reading(session, sensor, 0.30)

    assert client.put(f"/api/locations/{location_id}/automation", json={"strategy_key": "conservative"}).status_code == 200
    first = client.post(f"/api/locations/{location_id}/automation/evaluate").json()
    assert (first["strategy_key"], first["action"]) == ("conservative", "wait")

    assert client.put(f"/api/locations/{location_id}/automation", json={"strategy_key": "aggressive"}).status_code == 200
    second = client.post(f"/api/locations/{location_id}/automation/evaluate").json()
    assert (second["strategy_key"], second["action"]) == ("aggressive", "irrigate")


def test_upsert_keeps_one_row_per_location(client, session):
    location_id, _ = make_location(client)
    for key in ("conservative", "aggressive", "conservative"):
        assert client.put(f"/api/locations/{location_id}/automation", json={"strategy_key": key}).status_code == 200
    assert session.execute(select(func.count()).select_from(AutomationRuleRow)).scalar_one() == 1
    assert client.get(f"/api/locations/{location_id}/automation").json()["strategy_key"] == "conservative"


def test_unassigned_device_reading_is_not_used(client, session):
    location_id, _ = make_location(client)
    stray = add_sensor(session)  # no zone
    add_reading(session, stray, 0.05)

    body = client.post(f"/api/locations/{location_id}/automation/evaluate").json()
    assert body["action"] == "wait"
    assert "no moisture" in body["reason"].lower()


def test_latest_reading_wins_and_thresholds_come_from_zone(client, session):
    location_id, zone_id = make_location(client, low=0.5, high=0.9)
    sensor = add_sensor(session, zone_id=zone_id, location_id=location_id)
    add_reading(session, sensor, 0.95, at=T0 - timedelta(minutes=5))  # old, wet
    add_reading(session, sensor, 0.40, at=T0)  # newest, below this zone's low of 0.5

    body = client.post(f"/api/locations/{location_id}/automation/evaluate").json()
    assert body["action"] == "irrigate"
    assert body["zones"][0]["moisture"] == pytest.approx(0.40)


def test_unknown_key_is_400_and_missing_location_is_404(client):
    location_id, _ = make_location(client)
    assert client.put(f"/api/locations/{location_id}/automation", json={"strategy_key": "yolo"}).status_code == 400
    assert client.post(f"/api/locations/{location_id}/automation/evaluate?strategy_key=yolo").status_code == 400

    missing = uuid4()
    assert client.put(f"/api/locations/{missing}/automation", json={"strategy_key": "aggressive"}).status_code == 404
    assert client.post(f"/api/locations/{missing}/automation/evaluate").status_code == 404
    assert client.get(f"/api/locations/{missing}/automation").status_code == 404


def test_strategies_endpoint_lists_both_keys(client):
    keys = {s["key"] for s in client.get("/api/automation/strategies").json()}
    assert keys == {"conservative", "aggressive"}