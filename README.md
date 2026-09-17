# VertiGate

[![GitHub release](https://img.shields.io/github/v/release/SainsburyWellcomeCentre/aeon_vertigate?style=flat-square&cacheSeconds=3600)](https://github.com/SainsburyWellcomeCentre/aeon_vertigate/releases)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg?style=flat-square)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/SainsburyWellcomeCentre/aeon_vertigate?style=flat-square)](https://github.com/SainsburyWellcomeCentre/aeon_vertigate/issues)

A [Harp](https://harp-tech.org/) device that controls a vertical gate. A Dynamixel XM430-W210 servo moves the gate.

VertiGate is a Harp device (WhoAmI **5350**) on a USB CDC serial port. The gate has 256 positions. 0 is fully down and 255 is fully up. The device reports the gate state as a Harp event.

## 🔧 Features

- Harp protocol over USB CDC at 1 Mbaud, with clock synchronisation
- Position control with one command byte (0 to 255)
- Speed and torque limits that can be changed at runtime
- An offset register for fine mechanical calibration

## 🚀 Getting Started

### Hardware connections

TBC

### Firmware installation

1. **Flash MicroPython.** Download the latest RP2354 MicroPython UF2 from [micropython.org](https://micropython.org/download/RPI_PICO2/). Hold BOOTSEL and copy the file to the board.
2. **Install mpremote.** Run `pip install mpremote`.
3. **Copy the firmware.** From the repository root, run:

   ```bash
   mpremote cp -r firmware/. :
   ```

4. **Install the libraries.** Run:

   ```bash
   mpremote mip install github:SainsburyWellcomeCentre/micropython-dynamixel
   mpremote mip install github:SainsburyWellcomeCentre/micropython-microharp
   ```

5. **Reset the board.** The device appears as a USB CDC serial port and starts the Harp protocol.

### Basic usage

Write one byte to the **Operation** register (`0x21`):

| Value     | Effect                          |
| --------- | ------------------------------- |
| `0`       | Lower the gate fully (DOWN)     |
| `255`     | Raise the gate fully (UP)       |
| `1`–`254` | Move to a position in between   |

Read the **Status** register (`0x22`), or subscribe to its event, to follow the gate state.

A Bonsai workflow is provided in `bonsai/example.bonsai`.

## ⚙️ Configuration & Tuning

### Register table

| Address | Name      | Access    | Description                                                                    |
| ------- | --------- | --------- | ------------------------------------------------------------------------------ |
| `0x21`  | Operation | W         | Target position. 0 = down, 255 = up, 1–254 = in between. Unit: 1.2 mm          |
| `0x22`  | Status    | R + Event | `0x00` Idle, `0x01` UP, `0x02` DOWN, `0x03` MOVING                              |
| `0x23`  | Speed     | R/W       | Profile velocity. 0–255, default 255. Unit: 0.38 mm/s                          |
| `0x24`  | Torque    | R/W       | Current limit. 0–127, default 35. Unit: 0.36 kgf·mm                            |
| `0x25`  | Offset    | R/W       | Position offset in encoder counts. −128 to +127, default 0. Unit: 25 μm        |

### Calibration guidelines

- Write **Offset** (`0x25`) to adjust the fully-up position without moving hardware.
- Change **Torque** (`0x24`) if the gate stalls, or pushes too hard at the end stops.
- Lower **Speed** (`0x23`) for slower and smoother motion.

> The gate turns off motor torque when it reaches the fully-down position. This protects the motor.

## 💻 Software Requirements

- **MicroPython** for RP2354: [micropython.org](https://micropython.org/download/RPI_PICO2/)
- **mpremote**: `pip install mpremote` (to upload the firmware)
- **Bonsai**: [bonsai-rx.org](https://bonsai-rx.org/) (to run the example workflow)

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
