class UnknownStrategyError(ValueError):
    """Strategy key is not registered (API maps this to 400)."""


class LocationNotFoundError(LookupError):
    """Location id does not exist (API maps this to 404)."""