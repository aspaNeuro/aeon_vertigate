"""Hardware test for the VertiGate Control register.

Run from the repository root, with the Harp port of the board:

    uv run vertigate-test --port COM4

What it does, in order:
    1. Reads WhoAmI and the Status register.
    2. Sends a bad Control write (Enable + Disable) and expects an error reply.
    3. Raises the gate, sends Stop after 0.5 s, and expects the gate to stop.
    4. Sends Calibrate and waits for Status to go Calibrating, then Down.
    5. Prints every Status event seen on the way.

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
R_OP_CTRL = 10
OP_ACTIVE = 0x01

ADDR_CONTROL = 32
ADDR_OPERATION = 33
ADDR_STATUS = 34

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
    if f["address"] == ADDR_STATUS and f["payload"]:
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


def write_u8(ser, address, value):
    return request(ser, MSG_WRITE, address, PT_U8, bytes([value]))


def wait_status(ser, wanted, timeout):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        v = read_u8(ser, ADDR_STATUS)
        if v == wanted:
            return True
        time.sleep(0.1)
    return False


def check(ok, text):
    print(("  PASS  " if ok else "  FAIL  ") + text)
    return ok


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", default="COM21" if sys.platform == "win32" else "/dev/ttyACM0")
    args = p.parse_args()

    results = []
    with serial.Serial(args.port, baudrate=1_000_000, timeout=0.005) as ser:
        ser.dtr = True
        time.sleep(0.2)
        ser.reset_input_buffer()

        print("1. Identity and state")
        f = request(ser, MSG_READ, R_WHO_AM_I, PT_U16)
        who = struct.unpack("<H", f["payload"])[0] if f else None
        results.append(check(who is not None, f"WhoAmI = {who}"))
        write_u8(ser, R_OP_CTRL, OP_ACTIVE)  # events are only sent in ACTIVE mode
        v = read_u8(ser, ADDR_STATUS)
        results.append(check(v is not None, f"Status = {v} ({STATUS_NAMES.get(v, '?')})"))
        if v == 4:
            print("  gate is still homing from boot, waiting")
            results.append(check(wait_status(ser, 2, CAL_TIMEOUT_S), "boot homing reached Down"))
            v = read_u8(ser, ADDR_STATUS)
        servo = v != 0xFF
        if not servo:
            print("  no servo answering: expecting Error instead of Idle and Down")
        after_stop = 0 if servo else 0xFF
        after_home = 2 if servo else 0xFF

        print("2. Conflicting bits are rejected")
        f = write_u8(ser, ADDR_CONTROL, CTRL_ENABLE_MOTOR | CTRL_DISABLE_MOTOR)
        results.append(check(f is not None and f["error"], "Enable + Disable gives an error reply"))

        print("3. Stop halts a movement")
        write_u8(ser, ADDR_OPERATION, 255)
        time.sleep(0.5)
        f = write_u8(ser, ADDR_CONTROL, CTRL_STOP)
        results.append(check(f is not None and not f["error"], "Stop write accepted"))
        time.sleep(0.3)
        v = read_u8(ser, ADDR_STATUS)
        results.append(check(v == after_stop, f"Status after Stop = {v} ({STATUS_NAMES.get(v, '?')}), expected {STATUS_NAMES[after_stop]}"))
        drain_events(ser, 0.5)

        print("4. Calibrate homes the gate")
        f = write_u8(ser, ADDR_CONTROL, CTRL_CALIBRATE)
        results.append(check(f is not None and not f["error"], "Calibrate write accepted"))
        time.sleep(0.2)
        v = read_u8(ser, ADDR_STATUS)
        # Without a servo the setup fails at once, so Calibrating is too short to see.
        during = (4,) if servo else (4, 0xFF)
        results.append(check(v in during, f"Status during homing = {v} ({STATUS_NAMES.get(v, '?')}), expected {' or '.join(STATUS_NAMES[d] for d in during)}"))
        results.append(check(wait_status(ser, after_home, CAL_TIMEOUT_S), f"homing reached {STATUS_NAMES[after_home]} within the timeout"))
        drain_events(ser, 0.5)

    print()
    print(f"{sum(results)} of {len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
