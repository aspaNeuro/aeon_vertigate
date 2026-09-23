# VertiGate

[![GitHub release](https://img.shields.io/github/v/release/SainsburyWellcomeCentre/aeon_vertigate?style=flat-square&cacheSeconds=3600)](https://github.com/SainsburyWellcomeCentre/aeon_vertigate/releases)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg?style=flat-square)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/SainsburyWellcomeCentre/aeon_vertigate?style=flat-square)](https://github.com/SainsburyWellcomeCentre/aeon_vertigate/issues)

A [Harp](https://harp-tech.org/) device that controls a vertical gate. A Dynamixel XM430-W210 servo moves the gate.

VertiGate is a Harp device (WhoAmI **3002**, proposed for the SWC block 3000 to 3500, not registered yet) on a USB CDC serial port. The gate has 256 positions. 0 is fully down and 255 is fully up. The device reports the gate state as a Harp event.

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
2. **Erase the flash, first time only.** Copy
   [flash_nuke.uf2](https://datasheets.raspberrypi.com/soft/flash_nuke.uf2) to the drive. This
   removes any old file system. The drive disappears and comes back after a few seconds.
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

### Updating the firmware

The firmware keeps the REPL on its own port, so `mpremote` works while the device runs. Use
`resume` so that `mpremote` does not soft-reset the board:

```bash
uv run mpremote connect COM3 resume cp -r firmware/. :
uv run mpremote connect COM3 resume reset
```

If the device does not start, read the log it writes on the board:

```bash
uv run mpremote connect COM3 resume cat :error.log
```

### Testing

With the board connected and the Harp port known (for example `COM4`):

```bash
uv run vertigate-test --port COM4
```

The test checks the `Control` register and prints `PASS` or `FAIL` for each step. It works
with or without a servo. Without a servo the gate reports the `Error` state, and the script
expects that.

### Basic usage

Write one byte to the **TargetPosition** register (`0x21`):

| Value     | Effect                          |
| --------- | ------------------------------- |
| `0`       | Lower the gate fully (DOWN)     |
| `255`     | Raise the gate fully (UP)       |
| `1`–`254` | Move to a position in between   |

Read the **GateState** register (`0x22`), or subscribe to its event, to follow the gate state.

A Bonsai workflow is provided in `docs/workflows/GateControl.bonsai`.

### The pinned Bonsai environment

`.bonsai/` pins the Bonsai version and the packages, so everyone runs the
example workflow on the same environment. It holds Bonsai 2.9.1, `Bonsai.Harp`,
`Bonsai.Harp.Design`, which is the one that shows the Device Setup dialog, and
`Bonsai.Gui`, which the panel is built with. Bonsai installs itself into that
folder on first use, and the downloaded files are ignored by git.

`Aeon.VertiGate` is in that list too, so the workflow opens with the typed
operators already loaded. It is pinned at `42.42.42-dev0`, the version every
local build produces, and `.bonsai/NuGet.config` points at
`artifacts/package/release` so Bonsai can find it.

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
each package version it installs. So it may use the old copy and ignore the new
one. If Bonsai still shows the old operators, close it, delete
`.bonsai/Packages/Aeon.VertiGate.42.42.42-dev0/`, and start it again.

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

It runs 51 checks and writes an HTML report. It exits with 1 if any check
fails, so it can also run in CI. Some checks fail today. See the open issues.

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

Writing a bit of **Control** runs one command. A write with both bits of a pair set (for example
`EnableMotor` and `DisableMotor`) is rejected with an error reply.

| Bit    | Name                    | Effect                                                    |
| ------ | ----------------------- | --------------------------------------------------------- |
| `0x01` | EnableMotor             | Turn the motor torque on. The gate holds its position.    |
| `0x02` | DisableMotor            | Turn the motor torque off. The gate can be moved by hand. |
| `0x04` | Stop                    | Stop the current movement and hold the position.          |
| `0x08` | Calibrate               | Move the gate to the lower end stop and record it as home. |
| `0x10` | EnablePositionEvent     | Reserved for the Position register.                       |
| `0x20` | DisablePositionEvent    | Reserved for the Position register.                       |
| `0x40` | EnableTelemetryEvent    | Reserved for the ServoTelemetry register.                 |
| `0x80` | DisableTelemetryEvent   | Reserved for the ServoTelemetry register.                 |

The gate homes itself at boot. If the servo does not answer, GateState reports `Error`. Write
`Calibrate` to try again after fixing the connection.

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
