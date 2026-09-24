"""Hardware test for the VertiGate registers.

The test drives the board with the Harp client from harp-serial and the
interface generated from device.yml. Every address, command bit, state name and
default value comes from the specification, so the test cannot drift away from
it. It needs the harp extra:

    uv sync --all-extras

Run from the repository root, with the Harp port of the board:

    uv run vertigate-test --port COM4

What it does, in order:
    1. Reads the registers Bonsai reads on connect (WhoAmI, versions, name) and
       prints them the way the Bonsai console does. WhoAmI and the device name
       must match device.yml. Then reads GateState.
    2. Sends a bad Control write (EnableMotor + DisableMotor) and expects an
       error reply.
    3. Raises the gate, sends Stop after 0.5 s, and expects the gate to stop.
    4. Sends Calibrate and waits for GateState to go Calibrating, then Down.
    5. Checks every register that device.yml marks non-volatile. A written value
       and a written device name must survive a reboot, and RestoreDefault must
       bring the values in device.yml back.

Every event the device sends is printed as it arrives.

Section 5 reboots the board several times, so it takes about a minute. Skip it
with --no-reboot.

Stop early with Ctrl-C. The script leaves the device in ACTIVE mode.
"""

import argparse
import sys
import time
from pathlib import Path

from harp.device.client import DeviceError, TransportError
from harp.device.core import (
    AssemblyVersion,
    CoreVersionHigh,
    CoreVersionLow,
    DeviceName,
    FirmwareVersionHigh,
    FirmwareVersionLow,
    HardwareVersionHigh,
    HardwareVersionLow,
    OperationControl,
    OperationControlPayload,
    OperationMode,
    ResetDevice,
    ResetFlags,
    SerialNumber,
    WhoAmI,
)
from harp.device.schema import parse_device_schema
from harp.protocol import HarpParseError
from harp.serial import open_device

from aeon.vertigate import device as vertigate
from aeon.vertigate.device import (
    Control,
    ControlFlags,
    GateState,
    GateStatus,
    Speed,
    TargetPosition,
    Torque,
)

# device.yml, read for what the generated interface leaves out: which registers
# are non-volatile, and their default, minimum and maximum.
METADATA = Path(__file__).resolve().parents[3] / "device.yml"

REBOOT_SECONDS = 9
CAL_TIMEOUT_S = 12.0

# Failures the test reports as a FAIL instead of stopping on. DeviceError is
# only raised if the device is opened with raise_on_error, which this test does
# not, but catching it keeps the helpers safe either way.
DEVICE_FAILURES = (DeviceError, TransportError, TimeoutError, OSError)


class _ErrorReply:
    """Stand-in for an error reply the client cannot decode.

    The firmware answers a rejected write with the error flag set and an empty
    payload. Device.write decodes every reply against its register, even one
    that carries the error flag, so decoding an error reply raises instead of
    returning it. Until either side changes, a parse failure on a reply means
    the device rejected the write.
    """

    has_error = True


ERROR_REPLY = _ErrorReply()


def status_name(value):
    """Name of a GateState value, from the interface."""
    try:
        return GateStatus(value).name.title()
    except ValueError:
        return "?"


def check(ok, text):
    print(("  PASS  " if ok else "  FAIL  ") + text)
    return ok


def on_gate_state(msg):
    print(f"  event  GateState = {int(msg.payload)} ({status_name(msg.payload)})")


def on_other_event(msg):
    if msg.address != GateState.address:
        print(f"  event  address {msg.address} payload {msg.payload_bytes.hex()}")


def connect(port):
    """Open the device, start printing events and put it in ACTIVE mode.

    Opened without the device module, so a wrong WhoAmI is reported as a failed
    check instead of raising. Passing vertigate to open_device would make the
    client check the identity itself.
    """
    dev = open_device(port=port, raise_on_error=False)
    dev.subscribe(GateState, on_gate_state)
    dev.subscribe_all(on_other_event)
    write(dev, OperationControl, OperationControlPayload(operation_mode=OperationMode.ACTIVE))
    return dev


def read(dev, register):
    """Decoded payload of a register, or None if the device did not answer."""
    try:
        reply = dev.read(register)
    except HarpParseError:
        return None  # an error reply, see _ErrorReply
    except DEVICE_FAILURES:
        return None
    return None if reply.has_error else reply.payload


def write(dev, register, value):
    """Reply to a write, or None if the device did not answer. An error reply is
    returned, not raised, so a check can expect one."""
    try:
        return dev.write(register, value)
    except HarpParseError:
        return ERROR_REPLY
    except DEVICE_FAILURES:
        return None


def accepted(reply):
    return reply is not None and not reply.has_error


def rejected(reply):
    return reply is not None and reply.has_error


