# VertiGate → harp-tech device: gap analysis & migration plan

> Status: analysis only — no firmware, interface, or hardware changes have been made.
> Sources cross-checked: `harp-tech/protocol` (spec + `schema/{device,core,registers}.json`),
> `harp-tech/whoami`, `harp-tech/generators`, `harp-tech/toolkit`, `harp-tech/device.template`,
> `harp-tech/device.hobgoblin`, `harp-tech/device.syringepump`, `harp-tech/device.faststepper`,
> `harp-tech/harp-tech.github.io`, `SainsburyWellcomeCentre/micropython-microharp`, the
> AllenNeuralDynamics ecosystem (`harp.core.pico`, `harp.device.pico-template`,
> `harp.device.cuttlefish`, `pyharp`, `Bonsai.AllenNeuralDynamics`), and the existing SWC estate
> (`aeon_lineardrive`, `fablabs-automatic-shelter`, `virt-hunt-drv`, `micropython-neuropico`,
> `conspecific-carousel`, and the `fablabs-*` hardware repos).

## 0. Where we actually stand

VertiGate is much closer than a blank slate.

**Exists:** a valid-ish `device.yml`, a working MicroPython application on top of
`micropython-microharp` (which already installs core registers 0–19, including the newer
`R_UID` / `R_TAG` / `R_HEARTBEAT` / `R_VERSION`), USB CDC transport, sync-clock UART, and a
Bonsai example workflow.

**Does not exist:** registry identity, generated interfaces, ecosystem repo structure, CI,
versioning discipline, hardware artifacts, documentation. There are also several real
protocol-conformance bugs in the firmware.

Roughly: **protocol plumbing ~70% done, ecosystem integration ~0% done.**

---

## 0.5 Two reference ecosystems, not one

There is no single "harp-tech way". Two organisations ship Harp devices with materially
different conventions, and both are legitimate members of the same registry:

| | **harp-tech / Champalimaud** | **AllenNeuralDynamics (AIND)** |
| --- | --- | --- |
| Reference core | `core.atxmega` (C), `core.pico` (C++) | `harp.core.pico` (C++, RP2040 **and RP2350**) |
| Project template | `device.template` (ATxmega-era, sparse) | `harp.device.pico-template` (KiCad + CMake, actively used) |
| Repo layout | `Firmware/ Hardware/ Interface/ Assets/` (TitleCase) | `firmware/ hardware/ software/ assets/` (lowercase) |
| Interface generation | `Harp.Generators` + T4 via `Generators/Generators.csproj` | `harp.toolkit` pinned as a **local dotnet tool manifest** |
| C# namespace | `Harp.<Device>` | `AllenNeuralDynamics.<Device>` |
| Package aggregation | individual NuGet packages | `Bonsai.AllenNeuralDynamics` umbrella repo |
| Python | generated interface against `harp-tech/python` | hand-written scripts against `AllenNeuralDynamics/pyharp` |
| CI | full workflow, generated-code freshness gate, NuGet publish | **none in device repos** — replaced by a strict release convention |
| Listed on harp-tech.org | yes (submodules under `src/`) | **no** |

AIND holds ten WhoAmI allocations (1400–1411) under the `aind` owner key. So an external
institution running its own conventions, its own namespace and its own Python library is the
*normal* case, not an exception.

**What this means for VertiGate:** the AIND model is closer to where this repo already is
(lowercase folders, no CI, RP2350 silicon, a FabLab rather than a product team), and it is
cheaper to adopt. Several recommendations below shift accordingly. The rest of this document
flags where the two ecosystems diverge and which side to pick.

---

## 0.6 The SWC estate — VertiGate is not the first, and not the only one

Before importing anyone else's conventions: **SWC already runs several Harp devices**, on three
mutually incompatible firmware stacks, none of them registered.

| Repo | Harp? | Stack | `device.yml` | WhoAmI | Bonsai pkg | CI |
| --- | --- | --- | --- | --- | --- | --- |
| **`aeon_lineardrive`** | yes | legacy microharp (pinned `df88717c`) + SWC MicroPython fork `v1.18-swc` | **yes** | `0000` placeholder | **`Aeon.LinearDrive`, generated** | **yes** |
| **`fablabs-VertiGate`** | yes | **current** microharp API + stock MicroPython | yes | 5350, unregistered | no | no |
| **`fablabs-automatic-shelter`** | yes | legacy microharp API | no | `0x1234` placeholder | no | no |
| **`virt-hunt-drv`** | yes | oldest — `SainsburyWellcomeCentre/microharp` + `v1.18-swc` fork | no (README table) | not set | no | no |
| `conspecific-carousel` | **no** | bespoke framing (`HEADER 0xCC`) | no | — | no | no |
| `aeon_beambreak_filter` | no — TTL logic only | bare MicroPython | — | — | — | — |
| `fablabs-{valve-driver, lick-detector-piezo, monitor-blanking}` | no — passive/TTL **peripherals** | none | — | — | — | — |

### 0.6.1 `aeon_lineardrive` is the reference implementation — copy it

This is the single most useful discovery in this analysis. `aeon_lineardrive` is an **SWC-owned,
MicroPython, Harp device that already has the complete software pipeline** this document has
been reconstructing from first principles:

- `device.yml` at the repo root
- `.config/dotnet-tools.json` pinning `harp.toolkit` **0.2.2 — byte-identical to AIND's manifest**
- `software/Aeon.LinearDrive/` with committed `Device.Generated.cs` / `AsyncDevice.Generated.cs`
- `software/build/*.props` — the Bonsai Foundation shared build infrastructure
- `.github/workflows/Aeon.LinearDrive.yml`, derived from `bonsai-rx/prefect` ("automated
  standards enforcement for Bonsai Foundation projects"), and annotated in-file as *"a generic
  workflow meant for all Harp devices… Documentation is handled centrally and the MicroPython
  firmware is flashed manually, so this workflow has no DocFX or firmware jobs."*
- `hardware/eCAD/Altium Project/` with Assembly/Fabrication OutJobs, plus `hardware/README.md`
- a prebuilt firmware image attached to every release

That workflow comment describes VertiGate's exact situation — MicroPython, manually flashed,
docs hosted elsewhere. **The CI and packaging problem is already solved in-house.** Most of
§4–§6 below reduces to "copy `aeon_lineardrive`, rename, adjust."

### 0.6.2 Three firmware stacks, and VertiGate is on the newest

`aeon_lineardrive`'s README is explicit: *"Pin this commit; the current version of microharp is
an incompatible rewrite."* Concretely:

| Generation | Framework | MicroPython | USB / sync | Used by |
| --- | --- | --- | --- | --- |
| 1 | `SainsburyWellcomeCentre/microharp` | SWC fork `v1.18-swc` | frozen `usbcdc` + `harpsync` modules | `virt-hunt-drv` |
| 2 | `micropython-microharp` @ `df88717c` (`HarpTypes`, `ReadWriteReg`) | SWC fork `v1.18-swc` | frozen modules | `aeon_lineardrive`, `fablabs-automatic-shelter` |
| 3 | `micropython-microharp` current (`add_u8`, `@on_write`, `CdcTransport`) | **stock** RP2350 build | `usb.device.cdc` via mip | **`fablabs-VertiGate`** |

VertiGate is the only device on generation 3, and generation 3 is the only one that runs on
stock MicroPython with no custom fork. That is a genuine strategic advantage and an argument for
making **VertiGate the template for the fleet** — but it also means it cannot borrow
lineardrive's *firmware*, only its repo structure, tooling and CI, which are stack-independent.

### 0.6.3 Conformance problems elsewhere in the estate

Worth knowing, because they set expectations for review and because fixing VertiGate correctly
creates the pattern for fixing them:

- **`fablabs-automatic-shelter` places application registers at addresses 15–26.** The spec is
  unambiguous: *"Every application register MUST have an address equal to, or greater than, 32."*
  Those addresses collide with `R_TIMESTAMP_OFFSET` (15), `R_UID` (16), `R_TAG` (17),
  `R_HEARTBEAT` (18) and `R_VERSION` (19). Any standard Harp controller will misread this device.
  It also reports `whoAmI = 0x1234` and a device name of `"Feeder V2"`, and its README and
  `RELEASE_NOTE.md` are still unedited template placeholders.
- **`aeon_lineardrive` declares `whoAmI: 0000`** and still points at the pre-draft
  `harp-tech/reflex-generator` schema URL, older than the draft-02 URL VertiGate uses.
- **`virt-hunt-drv`** documents its register map as a README table with no `device.yml`, so no
  interface can be generated from it.

**Nothing in the SWC estate holds a registered WhoAmI.** Every one of these devices is currently
unaddressable in the wider ecosystem.

---

## 1. Identity & registry — blocking, do first

| Item | Status |
| --- | --- |
| `whoAmI: 5350` | **Not registered.** `harp-tech/whoami/whoami.yml` lists 46 devices; the highest allocated is 2110. Nothing in the 5000s. |
| Owner key for SWC | **Absent.** `owners:` contains aind, champalimaud, harptech, neurogears, neurophotometrics, oeps. No SWC entry. |

One PR to `harp-tech/whoami` is needed, adding an owner key (alphabetical order) plus the device:

```yaml
owners:
  swc: &swc
    authors: SainsburyWellcomeCentre
    copyright: SainsburyWellcomeCentre

devices:
  5350:
    <<: *swc
    name: VertiGate
    repositoryUrl: https://github.com/SainsburyWellcomeCentre/fablabs-VertiGate
    projectUrl: <fablabs documentation page>
```

`name` must match `^[a-zA-Z][a-zA-Z0-9_]*$` — `VertiGate` is fine. The id pattern in
`whoami.json` accepts 4-digit values, so 5350 is format-legal; it simply needs to be claimed.

**Until this merges, 5350 is squatted, not owned.**

**Precedent:** AIND added its own `aind` owner key and ten devices (1400–1411) pointing at
repositories in its own GitHub organisation. This is a routine, low-friction PR — the registry
is deliberately open to external institutions, and SWC is already a recognised ecosystem
partner. Expect this to be the easiest external interaction in the whole plan.

### 1.1 Reserve a block, not a single id

Per §0.6, **no SWC device holds a registered WhoAmI**: `aeon_lineardrive` ships `0000`,
`fablabs-automatic-shelter` ships `0x1234` (4660), `virt-hunt-drv` sets none, and VertiGate
claims an unregistered 5350. Two of those placeholders are actively deployed, and `0x1234` is a
value another institution could legitimately be allocated.

Since one PR is being opened anyway, **register the whole SWC fleet at once** — a contiguous
block (5350–5360, say) covering VertiGate, LinearDrive, AutomaticShelter and VirtHunt, following
AIND's 1400–1411 pattern. The marginal cost over registering VertiGate alone is a few lines of
YAML; the alternative is four separate PRs and four separate negotiations, and meanwhile
`0000`/`0x1234` stay in the field. Confirm the block with the Aeon and FabLabs teams before
submitting, since it commits their devices too.

---

## 2. `device.yml` — schema and modelling gaps

### 2.1 Mechanical fixes

- **Stale schema URL.** The file points at `draft-02`. The protocol repo now ships `draft-03`
  (`schema/device.json`, `core.json`, `registers.json`). Retarget.
- **`access` under-declares.** `Status` is `Event` only, but the firmware registers it
  `READ_ONLY | EVENT`, and the README says "R + Event". `Speed` / `Torque` / `Offset` are
  `Write` in YAML but `READ_WRITE` in firmware. Use the array form —
  `access: [Read, Event]`, `access: [Read, Write]`. A mismatch here directly produces a
  wrong Bonsai/Python interface.
- **Unused schema fields.** `defaultValue` (Speed 255, Torque 35, Offset 0),
  `volatile: false` on the three config registers, `minValue` / `maxValue` on Speed.
- **Units live only in the README** (1.2 mm/count, 0.38 mm/s, 0.36 kgf·mm, 25 µm). Fold them
  into `description` so they survive into generated documentation and IntelliSense.
- **`hardwareTargets: "0.1"`** must correspond to a real, versioned hardware revision (§7).

### 2.2 Register map redesign — the substantive design question

The current map is workable but off-convention. Nothing is released yet, so this is the cheap
moment to fix it.

Problems with the map as it stands:

1. **`Operation` is a bad name.** It reads as a sibling of core `R_OPERATION_CTRL` (addr 10).
   Every comparable Harp motion device uses a functional name.
2. **Magic values.** `0` and `255` mean "home" and "fully up" while `1–254` mean "position".
   That is a polymorphic payload in spirit; the spec's *Register polymorphism* section
   explicitly warns against overloading one register's semantics.
3. **No position readback.** There is no way to ask where the gate is, only which state-machine
   bucket it is in. Comparable devices expose a measured value as an Event
   (`faststepper` → `Encoder`, `syringepump` → `Protocol`).
4. **No stop, no enable/disable, no re-home command.** `Gate.stop()` exists in firmware but is
   unreachable over the wire. Homing only ever happens once, at boot.
5. **No error/fault register.** Dynamixel stalls, comms timeouts and out-of-travel conditions
   are invisible to the host. The spec's guidance is that such conditions should surface as an
   event on a dedicated register rather than as error replies.
6. **No `EnableEvents`.** `device.syringepump`, `device.stepperdriver` and `device.behavior`
   all carry an `EnableEvents` bitmask so hosts can gate event traffic. It is a de-facto
   ecosystem convention.

Proposed map, aligned with `faststepper` / `syringepump` naming:

| Addr | Name | Type | Access | Purpose |
| --- | --- | --- | --- | --- |
| 32 | `Control` | U8 | Write | bitmask: `EnableMotor`, `DisableMotor`, `Stop`, `Calibrate` |
| 33 | `TargetPosition` | U16 | Read, Write | absolute target (µm or 1.2 mm counts) — one meaning, no magic values |
| 34 | `GateState` | U8 | Read, Event | groupMask `Idle` / `Up` / `Down` / `Moving` / `Error` |
| 35 | `Speed` | U8 | Read, Write | as today, with default/min/max declared |
| 36 | `Torque` | U8 | Read, Write | as today |
| 37 | `CalibrationOffset` | S8 | Read, Write | renamed from `Offset`, per syringepump convention |
| 38 | `Position` | U16 | Read, Event | *measured* position reported by the servo |
| 39 | `MotorFault` | U8 | Read, Event | bitmask: `Stall`, `Overload`, `CommsTimeout`, `TravelLimit` |
| 40 | `EnableEvents` | U8 | Read, Write | bitmask gating `GateState` / `Position` / `MotorFault` |
| 41 *(optional)* | `ServoTelemetry` | U16×n | Read, Event | present current / temperature / voltage |

Keeping `Up` / `Down` as a convenience is fine — express it as two `Control` bits, not as
sentinel values inside a position register.

Whatever map is chosen, every register must be **dump-ready**: each `defaultValue` declared in
`device.yml` mirrored into register storage at construction, and `on_read` handlers on
`Position`, `GateState` and any telemetry register so a read queries the servo rather than
echoing the last write. See §3.3 for why this is not optional.

**This decision needs sign-off before anything else proceeds**, because the register map drives
firmware, generated interfaces, the Bonsai workflow, and the documentation.

---

## 3. Firmware conformance — bugs and gaps

Genuine defects in the current code:

- **S8 payloads are decoded as unsigned.** [`firmware/register.py:44-47`](../firmware/register.py#L44-L47)
  does `offset = payload[0]` on a memoryview, so a written `-10` arrives as `246`, and
  `max(min(246, 127), -128)` clamps it to `+127`. **Negative offsets are impossible today.**
  Needs `struct.unpack` or an explicit sign fixup.
- **Reply payloads report values that were never applied.** The spec requires a `Write` reply to
  contain the actual register value after processing. `_torque` stores the raw byte then applies
  `val & 0x7F`; `_speed` stores the raw byte then applies `vel & 0xFF` plus a `+60` offset.
  Write `200` to Torque and the device replies `200` while running at `72`. Either clamp before
  storing, or reject out-of-range writes with an error reply (spec case 5 explicitly permits this).
- **Version registers lie.** [`firmware/main.py`](../firmware/main.py) passes `who_am_i` and
  `device_name` but not `fw_version` / `hw_version`, so microharp defaults to `(1,0)` / `(1,0)`
  while `device.yml` declares `0.1` / `0.1`. `R_HW_VERSION_H/L`, `R_FW_VERSION_H/L` and bytes
  3–8 of `R_VERSION` are all wrong.
- **`R_VERSION` PROTOCOL / CORE_ID / INTERFACE_HASH are zero.** microharp leaves these at their
  spec defaults. `INTERFACE_HASH` is the SHA-1 of `device.yml`; leaving it zero tells controllers
  to skip schema validation — exactly the feature that makes a Harp device self-describing.
  Needs a build step that computes the digest and bakes it in, plus a three-character `CORE_ID`
  for the MicroPython core.
- **Boot can hang before enumeration.** `Gate.__init__` runs `_calibrate_home()` with blocking
  `time.sleep` in an unbounded `while True` loop, *before* `device.run()`. A missing or
  unresponsive Dynamixel means the board never enumerates and appears bricked. Needs a timeout
  and a fault state — better still, move homing behind an explicit `Control.Calibrate` command so
  the device always comes up on the bus.
- **Stale `_ismoving` on re-command.** `move()` cancels the in-flight `_run()` task; the cancelled
  task never runs `_disable()`, so state can be left inconsistent. The `isr.set()` / `clear()`
  pattern in [`firmware/task.py`](../firmware/task.py) can also coalesce two rapid transitions into
  a single event.
- **Torque/Speed setters cycle `torque_enabled` off→on.** Writing Speed mid-hold will drop the
  gate. Should be documented, or the setters should defer while the gate is holding position.
- **No non-volatile settings.** `R_RESET_DEV` bits `RST_DEF` / `RST_EE` / `SAVE` / `BOOT_DEF` /
  `BOOT_EE` are specified for persisting configuration; microharp's handler currently just calls
  `machine.reset()` on any non-zero write. Since Speed / Torque / CalibrationOffset are per-rig
  calibration values, persistence is worth having.
- **`R_CLOCK_CONFIG` is a plain R/W byte** in microharp with no `CLK_GEN` / `CLK_REP` / lock
  semantics behind it. Audit what the sync UART actually honours before claiming clock-sync
  conformance.

- **The register dump omits write-only registers.** `dispatch.py`'s `_dump_all_registers()`
  skips any register without `READ_ONLY` access, but the spec says the dump carries *"the current
  contents of all core and application registers"* and is explicit that even optional and
  deprecated registers "MUST be included". VertiGate's `Operation` register is write-only, so it
  disappears from the dump entirely. See §3.3.

Several of these — `SAVE` / `RST_EE`, `R_VERSION` hash and core id, clock config, and the
write-only-register dump deviation — are **upstream `micropython-microharp` work** that benefits
every future SWC MicroPython Harp device. Budget them there, not here.

### 3.1 Calibrate the conformance bar against AIND

Worth knowing before over-investing here: AIND's `harp.core.pico` — the C++ core running every
AIND device in production — enumerates core registers only up to `TAG = 17`. It implements
**neither `R_HEARTBEAT` (18) nor `R_VERSION` (19)**.

`micropython-microharp` already implements both, including the full 32-byte `R_VERSION` layout.
So on core-register coverage VertiGate is *ahead of* the most active reference core in the
ecosystem, not behind it. The `INTERFACE_HASH` / `CORE_ID` gap in §3 is a nice-to-have that
improves on the state of the art — it is not an admission requirement, and it should not block
Phases 1–5.

The items that genuinely matter for conformance are the ones that produce *wrong data on the
wire*: the S8 decode bug, the reply-value mismatches, and the version registers that disagree
with `device.yml`.

### 3.2 Strategic fork: stay on MicroPython, or port to `harp.core.pico`?

AIND's `harp.core.pico` explicitly targets **RP2040 and RP2350** — the same silicon family as
VertiGate's RP2354. A C++ port is therefore a real option, not a hypothetical one.

| | **Stay on `micropython-microharp`** | **Port to `harp.core.pico`** |
| --- | --- | --- |
| Effort | zero — already working | full firmware rewrite, plus a Dynamixel driver in C++ |
| Core-register coverage | better (0–19) | worse (0–17) |
| Ecosystem familiarity | none — no MicroPython Harp device exists | high — nine AIND devices + hobgoblin |
| Toolchain | `mpremote`, no build step | Pico SDK + CMake, submodules |
| Firmware update path | `mpremote` (not regulator-compatible) | UF2 via BOOTSEL, matches AIND release convention |
| Timing determinism | GC pauses, interpreted | deterministic, dual-core |
| Maintenance | SWC owns the whole stack | shared upstream core |

**Recommendation: stay on MicroPython.** The core-register argument now runs in your favour, the
Dynamixel driver already exists in MicroPython, and a rewrite would consume the entire budget of
this migration while changing nothing a Bonsai user can observe. Revisit only if gate timing
jitter turns out to matter experimentally, or if firmware distribution to non-developers becomes
a real burden (the UF2 story is genuinely better on the C++ side).

### 3.3 Register dump: the mechanism works, the payloads don't

Harp controllers read a device's whole state at connection time. This is not spontaneous — the
**controller requests it**: it writes `R_OPERATION_CTRL` with the **DUMP** bit (bit 3) set, and
per `Device.md` the device *"SHALL send a sequence of `Read` messages to the Controller, one per
register, with the current contents of all core and application registers"*, after the write
reply. `Bonsai.Harp`'s `Device` operator sets `DumpRegisters = true` in its constructor, so every
Bonsai workflow triggers this on startup by default — and
[`bonsai/example.bonsai`](../bonsai/example.bonsai) already has it enabled.
`harp-tech/core.pico` implements the device side in `harp_core.cpp` (masks DUMP out of stored
state, dispatches one READ per core register, then calls `dump_app_registers()`).

**The mechanism is fine.** `micropython-microharp` implements DUMP correctly in `dispatch.py`:
write-reply first, then `_dump_all_registers()` emits one READ per register, each individually
timestamped, then auto-clears the bit. It also honours `on_read` handlers.

**The payloads are wrong.** In [`firmware/register.py:14-18`](../firmware/register.py#L14-L18) all
five application registers are created with no initial value and **no `on_read` handler**, and
`RegisterEntry.storage` is a zeroed `bytearray`. A dump immediately after boot therefore reports:

| Register | Dump reports | Actual device state |
| --- | --- | --- |
| `Operation` 0x21 | **omitted** — microharp skips write-only registers | — |
| `Status` 0x22 | `0` (Idle) | gate is physically **down** after `_calibrate_home()`, but `_isdown` is never set during calibration |
| `Speed` 0x23 | `0` | `VEL_DEFAULT` = 255 |
| `Torque` 0x24 | `0` | `TRQ_DEFAULT` = 35 |
| `Offset` 0x25 | `0` | 0 — correct, by luck |

Two distinct root causes:

1. **Defaults are applied to the servo but never mirrored into register storage.** `Gate.__init__`
   sets `self.speed = VEL_DEFAULT` and `self.torque = TRQ_DEFAULT` on the Dynamixel; the
   corresponding `RegisterEntry.storage` bytes stay at zero.
2. **No `on_read` handlers, so a dump never queries the servo.** It can only echo what the host
   last wrote. Later in a session `Speed`/`Torque` still report the raw written byte rather than
   the masked/offset value actually applied — the same root cause as the reply-value mismatch
   in §3.

**Why this matters more than it looks.** A workflow that uses the startup dump to populate its UI
or to log rig configuration will silently record `Speed=0, Torque=0, Status=Idle` for a device
running at 255/35 and sitting at the bottom of its travel. Nothing raises an error; it is simply
wrong data in the experimental record. Fix alongside the register redesign (§2.2) — the cost is
initialising storage at construction plus a handful of `on_read` handlers.

---

## 4. Generated interfaces — entirely missing

This is what makes a device a *harp-tech* device rather than a device that merely speaks Harp.
Two artifacts are generated from `device.yml`:

### Bonsai / C# package (name TBD — see below)

Reference implementation: `device.hobgoblin` — a `Generators/Generators.csproj` referencing
`Harp.Generators` (0.4.0) driving T4 templates, output into
`Interface/<Namespace>/{Device,AsyncDevice}.Generated.cs`, packaged as
`<PackageType>Dependency;BonsaiLibrary</PackageType>` against `Bonsai.Harp` 3.6.1, targeting
`net462;netstandard2.0`, with `device.yml` embedded as a resource. Generated code is
**checked in**, and CI fails if it is stale.

Simpler alternative: the `harp.toolkit` dotnet tool exposes `generate interface`,
`generate python-interface` and `generate register-metadata` directly, avoiding the T4/MSBuild
scaffolding.

**Recommendation: the toolkit route — proven both by AIND and inside SWC.**
`harp.device.cuttlefish` carries no `Generators/` project at all; instead it pins the tool in a
manifest. **`aeon_lineardrive` pins the identical tool at the identical version** in
`.config/dotnet-tools.json`, so this is already the de-facto SWC standard and needs no debate:

```json
{ "version": 1, "isRoot": true,
  "tools": { "harp.toolkit": { "version": "0.2.2",
             "commands": ["harp.toolkit"], "rollForward": false } } }
```

and commits the resulting `Device.Generated.cs` / `AsyncDevice.Generated.cs`. That is
dramatically less machinery than the hobgoblin T4 pipeline, and it is what a device on
MicroPython (with no C firmware generation to do) actually needs.

Skip `ios.yml` / `Firmware.tt` entirely — that generator targets ATxmega/pico C firmware and is
irrelevant here.

### Naming and distribution — a decision, not a default

| | harp-tech style | AIND style | **SWC precedent (`aeon_lineardrive`)** |
| --- | --- | --- | --- |
| Namespace / package | `Harp.VertiGate` | `AllenNeuralDynamics.Cuttlefish` | **`Aeon.LinearDrive`** |
| Location in repo | `Interface/` | `software/bonsai/Interface/` | **`software/<Namespace>/`** |
| Publishing | individual NuGet package | umbrella repo (`Bonsai.AllenNeuralDynamics`) | individual, via the shared workflow |

The `Harp.*` namespace carries an implicit claim of being a harp-tech-org device; AIND
deliberately avoided it, and so did Aeon. The in-house precedent uses a **project/programme
name**, not the institution name — `Aeon.LinearDrive`, not `SainsburyWellcomeCentre.LinearDrive`.

Applying that convention gives **`Fablabs.VertiGate`** in `software/Fablabs.VertiGate/`, which
scales to the six sibling FabLabs devices and matches the existing `fablabs-*` repo prefix.
Confirm with the FabLabs team, since it sets the pattern for every future device — but prefer it
over inventing a third scheme.

Note the AIND csproj also sets `GeneratePackageOnBuild` on Release and pins `Bonsai.Harp` 3.5.0
(hobgoblin uses 3.6.1); take the newer.

### Python package

Two options, and they are not equivalent:

- **`harp-tech/python`** — `PyDevice.tt` / `harp.toolkit generate python-interface` emits a
  typed module importing from `harp.protocol`. Generated, typed, stays in sync with `device.yml`.
- **`AllenNeuralDynamics/pyharp`** — AIND's own implementation. Cuttlefish ships
  `software/pyharp/*.py` as **hand-written example scripts**, not a generated interface.

**Recommendation: generate against `harp-tech/python`.** It is derived from `device.yml`, so it
cannot drift, and it also covers reading recorded binary data. Optionally add a couple of
hand-written `pyharp`-style scripts as usage examples — that part of the AIND pattern is worth
copying.

### Downstream consequence

The current Bonsai workflow hand-codes `Address 33`, `PayloadType U8` in raw
`CreateMessage` / `Format` nodes, with `PortName COM21` hard-coded. With a generated package
those become typed, discoverable operators.

---

## 5. Repository structure

VertiGate is currently a flat `firmware/` + `bonsai/`. There are two established target layouts.

**Option A — harp-tech (`device.template`, hobgoblin, behavior):**

```
Assets/            device photo, pinout diagrams, PCB render
Firmware/          MicroPython application (today's firmware/, relocated)
Hardware/
  PCB/             KiCad — fablabs-kicad-library already exists
  Mechanical/      gate assembly CAD, STEP/DXF
Interface/         generated Bonsai package + .sln + csproj
Generators/        (or a toolkit invocation script)
device.yml
README.md
global.json
.github/workflows/
```

**Option B — AIND (`harp.device.cuttlefish`, `harp.device.pico-template`):** lowercase
`assets/ firmware/ hardware/{board,mechanical}/ software/bonsai/Interface/` + `device.yml`.

**Option C — `aeon_lineardrive`, the in-house hybrid *(recommended)*:**

```
.config/dotnet-tools.json    pins harp.toolkit 0.2.2
.github/workflows/           the shared Harp device workflow
.img/                        FabLabs house convention: README imagery
device.yml
firmware/                    MicroPython application (stays where it is)
hardware/
  eCAD/                      Altium project + Assembly/Fabrication OutJobs
  mCAD/                      gate assembly CAD (Inventor), STEP/DXF
  README.md
software/
  Fablabs.VertiGate/         generated Device.Generated.cs + csproj + README
  build/                     shared Bonsai Foundation props
  Fablabs.VertiGate.sln
  Directory.Build.props
LICENSE
README.md
RELEASE_NOTE.md              FabLabs house convention
altium-viewer.json           FabLabs house convention
global.json
CITATION.cff
```

**Why Option C.** It is the only layout that satisfies all three constituencies at once: it keeps
the lowercase folders VertiGate already has, it adopts the SWC FabLabs hardware conventions
(`.img/`, `eCAD/`, `mCAD/`, `RELEASE_NOTE.md`, `altium-viewer.json` — used consistently across
`fablabs-automatic-shelter`, `-valve-driver`, `-lick-detector-piezo`, `-monitor-blanking`,
`-environmental-sensor`), and it carries the harp-tech software pipeline in `software/` with
generated code and CI. It exists, it works, and it is maintained by colleagues.

Note VertiGate currently has **none** of the FabLabs hardware-side items — no `.img/`, no
`eCAD/`, no `mCAD/`, no `RELEASE_NOTE.md`, no `altium-viewer.json`. It is the only `fablabs-*`
repo without them.

**Altium vs KiCad:** every existing `fablabs-*` and Aeon board is Altium (`.PcbDoc`/`.SchDoc`),
published through the Altium 365 Viewer via `fablabs-documentation`. But `fablabs-kicad-library`
("global KiCAD library for all PCB projects") is active. Establish which VertiGate targets before
creating `hardware/eCAD/` — a migration may be in flight, and this is a FabLabs-wide call, not a
VertiGate one.

### Licensing — less contradictory than it first appears

The FabLabs README template states: *"Sainsbury Wellcome Centre hardware is released under
Creative Commons Attribution-ShareAlike 4.0 International."* Combined with VertiGate's own README
line about code being BSD 3-Clause, the house convention is clearly **hardware CC BY-SA 4.0,
code/firmware BSD 3-Clause**.

So the root `LICENSE` (BSD 3-Clause) is correct for the code, and the CC BY-SA badge at the top of
the README is correct for hardware — they are just presented as though one governs the whole
repo. Fix by adding per-directory `LICENSE` files (`hardware/LICENSE` = CC BY-SA,
`firmware/LICENSE` and `software/LICENSE` = BSD-3) and stating both in the README, exactly as
`aeon_lineardrive` and `fablabs-automatic-shelter` already do. This is a documentation fix, not a
licensing decision.

Keep `bonsai/example.bonsai`, but relocate it (`software/bonsai/` or `examples/`) and strip the
hard-coded `COM21` port. `aeon_lineardrive` also ships a `.bonsai/` directory with
`Bonsai.config` + `NuGet.config`, which pins the Bonsai environment and package feed for anyone
running the example — worth copying.

---

## 6. CI/CD, versioning, release

Nothing exists today. The two ecosystems answer this very differently, and the AIND answer is
probably the right size for a FabLab device.

### Option A — harp-tech: heavy CI (`Harp.Hobgoblin.yml`)

- Triggers on push / PR / published release; `CiBuildVersion` derived from the release tag
  (`v*`), enforced by `Directory.Build.props` sanity checks that **fail the build** if the tag
  and assembly version disagree.
- Steps: setup .NET 8 → install `dotnet-t4` → restore/build `Generators` →
  **`git diff --exit-code` to prove generated code was committed up to date** → build →
  `dotnet pack` → upload artifacts → publish to NuGet.org on release under a `public-release`
  environment.
- `harp-tech/configure-build` provides the shared Bonsai Foundation versioning action.

### Option B — AIND: no CI, strict release convention

AIND device repos have **no GitHub Actions workflows at all**. Instead `harp.device.pico-template`
specifies a release policy, which is arguably more valuable for a hardware device than a build
matrix:

- Release title encodes both versions: `hw{major}.{minor}.{patch}-fw{major}.{minor}.{patch}`
  (drop the `hw*` half for firmware-only releases, and vice versa).
- **Every hardware release attaches:** STEP file of the PCB, schematic PDF, Gerbers (logos
  removed), component position files, and the BOM.
- **Every firmware release attaches:** the compiled binary, and states which hardware revisions
  it is compatible with.
- The PCB silkscreen carries the part number with the hardware semantic version appended, plus a
  QR code linking to the repository.

### Option C — copy `aeon_lineardrive`'s workflow *(recommended)*

Neither option needs writing from scratch. `aeon_lineardrive/.github/workflows/Aeon.LinearDrive.yml`
is derived from `bonsai-rx/prefect` (Bonsai Foundation standards enforcement) and states in its
own header comment that it is **"a generic workflow meant for all Harp devices"**, with
DocFX and firmware jobs deliberately removed because *"documentation is handled centrally and the
MicroPython firmware is flashed manually."*

That is VertiGate's situation verbatim. It builds the interface on Windows and Linux, debug and
release, and publishes packages to GitHub and NuGet.org on release. Copy it, rename, adjust the
namespace, and this phase is essentially done.

**Then layer on the two release conventions that CI does not cover:**

1. **`RELEASE_NOTE.md`** — the FabLabs house template (already present, unfilled, in
   `fablabs-automatic-shelter`): PCB version(s), firmware version, key changes, BOM table, PCB
   fabrication parameters, JLCPCB ordering pointer.
2. **AIND's version-encoding release titles** — `hw{major}.{minor}.{patch}-fw{major}.{minor}.{patch}`,
   with hardware releases attaching STEP, schematic PDF, Gerbers, position files and BOM.

Adapt the firmware half to MicroPython the way `aeon_lineardrive` already does: **attach a
prebuilt firmware image to every release**, so that flashing does not require `mpremote` plus two
`mip install` calls against GitHub. The SWC FabLabs equivalent of AIND's SIPE part number needs
deciding — see §7.

Also add, since the shared workflow does not include it: a **generated-code freshness gate**
(regenerate from `device.yml`, then `git diff --exit-code`) and `device.yml` schema validation.
Without the former, the committed `Device.Generated.cs` silently drifts from the schema, which is
the single most likely way this setup rots.

**Versioning discipline (either option):** `firmwareVersion` in `device.yml`, the values passed
to `HarpDevice(...)`, the `R_VERSION` bytes, the release tag, and the package version must all
move together. Today three of those disagree.

---

## 7. Hardware

`### Hardware connections` in the README is literally `TBC`. This is the largest genuinely
unknown item.

- The board is a **NeuroPico** (RP2354). Firmware hard-codes `Pin(11/12/13)`, `Pin(7)` LED,
  `UART0 rx=Pin(1)` for the Harp sync clock, and `UART1 tx=Pin(8)/rx=Pin(9)` at 1 Mbaud for the
  servo. None of this is documented in the repo.

### 7.1 A board support library exists — and its pin map disagrees

`SainsburyWellcomeCentre/micropython-neuropico` has a stub README, but `neuropico.py` is not a
stub: it defines the full board pin map. **VertiGate does not import it**, and the hard-coded
literals conflict with it:

| NeuroPico constant | Pin | VertiGate uses that pin as |
| --- | --- | --- |
| `PIN_CLK_IN` | 13 | `Pin(13, Pin.OUT, value=1)` — driven as an output |
| `PIN_CLK_nEN` | 12 | `Pin(12, Pin.OUT, value=0)` — consistent with an active-low clock enable |
| `PIN_LED` | 16 (WS2812C RGB) | LED declared on `Pin(7)` instead |
| `PIN_PORT6_{A,B,C,D}` | 8, 9, 10, 11 | 8/9 = Dynamixel UART, 11 driven high |
| `PIN_PORT5_D` | 1 | `UART0 rx` for the sync clock |

One point does corroborate: `NeuroPico.CLK_SPEED = 100_000` matches VertiGate's
`UART(0, baudrate=100_000)`, so the sync clock rate is right.

This needs reconciling before anything is documented — the plausible readings are that VertiGate
targets a different board revision, or that it predates the library, or that the sync input is
genuinely wired to a port pin rather than `PIN_CLK_IN`. **Do not write the pinout table until
this is resolved**, and prefer importing `micropython-neuropico` over re-declaring literals, so
the board definition lives in one place for the whole fleet.
- Harp specifies a **physical sync connector** (`protocol/assets/PhysicalConnector.sch/.pdf`).
  Conformance means matching it, not merely having a UART.
- Needed: pinout table, power budget (XM430 stall current vs. supply), Dynamixel bus wiring,
  `hardwareTargets` tied to an actual PCB revision, and PCB/mechanical sources under `hardware/`.
- README inconsistency: it says RP2354 but links the `RPI_PICO2` UF2 in one place and `RPI_PICO`
  in another.

### `harp.device.pico-template` largely solves this — use it

This is the most immediately useful thing AIND brings to the analysis. The template ships **real
KiCad sources** for a generic RP2040/RP2350 Harp device, in two power variants
(`usb_isolated/` and `usb_powered_small/`), covering exactly the things listed above as unknowns:

- ground-isolated full-speed USB
- **a 3.5 mm audio jack for the Harp time-synchronisation signal** — a concrete, working answer
  to "what connector does the sync clock use", against which the NeuroPico's `UART0 rx=Pin(1)`
  can be checked
- the RP2040 plus required support components (2 MB external flash), and two power-supply chains
  (USB-direct or DC barrel jack) — the barrel-jack variant is the relevant one, since an XM430
  cannot be USB-powered
- PCBA layout with size hints for existing enclosures, DC barrel jack, USB-C, ground lug
- a `.gitignore` tuned to strip extraneous KiCad artifacts

Practical steps: diff the NeuroPico schematic against the template's sync and USB sections to
confirm connector conformance, and adopt the template's silkscreen convention (part number +
hardware semver + QR code to the repo). SWC has no SIPE numbering, so **decide the FabLabs
equivalent of a part number now** — it is referenced by the release convention in §6 and by
`hardwareTargets` in `device.yml`.

---

## 8. Documentation & ecosystem listing

- **README conventions:** shipped devices lead with a photo (`Assets/`), key features,
  connectivity, and an interface section pointing at the Bonsai package.
- **Docs site — and the two-tier reality.** `harp-tech.github.io` aggregates devices as **git
  submodules** under `src/`, built with docfx via `bonsai-rx/docfx-tools`. Every submodule is a
  `harp-tech/*` repo. **Not one AIND device appears there**, despite ten registered WhoAmIs and
  active production use.

  So ecosystem membership has two independent tiers:

  | Tier | Requirement | Open to SWC? |
  | --- | --- | --- |
  | **Registry** — a real, addressable Harp device | WhoAmI PR + conformant `device.yml` | yes, routine (§1) |
  | **harp-tech.org docs site** | repo lives in the `harp-tech` org | no, without donating the repo |

  The site does carry `images/light-logo-swc.svg`, so SWC is a recognised partner — but a logo is
  not a device listing. **Treat harp-tech.org inclusion as optional and out of scope.** Host
  VertiGate's documentation on the existing FabLabs site (already linked from the README) and let
  `whoami.yml` be the canonical discovery route. If harp-tech.org listing is genuinely wanted,
  that is a separate conversation with the maintainers about repo ownership, not a task in this
  plan.
- `harp-tech/community` (Sphinx) has a per-device page pattern under
  `source/Devices/alldevices/`. Its `Making-HARP/new_devices.rst` is an empty stub, so there is
  no formal written admission checklist — the de-facto checklist is: registered WhoAmI +
  conformant `device.yml` + published interface package + documentation.

---

## 9. Suggested sequencing

| Phase | Work | Estimate |
| --- | --- | --- |
| **0 — Decisions** *(blocking)* | Lock the register map (§2.2). Confirm the `Fablabs.*` namespace (§4). Agree the WhoAmI block with Aeon + FabLabs (§1.1). Decide Altium vs KiCad and the part-number scheme (§5, §7). Confirm staying on MicroPython (§3.2). | ~1 day |
| **1 — Identity** *(long lead time)* | One WhoAmI PR to `harp-tech/whoami` covering the **whole SWC fleet**, not just VertiGate. Do this first — it is the only item gated on an external maintainer. | ~1 day |
| **2 — Metadata** | Rewrite `device.yml` against draft-03 with the new map, correct `access` arrays, defaults, min/max, and units in descriptions. Validate against the published schema. | ~2 days |
| **3 — Firmware** | Implement the new map. Fix the S8 decode, reply-value mismatches, version arguments, blocking-boot hazard, event coalescing. Add `MotorFault` and `EnableEvents`. Move homing behind `Control.Calibrate`. | 1–2 weeks |
| **3b — Upstream microharp** *(parallel)* | `R_RESET_DEV` SAVE/RST_EE with non-volatile storage; `R_VERSION` PROTOCOL/CORE_ID/INTERFACE_HASH population; `R_CLOCK_CONFIG` semantics audit. | ~1 week |
| **4 — Repo + interfaces** | Adopt the `aeon_lineardrive` layout (§5 Option C), per-directory licenses, copy its `.config/dotnet-tools.json` and `software/build/`, generate and commit the Bonsai + Python interfaces, rewrite the Bonsai example against typed operators. | ~3 days *(mostly copy-and-rename from `aeon_lineardrive`)* |
| **5 — Release process** | Copy `Aeon.LinearDrive.yml`; add the freshness gate and schema validation. Fill in `RELEASE_NOTE.md` from the FabLabs template; adopt `hw*-fw*` release titles; attach a prebuilt firmware image. | ~2 days |
| **6 — Hardware & docs** | **Reconcile the NeuroPico pin map first (§7.1).** Then diff against `harp.device.pico-template` for sync-connector and USB conformance; pinout table; `.img/`, `eCAD/`, `mCAD/`; silkscreen part number; README rewrite; FabLabs docs page. | 1–2 weeks *(depends on what exists offline)* |
| **7 — Fleet follow-up** *(optional, separate)* | Apply the same treatment to `fablabs-automatic-shelter` (**register addresses 15–26 are a hard spec violation**), `aeon_lineardrive` (`whoAmI: 0000`, stale schema URL) and `virt-hunt-drv` (no `device.yml`). Propose migrating them onto the generation-3 stack. | separate project |

---

## 10. Risks

- **WhoAmI 5350 is unclaimed** and nothing stops another submission taking it. Highest-urgency,
  lowest-effort item.
- **No MicroPython precedent in the ecosystem** *(downgraded from the first draft)*. Every other
  device is C/C++ (ATxmega, Pico SDK), and `micropython-microharp` is SWC's own core rather than
  an upstream-blessed one. But AIND demonstrates that running your own core, your own namespace
  and your own Python library is normal, and `micropython-microharp` already implements more core
  registers (0–19) than AIND's production `harp.core.pico` does (0–17). The residual risk is
  narrow: `CORE_ID` allocation, and the fact that `mpremote` is not a bootloader, so
  `harp-regulator` / `regulator` cannot update this device.
- **Firmware distribution to non-developers.** AIND ships a UF2 per release; VertiGate requires
  `mpremote` plus two `mip install` steps against GitHub. Fine for the FabLab, awkward for a
  visiting experimenter. `aeon_lineardrive` already solves this by attaching a prebuilt image to
  each release — adopt that rather than inventing something.
- **Fleet fragmentation.** SWC runs three incompatible MicroPython Harp stacks (§0.6.2), and
  `micropython-microharp`'s rewrite means `aeon_lineardrive` must pin a specific commit and warn
  about it in its README. VertiGate is on the newest stack, so the fleet either converges on it
  or the split hardens. That is a FabLabs/Aeon decision beyond this repo, but VertiGate's choices
  here will set the precedent either way.
- **Two placeholder WhoAmIs are already deployed** (`0000`, `0x1234`). Registering VertiGate
  alone leaves them in the field; hence the block reservation in §1.1.
- **The NeuroPico pin map is contested** (§7.1). The board library and the firmware disagree on
  what pins 12, 13 and 16 are for. Until that is settled, any pinout documentation would be
  guesswork, and it is on the critical path for Phase 6.
- **Silent wrong data in the experimental record.** The startup register dump (§3.3) reports
  `Speed=0, Torque=0, Status=Idle` for a device actually running at 255/35 and sitting down. No
  error is raised, so a workflow logging rig configuration from the dump records values that were
  never true. This is the most damaging class of defect in the repo precisely because it is
  invisible — rank it above the S8 decode bug when scheduling Phase 3.
- **The register map change is breaking.** Cheap now, expensive after the first release — hence
  Phase 0.
- **Convention drift.** Mixing the two ecosystems half-and-half (harp-tech layout, AIND tooling,
  neither release convention) is worse than committing to either. Phase 0 exists to prevent this.
- **Hardware documentation may not exist yet** in any form. Still the item most likely to blow
  the estimate — though `harp.device.pico-template` now supplies a reference schematic to check
  against rather than a blank page.
