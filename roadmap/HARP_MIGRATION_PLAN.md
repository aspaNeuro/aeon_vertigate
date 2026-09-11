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
  3000:
    <<: *swc
    name: VertiGate
    repositoryUrl: https://github.com/SainsburyWellcomeCentre/fablabs-VertiGate
    projectUrl: <fablabs documentation page>
```

`name` must match `^[a-zA-Z][a-zA-Z0-9_]*$` — `VertiGate` is fine. The id pattern in
`whoami.json` accepts 3- and 4-digit values, so anything in the proposed range is format-legal;
it simply needs to be claimed.

> **VertiGate's id changes.** The current `5350` sits outside the proposed SWC range (§1.1), so
> adopting the block moves VertiGate to an id within it — `3000` above, pending the teams' own
> allocation. That touches `device.yml`, `main.py`, `bonsai/example.bonsai` and the README. Cheap
> now, since nothing is released and no interface package exists; not cheap later.

**Until this merges, the id is squatted, not owned.**

**Precedent:** AIND added its own `aind` owner key and ten devices (1400–1411) pointing at
repositories in its own GitHub organisation. This is a routine, low-friction PR — the registry
is deliberately open to external institutions, and SWC is already a recognised ecosystem
partner. Expect this to be the easiest external interaction in the whole plan.

### 1.1 Reserve a block, not a single id

Per §0.6, **no SWC device holds a registered WhoAmI**: `aeon_lineardrive` ships `0000`,
`fablabs-automatic-shelter` ships `0x1234` (4660), `virt-hunt-drv` sets none, and VertiGate
claims an unregistered 5350. Two of those placeholders are actively deployed, and `0x1234` is a
value another institution could legitimately be allocated.

Since one PR is being opened anyway, **register the whole SWC fleet at once** rather than one id
per device, following AIND's 1400–1411 pattern but sized for an institution running several
device-producing groups.

**Proposed reservation: `3000`–`3500` for SWC devices.**

The range is clear — the registry's highest current allocation is 2110, and nothing above 2110 is
assigned — and it is well away from both the Champalimaud clusters and AIND's 1400s, so it leaves
room for the existing owners to grow contiguously.

Initial allocations to propose in the same PR:

| Id | Device | Repo |
| --- | --- | --- |
| 3000 | `VertiGate` | `fablabs-VertiGate` |
| 3001 | `LinearDrive` | `aeon_lineardrive` (currently ships `0000`) |
| 3002 | `AutomaticShelter` | `fablabs-automatic-shelter` (currently ships `0x1234`) |
| 3003 | `VirtHunt` | `virt-hunt-drv` (sets none) |

Two things to prepare for:

- **500 ids is a large ask.** AIND took twelve. Expect harp-tech to want a rationale — the honest
  one is that SWC has multiple independent groups building Harp devices (FabLabs, Aeon, and
  others), and a block avoids a stream of one-off PRs and the placeholder ids that appear while
  people wait. If the maintainers push back, a smaller block that can be extended later is a
  reasonable fallback; the important part is having *a* range rather than scattered ids.
- **A reserved block needs an owner.** Blocks rot when nobody tracks them. Whoever holds it should
  keep a short allocation list — ideally in `fablabs-documentation` — so the next device takes the
  next free id rather than inventing another `0x1234`.

Confirm the range and the initial allocations with the Aeon and FabLabs teams before submitting,
since the PR commits their devices too.

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
   Every comparable Harp motion device uses a functional name. It is also **write-only, so the
   register dump skips it** — a connecting controller cannot learn the commanded target (§3.3).
2. **No position readback.** There is no way to ask where the gate is, only which state-machine
   bucket it is in. Comparable devices expose a measured value as an Event
   (`faststepper` → `Encoder`, `syringepump` → `Protocol`).
3. **No stop, no enable/disable, no re-home command.** `Gate.stop()` exists in firmware but is
   unreachable over the wire. Homing only ever happens once, at boot.
4. **No error/fault register.** Dynamixel stalls, comms timeouts and out-of-travel conditions
   are invisible to the host. The spec's guidance is that such conditions should surface as an
   event on a dedicated register rather than as error replies.
5. **No way to gate event traffic.** Once a `Position` event streams, a host that only cares
   about end-stop transitions must filter it downstream. Harp devices provide an off switch —
   either a standalone `EnableEvents` mask (`syringepump`, `stepperdriver`, `behavior`) or paired
   bits inside `Control` (`faststepper`).

Proposed map, aligned with `faststepper` / `syringepump` naming:

| Addr | Name | Type | Access | Purpose |
| --- | --- | --- | --- | --- |
| 32 | `Control` | U8 | Write | bitmask, all 8 bits: `EnableMotor` / `DisableMotor`, `Stop`, `Calibrate`, `Enable`/`DisablePositionEvent`, `Enable`/`DisableTelemetryEvent` |
| 33 | `TargetPosition` | **U8** | **Read**, Write | absolute target, unchanged 1.2 mm scale — gains read access so it appears in the register dump |
| 34 | `GateState` | U8 | Read, Event | groupMask `Idle` / `Up` / `Down` / `Moving` / `Error` |
| 35 | `Speed` | U8 | Read, Write | as today, with default/min/max declared |
| 36 | `Torque` | U8 | Read, Write | as today |
| 37 | `CalibrationOffset` | S8 | Read, Write | renamed from `Offset`, per syringepump convention |
| 38 | `Position` | U16 | Read, Event | *measured* position from the servo, in encoder counts (25 µm) |
| 39 | `MotorFault` | U8 | Read, Event | bitmask: `Stall`, `Overload`, `CommsTimeout`, `TravelLimit` |
| 40 *(optional)* | `ServoTelemetry` | U16×n | Read, Event | present current / temperature / voltage |

Keeping `Up` / `Down` as a convenience is fine — express it as two `Control` bits alongside the
position register.

> **Decision (2026-09-09): address 33 stays U8.** 1.2 mm is adequate for this mechanism, so the
> target is not widened. This is what makes the whole map **purely additive on the wire** — every
> existing register keeps its address and payload type, and only unused addresses gain registers.
> Existing Bonsai workflows keep working unmodified.
>
> An earlier draft proposed U16 and described `0`/`255` as "magic values" barred by the spec's
> *Register polymorphism* section. That reasoning was wrong: `lower_down()` calls `move(0)`,
> `raise_up()` calls `move(255)`, and `move()` is a plain linear map, so the endpoints are
> ordinary values on the same scale and the special-casing is only an idempotence guard.
>
> See [`REGISTER_MAP_COMPARISON.md`](REGISTER_MAP_COMPARISON.md) for the full implemented-vs-proposed
> analysis, the cost breakdown, and a reduced subset if less churn is wanted.

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

### 3.4 Version registers: what tooling actually reads

The two version problems listed in §3 are **not equally urgent**, and the difference only becomes
clear once you check what consumes each field.

#### The deprecated block is what everything reads

`Bonsai.Harp`'s `Device` operator reads registers 0, 1, 2, 6, 7 on every connect and prints them
to the Bonsai console; `Bonsai.Harp.Design`'s Device Setup dialog shows the same block. Nothing in
`bonsai-rx/harp` references `R_VERSION` (19) or its interface hash at all, and `HarpVersion` is
major.minor only.

So the **deprecated** registers are the live ones in practice. Side by side with a current
harp-tech device (`OutputExpander`, WhoAmI 1108):

| Device Setup field | Register(s) | OutputExpander | VertiGate today | Should be |
| --- | --- | --- | --- | --- |
| DeviceName | 12 | Output Expander | VertiGate | ✓ |
| FirmwareVersion | 6, 7 | 2.2 | **1.0** | 0.1 |
| CoreVersion | 4, 5 | 1.13 | **0.0** | 1.13 |
| HardwareVersion | 1, 2 | 1.0 | **1.0** | 0.1 |
| AssemblyVersion | 3 | 0 | 0 | ✓ — deprecated, 0 is normal |
| WhoAmI | 0 | 1108 | 5350 | ✓ once registered (§1) |
| SerialNumber | 13 | 65535 | 0 | — |

Three of seven fields are wrong or blank, and they are the fields a person reads when identifying
a device on a rig.

**`CoreVersion` (registers 4–5)** is the version of the Harp *core library* the firmware is built
on. Formally that is not the protocol version — but Champalimaud's core versions track the
protocol document, so in practice a device reporting `1.13` is saying it implements Harp Device
spec **v1.13.0**, which is the current and only tag on `harp-tech/protocol`. Set VertiGate's to
`1.13` to match that reading, rather than to microharp's own release number.

#### Fixes

- **`fw_version` / `hw_version`:** pass `fw_version=(0, 1)`, `hw_version=(0, 1)` to
  `HarpDevice(...)`. One line. microharp otherwise defaults both to `(1, 0)`.
- **`CoreVersion`:** awkward — `install_common_registers` has **no parameter for it**, unlike the
  firmware and hardware versions. Either add the argument upstream, or write registers 4–5
  directly after construction.
- **Stop hand-maintaining versions in two files.** `device.yml` and `main.py` drifting apart is
  exactly how this happened. Generate a `firmware/_version.py` from `device.yml` at deploy/CI time
  and guard it with the same freshness gate as the C# interface (§6).

#### `R_VERSION` PROTOCOL / CORE_ID / INTERFACE_HASH — no consumer yet

Worth doing eventually, but nothing reads these today, and each has an unresolved question:

- **PROTOCOL** (bytes 0–2): `1.13.0`. A microharp constant, not per-device.
- **CORE_ID** (bytes 9–11): three characters naming the core. **There is no registry** — the spec
  gives one line and no examples, and no shipped core implements `R_VERSION` at all (`core.pico`
  and AIND's both stop at `TAG = 17`). Picking a code (`mpy`?) means asking harp-tech first.
- **INTERFACE_HASH** (bytes 12–31): SHA-1 of `device.yml`. Three traps: (a) `device.yml` is not on
  the board, so it must be computed at build time into the generated version module; (b) the spec
  says little-endian, but a digest is a 20-byte string rather than an integer and **no reference
  implementation exists anywhere in the ecosystem** to disambiguate — whoever ships first defines
  it; (c) line endings change the digest, so pin `device.yml` to LF in `.gitattributes` *before*
  baking in any hash, or Windows checkouts and CI will disagree permanently.

Also note `device.yml`'s `firmwareVersion` schema is major.minor only, while `R_VERSION` wants
major.minor.patch — the patch bytes have no source in the schema. Either fix them at `0`, or take
them from the release tag.

#### Order

1. Pass `fw_version` / `hw_version` — fixes what Bonsai reads, prints and displays.
2. Set `CoreVersion` to `1.13`.
3. Add the `.gitattributes` LF rule for `device.yml`.
4. Generate `_version.py`; wire the freshness gate.
5. Ask harp-tech: a CORE_ID for MicroPython, and the INTERFACE_HASH byte order.
6. Extend microharp to accept core version, protocol, core id, hash and patch versions — fleet-wide
   benefit, per the upstream split in §3.

Steps 1–3 are worth doing regardless. Steps 4–6 only pay off once something validates the hash.

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
hardware/                    → git submodule: the whole hardware design, own repo
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
the hardware repository is populated — a migration may be in flight, and this is a FabLabs-wide
call, not a VertiGate one.

### Hardware as a submodule

**Proposal: the entire hardware design lives in its own repository, included here as a git
submodule at `hardware/`. This repository then contains only firmware, host software and
metadata.**

Why this is the better split:

- **The licence boundary becomes a repository boundary.** This repo is BSD-3, full stop. The
  hardware repo carries CERN-OHL-W and whatever component terms apply. No licence map, no
  per-directory `LICENSE` files, no prose explaining which paragraph governs which folder.
- **Hardware and firmware version independently.** They already do — AIND's release convention
  encodes `hw{major}.{minor}.{patch}-fw{major}.{minor}.{patch}` precisely because they move at
  different rates. Separate repos make that natural instead of something the release title has to
  paper over.
- **The pin is a compatibility record.** A submodule pinned at a commit states, in a
  machine-checkable way, which hardware revision a given firmware was validated against. For a lab
  device where several board revisions circulate, that is worth more than the convenience it costs.
- **Binary CAD stays out of the firmware history.** Altium and Inventor files are large and opaque
  to diff. Software contributors cloning for a firmware fix do not pay for them.

#### Constraint: submodules cannot be subdirectories

Git submodules bring in a whole repository, not a path within one. So "`hardware/` is a submodule"
rules out a single shared `fablabs-hardware` repo containing every device — that would drop every
device's CAD into VertiGate's `hardware/`.

The workable shapes are therefore:

| Shape | Implication |
| --- | --- |
| **One hardware repo per device** (e.g. `fablabs-VertiGate-hardware`) | ✅ clean pin, clean licence boundary. 2× repo count across the estate. |
| Shared repo holding *only* reusable component models | ✅ works, but then per-device CAD stays in the device repo, which is not what is proposed here |
| Shared repo holding all devices' hardware | ❌ not expressible as a submodule at `hardware/` |

So this implies **a hardware repo per device**. Worth confirming that the FabLabs team is happy
with roughly double the repositories before committing to it.

#### What this diverges from

Both existing SWC conventions keep hardware in the device repo — every `fablabs-*` repo has
`eCAD/` and `mCAD/` alongside `firmware/`, and so does `aeon_lineardrive`. This is a FabLabs-wide
call, not a VertiGate one, and VertiGate is a convenient place to try it precisely because it has
no hardware files yet.

Three practical frictions to plan for:

- `git clone --recursive`, or an empty `hardware/` and a confused colleague. Worth a line in the
  README and in CI checkout steps.
- `altium-viewer.json` sits at the repo root in the `fablabs-*` repos, and the Altium 365 Viewer
  integration via `fablabs-documentation` points at a repository. Check what moves with the CAD.
- Releases split into two streams. AIND already solves this by having each firmware release state
  the hardware revisions it is compatible with — adopt that wording rather than inventing one.

#### The provenance rule still applies, wherever the files live

A submodule changes *where* files are hosted, not *whether* SWC distributes them. A public
hardware repo containing SamacSys- or TraceParts-derived models carries exactly the same exposure,
just relocated. So the split is still by provenance:

| Model | Where it goes |
| --- | --- |
| SWC's own design and component models | the hardware repo, under CERN-OHL-W |
| Redistributable third-party (official vendor STEP, models carrying an explicit grant such as CC BY-ND) | the hardware repo, with attribution preserved |
| Portal-sourced, non-transferable (SamacSys, TraceParts, GrabCAD, Ultra Librarian) | **nowhere in git** — referenced by MPN as CERN-OHL *Available Components* |

Moving encumbered files into a separate repository does not make distributing them lawful. It only
makes the audit one-time, and `fablabs-kicad-library` is the existing precedent for shared
component assets that could hold the redistributable ones.

### Licensing — adopt the Aeon model (CERN-OHL), not the FabLabs CC BY-SA convention

Two SWC conventions currently diverge, and VertiGate has to pick one before it publishes any
hardware.

| | FabLabs today | Aeon proposal ([`aeon_roadmap#69`](https://github.com/SainsburyWellcomeCentre/aeon_roadmap/issues/69)) |
| --- | --- | --- |
| Hardware | **CC BY-SA 4.0**, full text as the single root `LICENSE` | **CERN-OHL-W 2.0** |
| Software / firmware | BSD-3 (stated in the README only) | BSD-3 |
| Third-party vendor CAD | bundled in the repo | **Available Components** — referenced by MPN, not redistributed |