def reopen(dev, port):
    """Close the port, wait for the device to boot, and open it again."""
    try:
        dev.close()
    except DEVICE_FAILURES:
        pass
    time.sleep(REBOOT_SECONDS)
    return connect(port)


def reboot(dev, port, command):
    """Send a reset command and reconnect. The device replies and then drops the
    USB port, so the port has to be closed and opened again."""
    write(dev, ResetDevice, command)
    return reopen(dev, port)


def wait_status(dev, wanted, timeout):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if read(dev, GateState) == wanted:
            return True
        time.sleep(0.1)
    return False


def print_identity(dev):
    """Read what Bonsai reads when the Device node connects, and print it the way
    the Bonsai console does. Returns WhoAmI and the device name."""
    who = read(dev, WhoAmI)
    hw = (read(dev, HardwareVersionHigh), read(dev, HardwareVersionLow))
    fw = (read(dev, FirmwareVersionHigh), read(dev, FirmwareVersionLow))
    core = (read(dev, CoreVersionHigh), read(dev, CoreVersionLow))
    asm = read(dev, AssemblyVersion)
    name = read(dev, DeviceName)
    serial_no = read(dev, SerialNumber)
    print(f"  Bonsai console line:  Serial Harp device. WhoAmI: {who} Hw: {hw[0]}.{hw[1]} "
          f"Fw: {fw[0]}.{fw[1]} DeviceName: {name}")
    print(f"  Device Setup dialog:  DeviceName={name} WhoAmI={who} HardwareVersion={hw[0]}.{hw[1]}")
    print(f"                        FirmwareVersion={fw[0]}.{fw[1]} CoreVersion={core[0]}.{core[1]} "
          f"AssemblyVersion={asm} SerialNumber={serial_no}")
    return who, name


def non_volatile(schema):
    """Registers device.yml marks non-volatile, as name -> (register class,
    default value, test value). The test value is one step away from the default
    and inside the declared range."""
    out = {}
    for name, model in schema.registers.items():
        if model.volatile is not False or model.defaultValue is None:
            continue
        default = int(model.defaultValue.root)
        low = int(model.minValue.root) if model.minValue is not None else 0
        high = int(model.maxValue.root) if model.maxValue is not None else 255
        probe = next(v for v in (default - 1, default + 1) if low <= v <= high)
        out[name] = (vertigate.REGISTER_MAP[model.address], default, probe)
    return out


