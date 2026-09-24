import asyncio
import struct

from micropython import const

from microharp import HarpDevice, PT_U8, PT_S16, PT_S32
from gate import Gate, MOVING, CALIBRATING, scale_position

# Position only changes while the gate is under way, so the stream runs at this
# period and stops when the gate stops. Telemetry drifts rather than jumps, so
# it is reported far less often.
POSITION_PERIOD_MS = const(50)
TELEMETRY_PERIOD_MS = const(1000)


def setup_user_task(device: HarpDevice, gate: Gate, status_address: int, motor_address: int,
                    position_address: int, telemetry_address: int, raw_address: int):

    @device.task
    async def _state_task():
        """Report the gate state on every change, and the motor state when it
        changes. Both are driven by the gate, not by a timer."""
        payload = bytearray(1)
        motor = bytearray(1)
        last_motor = None
        while True:
            await gate.isr.wait()
            payload[0] = gate.status
            await device.emit(status_address, payload, PT_U8)
            motor[0] = 1 if gate.motor_enabled else 0
            if motor[0] != last_motor:
                last_motor = motor[0]
                await device.emit(motor_address, motor, PT_U8)
            gate.isr.clear()

    @device.task
    async def _position_task():
        """Report the position while the gate is under way, if the host asked
        for it. Homing counts, so the host can watch the gate find the stop.

        RawPosition goes out beside it. Position is clamped to 0 to 255, which
        hides the travel below home and the step a calibration makes when it
        records a new one. The raw pair shows both."""
        payload = bytearray(1)
        raw = bytearray(8)
        while True:
            await asyncio.sleep_ms(POSITION_PERIOD_MS)
            if not gate.position_events or gate.status not in (MOVING, CALIBRATING):
                continue
            try:
                # One servo read for both, so the clamped value and the raw
                # pair always describe the same instant.
                encoder, home = gate.raw_position
            except Exception:
                continue  # No servo. The gate already reports Error.
            payload[0] = scale_position(encoder, home)
            struct.pack_into("<2i", raw, 0, encoder, home)
            await device.emit(position_address, payload, PT_U8)
            await device.emit(raw_address, raw, PT_S32)

    @device.task
    async def _telemetry_task():
        """Report the servo readings once a second, if the host asked for it."""
        payload = bytearray(8)
        while True:
            await asyncio.sleep_ms(TELEMETRY_PERIOD_MS)
            if not gate.telemetry_events:
                continue
            try:
                struct.pack_into("<4h", payload, 0, *gate.telemetry)
            except Exception:
                continue  # No servo. The gate already reports Error.
            await device.emit(telemetry_address, payload, PT_S16)
