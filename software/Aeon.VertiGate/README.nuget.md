# Aeon.VertiGate

Bonsai operators for the VertiGate Harp device.

VertiGate is a vertical gate. A Dynamixel XM430-W210 servo moves the gate. The
device connects over a USB serial port and uses the Harp protocol.

## Use

Add a **Device** operator to a workflow. Set its port to the Harp port of the
board. The device reports WhoAmI 3002, and Bonsai checks this value when it
connects.

The package gives one operator for each register, so a workflow does not use
raw addresses or payload types:

| Operator | Use |
| --- | --- |
| `Control` | Run one command. Enable or disable the motor, stop, or calibrate. |
| `TargetPosition` | Move the gate. 0 lowers it fully, 255 raises it fully. |
| `GateState` | Read the state of the gate, or subscribe to its event. |
| `Speed` | Set the movement speed. |
| `Torque` | Set the torque limit. |
| `CalibrationOffset` | Trim the fully-raised position. |

`Speed`, `Torque` and `CalibrationOffset` are non-volatile. The device stores a
written value and uses it again after a reboot.

## From C# code

The package also works outside the Bonsai editor. `Device.CreateAsync` opens a
serial port, checks WhoAmI, and returns an `AsyncDevice`. This class has a read
method and a write method for each register.

## Requirements

- Bonsai 2.9 or later
- Bonsai.Harp 3.6.1

The package targets .NET Framework 4.7.2 and .NET 8.

## More information

- Source code, firmware and hardware:
  [github.com/SainsburyWellcomeCentre/aeon_vertigate](https://github.com/SainsburyWellcomeCentre/aeon_vertigate)
- The Aeon project: [aeon.swc.ucl.ac.uk](https://aeon.swc.ucl.ac.uk/)
- The Harp protocol: [harp-tech.org](https://harp-tech.org/)
