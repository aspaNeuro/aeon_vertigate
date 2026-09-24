# This file was automatically generated and should not be edited directly.
# To make changes, edit the device metadata and regenerate the interface.

import enum
from typing import Any, ClassVar

import numpy as np
from harp.protocol import (
    AnonymousPayload,
    BitMask,
    Field,
    GroupMask,
    IdentityConverter,
    PayloadType,
    RegisterBase,
    RegisterS8,
    RegisterU8,
    StructPayload,
)
from harp.device.core import REGISTER_MAP as _CORE_REGISTER_MAP


__all__ = [
    "DEVICE_NAME",
    "WHO_AM_I",
    "ControlFlags",
    "MotorStatus",
    "GateStatus",
    "ControlPayload",
    "GateStatePayload",
    "MotorStatePayload",
    "ServoTelemetryPayload",
    "RawPositionPayload",
    "Control",
    "TargetPosition",
    "GateState",
    "Speed",
    "Torque",
    "CalibrationOffset",
    "MotorState",
    "Position",
    "ServoTelemetry",
    "RawPosition",
    "REGISTER_MAP",
]

DEVICE_NAME: str = "VertiGate"
WHO_AM_I: int = 3002


class ControlFlags(enum.IntFlag):
    """Commands accepted by the Control register."""

    ENABLE_MOTOR = 0x1
    """Turn the motor torque on. The gate holds its position."""

    DISABLE_MOTOR = 0x2
    """Turn the motor torque off. The gate can be moved by hand."""

    STOP = 0x4
    """Stop the current movement and hold the position."""

    CALIBRATE = 0x8
    """Move the gate to the lower end stop and record it as home."""

    ENABLE_POSITION_EVENT = 0x10
    """Start sending Position events."""

    DISABLE_POSITION_EVENT = 0x20
    """Stop sending Position events."""

    ENABLE_TELEMETRY_EVENT = 0x40
    """Start sending ServoTelemetry events."""

    DISABLE_TELEMETRY_EVENT = 0x80
    """Stop sending ServoTelemetry events."""


class MotorStatus(enum.IntEnum):
    """Enumerates the states of the gate motor."""

    DISABLED = 0
    """The motor is off. The gate refuses to move until the motor is enabled."""

    ENABLED = 1
    """The motor is on and holds the gate."""


class GateStatus(enum.IntEnum):
    """Enumerates the possible states of the gate."""

    IDLE = 0
    """The gate is stationary and not at a known end stop."""

    UP = 1
    """The gate is fully raised up."""

    DOWN = 2
    """The gate is fully lowered down."""

    MOVING = 3
    """The gate is moving towards a target position."""

    CALIBRATING = 4
    """The gate is moving to the lower end stop to find home."""

    ERROR = 255
    """The last movement or calibration failed."""


class ControlPayload(AnonymousPayload[np.uint8]):
    """Represents the payload of the Control register."""

    __value__: ControlFlags = BitMask(enum=ControlFlags)


class GateStatePayload(AnonymousPayload[np.uint8]):
    """Represents the payload of the GateState register."""

    __value__: GateStatus = GroupMask(enum=GateStatus, mask=0xFF)


class MotorStatePayload(AnonymousPayload[np.uint8]):
    """Represents the payload of the MotorState register."""

    __value__: MotorStatus = GroupMask(enum=MotorStatus, mask=0xFF)


class ServoTelemetryPayload(StructPayload[np.int16], length=4):
    """Represents the payload of the ServoTelemetry register."""

    voltage: np.int16 = Field(IdentityConverter(np.int16))
    """Supply voltage at the servo, in units of 0.1 V."""

    temperature: np.int16 = Field(IdentityConverter(np.int16), offset=1)
    """Servo temperature, in degrees Celsius."""

    current: np.int16 = Field(IdentityConverter(np.int16), offset=2)
    """Current through the motor, in mA. Negative means the other direction."""

    hardware_error: np.int16 = Field(IdentityConverter(np.int16), offset=3)
    """Servo hardware error status. 0 means no fault."""


