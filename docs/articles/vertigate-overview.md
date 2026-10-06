## VertiGate

VertiGate is a Harp device that raises and lowers a vertical gate. A Dynamixel XM430-W210 servo moves the gate, and the device reports the position of the gate on the Harp clock.

[placeholder - vertigate-pcb.png]{width=450}

### Key Features

- Position control over the full travel of the gate, commanded with a single byte.
- A homing routine that drives the gate to the lower end stop and records it as the reference position.
- Speed and torque limits that you can change while an experiment runs, and that survive a power cycle.
- Servo telemetry: supply voltage, temperature, motor current, and the hardware fault status.

### Specs

- Servo: Dynamixel XM430-W210
- Travel: 300 mm
- Position step: 1.2 mm (48 encoder counts)
- Encoder resolution: 25 µm
- Speed step: 0.38 mm/s
- Torque step: 0.36 kgf·mm
- Host interface: USB CDC at 1 Mbaud
- WhoAmI: 3002
- Position event rate: one event every 50 ms while the gate moves
- Telemetry event rate: one event per second
- Timestamp resolution: 32 µs
- Synchronization frequency: 1 Hz

> [!WARNING]
> **TODO**: Measure the synchronization accuracy of this device against a Harp clock generator. VertiGate runs the MicroPython `microharp` core, not the shared ATxmega core, so the accuracy published for ATxmega devices does not apply and must not be copied here.

> [!NOTE]
> The WhoAmI value 3002 is proposed for the SWC block 3000 to 3500. It is not registered yet.

### The Top of the Position Range

`TargetPosition` and `Position` are declared 0 to 255, but the gate stops at step 250. The travel is 12000 encoder counts and one step is 48 counts, so 48 × 250 covers the whole travel. A write of 251 to 255 moves the gate to the same place as 250.

The five unreachable steps are 6 mm at the top of 300 mm. A change to the scale would move every position already in use, so the limit is documented and not corrected.

### Hardware

| Version | Notes |
| ------- | ----- |
| 0.1 | <ul><li> First board. RP2354A with 2 MB of internal flash, driving one Dynamixel servo on a half-duplex TTL UART. </li></ul> |

### Firmware

| Version | Notes |
| ------- | ----- |
| 0.1 | <ul><li> First release on the Harp unified stack. </li><li> Register set generated from <code>device.yml</code>. </li><li> Non-volatile Speed, Torque, CalibrationOffset, and Control state. </li></ul> |

> [!WARNING]
> **TODO**: Rebuild both tables from the release page once VertiGate has published releases. There are none today, so the rows above record the single hardware and firmware pairing that `device.yml` declares.

[!INCLUDE [](version-footer.md)]
