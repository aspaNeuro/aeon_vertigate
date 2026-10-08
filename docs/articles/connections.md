## Ports and Connections

This article covers the ports and the status indicator on the VertiGate, and how to connect the device to the servo and to the rest of the rig.

### Ports

[placeholder - vertigate-devicepinout.svg]{width=600}

> [!WARNING]
> **TODO**: Confirm every connector label and connector type below. The repository holds no hardware design files, so the entries name the microcontroller pins from `firmware/vertigate/main.py` instead of the silkscreen labels. Replace each pin number with the printed label once the board drawing is available.

**USB** - This port connects the device to the computer that runs [Bonsai](harp-bonsai.md). It carries power for the board and the Harp protocol at 1 Mbaud.

The board presents **two** serial ports over this one connector. The first is the MicroPython REPL. The second is the Harp interface. Use the second one in Bonsai. The [troubleshooting](troubleshooting.md) article covers how to tell them apart.

**Servo (GPIO 8 and GPIO 9)** - The half-duplex TTL bus to the Dynamixel XM430-W210 servo, at 1 Mbaud. The servo moves the gate and reports its own position, voltage, temperature, and current. Refer to the [Move the Gate](move-the-gate.md) article to command it from Bonsai.

The servo must be set to **ID 1** and **1 Mbaud**. The firmware opens the bus at that rate and addresses that ID, and it does not search for others. A servo on any other setting does not answer, and the gate reports `Error`. [Indicators and Errors](troubleshooting.md#device-errors) covers how to find and correct this.

**Clock input (GPIO 1)** - The Harp synchronization clock input, at 100 kbaud. Connect it to a Harp clock generator to put the VertiGate on the same clock as the rest of the rig.

> [!WARNING]
> **TODO**: Confirm the purpose of GPIO 11, GPIO 12, and GPIO 13. The firmware drives them to 1, 0, and 1 at start-up ([main.py:21-23](https://github.com/SainsburyWellcomeCentre/aeon_vertigate/blob/main/firmware/vertigate/main.py#L21-L23)) and never touches them again. They are probably a bus direction control or a power enable for the servo, but nothing in the repository says so.

### Indicator Lights

**STATE** - The LED on GPIO 7 cycles on and off with a period of:

- 2 seconds when the device is communicating with Bonsai
- 4 seconds when the device is in standby

> [!WARNING]
> **TODO**: Confirm the blink periods on hardware. The `microharp` core drives this LED from a clock bit on each second boundary, and its own docstring disagrees with its code about the rate. The core has no error pattern, so a fast blink does not indicate a fault on this device.

### Connections

# [Servo](#tab/servo)

[placeholder - connection-servo.svg]{width=450}

1. Connect the Dynamixel XM430-W210 to the servo bus of the board.
2. Power the servo from its own supply. The servo draws far more current than USB provides.
3. Refer to the [Move the Gate](move-the-gate.md) article to command the gate in Bonsai.

The servo runs at 12 V. A working rig was measured at 12.2 V at the servo on 2026-10-07.

> [!WARNING]
> **TODO**: State the current budget, and say whether the board passes power through to the servo or expects a separate supply. The 12 V figure above is one measurement, not a specification.

# [Harp Synchronization](#tab/harpsynchronization)

[placeholder - connection-harpsynchronization.svg]{width=450}

1. Connect a clock output of a Harp clock generator, for example the [Harp Timestamp Generator](https://github.com/harp-tech/device.timestampgeneratorgen3), to the clock input of the VertiGate.
2. The VertiGate adopts the clock of the generator automatically. To check the connection, confirm that the **STATE** LEDs of the connected boards blink at the same time.
3. Refer to the [Harp synchronization clock](https://harp-tech.org/protocol/SynchronizationClock.html) documentation for how devices synchronize.

> [!NOTE]
> The device treats itself as unsynchronized after 1.5 seconds without a clock packet. It then keeps its own free-running second tick, so the heartbeat continues and the LED keeps blinking.

---

[!INCLUDE [](version-footer.md)]
