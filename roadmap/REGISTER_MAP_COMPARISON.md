# VertiGate register map: implemented vs proposed

> Companion to [`HARP_MIGRATION_PLAN.md`](HARP_MIGRATION_PLAN.md) §2.2. Analysis only — no code
> changes. Sources: [`firmware/register.py`](../firmware/register.py),
> [`firmware/gate.py`](../firmware/gate.py), [`device.yml`](../device.yml).

## 1. Side by side

| Addr | **Implemented today** | **Proposed** | Change |
| --- | --- | --- | --- |
| 32 | *(unused)* | `Control` U8, Write — motor enable/disable, `Stop`, `Calibrate`, plus paired gating for the two streaming events | **new** |
| 33 | `Operation` U8, **Write-only** — 0 = down, 255 = up, linear in between | `TargetPosition` U8, **Read** + Write — same 1.2 mm scale | **name + read access** |
| 34 | `Status` U8, Read + Event — `Idle/Up/Down/Moving` | `GateState` U8, Read + Event — adds `Error` | rename + one value |
| 35 | `Speed` U8, Read + Write | `Speed` U8, Read + Write | **unchanged** (declare defaults) |
| 36 | `Torque` U8, Read + Write | `Torque` U8, Read + Write | **unchanged** (declare defaults) |
| 37 | `Offset` S8, Read + Write | `CalibrationOffset` S8, Read + Write | **rename only** |
| 38 | — | `Position` U16, Read + Event — measured, encoder counts | **new** |
| 39 | — | `MotorFault` U8, Read + Event | **new** |
| 40 | — | `ServoTelemetry` U16×n, Read + Event *(optional)* | **new** |

**All five existing registers keep their address and payload type.** Speed, Torque and Status are
untouched; Offset and Operation are renamed; Operation additionally gains read access. Everything
else is a new register at a previously unused address.

**The map is therefore purely additive on the wire.** Register names live in `device.yml` and the
generated interface, not in the protocol — what a controller sees is address plus payload type,
and none of those change. An existing Bonsai workflow written against the current map keeps
working unmodified.

> **Decision (2026-09-09):** address 33 stays **U8**. Widening it to U16 would have taken the
> commandable step from 1.2 mm to 25 µm (one encoder count), but 1.2 mm is adequate for this
> mechanism. Recorded here because it is what makes the map additive rather than breaking.
>
> Note µm would not have been a viable unit in any case: the ~300 mm travel is 300,000 µm, which
> needs U32. A widened target would have had to be expressed in **encoder counts** (0–12000).

`Position` (38) is proposed as U16 in encoder counts despite the U8 target. This asymmetry is
deliberate — you command in 1.2 mm steps but observe at the servo's full 25 µm resolution, which
is what makes the register useful for diagnosing overshoot and slip. Use U8 instead if symmetry
with the target matters more than measurement resolution.

---

## 2. What actually changes behaviour

Everything else in the table is cosmetic. These five items are not.

### 2.1 `Stop` becomes reachable

`Gate.stop()` already exists in [`gate.py`](../firmware/gate.py) — it cancels the motion task and
holds position. **There is no register that calls it.** A gate in motion today can only be
redirected, never halted. `Control.Stop` exposes code that is already written and tested.

### 2.2 Re-homing becomes possible, and stops being a boot hazard

`_calibrate_home()` runs once, inside `Gate.__init__`, with blocking `time.sleep` in an unbounded
`while True` loop — *before* `device.run()`. Consequences today:

- if the Dynamixel is absent or unresponsive, the board never enumerates and looks bricked
- if the mechanism slips mid-session, the only recovery is a power cycle

`Control.Calibrate` makes homing a command. The device then always comes up on the bus, and a
drifted gate can be re-homed from Bonsai.

### 2.3 Position becomes observable

There is currently **no way to ask where the gate is**. `Status` reports a four-state bucket, and
that bucket is degenerate in a way that is easy to miss:

- `_isup` is set only when `target_pos == max_pos`; `_isdown` only when `target_pos == home_pos`
- so after a move to **any intermediate position, `status` returns `Idle` (0)** — the same value
  as "stationary and not homed"

