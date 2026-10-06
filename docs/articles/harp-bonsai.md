## Bonsai

Bonsai is a visual reactive programming language for interactive experiments and for processing data streams in real time. It supports a growing set of hardware and software packages that are common in neuroscience. This article covers how to set up the VertiGate in Bonsai.

> [!TIP]
> More information on Bonsai is in the official [documentation](https://bonsai-rx.org/docs/).

### First Steps

We use a small example to connect to the device and test it in Bonsai. The example reads the state of the gate and shows it as it changes. We return to this example in more detail in the "Bonsai Workflows" section.

Before you begin:

- Connect the [USB](connections.md) cable to the computer.
- Launch "Bonsai" from the Windows Start menu.
- Hover over the workflow cell below, and click the "Copy" icon at the top right.
- Paste the workflow into Bonsai.

:::workflow
![VertiGate First Steps](../workflows/vertigate-firststeps.bonsai)
:::

> [!TIP]
> The [Harp device pattern](https://harp-tech.org/articles/operators.html#device-pattern) initializes the device, logs the data, and gives hooks to send commands and to receive messages over the [Harp communication protocol](https://harp-tech.org/protocol/BinaryProtocol-8bit.html). If your workflow does not look like the one above, confirm that the [Aeon.VertiGate](./installation.md#software-packages) package is installed.

- Click the [`VertiGate (Device)`] operator and set the `PortName` property to the port of the device, for example COM8.
- Click the [`VertiGateDataWriter (DeviceDataWriter)`] operator and set the `Path` property to the name and location of the save folder, for example `VertiGate.harp`. Despite the property name, `DeviceDataWriter` creates a **folder** of that name that holds one binary file per register.
- Press the "Start" button in Bonsai to run the workflow.

> [!WARNING]
> Use the **second** serial port of the board, not the first. The first port is the MicroPython REPL. A workflow pointed at the REPL port connects and then reports nothing. The [Ports and Connections](connections.md#ports) article covers this.

A [visualizer](xref:Bonsai.Design.VisualizerWindow) opens when the workflow starts and shows the state of the gate. The device sends the value of every register when Bonsai connects, so a value appears at once, and a new one appears on every change:

```text
Idle
Calibrating
Down
```

> [!WARNING]
> **TODO**: Confirm the exact layout the visualizer prints for a timestamped enum, and replace the sample above with a real capture. The state names are from `device.yml` and are correct. The arrangement of the timestamp column is not confirmed.

The device is ready to use. If an error appears in Bonsai instead, read the [troubleshooting](troubleshooting.md) article.

> [!NOTE]
> If the gate reports `Error`, the servo did not answer. The device still starts, and every register still reads back, so this is the expected result when no servo is attached. Check the [servo connection](connections.md?tabs=servo#connections), then write `Calibrate`.

Next, we suggest the "Bonsai Workflows" section if you are not familiar with Harp devices in Bonsai.

If you already have experience with Harp devices, you can read the [register table](xref:Aeon.VertiGate) in the reference and use the device functionality directly.

[!INCLUDE [](version-footer.md)]

<!--Reference Style Links -->
[`VertiGate (Device)`]: xref:Aeon.VertiGate.Device
[`VertiGateDataWriter (DeviceDataWriter)`]: xref:Aeon.VertiGate.DeviceDataWriter
