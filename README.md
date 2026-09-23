# VertiGate

[![GitHub release](https://img.shields.io/github/v/release/SainsburyWellcomeCentre/aeon_vertigate?style=flat-square&cacheSeconds=3600)](https://github.com/SainsburyWellcomeCentre/aeon_vertigate/releases)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg?style=flat-square)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/SainsburyWellcomeCentre/aeon_vertigate?style=flat-square)](https://github.com/SainsburyWellcomeCentre/aeon_vertigate/issues)

A [Harp](https://harp-tech.org/) device that controls a vertical gate. A Dynamixel XM430-W210 servo moves the gate.

VertiGate is a Harp device on a USB CDC serial port. Its WhoAmI is **3002**. That value is proposed for the SWC block 3000 to 3500. It is not registered yet. The gate has 256 positions. 0 is fully down and 255 is fully up. The device reports the gate state as a Harp event.

## 🔧 Features

- Harp protocol over USB CDC at 1 Mbaud, with clock synchronisation
- Position control with one command byte (0 to 255)
- Speed and torque limits that can be changed at runtime
- An offset register for fine mechanical calibration

## 🚀 Getting Started

### Hardware connections

TBC

### Firmware installation

> **Which MicroPython build.** The NeuroPico uses an RP2354A with **2 MB** of flash inside the chip.
> Do not use the `RPI_PICO2` build. It assumes 4 MB and its file system wraps around onto the
> firmware. The board works for a while, then freezes or corrupts its files. Use the
> **`SEEED_XIAO_RP2350`** build, **v1.29.0 or later**. It is made for an RP2350A with 2 MB and has
> no board-specific code that affects VertiGate. Older versions of that build have the same 4 MB
> problem.

1. **Enter the bootloader.** Hold BOOTSEL and press reset (or plug the board in while holding
   BOOTSEL). A drive named `RP2350` appears.
2. **Erase the file system, first time only.** Do not use `flash_nuke.uf2`. That file is an
   RP2040 image and this board is an RP2350, so the boot loader ignores it. Clear the file
   system from the REPL instead, as
   [docs/firmware-image.md](docs/firmware-image.md) describes. A board straight from the
   factory needs nothing here.
3. **Flash MicroPython.** Copy
   [SEEED_XIAO_RP2350-20260824-v1.29.0.uf2](https://micropython.org/resources/firmware/SEEED_XIAO_RP2350-20260824-v1.29.0.uf2)
   to the drive (newer releases: [micropython.org/download/SEEED_XIAO_RP2350](https://micropython.org/download/SEEED_XIAO_RP2350/)).
   The board reboots and a COM port appears.
4. **Install the host tools.** Install [uv](https://docs.astral.sh/uv/), then run from the repository root:

   ```bash
   uv sync
   ```

   This creates a `.venv` with `mpremote` and `pyserial`. Add `--all-extras` to also install the
   packages the generated Python interface needs.
5. **Install the libraries.** Replace `COM3` with your port:

   ```bash
   uv run mpremote connect COM3 mip install github:SainsburyWellcomeCentre/micropython-dynamixel
   uv run mpremote connect COM3 mip install github:SainsburyWellcomeCentre/micropython-microharp
   ```

6. **Copy the firmware.** From the repository root, run:

   ```bash
   uv run mpremote connect COM3 cp -r firmware/. :
   uv run mpremote connect COM3 reset
   ```

7. **Check the ports.** After the reset the board shows **two** COM ports. The first is the
   MicroPython REPL. The second is the Harp interface. Use the second one in Bonsai.

These steps put the Python files on the board file system, which is what you want while you
work on the firmware. For a release there is one `.uf2` that holds MicroPython, the firmware
and both libraries. See [docs/firmware-image.md](docs/firmware-image.md).

### Updating the firmware

The firmware keeps the REPL on its own port, so `mpremote` can reach the board while the
device is plugged in. **`mpremote` stops the running firmware.** It enters the raw REPL,
which raises `KeyboardInterrupt` inside the device loop, and the Harp port disappears. Copy
the files, then reset:

```bash
uv run mpremote connect COM3 resume cp -r firmware/. :
uv run mpremote connect COM3 reset
```

The Harp port comes back about 10 seconds after the reset. If it does not come back at all,
unplug the board and plug it in again. The USB stack can stay down after several soft
resets in a row.

If the device does not start, read the log it writes on the board:

```bash
uv run mpremote connect COM3 resume cat :error.log
```

### Testing

There are two tests. The first drives the device and checks what it does. The second checks
the device against the Harp specification. Both use the Harp port.

**The hardware test.** With the board connected and the Harp port known (for example `COM4`):

```bash
uv sync --all-extras
uv run vertigate-test --port COM4
```

It runs 28 checks and prints `PASS` or `FAIL` for each one. It takes about a minute, because
it reboots the board four times to prove the non-volatile settings survive. Add `--no-reboot`
to skip that part, which leaves 9 checks and takes a few seconds.

The test works with or without a servo. Without a servo the gate reports the `Error` state,
and the test expects that.

**The conformance test.** See [Checking the device against the specification](#checking-the-device-against-the-specification).

### Basic usage

Write one byte to the **TargetPosition** register (`0x21`):

| Value     | Effect                          |
| --------- | ------------------------------- |
| `0`       | Lower the gate fully (DOWN)     |
| `255`     | Raise the gate fully (UP)       |
| `1`–`254` | Move to a position in between   |

Read the **GateState** register (`0x22`), or subscribe to its event, to follow the gate state.

### The example workflow

Open `docs/workflows/GateControl.bonsai`. It owns the device and nothing else.
The panel it shows is `docs/workflows/Extensions/GateControlPanel.bonsai`,
built with `Bonsai.Gui`.

| Control | What it does |
| ------- | ------------ |
| Lower down, Raise up | Move the gate to an end stop |
| Calibrate, Stop, Enable motor, Disable motor | Send one `Control` command |
| Position slider | Move the gate. The gate follows the slider |
| Speed, Torque, Calibration offset | Set a value, then press Apply |

The three settings need an Apply button because `device.yml` marks them
non-volatile. The firmware stores every write on the flash. It also switches
the motor off and on to change the speed or the torque. A slider that wrote on
every step would do both many times a second.

Each of those sliders starts at the value the device reports. The label beside
it shows what the device holds now. The two can differ. The firmware masks
`Torque` to 7 bits, so it stores a write of 200 as 72.

Set the port on the `VertiGate.Device` node before you start. Use the Harp
port, not the REPL port.

### The pinned Bonsai environment

`.bonsai/` pins the Bonsai version and the packages, so everyone runs the
example workflow on the same environment. It holds Bonsai 2.9.1, `Bonsai.Harp`,
`Bonsai.Harp.Design`, which is the one that shows the Device Setup dialog, and
`Bonsai.Gui`, which builds the panel. Bonsai installs itself into that folder
on first use. `.gitignore` keeps the downloaded files out.

`Aeon.VertiGate` is in that list too, so the workflow opens with the typed
operators already loaded. The pin is `42.42.42-dev0`, the version every local
build produces. `.bonsai/NuGet.config` points at `artifacts/package/release`,
so Bonsai finds it.

**Build the package before you start Bonsai for the first time**, or it will
not find `Aeon.VertiGate`:

```bash
dotnet pack software/Aeon.VertiGate.sln -c Release
```

#### If you change `device.yml`

The build does not generate the interfaces. It compiles the `.Generated.cs`
files that are on disk. But it does copy the new `device.yml` into the package.
So a package built without the generate step holds a specification that does
not match its own operators. Nothing warns you.

Generate first, then pack:

```bash
dotnet harp.toolkit generate interface csharp device.yml --namespace Aeon.VertiGate --output software/Aeon.VertiGate
dotnet harp.toolkit generate interface python device.yml --output src/aeon/vertigate
dotnet pack software/Aeon.VertiGate.sln -c Release
```

Every local build has the same version, `42.42.42-dev0`. Bonsai keeps a copy of
each version it installs, and it does not read a version it already has. So
Bonsai keeps the old operators until you remove its copy. Close Bonsai, then
run this from the repository root:

```bash
rm -rf .bonsai/Packages/Aeon.VertiGate.42.42.42-dev0
```

Start Bonsai again. It installs the new package from
`artifacts/package/release`.

## 🧩 Interfaces

`device.yml` describes every register. Two interfaces are generated from it:

- **Bonsai**, in `software/Aeon.VertiGate/`. It gives one typed operator per
  register, instead of raw addresses and payload types.
- **Python**, in `src/aeon/vertigate/device.py`. It works with
  [harp-python](https://github.com/harp-tech/python).

Both are committed. You only need to generate them again after you change
`device.yml`.

### Generating them again

`harp.toolkit` is pinned in `.config/dotnet-tools.json`, so everyone uses the
same version. Install it once per clone:

```bash
dotnet tool restore
```

Then, from the repository root:

```bash
dotnet harp.toolkit generate interface csharp device.yml --namespace Aeon.VertiGate --output software/Aeon.VertiGate
dotnet harp.toolkit generate interface python device.yml --output src/aeon/vertigate
```

Commit the result. Do not edit the generated files by hand. They say so at the
top, and the next run would overwrite the change.

### Building the Bonsai package

```bash
dotnet build software/Aeon.VertiGate.sln -c Release
dotnet pack software/Aeon.VertiGate.sln -c Release
```

The package lands in `artifacts/package/release/`. A local build is always
version `42.42.42-dev0`, so it is never mistaken for a release. That is the
version the pinned Bonsai environment expects, so a build is all Bonsai needs.

### Using the Python interface

```bash
uv sync --all-extras
```

```python
from aeon.vertigate import device

print(device.WHO_AM_I)    # 3002
print(device.REGISTER_MAP)
```

### Checking the device against the specification

`harp.toolkit` can test a connected device. Use the Harp port, not the REPL
port:

```bash
dotnet harp.toolkit verify --port COM4 --metadata device.yml --report artifacts/verify.html
```

It runs 52 checks and writes an HTML report. It exits with 1 if any check fails,
so it can also run in CI.

Five checks do not pass today. All five are known:

| Check | Result | Why |
| ----- | ------ | --- |
| `R_CLOCK_CONFIG::LockRefusesTimestampWrite` | Failed | The core stores `CLOCK_LOCK` but does not act on it. A write to the timestamp is accepted while the clock is locked. This is in `micropython-microharp`, not in this firmware. |
| `DeviceInterfaceSuite::Control` | Error | The register is write only, so `verify` cannot read it back. Issue #6. |
| `DeviceInterfaceSuite::TargetPosition` | Error | The same. Issue #6. |
| `ClockTestSuite::SimultaneousWhoAmI` | Skipped | Needs `--clock-port` and a second Harp device as a reference clock. |
| `ClockTestSuite::PpsEventAlignment` | Skipped | The same. |

So CI must expect exit code 1 until issue #6 is closed and the core gains the
`CLOCK_LOCK` guard.

One check is worth knowing about: `DeviceInterfaceSuite::GenerateAndCompileInterface`
generates the C# from `device.yml` and compiles it. So `verify` already tells you
whether `device.yml` still produces a valid interface.

## ⚙️ Configuration & Tuning

### Register table

| Address | Name      | Access    | Description                                                                    |
| ------- | --------- | --------- | ------------------------------------------------------------------------------ |
| `0x20`  | Control   | W         | Commands, one per bit. See the table below.                                    |
| `0x21`  | TargetPosition | W    | Target position. 0 = down, 255 = up, 1–254 = in between. Unit: 1.2 mm          |
| `0x22`  | GateState | R + Event | `0x00` Idle, `0x01` Up, `0x02` Down, `0x03` Moving, `0x04` Calibrating, `0xFF` Error |
| `0x23`  | Speed     | R/W       | Profile velocity. 0–255, default 255. Unit: 0.38 mm/s                          |
| `0x24`  | Torque    | R/W       | Current limit. 0–127, default 35. Unit: 0.36 kgf·mm                            |
| `0x25`  | CalibrationOffset | R/W | Offset for the fully-up position. −128 to +127, default 0. Unit: 25 μm       |
| `0x26`  | MotorState | R + Event | `0x00` Disabled, `0x01` Enabled                                               |

Writing a bit of **Control** runs one command. A write with both bits of a pair set (for example
`EnableMotor` and `DisableMotor`) is rejected with an error reply.

| Bit    | Name                    | Effect                                                    |
| ------ | ----------------------- | --------------------------------------------------------- |
| `0x01` | EnableMotor             | Turn the motor on. The gate holds its position.           |
| `0x02` | DisableMotor            | Turn the motor off and stop any movement. The gate refuses to move until you enable the motor again. |
| `0x04` | Stop                    | Stop the current movement and hold the position.          |
| `0x08` | Calibrate               | Move the gate to the lower end stop and record it as home. |
| `0x10` | EnablePositionEvent     | Reserved for the Position register.                       |
| `0x20` | DisablePositionEvent    | Reserved for the Position register.                       |
| `0x40` | EnableTelemetryEvent    | Reserved for the ServoTelemetry register.                 |
| `0x80` | DisableTelemetryEvent   | Reserved for the ServoTelemetry register.                 |

The gate homes itself at boot. If the servo does not answer, GateState reports `Error`. Write
`Calibrate` to try again after fixing the connection.

**DisableMotor is a state, not a one-off command.** While **MotorState** (`0x26`) reads
`Disabled`, a write to **TargetPosition** or a `Calibrate` command is refused with an error
reply, and the gate does not move. Writes to **Speed** and **Torque** are accepted, and they
leave the motor off. Only `EnableMotor` clears the state.

### Calibration guidelines

- Write **CalibrationOffset** (`0x25`) to adjust the fully-up position without moving hardware.
- Change **Torque** (`0x24`) if the gate stalls, or pushes too hard at the end stops.
- Lower **Speed** (`0x23`) for slower and smoother motion.

> The gate turns off motor torque when it reaches the fully-down position. This protects the motor.

## 💻 Software Requirements

- **MicroPython** `SEEED_XIAO_RP2350` build, v1.29.0 or later: [micropython.org](https://micropython.org/download/SEEED_XIAO_RP2350/). See "Which MicroPython build" above.
- **uv**: [docs.astral.sh/uv](https://docs.astral.sh/uv/) (creates the `.venv` with `mpremote` and `pyserial`)
- **Bonsai**: [bonsai-rx.org](https://bonsai-rx.org/) (to run the example workflow)
- **.NET SDK 8 or later**: [dotnet.microsoft.com](https://dotnet.microsoft.com/download) (only to generate the interfaces or build the Bonsai package)

## 📜 License

**Sainsbury Wellcome Centre code, firmware, and software is released under the [BSD 3-Clause License](https://opensource.org/license/bsd-3-clause).**

> For the full legal text, see [LICENSE](LICENSE).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## ❤ Contributors

 <a href = "https://github.com/sainsburywellcomecentre/aeon_vertigate/graphs/contributors">
   <img src = "https://contrib.rocks/image?repo=sainsburywellcomecentre/aeon_vertigate" alt="Contributors"/>
 </a>

## 📧 Contact

- **Author**: [Sainsbury Wellcome Centre FabLabs](https://www.sainsburywellcome.org/content/fablab)
- **Email**: [swc.fablabs@ucl.ac.uk](mailto:swc.fablabs@ucl.ac.uk)
- **Website**: [FabLabs](https://sainsburywellcomecentre.github.io/fablabs-documentation/#fablabs-VertiGate)
