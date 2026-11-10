from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.domain.actuators.context import ActuatorContext
from src.domain.actuators.errors import PolicyViolationError
from src.domain.actuators.execution import ExecutionRecord
from src.domain.actuators.ports import ActuatorPort
from src.infrastructure.adapters.actuators.logging_decorator import LoggingActuatorDecorator
from src.infrastructure.adapters.actuators.max_runtime_decorator import MaxRunTimeActuatorDecorator
from src.infrastructure.adapters.actuators.simulation import SimulationActuatorAdapter
from src.infrastructure.persistence.base import Base, get_db
from src.infrastructure.persistence.models import ActuatorExecutionLogRow, ActuatorStateRow
from src.main import app

NOW = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)


# ---------- unit tests: fakes, no DB ----------


class SpyPort(ActuatorPort):
    def __init__(self):
        self.calls = []

    def apply(self, device_id, command, payload):
        self.calls.append((device_id, command, payload))


class FakeStates:
    def __init__(self, context):
        self._context = context

    def get(self, device_id):
        return self._context


class FakeLog:
    def __init__(self):
        self.rows: list[ExecutionRecord] = []

    def add(self, device_id, *, success, policy_applied, message):
        record = ExecutionRecord(
            id=uuid4(),
            device_id=device_id,
            success=success,
            policy_applied=list(policy_applied),
            message=message,
            created_at=NOW,
        )
        self.rows.append(record)
        return record


def running_for(minutes: int) -> FakeStates:
    return FakeStates(ActuatorContext(uuid4(), "running", updated_at=NOW - timedelta(minutes=minutes)))


def test_decorators_share_the_port():
    assert issubclass(LoggingActuatorDecorator, ActuatorPort)
    assert issubclass(MaxRunTimeActuatorDecorator, ActuatorPort)
    assert issubclass(SimulationActuatorAdapter, ActuatorPort)


def test_max_runtime_does_not_call_inner():
    spy = SpyPort()
    port = MaxRunTimeActuatorDecorator(spy, running_for(31), clock=lambda: NOW)
    with pytest.raises(PolicyViolationError) as err:
        port.apply(uuid4(), "stop_pump", {})
    assert err.value.policy == "maxRunTime"
    assert err.value.message == "Max run time exceeded"
    assert spy.calls == []


def test_max_runtime_blocks_at_exactly_30_minutes():
    spy = SpyPort()
    with pytest.raises(PolicyViolationError):
        MaxRunTimeActuatorDecorator(spy, running_for(30), clock=lambda: NOW).apply(uuid4(), "x", {})
    assert spy.calls == []


def test_max_runtime_allows_under_30_minutes():
    spy = SpyPort()
    MaxRunTimeActuatorDecorator(spy, running_for(29), clock=lambda: NOW).apply(uuid4(), "x", {})
    assert len(spy.calls) == 1


def test_max_runtime_ignores_old_state_that_is_not_running():
    spy = SpyPort()
    old_idle = FakeStates(ActuatorContext(uuid4(), "idle", updated_at=NOW - timedelta(hours=5)))
    MaxRunTimeActuatorDecorator(spy, old_idle, clock=lambda: NOW).apply(uuid4(), "x", {})
    assert len(spy.calls) == 1


def test_logging_records_success_for_any_command():
    spy, log = SpyPort(), FakeLog()
    LoggingActuatorDecorator(spy, log).apply(uuid4(), "totally_unknown_command", {})
    assert len(spy.calls) == 1
    row = log.rows[0]
    assert (row.success, row.policy_applied, row.message) == (True, ["logging"], None)


def test_failed_policy_writes_execution_row():
    spy, log = SpyPort(), FakeLog()
    stack = LoggingActuatorDecorator(
        MaxRunTimeActuatorDecorator(spy, running_for(45), clock=lambda: NOW), log
    )
    with pytest.raises(PolicyViolationError):
        stack.apply(uuid4(), "stop_pump", {})
    row = log.rows[0]
    assert row.success is False
    assert row.policy_applied == ["maxRunTime", "logging"]
    assert row.message == "Max run time exceeded"
    assert spy.calls == []


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


def log_count(session) -> int:
    session.expire_all()
    return session.execute(select(func.count()).select_from(ActuatorExecutionLogRow)).scalar_one()


def test_success_attempt_inserts_row(client, session):
    pump = provision_pump(client)
    resp = client.post(f"/api/actuators/{pump['id']}/apply", json={"command": "whatever"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert (body["success"], body["policy_applied"], body["message"]) == (True, ["logging"], None)
    assert log_count(session) == 1


def test_blocked_attempt_is_persisted_and_listed(client, session):
    pump = provision_pump(client)
    assert client.post(f"/api/devices/{pump['id']}/transition", json={"target": "running"}).status_code == 200

    row = session.get(ActuatorStateRow, UUID(pump["id"]))
    row.updated_at = datetime.now(timezone.utc) - timedelta(minutes=31)
    session.commit()

    resp = client.post(f"/api/actuators/{pump['id']}/apply", json={"command": "stop_pump"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["policy_applied"] == ["maxRunTime", "logging"]
    assert body["message"] == "Max run time exceeded"
    assert log_count(session) == 1

    listed = client.get("/api/actuators/executions?limit=20").json()
    assert listed[0]["success"] is False
    assert listed[0]["device_id"] == pump["id"]
    assert listed[0]["policy_applied"] == ["maxRunTime", "logging"]


def test_recently_started_actuator_is_not_blocked(client):
    pump = provision_pump(client)
    client.post(f"/api/devices/{pump['id']}/transition", json={"target": "running"})
    assert client.post(f"/api/actuators/{pump['id']}/apply", json={"command": "stop_pump"}).json()["success"] is True


def test_apply_on_missing_actuator_is_404(client):
    assert client.post(f"/api/actuators/{uuid4()}/apply", json={"command": "x"}).status_code == 404


def test_executions_empty_by_default(client):
    assert client.get("/api/actuators/executions").json() == []