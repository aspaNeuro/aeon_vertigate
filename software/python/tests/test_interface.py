"""Check the generated Python interface against device.yml.

The freshness gate in CI proves the committed interface matches what the
generator emits. It does not prove the result imports, or that it describes the
device the specification describes. These tests do that.

They need no hardware. The hardware checks are in `aeon.vertigate.hwtest`, run
as `uv run vertigate-test --port COMx`.
"""

from pathlib import Path

import pytest
import yaml
from harp.device import core

from swc.aeon.device import vertigate

# tests/ -> software/python/ -> the repository root.
METADATA = Path(__file__).resolve().parents[3] / "device.yml"


@pytest.fixture(scope="module")
def schema():
    return yaml.safe_load(METADATA.read_text(encoding="utf-8"))


def test_device_identity_matches_the_metadata(schema):
    assert vertigate.DEVICE_NAME == schema["device"]
    assert vertigate.WHO_AM_I == schema["whoAmI"]


def test_register_map_covers_the_core_and_application_registers():
    # Application registers start at address 32, so the map is only complete if
    # the core registers were merged into it as well.
    assert vertigate.REGISTER_MAP
    assert all(address in vertigate.REGISTER_MAP for address in core.REGISTER_MAP)
    assert any(address >= 32 for address in vertigate.REGISTER_MAP)


def test_every_declared_register_is_in_the_map(schema):
    for name, declared in schema["registers"].items():
        address = declared["address"]
        assert address in vertigate.REGISTER_MAP, f"{name} at {address} is missing"
        assert vertigate.REGISTER_MAP[address].__name__ == name


def test_the_hardware_test_entry_point_imports():
    # The entry point is published in pyproject.toml, so a broken import here is
    # a broken console script for anyone who installs the package.
    from swc.aeon.device.vertigate import hwtest

    assert callable(hwtest.main)
