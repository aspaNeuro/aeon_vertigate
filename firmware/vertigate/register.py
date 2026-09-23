import asyncio
import struct

from microharp import EVENT, PT_U8, PT_S8, READ_ONLY, READ_WRITE, WRITE_ONLY, HarpDevice
from microharp.registers import R_DEVICE_NAME, R_RESET_DEV
from microharp.device import DEVICE_NAME_LEN
from micropython import const
import settings
from gate import Gate, TRQ_DEFAULT, VEL_DEFAULT


ADDR_CONTROL = 0x20
ADDR_TARGET_POSITION = 0x21
ADDR_GATE_STATE = 0x22
ADDR_SPD = 0x23
ADDR_TRQ = 0x24
ADDR_CALIBRATION_OFFSET = 0x25
ADDR_MOTOR_STATE = 0x26

# Registers marked `volatile: false` in device.yml, with the `defaultValue`
# declared there. Keep both in step with device.yml.
DEFAULTS = {
    ADDR_SPD: VEL_DEFAULT,
    ADDR_TRQ: TRQ_DEFAULT,
    ADDR_CALIBRATION_OFFSET: 0,
}

# R_RESET_DEV (address 11) bits, from the Harp specification.
RST_DEF = const(0x01)   # reboot with the defaults and erase the stored values
RST_EE = const(0x02)    # reboot with the stored values
SAVE = const(0x04)      # store the non-volatile registers, then reboot
BOOT_DEF = const(0x40)  # read-only: the device booted with the defaults
BOOT_EE = const(0x80)   # read-only: the device booted from storage
BOOT_BITS = const(0xC0)

# Long enough for the write reply to reach the host before the port drops.
REBOOT_DELAY_MS = const(150)

# Control register bits. Each write is a command, not a setting.
CTRL_ENABLE_MOTOR = const(0x01)
CTRL_DISABLE_MOTOR = const(0x02)
CTRL_STOP = const(0x04)
CTRL_CALIBRATE = const(0x08)
CTRL_ENABLE_POSITION_EVENT = const(0x10)
CTRL_DISABLE_POSITION_EVENT = const(0x20)
CTRL_ENABLE_TELEMETRY_EVENT = const(0x40)
CTRL_DISABLE_TELEMETRY_EVENT = const(0x80)
CTRL_PAIRS = (
    CTRL_ENABLE_MOTOR | CTRL_DISABLE_MOTOR,
    CTRL_ENABLE_POSITION_EVENT | CTRL_DISABLE_POSITION_EVENT,
    CTRL_ENABLE_TELEMETRY_EVENT | CTRL_DISABLE_TELEMETRY_EVENT,
)

ERR_BAD_VALUE = const(1)
ERR_SERVO = const(2)
ERR_READ_ONLY_BIT = const(3)
ERR_STORAGE = const(4)
ERR_MOTOR_DISABLED = const(5)


def _write_register(device, address, value):
    """Put a value in register storage, signed or unsigned to match the type."""
    reg = device.bank.get(address)
    fmt = "<b" if reg.payload_type == PT_S8 else "<B"
    struct.pack_into(fmt, reg.storage, 0, value)


def _read_register(device, address):
    reg = device.bank.get(address)
    fmt = "<b" if reg.payload_type == PT_S8 else "<B"
    return struct.unpack_from(fmt, reg.storage)[0]


def _decode_name(payload):
    """Read the device name out of its null-padded byte array."""
    return bytes(payload).split(b"\x00", 1)[0].decode()


def _apply(gate, address, value):
    """Send one setting to the servo. Raises if the servo does not answer."""
    if address == ADDR_SPD:
        gate.speed = value
    elif address == ADDR_TRQ:
        gate.torque = value
    elif address == ADDR_CALIBRATION_OFFSET:
        gate.offset = value


# The values on flash, kept in memory so a write that changes nothing does not
# touch the flash. Filled by _load_settings() at start-up.
_stored = {}


def _reboot_after_reply():
    """Reboot, but let the write reply go out first.

    The specification says the device must reply to the write before it
    reboots. microharp sends the reply after the handler returns, so a
    handler that calls machine.reset() directly loses it.
    """

    async def _later():
        await asyncio.sleep_ms(REBOOT_DELAY_MS)
        import machine

        machine.reset()

    asyncio.create_task(_later())


