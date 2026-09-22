"""Hardware test for the VertiGate Control register.

Run from the repository root, with the Harp port of the board:

    uv run vertigate-test --port COM4

What it does, in order:
    1. Reads the registers Bonsai reads on connect (WhoAmI, versions, name)
       and prints them the way the Bonsai console does. Then reads Status.
    2. Sends a bad Control write (Enable + Disable) and expects an error reply.
    3. Raises the gate, sends Stop after 0.5 s, and expects the gate to stop.
    4. Sends Calibrate and waits for GateState to go Calibrating, then Down.
    5. Checks the non-volatile settings. A written Speed, Torque or device
       name must survive a reboot, and RST_DEF must bring the defaults back.

Every GateState event seen on the way is printed.

Section 5 reboots the board several times, so it takes about a minute. Skip it
with --no-reboot.

Stop early with Ctrl-C. The script leaves the device in ACTIVE mode.
"""

import argparse
import struct
import sys
import time

import serial

MSG_READ, MSG_WRITE, MSG_EVENT = 1, 2, 3
MSG_ERROR = 0x08
PT_U8, PT_U16 = 1, 2
PT_TIMESTAMP = 0x10

R_WHO_AM_I = 0
R_HW_VERSION_H, R_HW_VERSION_L = 1, 2
R_ASSEMBLY_VERSION = 3
R_CORE_VERSION_H, R_CORE_VERSION_L = 4, 5
R_FW_VERSION_H, R_FW_VERSION_L = 6, 7
R_RESET_DEV = 11
R_OP_CTRL = 10
R_DEVICE_NAME = 12
R_SERIAL_NUMBER = 13
OP_ACTIVE = 0x01

ADDR_CONTROL = 32
ADDR_TARGET_POSITION = 33
ADDR_GATE_STATE = 34
ADDR_SPEED = 35
ADDR_TORQUE = 36
ADDR_CALIBRATION_OFFSET = 37

# R_RESET_DEV bits.
RST_DEF = 0x01
RST_EE = 0x02
SAVE = 0x04
BOOT_DEF = 0x40
BOOT_EE = 0x80

# device.yml defaultValue for the registers marked volatile: false.
SPEED_DEFAULT = 255
TORQUE_DEFAULT = 35

REBOOT_SECONDS = 9
DEVICE_NAME_LEN = 25

CTRL_ENABLE_MOTOR = 0x01
CTRL_DISABLE_MOTOR = 0x02
CTRL_STOP = 0x04
CTRL_CALIBRATE = 0x08

STATUS_NAMES = {0: "Idle", 1: "Up", 2: "Down", 3: "Moving", 4: "Calibrating", 0xFF: "Error"}

CAL_TIMEOUT_S = 12.0


def encode(msg_type, address, payload_type, payload=b""):
    body = bytes([address, 255, payload_type]) + payload
    frame = bytes([msg_type, len(body) + 1]) + body
    return frame + bytes([sum(frame) & 0xFF])


def read_frame(ser, deadline):
    """Return one decoded frame, or None on timeout."""
    while time.perf_counter() < deadline:
        head = ser.read(2)
        if len(head) < 2:
            continue
        msg_type, length = head
        rest = ser.read(length)
        if len(rest) < length:
            return None
        frame = head + rest
        if sum(frame[:-1]) & 0xFF != frame[-1]:
            print("  ! bad checksum, frame dropped")
            continue
        address, port, ptype = rest[0], rest[1], rest[2]
        offset = 3
        if ptype & PT_TIMESTAMP:
            offset += 6
        payload = rest[offset:-1]
        return {
            "type": msg_type & ~MSG_ERROR,
            "error": bool(msg_type & MSG_ERROR),
            "address": address,
            "payload": payload,
        }
    return None


def request(ser, msg_type, address, payload_type, payload=b"", timeout=1.0):
    """Send one request and return the matching reply. Events seen on the
    way are printed and skipped."""
    ser.write(encode(msg_type, address, payload_type, payload))
    deadline = time.perf_counter() + timeout
    while True:
        f = read_frame(ser, deadline)
        if f is None:
            return None
        if f["type"] == MSG_EVENT:
            print_event(f)
            continue
        if f["address"] == address:
            return f


def print_event(f):
    if f["address"] == ADDR_GATE_STATE and f["payload"]:
        v = f["payload"][0]
        print(f"  event  Status = {v} ({STATUS_NAMES.get(v, '?')})")
    else:
        print(f"  event  address {f['address']} payload {f['payload'].hex()}")


def drain_events(ser, seconds):
    deadline = time.perf_counter() + seconds
    while True:
        f = read_frame(ser, deadline)
        if f is None:
            return
        if f["type"] == MSG_EVENT:
            print_event(f)


