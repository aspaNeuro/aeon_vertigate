# VertiGate

[![GitHub release](https://img.shields.io/github/v/release/SainsburyWellcomeCentre/fablabs-VertiGate?style=flat-square&cacheSeconds=3600)](https://github.com/SainsburyWellcomeCentre/fablabs-VertiGate/releases)
[![License](https://img.shields.io/badge/license-CC%20BY--SA%204.0-blue.svg?style=flat-square)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/SainsburyWellcomeCentre/fablabs-VertiGate?style=flat-square)](https://github.com/SainsburyWellcomeCentre/fablabs-VertiGate/issues)

A [Harp](https://harp-tech.org/)-compatible vertical gate controller driven by a Dynamixel XM430-W210 servo motor.

VertiGate exposes a Harp device (WhoAmI **5350**) over USB CDC that controls a vertically-travelling gate. A Dynamixel XM430-W210 servo provides the actuation. The gate can be commanded to any of 256 positions (0 = fully down, 255 = fully up) and reports its status back as a Harp event.

## 🔧 Features

- Harp-protocol USB CDC interface (1 Mbaud) with clock synchronisation
- Full-range position control via a single 0–255 command byte
- Configurable speed and torque limits at runtime
- Fine position offset register for mechanical calibration

## 🚀 Getting Started

### Hardware connections
TBC
### Firmware installation

1. **Flash MicroPython** — download the latest RP2354 MicroPython UF2 from [micropython.org](https://micropython.org/download/RPI_PICO2/) and copy it to the board while holding BOOTSEL.
2. **Install mpremote** — `pip install mpremote`
3. **Copy firmware files** — from the `firmware/` directory, copy everything to the board:

   ```bash
   mpremote cp -r firmware/. :
   ```

4. **Install dependencies** — run the following commands to install the required libraries from GitHub:

   ```bash
   mpremote mip install github:SainsburyWellcomeCentre/micropython-dynamixel
   mpremote mip install github:SainsburyWellcomeCentre/micropython-microharp
   ```

5. **Reset the board** — the device will enumerate as a USB CDC serial port and announce itself on the Harp bus.

### Basic usage

Send an **Operation** command (register `0x21`) with a single byte:

| Value     | Effect                        |
| --------- | ----------------------------- |
| `0`       | Lower gate fully (DOWN)       |
| `255`     | Raise gate fully (UP)         |
| `1`–`254` | Move to intermediate position |

Monitor gate state by reading or subscribing to the **Status** event (register `0x22`).

A ready-to-use Bonsai workflow is provided in `bonsai/example.bonsai`.

## ⚙️ Configuration & Tuning

### Register table

| Address | Name      | Access    | Description                                                                 |
| ------- | --------- | --------- | --------------------------------------------------------------------------- |
| `0x21`  | Operation | W         | Target position (0 = down, 255 = up, 1–254 = intermediate)unit: 1.2mm       |
| `0x22`  | Status    | R + Event | `0x00` Idle · `0x01` UP · `0x02` DOWN · `0x03` MOVING                       |
| `0x23`  | Speed     | R/W       | Profile velocity (0–255, default 255) unit: 0.38mm/s                        |
| `0x24`  | Torque    | R/W       | Current limit (0–127, default 35) unit:0.36kgf·mm                           |
| `0x25`  | Offset    | R/W       | Fine position offset in encoder counts (−128 to +127, default 0) unit: 25μm |

### Calibration guidelines

- Write the **Offset** register (`0x25`) to fine-tune the fully-up endpoint without mechanical adjustment.
- Tune **Torque** (`0x24`) if the gate stalls or applies too much force at end-stops.
- Reduce **Speed** (`0x23`) for smoother, slower motion.
  > The gate disables motor torque automatically when it reaches the fully-down position to prevent motor stress.

## 💻 Software Requirements

- **MicroPython** for RP2354 — [micropython.org](https://micropython.org/download/RPI_PICO/)
- **mpremote** — `pip install mpremote` _(for firmware upload)_
- **Bonsai** — [bonsai-rx.org](https://bonsai-rx.org/) _(for the example workflow)_

## 📜 License

**Sainsbury Wellcome Centre code, firmware, and software is released under the [BSD 3-Clause License](https://opensource.org/license/bsd-3-clause).**

> For the full legal text, see [LICENSE](LICENSE).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## ❤ Contributors

 <a href = "https://github.com/sainsburywellcomecentre/fablabs-VertiGate/graphs/contributors">
   <img src = "https://contrib.rocks/image?repo=sainsburywellcomecentre/fablabs-VertiGate" alt="Contributors"/>
 </a>

## 📧 Contact

- **Author**: [@DCisHurt](https://github.com/DCisHurt)
- **Email**: [yuhsuan.chen@ucl.ac.uk](mailto:yuhsuan.chen@ucl.ac.uk)
- **Website**: [FabLabs](https://sainsburywellcomecentre.github.io/fablabs-documentation/#fablabs-VertiGate)
