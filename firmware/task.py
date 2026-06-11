from microharp import HarpDevice, PT_U8
from gate import Gate

def setup_user_task(device: HarpDevice, gate: Gate, status_address: int):
    @device.task
    async def _main_task():
        payload = bytearray(1)
        while True:
            await gate.isr.wait()
            payload[0] = gate.status
            await device.emit(status_address, payload, PT_U8)
            gate.isr.clear()
