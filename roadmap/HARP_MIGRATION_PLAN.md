# VertiGate to harp-tech device: gap analysis and migration plan

> Status: analysis, plus Phase 1 repo hygiene (`.gitattributes`, `.gitignore`) on `aa-dev/harp-migration`.
> No firmware, interface, or hardware changes have been made.
> Sources checked: `harp-tech/protocol` (spec + `schema/{device,core,registers}.json`),
> `harp-tech/whoami`, `harp-tech/generators`, `harp-tech/toolkit`, `harp-tech/core.pico`,
> `harp-tech/core.atxmega`, `bonsai-rx/prefect` (reference trees + `Ruleset.cs`), `harp-tech/device.template`,
> `harp-tech/device.hobgoblin`, `harp-tech/device.syringepump`, `harp-tech/device.faststepper`,
> `harp-tech/harp-tech.github.io`, `SainsburyWellcomeCentre/micropython-microharp`, the
> AllenNeuralDynamics ecosystem (`harp.core.pico`, `harp.device.pico-template`,
> `harp.device.cuttlefish`, `pyharp`, `Bonsai.AllenNeuralDynamics`), and the existing SWC estate
> (`aeon_lineardrive`, `fablabs-automatic-shelter`, `virt-hunt-drv`, `micropython-neuropico`,
> `conspecific-carousel`, and the `fablabs-*` hardware repos).

## 0. Where we stand

VertiGate is not a blank slate.

**Exists:** a mostly valid `device.yml`, a working MicroPython application on
`micropython-microharp` (which already installs core registers 0 to 19, including the newer
`R_UID`, `R_TAG`, `R_HEARTBEAT` and `R_VERSION`), USB CDC transport, a sync-clock UART, and a
Bonsai example workflow.

**Does not exist:** a registered identity, generated interfaces, the ecosystem repo layout, CI,
version discipline, hardware files, documentation. The firmware also has several real
protocol-conformance bugs.

In short: **protocol plumbing is about 70% done, ecosystem integration about 0% done.**

---

## 0.5 Two reference ecosystems, not one

There is no single "harp-tech way". Two organisations ship Harp devices with different
conventions. Both are legitimate members of the same registry:

| | **harp-tech / Champalimaud** | **AllenNeuralDynamics (AIND)** |
| --- | --- | --- |
| Reference core | `core.atxmega` (C), `core.pico` (C++) | `harp.core.pico` (C++, RP2040 **and RP2350**) |
| Project template | `device.template` (ATxmega era, sparse) | `harp.device.pico-template` (KiCad + CMake, in active use) |
| Repo layout | `Firmware/ Hardware/ Interface/ Assets/` (TitleCase) | `firmware/ hardware/ software/ assets/` (lowercase) |
| Interface generation | `Harp.Generators` + T4 via `Generators/Generators.csproj` | `harp.toolkit` pinned as a **local dotnet tool manifest** |
| C# namespace | `Harp.<Device>` | `AllenNeuralDynamics.<Device>` |
| Package aggregation | individual NuGet packages | `Bonsai.AllenNeuralDynamics` umbrella repo |
| Python | generated interface against `harp-tech/python` | hand-written scripts against `AllenNeuralDynamics/pyharp` |
| CI | full workflow, generated-code freshness gate, NuGet publish | **none in device repos**; a strict release convention instead |
| Listed on harp-tech.org | yes (submodules under `src/`) | **no** |

AIND holds ten WhoAmI allocations (1400 to 1411) under the `aind` owner key. So an external
institution with its own conventions, namespace and Python library is the *normal* case, not an
exception.

**What this means for VertiGate:** the AIND model is closer to where this repo already is
(lowercase folders, no CI, RP2350 silicon, a lab team rather than a product team), and it is
cheaper to adopt. Several recommendations below follow from this. The rest of this document
says where the two ecosystems differ and which side to pick.

---

## 0.6 The SWC estate: VertiGate is not the first, and not the only one

Before importing anyone else's conventions: **SWC already runs several Harp devices**, on three
incompatible firmware stacks. None of them is registered.

| Repo | Harp? | Stack | `device.yml` | WhoAmI | Bonsai pkg | CI |
| --- | --- | --- | --- | --- | --- | --- |
| **`aeon_lineardrive`** | yes | legacy microharp (pinned `df88717c`) + SWC MicroPython fork `v1.18-swc` | **yes** | `0000` placeholder | **`Aeon.LinearDrive`, generated** | **yes** |
| **`aeon_vertigate`** (was `fablabs-VertiGate`) | yes | **current** microharp API + stock MicroPython | yes | 5350, unregistered | no | no |
| **`fablabs-automatic-shelter`** | yes | legacy microharp API | no | `0x1234` placeholder | no | no |
| **`virt-hunt-drv`** | yes | oldest: `SainsburyWellcomeCentre/microharp` + `v1.18-swc` fork | no (README table) | not set | no | no |
| `conspecific-carousel` | **no** | custom framing (`HEADER 0xCC`) | no | — | no | no |
| `aeon_beambreak_filter` | no, TTL logic only | bare MicroPython | — | — | — | — |
| `fablabs-{valve-driver, lick-detector-piezo, monitor-blanking}` | no, passive/TTL **peripherals** | none | — | — | — | — |

### 0.6.1 `aeon_lineardrive` is the reference implementation. Copy it.

This is the most useful finding in this analysis. `aeon_lineardrive` is an **SWC-owned MicroPython
Harp device that already has the complete software pipeline** this document was building up from
first principles:

- `device.yml` at the repo root
- `.config/dotnet-tools.json` pinning `harp.toolkit` **0.2.2, byte-identical to AIND's manifest**
- `software/Aeon.LinearDrive/` with committed `Device.Generated.cs` / `AsyncDevice.Generated.cs`
- `software/build/*.props`, the Bonsai Foundation shared build infrastructure
- `.github/workflows/Aeon.LinearDrive.yml`, derived from `bonsai-rx/prefect` ("automated
  standards enforcement for Bonsai Foundation projects"). Its header comment says: *"a generic
  workflow meant for all Harp devices… Documentation is handled centrally and the MicroPython
  firmware is flashed manually, so this workflow has no DocFX or firmware jobs."*
- `hardware/eCAD/Altium Project/` with Assembly/Fabrication OutJobs, plus `hardware/README.md`
- a prebuilt firmware image attached to every release

That workflow comment describes VertiGate exactly: MicroPython, flashed by hand, docs hosted
elsewhere. **The CI and packaging problem is already solved in-house.** Most of §4 to §6 below
reduces to "copy `aeon_lineardrive`, rename, adjust".

### 0.6.2 Three firmware stacks, and VertiGate is on the newest

The `aeon_lineardrive` README says: *"Pin this commit; the current version of microharp is an
incompatible rewrite."* In detail:

| Generation | Framework | MicroPython | USB / sync | Used by |
| --- | --- | --- | --- | --- |
| 1 | `SainsburyWellcomeCentre/microharp` | SWC fork `v1.18-swc` | frozen `usbcdc` + `harpsync` modules | `virt-hunt-drv` |
| 2 | `micropython-microharp` @ `df88717c` (`HarpTypes`, `ReadWriteReg`) | SWC fork `v1.18-swc` | frozen modules | `aeon_lineardrive`, `fablabs-automatic-shelter` |
| 3 | `micropython-microharp` current (`add_u8`, `@on_write`, `CdcTransport`) | **stock** RP2350 build | `usb.device.cdc` via mip | **`aeon_vertigate`** |

VertiGate is the only device on generation 3. Generation 3 is the only one that runs on stock
MicroPython with no custom fork. That is a real strategic advantage and an argument for making
**VertiGate the template for the fleet**. But it also means VertiGate cannot reuse lineardrive's
*firmware*. It can reuse the repo layout, tooling and CI, which do not depend on the stack.

### 0.6.3 Conformance problems elsewhere in the estate

Worth knowing, because they set expectations for review, and because fixing VertiGate correctly
creates the pattern for fixing them:

- **`fablabs-automatic-shelter` puts application registers at addresses 15 to 26.** The spec is
  clear: *"Every application register MUST have an address equal to, or greater than, 32."*
  Those addresses collide with `R_TIMESTAMP_OFFSET` (15), `R_UID` (16), `R_TAG` (17),
  `R_HEARTBEAT` (18) and `R_VERSION` (19). Any standard Harp controller will misread this device.
  It also reports `whoAmI = 0x1234` and a device name of `"Feeder V2"`. Its README and
  `RELEASE_NOTE.md` are still unedited template placeholders.
- **`aeon_lineardrive` declares `whoAmI: 0000`** and still points at the old
  `harp-tech/reflex-generator` schema URL, which is older than the draft-02 URL VertiGate uses.
- **`virt-hunt-drv`** documents its register map as a README table. It has no `device.yml`, so
  no interface can be generated from it.

**No device in the SWC estate holds a registered WhoAmI.** None of them can be addressed in the
wider ecosystem today.

---

## 1. Identity and registry: blocking, do first

| Item | Status |
| --- | --- |
| `whoAmI: 5350` | **Not registered.** `harp-tech/whoami/whoami.yml` lists 46 devices; the highest id is 2110. Nothing in the 5000s. |
| Owner key for SWC | **Absent.** `owners:` has aind, champalimaud, harptech, neurogears, neurophotometrics, oeps. No SWC entry. |

One PR to `harp-tech/whoami` is needed. It adds an owner key (in alphabetical order) and the
device:

```yaml
owners:
  swc: &swc
    authors: SainsburyWellcomeCentre
    copyright: SainsburyWellcomeCentre

devices:
  3002:
    <<: *swc
    name: VertiGate
    repositoryUrl: https://github.com/SainsburyWellcomeCentre/aeon_vertigate
    projectUrl: <fablabs documentation page>
```

`name` must match `^[a-zA-Z][a-zA-Z0-9_]*$`. `VertiGate` is fine. The id pattern in
`whoami.json` accepts 3- and 4-digit values, so any id in the proposed range is valid. It only
needs to be claimed.

> **VertiGate's id changes.** The current `5350` is outside the proposed SWC range (§1.1). Taking
> the block moves VertiGate to an id inside it, `3002` above, subject to the teams' own
> allocation. That touches `device.yml`, `main.py`, `bonsai/example.bonsai` and the README. It
> is cheap now, because nothing is released and no interface package exists. It is not cheap
> later.

**Until this PR merges, the id is squatted, not owned.**

**Precedent:** AIND added its own `aind` owner key and ten devices (1400 to 1411) pointing at
repositories in its own GitHub organisation. This is a routine PR. The registry is open to
external institutions on purpose, and SWC is already a known ecosystem partner. Expect this to
be the easiest external step in the whole plan.

### 1.1 Reserve a block, not a single id

As §0.6 shows, **no SWC device holds a registered WhoAmI**: `aeon_lineardrive` ships `0000`,
`fablabs-automatic-shelter` ships `0x1234` (4660), `virt-hunt-drv` sets none, and VertiGate
claims an unregistered 5350. Two of those placeholders are in active use, and `0x1234` is a
value another institution could be given.

Since one PR is being opened anyway, **register the whole SWC fleet at once**, not one id per
device. Follow AIND's 1400 to 1411 pattern, but sized for an institution with several groups
that build devices.

**Proposed reservation: `3000` to `3500` for SWC devices.**

The range is free. The registry's highest id is 2110 and nothing above it is assigned. It is
also well away from the Champalimaud clusters and from AIND's 1400s, so the existing owners can
still grow.

Initial allocations to propose in the same PR. Ids are assigned from 3000 in order of repository
creation date:

| Id | Device | Repo | Repo created |
| --- | --- | --- | --- |
| 3000 | `VirtHunt` | `virt-hunt-drv` (sets none today) | 2022-02 |
| 3001 | `LinearDrive` | `aeon_lineardrive` (ships `0000` today) | 2023-05 |
| 3002 | `VertiGate` | `aeon_vertigate` (was `fablabs-VertiGate`; ships 5350 today) | 2026-06 |

> **Decision (2026-09-17):** allocate by repository age, starting at 3000. `fablabs-automatic-shelter`
> is **not included**. It is not maintained, and its register map violates the spec (§0.6.3), so
> it would need a rewrite before a registered id is useful. It can take the next free id if that
> work happens. Note that `virt-hunt-drv` was last pushed in 2022-10, so it is the least active of
> the three that are included.

Two things to prepare for:

- **500 ids is a large ask.** AIND took twelve. Expect harp-tech to ask why. The honest answer
  is that SWC has several independent groups building Harp devices (FabLabs, Aeon, and others),
  and one block avoids a stream of small PRs and the placeholder ids that appear while people
  wait. If the maintainers push back, a smaller block that can grow later is a fine fallback.
  The important thing is to have *a* range, not scattered ids.
- **A reserved block needs an owner.** Blocks rot when nobody tracks them. Whoever holds it
  should keep a short allocation list, ideally in `fablabs-documentation`, so the next device
  takes the next free id instead of inventing another `0x1234`.

Confirm the range and the initial allocations with the Aeon and FabLabs teams before opening the
PR. The PR commits their devices too.

---

## 2. `device.yml`: schema and modelling gaps

### 2.1 Mechanical fixes

- **Old schema URL.** The file points at `draft-02`. The protocol repo now ships `draft-03`
  (`schema/device.json`, `core.json`, `registers.json`). Update it.
- **`access` is correct as it is.** An earlier draft said `Status` should be `[Read, Event]`
  and the settings `[Read, Write]`. The idea was to match the firmware flags `READ_ONLY | EVENT`
  and `READ_WRITE`. That was wrong. Checked on 2026-09-21:
  - The schema defines `access` as *"the expected use of the register"*.
  - The protocol makes every register readable.
  - The generator emits `ReadXAsync` for every register. It never checks the `Read` flag.
  - Only `Write` and `Event` change the output. `Write` adds `WriteXAsync`. `Event` adds the
    event operators.
  - No harp-tech device uses `[Read, Event]`. `device.behavior` uses plain `Event` for its four
    event registers and plain `Write` for its twenty settings.

  Keep the single-value form. The firmware access flags are a separate matter (§3.3).
- **Unused schema fields.** `defaultValue` (Speed 255, Torque 35, Offset 0), `volatile: false`
  on the three config registers, `minValue` / `maxValue` on Speed.
- **Units live only in the README** (1.2 mm/count, 0.38 mm/s, 0.36 kgf·mm, 25 µm). Put them in
  `description` so they reach the generated documentation and IntelliSense.
- **`hardwareTargets: "0.1"`** must match a real, versioned hardware revision (§7).

### 2.2 Register map redesign: the main design question

The current map works but does not follow convention. Nothing is released yet, so this is the
cheap moment to fix it.

Problems with the current map:

1. **`Operation` is a bad name.** It sounds like a sibling of core `R_OPERATION_CTRL` (address
   10). Every comparable Harp motion device uses a functional name. It is also **write-only, so
   the register dump skips it**. A controller that connects cannot learn the commanded target
   (§3.3).
2. **No position readback.** There is no way to ask where the gate is, only which state it is
   in. Comparable devices expose a measured value as an Event (`faststepper` has `Encoder`,
   `syringepump` has `Protocol`).
3. **No stop, no enable/disable, no re-home command.** `Gate.stop()` exists in firmware but
   cannot be reached over the wire. Homing happens once, at boot.
4. **No error or fault register.** Dynamixel stalls, comms timeouts and out-of-travel conditions
   are invisible to the host. The spec says such conditions should be an event on a dedicated
   register, not error replies.
5. **No way to switch event traffic off.** Once a `Position` event streams, a host that only
   wants end-stop transitions must filter it downstream. Harp devices provide an off switch:
   either a separate `EnableEvents` mask (`syringepump`, `stepperdriver`, `behavior`) or paired
   bits inside `Control` (`faststepper`).

Proposed map, using `faststepper` / `syringepump` naming:

| Addr | Name | Type | Access | Purpose |
| --- | --- | --- | --- | --- |
| 32 | `Control` | U8 | Write | bitmask, all 8 bits: `EnableMotor` / `DisableMotor`, `Stop`, `Calibrate`, `Enable`/`DisablePositionEvent`, `Enable`/`DisableTelemetryEvent` |
| 33 | `TargetPosition` | **U8** | Write | absolute target, same 1.2 mm scale. Firmware gains read access so it appears in the register dump |
| 34 | `GateState` | U8 | Event | groupMask `Idle` / `Up` / `Down` / `Moving` / `Calibrating` / `Error` (`0xFF`) |
| 35 | `Speed` | U8 | Write | as today, with default/min/max declared |
| 36 | `Torque` | U8 | Write | as today |
| 37 | `CalibrationOffset` | S8 | Write | renamed from `Offset`, per syringepump convention |
| 38 | `Position` | U16 | Event | *measured* position from the servo, in encoder counts (25 µm) |
| 39 | `MotorFault` | U8 | Event | bitmask: `Stall`, `Overload`, `CommsTimeout`, `TravelLimit` |
| 40 *(optional)* | `ServoTelemetry` | U16×n | Event | present current / temperature / voltage |

Keeping `Up` / `Down` as a convenience is fine. Express it as two `Control` bits next to the
position register.

> **Decision (2026-09-09): address 33 stays U8.** 1.2 mm is enough for this mechanism, so the
> target is not widened. This is what makes the whole map **purely additive on the wire**. Every
> existing register keeps its address and payload type. Only unused addresses gain registers.
> Existing Bonsai workflows keep working without changes.
>
> An earlier draft proposed U16 and called `0`/`255` "magic values" that the spec's *Register
> polymorphism* section forbids. That reasoning was wrong. `lower_down()` calls `move(0)`,
> `raise_up()` calls `move(255)`, and `move()` is a plain linear map. The endpoints are ordinary
> values on the same scale, and the special cases are only an idempotence guard.
>
> See [`REGISTER_MAP_COMPARISON.md`](REGISTER_MAP_COMPARISON.md) for the full implemented-vs-proposed
> analysis, the cost breakdown, and a reduced subset if less churn is wanted.

Whatever map is chosen, every register must be **dump-ready**: each `defaultValue` in
`device.yml` copied into register storage at construction, and `on_read` handlers on `Position`,
`GateState` and any telemetry register, so a read asks the servo instead of echoing the last
write. See §3.3 for why this is not optional.

**This decision needs sign-off before anything else proceeds.** The register map drives the
firmware, the generated interfaces, the Bonsai workflow, and the documentation.

---

## 3. Firmware conformance: bugs and gaps

Real defects in the current code:

- **S8 payloads are decoded as unsigned.** [`firmware/register.py:44-47`](../firmware/register.py#L44-L47)
  does `offset = payload[0]` on a memoryview, so a written `-10` arrives as `246`, and
  `max(min(246, 127), -128)` clamps it to `+127`. **Negative offsets are impossible today.**
  Needs `struct.unpack` or an explicit sign fix.
- **Reply payloads report values that were never applied.** The spec requires a `Write` reply to
  contain the actual register value after processing. `_torque` stores the raw byte and then
  applies `val & 0x7F`. `_speed` stores the raw byte and then applies `vel & 0xFF` plus a `+60`
  offset. Write `200` to Torque and the device replies `200` while running at `72`. Either clamp
  before storing, or reject out-of-range writes with an error reply (spec case 5 allows this).
- **Version registers are wrong.** [`firmware/main.py`](../firmware/main.py) passes `who_am_i`
  and `device_name` but not `fw_version` / `hw_version`, so microharp defaults to `(1,0)` /
  `(1,0)` while `device.yml` declares `0.1` / `0.1`. `R_HW_VERSION_H/L`, `R_FW_VERSION_H/L` and
  bytes 3 to 8 of `R_VERSION` are all wrong.
- **`R_VERSION` PROTOCOL / CORE_ID / INTERFACE_HASH are zero.** microharp leaves them at the spec
  defaults. `INTERFACE_HASH` is the SHA-1 of `device.yml`. Leaving it zero tells controllers to
  skip schema validation, which is the feature that makes a Harp device self-describing. Needs a
  build step that computes the digest and bakes it in, plus a three-character `CORE_ID` for the
  MicroPython core.
- **Boot can hang before USB enumeration.** `Gate.__init__` runs `_calibrate_home()` with
  blocking `time.sleep` in a `while True` loop with no timeout, *before* `device.run()`. A
  missing or unresponsive Dynamixel means the board never enumerates and looks bricked. Needs a
  timeout and a fault state. Better: move homing behind an explicit `Control.Calibrate` command
  so the device always comes up on the bus.
- **Stale `_ismoving` after a new command.** `move()` cancels the running `_run()` task. The
  cancelled task never runs `_disable()`, so state can be left inconsistent. The `isr.set()` /
  `clear()` pattern in [`firmware/task.py`](../firmware/task.py) can also merge two quick
  transitions into one event.
- **Torque and Speed setters switch `torque_enabled` off and on.** Writing Speed while the gate
  is holding will drop the gate. Document this, or make the setters wait while the gate is
  holding position.
- **No non-volatile settings.** `R_RESET_DEV` bits `RST_DEF` / `RST_EE` / `SAVE` / `BOOT_DEF` /
  `BOOT_EE` are specified for saving configuration. microharp's handler only calls
  `machine.reset()` on any non-zero write. Speed, Torque and CalibrationOffset are per-rig
  calibration values, so saving them is worth having.
- **`R_CLOCK_CONFIG` is a plain R/W byte** in microharp, with no `CLK_GEN` / `CLK_REP` / lock
  behaviour behind it. Check what the sync UART actually does before claiming clock-sync
  conformance.
- **The register dump omits write-only registers.** `dispatch.py`'s `_dump_all_registers()`
  skips any register without `READ_ONLY` access. The spec says the dump carries *"the current
  contents of all core and application registers"* and that even optional and deprecated
  registers "MUST be included". VertiGate's `Operation` register is write-only, so it is missing
  from the dump. See §3.3.

Several of these are **upstream `micropython-microharp` work** that helps every future SWC
MicroPython Harp device: `SAVE` / `RST_EE`, the `R_VERSION` hash and core id, clock config, and
the write-only dump gap. Budget them there, not here.

### 3.1 Set the conformance bar against AIND

Before investing too much here: AIND's `harp.core.pico`, the C++ core in every AIND production
device, enumerates core registers only up to `TAG = 17`. It implements **neither `R_HEARTBEAT`
(18) nor `R_VERSION` (19)**.

`micropython-microharp` already implements both, including the full 32-byte `R_VERSION` layout.
So on core-register coverage VertiGate is *ahead of* the most active reference core, not behind
it. Upstream `harp-tech/core.pico` does go to 19. It fills protocol, firmware, hardware and
`CORE_ID = 'rpi'`, and takes `INTERFACE_HASH` as an array supplied by the caller. But nothing
pushed in its examples or in `device.hobgoblin` computes that hash (the first attempt is on an
unpushed branch, `core.pico#64`), and `core.atxmega` leaves it zero. The `INTERFACE_HASH` gap in
§3 is therefore shared by every shipped core, not a VertiGate problem. It is not an admission
requirement and should not block Phases 1 to 5.

The items that matter for conformance are the ones that put *wrong data on the wire*: the S8
decode bug, the reply-value mismatches, and the version registers that disagree with
`device.yml`.

### 3.2 Strategic choice: stay on MicroPython, or port to `harp.core.pico`?

AIND's `harp.core.pico` targets **RP2040 and RP2350**, the same silicon family as VertiGate's
RP2354. A C++ port is a real option.

| | **Stay on `micropython-microharp`** | **Port to `harp.core.pico`** |
| --- | --- | --- |
| Effort | zero, already working | full firmware rewrite, plus a Dynamixel driver in C++ |
| Core-register coverage | better (0 to 19) | worse (0 to 17) |
| Ecosystem familiarity | none, no MicroPython Harp device exists | high, nine AIND devices + hobgoblin |
| Toolchain | `mpremote`, no build step | Pico SDK + CMake, submodules |
| Firmware update path | `mpremote` (not regulator-compatible) | UF2 via BOOTSEL, matches the AIND release convention |
| Timing determinism | GC pauses, interpreted | deterministic, dual-core |
| Maintenance | SWC owns the whole stack | shared upstream core |

**Recommendation: stay on MicroPython.** The core-register argument is in your favour, the
Dynamixel driver already exists in MicroPython, and a rewrite would use the whole budget of this
migration while changing nothing a Bonsai user can see. Revisit only if gate timing jitter turns
out to matter in experiments, or if firmware distribution to non-developers becomes a real
problem (the UF2 story is better on the C++ side).

### 3.3 Register dump: the mechanism works, the payloads do not

Harp controllers read a device's whole state when they connect. The **controller asks for it**:
it writes `R_OPERATION_CTRL` with the **DUMP** bit (bit 3) set. Per `Device.md`, the device
*"SHALL send a sequence of `Read` messages to the Controller, one per register, with the current
contents of all core and application registers"*, after the write reply. `Bonsai.Harp`'s
`Device` operator sets `DumpRegisters = true` in its constructor, so every Bonsai workflow does
this at startup by default. [`bonsai/example.bonsai`](../bonsai/example.bonsai) already has it
enabled. `harp-tech/core.pico` implements the device side in `harp_core.cpp` (masks DUMP out of
stored state, sends one READ per core register, then calls `dump_app_registers()`).

**The mechanism is fine.** `micropython-microharp` implements DUMP correctly in `dispatch.py`:
write reply first, then `_dump_all_registers()` sends one READ per register, each with its own
timestamp, then clears the bit. It also calls `on_read` handlers.

**The payloads are wrong.** In [`firmware/register.py:14-18`](../firmware/register.py#L14-L18)
all five application registers are created with no initial value and **no `on_read` handler**,
and `RegisterEntry.storage` is a zeroed `bytearray`. A dump right after boot reports:

| Register | Dump reports | Actual device state |
| --- | --- | --- |
| `Operation` 0x21 | **omitted**, microharp skips write-only registers | — |
| `Status` 0x22 | `0` (Idle) | the gate is physically **down** after `_calibrate_home()`, but `_isdown` is never set during calibration |
| `Speed` 0x23 | `0` | `VEL_DEFAULT` = 255 |
| `Torque` 0x24 | `0` | `TRQ_DEFAULT` = 35 |
| `Offset` 0x25 | `0` | 0, correct by luck |

Two separate root causes:

1. **Defaults are applied to the servo but never copied into register storage.** `Gate.__init__`
   sets `self.speed = VEL_DEFAULT` and `self.torque = TRQ_DEFAULT` on the Dynamixel. The matching
   `RegisterEntry.storage` bytes stay at zero.
2. **No `on_read` handlers, so a dump never asks the servo.** It can only echo what the host last
   wrote. Later in a session, `Speed` and `Torque` still report the raw written byte, not the
   masked or offset value in use. This is the same root cause as the reply-value mismatch in §3.

**Why this matters more than it looks.** A workflow that uses the startup dump to fill its UI or
to log rig configuration will silently record `Speed=0, Torque=0, Status=Idle` for a device
running at 255/35 and sitting at the bottom of its travel. No error is raised. It is wrong data
in the experimental record. Fix it together with the register redesign (§2.2). The cost is
setting storage at construction plus a few `on_read` handlers.

### 3.4 Version registers: what tooling actually reads

The two version problems in §3 are **not equally urgent**. The difference only shows once you
check what reads each field.

#### The deprecated block is what everything reads

`Bonsai.Harp`'s `Device` operator reads registers 0, 1, 2, 6 and 7 on every connect and prints
them to the Bonsai console. `Bonsai.Harp.Design`'s Device Setup dialog shows the same block.
Nothing in `bonsai-rx/harp` references `R_VERSION` (19) or its interface hash, and `HarpVersion`
is major.minor only.

So the **deprecated** registers are the live ones in practice. Side by side with a current
harp-tech device (`OutputExpander`, WhoAmI 1108):

| Device Setup field | Register(s) | OutputExpander | VertiGate today | Should be |
| --- | --- | --- | --- | --- |
| DeviceName | 12 | Output Expander | VertiGate | ✓ |
| FirmwareVersion | 6, 7 | 2.2 | **1.0** | 0.1 |
| CoreVersion | 4, 5 | 1.13 | **0.0** | 1.13 |
| HardwareVersion | 1, 2 | 1.0 | **1.0** | 0.1 |
| AssemblyVersion | 3 | 0 | 0 | ✓, deprecated, 0 is normal |
| WhoAmI | 0 | 1108 | 5350 | ✓ once registered (§1) |
| SerialNumber | 13 | 65535 | 0 | — |

Three of seven fields are wrong or blank. They are the fields a person reads when identifying a
device on a rig.

**`CoreVersion` (registers 4 and 5)** is the version of the Harp *core library* the firmware is
built on. Formally that is not the protocol version. But Champalimaud's core versions follow the
protocol document, so in practice a device that reports `1.13` says it implements Harp Device
spec **v1.13.0**, the current and only tag on `harp-tech/protocol`. Set VertiGate's to `1.13`
to match that reading, not to microharp's own release number.

> That is the ATxmega convention, not a universal one. `harp-tech/core.pico` fills registers 4
> and 5 from its `HARP_PROTOCOL = {2, 0, 0}` constant, the protocol *draft* it targets. Its own
> library version (`PICO_CORE_VERSION = 1.1.1`) is not on the wire at all. So a Pico-based device
> reports `2.0` here and an ATxmega one reports `1.13`, for the same field. `1.13` is still the
> right choice for VertiGate (it matches the only tagged spec), but expect the question.

#### Fixes

- **`fw_version` / `hw_version`:** pass `fw_version=(0, 1)`, `hw_version=(0, 1)` to
  `HarpDevice(...)`. One line. Otherwise microharp defaults both to `(1, 0)`.
- **`CoreVersion`:** awkward. `install_common_registers` has **no parameter for it**, unlike the
  firmware and hardware versions. Either add the argument upstream, or write registers 4 and 5
  directly after construction.
- **Stop maintaining versions by hand in two files.** `device.yml` and `main.py` drifting apart
  is how this happened. Generate `firmware/_version.py` from `device.yml` at deploy or CI time
  and guard it with the same freshness gate as the C# interface (§6).

#### `R_VERSION` PROTOCOL / CORE_ID / INTERFACE_HASH: one consumer, no validator

Worth doing eventually. `Bonsai.Harp` does not read these fields. `harp.toolkit`'s newer
`Verify` suite (`Verify/Suites/CoreRegisters/R_VERSION.cs`, not in the local clone) does: it
reports PROTOCOL / FIRMWARE / HARDWARE / CORE_ID and prints `INTERFACE_HASH` as hex in the order
received. It does not compare the hash against `device.yml`. Each field still has an open
question:

- **PROTOCOL** (bytes 0 to 2): `1.13.0`. A microharp constant, not per device.
- **CORE_ID** (bytes 9 to 11): three characters naming the core. **There is no registry, but
  there is precedent.** `core.atxmega` writes `'ATX'` and `harp-tech/core.pico` writes `'rpi'`
  (`RPI_CORE_ID` in `harp_core.h`). Neither asked anyone. *(An earlier draft said no shipped core
  implements `R_VERSION`. That was wrong for `harp-tech/core.pico`, whose `main` goes up to
  `VERSION = 19`. AIND's fork is the one that stops at `TAG = 17`.)* Pick `'mpy'` for microharp
  and record it in the README. No upstream conversation needed.
- **INTERFACE_HASH** (bytes 12 to 31): SHA-1 of `device.yml`. Three traps:
  - (a) `device.yml` is not on the board, so the hash must be computed at build time into the
    generated version module.
  - (b) **Byte order: resolved by `protocol#233`** (glopesdev, 2026-09-16, open at time of
    writing). The spec said "little-endian", which has no meaning for a 20-byte digest. The PR
    deletes that sentence, limits the little-endian rule to each multi-byte value (arrays are
    never reordered), and lets the byte-indexed `R_VERSION` diagram define the layout: digest
    bytes at 12 to 31 in produced order, that is `sha1sum` order. `harp.toolkit`'s verifier
    already reads them that way. Before the PR, no implementation could settle this.
    `core.atxmega` zeroes bytes 12 to 31. `core.pico` takes the array from the caller, and its
    shipped examples pass a git *commit* hash into the slot. The first real computation
    (`core.pico#64`, closed 2026-09-11, CMake + `add_definitions`) is on a branch that is not
    pushed anywhere findable.
  - (c) **Input bytes: proposal open, `protocol#234`** (glopesdev, 2026-09-17). Digest over the
    file as UTF-8, no BOM, LF. Comments, key order and anchors stay significant.
    `harp-tech/generators` computes it and emits it to both the firmware and the client
    interface. He reproduced the CRLF/LF split on `device.behavior` (`e1cae0…` vs `f5cf13…`, same
    commit) and rejected the git blob id (a third value, because git prepends `blob <len>\0`).
    **Gap to raise from VertiGate:** "emits a firmware header" assumes C firmware. MicroPython
    devices have no build step and `device.yml` is not on the board. The generator must also emit
    the 20 bytes in a language-neutral form (Python module, JSON, or toolkit output) for a deploy
    script to bake in. That is the `_version.py` step below. VertiGate briefly had a
    `device.yml text eol=lf` pin in `.gitattributes`. It was **dropped at the Harp maintainer's
    request** in favour of the plain prefect reference, since `#234` normalises at hash time.
    Consequence: a plain `sha1sum` of a Windows working tree will not match the generator's
    digest. Always take the value from the generator. Never compute it by hand.

> **Separate finding, larger than the hash.** `harp-tech/python`'s `register_models.py` puts
> `Version` at address **35** with protocol `2.0.0`. `core.pico` declares
> `HARP_PROTOCOL = 2.0.0`. `harp.toolkit`'s verifier checks against a `PrereleaseMajorVersion`.
> Poofjunior in `core.pico#64`: *"long term, the register numbers will be updated and redundant
> registers will be deleted."* A **protocol v2 that renumbers core registers is in progress**.
> This changes nothing in Phases 1 to 5. v1.13 is the only tagged spec and `Bonsai.Harp` reads
> the deprecated block. But it means microharp's core register table will need a v2 mode one
> day, and it is worth asking harp-tech about the timeline before investing in the `R_VERSION`
> extras (§3.4 order, steps 5 and 6).

##### The line-ending trap is ecosystem-wide, not VertiGate's

Checked on 2026-09-16: none of `device.faststepper`, `device.outputexpander`,
`device.clocksynchronizer`, `device.template`, `protocol`, `core.pico` or `core.atxmega` has a
`.gitattributes`. `device.hobgoblin` has `* text=auto` only. `bonsai-rx/prefect`'s
`reference-harp/.gitattributes`, the template every harp-tech device repo is checked against,
is `* text=auto` / `*.cs text` / `*.csproj text`. `text=auto` normalises the *index* but leaves
the working tree to each machine's `core.autocrlf`. On a default Git for Windows install,
`git ls-files --eol device.yml` in those device repos reports `i/lf w/crlf`. Any hash computed
from that working tree differs from the same commit hashed on Linux or CI.

prefect issue `#56` already pins `charset = utf-8` (no BOM) for YAML in `.editorconfig` and says
`end_of_line` is left to `.gitattributes`. `.gitattributes` then does not set it.

**The whole gap was picked up upstream within a day of being raised informally**, as three
linked items: `protocol#233` (byte layout), `protocol#234` (input bytes: UTF-8, no BOM, LF; the
generator is the single implementation), and `generators#142` (implementation: compute in the
read path, which is currently duplicated between `TemplateHelper` and the toolkit's
`GeneratorHelper`, and emit a C# constant, a Python constant, and a C firmware header). What is
left to send:

| Target | Status | What is left |
| --- | --- | --- |
| `harp-tech/generators#142` | open | a fourth consumer: MicroPython firmware. None of the three emit targets fits (no compiler; the Python target is the Controller module). Ask for an import-free `interface_hash.py`, a hex string in the provenance header, or a toolkit print, whichever is cheapest |
| `bonsai-rx/prefect` `.gitattributes` question | **withdrawn** | the maintainer asked for the reference `.gitattributes` to stay as it is. `#234`'s normalisation makes the pin unnecessary |

Also note that `device.yml`'s `firmwareVersion` schema is major.minor only, while `R_VERSION`
wants major.minor.patch. The patch bytes have no source in the schema. Either fix them at `0`,
or take them from the release tag.

#### Order

1. Pass `fw_version` / `hw_version`. Fixes what Bonsai reads, prints and displays.
2. Set `CoreVersion` to `1.13`.
3. ~~Add the `.gitattributes` LF rule for `device.yml`~~. **Dropped** at the maintainer's
   request. Prefect reference only.
4. Comment on `generators#142` with the MicroPython data point (drafted, see above). The
   `.gitattributes` and byte-order questions are already answered by `#233` / `#234`.
5. Generate `_version.py` and wire the freshness gate. Take the digest from whatever `#234` and
   `harp-tech/generators` settle on. Do not invent a local rule.
6. Extend microharp to accept core version, protocol, core id (`'mpy'`), hash and patch
   versions. Fleet-wide benefit, per the upstream split in §3.

Steps 1 to 4 are worth doing in any case. Steps 5 and 6 only pay off once something validates
the hash, and step 6 should wait for the protocol issue to settle the hash definition.

---

## 4. Generated interfaces: missing

This is what makes a device a *harp-tech* device rather than a device that only speaks Harp. Two
artifacts are generated from `device.yml`:

### Bonsai / C# package

Reference implementation: `device.hobgoblin`. A `Generators/Generators.csproj` references
`Harp.Generators` (0.4.0) and drives T4 templates. Output goes to
`Interface/<Namespace>/{Device,AsyncDevice}.Generated.cs`, packaged as
`<PackageType>Dependency;BonsaiLibrary</PackageType>` against `Bonsai.Harp` 3.6.1, targeting
`net462;netstandard2.0`, with `device.yml` embedded as a resource. Generated code is
**checked in**, and CI fails if it is stale.

Simpler alternative: the `harp.toolkit` dotnet tool exposes `generate interface`,
`generate python-interface` and `generate register-metadata` directly, with no T4 or MSBuild
scaffolding.

**Recommendation: the toolkit route. Proven both by AIND and inside SWC.**
`harp.device.cuttlefish` has no `Generators/` project. It pins the tool in a manifest instead.
**`aeon_lineardrive` pins the same tool at the same version** in `.config/dotnet-tools.json`, so
this is already the de facto SWC standard:

```json
{ "version": 1, "isRoot": true,
  "tools": { "harp.toolkit": { "version": "0.2.2",
             "commands": ["harp.toolkit"], "rollForward": false } } }
```

It commits the resulting `Device.Generated.cs` / `AsyncDevice.Generated.cs`. That is much less
machinery than the hobgoblin T4 pipeline, and it is what a MicroPython device (with no C firmware
to generate) actually needs.

Skip `ios.yml` / `Firmware.tt` entirely. That generator targets ATxmega and Pico C firmware and
does not apply here.

### Naming and distribution: a decision, not a default

| | harp-tech style | AIND style | **SWC precedent (`aeon_lineardrive`)** |
| --- | --- | --- | --- |
| Namespace / package | `Harp.VertiGate` | `AllenNeuralDynamics.Cuttlefish` | **`Aeon.LinearDrive`** |
| Location in repo | `Interface/` | `software/bonsai/Interface/` | **`software/<Namespace>/`** |
| Publishing | individual NuGet package | umbrella repo (`Bonsai.AllenNeuralDynamics`) | individual, via the shared workflow |

The `Harp.*` namespace implies a harp-tech-org device. AIND avoided it on purpose, and so did
Aeon. The in-house precedent uses a **project or programme name**, not the institution name:
`Aeon.LinearDrive`, not `SainsburyWellcomeCentre.LinearDrive`.

Applying that convention gives **`Aeon.VertiGate`** in `software/Aeon.VertiGate/`. It has the
same form as `Aeon.LinearDrive` and matches the repository's `aeon_` prefix.

> **Decision (2026-09-17):** the repository was renamed from `fablabs-VertiGate` to
> `aeon_vertigate`, placing the device under the Aeon programme. An earlier draft proposed
> `Fablabs.VertiGate` because of the `fablabs-*` prefix. That reasoning now points the other way.
> `Aeon.VertiGate` also needs no new convention. It reuses the one `aeon_lineardrive` already
> set, including its `software/build/*.props` and workflow, unchanged.

Note that the AIND csproj also sets `GeneratePackageOnBuild` on Release and pins `Bonsai.Harp`
3.5.0 (hobgoblin uses 3.6.1). Take the newer.

### Python package

Two options, and they are not equivalent:

- **`harp-tech/python`**: `PyDevice.tt` / `harp.toolkit generate python-interface` emits a typed
  module that imports from `harp.protocol`. Generated, typed, stays in sync with `device.yml`.
- **`AllenNeuralDynamics/pyharp`**: AIND's own implementation. Cuttlefish ships
  `software/pyharp/*.py` as **hand-written example scripts**, not a generated interface.

**Recommendation: generate against `harp-tech/python`.** It is derived from `device.yml`, so it
cannot drift, and it also covers reading recorded binary data. Optionally add a few hand-written
`pyharp`-style scripts as usage examples. That part of the AIND pattern is worth copying.

### Downstream consequence

The current Bonsai workflow hard-codes `Address 33`, `PayloadType U8` in raw `CreateMessage` /
`Format` nodes, with `PortName COM21` fixed. With a generated package those become typed,
discoverable operators.

---

## 5. Repository structure

VertiGate is currently a flat `firmware/` + `bonsai/`. There are two established target layouts.

**Option A: harp-tech (`device.template`, hobgoblin, behavior):**

```
Assets/            device photo, pinout diagrams, PCB render
Firmware/          MicroPython application (today's firmware/, moved)
Hardware/
  PCB/             KiCad; fablabs-kicad-library already exists
  Mechanical/      gate assembly CAD, STEP/DXF
Interface/         generated Bonsai package + .sln + csproj
Generators/        (or a toolkit invocation script)
device.yml
README.md
global.json
.github/workflows/
```

**Option B: AIND (`harp.device.cuttlefish`, `harp.device.pico-template`):** lowercase
`assets/ firmware/ hardware/{board,mechanical}/ software/bonsai/Interface/` + `device.yml`.

**Option C: `aeon_lineardrive`, the in-house hybrid *(recommended)*:**

```
.config/dotnet-tools.json    pins harp.toolkit 0.2.2
.github/workflows/           the shared Harp device workflow
.img/                        FabLabs house convention: README images
device.yml
firmware/                    MicroPython application (stays where it is)
hardware/                    git submodule: the whole hardware design, own repo
software/
  Aeon.VertiGate/            generated Device.Generated.cs + csproj + README
  build/                     shared Bonsai Foundation props
  Aeon.VertiGate.sln
  Directory.Build.props
LICENSE
README.md
RELEASE_NOTE.md              FabLabs house convention
altium-viewer.json           FabLabs house convention
global.json
CITATION.cff
```

**Why Option C.** It is the only layout that satisfies all three groups at once. It keeps the
lowercase folders VertiGate already has. It adopts the SWC FabLabs hardware conventions (`.img/`,
`eCAD/`, `mCAD/`, `RELEASE_NOTE.md`, `altium-viewer.json`, used across
`fablabs-automatic-shelter`, `-valve-driver`, `-lick-detector-piezo`, `-monitor-blanking`,
`-environmental-sensor`). And it carries the harp-tech software pipeline in `software/` with
generated code and CI. It exists, it works, and colleagues maintain it.

Note that VertiGate currently has **none** of the FabLabs hardware-side items: no `.img/`, no
`eCAD/`, no `mCAD/`, no `RELEASE_NOTE.md`, no `altium-viewer.json`. It is the only `fablabs-*`
repo without them.

**Altium vs KiCad:** every existing `fablabs-*` and Aeon board is Altium (`.PcbDoc`/`.SchDoc`),
published through the Altium 365 Viewer via `fablabs-documentation`. But `fablabs-kicad-library`
("global KiCAD library for all PCB projects") is active. Decide which one VertiGate targets
before the hardware repository is filled. A migration may be under way, and this is a
FabLabs-wide call, not a VertiGate one.

### Hardware as a submodule

**Proposal: the whole hardware design lives in its own repository, included here as a git
submodule at `hardware/`. This repository then contains only firmware, host software and
metadata.**

Why this split is better:

- **The licence boundary becomes a repository boundary.** This repo is BSD-3, nothing else. The
  hardware repo carries CERN-OHL-W and whatever component terms apply. No licence map, no
  per-directory `LICENSE` files, no prose explaining which paragraph applies to which folder.
- **Hardware and firmware version independently.** They already do. AIND's release convention
  encodes `hw{major}.{minor}.{patch}-fw{major}.{minor}.{patch}` precisely because they move at
  different rates. Separate repos make that natural instead of something the release title has
  to explain.
- **The pin is a compatibility record.** A submodule pinned at a commit states, in a
  machine-checkable way, which hardware revision a given firmware was tested against. For a lab
  device with several board revisions in use, that is worth more than the convenience it costs.
- **Binary CAD stays out of the firmware history.** Altium and Inventor files are large and
  cannot be diffed. Software contributors who clone for a firmware fix do not pay for them.

#### Constraint: submodules cannot be subdirectories

A git submodule brings in a whole repository, not a path inside one. So "`hardware/` is a
submodule" rules out one shared `fablabs-hardware` repo with every device in it. That would put
every device's CAD into VertiGate's `hardware/`.

The workable shapes are:

| Shape | Implication |
| --- | --- |
| **One hardware repo per device** (e.g. `aeon_vertigate-hardware`) | ✅ clean pin, clean licence boundary. Twice the repo count across the estate. |
| Shared repo with *only* reusable component models | ✅ works, but then per-device CAD stays in the device repo, which is not what is proposed here |
| Shared repo with all devices' hardware | ❌ cannot be expressed as a submodule at `hardware/` |

So this means **one hardware repo per device**. Check that the FabLabs team is happy with about
twice the number of repositories before committing to it.

#### What this differs from

Both existing SWC conventions keep hardware in the device repo. Every `fablabs-*` repo has
`eCAD/` and `mCAD/` next to `firmware/`, and so does `aeon_lineardrive`. This is a FabLabs-wide
call, not a VertiGate one. VertiGate is a convenient place to try it because it has no hardware
files yet.

Three practical points to plan for:

- `git clone --recursive`, or an empty `hardware/` and a confused colleague. Worth a line in the
  README and in CI checkout steps.
- `altium-viewer.json` sits at the repo root in the `fablabs-*` repos, and the Altium 365 Viewer
  integration via `fablabs-documentation` points at a repository. Check what moves with the CAD.
- Releases split into two streams. AIND already solves this: each firmware release states the
  hardware revisions it is compatible with. Adopt that wording rather than inventing one.

#### The provenance rule still applies, wherever the files live

A submodule changes *where* files are hosted, not *whether* SWC distributes them. A public
hardware repo with SamacSys or TraceParts models carries the same exposure, only in a different
place. So the split is still by provenance:

| Model | Where it goes |
| --- | --- |
| SWC's own design and component models | the hardware repo, under CERN-OHL-W |
| Redistributable third-party (official vendor STEP, models with an explicit grant such as CC BY-ND) | the hardware repo, with attribution kept |
| Portal-sourced, non-transferable (SamacSys, TraceParts, GrabCAD, Ultra Librarian) | **nowhere in git**. Referenced by MPN as CERN-OHL *Available Components* |

Moving encumbered files into a separate repository does not make distributing them lawful. It
only makes the audit a one-time job. `fablabs-kicad-library` is the existing precedent for shared
component assets and could hold the redistributable ones.

### Licensing: adopt the Aeon model (CERN-OHL), not the FabLabs CC BY-SA convention

Two SWC conventions currently differ, and VertiGate has to pick one before it publishes any
hardware.

| | FabLabs today | Aeon proposal ([`aeon_roadmap#69`](https://github.com/SainsburyWellcomeCentre/aeon_roadmap/issues/69)) |
| --- | --- | --- |
| Hardware | **CC BY-SA 4.0**, full text as the single root `LICENSE` | **CERN-OHL-W 2.0** |
| Software / firmware | BSD-3 (stated in the README only) | BSD-3 |
| Third-party vendor CAD | bundled in the repo | **Available Components**: referenced by MPN, not redistributed |

`fablabs-valve-driver`, `-automatic-shelter`, `-lick-detector-piezo` and `-environmental-sensor`
all carry the CC BY-SA 4.0 text as their root `LICENSE`.

**Decision: follow the Aeon model.** CC BY-SA is a poor fit for hardware for four reasons:

1. **It does not define "source" for hardware.** ShareAlike applies to "Adapted Material", but CC
   has no answer to whether a fabricated board, or a Gerber, is an adaptation of a schematic.
   CERN-OHL defines *Covered Source* and *Product* explicitly and says when reciprocity applies
   to a manufactured object.
2. **No patent grant.** That is the difference between "you may copy my drawings" and "you may
   build and sell the thing". CERN-OHL includes one.
3. **Creative Commons itself advises against it** for software, and points hardware projects to
   purpose-built licences.
4. **No Available Components concept.** This is the formal basis for referencing proprietary
   vendor CAD without redistributing it. `aeon_roadmap#69` depends on it, and CC BY-SA does not
   have it.

**Variant: CERN-OHL-W**, matching the Aeon default. Reciprocal on the design files, while a rig
that only *uses* a VertiGate is not affected. `-S` would be awkward for a device embedded in
larger setups. `-P` gives away reciprocity for no benefit here.

#### How the two licences relate

Neither is a subset of the other, and they are **not compatible**. Each grants and requires
things the other does not:

| | CC BY-SA 4.0 | CERN-OHL-W 2.0 |
| --- | --- | --- |
| Attribution | ✅ | ✅ |
| Copyleft / reciprocity | ✅ on "Adapted Material" | ✅ on conveying a **Product** |
| **Patent licence** | ❌ **explicitly excluded**. §2(b)(2): *"Patent and trademark rights are not licensed under this Public License"* | ✅ §7.1: *"perpetual, worldwide… irrevocable patent license to Make, have Made, use, offer to sell, sell, import"* |
| Defined "Source" for hardware | ❌ no concept | ✅ Covered Source / Complete Source |
| Available Components | ❌ none | ✅ parts available *"with sufficient rights and information… to enable it to be Made… or sourced and used to Make the Product"* |
| Obligation attaches to physical objects | ❌ unclear. Copyright is in the drawing, not the thing built from it | ✅ §3.2 / §4.1, triggered by conveying a Product |
| Sui generis database rights | ✅ §4 | ❌ |
| Anti-DRM / TPM clause | ✅ | ❌ |
| Moral rights waiver | ✅ | ❌ |

CERN-OHL is stronger on the hardware-specific points. CC BY-SA is broader on general copyright
points. They overlap in places but neither contains the other.

CC BY-SA 4.0 has a "Compatible License" mechanism, but Creative Commons lists only specific
licences under it (GPLv3, one-way), and **CERN-OHL is not among them**. So CC BY-SA material
cannot be absorbed into a CERN-OHL project, and the reverse is also not possible.

**What that means for migrating the FabLabs estate.** A copyright holder is not bound by the
licence it chose before. Where SWC authored the designs, SWC can license future versions under
CERN-OHL-W regardless of what shipped before. Two caveats:

1. **CC licences are irrevocable.** Anything already published under CC BY-SA stays available
   under CC BY-SA. The licence changes going *forward*. Past releases cannot be taken back.
2. **External contributions need consent.** If anyone outside SWC contributed hardware design to
   those repos, relicensing their contribution needs their agreement. Check contributor lists
   before announcing a change.

For VertiGate this does not apply. No hardware files exist, so there is nothing to relicense.

**It is also not one-or-the-other per repository.** CERN-OHL governs *design* files. CC BY-SA is
still a good choice for documentation, photos and diagrams. That is why the target below is a
licence **map**, not a single root `LICENSE`.

> This is a licence reading, not legal advice. UCL's research office should confirm before
> anything is announced across repositories.

#### Immediate defect, independent of the above

VertiGate is the only `fablabs-*` repo with **no hardware files at all**. Its root `LICENSE` is
BSD 3-Clause, but the README badge said CC BY-SA 4.0. The badge advertised a licence for content
that does not exist, and misrepresented the licence on the content that does. **Fixed on
2026-09-17**: the badge now says BSD-3-Clause. Revisit when hardware lands.

#### Target structure, when hardware lands (Phase 6)

With hardware in its own repository (see "Hardware as a submodule" above), the licence map
mostly disappears. The repository boundary carries it instead:

**This repository:**

```
LICENSE          BSD-3-Clause: firmware, host software, device.yml
hardware/        submodule; governed entirely by the hardware repo's own terms
```

**The hardware repository:**

```
LICENSE          CERN-OHL-W-2.0: the design we authored
mCAD/README.md   Available Components: MPN + vendor download link per part
```

This is the main practical argument for the split. Instead of per-directory `LICENSE` files and
a root map explaining which paragraph applies to which folder, each repository has one licence
and says so once. Documentation, photos and diagrams can stay CC BY-SA in either repo if that is
preferred. That choice no longer has to be encoded in a map.

Plus SPDX headers, and a standing rule never to commit portal-sourced CAD.

Note the argument in `aeon_roadmap#69` that **having no licence does not fix this**. Leaving
hardware unlicensed until someone decides still distributes any third-party files, and leaves
SWC's own PCB work all-rights-reserved. So this is decided *before* hardware is published, not
after. It has the same cheap-now, expensive-later shape as the register map.

#### Worth flagging to the FabLabs team

The third-party CAD problem may already exist across the estate. Four published repos carry
vendor CAD under `ConvertedComponents/`:

| Repo | Files |
| --- | --- |
| `fablabs-monitor-blanking` | 50 |
| `fablabs-lick-detector-piezo` | 39 |
| `fablabs-valve-driver` | 19 |
| `fablabs-environmental-sensor` | 18 |

The filenames carry `CMP-xxx-xxxx-x` identifiers, which is SamacSys / Component Search Engine
numbering, next to vendor part numbers such as TE's `BNC-TE-5227222` and Samtec's
`853-004-213R00Y`. Those are the portals `aeon_roadmap#69` identifies as granting
use-in-your-own-design rights only.

This is an inference from filenames, not an audit. It needs checking, not acting on. But if it
holds, the position is worse than `aeon_lineardrive`'s was. A single root CC BY-SA does not only
redistribute those files. It claims to **license them share-alike to the public**, which
overclaims rights on third-party IP. That is the second mistake `aeon_roadmap#69` names.

VertiGate's advantage is that it is empty. It can adopt the right structure from the start
instead of fixing things later, which makes it a reasonable pilot for whatever FabLabs decides.
The decision belongs to the team, and probably to UCL's research office.

Keep `bonsai/example.bonsai`, but move it (`software/bonsai/` or `examples/`) and remove the
hard-coded `COM21` port. `aeon_lineardrive` also ships a `.bonsai/` directory with
`Bonsai.config` + `NuGet.config`, which pins the Bonsai environment and package feed for anyone
who runs the example. Worth copying.

---

## 6. CI/CD, versioning, release

Nothing exists today. The two ecosystems answer this very differently, and the AIND answer is
probably the right size for a lab device.

### Option A: harp-tech, heavy CI (`Harp.Hobgoblin.yml`)

- Triggers on push, PR and published release. `CiBuildVersion` comes from the release tag
  (`v*`), enforced by `Directory.Build.props` checks that **fail the build** if the tag and the
  assembly version disagree.
- Steps: set up .NET 8, install `dotnet-t4`, restore and build `Generators`, then
  **`git diff --exit-code` to prove the generated code was committed up to date**, then build,
  `dotnet pack`, upload artifacts, and publish to NuGet.org on release under a `public-release`
  environment.
- `harp-tech/configure-build` provides the shared Bonsai Foundation versioning action.

### Option B: AIND, no CI, strict release convention

AIND device repos have **no GitHub Actions workflows at all**. Instead `harp.device.pico-template`
specifies a release policy, which is arguably more valuable for a hardware device than a build
matrix:

- The release title encodes both versions: `hw{major}.{minor}.{patch}-fw{major}.{minor}.{patch}`
  (drop the `hw*` half for firmware-only releases, and the reverse).
- **Every hardware release attaches:** STEP file of the PCB, schematic PDF, Gerbers (logos
  removed), component position files, and the BOM.
- **Every firmware release attaches:** the compiled binary, and states which hardware revisions
  it is compatible with.
- The PCB silkscreen carries the part number with the hardware semantic version, plus a QR code
  linking to the repository.

### Option C: copy `aeon_lineardrive`'s workflow *(recommended)*

Neither option needs writing from scratch.
`aeon_lineardrive/.github/workflows/Aeon.LinearDrive.yml` is derived from `bonsai-rx/prefect`
(Bonsai Foundation standards enforcement). Its own header comment says it is **"a generic
workflow meant for all Harp devices"**, with the DocFX and firmware jobs removed on purpose
because *"documentation is handled centrally and the MicroPython firmware is flashed manually."*

prefect is worth reading directly, not only through `aeon_lineardrive`, because it carries rules
the workflow file does not show. Its `reference-harp/` tree is the template harp-tech device
repos are checked against, and `Ruleset.cs` adds programmatic checks. The notable one is
`ModernDotNetGitignoreRule`. It **requires** `.vs/`, `/artifacts/`, `**/.bonsai/Settings/`,
`**/.bonsai/Packages/`, `**/.bonsai/Bonsai.exe*` in `.gitignore`. It **forbids** the legacy
`bin`, `obj`, `packages`, `.nuget`, `*.exe`, `*.dll` patterns (modern .NET builds go to
`artifacts/` via `UseArtifactsOutput`, and the generic patterns hide problems). VertiGate's
`.gitignore` and `.gitattributes` now follow it exactly, at the Harp maintainer's request, with
no local additions such as the `device.yml` LF pin once considered in §3.4.

That workflow comment is VertiGate's situation exactly. The workflow builds the interface on
Windows and Linux, debug and release, and publishes packages to GitHub and NuGet.org on release.
Copy it, rename, adjust the namespace, and this phase is mostly done.

**Then add the two release conventions that CI does not cover:**

1. **`RELEASE_NOTE.md`**: the FabLabs house template (present but unfilled in
   `fablabs-automatic-shelter`). PCB version(s), firmware version, key changes, BOM table, PCB
   fabrication parameters, JLCPCB ordering pointer.
2. **AIND's version-encoding release titles**: `hw{major}.{minor}.{patch}-fw{major}.{minor}.{patch}`,
   with hardware releases attaching STEP, schematic PDF, Gerbers, position files and BOM.

Adapt the firmware half to MicroPython the way `aeon_lineardrive` already does: **attach a
prebuilt firmware image to every release**, so flashing does not need `mpremote` plus two
`mip install` calls against GitHub. The SWC FabLabs equivalent of AIND's SIPE part number needs
deciding. See §7.

Also add, because the shared workflow does not include it: a **generated-code freshness gate**
(regenerate from `device.yml`, then `git diff --exit-code`) and `device.yml` schema validation.
Without the freshness gate, the committed `Device.Generated.cs` silently drifts from the schema.
That is the most likely way this setup rots.

**Version discipline (either option):** `firmwareVersion` in `device.yml`, the values passed to
`HarpDevice(...)`, the `R_VERSION` bytes, the release tag, and the package version must all move
together. Today three of those disagree.

---

## 7. Hardware

`### Hardware connections` in the README is literally `TBC`. This is the largest unknown.

- The board is a **NeuroPico** (RP2354). The firmware hard-codes `Pin(11/12/13)`, `Pin(7)` LED,
  `UART0 rx=Pin(1)` for the Harp sync clock, and `UART1 tx=Pin(8)/rx=Pin(9)` at 1 Mbaud for the
  servo. None of this is documented in the repo.

### 7.1 A board support library exists, and its pin map disagrees

`SainsburyWellcomeCentre/micropython-neuropico` has a stub README, but `neuropico.py` is not a
stub. It defines the full board pin map. **VertiGate does not import it**, and the hard-coded
values conflict with it:

| NeuroPico constant | Pin | VertiGate uses that pin as |
| --- | --- | --- |
| `PIN_CLK_IN` | 13 | `Pin(13, Pin.OUT, value=1)`, driven as an output |
| `PIN_CLK_nEN` | 12 | `Pin(12, Pin.OUT, value=0)`, consistent with an active-low clock enable |
| `PIN_LED` | 16 (WS2812C RGB) | LED declared on `Pin(7)` instead |
| `PIN_PORT6_{A,B,C,D}` | 8, 9, 10, 11 | 8/9 = Dynamixel UART, 11 driven high |
| `PIN_PORT5_D` | 1 | `UART0 rx` for the sync clock |

One point does agree: `NeuroPico.CLK_SPEED = 100_000` matches VertiGate's
`UART(0, baudrate=100_000)`, so the sync clock rate is right.

This needs resolving before anything is documented. The plausible explanations are that
VertiGate targets a different board revision, or that it predates the library, or that the sync
input really is wired to a port pin rather than `PIN_CLK_IN`. **Do not write the pinout table
until this is resolved.** Prefer importing `micropython-neuropico` over re-declaring values, so
the board definition lives in one place for the whole fleet.

- Harp specifies a **physical sync connector** (`protocol/assets/PhysicalConnector.sch/.pdf`).
  Conformance means matching it, not only having a UART.
- Needed: pinout table, power budget (XM430 stall current vs supply), Dynamixel bus wiring,
  `hardwareTargets` tied to a real PCB revision, and PCB and mechanical sources under
  `hardware/`.
- The README said RP2354 but linked the `RPI_PICO2` UF2 in one place and `RPI_PICO` in another.
  **Fixed on 2026-09-17**: both links now point at `RPI_PICO2`.

### `harp.device.pico-template` solves most of this. Use it.

This is the most immediately useful thing AIND brings. The template ships **real KiCad sources**
for a generic RP2040/RP2350 Harp device, in two power variants (`usb_isolated/` and
`usb_powered_small/`). They cover exactly the unknowns listed above:

- ground-isolated full-speed USB
- **a 3.5 mm audio jack for the Harp time-synchronisation signal**: a concrete, working answer
  to "what connector does the sync clock use", against which the NeuroPico's `UART0 rx=Pin(1)`
  can be checked
- the RP2040 plus the required support components (2 MB external flash), and two power-supply
  chains (USB-direct or DC barrel jack). The barrel-jack variant is the relevant one, since an
  XM430 cannot be USB-powered
- PCBA layout with size hints for existing enclosures, DC barrel jack, USB-C, ground lug
- a `.gitignore` tuned to remove extra KiCad artifacts

Practical steps: diff the NeuroPico schematic against the template's sync and USB sections to
confirm connector conformance, and adopt the template's silkscreen convention (part number +
hardware semver + QR code to the repo). SWC has no SIPE numbering, so **decide the FabLabs
equivalent of a part number now**. The release convention in §6 and `hardwareTargets` in
`device.yml` both refer to it.

---

## 8. Documentation and ecosystem listing

- **README conventions:** shipped devices start with a photo (`Assets/`), key features,
  connectivity, and an interface section pointing at the Bonsai package.
- **Docs site, and the two-tier reality.** `harp-tech.github.io` collects devices as **git
  submodules** under `src/`, built with docfx via `bonsai-rx/docfx-tools`. Every submodule is a
  `harp-tech/*` repo. **Not one AIND device appears there**, despite ten registered WhoAmIs and
  active production use.

  So ecosystem membership has two independent tiers:

  | Tier | Requirement | Open to SWC? |
  | --- | --- | --- |
  | **Registry**: a real, addressable Harp device | WhoAmI PR + conformant `device.yml` | yes, routine (§1) |
  | **harp-tech.org docs site** | repo lives in the `harp-tech` org | no, unless the repo is donated |

  The site does carry `images/light-logo-swc.svg`, so SWC is a known partner. But a logo is not
  a device listing. **Treat harp-tech.org inclusion as optional and out of scope.** Host
  VertiGate's documentation on the existing FabLabs site (already linked from the README) and
  let `whoami.yml` be the discovery route. If a harp-tech.org listing is really wanted, that is
  a separate conversation with the maintainers about repo ownership, not a task in this plan.
- `harp-tech/community` (Sphinx) has a per-device page pattern under
  `source/Devices/alldevices/`. Its `Making-HARP/new_devices.rst` is an empty stub, so there is
  no written admission checklist. The de facto checklist is: registered WhoAmI + conformant
  `device.yml` + published interface package + documentation.

---

## 9. Suggested sequencing

| Phase | Work | Estimate |
| --- | --- | --- |
| **0: Decisions** *(blocking)* | Lock the register map (§2.2). Confirm the `Aeon.*` namespace (§4). Agree the WhoAmI block with Aeon + FabLabs (§1.1). Decide Altium vs KiCad and the part-number scheme (§5, §7). Confirm staying on MicroPython (§3.2). Take the licensing decision to FabLabs (§5). **CERN-OHL-W proposed**, in line with `aeon_roadmap#69`. | ~1 day |
| **1: Identity** *(long lead time)* | One WhoAmI PR to `harp-tech/whoami` reserving **3000 to 3500 for SWC** and allocating ids across the fleet, not only VertiGate (§1.1). Do this first. It is the only item that depends on an external maintainer. VertiGate's id moves from 5350 to 3002. | ~1 day |
| **2: Metadata** | Rewrite `device.yml` against draft-03 with the new map, correct `access` arrays, defaults, min/max, and units in descriptions. Validate against the published schema. | ~2 days |
| **3: Firmware** | Implement the new map. Fix the S8 decode, reply-value mismatches, version arguments, blocking-boot hazard, event merging. Add `MotorFault` and the `Control` event on/off bits. Move homing behind `Control.Calibrate`. | 1 to 2 weeks |
| **3b: Upstream microharp** *(parallel)* | `R_RESET_DEV` SAVE/RST_EE with non-volatile storage; `R_VERSION` PROTOCOL/CORE_ID (`'mpy'`)/INTERFACE_HASH population, taking the digest from whatever `generators#142` emits; `R_CLOCK_CONFIG` behaviour audit. | ~1 week |
| **4: Repo + interfaces** | Adopt the `aeon_lineardrive` layout (§5 Option C), copy its `.config/dotnet-tools.json` and `software/build/`, generate and commit the Bonsai + Python interfaces, rewrite the Bonsai example with typed operators. | ~3 days *(mostly copy and rename from `aeon_lineardrive`)* |
| **5: Release process** | Copy `Aeon.LinearDrive.yml`. Add the freshness gate and schema validation. Fill in `RELEASE_NOTE.md` from the FabLabs template. Adopt `hw*-fw*` release titles. Attach a prebuilt firmware image. | ~2 days |
| **6: Hardware and docs** | **Resolve the NeuroPico pin map first (§7.1).** Then diff against `harp.device.pico-template` for sync-connector and USB conformance; pinout table; `.img/`, `eCAD/`, `mCAD/`; silkscreen part number; README rewrite; FabLabs docs page. | 1 to 2 weeks *(depends on what exists offline)* |
| **7: Fleet follow-up** *(optional, separate)* | Apply the same treatment to `fablabs-automatic-shelter` (**register addresses 15 to 26 are a hard spec violation**), `aeon_lineardrive` (`whoAmI: 0000`, old schema URL) and `virt-hunt-drv` (no `device.yml`). Propose migrating them to the generation-3 stack. | separate project |

---

## 10. Risks

- **No SWC device holds a registered WhoAmI**, and nothing stops another institution being
  given the ids currently in use (`5350`, `0x1234`, `0000`). The proposed 3000 to 3500
  reservation (§1.1) is the most urgent and least effort item in the plan.
- **No MicroPython precedent in the ecosystem** *(downgraded from the first draft)*. Every other
  device is C/C++ (ATxmega, Pico SDK), and `micropython-microharp` is SWC's own core, not an
  upstream one. But AIND shows that running your own core, namespace and Python library is
  normal, and `micropython-microharp` already implements more core registers (0 to 19) than
  AIND's production `harp.core.pico` does (0 to 17). The remaining risk is narrow: `mpremote` is
  not a bootloader, so `harp-regulator` / `regulator` cannot update this device. (`CORE_ID` is
  no longer a risk. `'ATX'` and `'rpi'` set the precedent of cores naming themselves. See §3.4.)
- **`INTERFACE_HASH` is being defined right now, upstream.** The spec named SHA-1 of `device.yml`
  without saying which bytes. `protocol#233` / `#234` and `generators#142` (all September 2026)
  fix the layout, pin the input (UTF-8, no BOM, LF) and move the computation into the generator.
  Remaining risk for VertiGate: the three emit targets are C#, Python client and a C header, and
  none is usable by MicroPython firmware. The digest must come from whatever `#142` adds for us,
  and must never be computed by hand from a Windows working tree (§3.4).
- **Firmware distribution to non-developers.** AIND ships a UF2 per release. VertiGate needs
  `mpremote` plus two `mip install` steps against GitHub. Fine for the FabLab, awkward for a
  visiting experimenter. `aeon_lineardrive` already solves this by attaching a prebuilt image to
  each release. Adopt that instead of inventing something.
- **Fleet fragmentation.** SWC runs three incompatible MicroPython Harp stacks (§0.6.2), and the
  `micropython-microharp` rewrite means `aeon_lineardrive` must pin a specific commit and warn
  about it in its README. VertiGate is on the newest stack, so the fleet either converges on it
  or the split becomes permanent. That is a FabLabs/Aeon decision beyond this repo, but
  VertiGate's choices here will set the precedent either way.
- **Two placeholder WhoAmIs are already deployed** (`0000`, `0x1234`). Registering VertiGate
  alone leaves them in the field. Hence the block reservation in §1.1.
- **The NeuroPico pin map is contested** (§7.1). The board library and the firmware disagree on
  what pins 12, 13 and 16 are for. Until that is settled, any pinout documentation would be
  guesswork, and it is on the critical path for Phase 6.
- **Silent wrong data in the experimental record.** The startup register dump (§3.3) reports
  `Speed=0, Torque=0, Status=Idle` for a device actually running at 255/35 and sitting down. No
  error is raised, so a workflow that logs rig configuration from the dump records values that
  were never true. This is the most damaging class of defect in the repo because it is invisible.
  Rank it above the S8 decode bug when scheduling Phase 3.
- **The register renames are breaking for the generated API.** The map itself is additive on the
  wire (§2.2), but `Operation` to `TargetPosition` and `Offset` to `CalibrationOffset` change
  the C# and Python names. Cheap now, expensive after the first `Aeon.VertiGate` package ships.
  Hence Phase 0.
- **Convention drift.** Mixing the two ecosystems half and half (harp-tech layout, AIND tooling,
  neither release convention) is worse than committing to either. Phase 0 exists to prevent
  this.
- **Hardware documentation may not exist yet** in any form. Still the item most likely to blow
  the estimate, though `harp.device.pico-template` now supplies a reference schematic to check
  against instead of a blank page.
