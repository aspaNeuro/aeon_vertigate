# VertiGate register map: implemented vs proposed

> Companion to [`HARP_MIGRATION_PLAN.md`](HARP_MIGRATION_PLAN.md) §2.2. Analysis only, no code
> changes. Sources: [`firmware/register.py`](../firmware/register.py),
> [`firmware/gate.py`](../firmware/gate.py), [`device.yml`](../device.yml).

## 1. Side by side

| Addr | **Implemented today** | **Proposed** | Change |
| --- | --- | --- | --- |
| 32 | *(unused)* | `Control` U8, Write. Motor enable/disable, `Stop`, `Calibrate`, and on/off bits for the two streaming events | **new** |
| 33 | `Operation` U8, **Write-only**. 0 = down, 255 = up, linear in between | `TargetPosition` U8, **Read** + Write. Same 1.2 mm scale | **name + read access** |
| 34 | `Status` U8, Read + Event. `Idle/Up/Down/Moving` | `GateState` U8, Read + Event. Adds `Error` | rename + one value |
| 35 | `Speed` U8, Read + Write | `Speed` U8, Read + Write | **unchanged** (declare defaults) |
| 36 | `Torque` U8, Read + Write | `Torque` U8, Read + Write | **unchanged** (declare defaults) |
| 37 | `Offset` S8, Read + Write | `CalibrationOffset` S8, Read + Write | **rename only** |
| 38 | — | `Position` U16, Read + Event. Measured, in encoder counts | **new** |
| 39 | — | `MotorFault` U8, Read + Event | **new** |
| 40 | — | `ServoTelemetry` U16×n, Read + Event *(optional)* | **new** |

**All five existing registers keep their address and payload type.** Speed, Torque and Status do
not change. Offset and Operation are renamed. Operation also gains read access. Everything else is
a new register at an unused address.

**The map is therefore purely additive on the wire.** Register names live in `device.yml` and in
the generated interface, not in the protocol. A controller sees only the address and the payload
type, and none of those change. An existing Bonsai workflow written for the current map keeps
working without changes.

> **Decision (2026-09-09):** address 33 stays **U8**. Widening it to U16 would change the step
> from 1.2 mm to 25 µm (one encoder count). 1.2 mm is enough for this mechanism. This decision is
> what makes the map additive instead of breaking.
>
> Note that µm would not have worked as a unit anyway. The travel is about 300 mm, which is
> 300,000 µm and needs U32. A wider target would have had to use **encoder counts** (0 to 12000).

`Position` (38) is proposed as U16 in encoder counts, even though the target is U8. This is on
purpose. You command in 1.2 mm steps, but you observe at the servo's full 25 µm resolution. That
is what makes the register useful for finding overshoot and slip. Use U8 instead if you prefer
the same scale as the target.

---

## 2. What actually changes behaviour

Most items in the table are cosmetic. These five are not.

### 2.1 `Stop` becomes reachable

`Gate.stop()` already exists in [`gate.py`](../firmware/gate.py). It cancels the motion task and
holds position. **No register calls it.** Today a moving gate can only be redirected, not stopped.
`Control.Stop` exposes code that is already written and tested.

### 2.2 Re-homing becomes possible, and stops being a boot hazard

`_calibrate_home()` runs once, inside `Gate.__init__`. It uses blocking `time.sleep` in a
`while True` loop with no timeout, and it runs *before* `device.run()`. Today this means:

- if the Dynamixel is absent or does not respond, the board never appears on USB and looks bricked
- if the mechanism slips during a session, the only recovery is a power cycle

`Control.Calibrate` makes homing a command. The device then always comes up on the bus, and a
drifted gate can be re-homed from Bonsai.

### 2.3 Position becomes observable

Today there is **no way to ask where the gate is**. `Status` reports one of four states, and the
states hide a problem:

- `_isup` is set only when `target_pos == max_pos`; `_isdown` only when `target_pos == home_pos`
- so after a move to **any position in between, `status` returns `Idle` (0)**, the same value as
  "stationary and not homed"

`Idle` therefore means both "position unknown" and "parked at 137". A `Position` event register
fixes this. Every comparable Harp device has one (`faststepper` has `Encoder`, `aeon_lineardrive`
has `Position`).

