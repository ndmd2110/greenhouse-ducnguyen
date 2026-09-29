from typing import Optional

from src.domain.devices.entity import Device
from src.domain.devices.family_factory import DeviceFamilyFactory
from src.infrastructure.persistence.device_repository import DeviceRepository


class DeviceFamilyService:
    def __init__(self, repository: DeviceRepository):
        self.repository = repository
        self._factories: dict[str, DeviceFamilyFactory] = {}

    def register_factory(self, factory: DeviceFamilyFactory) -> None:
        self._factories[factory.family_key] = factory

    def provision_family(self, family: str) -> list[Device]:
        factory = self._factories.get(family.lower())
        if factory is None:
            raise ValueError(f"Unknown device family: '{family}'")
        return self.repository.save_devices(factory.create_device_set())

    def list_devices(
        self, *, family: Optional[str] = None, role: Optional[str] = None
    ) -> list[Device]:
        return self.repository.list_devices(device_family=family, role=role)
