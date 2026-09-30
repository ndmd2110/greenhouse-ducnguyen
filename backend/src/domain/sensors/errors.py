class DeviceNotFoundError(LookupError):
    """Device id does not exist (API maps this to 404)."""


class SensorReadError(ValueError):
    """Adapter cannot produce or translate a reading (API maps this to 400)."""


class InvalidSamplingError(ValueError):
    """Sampling settings are invalid, e.g. interval below the minimum (API maps this to 400)."""