### 2.4 Resolution stays at 1.2 mm, but the top of travel is degenerate

`move()` computes `pos = 48 * pos + home_pos` over a `LENGTH` of 12000 encoder counts. So one
step is **48 encoder counts, about 1.2 mm**. That is kept on purpose (see §1). One side effect of
the scaling is worth fixing while the map is open:

`48 × 250 = 12000`, so **command values 250 to 255 all clamp to the same physical position**. Six
of the 256 values are redundant, and `raise_up()` calls `move(255)`, which lands in that clamped
range. Either scale by `12000 / 255 ≈ 47.06` so the full byte range maps to the full travel, or
document 250 as the top of the scale. Cosmetic, but it is one line.

### 2.5 Faults become visible

Dynamixel stalls, comms timeouts and out-of-travel conditions are invisible to the host today. The
gate can fail to reach its target and report nothing. `MotorFault`, plus the `Error` value in
`GateState`, reports these as an event. This is what the spec recommends for such conditions,
instead of error replies to unrelated writes.

---

## 3. What changes for conformance rather than capability

- **`Operation` is write-only, so it does not appear in the register dump.** microharp's
  `_dump_all_registers()` skips registers without read access. A controller that connects today
  never learns the commanded target. A Read + Write `TargetPosition` appears in the dump. See plan
  §3.3.
- **`Operation` reads like a sibling of core `R_OPERATION_CTRL` (address 10)**, which is a
  different thing. Every comparable device uses a functional name.
- **The `0` / `255` special cases are an idempotence guard, not a semantic overload.** An earlier
  draft of this analysis cited the spec's *Register polymorphism* section here. That was wrong.
  `lower_down()` calls `move(0)`, `raise_up()` calls `move(255)`, and `move()` is a plain linear
  map. The endpoints are ordinary values on the same scale, not special values. The only real
  effect of the branching is that endpoint commands are skipped when the gate is already there,
  while commands for other positions always re-issue the move. Worth making uniform, but it is a
  wart, not a conformance defect.
- **Event traffic cannot be switched off.** Once `Position` streams, a host that only cares about
  end-stop transitions has no way to stop it and must filter downstream. Harp devices provide a
  way to switch event sources off. See the `Control` entry in §7 for how this map does it.

---

## 4. Migration risk: none, given the U8 decision

Address 33 keeps its address, payload type and linear scale, so **no register changes meaning on
the wire.** Existing workflows keep working:

| Write to 33 | Behaviour before | Behaviour after |
| --- | --- | --- |
| `0` | lower fully | lower fully |
| `255` | raise fully | raise fully |
| `1`–`254` | proportional position | proportional position |

The only difference is that endpoint commands are no longer silently skipped when the gate is
already there (§3). That is an edge case for repeated commands, not a migration hazard.

> An earlier draft of this document proposed widening 33 to U16. It warned that reusing the
> address would fail silently: a workflow writing `0` would still work, while `255` would barely
> move the gate. **That risk no longer exists**, because the type is unchanged. It is recorded
> here so the reasoning is not rediscovered later. If anyone revisits the U16 question, that trap
> comes back with it, and `TargetPosition` should then move to a fresh address so old workflows
> fail loudly instead.

Renaming `Operation` to `TargetPosition` and `Offset` to `CalibrationOffset` changes the
generated C# and Python API, not the protocol. No interface package has shipped yet, so there is
nothing downstream to update.

---

## 5. Cost

| Item | Firmware work |
| --- | --- |
| `Control` (32) | small. `Stop` and `EnableMotor`/`DisableMotor` wrap existing methods |
| `Calibrate` bit | **moderate**. `_calibrate_home()` must become non-blocking, with a timeout and a fault path |
| `TargetPosition` (33) | **trivial**. Add read access and rename. Optionally fix the 250–255 clamp |
| `GateState` + `Error` | small. One extra state, set from the fault path |
| `Position` (38) | small. Poll `present_position`. Needs an `on_read` handler and a decision on event rate |
| `MotorFault` (39) | **moderate**. Needs real stall and timeout detection, which does not exist today |
| Event on/off bits (in `Control`) | small. A flag check in the event task |
| `ServoTelemetry` (40) | small, but adds Dynamixel bus traffic. Defer |
| Storage defaults + `on_read` on all registers | small, and **required in any case** (plan §3.3) |

