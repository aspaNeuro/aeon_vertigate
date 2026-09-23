# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Generate firmware/vertigate/_version.py from device.yml.

The firmware reports WhoAmI and the firmware and hardware versions in its core registers. This script copies them out of device.yml so the two cannot drift. Run it after changing device.yml and commit the result:

    uv run tools/firmware_version.py

CI runs the same command and fails if the committed file is out of date.
"""

import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEVICE_YML = ROOT / "device.yml"
OUTPUT = ROOT / "firmware" / "vertigate" / "_version.py"

# Version of the Harp device specification the firmware follows. Bonsai shows
# it as CoreVersion. The draft-02 schema of device.yml has no field for it.
HARP_VERSION = (1, 13)

TEMPLATE = '''"""Device identity. Generated from device.yml by tools/firmware_version.py. Do not edit."""

WHO_AM_I = {who_am_i}
FW_VERSION = ({fw[0]}, {fw[1]})
HW_VERSION = ({hw[0]}, {hw[1]})
HARP_VERSION = ({harp[0]}, {harp[1]})
'''


def parse_version(value):
    """Return (major, minor) from a "major.minor" string or number."""
    parts = str(value).split(".")
    if len(parts) != 2:
        raise ValueError(f"expected major.minor, got {value!r}")
    return int(parts[0]), int(parts[1])


def main():
    metadata = yaml.safe_load(DEVICE_YML.read_text(encoding="utf-8"))
    targets = metadata["hardwareTargets"]
    if isinstance(targets, list):
        if len(targets) != 1:
            sys.exit("device.yml lists several hardware targets; the firmware reports one")
        targets = targets[0]
    content = TEMPLATE.format(
        who_am_i=int(metadata["whoAmI"]),
        fw=parse_version(metadata["firmwareVersion"]),
        hw=parse_version(targets),
        harp=HARP_VERSION,
    )
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
