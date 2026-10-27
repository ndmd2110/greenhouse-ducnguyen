from src.infrastructure.persistence.base import Base, engine, SessionLocal
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository
from src.infrastructure.adapters.sensors.selector import select_sensor_port
from src.domain.devices.entity import Device

Base.metadata.create_all(bind=engine)
with SessionLocal() as s:
       devices, readings = DeviceRepository(s), ReadingRepository(s)
       d = devices.save_device(Device(id=None, device_type="moisture_sensor", role="sensor",
               device_family="simulation", display_name="scratch",
               default_config={"protocol": "simulation", "sampling_interval_seconds": 60}))
       print("interval:", d.sampling_interval_seconds, "tracking:", d.tracking_enabled)
       readings.insert(select_sensor_port(d).read(d))
       print(readings.list_for_device(d.id))
       print("latest:", readings.latest_recorded_at(d.id))