The two moderate items, non-blocking calibration and real fault detection, are the substance.
Everything else is plumbing.

---

## 6. Conclusion

**With the U8 decision taken, this is not a redesign. It is three additions, two renames and one
access-flag change.** No existing register moves, changes type, or changes meaning.

What you get that does not exist today, in rough order of value:

1. **Stop**. Already implemented in firmware, currently unreachable.
2. **Position readback**. The device cannot report where it is today, and `Idle` silently also
   means "at a position in between".
3. **Fault visibility**. Failures are silent today.
4. **Re-homing on command**, which also removes the boot-hang hazard.
5. **A readable target**. Write-only registers are skipped in the register dump, so a controller
   that connects today cannot learn what was commanded.

What is only cosmetic: `Offset` to `CalibrationOffset`, `Operation` to `TargetPosition`, and
`Status` to `GateState`. Worth doing while the map is open, not worth doing alone.

**Recommendation: adopt the map in §1, keeping `TargetPosition` at address 33.**

Because the change is additive, the usual "before release or never" pressure does not apply to
*this* map. The additions can land later at their unused addresses without breaking anything.
What still carries that pressure is any future decision to widen 33 (§4), and the renames. The
renames change the generated API and are free only until an `Aeon.VertiGate` package ships.

### If you want less churn

A minimum subset gives most of the value for about a third of the work, and is compatible with
the full map later:

| Addr | Register | Why |
| --- | --- | --- |
| 32 | `Control`, `Stop` + `Calibrate` only | unlocks existing code, fixes the boot hazard |
| 38 | `Position` Read + Event | makes the device observable |
| 34 | `GateState`, add `Error` | lets faults be reported at all |

Keep `Operation` at 33 as it is, fill only the first four `Control` bits, and defer `MotorFault`
and `ServoTelemetry`. Nothing here blocks adopting the rest later. The remaining additions are
unused bits in `Control` and one unused address.

---

## 7. Register reference

What each register in the proposed map is for, what it carries, and what it costs to implement.
"Exists" means the register is already in [`device.yml`](../device.yml) and
[`register.py`](../firmware/register.py) today.

### `Control`: address 32, U8, Write. **New**

A command register. Writing a bit triggers an action; it does not store a setting. This is the
standard Harp pattern for verbs (`device.faststepper` has `Control`, `device.syringepump` has
`EnableMotorDriver`). It keeps one-shot actions out of the position register.

| Bit | Mask | Name | Action |
| --- | --- | --- | --- |
| 0 | `0x01` | `EnableMotor` | `gate.torque_enabled = True`. Hold position |
| 1 | `0x02` | `DisableMotor` | `gate.torque_enabled = False`. Free the gate, for example for manual handling |
| 2 | `0x04` | `Stop` | calls the existing `Gate.stop()`. Cancels the motion task and holds where it is |
| 3 | `0x08` | `Calibrate` | runs homing again |
| 4 | `0x10` | `EnablePositionEvent` | start emitting `Position` (38) events |
| 5 | `0x20` | `DisablePositionEvent` | stop emitting them |
| 6 | `0x40` | `EnableTelemetryEvent` | start emitting `ServoTelemetry` (40) events |
| 7 | `0x80` | `DisableTelemetryEvent` | stop emitting them |

Address 32 is unused today. The Harp spec reserves 0 to 31 for core registers, so 32 is the first
legal application address.

**Why the event on/off bits are here and not in a separate `EnableEvents` register.** Both
patterns exist. `device.syringepump` uses a separate `EnableEvents` mask (address 52, U8, six
bits). `device.faststepper` puts paired bits in `Control` instead: `EnableAnalogInput` `0x4` /
`DisableAnalogInput` `0x8`, `EnableEncoder` `0x10` / `DisableEncoder` `0x20`. These control its
`AnalogInput` and `Encoder` event registers.

