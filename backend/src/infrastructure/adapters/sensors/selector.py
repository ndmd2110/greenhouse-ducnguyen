from src.domain.devices.entity import Device
from src.domain.sensors.errors import SensorReadError
from src.domain.sensors.ports import SensorPort
from src.domain.sensors.protocols import PROTOCOL_MQTT, PROTOCOL_SIMULATION, resolve_protocol, uses_vendor_stub
from src.infrastructure.adapters.sensors.mqtt import MqttSensorAdapter
from src.infrastructure.adapters.sensors.simulation import SimulationSensorAdapter
from src.infrastructure.adapters.sensors.vendor_stub import VendorStubSensorAdapter


def select_sensor_port(device: Device) -> SensorPort:
    protocol = resolve_protocol(device)
    if protocol == PROTOCOL_SIMULATION:
        return VendorStubSensorAdapter() if uses_vendor_stub(device) else SimulationSensorAdapter()
    if protocol == PROTOCOL_MQTT:
        return MqttSensorAdapter()
    raise SensorReadError(f"Unsupported protocol '{protocol}'. Expected '{PROTOCOL_SIMULATION}' or '{PROTOCOL_MQTT}'.")