def _store(address, value):
    """Save one setting, if it is not already the value on flash.

    `device.yml` marks these registers `volatile: false`, so a written value
    must survive a power cycle. The check against `_stored` is what makes this
    safe to do on every write: a workflow that writes the same Speed on every
    trial touches the flash once, not once per trial.

    A failed write is not reported to the host. The value is already applied
    and readable, and refusing the write would be a worse answer than losing
    it at the next power cycle.
    """
    if _stored.get(address) == value:
        return
    _stored[address] = value
    try:
        settings.save(_stored)
    except Exception:
        _stored.pop(address, None)  # Try again on the next write.


def setup_register_handlers(device: HarpDevice, gate: Gate):

    device.add_u8(ADDR_CONTROL, access=WRITE_ONLY, name="Control")
    device.add_u8(ADDR_TARGET_POSITION, access=WRITE_ONLY, name="TargetPosition")
    device.add_u8(ADDR_GATE_STATE, access=READ_ONLY | EVENT, name="GateState")
    device.add_u8(ADDR_SPD, access=READ_WRITE, name="Speed")
    device.add_u8(ADDR_TRQ, access=READ_WRITE, name="Torque")
    # microharp has no add_s8 helper. Use the generic form.
    device.add_register(ADDR_CALIBRATION_OFFSET, PT_S8, access=READ_WRITE, name="CalibrationOffset")
    device.add_u8(ADDR_MOTOR_STATE, access=READ_ONLY | EVENT, name="MotorState")

    @device.on_read(address=ADDR_GATE_STATE, payload_type=PT_U8, name="GateState")
    async def _gate_state(reg):
        reg.storage[0] = gate.status

    @device.on_read(address=ADDR_MOTOR_STATE, payload_type=PT_U8, name="MotorState")
    async def _motor_state(reg):
        reg.storage[0] = 1 if gate.motor_enabled else 0

    @device.on_write(address=ADDR_CONTROL, payload_type=PT_U8, name="Control")
    async def _control(reg, payload):
        cmd = payload[0]
        # Reject the whole write if both bits of an on/off pair are set.
        # Nothing is applied in that case.
        for pair in CTRL_PAIRS:
            if cmd & pair == pair:
                return ERR_BAD_VALUE
        # Calibration moves the gate, so it needs the motor. A write that
        # enables the motor in the same command is allowed to calibrate.
        if cmd & CTRL_CALIBRATE and not gate.motor_enabled and not cmd & CTRL_ENABLE_MOTOR:
            return ERR_MOTOR_DISABLED
        reg.storage[0] = cmd

        try:
            if cmd & CTRL_STOP:
                gate.stop()
            if cmd & CTRL_DISABLE_MOTOR:
                gate.disable()
            if cmd & CTRL_ENABLE_MOTOR:
                gate.enable()
        except Exception:
            # The servo did not answer. Reply with an error, keep running.
            return ERR_SERVO
        if cmd & CTRL_CALIBRATE:
            gate.start_calibration()
        if cmd & CTRL_ENABLE_POSITION_EVENT:
            gate.position_events = True
        if cmd & CTRL_DISABLE_POSITION_EVENT:
            gate.position_events = False
        if cmd & CTRL_ENABLE_TELEMETRY_EVENT:
            gate.telemetry_events = True
        if cmd & CTRL_DISABLE_TELEMETRY_EVENT:
            gate.telemetry_events = False

    @device.on_write(address=ADDR_TARGET_POSITION, payload_type=PT_U8, name="TargetPosition")
    async def _target_position(reg, payload):
        # DisableMotor is a state, not a one-off command. The gate does not
        # move until the host enables the motor again.
        if not gate.motor_enabled:
            return ERR_MOTOR_DISABLED
        pos = payload[0]
        reg.storage[0] = pos
        if pos == 0:
            gate.lower_down()
        elif pos == 255:
            gate.raise_up()
        else:
            gate.move(pos)

    @device.on_write(address=ADDR_SPD, payload_type=PT_U8, name="Speed")
    async def _speed(reg, payload):
        speed = payload[0]
        reg.storage[0] = speed
        try:
            gate.speed = speed
        except Exception:
            return ERR_SERVO
        _store(ADDR_SPD, speed)

    @device.on_write(address=ADDR_TRQ, payload_type=PT_U8, name="Torque")
    async def _torque(reg, payload):
        torque = payload[0]
        reg.storage[0] = torque
        try:
            gate.torque = torque
        except Exception:
            return ERR_SERVO
        _store(ADDR_TRQ, torque)

    @device.on_write(address=ADDR_CALIBRATION_OFFSET, payload_type=PT_S8, name="CalibrationOffset")
    async def _calibration_offset(reg, payload):
        offset = struct.unpack_from("<b", payload)[0]
        reg.storage[0] = payload[0]
        gate.offset = offset
        _store(ADDR_CALIBRATION_OFFSET, offset)

    # ------------------------------------------------------------------
    # Non-volatile settings, through R_RESET_DEV (address 11).
    #
    # microharp registers this as write-only and reboots on any non-zero
    # write. The specification needs more: the command bits must act, the
    # boot bits must be readable, and the values of the registers marked
    # `volatile: false` in device.yml must survive a power cycle. The
    # handlers below replace microharp's.
    # ------------------------------------------------------------------

    boot_flags = _load_settings(device, gate)

    @device.on_read(address=R_RESET_DEV, payload_type=PT_U8, name="ResetDevice")
    async def _reset_read(reg):
        # The command bits are cleared on a read. Only the boot bits remain,
        # and they say how this session started.
        reg.storage[0] = boot_flags

    @device.on_write(address=R_RESET_DEV, payload_type=PT_U8, name="ResetDevice")
    async def _reset_write(reg, payload):
        cmd = payload[0]
        if cmd & BOOT_BITS:
            # The boot bits report state. A write cannot set them.
            return ERR_READ_ONLY_BIT
        if cmd & SAVE:
            # Every write to a non-volatile register is already stored, so
            # there is normally nothing to do. The bit is still honoured, for
            # conformance and in case an earlier store failed.
            try:
                settings.save({a: _read_register(device, a) for a in DEFAULTS})
            except Exception:
                return ERR_STORAGE
        elif cmd & RST_DEF:
            settings.clear()
        if cmd & (SAVE | RST_DEF | RST_EE):
            _reboot_after_reply()

    # R_DEVICE_NAME (address 12) is non-volatile too, and the specification
    # gives it its own rule: a write must be saved and the device must reset.
    # microharp keeps the name in RAM only, so it is lost on the next boot.

    @device.on_write(address=R_DEVICE_NAME, payload_type=PT_U8,
                     n_elements=DEVICE_NAME_LEN, name="DeviceName")
    async def _device_name(reg, payload):
        reg.storage[:] = payload
        name = _decode_name(payload)
        if _stored.get(R_DEVICE_NAME) == name:
            return  # Writing the same name changes nothing, so do not reboot.
        _stored[R_DEVICE_NAME] = name
        try:
            settings.save(_stored)
        except Exception:
            _stored.pop(R_DEVICE_NAME, None)
            return ERR_STORAGE
        _reboot_after_reply()


def _load_settings(device, gate):
    """Put the defaults in the registers, then the stored values on top.

    Also fills `_stored`, so a later write that changes nothing does not touch
    the flash.

    Returns the R_RESET_DEV boot bits: BOOT_EE when stored values were used,
    BOOT_DEF otherwise.
    """
    stored = settings.load()
    values = dict(DEFAULTS)
    values.update({a: v for a, v in stored.items() if a in DEFAULTS})

    _stored.clear()
    _stored.update(values)

    for address, value in values.items():
        _write_register(device, address, value)
        try:
            _apply(gate, address, value)
        except Exception:
            pass  # No servo. The gate reports Error; the registers still read back.

    # The device name is a byte array, not a number, so it is restored apart.
    # Its default comes from the name passed to HarpDevice, already in storage.
    reg = device.bank.get(R_DEVICE_NAME)
    name = stored.get(R_DEVICE_NAME)
    if name:
        encoded = name.encode()[:DEVICE_NAME_LEN - 1]
        reg.storage[:] = encoded + bytes(DEVICE_NAME_LEN - len(encoded))
    _stored[R_DEVICE_NAME] = _decode_name(reg.storage)

    return BOOT_EE if stored else BOOT_DEF