`Idle` therefore means both "at an unknown position" and "parked at 137". A `Position` event
register resolves this, and is what every comparable Harp device provides
(`faststepper` → `Encoder`, `aeon_lineardrive` → `Position`).

### 2.4 Resolution stays at 1.2 mm — but the top of travel is degenerate

`move()` computes `pos = 48 * pos + home_pos` over a `LENGTH` of 12000 encoder counts, so the
effective step is **48 encoder counts ≈ 1.2 mm**. That is being kept deliberately (see §1), so
this is not a change — but one artifact of the scaling is worth fixing while the map is open:

`48 × 250 = 12000`, so **command values 250–255 all clamp to the same physical position**. Six of
the 256 values are redundant, and `raise_up()` issues `move(255)`, landing in that clamped
region. Either scale by `12000 / 255 ≈ 47.06` so the full byte range maps onto the full travel,
or document 250 as the top of scale. Cosmetic, but it costs one line to get right.

### 2.5 Faults become visible

Dynamixel stalls, comms timeouts and out-of-travel conditions are invisible to the host today.
The gate can fail to reach its target and report nothing. `MotorFault` plus the `Error` value in
`GateState` surfaces it as an event, which is what the spec recommends for conditions like these
(rather than error replies to unrelated writes).

---

## 3. What changes for conformance rather than capability

- **`Operation` is write-only, so it is invisible in the register dump.** microharp's
  `_dump_all_registers()` skips registers without read access, so a controller connecting today
  never learns the commanded target. A Read + Write `TargetPosition` appears in the dump. See
  plan §3.3.
- **`Operation` reads as a sibling of core `R_OPERATION_CTRL` (addr 10)**, which is a different
  thing entirely. Every comparable device uses a functional name.
- **The `0` / `255` special-casing is an idempotence guard, not a semantic overload.** An earlier
  draft of this analysis cited the spec's *Register polymorphism* section here; that was wrong.
  `lower_down()` calls `move(0)` and `raise_up()` calls `move(255)`, and `move()` is a plain
  linear map — the endpoints are ordinary values on the same scale, not sentinels. The only real
  effect of the branching is that endpoint commands are skipped when the gate is already there,
  while intermediate commands always re-issue the move. Worth making uniform, but it is a wart,
  not a conformance defect.
- **Event traffic cannot be gated.** Once `Position` streams, a host that only cares about
  end-stop transitions has no way to turn it off and must filter downstream. Harp devices provide
  a way to switch event sources off; see the `Control` entry in §7 for how this map does it.

---

## 4. Migration risk — none, given the U8 decision

With address 33 keeping its address, payload type and linear scale, **no register changes meaning
on the wire.** Existing workflows keep working:

| Write to 33 | Behaviour before | Behaviour after |
| --- | --- | --- |
| `0` | lower fully | lower fully |
| `255` | raise fully | raise fully |
| `1`–`254` | proportional position | proportional position |

The only behavioural difference is that endpoint commands stop being silently skipped when the
gate is already there (§3), which is a repeat-command edge case, not a migration hazard.

> An earlier draft of this document proposed widening 33 to U16 and warned that reusing the
> address would fail silently — a workflow writing `0` would still work while `255` would move
> the gate barely at all. **That risk no longer exists**, because the type is unchanged. It is
> recorded here only so the reasoning is not rediscovered later: if anyone revisits the U16
> question, that trap comes back with it, and `TargetPosition` should then move to a fresh
> address so old workflows fail loudly instead.

Renaming `Operation` → `TargetPosition` and `Offset` → `CalibrationOffset` changes the generated
C# and Python API, not the protocol. Since no interface package has shipped yet, there is nothing
downstream to update.

---

## 5. Cost

| Item | Firmware work |
| --- | --- |
| `Control` (32) | small — `Stop` and `EnableMotor`/`DisableMotor` wrap existing methods |
| `Calibrate` bit | **moderate** — requires making `_calibrate_home()` non-blocking and adding a timeout + fault path |
| `TargetPosition` (33) | **trivial** — add read access, rename; optionally fix the 250–255 clamp |
| `GateState` + `Error` | small — one extra state, plus setting it from the fault path |
| `Position` (38) | small — poll `present_position`; needs an `on_read` handler and an event cadence decision |
| `MotorFault` (39) | **moderate** — needs actual stall/timeout detection, which does not exist today |
| Event gating (in `Control`) | small — a flag check in the event task |
| `ServoTelemetry` (40) | small, but adds Dynamixel bus traffic; defer |
| Storage defaults + `on_read` on all registers | small, and **required regardless** (plan §3.3) |

