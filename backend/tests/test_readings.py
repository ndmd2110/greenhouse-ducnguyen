import random
import socket
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.application.readings.sampler import SimulationSampler
from src.application.readings.service import ReadingIngest
from src.domain.devices.entity import Device
from src.domain.sensors.errors import DeviceNotFoundError, InvalidSamplingError, SensorReadError
from src.domain.sensors.sampling import validate_sampling_interval
from src.infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from src.infrastructure.adapters.sensors.mqtt import MqttSensorAdapter
from src.infrastructure.adapters.sensors.profiles import PROFILES
from src.infrastructure.adapters.sensors.selector import select_sensor_port
from src.infrastructure.adapters.sensors.simulation import SimulationSensorAdapter
from src.infrastructure.adapters.sensors.vendor_stub import VendorStubSensorAdapter
from src.infrastructure.persistence.base import Base, get_db
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.models import ReadingRow
from src.infrastructure.persistence.reading_repository import ReadingRepository
from src.main import app

T0 = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)

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
def devices(session):
    return DeviceRepository(session)


@pytest.fixture
def readings(session):
    return ReadingRepository(session)


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
    yield TestClient(app)  # no `with`: lifespan (and the sampler loop) does not start
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


def make_device(device_type="moisture_sensor", protocol="simulation", interval=None, tracking=True, extra=None):
    config = {"protocol": protocol, **(extra or {})}
    if interval is not None:
        config["sampling_interval_seconds"] = interval
    return Device(
        id=uuid4(),
        device_type=device_type,
        role="sensor",
        device_family="simulation" if protocol == "simulation" else "edge",
        display_name="test sensor",
        default_config=config,
        tracking_enabled=tracking,
    )


def build_sampler(devices, readings):
    ingest = ReadingIngest(devices, readings, select_sensor_port)
    return SimulationSampler(devices, readings, ingest, select_sensor_port)


# ---------- adapter unit tests (no HTTP, no broker) ----------

def test_vendor_adapter_normalizes_raw_payload():
    device = make_device()
    raw = {"measurement": {"raw": 410, "scale": 1000, "unit_code": "VWC"}, "ts_epoch_ms": 1_790_000_000_000}

    reading = VendorStubSensorAdapter().translate(device, raw)

    assert reading.device_id == device.id
    assert reading.value == pytest.approx(0.41)
    assert reading.unit == "vwc"
    assert reading.source == "vendor"
    assert reading.recorded_at == datetime.fromtimestamp(1_790_000_000, tz=timezone.utc)


def test_vendor_adapter_rejects_malformed_payload():
    with pytest.raises(SensorReadError):
        VendorStubSensorAdapter().translate(make_device(), {"measurement": {}})


@pytest.mark.parametrize("device_type", ["moisture_sensor", "light_sensor"])
def test_simulation_adapter_value_in_range(device_type):
    profile = PROFILES[device_type]
    adapter = SimulationSensorAdapter(rng=random.Random(1), clock=lambda: T0)
    device = make_device(device_type=device_type)

    for _ in range(200):
        reading = adapter.read(device)
        assert profile.low <= reading.value <= profile.high
        assert reading.unit == profile.unit
        assert reading.source == "simulation"


def test_mqtt_adapter_translates_payload(monkeypatch):
    def no_sockets(*args, **kwargs):
        raise AssertionError("the MQTT adapter must not open a socket")

    monkeypatch.setattr(socket, "socket", no_sockets)
    device = make_device(protocol="mqtt")

    reading = MqttSensorAdapter(clock=lambda: T0).translate(device, {"value": 0.41, "unit": "vwc"})

    assert reading.device_id == device.id
    assert reading.value == 0.41
    assert reading.unit == "vwc"
    assert reading.source == "mqtt"
    assert reading.recorded_at == T0


def test_mqtt_adapter_rejects_bad_payload():
    with pytest.raises(SensorReadError):
        MqttSensorAdapter().translate(make_device(protocol="mqtt"), {"value": "warm", "unit": "vwc"})


def test_selector_picks_adapter_by_protocol_and_vendor_flag():
    assert isinstance(select_sensor_port(make_device()), SimulationSensorAdapter)
    assert isinstance(select_sensor_port(make_device(extra={"vendor_stub": True})), VendorStubSensorAdapter)
    assert isinstance(select_sensor_port(make_device(protocol="mqtt")), MqttSensorAdapter)
    with pytest.raises(SensorReadError):
        select_sensor_port(make_device(protocol="carrier-pigeon"))


def test_simulation_actuator_records_intent():
    actuator = SimulationActuatorAdapter()
    device_id = uuid4()

    actuator.apply(device_id, "on", {"duration_s": 5})

    assert len(actuator.applied) == 1
    assert actuator.applied[0].device_id == device_id
    assert actuator.applied[0].command == "on"


