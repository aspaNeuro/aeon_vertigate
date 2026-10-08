---
uid: Aeon.VertiGate.Device
---

Use the [Harp device pattern](https://harp-tech.org/articles/operators.html#device-pattern) to initialize the device, log data, and send commands to and receive messages from the VertiGate.

:::workflow
![Harp Device Pattern](../workflows/harp-devicepattern.bonsai)
:::

Check out the following in-depth guides to learn how to access the device functionality with the `Aeon.VertiGate` package:
- [Calibrate the Gate](../articles/calibrate-the-gate.md)
- [Tune Speed and Torque](../articles/tune-the-motion.md)
- [Move the Gate](../articles/move-the-gate.md)
- [Monitor the Servo](../articles/monitor-the-servo.md)

Refer to the register table below for a complete listing of the available registers on the device.

<table>
  <thead>
    <tr><th colspan="2">VertiGate</th></tr>
  </thead>
  <tbody>
    <tr><td>whoAmI</td><td>3002</td></tr>
    <tr><td>firmwareVersion</td><td>0.1</td></tr>
    <tr><td>hardwareTargets</td><td>0.1</td></tr>
  </tbody>
</table>

### Registers

| name | address | type | length | access | description | range | interfaceType |
|-|-|-|-|-|-|-|-|
| [Control](xref:Aeon.VertiGate.Control) | 32 | U8 |  | Write | Commands for the gate. Writing a bit runs one command. A write with both bits of a pair set is rejected with an error reply. Reading reports the state, not the last command: EnableMotor when the motor is on, EnablePositionEvent when Position events are on, and EnableTelemetryEvent when ServoTelemetry events are on. Stop and Calibrate are commands, so they never appear in a read. The state is kept over a power cycle. |  | [ControlFlags](xref:Aeon.VertiGate.ControlFlags) |
| [TargetPosition](xref:Aeon.VertiGate.TargetPosition) | 33 | U8 |  | Write | Target position of the gate. 0 lowers the gate fully down, 255 raises it fully up, and any value in between moves the gate to the matching position. One count is 1.2 mm. The gate stops at step 250. A write of 251 to 255 moves the gate to the same place as 250. | [0:255] | |
| [GateState](xref:Aeon.VertiGate.GateState) | 34 | U8 |  | Event | Reports the current state of the gate. |  | [GateStatus](xref:Aeon.VertiGate.GateStatus) |
| [Speed](xref:Aeon.VertiGate.Speed) | 35 | U8 |  | Write | Movement speed of the gate, mapped onto the Dynamixel profile velocity. One count is 0.38 mm/s. | 255 [0:255] | |
| [Torque](xref:Aeon.VertiGate.Torque) | 36 | U8 |  | Write | Torque limit applied to the gate motor, as a servo current limit. Values are masked to the lower 7 bits. One count is 0.36 kgf·mm. Writing this register switches the motor off and on, so the gate drops for a moment if it is holding a position. It leaves the motor off if MotorState is Disabled. | 35 [0:127] | |
| [CalibrationOffset](xref:Aeon.VertiGate.CalibrationOffset) | 37 | S8 |  | Write | Offset applied to the fully-raised position, to trim the end stop without moving hardware. One count is one encoder count, 25 µm. | 0 [-128:127] | |
| [MotorState](xref:Aeon.VertiGate.MotorState) | 38 | U8 |  | Event | Reports whether the motor holds the gate. DisableMotor and EnableMotor set it. |  | [MotorStatus](xref:Aeon.VertiGate.MotorStatus) |
| [Position](xref:Aeon.VertiGate.Position) | 39 | U8 |  | Event | Where the gate is now, on the same scale as TargetPosition. Read it at any time. EnablePositionEvent also reports it while the gate moves or homes. Homing measures against the old home until the new one is recorded, so the value steps at the end of a calibration. One count is 1.2 mm. The value stops at 250, like TargetPosition. | [0:255] | |
| [ServoTelemetry](xref:Aeon.VertiGate.ServoTelemetry) | 40 | S16 | 4 | Event | Readings from the servo. Read it at any time. EnableTelemetryEvent also reports it once a second. |  | [ServoTelemetryPayload](xref:Aeon.VertiGate.ServoTelemetryPayload) |
| [RawPosition](xref:Aeon.VertiGate.RawPosition) | 41 | S32 | 2 | Event | The two encoder counts that Position is built from. Read it at any time. EnablePositionEvent also reports it beside every Position event. Position is Encoder minus Home, divided by 48 and clamped to 0 to 255, so this pair shows the travel the clamp hides and the step when a calibration records a new home. One count is 25 um. |  | [RawPositionPayload](xref:Aeon.VertiGate.RawPositionPayload) |
