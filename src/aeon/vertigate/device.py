# This file was automatically generated and should not be edited directly.
# To make changes, edit the device metadata and regenerate the interface.

import enum
from typing import Any, ClassVar

import numpy as np
from harp.protocol import (
    AnonymousPayload,
    BitMask,
    GroupMask,
    PayloadType,
    RegisterBase,
    RegisterS8,
    RegisterU8,
)
from harp.device.core import REGISTER_MAP as _CORE_REGISTER_MAP


__all__ = [
    "DEVICE_NAME",
    "WHO_AM_I",
    "ControlFlags",
    "GateStatus",
    "ControlPayload",
    "GateStatePayload",
    "Control",
    "TargetPosition",
    "GateState",
    "Speed",
    "Torque",
    "CalibrationOffset",
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


class Control(RegisterBase[ControlFlags]):
    """Commands for the gate. Each bit is one command. Writing a bit runs the command. The register stores no state. A write with both bits of a pair set is rejected with an error reply."""

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
    """Torque limit applied to the gate motor, as a servo current limit. Values are masked to the lower 7 bits. One count is 0.36 kgf·mm. Writing this register switches the motor torque off and on, so the gate drops for a moment if it is holding a position."""

    address: ClassVar[int] = 36


class CalibrationOffset(RegisterS8):
    """Offset applied to the fully-raised position, to trim the end stop without moving hardware. One count is one encoder count, 25 µm."""

    address: ClassVar[int] = 37


REGISTER_MAP: dict[int, type[RegisterBase[Any]]] = {
    **_CORE_REGISTER_MAP,
    32: Control,
    33: TargetPosition,
    34: GateState,
    35: Speed,
    36: Torque,
    37: CalibrationOffset,
}