The two moderate items — non-blocking calibration and real fault detection — are the substance.
Everything else is plumbing.

---

## 6. Conclusion

**With the U8 decision taken, this is not a redesign at all — it is three additions, two renames
and one access-flag change.** No existing register moves, changes type, or changes meaning.

What you get that does not exist today, in rough order of value:

1. **Stop** — already implemented in firmware, currently unreachable
2. **Position readback** — the device cannot presently report where it is, and `Idle` silently
   doubles as "at an intermediate position"
3. **Fault visibility** — failures are currently silent
4. **Commandable re-homing**, which also removes the boot-hang hazard
5. **A readable target** — write-only registers are skipped in the register dump, so a connecting
   controller currently cannot learn what was commanded

What is merely cosmetic: `Offset` → `CalibrationOffset`, `Operation` → `TargetPosition`, and
`Status` → `GateState`. Worth doing while the map is open, not worth doing alone.

**Recommendation: adopt it as specified in §1, keeping `TargetPosition` at address 33.**

Because the change is additive, the usual "do it before release or never" pressure does not
apply to *this* map — the additions can land later at their unused addresses without breaking
anything. What still does carry that pressure is any future decision to widen 33 (§4), and the
renames, which change the generated API and are free only until a `Fablabs.VertiGate` package
ships.

### If you want less churn

A minimum viable subset captures most of the value for roughly a third of the work, and is
forward-compatible with the full map:

| Addr | Register | Why |
| --- | --- | --- |
| 32 | `Control` — `Stop` + `Calibrate` only | unlocks existing code, fixes the boot hazard |
| 38 | `Position` Read + Event | makes the device observable |
| 34 | `GateState` — add `Error` | lets faults be reported at all |

Keep `Operation` at 33 as-is, populate only the first four `Control` bits, and defer `MotorFault`
and `ServoTelemetry`. Nothing here forecloses adopting the rest later — the remaining additions
are unused bits in `Control` and one unused address.

---

## 7. Register reference

What each register in the proposed map is for, what it carries, and what implementing it costs.
"Exists" means the register is already in [`device.yml`](../device.yml) and
[`register.py`](../firmware/register.py) today.

### `Control` — address 32, U8, Write — **new**

A command register: writing a bit triggers an action, rather than storing a setting. This is the
standard Harp idiom for verbs (`device.faststepper` → `Control`, `device.syringepump` →
`EnableMotorDriver`), keeping one-shot actions out of the position register.

| Bit | Mask | Name | Action |
| --- | --- | --- | --- |
| 0 | `0x01` | `EnableMotor` | `gate.torque_enabled = True` — hold position |
| 1 | `0x02` | `DisableMotor` | `gate.torque_enabled = False` — free the gate, e.g. for manual handling |
| 2 | `0x04` | `Stop` | calls the existing `Gate.stop()` — cancels the motion task, holds where it is |
| 3 | `0x08` | `Calibrate` | re-runs homing |
| 4 | `0x10` | `EnablePositionEvent` | start emitting `Position` (38) events |
| 5 | `0x20` | `DisablePositionEvent` | stop emitting them |
| 6 | `0x40` | `EnableTelemetryEvent` | start emitting `ServoTelemetry` (40) events |
| 7 | `0x80` | `DisableTelemetryEvent` | stop emitting them |

Address 32 is currently unused; the Harp spec reserves 0–31 for core registers, so 32 is the
first legal application address.

**Why event gating lives here rather than in a separate `EnableEvents` register.** Both patterns
exist in the ecosystem. `device.syringepump` uses a standalone `EnableEvents` mask (address 52,
U8, six bits); `device.faststepper` instead folds it into `Control` as paired bits —
`EnableAnalogInput` `0x4` / `DisableAnalogInput` `0x8`, `EnableEncoder` `0x10` /
`DisableEncoder` `0x20` — gating its `AnalogInput` and `Encoder` event registers.