The paired form is used here because it keeps every write to `Control` a **pure command with no
state**. A single mask register would force the host to read, modify and write on every command,
or risk `Control = Stop` clearing the event-enable bits by accident. The trade-off is that the
enable state cannot be read back, because there is nothing to read, so it does not appear in the
register dump.

**Only the two streaming sources have on/off bits.** `GateState` fires from `_enable()` /
`_disable()`, about twice per move. `MotorFault` fires once per fault. Neither can burst, so
neither needs a switch. `Position` and `ServoTelemetry` are the only sources that can saturate
the link.

This uses all 8 bits. That is acceptable because the map is additive (§4). A future command can
use a new register at an unused address without breaking anything.

**Cost:** `Stop`, `EnableMotor` and `DisableMotor` are thin wrappers over existing code. The
on/off bits are a flag check in the event task. `Calibrate` is the expensive bit (see §5),
because `_calibrate_home()` must first become non-blocking, with a timeout and a failure path.

### `TargetPosition`: address 33, U8, Read + Write. **Exists** (as `Operation`)

Where you want the gate to go. `0` = fully down, `255` = fully up, linear in between at about
1.2 mm per count. **Address, type and scale do not change.** See the decision note in §1.

Two changes. The rename, because `Operation` sounds like core `R_OPERATION_CTRL` at address 10.
And **read access**, so the register appears in the startup dump and a controller can see what
was last commanded.

**Cost:** trivial. Optionally fix the 250–255 clamp from §2.4 at the same time.

### `GateState`: address 34, U8, Read + Event. **Exists** (as `Status`)

The gate's state machine, emitted as an event on every change. Existing values keep their
numbers, so nothing on the wire changes:

| Value | Name | Meaning |
| --- | --- | --- |
| 0 | `Idle` | stationary, not at a known end stop |
| 1 | `Up` | at the fully-raised end |
| 2 | `Down` | at the fully-lowered end |
| 3 | `Moving` | moving towards a target |
| 4 | `Error` | **new**. Motion failed; see `MotorFault` |

Note the `Idle` ambiguity from §2.3. It currently means both "at a position in between" and
"position unknown". Adding `Position` (38) resolves this in practice, without more states.

**Cost:** small. One added value, set from whatever fault path is built.

### `Speed`: address 35, U8, Read + Write. **Exists, unchanged**

Movement speed, mapped to the Dynamixel profile velocity. The firmware applies
`profile_velocity = (value & 0xFF) + 60`. The fixed `VEL_OFFSET` of 60 means that a written `0`
still moves the gate instead of stalling.

Two fixes belong here. Both are in the migration plan already and are not map changes: declare
`defaultValue: 255` and copy it into register storage at construction (plan §3.3), and make the
write reply report the value actually applied, not the raw byte (plan §3).

### `Torque`: address 36, U8, Read + Write. **Exists, unchanged**

Current limit for the motor, masked to the low 7 bits (0 to 127), default 35. It sets how hard
the gate pushes at the end stops, and so whether it stalls or crushes.

Same two fixes as `Speed`. Also worth documenting: the setter switches `torque_enabled` off and
then on, so **writing this register while the gate is holding will briefly drop the gate**.

### `CalibrationOffset`: address 37, S8, Read + Write. **Exists** (as `Offset`), rename only

Fine adjustment of the fully-raised end, in encoder counts of 25 µm each, range −128 to +127
(about ±3.2 mm). Lets you trim the up position without moving hardware.

Renamed to match the ecosystem convention (`device.syringepump` uses `CalibrationOffset` /
`CalibrationSlope`) and to say clearly that it is a calibration constant, not a runtime offset.

**This register is broken today.** `payload[0]` on a memoryview gives an unsigned byte, so
negative values arrive as 128 to 255 and clamp to +127. Negative offsets do not work (plan §3).

### `Position`: address 38, U16, Read + Event. **New**

The gate's **measured** position, read from the servo encoder, in encoder counts (0 to about
12000, 25 µm each). Different from `TargetPosition`, which is only what was asked for.

This is the most valuable addition. The device cannot report where it is today, and `GateState`
collapses every position in between into `Idle`. With `Position` you can check that the gate
arrived, detect slip or obstruction, and log the true gate height against behavioural events.

