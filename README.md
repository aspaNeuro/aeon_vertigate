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

Each [release](https://github.com/SainsburyWellcomeCentre/aeon_vertigate/releases) attaches one firmware image, `VertiGate-fw<x.y>-harp1.13-hw<x.y>-ass0.uf2`. It is a MicroPython build for the NeuroPico with the VertiGate application and its libraries frozen inside. Flashing it is the whole installation.

1. **Enter the bootloader.** Hold BOOTSEL and press reset (or plug the board in while holding
   BOOTSEL). A drive named `RP2350` appears.
2. **Erase the file system, first time only.** Do not use `flash_nuke.uf2`. That file is an
   RP2040 image, and this board is an RP2350, so the boot loader ignores it. Clear the file
   system from the REPL instead, as [docs/firmware-image.md](docs/firmware-image.md)
   describes. A board straight from the factory needs nothing here.
3. **Flash the image.** Copy the `.uf2` from the release to the drive. The board reboots.
4. **Check the ports.** The board shows **two** COM ports. The first is the MicroPython REPL.
   The second is the Harp interface. Use the second one in Bonsai.

To update, flash the new `.uf2` the same way. The settings file and the error log on the file system survive, because the image only replaces the firmware region.

### Developing the firmware

The image runs its frozen `main.py` even when a `main.py` is on the file system, so it cannot be used to try out changes. For development, run the Python files from the file system of a stock MicroPython build.

> **Which MicroPython build.** The NeuroPico uses an RP2354A with **2 MB** of flash inside the chip.
> Do not use the `RPI_PICO2` build. It assumes 4 MB and its file system wraps around onto the
> firmware. The board works for a while, then freezes or corrupts its files. Use the
> **`SEEED_XIAO_RP2350`** build, **v1.29.0 or later**. It is made for an RP2350A with 2 MB and has
> no board-specific code that affects VertiGate. Older versions of that build have the same 4 MB
> problem.

1. **Flash MicroPython.** Enter the bootloader and erase the flash as above, then copy
   [SEEED_XIAO_RP2350-20260824-v1.29.0.uf2](https://micropython.org/resources/firmware/SEEED_XIAO_RP2350-20260824-v1.29.0.uf2)
   to the drive (newer releases: [micropython.org/download/SEEED_XIAO_RP2350](https://micropython.org/download/SEEED_XIAO_RP2350/)).
   The board reboots and a COM port appears.
2. **Install the host tools.** Install [uv](https://docs.astral.sh/uv/), then create the
   firmware environment:

   ```bash
   uv sync --directory firmware
   ```

   It holds `mpremote` and `pyserial`, pinned in `firmware/uv.lock`. The Python interface is a
   separate environment in `software/python/`, and is only needed to read data from a device.
3. **Install the libraries.** Replace `COM3` with your port. The versions are the ones pinned as
   submodules under `firmware/lib/`, which is what the release image is built from:

   ```bash
   uv run --directory firmware mpremote connect COM3 mip install github:SainsburyWellcomeCentre/micropython-dynamixel@846451ee2db58569f1aae4c8527ef053a9df291a
   uv run --directory firmware mpremote connect COM3 mip install github:SainsburyWellcomeCentre/micropython-microharp@v2.1.0
   ```

4. **Copy the firmware.** From the repository root, run:

   ```bash
   uv run --directory firmware mpremote connect COM3 cp -r firmware/vertigate/. :
   uv run --directory firmware mpremote connect COM3 reset
   ```

The firmware keeps the REPL on its own port, so `mpremote` can reach the board while the
device is plugged in. **`mpremote` stops the running firmware.** It enters the raw REPL,
which raises `KeyboardInterrupt` inside the device loop, and the Harp port disappears. Copy
the files, then reset:

```bash
uv run --directory firmware mpremote connect COM3 resume cp -r firmware/vertigate/. :
uv run --directory firmware mpremote connect COM3 reset
```

The Harp port comes back about 10 seconds after the reset. If it does not come back at all,
unplug the board and plug it in again. The USB stack can stay down after several soft
resets in a row.

If the device does not start, read the log it writes on the board:

```bash
uv run --directory firmware mpremote connect COM3 resume cat :error.log
```

### Testing

There are two tests. The first drives the device and checks what it does. The second checks
the device against the Harp specification. Both use the Harp port.

**The hardware test.** With the board connected and the Harp port known (for example `COM4`):

```bash
uv run --directory software/python --extra test vertigate-test --port COM4
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
dotnet pack software/dotnet/Aeon.VertiGate.sln -c Release
```

#### If you change `device.yml`

The build does not generate the interfaces. It compiles the `.Generated.cs`
files that are on disk. But it does copy the new `device.yml` into the package.
So a package built without the generate step holds a specification that does
not match its own operators. Nothing warns you.

Generate first, then pack:

```bash
dotnet harp.toolkit generate interface csharp device.yml --namespace Aeon.VertiGate --output software/dotnet/Aeon.VertiGate
dotnet harp.toolkit generate interface python device.yml --package \n  --output software/python/src/swc/aeon/device/vertigate
uv run firmware/tools/firmware_version.py
dotnet pack software/dotnet/Aeon.VertiGate.sln -c Release
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

`device.yml` describes every register. Two interfaces and one firmware module are generated from it:

- **Bonsai**, in `software/dotnet/Aeon.VertiGate/`. It gives one typed operator per
  register, instead of raw addresses and payload types.
- **Python**, in `software/python/src/swc/aeon/device/vertigate/`. It works with
  [harp-python](https://github.com/harp-tech/python).
- **Firmware identity**, in `firmware/vertigate/_version.py`. It holds the WhoAmI and the
  firmware and hardware versions the device reports on connect.

All three are committed, and CI fails if any of them is out of date. You only need to generate them again after you change
`device.yml`.

### Generating them again

`harp.toolkit` is pinned in `.config/dotnet-tools.json`, so everyone uses the
same version. Install it once per clone:

```bash
dotnet tool restore
```

Then, from the repository root:

```bash
dotnet harp.toolkit generate interface csharp device.yml --namespace Aeon.VertiGate --output software/dotnet/Aeon.VertiGate
dotnet harp.toolkit generate interface python device.yml --package \n  --output software/python/src/swc/aeon/device/vertigate
uv run firmware/tools/firmware_version.py
```

Commit the result. Do not edit the generated files by hand. They say so at the
top, and the next run would overwrite the change.

### Building the firmware image

The release image is a MicroPython build with the application frozen in. The inputs are in `firmware/`:

- `vertigate/`: the application.
- `lib/`: `micropython-microharp` and `micropython-dynamixel` as git submodules, pinned to the versions the application is tested with. Clone with `git clone --recursive`, or run `git submodule update --init` in an existing clone.
- `boards/NEUROPICO/`: the MicroPython board definition. It reuses the Seeed XIAO RP2350 board support, pins the flash size to 2 MB and the file system to 1 MiB, and names the modules to freeze in `manifest.py`.

CI builds the image on every push and attaches it to releases. To build it locally on Linux, with `gcc-arm-none-eabi` 13, `cmake` and `picotool` installed (GCC 15 rejects a warning in the bundled mbedtls, so use the GCC 13 toolchain CI uses):

```bash
git clone --depth 1 --branch v1.29.0 https://github.com/micropython/micropython.git
make -C micropython/ports/rp2 BOARD_DIR=$PWD/firmware/boards/NEUROPICO submodules
make -C micropython/mpy-cross
make -C micropython/ports/rp2 BOARD_DIR=$PWD/firmware/boards/NEUROPICO
```

The image is `micropython/ports/rp2/build-NEUROPICO/firmware.uf2`. Use the same MicroPython version as CI, set in the workflow file.

The release tag must match `firmwareVersion` in `device.yml` in its major and minor parts. CI checks this and stops the release if they differ.

### Building the Bonsai package

```bash
dotnet build software/dotnet/Aeon.VertiGate.sln -c Release
dotnet pack software/dotnet/Aeon.VertiGate.sln -c Release
```

The package lands in `artifacts/package/release/`. A local build is always
version `42.42.42-dev0`, so it is never mistaken for a release. That is the
version the pinned Bonsai environment expects, so a build is all Bonsai needs.

### Using the Python interface

The package is `swc-aeon-vertigate`, in `software/python/`. From a checkout:

```bash
uv sync --directory software/python --all-extras
```

```python
from swc.aeon.device import vertigate

print(vertigate.WHO_AM_I)    # 3002
print(vertigate.REGISTER_MAP)
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
| `0x27`  | Position  | R + Event | Where the gate is now, on the TargetPosition scale. Unit: 1.2 mm              |
| `0x28`  | ServoTelemetry | R + Event | Voltage, temperature, current and the fault status of the servo. 4 x S16 |
| `0x29`  | RawPosition | R + Event | The two encoder counts that make Position: `Encoder` and `Home`. 2 x S32     |

Writing a bit of **Control** runs one command. A write with both bits of a pair set (for example
`EnableMotor` and `DisableMotor`) is rejected with an error reply.

| Bit    | Name                    | Effect                                                    |
| ------ | ----------------------- | --------------------------------------------------------- |
| `0x01` | EnableMotor             | Turn the motor on. The gate holds its position.           |
| `0x02` | DisableMotor            | Turn the motor off and stop any movement. The gate refuses to move until you enable the motor again. |
| `0x04` | Stop                    | Stop the current movement and hold the position.          |
| `0x08` | Calibrate               | Move the gate to the lower end stop and record it as home. |
| `0x10` | EnablePositionEvent     | Start sending Position and RawPosition events.            |
| `0x20` | DisablePositionEvent    | Stop sending Position and RawPosition events.             |
| `0x40` | EnableTelemetryEvent    | Start sending ServoTelemetry events.                      |
| `0x80` | DisableTelemetryEvent   | Stop sending ServoTelemetry events.                       |

**A read of Control reports the state, not the last command.** The device sets these bits:

- `EnableMotor`, while the motor is on
- `EnablePositionEvent`, while the Position stream runs
- `EnableTelemetryEvent`, while the ServoTelemetry stream runs

Stop and Calibrate are commands. A read never reports them.

Control is non-volatile. The enabled streams and the motor state stay the same when the power
goes off and on.

The gate homes itself at boot. The gate does not home if the stored state has the motor off.
If the servo does not answer, GateState reports `Error`. Correct the connection, then write
`Calibrate`.

**DisableMotor is a state, not a single command.** The device refuses a write to
**TargetPosition** while **MotorState** (`0x26`) reads `Disabled`. The device also refuses a
`Calibrate` command. Each refusal is an error reply, and the gate does not move. The device
accepts a write to **Speed** or **Torque**, and the motor stays off. Only `EnableMotor` clears
the state.

### Event streams

Three registers report the position of the gate and the readings of the servo. You can read
all three at any time. The `Control` bits start and stop the event streams.

| Stream | Bit | Rate | Contents |
| ------ | --- | ---- | -------- |
| Position and RawPosition | `0x10` | 50 ms, while the gate moves or homes | The gate position |
| ServoTelemetry | `0x40` | 1 s | Voltage in 0.1 V, temperature in C, current in mA, servo fault status |

**Position has the range 0 to 255.** The firmware computes Position from RawPosition:

```
Position = (Encoder - Home) / 48, limited to 0 to 255
```

One encoder count is 25 um. One Position step is 48 counts, or 1.2 mm. The full travel is
12000 counts, or 300 mm.

**The range limit hides two things. RawPosition shows them.** The gate rests about 400 counts
below `Home`. Position therefore reads 0 for the last 10 mm of travel. A calibration also
replaces `Home`. The reference moves, but Position does not change. RawPosition reports
`Encoder` and `Home` as two values, so you can see both.

To watch a calibration, set `EnablePositionEvent` and then write `Calibrate`. `Encoder`
decreases while the gate goes down. `Home` stays at the same value. At the end of the
calibration, `Home` changes once to the new value. The size of that change is the error in the
previous home.

### Calibration guidelines

- Write **CalibrationOffset** (`0x25`) to adjust the fully-up position without moving hardware.
- Change **Torque** (`0x24`) if the gate stalls, or pushes too hard at the end stops.
- Lower **Speed** (`0x23`) for slower and smoother motion.

> The gate turns off motor torque when it reaches the fully-down position. This protects the motor.

## 💻 Software Requirements

Running a released firmware image needs no software beyond Bonsai. The rest is for development:

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