class RawPositionPayload(StructPayload[np.int32], length=2):
    """Represents the payload of the RawPosition register."""

    encoder: np.int32 = Field(IdentityConverter(np.int32))
    """Position reported by the servo, in raw encoder counts."""

    home: np.int32 = Field(IdentityConverter(np.int32), offset=1)
    """The encoder count recorded as the fully-lowered home."""


class Control(RegisterBase[ControlFlags]):
    """Commands for the gate. Writing a bit runs one command. A write with both bits of a pair set is rejected with an error reply. Reading reports the state, not the last command: EnableMotor when the motor is on, EnablePositionEvent when Position events are on, and EnableTelemetryEvent when ServoTelemetry events are on. Stop and Calibrate are commands, so they never appear in a read. The state is kept over a power cycle."""

    address: ClassVar[int] = 32
    payload_type: ClassVar[PayloadType] = PayloadType.U8
    payload_class = ControlPayload


class TargetPosition(RegisterU8):
    """Target position of the gate. 0 lowers the gate fully down, 255 raises it fully up, and any value in between moves the gate to the matching position. One count is 1.2 mm."""

    address: ClassVar[int] = 33


class GateState(RegisterBase[GateStatus]):
    """Reports the current state of the gate."""

    address: ClassVar[int] = 34
    payload_type: ClassVar[PayloadType] = PayloadType.U8
    payload_class = GateStatePayload


class Speed(RegisterU8):
    """Movement speed of the gate, mapped onto the Dynamixel profile velocity. One count is 0.38 mm/s."""

    address: ClassVar[int] = 35


class Torque(RegisterU8):
    """Torque limit applied to the gate motor, as a servo current limit. Values are masked to the lower 7 bits. One count is 0.36 kgf·mm. Writing this register switches the motor off and on, so the gate drops for a moment if it is holding a position. It leaves the motor off if MotorState is Disabled."""

    address: ClassVar[int] = 36


class CalibrationOffset(RegisterS8):
    """Offset applied to the fully-raised position, to trim the end stop without moving hardware. One count is one encoder count, 25 µm."""

    address: ClassVar[int] = 37


class MotorState(RegisterBase[MotorStatus]):
    """Reports whether the motor holds the gate. DisableMotor and EnableMotor set it."""

    address: ClassVar[int] = 38
    payload_type: ClassVar[PayloadType] = PayloadType.U8
    payload_class = MotorStatePayload


class Position(RegisterU8):
    """Where the gate is now, on the same scale as TargetPosition. Read it at any time. EnablePositionEvent also reports it while the gate moves or homes. Homing measures against the old home until the new one is recorded, so the value steps at the end of a calibration. One count is 1.2 mm."""

    address: ClassVar[int] = 39


class ServoTelemetry(RegisterBase[ServoTelemetryPayload]):
    """Readings from the servo. Read it at any time. EnableTelemetryEvent also reports it once a second."""

    address: ClassVar[int] = 40
    payload_type: ClassVar[PayloadType] = PayloadType.S16
    payload_class = ServoTelemetryPayload


class RawPosition(RegisterBase[RawPositionPayload]):
    """The two encoder counts that Position is built from. Read it at any time. EnablePositionEvent also reports it beside every Position event. Position is Encoder minus Home, divided by 48 and clamped to 0 to 255, so this pair shows the travel the clamp hides and the step when a calibration records a new home. One count is 25 um."""

    address: ClassVar[int] = 41
    payload_type: ClassVar[PayloadType] = PayloadType.S32
    payload_class = RawPositionPayload


REGISTER_MAP: dict[int, type[RegisterBase[Any]]] = {
    **_CORE_REGISTER_MAP,
    32: Control,
    33: TargetPosition,
    34: GateState,
    35: Speed,
    36: Torque,
    37: CalibrationOffset,
    38: MotorState,
    39: Position,
    40: ServoTelemetry,
    41: RawPosition,
}
