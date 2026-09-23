from microharp import HarpDevice, PT_U8
from gate import Gate

def setup_user_task(device: HarpDevice, gate: Gate, status_address: int, motor_address: int):
    @device.task
    async def _main_task():
        payload = bytearray(1)
        motor = bytearray(1)
        last_motor = None
        while True:
            await gate.isr.wait()
            payload[0] = gate.status
            await device.emit(status_address, payload, PT_U8)
            # The motor state changes far less often than the gate state, so
            # only report it when it has moved.
            motor[0] = 1 if gate.motor_enabled else 0
            if motor[0] != last_motor:
                last_motor = motor[0]
                await device.emit(motor_address, motor, PT_U8)
            gate.isr.clear()