`fablabs-valve-driver`, `-automatic-shelter`, `-lick-detector-piezo` and `-environmental-sensor`
all carry the CC BY-SA 4.0 text as their root `LICENSE`.

**Decision: follow the Aeon model.** CC BY-SA is a poor fit for hardware on four counts:

1. **It does not define "source" for hardware.** ShareAlike triggers on "Adapted Material", but CC
   has no answer to whether a fabricated board, or a Gerber, is an adaptation of a schematic.
   CERN-OHL defines *Covered Source* and *Product* explicitly and states when reciprocity attaches
   to a manufactured object.
2. **No patent grant.** That is the difference between "you may copy my drawings" and "you may
   build and sell the thing". CERN-OHL includes one.
3. **Creative Commons themselves advise against it** for software, and steer hardware projects
   toward purpose-built licences.
4. **No Available Components concept.** This is the formal basis for referencing proprietary
   vendor CAD without redistributing it — the mechanism `aeon_roadmap#69` depends on, and which
   CC BY-SA simply lacks.

**Variant: CERN-OHL-W**, matching the Aeon default. Reciprocal on the design files, while a rig
that merely *uses* a VertiGate is unaffected. `-S` would be awkward for a device embedded in
larger setups; `-P` gives away reciprocity for no benefit here.

