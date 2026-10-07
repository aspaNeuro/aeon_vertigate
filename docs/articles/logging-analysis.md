## Logging and Analysis

This article covers how data from the device is logged to disk, and how to read and plot the logged data in Python.

### Log Data

Data from the device is logged by the [`DeviceDataWriter`] operator in the Harp device pattern. It saves raw data from all device registers in the Harp binary format, to the folder set in its `Path` property:

:::workflow
![Harp Device Pattern](../workflows/harp-devicepattern.bonsai)
:::

While the workflow runs, registers are logged as the device produces messages, both events and command echoes. Two properties of the [`Device`] operator also matter for logging:

- `DumpRegisters` - Enabled by default. This logs a read of every register when the device initializes, which captures the state of the device at the start of the experiment.
- `Heartbeat` - Disabled by default. Enable it to log the hardware timestamp of the device once per second.

> [!WARNING]
> The register dump can be used as an approximate start time for the workflow or experiment. Keep in mind that other devices in the workflow may initialize at a different time.

> [!NOTE]
> The VertiGate logs only what it sends. Its event streams are off until you turn them on, so a recording made without `EnablePositionEvent` holds the register dump and the command echoes, but no position trace. Turn the streams on at the start of the workflow, as [Move the Gate](./move-the-gate.md#enable-position-events) and [Monitor the Servo](./monitor-the-servo.md#enable-telemetry-events) show.

### Analyze Data

The [`harp-data`](https://harp-tech.org/python/) package imports data stored in the Harp binary format as [pandas](https://pandas.pydata.org/) DataFrames, which you can then analyze with any plotting or analysis library that works with `pandas`.

The following example reads and plots data from the [`Position`](move-the-gate.md) register.

> [!NOTE]
> This example needs a Python environment with [harp-data](installation.md#software-packages) and [`matplotlib`](https://matplotlib.org/) installed. `matplotlib` is the plotting backend that `pandas` uses.

```python
# Import the dependencies
import matplotlib.pyplot as plt
from harp import data

# Finds device.yml in the folder, builds the device module, returns a dataset reader
reader = data.open_dataset("VertiGate.harp")

# Lists every register in the reader by name and address
print(reader.contents)

# Load data from a particular register
df = reader.read("Position")   # by name
df = reader.read(39)           # or by address

# Inspect DataFrame
print(df.head())

# Plot the position of the gate over time
df.plot()
plt.show()
```

> [!WARNING]
> **TODO**: Run this example against a real recording and correct it if the API differs. `device.yml` must be in the logged folder for `open_dataset` to build the device module. Confirm whether `DeviceDataWriter` copies it there, or whether the user has to place it.

> [!TIP]
> `Position` is clamped to 0 to 250, so a trace alone does not show the travel below home. Read `RawPosition` (address 41) beside it when you need the encoder counts. [Calibrate the Gate](./calibrate-the-gate.md#visualize-the-raw-encoder-counts) explains what the pair holds.

The typed register names are also available from Python through the `swc-aeon-vertigate` package, which [Installation](installation.md?tabs=python#software-packages) covers.

[!INCLUDE [](version-footer.md)]

<!--Reference Style Links -->
[`DeviceDataWriter`]: xref:Aeon.VertiGate.DeviceDataWriter
[`Device`]: xref:Aeon.VertiGate.Device
