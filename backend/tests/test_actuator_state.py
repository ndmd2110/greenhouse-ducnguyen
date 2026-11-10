from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.domain.actuators.context import ActuatorContext
from src.domain.actuators.errors import IllegalTransitionError, UnknownStateError
from src.domain.actuators.state import STATES
from src.domain.devices.entity import Device
from src.infrastructure.persistence.base import Base, get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.models import ActuatorStateRow
from src.main import app

# ---------- unit tests: transition table, no DB ----------

LEGAL = [
    ("idle", "running"),
    ("running", "idle"),
    ("idle", "off"),
    ("idle", "maintenance"),
    ("off", "idle"),
    ("error", "idle"),  # reset
    ("error", "maintenance"),
    ("maintenance", "idle"),
    # * -> error
    ("idle", "error"),
    ("running", "error"),
    ("off", "error"),
    ("maintenance", "error"),
]

ILLEGAL = [
    ("running", "maintenance"),
    ("running", "off"),
    ("off", "running"),
    ("off", "maintenance"),
    ("error", "running"),
    ("error", "off"),
    ("maintenance", "running"),
    ("maintenance", "off"),
    ("idle", "idle"),
    ("error", "error"),
]


def test_table_covers_every_state():
    assert set(STATES) == {"off", "idle", "running", "error", "maintenance"}


@pytest.mark.parametrize("current,target", LEGAL)
def test_legal_edges(current, target):
    ctx = ActuatorContext(uuid4(), current)
    ctx.transition(target)
    assert ctx.state == target


def test_idle_to_running_allowed():
    ctx = ActuatorContext(uuid4(), "idle")
    ctx.transition("running")
    assert ctx.state == "running"


@pytest.mark.parametrize("current,target", ILLEGAL)
def test_illegal_edges_raise_and_do_not_mutate(current, target):
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ctx = ActuatorContext(uuid4(), current, updated_at=stamp)
    with pytest.raises(IllegalTransitionError):
        ctx.transition(target)
    assert ctx.state == current
    assert ctx.updated_at == stamp


def test_running_to_maintenance_rejected():
    with pytest.raises(IllegalTransitionError):
        ActuatorContext(uuid4(), "running").transition("maintenance")


def test_unknown_target_rejected():
    with pytest.raises(UnknownStateError):
        ActuatorContext(uuid4(), "idle").transition("banana")


def test_allowed_commands_follow_state():
    assert ActuatorContext(uuid4(), "idle").allowed_commands() == ["start_pump"]
    assert ActuatorContext(uuid4(), "running").allowed_commands() == ["stop_pump"]
    assert ActuatorContext(uuid4(), "error").allowed_commands() == []


# ---------- integration tests: DB + API ----------

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


def provision_pump(client) -> dict:
    resp = client.post("/api/devices/provision?family=simulation")
    assert resp.status_code == 201, resp.text
    return next(d for d in resp.json() if d["device_type"] == "water_pump")


def stored_state(session, device_id: str) -> ActuatorStateRow:
    session.expire_all()
    return session.get(ActuatorStateRow, UUID(device_id))


def test_provisioned_actuator_is_idle_with_allowed_commands(client):
    resp = client.post("/api/devices/provision?family=simulation")
    devices = resp.json()
    pump = next(d for d in devices if d["device_type"] == "water_pump")
    assert pump["state"] == "idle"
    assert pump["allowed_commands"] == ["start_pump"]
    sensors = [d for d in devices if d["role"] == "sensor"]
    assert sensors and all(s["state"] is None and s["allowed_commands"] == [] for s in sensors)


def test_legal_transition_updates_row(client, session):
    pump = provision_pump(client)
    resp = client.post(f"/api/devices/{pump['id']}/transition", json={"target": "running"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["state"] == "running"
    assert resp.json()["allowed_commands"] == ["stop_pump"]
    assert stored_state(session, pump["id"]).state == "running"


def test_illegal_transition_does_not_update_row(client, session):
    pump = provision_pump(client)
    assert client.post(f"/api/devices/{pump['id']}/transition", json={"target": "running"}).status_code == 200
    before = stored_state(session, pump["id"]).updated_at

    resp = client.post(f"/api/devices/{pump['id']}/transition", json={"target": "maintenance"})
    assert resp.status_code == 409
    assert "running" in resp.json()["detail"]

    row = stored_state(session, pump["id"])
    assert row.state == "running"
    assert row.updated_at == before


def test_unknown_target_is_400(client):
    pump = provision_pump(client)
    assert client.post(f"/api/devices/{pump['id']}/transition", json={"target": "banana"}).status_code == 400


def test_missing_actuator_and_sensor_are_404(client):
    assert client.post(f"/api/devices/{uuid4()}/transition", json={"target": "running"}).status_code == 404
    resp = client.post("/api/devices/provision?family=simulation")
    sensor = next(d for d in resp.json() if d["role"] == "sensor")
    assert client.post(f"/api/devices/{sensor['id']}/transition", json={"target": "running"}).status_code == 404


def test_state_survives_a_fresh_session(client):
    pump = provision_pump(client)
    client.post(f"/api/devices/{pump['id']}/transition", json={"target": "running"})
    listed = client.get("/api/devices?role=actuator").json()
    assert next(d for d in listed if d["id"] == pump["id"])["state"] == "running"


def test_actuator_without_state_row_resolves_to_idle(client, session):
    device = DeviceRepository(session).save_device(
        Device(
            id=uuid4(),
            device_type="water_pump",
            role="actuator",
            device_family="simulation",
            display_name="legacy pump",
            default_config={"protocol": "simulation"},
        )
    )
    session.query(ActuatorStateRow).delete()  # simulate an actuator created before Phase 8
    session.commit()

    listed = client.get("/api/devices?role=actuator").json()
    legacy = next(d for d in listed if d["id"] == str(device.id))
    assert legacy["state"] == "idle"
    assert stored_state(session, str(device.id)).state == "idle"