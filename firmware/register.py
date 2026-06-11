from microharp import EVENT, PT_U8, PT_S8, READ_ONLY, READ_WRITE, WRITE_ONLY, HarpDevice
from gate import Gate


ADDR_OP = 0x21
ADDR_STATUS = 0x22
ADDR_SPD = 0x23
ADDR_TRQ = 0x24
ADDR_OFFSET = 0x25


def setup_register_handlers(device: HarpDevice, gate: Gate):

    device.add_u8(ADDR_OP, access=WRITE_ONLY, name="Operation")
    device.add_u8(ADDR_STATUS, access=READ_ONLY | EVENT, name="Status")
    device.add_u8(ADDR_SPD, access=READ_WRITE, name="Speed")
    device.add_u8(ADDR_TRQ, access=READ_WRITE, name="Torque")
    device.add_s8(ADDR_OFFSET, access=READ_WRITE, name="Offset")

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
        gate.speed = speed

    @device.on_write(address=ADDR_TRQ, payload_type=PT_U8, name="Torque")
    async def _torque(reg, payload):
        torque = payload[0]
        reg.storage[0] = torque
        gate.torque = torque

    @device.on_write(address=ADDR_OFFSET, payload_type=PT_S8, name="Offset")
    async def _offset(reg, payload):
        offset = payload[0]
        reg.storage[0] = offset
        gate.offset = offset
