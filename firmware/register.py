from microharp import EVENT, PT_U8, PT_S8, READ_ONLY, READ_WRITE, WRITE_ONLY, HarpDevice
from micropython import const
from gate import Gate


ADDR_CONTROL = 0x20
ADDR_OP = 0x21
ADDR_STATUS = 0x22
ADDR_SPD = 0x23
ADDR_TRQ = 0x24
ADDR_OFFSET = 0x25

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


def setup_register_handlers(device: HarpDevice, gate: Gate):

    device.add_u8(ADDR_CONTROL, access=WRITE_ONLY, name="Control")
    device.add_u8(ADDR_OP, access=WRITE_ONLY, name="Operation")
    device.add_u8(ADDR_STATUS, access=READ_ONLY | EVENT, name="Status")
    device.add_u8(ADDR_SPD, access=READ_WRITE, name="Speed")
    device.add_u8(ADDR_TRQ, access=READ_WRITE, name="Torque")
    # microharp has no add_s8 helper. Use the generic form.
    device.add_register(ADDR_OFFSET, PT_S8, access=READ_WRITE, name="Offset")

    @device.on_read(address=ADDR_STATUS, payload_type=PT_U8, name="Status")
    async def _status(reg):
        reg.storage[0] = gate.status

    @device.on_write(address=ADDR_CONTROL, payload_type=PT_U8, name="Control")
    async def _control(reg, payload):
        cmd = payload[0]
        # Reject the whole write if both bits of an on/off pair are set.
        # Nothing is applied in that case.
        for pair in CTRL_PAIRS:
            if cmd & pair == pair:
                return ERR_BAD_VALUE
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

    @device.on_write(address=ADDR_OP, payload_type=PT_U8, name="Operation")
    async def _operation(reg, payload):
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

    @device.on_write(address=ADDR_TRQ, payload_type=PT_U8, name="Torque")
    async def _torque(reg, payload):
        torque = payload[0]
        reg.storage[0] = torque
        try:
            gate.torque = torque
        except Exception:
            return ERR_SERVO

    @device.on_write(address=ADDR_OFFSET, payload_type=PT_S8, name="Offset")
    async def _offset(reg, payload):
        offset = payload[0]
        reg.storage[0] = offset
        gate.offset = offset