#### How the two licences actually relate

Neither is a subset of the other, and they are **not compatible**. Each grants and requires things
the other does not:

| | CC BY-SA 4.0 | CERN-OHL-W 2.0 |
| --- | --- | --- |
| Attribution | ✅ | ✅ |
| Copyleft / reciprocity | ✅ on "Adapted Material" | ✅ on conveying a **Product** |
| **Patent licence** | ❌ **explicitly excluded** — §2(b)(2): *"Patent and trademark rights are not licensed under this Public License"* | ✅ §7.1: *"perpetual, worldwide… irrevocable patent license to Make, have Made, use, offer to sell, sell, import"* |
| Defined "Source" for hardware | ❌ no concept | ✅ Covered Source / Complete Source |
| Available Components | ❌ none | ✅ parts available *"with sufficient rights and information… to enable it to be Made… or sourced and used to Make the Product"* |
| Obligation attaches to physical objects | ❌ unclear — copyright subsists in the drawing, not the thing built from it | ✅ §3.2 / §4.1, triggered by conveying a Product |
| Sui generis database rights | ✅ §4 | ❌ |
| Anti-DRM / TPM clause | ✅ | ❌ |
| Moral rights waiver | ✅ | ❌ |

CERN-OHL is stronger on the hardware-specific axes; CC BY-SA is broader on general-copyright
axes. They are orthogonal in places, not nested.