def read_u8(ser, address):
    f = request(ser, MSG_READ, address, PT_U8)
    return None if f is None or not f["payload"] else f["payload"][0]


def read_u16(ser, address):
    f = request(ser, MSG_READ, address, PT_U16)
    return None if f is None or len(f["payload"]) < 2 else struct.unpack("<H", f["payload"][:2])[0]


def read_str(ser, address):
    f = request(ser, MSG_READ, address, PT_U8)
    return None if f is None else f["payload"].split(b"\x00", 1)[0].decode("ascii", "replace")


def print_identity(ser):
    """Read what Bonsai reads when the Device node connects, and print it
    the way the Bonsai console does. Returns the WhoAmI value."""
    who = read_u16(ser, R_WHO_AM_I)
    hw = (read_u8(ser, R_HW_VERSION_H), read_u8(ser, R_HW_VERSION_L))
    fw = (read_u8(ser, R_FW_VERSION_H), read_u8(ser, R_FW_VERSION_L))
    core = (read_u8(ser, R_CORE_VERSION_H), read_u8(ser, R_CORE_VERSION_L))
    asm = read_u8(ser, R_ASSEMBLY_VERSION)
    name = read_str(ser, R_DEVICE_NAME)
    serial_no = read_u16(ser, R_SERIAL_NUMBER)
    print(f"  Bonsai console line:  Serial Harp device. WhoAmI: {who} Hw: {hw[0]}.{hw[1]} Fw: {fw[0]}.{fw[1]} DeviceName: {name}")
    print(f"  Device Setup dialog:  DeviceName={name} WhoAmI={who} HardwareVersion={hw[0]}.{hw[1]}")
    print(f"                        FirmwareVersion={fw[0]}.{fw[1]} CoreVersion={core[0]}.{core[1]} AssemblyVersion={asm} SerialNumber={serial_no}")
    return who


def write_u8(ser, address, value):
    return request(ser, MSG_WRITE, address, PT_U8, bytes([value]))


def wait_status(ser, wanted, timeout):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        v = read_u8(ser, ADDR_GATE_STATE)
        if v == wanted:
            return True
        time.sleep(0.1)
    return False


def check(ok, text):
    print(("  PASS  " if ok else "  FAIL  ") + text)
    return ok


def open_port(port, settle=0.2):
    ser = serial.Serial(port, baudrate=1_000_000, timeout=0.005)
    ser.dtr = True
    time.sleep(settle)
    ser.reset_input_buffer()
    return ser


def reboot(ser, port, command):
    """Send a reset command, wait for the device to come back, and reopen.

    The device drops the USB port while it reboots, so the port has to be
    closed and opened again.
    """
    # Do not wait for the reply. The device answers and then reboots, so the
    # port can disappear while the reply is still being read.
    try:
        ser.write(encode(MSG_WRITE, R_RESET_DEV, PT_U8, bytes([command])))
        time.sleep(0.3)
    except serial.SerialException:
        pass
    ser.close()
    time.sleep(REBOOT_SECONDS)
    ser = open_port(port, settle=1.0)
    write_u8(ser, R_OP_CTRL, OP_ACTIVE)
    return ser


def write_name(ser, name):
    padded = name.encode()[:DEVICE_NAME_LEN - 1]
    padded += bytes(DEVICE_NAME_LEN - len(padded))
    return request(ser, MSG_WRITE, R_DEVICE_NAME, PT_U8, padded)


