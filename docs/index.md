## Overview

The Harp [VertiGate](articles/vertigate-overview.md) is a vertical gate controller for behavioral rigs. It raises and lowers a gate with a Dynamixel XM430-W210 servo, and it reports every movement as a timestamped Harp event.

[placeholder - vertigate-with-peripherals.svg]{width=450}

A gate that opens and closes on cue is part of many behavioral tasks. The host needs to know where the gate is, not only where it was told to go. The record also needs to agree with the rest of the rig. VertiGate drives the servo, measures the gate against its own end stop, and timestamps the result on the same clock as every other Harp device.

The VertiGate provides:

- Position control over 300 mm of travel, in steps of 1.2 mm.
- Speed and torque limits that you can change while an experiment runs.
- A homing routine that finds the lower end stop and records it as the reference.
- Live telemetry from the servo: voltage, temperature, current, and fault status.
- Hardware timestamping and synchronization with other [Harp](https://harp-tech.org/articles/about.html) devices.
- [Bonsai](https://bonsai-rx.org/) integration for flexible experiment acquisition and control.

## Getting a Device

The Sainsbury Wellcome Centre [FabLabs](https://www.sainsburywellcome.org/content/fablab) builds the VertiGate. The firmware, the Bonsai interface, and the device specification are in the [aeon_vertigate](https://github.com/SainsburyWellcomeCentre/aeon_vertigate) repository.

> [!WARNING]
> **TODO**: Confirm how a user outside the SWC obtains a VertiGate board and the gate assembly. There is no store page today.

## Acknowledgments

Hardware, firmware, and the Bonsai interface by the Sainsbury Wellcome Centre [FabLabs](https://www.sainsburywellcome.org/content/fablab). Built on the [Harp](https://harp-tech.org/) protocol and the [Bonsai](https://bonsai-rx.org/) ecosystem.

[!INCLUDE [](./articles/version-footer.md)]
