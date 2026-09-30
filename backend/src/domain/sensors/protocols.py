from src.domain.devices.entity import Device

PROTOCOL_SIMULATION = "simulation"
PROTOCOL_MQTT = "mqtt"
VENDOR_STUB_FLAG = "vendor_stub"


def resolve_protocol(device: Device) -> str:
    protocol = (device.default_config or {}).get("protocol")
    return protocol if protocol else PROTOCOL_SIMULATION  # missing means simulation


def uses_vendor_stub(device: Device) -> bool:
    return bool((device.default_config or {}).get(VENDOR_STUB_FLAG))