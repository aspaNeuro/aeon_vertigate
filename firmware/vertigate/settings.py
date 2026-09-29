"""Non-volatile settings for the VertiGate device.

`device.yml` marks Speed, Torque and CalibrationOffset as `volatile: false`,
which means their values should survive a power cycle. The Harp specification
does this through `R_RESET_DEV` (address 11): write `SAVE` to store the
non-volatile registers, `RST_EE` to reboot from the stored values, and
`RST_DEF` to erase them and go back to the defaults in `device.yml`.

microharp does not implement any of that. Its handler reboots on any non-zero
write and stores nothing. This module adds the storage, and `register.py` adds
the register handlers that use it.

Values are kept in one small JSON file on the MicroPython file system. It is
written only on a `SAVE` command, not on every register write, so the flash is
not worn out by normal use.
"""

import json
import os

FILE = "settings.json"


def load():
    """Return the saved values as {address: value}.

    Returns an empty dict when nothing is stored, or when the file cannot be
    read. A damaged file must not stop the device from starting, so the
    defaults are used instead.
    """
    try:
        with open(FILE) as f:
            saved = json.load(f)
        return {int(address): value for address, value in saved.items()}
    except Exception:
        return {}


def save(values):
    """Write {address: value} to storage. Raises if the write fails."""
    with open(FILE, "w") as f:
        json.dump({str(address): value for address, value in values.items()}, f)


def clear():
    """Remove the stored values, so the next boot uses the defaults."""
    try:
        os.remove(FILE)
    except Exception:
        pass  # Nothing stored, which is the state the caller asked for.


def exists():
    """Return True when values are stored."""
    try:
        os.stat(FILE)
        return True
    except Exception:
        return False
