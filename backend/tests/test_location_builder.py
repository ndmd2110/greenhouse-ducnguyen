import pytest

from src.domain.locations.config_builder import LocationConfigBuilder
from src.domain.locations.errors import ConfigurationError


def test_valid_location_builds():
    config = (
        LocationConfigBuilder()
        .with_location_name("North Wing")
        .add_zone("  Zone A  ", 0.2, 0.7)
        .add_zone("Zone B", 0.3, 0.8)
        .build()
    )

    assert config.location.name == "North Wing"
    assert len(config.location.zones) == 2
    assert config.location.zones[0].name == "Zone A"


def test_location_requires_name():
    with pytest.raises(ConfigurationError, match="Location name"):
        LocationConfigBuilder().add_zone("Zone A", 0.2, 0.8).build()


def test_location_requires_at_least_one_zone():
    with pytest.raises(ConfigurationError, match="at least one zone"):
        LocationConfigBuilder().set_name("North Wing").build()


def test_invalid_threshold_order_is_rejected():
    with pytest.raises(ConfigurationError, match="strictly less than"):
        LocationConfigBuilder().set_name("North Wing").add_zone("Zone A", 0.8, 0.2).build()