CC BY-SA 4.0 does have a "Compatible License" mechanism, but Creative Commons designates only
specific licences under it (GPLv3, one-way) and **CERN-OHL is not among them**. So CC BY-SA
material cannot be absorbed into a CERN-OHL project, nor the reverse.

**What that means for migrating the FabLabs estate.** A copyright holder is not bound by the
licence it previously chose: where SWC authored the designs, SWC can license future versions under
CERN-OHL-W regardless of what shipped before. Two caveats:

1. **CC licences are irrevocable.** Anything already published under CC BY-SA stays available under
   CC BY-SA permanently. The licence changes going *forward*; past releases cannot be clawed back.
2. **External contributions need consent.** If anyone outside SWC contributed hardware design to
   those repos, relicensing their contribution requires their agreement. Check contributor lists
   before announcing a change.

For VertiGate this is moot — no hardware files exist, so there is nothing to relicense.

**It is also not either/or per repository.** CERN-OHL governs *design* files; CC BY-SA remains a
good choice for documentation, photos and diagrams. That is precisely why the target below is a
licence **map** rather than a single root `LICENSE`.

> Licence reading, not legal advice. Worth UCL's research office confirming before anything is
> announced across repositories.

#### Immediate defect, independent of the above

VertiGate is the only `fablabs-*` repo with **no hardware files at all**. Its root `LICENSE` is
BSD 3-Clause while the README badge says CC BY-SA 4.0 — so the badge advertises a licence for
content that does not exist, and misrepresents the licence on the content that does. Point the
badge at BSD-3 until hardware lands. One line, worth doing now.