The paired form is used here because it keeps every write to `Control` a **pure command carrying
no state**. A single mask register would force the host to read-modify-write on every command, or
risk `Control = Stop` clearing the event-enable bits as a side effect. The trade-off accepted is
that enable state cannot be read back — there is nothing to read — so it does not appear in the
register dump.

**Only the two streaming sources are gated.** `GateState` fires from `_enable()` / `_disable()`,
roughly twice per move, and `MotorFault` fires per fault; neither can burst, so neither needs an
off switch. `Position` and `ServoTelemetry` are the only sources that can saturate the link.

That fills all 8 bits exactly. This is acceptable because the map is additive (§4): a future
command can take a new register at an unused address without breaking anything.

**Cost:** `Stop`, `EnableMotor` and `DisableMotor` are thin wrappers over code that already
exists, and the gating bits are a flag check in the event task. `Calibrate` is the expensive bit
— see §5 — because `_calibrate_home()` must first be made non-blocking with a timeout and a
failure path.

### `TargetPosition` — address 33, U8, Read + Write — **exists** (as `Operation`)

Where you want the gate to go. `0` = fully down, `255` = fully up, linear in between at
~1.2 mm per count. **Unchanged in address, type and scale** — see the decision note in §1.

Two changes: the rename (because `Operation` collides conceptually with core `R_OPERATION_CTRL`
at address 10), and **adding read access**, so the register appears in the startup dump and a
connecting controller can see what was last commanded.

**Cost:** trivial. Optionally fix the 250–255 clamp described in §2.4 at the same time.

### `GateState` — address 34, U8, Read + Event — **exists** (as `Status`)

The gate's state machine, emitted as an event on every transition. Existing values keep their
numbers, so nothing on the wire changes:

| Value | Name | Meaning |
| --- | --- | --- |
| 0 | `Idle` | stationary, position not at a known end stop |
| 1 | `Up` | at the fully-raised end |
| 2 | `Down` | at the fully-lowered end |
| 3 | `Moving` | in transit toward a target |
| 4 | `Error` | **new** — motion failed; see `MotorFault` |

Note the `Idle` ambiguity described in §2.3: it currently means both "at an intermediate
position" and "position unknown". Adding `Position` (38) resolves this in practice without
needing more states.

**Cost:** small — one added value, plus setting it from whatever fault path is built.

### `Speed` — address 35, U8, Read + Write — **exists, unchanged**

Movement speed, mapped onto the Dynamixel profile velocity. The firmware applies
`profile_velocity = (value & 0xFF) + 60`, i.e. a fixed `VEL_OFFSET` of 60 so that a written `0`
still produces motion rather than a stalled move.

Two fixes belong here, both already in the migration plan rather than being map changes:
declare `defaultValue: 255` and mirror it into register storage at construction (plan §3.3), and
make the write reply report the value actually applied rather than the raw byte (plan §3).

### `Torque` — address 36, U8, Read + Write — **exists, unchanged**

Current limit applied to the motor, masked to the low 7 bits (0–127), default 35. Governs how
hard the gate pushes at the end stops, and therefore whether it stalls or crushes.

Same two fixes as `Speed`. Also worth documenting: the setter cycles `torque_enabled` off then on,
so **writing this register mid-hold will briefly drop the gate**.

### `CalibrationOffset` — address 37, S8, Read + Write — **exists** (as `Offset`), rename only

Fine adjustment of the fully-raised endpoint, in encoder counts of 25 µm each, range −128…+127
(≈ ±3.2 mm). Lets the up position be trimmed mechanically without moving hardware.

Renamed to match the ecosystem convention (`device.syringepump` uses `CalibrationOffset` /
`CalibrationSlope`) and to say plainly that it is a calibration constant, not a runtime offset.

**This register is currently broken** — `payload[0]` on a memoryview yields an unsigned byte, so
negative values arrive as 128–255 and clamp to +127. Negative offsets are impossible today
(plan §3).

### `Position` — address 38, U16, Read + Event — **new**

The gate's **measured** position, read back from the servo's encoder, in encoder counts
(0…~12000, 25 µm each). Distinct from `TargetPosition`, which is only what was asked for.

This is the single most valuable addition: the device currently cannot report where it is, and
`GateState` collapses every intermediate position into `Idle`. With `Position` you can verify the
gate actually arrived, detect slip or obstruction, and log true gate height against behavioural
events.