def check_settings(dev, port, schema, results):
    """Check that a written value survives a reboot.

    The firmware stores a non-volatile register when it is written. ResetDevice
    reports how the device booted and can put the defaults back.
    """
    registers = non_volatile(schema)
    print(f"   device.yml marks {len(registers)} registers non-volatile: {', '.join(registers)}")

    flags = read(dev, ResetDevice)
    results.append(check(flags is not None, "ResetDevice is readable"))
    boot_bits = (ResetFlags.BOOT_FROM_DEFAULT, ResetFlags.BOOT_FROM_EEPROM)
    results.append(check(flags in boot_bits,
                         f"one boot bit set, read 0x{flags:02X}" if flags is not None else "no boot bits"))
    results.append(check(rejected(write(dev, ResetDevice, ResetFlags.BOOT_FROM_EEPROM)),
                         "writing a boot bit gives an error reply"))

    dev = reboot(dev, port, ResetFlags.RESTORE_DEFAULT)
    results.append(check(read(dev, ResetDevice) == ResetFlags.BOOT_FROM_DEFAULT,
                         "RestoreDefault boots from the defaults"))
    for name, (register, default, _) in registers.items():
        value = read(dev, register)
        results.append(check(value == default,
                             f"{name} holds the default from device.yml, expected {default}, read {value}"))

    for name, (register, _, probe) in registers.items():
        results.append(check(accepted(write(dev, register, probe)), f"{name} accepted the value {probe}"))
    dev = reboot(dev, port, ResetFlags.RESTORE_EEPROM)
    results.append(check(read(dev, ResetDevice) == ResetFlags.BOOT_FROM_EEPROM,
                         "the device boots from storage"))
    for name, (register, _, probe) in registers.items():
        value = read(dev, register)
        results.append(check(value == probe, f"{name} kept {probe} over the reboot, read {value}"))

    dev = reboot(dev, port, ResetFlags.RESTORE_DEFAULT)
    for name, (register, default, _) in registers.items():
        value = read(dev, register)
        results.append(check(value == default, f"RestoreDefault put {name} back to {default}, read {value}"))

    # The device name is non-volatile too, and the specification says a write to
    # it must be saved and must reset the device. So the write is its own
    # reboot: no ResetDevice command follows it.
    write(dev, DeviceName, "GateTestName")
    dev = reopen(dev, port)
    name = read(dev, DeviceName)
    results.append(check(name == "GateTestName", f"the written device name survived the reboot, read {name!r}"))

    dev = reboot(dev, port, ResetFlags.RESTORE_DEFAULT)
    name = read(dev, DeviceName)
    results.append(check(name == vertigate.DEVICE_NAME,
                         f"RestoreDefault put the name back to {vertigate.DEVICE_NAME!r}, read {name!r}"))
    return dev


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", default="COM21" if sys.platform == "win32" else "/dev/ttyACM0")
    p.add_argument("--metadata", type=Path, default=METADATA, help="device.yml to test against")
    p.add_argument("--no-reboot", action="store_true",
                   help="skip the non-volatile settings checks, which reboot the board")
    args = p.parse_args()

    if not args.metadata.is_file():
        print(f"device.yml not found at {args.metadata}. Pass --metadata.", file=sys.stderr)
        return 2
    schema = parse_device_schema(args.metadata.read_text(encoding="utf-8"))

    results = []
    dev = connect(args.port)
    try:
        print("1. Identity and state, as Bonsai sees it on connect")
        who, name = print_identity(dev)
        results.append(check(who == vertigate.WHO_AM_I,
                             f"WhoAmI = {who}, device.yml says {vertigate.WHO_AM_I}"))
        results.append(check(name == vertigate.DEVICE_NAME,
                             f"DeviceName = {name!r}, device.yml says {vertigate.DEVICE_NAME!r}"))
        state = read(dev, GateState)
        results.append(check(state is not None, f"GateState = {state} ({status_name(state)})"))
        if state == GateStatus.CALIBRATING:
            print("  gate is still homing from boot, waiting")
            results.append(check(wait_status(dev, GateStatus.DOWN, CAL_TIMEOUT_S), "boot homing reached Down"))
            state = read(dev, GateState)
        servo = state != GateStatus.ERROR
        if not servo:
            print("  no servo answering: expecting Error instead of Idle and Down")
        after_stop = GateStatus.IDLE if servo else GateStatus.ERROR
        after_home = GateStatus.DOWN if servo else GateStatus.ERROR

        print("2. Conflicting bits are rejected")
        reply = write(dev, Control, ControlFlags.ENABLE_MOTOR | ControlFlags.DISABLE_MOTOR)
        results.append(check(rejected(reply), "EnableMotor + DisableMotor gives an error reply"))

        print("3. Stop halts a movement")
        # Drive towards the far end, so there is always a movement to stop. A
        # gate that is already at the target never moves, and Stop would then
        # leave it reporting Up or Down instead of Idle.
        target = 0 if state == GateStatus.UP else 255
        print(f"  gate is {status_name(state)}, moving to {target}")
        write(dev, TargetPosition, target)
        time.sleep(0.5)
        results.append(check(accepted(write(dev, Control, ControlFlags.STOP)), "Stop write accepted"))
        time.sleep(0.3)
        state = read(dev, GateState)
        results.append(check(state == after_stop,
                             f"GateState after Stop = {state} ({status_name(state)}), "
                             f"expected {status_name(after_stop)}"))

        print("4. Calibrate homes the gate")
        results.append(check(accepted(write(dev, Control, ControlFlags.CALIBRATE)), "Calibrate write accepted"))
        time.sleep(0.2)
        state = read(dev, GateState)
        # Without a servo the setup fails at once, so Calibrating is too short to see.
        during = (GateStatus.CALIBRATING,) if servo else (GateStatus.CALIBRATING, GateStatus.ERROR)
        results.append(check(state in during,
                             f"GateState during homing = {state} ({status_name(state)}), "
                             f"expected {' or '.join(status_name(d) for d in during)}"))
        results.append(check(wait_status(dev, after_home, CAL_TIMEOUT_S),
                             f"homing reached {status_name(after_home)} within the timeout"))

        # Homing puts the safe default speed and torque on the servo. It must put
        # the configured values back, or a calibration silently resets them.
        if servo:
            write(dev, Speed, 200)
            write(dev, Torque, 40)
            write(dev, Control, ControlFlags.CALIBRATE)
            wait_status(dev, after_home, CAL_TIMEOUT_S)
            time.sleep(0.3)
            kept = (read(dev, Speed), read(dev, Torque))
            results.append(check(kept == (200, 40),
                                 f"Calibrate kept Speed and Torque, read {kept}, expected (200, 40)"))
        else:
            print("  no servo: skipping the Calibrate settings check")

        if args.no_reboot:
            print("5. Non-volatile settings: skipped (--no-reboot)")
        else:
            print("5. Non-volatile settings survive a reboot")
            print(f"   this reboots the board four times, about {4 * REBOOT_SECONDS} seconds")
            dev = check_settings(dev, args.port, schema, results)
    finally:
        dev.close()

    print()
    print(f"{sum(results)} of {len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
