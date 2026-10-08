## Indicators and Errors

This article covers how to resolve common errors on the VertiGate.

### COM Port Errors

**Q: In Bonsai, running the workflow throws an error "The port `ComX` does not exist."**

A: Either the wrong communications port was selected in the `PortName` property of [`Device`], or the [USB](connections.md) cable is not properly connected. Try a different communications port and check the connection.

**Q: In Bonsai, running the workflow throws an error "Access to the port `ComX` is denied".**

A: Only one interface connection to the VertiGate can be open at one time. Check that several instances of Bonsai are not running. The port can also be locked by a program that did not terminate correctly. Restarting the computer clears it.

**Q: Bonsai connects, but no data ever arrives.**

A: One possible reason is the wrong port. The board presents **two** serial ports. The first is the MicroPython REPL and the second is the Harp interface. A workflow pointed at the REPL port opens without an error and then reports nothing. Select the other port. [Ports and Connections](connections.md#ports) covers this.

Another possible reason is that the event streams are off. The VertiGate sends `Position` and `ServoTelemetry` only after you enable them. See [Move the Gate](move-the-gate.md#enable-position-events).

### Device Errors

**Q: The gate does not move, and every command is answered with an error.**

A: One possible reason is that the motor is off. `DisableMotor` is a state, not a one-off command. While it is set, the device refuses every write to `TargetPosition` and every `Calibrate` command. Write `EnableMotor` to clear it. See [Enable the Motor](enable-the-motor.md).

**Q: `GateState` reports `Error`.**

A: The servo did not answer. The device still starts and every register still reads back, so this is also what you see with no servo attached. After you correct the problem, write `Calibrate` to recover.

Check the power and the data connection first. If both are good, the servo is probably set to the wrong ID or the wrong baud rate. The firmware opens the bus at 1 Mbaud and addresses ID 1, and it does not search for anything else. A servo from a different rig, or one straight from the factory at 57600, is silent.

To find out what is on the bus, scan it from the REPL port:

```python
from machine import UART, Pin
from dynamixel import Dynamixel

dxl = Dynamixel(UART(1, baudrate=1000000, tx=Pin(8), rx=Pin(9)))
for baud in (9600, 57600, 115200, 1000000, 2000000, 3000000, 4000000):
    if dxl.ping(baud):
        print("found id", dxl.id, "model", dxl.model, "at", baud, "baud")
```

Save it as `dxlscan.py` and run it with `uv run --project firmware mpremote connect COM3 resume run dxlscan.py`. A broadcast ping answers whatever the ID is.

If the scan finds the servo at the wrong rate, set the Baud Rate register to code 3, which is 1 Mbaud:

```python
from dynamixel.table import ControlTableItem

dxl.ping(57600)                 # the rate the scan reported
dxl.torque_enabled = False      # EEPROM writes are refused while torque is on
dxl._write_register(ControlTableItem.BAUD_RATE, 3)
print(dxl.ping(1000000))        # True once it has switched
```

Reset the board afterwards, so the firmware configures the servo and homes the gate.

> [!NOTE]
> `mpremote` stops the running firmware while it holds the REPL, so the Harp port disappears during a scan. Reset the board when you finish. If the port does not come back, unplug the board and plug it in again.

**Q: The position stream shows nothing while the gate sits still.**

A: This is correct behavior. `Position` events are sent only while the gate moves or homes. A gate resting at its target sends nothing.

**Q: I wrote 200 to `Torque` and the device reports 72.**

A: `Torque` is masked to seven bits, so 200 becomes 72. The reply carries the value the device applied, not the value you sent. See [Tune the Motion](tune-the-motion.md#set-the-torque).

**Q: The gate dropped for a moment when I changed a setting.**

A: Writing `Speed` or `Torque` switches the motor off and on. If the gate was holding a position, it falls until the motor takes hold again. Set both before a session rather than during one.

**Q: Positions are all slightly wrong after a `Stop` during a calibration.**

A: A `Stop` that interrupts a calibration leaves a provisional home, so the reference is wrong. Run a full calibration to recover. See [Calibrate the Gate](calibrate-the-gate.md).

**Q: The gate did not home when I powered it on.**

A: The `Control` state survives a power cycle. If the motor was off when the device was last used, the gate does not home at start-up and reports `Idle`. Write `EnableMotor`, then `Calibrate`.

**Q: A telemetry or position value never changes.**

A: One possible reason is a servo that stopped answering. The device detects the failure but the Harp core discards that result, so the reply carries the previous value instead of an error. Check `GateState` for `Error`.

### Indicator Lights

The **STATE** LED cycles on and off with a period of 2 seconds while the device communicates with Bonsai, and 4 seconds in standby. The `microharp` core has no error blink pattern, so a fault does not change the LED. Read `GateState` to find out whether the device is in `Error`.

> [!WARNING]
> **TODO**: Confirm the blink periods on hardware. See the same note in [Ports and Connections](connections.md#indicator-lights).

### Read the Device Log

If the device does not start at all, and no serial port appears, the firmware writes the exception to a file on the board. Read it over the REPL port:

```bash
uv run --project firmware mpremote connect COM3 resume cat :error.log
```

An unhandled error inside a device task stops the firmware, and the Harp port disappears. An error inside a single register handler does not. The device keeps running, and only that one message goes unanswered.

[!INCLUDE [](version-footer.md)]

<!--Reference Style Links -->
[`Device`]: xref:Aeon.VertiGate.Device