def check_settings(ser, port, results):
    """Check that a written value survives a reboot.

    device.yml marks Speed, Torque and CalibrationOffset `volatile: false`,
    so the firmware stores them on write. R_RESET_DEV reports how the device
    booted and can put the defaults back.
    """
    flags = read_u8(ser, R_RESET_DEV)
    results.append(check(flags is not None, "ResetDevice is readable"))
    results.append(check(flags in (BOOT_DEF, BOOT_EE), f"one boot bit set, read 0x{flags:02X}" if flags is not None else "no boot bits"))

    reply = request(ser, MSG_WRITE, R_RESET_DEV, PT_U8, bytes([BOOT_EE]))
    results.append(check(reply is not None and reply["error"], "writing a boot bit gives an error reply"))

    ser = reboot(ser, port, RST_DEF)
    results.append(check(read_u8(ser, R_RESET_DEV) == BOOT_DEF, "RST_DEF boots from the defaults"))
    speed, torque = read_u8(ser, ADDR_SPEED), read_u8(ser, ADDR_TORQUE)
    results.append(check(speed == SPEED_DEFAULT and torque == TORQUE_DEFAULT,
                         f"defaults are in the registers: Speed {speed}, Torque {torque}"))

    write_u8(ser, ADDR_SPEED, 200)
    write_u8(ser, ADDR_TORQUE, 42)
    ser = reboot(ser, port, RST_EE)
    results.append(check(read_u8(ser, R_RESET_DEV) == BOOT_EE, "the device boots from storage"))
    speed, torque = read_u8(ser, ADDR_SPEED), read_u8(ser, ADDR_TORQUE)
    results.append(check(speed == 200 and torque == 42,
                         f"written values survived the reboot: Speed {speed}, Torque {torque}"))

    ser = reboot(ser, port, RST_DEF)
    speed, torque = read_u8(ser, ADDR_SPEED), read_u8(ser, ADDR_TORQUE)
    results.append(check(speed == SPEED_DEFAULT and torque == TORQUE_DEFAULT,
                         f"RST_DEF puts the defaults back: Speed {speed}, Torque {torque}"))

    # The device name is non-volatile too, and the specification says a write
    # to it must be saved and must reset the device.
    original = read_str(ser, R_DEVICE_NAME)
    write_name(ser, "GateTestName")
    time.sleep(0.3)
    ser.close()
    time.sleep(REBOOT_SECONDS)
    ser = open_port(port, settle=1.0)
    write_u8(ser, R_OP_CTRL, OP_ACTIVE)
    name = read_str(ser, R_DEVICE_NAME)
    results.append(check(name == "GateTestName", f"the written device name survived the reboot, read {name!r}"))

    ser = reboot(ser, port, RST_DEF)
    name = read_str(ser, R_DEVICE_NAME)
    results.append(check(name == original, f"RST_DEF puts the name back to {original!r}, read {name!r}"))
    return ser


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", default="COM21" if sys.platform == "win32" else "/dev/ttyACM0")
    p.add_argument("--no-reboot", action="store_true",
                   help="skip the non-volatile settings checks, which reboot the board")
    args = p.parse_args()

    results = []
    with open_port(args.port) as ser:

        print("1. Identity and state, as Bonsai sees it on connect")
        who = print_identity(ser)
        results.append(check(who is not None, f"WhoAmI = {who}"))
        write_u8(ser, R_OP_CTRL, OP_ACTIVE)  # events are only sent in ACTIVE mode
        v = read_u8(ser, ADDR_GATE_STATE)
        results.append(check(v is not None, f"Status = {v} ({STATUS_NAMES.get(v, '?')})"))
        if v == 4:
            print("  gate is still homing from boot, waiting")
            results.append(check(wait_status(ser, 2, CAL_TIMEOUT_S), "boot homing reached Down"))
            v = read_u8(ser, ADDR_GATE_STATE)
        servo = v != 0xFF
        if not servo:
            print("  no servo answering: expecting Error instead of Idle and Down")
        after_stop = 0 if servo else 0xFF
        after_home = 2 if servo else 0xFF

        print("2. Conflicting bits are rejected")
        f = write_u8(ser, ADDR_CONTROL, CTRL_ENABLE_MOTOR | CTRL_DISABLE_MOTOR)
        results.append(check(f is not None and f["error"], "Enable + Disable gives an error reply"))

        print("3. Stop halts a movement")
        write_u8(ser, ADDR_TARGET_POSITION, 255)
        time.sleep(0.5)
        f = write_u8(ser, ADDR_CONTROL, CTRL_STOP)
        results.append(check(f is not None and not f["error"], "Stop write accepted"))
        time.sleep(0.3)
        v = read_u8(ser, ADDR_GATE_STATE)
        results.append(check(v == after_stop, f"Status after Stop = {v} ({STATUS_NAMES.get(v, '?')}), expected {STATUS_NAMES[after_stop]}"))
        drain_events(ser, 0.5)

        print("4. Calibrate homes the gate")
        f = write_u8(ser, ADDR_CONTROL, CTRL_CALIBRATE)
        results.append(check(f is not None and not f["error"], "Calibrate write accepted"))
        time.sleep(0.2)
        v = read_u8(ser, ADDR_GATE_STATE)
        # Without a servo the setup fails at once, so Calibrating is too short to see.
        during = (4,) if servo else (4, 0xFF)
        results.append(check(v in during, f"Status during homing = {v} ({STATUS_NAMES.get(v, '?')}), expected {' or '.join(STATUS_NAMES[d] for d in during)}"))
        results.append(check(wait_status(ser, after_home, CAL_TIMEOUT_S), f"homing reached {STATUS_NAMES[after_home]} within the timeout"))
        drain_events(ser, 0.5)

        if args.no_reboot:
            print("5. Non-volatile settings: skipped (--no-reboot)")
        else:
            print("5. Non-volatile settings survive a reboot")
            print(f"   this reboots the board three times, about {3 * REBOOT_SECONDS} seconds")
            ser = check_settings(ser, args.port, results)
        ser.close()

    print()
    print(f"{sum(results)} of {len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
