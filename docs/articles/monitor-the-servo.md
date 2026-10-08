## Monitor the Servo

The servo reports its own health: supply voltage, temperature, motor current, and a hardware fault status. Watching these tells you when a gate is binding, when the supply is sagging, and when the servo is about to protect itself. Refer to the [connections](./connections.md?tabs=servo#connections) article to set up the servo, which we will use for the rest of these examples.

This article covers how to turn the telemetry stream on and how to read the four values in Bonsai.

The complete workflow is shown below. Copy and paste it into Bonsai, or build each section by following the step-by-step instructions.

:::workflow
![Monitor the Servo](../workflows/monitortheservo-toplevel.bonsai)
:::

### Enable Telemetry Events

The servo readings are off by default. Write the `EnableTelemetryEvent` bit of the `Control` register to start the stream.

:::workflow
![Enable Telemetry Events](../workflows/monitortheservo-enabletelemetry.bonsai)
:::

- Insert a [`KeyDown`] operator and set the `Filter` property to `A`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateControlPayload`.
    - `Control` - Select `EnableMotor` and `EnableTelemetryEvent`.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

Run the workflow and press <kbd>A</kbd>. The device starts to broadcast `ServoTelemetry` events once per second.

> [!TIP]
> Unlike the position stream, telemetry does not depend on the gate moving. It reports once per second whether the gate is moving or at rest.

> [!NOTE]
> The `Control` state survives a power cycle, so the telemetry stream is still on after a reboot.

### Visualize Servo Telemetry

The VertiGate broadcasts events using the [Harp communication protocol](https://harp-tech.org/protocol/BinaryProtocol-8bit.html). To read the servo values, decode the [`HarpMessages`] coming from the device with the workflow below.

:::workflow
![Visualize Servo Telemetry](../workflows/monitortheservo-visualizeevents.bonsai)
:::

- Insert a [`SubscribeSubject`] operator named `VertiGate Events`. This listens to the [`HarpMessages`] broadcast from the [`PublishSubject`] named `VertiGate Events` in the Harp device pattern.
- Insert a [`Parse`] operator and set the `Register` property to `TimestampedServoTelemetry`.
- Insert a [`VisualizerWindow`] operator. This opens a window with the parsed events when the workflow starts.

Run the workflow and press <kbd>A</kbd>. The visualizer displays four values once per second.

| Field | Meaning |
| --- | --- |
| `Voltage` | Supply voltage at the servo, in units of 0.1 V. A value of 120 is 12.0 V. |
| `Temperature` | Servo temperature, in degrees Celsius. |
| `Current` | Current through the motor, in mA. A negative value means the other direction. |
| `HardwareError` | Servo hardware fault status. 0 means no fault. |

> [!TIP]
> `Current` is the most useful of the four during an experiment. It rises when the gate meets resistance, so a gate that starts to bind shows up here before it fails.

> [!WARNING]
> If the servo does not answer, the device returns the **previous** telemetry values rather than an error. The read handler detects the failure, but the Harp core discards the result, so the reply looks normal. Treat a telemetry stream that stops changing as a possible servo fault, and check `GateState` for `Error`.

[!INCLUDE [](version-footer.md)]

<!--Reference Style Links -->
[`CreateMessage`]: xref:Aeon.VertiGate.CreateMessage
[`HarpMessages`]: xref:Bonsai.Harp.HarpMessage
[`KeyDown`]: xref:Bonsai.Windows.Input.KeyDown
[`MulticastSubject`]: xref:Bonsai.Expressions.MulticastSubject
[`Parse`]: xref:Aeon.VertiGate.Parse
[`PublishSubject`]: xref:Bonsai.Reactive.PublishSubject
[`SubscribeSubject`]: xref:Bonsai.Expressions.SubscribeSubject
[`VisualizerWindow`]: xref:Bonsai.Design.VisualizerWindow