def test_sampling_interval_below_minimum_is_rejected():
    assert validate_sampling_interval(5) == 5
    with pytest.raises(InvalidSamplingError):
        validate_sampling_interval(4)


# ---------- ingest + sampler (fake clock, real in-memory DB) ----------

def test_ingest_take_reading_persists_and_returns_dto(devices, readings):
    device = devices.save_device(make_device(extra={"vendor_stub": True}))
    ingest = ReadingIngest(devices, readings, select_sensor_port)

    dto = ingest.take_reading(device.id)

    assert dto.source == "vendor"  # same logical read, different source than simulation
    assert len(readings.list_for_device(device.id)) == 1


def test_ingest_record_persists_translated_mqtt_reading(devices, readings):
    device = devices.save_device(make_device(protocol="mqtt"))
    ingest = ReadingIngest(devices, readings, select_sensor_port)
    reading = MqttSensorAdapter(clock=lambda: T0).translate(device, {"value": 0.41, "unit": "vwc"})

    dto = ingest.record(device.id, reading)

    assert dto.source == "mqtt"
    assert dto.value == 0.41
    assert len(readings.list_for_device(device.id)) == 1


def test_ingest_unknown_device_raises_not_found(devices, readings):
    ingest = ReadingIngest(devices, readings, select_sensor_port)
    with pytest.raises(DeviceNotFoundError):
        ingest.take_reading(uuid4())


def test_sampler_respects_interval_and_tracking(devices, readings):
    sim = devices.save_device(make_device(interval=30))
    off = devices.save_device(make_device(interval=30, tracking=False))
    mqtt = devices.save_device(make_device(protocol="mqtt", interval=30))
    sampler = build_sampler(devices, readings)

    assert sampler.run_once(T0) == 1                            # no previous row counts as elapsed
    assert sampler.run_once(T0 + timedelta(seconds=10)) == 0    # inside the interval
    assert sampler.run_once(T0 + timedelta(seconds=30)) == 1    # interval elapsed

    stored = readings.list_for_device(sim.id, limit=10)
    assert len(stored) == 2
    assert stored[0].recorded_at == T0 + timedelta(seconds=30)  # stamped with the tick clock
    assert readings.list_for_device(off.id) == []               # tracking off: skipped
    assert readings.list_for_device(mqtt.id) == []              # mqtt: skipped


def test_sampler_resumes_after_tracking_is_turned_back_on(devices, readings):
    device = devices.save_device(make_device(interval=30, tracking=False))
    sampler = build_sampler(devices, readings)

    assert sampler.run_once(T0) == 0
    devices.update_sampling(device.id, 30, True)
    assert sampler.run_once(T0 + timedelta(seconds=1)) == 1


# ---------- API integration ----------

def _provision(client, family):
    res = client.post("/api/devices/provision", params={"family": family})
    assert res.status_code == 201
    return [d for d in res.json() if d["role"] == "sensor"]


def test_read_inserts_sensor_reading(client, session):
    sensor = _provision(client, "simulation")[0]

    first = client.post(f"/api/sensors/{sensor['id']}/read")
    second = client.post(f"/api/sensors/{sensor['id']}/read")

    assert first.status_code == 201 and second.status_code == 201
    body = first.json()
    assert set(body) == {"device_id", "value", "unit", "source", "recorded_at"}
    assert body["source"] == "simulation"

    count = session.execute(select(func.count()).select_from(ReadingRow)).scalar_one()
    assert count == 2

    history = client.get(f"/api/sensors/{sensor['id']}/readings", params={"limit": 10}).json()
    assert len(history) == 2


def test_read_errors_map_to_404_and_400(client):
    assert client.post(f"/api/sensors/{uuid4()}/read").status_code == 404
    edge_sensor = _provision(client, "edge")[0]
    res = client.post(f"/api/sensors/{edge_sensor['id']}/read")
    assert res.status_code == 400
    assert "MQTT" in res.json()["detail"]


def test_patch_sampling_persists_and_validates(client):
    sensor = _provision(client, "simulation")[0]
    url = f"/api/devices/{sensor['id']}/sampling"

    ok = client.patch(url, json={"sampling_interval_seconds": 10, "tracking_enabled": False})
    assert ok.status_code == 200
    assert ok.json()["sampling_interval_seconds"] == 10
    assert ok.json()["tracking_enabled"] is False

    stored = next(d for d in client.get("/api/devices").json() if d["id"] == sensor["id"])
    assert stored["sampling_interval_seconds"] == 10
    assert stored["tracking_enabled"] is False

    too_small = client.patch(url, json={"sampling_interval_seconds": 2, "tracking_enabled": True})
    assert too_small.status_code == 400

    missing = client.patch(
        f"/api/devices/{uuid4()}/sampling",
        json={"sampling_interval_seconds": 30, "tracking_enabled": True},
    )
    assert missing.status_code == 404