U16 in encoder counts is finer than the U8 target on purpose. You command in 1.2 mm steps and
observe at 25 µm. See the note in §1.

**Cost:** small. `gate.present_position` already exists and `_run()` already polls it. Needs an
`on_read` handler and a decision on event rate: on change with a deadband, or periodic only while
moving. Avoid a fast periodic event. Every read is a transaction on the 1 Mbaud Dynamixel bus.

### `MotorFault`: address 39, U8, Read + Event. **New**

Why a move failed. Emitted as an event, so failures appear immediately instead of being guessed
from a gate that never reaches its target.

| Bit | Name | Source |
| --- | --- | --- |
| 0 | `Stall` | target not reached within a timeout while `Moving` |
| 1 | `Overload` | servo `Hardware Error Status` overload bit |
| 2 | `CommsTimeout` | no valid reply from the Dynamixel |
| 3 | `TravelLimit` | commanded or measured position outside `home_pos` to `max_pos` |

The servo keeps its own `Hardware Error Status` byte (control table item 40). It has bits for
input voltage, overheating, encoder error, electrical shock and overload. That is the natural
source for bits 1 and 2.

**Cost: moderate, the highest of any register here.** None of this detection exists today.
`Stall` needs a timeout in `Gate._run()`, which currently waits in a `while` loop with no limit.
`CommsTimeout` needs the driver's retry path to report failures instead of hiding them. And
`HARDWARE_ERROR_STATUS` is defined in the driver's control table but **has no property that
reads it**, so reading it means a small addition to `micropython-dynamixel`.

### `EnableEvents`: **dropped from this map**

An earlier draft proposed a separate `EnableEvents` mask at address 40, because
`device.syringepump`, `device.stepperdriver` and `device.behavior` all have one and it looked
like the convention. That was overstated. `device.faststepper` uses paired bits inside `Control`
and has no such register. Both patterns are current.

Event on/off is now handled by bits 4 to 7 of `Control` (32). See that entry for the reasoning
and the trade-off.

### `ServoTelemetry`: address 40, U16 × n, Read + Event. **New, optional**

**This is the register you asked about.** It exposes the Dynamixel's own health readings: the
state of the *motor*, as opposed to the state of the *gate*. `Position` and `GateState` answer
"what is the mechanism doing". Telemetry answers "how hard is the servo working, and is it about
to fail".

Proposed payload, one U16 per field:

| Offset | Field | Unit *(check against the Robotis XM430 control table)* | Use |
| --- | --- | --- | --- |
| 0 | `Current` | about 2.69 mA per count | load on the gate. Rising current means friction, binding, or an obstruction |
| 1 | `Temperature` | 1 °C per count | thermal headroom. The XM430 shuts down at about 80 °C |
| 2 | `Voltage` | 0.1 V per count | supply drop under load. A common cause of intermittent stalls |

Why it is worth having: these three numbers are how you diagnose a gate that "sometimes does not
close" without adding instruments to the rig. A slow rise in current across a session means the
mechanism is binding. A temperature rise means the duty cycle is too high. A voltage dip during
movement means the supply is too small for the XM430 stall current.

Why it is optional and deferred:

- **Not readable today.** The driver exposes `present_current`, but `PRESENT_TEMPERATURE` and
  `PRESENT_INPUT_VOLTAGE` exist only as control-table constants, with **no properties**. Each
  needs a few lines in `micropython-dynamixel`. That is upstream work that helps the whole fleet,
  but it is not free.
- **It costs bus bandwidth.** Every field is a separate Dynamixel transaction, competing with the
  position polling in `_run()`. Sample at about 1 Hz, or only while moving, not on every control
  cycle. `Control` bits 6 and 7 switch the event off. If a configurable *rate* is wanted as well,
  that is a separate period register (with `0` meaning disabled, by convention), to add when
  telemetry itself lands.
- **Nothing depends on it.** Unlike `MotorFault`, no correctness argument needs it. It is
  diagnostics. If the gate is reliable, nobody reads it.

A reasonable middle path: implement `MotorFault` first, and add `ServoTelemetry` only if faults
start to happen and you need the numbers behind them.