#### Target structure, when hardware lands (Phase 6)

With hardware moved to its own repository (see "Hardware as a submodule" above), the licence map
mostly disappears — the repository boundary carries it instead:

**This repository:**

```
LICENSE          BSD-3-Clause — firmware, host software, device.yml
hardware/        submodule; governed entirely by the hardware repo's own terms
```

**The hardware repository:**

```
LICENSE          CERN-OHL-W-2.0 — the design we authored
mCAD/README.md   Available Components: MPN + vendor download link per part
```

This is the main practical argument for the split: instead of per-directory `LICENSE` files and a
root map explaining which paragraph governs which folder, each repository has one licence and says
so once. Documentation, photos and diagrams can stay CC BY-SA in either repo if that is preferred;
that choice no longer has to be encoded in a map.

Plus SPDX headers, and a standing rule never to commit portal-sourced CAD.

Note the argument in `aeon_roadmap#69` that **absence of a licence does not fix this**: leaving
hardware unlicensed until someone decides still distributes any third-party files, and leaves
SWC's own PCB work all-rights-reserved. So this is decided *before* hardware is published, not
after — the same cheap-now / expensive-later shape as the register map.

#### Worth flagging to the FabLabs team

The third-party CAD problem may already be live across the estate. Four published repos carry
vendor CAD under `ConvertedComponents/`:

| Repo | Files |
| --- | --- |
| `fablabs-monitor-blanking` | 50 |
| `fablabs-lick-detector-piezo` | 39 |
| `fablabs-valve-driver` | 19 |
| `fablabs-environmental-sensor` | 18 |

The filenames carry `CMP-xxx-xxxx-x` identifiers — SamacSys / Component Search Engine numbering —
alongside vendor part numbers such as TE's `BNC-TE-5227222` and Samtec's `853-004-213R00Y`. Those
are the portals `aeon_roadmap#69` identifies as granting use-in-your-own-design rights only.

This is an inference from filenames, not an audit, and needs checking rather than acting on. But
if it holds, the position is worse than `aeon_lineardrive`'s was: a single root CC BY-SA does not
merely redistribute those files, it purports to **license them share-alike to the public** —
overclaiming rights on third-party IP, which is the second mistake `aeon_roadmap#69` names.

VertiGate's advantage is that it is empty: it can adopt the right structure from the start rather
than remediate, which makes it a reasonable pilot for whatever FabLabs settles on. The actual call
belongs to the team, and probably to UCL's research office.

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
| **0 — Decisions** *(blocking)* | Lock the register map (§2.2). Confirm the `Fablabs.*` namespace (§4). Agree the WhoAmI block with Aeon + FabLabs (§1.1). Decide Altium vs KiCad and the part-number scheme (§5, §7). Confirm staying on MicroPython (§3.2). Take the licensing decision to FabLabs (§5) — **CERN-OHL-W proposed**, aligning with `aeon_roadmap#69`. | ~1 day |
| **1 — Identity** *(long lead time)* | One WhoAmI PR to `harp-tech/whoami` reserving **3000–3500 for SWC** and allocating ids across the fleet, not just VertiGate (§1.1). Do this first — it is the only item gated on an external maintainer. Note VertiGate's id moves off 5350. | ~1 day |
| **2 — Metadata** | Rewrite `device.yml` against draft-03 with the new map, correct `access` arrays, defaults, min/max, and units in descriptions. Validate against the published schema. | ~2 days |
| **3 — Firmware** | Implement the new map. Fix the S8 decode, reply-value mismatches, version arguments, blocking-boot hazard, event coalescing. Add `MotorFault` and the `Control` event-gating bits. Move homing behind `Control.Calibrate`. | 1–2 weeks |
| **3b — Upstream microharp** *(parallel)* | `R_RESET_DEV` SAVE/RST_EE with non-volatile storage; `R_VERSION` PROTOCOL/CORE_ID/INTERFACE_HASH population; `R_CLOCK_CONFIG` semantics audit. | ~1 week |
| **4 — Repo + interfaces** | Adopt the `aeon_lineardrive` layout (§5 Option C), per-directory licenses, copy its `.config/dotnet-tools.json` and `software/build/`, generate and commit the Bonsai + Python interfaces, rewrite the Bonsai example against typed operators. | ~3 days *(mostly copy-and-rename from `aeon_lineardrive`)* |
| **5 — Release process** | Copy `Aeon.LinearDrive.yml`; add the freshness gate and schema validation. Fill in `RELEASE_NOTE.md` from the FabLabs template; adopt `hw*-fw*` release titles; attach a prebuilt firmware image. | ~2 days |
| **6 — Hardware & docs** | **Reconcile the NeuroPico pin map first (§7.1).** Then diff against `harp.device.pico-template` for sync-connector and USB conformance; pinout table; `.img/`, `eCAD/`, `mCAD/`; silkscreen part number; README rewrite; FabLabs docs page. | 1–2 weeks *(depends on what exists offline)* |
| **7 — Fleet follow-up** *(optional, separate)* | Apply the same treatment to `fablabs-automatic-shelter` (**register addresses 15–26 are a hard spec violation**), `aeon_lineardrive` (`whoAmI: 0000`, stale schema URL) and `virt-hunt-drv` (no `device.yml`). Propose migrating them onto the generation-3 stack. | separate project |

---

## 10. Risks

- **No SWC device holds a registered WhoAmI**, and nothing stops another institution being
  allocated the ids currently in the field (`5350`, `0x1234`, `0000`). The proposed 3000–3500
  reservation (§1.1) is the highest-urgency, lowest-effort item in the plan.
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