U16 in encoder counts is deliberately finer than the U8 target — you command in 1.2 mm steps but
observe at 25 µm. See the note in §1.

**Cost:** small. `gate.present_position` already exists and is polled by `_run()`. Needs an
`on_read` handler plus a decision on event cadence — on-change with a deadband, or periodic
during motion only. Avoid a high-rate periodic event: every read is a transaction on the
1 Mbaud Dynamixel bus.

### `MotorFault` — address 39, U8, Read + Event — **new**

Why a move failed. Emitted as an event so failures surface immediately rather than being inferred
from a gate that never reaches its target.

| Bit | Name | Source |
| --- | --- | --- |
| 0 | `Stall` | target not reached within a timeout while `Moving` |
| 1 | `Overload` | servo `Hardware Error Status` overload bit |
| 2 | `CommsTimeout` | no valid reply from the Dynamixel |
| 3 | `TravelLimit` | commanded or measured position outside `home_pos … max_pos` |

The servo maintains its own `Hardware Error Status` byte (control table item 40) with bits for
input voltage, overheating, encoder error, electrical shock and overload — the natural backing for
bits 1–2.

**Cost: moderate, and the highest of any register here.** None of this detection exists today.
`Stall` needs a timeout in `Gate._run()`, which currently waits in an unbounded `while` loop;
`CommsTimeout` needs the driver's retry path to surface failures rather than swallow them; and
`HARDWARE_ERROR_STATUS` is defined in the driver's control table but **has no property exposing
it**, so reading it means a small addition to `micropython-dynamixel`.

### `EnableEvents` — **dropped from this map**

An earlier draft proposed a standalone `EnableEvents` mask at address 40, on the grounds that
`device.syringepump`, `device.stepperdriver` and `device.behavior` all carry one and it was
therefore the convention. That was overstated: `device.faststepper` gates its event sources with
paired bits inside `Control` and has no such register. Both patterns are current.

Event gating is now handled by bits 4–7 of `Control` (32). See that entry for the reasoning and
the trade-off.

### `ServoTelemetry` — address 40, U16 × n, Read + Event — **new, optional**

**This is the register you asked about.** It exposes the Dynamixel's own health readings — the
state of the *motor*, as opposed to the state of the *gate*. Where `Position` and `GateState`
answer "what is the mechanism doing", telemetry answers "how hard is the servo working, and is it
about to fail".

Proposed payload, one U16 per field:

| Offset | Field | Unit *(verify against the Robotis XM430 control table)* | Use |
| --- | --- | --- | --- |
| 0 | `Current` | ~2.69 mA per count | load on the gate — rising current means friction, binding, or an obstruction |
| 1 | `Temperature` | 1 °C per count | thermal headroom; XM430 shuts down around 80 °C |
| 2 | `Voltage` | 0.1 V per count | supply sag under load — a common cause of intermittent stalls |

Why it is worth having: these three numbers are how you diagnose a gate that "sometimes doesn't
close" without instrumenting the rig. A slow upward drift in current across a session means the
mechanism is binding; a temperature climb means duty cycle is too high; a voltage dip correlated
with movement means the supply is undersized for XM430 stall current.

Why it is marked optional and deferred:

- **Not currently readable.** The driver exposes `present_current`, but `PRESENT_TEMPERATURE` and
  `PRESENT_INPUT_VOLTAGE` exist only as control-table constants with **no properties**. Each needs
  a few lines added to `micropython-dynamixel` — upstream work benefiting the whole fleet, but not
  free.
- **It costs bus bandwidth.** Every field is a separate Dynamixel transaction competing with the
  position polling in `_run()`. Sample at ~1 Hz, or only while moving — not per control cycle.
  `Control` bits 6–7 switch the event off; if a configurable *rate* is wanted as well, that is a
  separate period register (with `0` conventionally meaning disabled) to be added when telemetry
  itself lands.
- **Nothing depends on it.** Unlike `MotorFault`, no correctness argument requires it; it is
  diagnostics. If the gate is reliable, it goes unread.

A reasonable middle path: implement `MotorFault` first, and add `ServoTelemetry` only if faults
start occurring and you need the numbers behind them.
