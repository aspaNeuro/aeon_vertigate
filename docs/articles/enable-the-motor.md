## Enable the Motor

The motor holds the gate in place. When it is off, the gate is free and you can move it by hand, which is what you want while you mount it or clear a jam. Refer to the [connections](./connections.md?tabs=servo#connections) article to set up the servo, which we will use for the rest of these examples.

This article covers how to turn the motor on and off, how to stop a movement that is under way, and how to follow the motor state in Bonsai.

The complete workflow is shown below. Copy and paste it into Bonsai, or build each section by following the step-by-step instructions.

:::workflow
![Enable the Motor](../workflows/enablethemotor-toplevel.bonsai)
:::

### Enable and Disable the Motor

The `EnableMotor` and `DisableMotor` bits of the `Control` register turn the motor on and off.

:::workflow
![Enable the Motor](../workflows/enablethemotor-enablemotor.bonsai)
:::

- Insert a [`KeyDown`] operator and set the `Filter` property to `A`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateControlPayload`.
    - `Control` - Select `EnableMotor`.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

In a separate branch:

:::workflow
![Disable the Motor](../workflows/enablethemotor-disablemotor.bonsai)
:::

- Insert a [`KeyDown`] operator and set the `Filter` property to `S`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateControlPayload`.
    - `Control` - Select `DisableMotor`.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

Run the workflow and press <kbd>A</kbd>. The motor holds the gate. Press <kbd>S</kbd> and the gate becomes free.

> [!WARNING]
> `DisableMotor` is a state, not a single command. While the motor is off, the device refuses every write to `TargetPosition` and every `Calibrate` command, and answers each one with an error. The gate does not move. Only `EnableMotor` clears the state. Writes to `Speed` and `Torque` are still accepted, and the motor stays off.

> [!WARNING]
> A write that sets both bits of a pair is rejected with an error reply, and nothing is applied. The three pairs are `EnableMotor` with `DisableMotor`, `EnablePositionEvent` with `DisablePositionEvent`, and `EnableTelemetryEvent` with `DisableTelemetryEvent`.

> [!NOTE]
> The `Control` state survives a power cycle. The gate homes itself at start-up, but only when the stored state has the motor on. If you leave the motor off and reboot, the gate stays where it is and reports `Idle`, because it has not been homed. This is deliberate: a motor turned off because of a fault must stay off.

### Stop the Gate

The `Stop` bit halts a movement that is under way and holds the gate where it is.

:::workflow
![Stop the Gate](../workflows/enablethemotor-stop.bonsai)
:::

- Insert a [`KeyDown`] operator and set the `Filter` property to `D`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateControlPayload`.
    - `Control` - Select `Stop`.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

Run the workflow, start a movement, and press <kbd>D</kbd>. The gate stops and holds.

> [!WARNING]
> A `Stop` during a calibration leaves the gate with a provisional home. The reference is wrong until you calibrate again. See [Calibrate the Gate](./calibrate-the-gate.md).

> [!TIP]
> `Stop` and `Calibrate` are commands, not states. A read of `Control` reports only the states, so these two bits never appear in a read.

### Visualize Motor State

The VertiGate broadcasts events using the [Harp communication protocol](https://harp-tech.org/protocol/BinaryProtocol-8bit.html). To follow whether the motor holds the gate, decode the [`HarpMessages`] coming from the device with the workflow below.

:::workflow
![Visualize Motor State](../workflows/enablethemotor-visualizeevents.bonsai)
:::

- Insert a [`SubscribeSubject`] operator named `VertiGate Events`. This listens to the [`HarpMessages`] broadcast from the [`PublishSubject`] named `VertiGate Events` in the Harp device pattern.
- Insert a [`Parse`] operator and set the `Register` property to `TimestampedMotorState`.
- Insert a [`VisualizerWindow`] operator. This opens a window with the parsed events when the workflow starts.

Run the workflow and press <kbd>A</kbd> and <kbd>S</kbd>. The visualizer displays:

```text
Enabled@18.2304
Disabled@21.9872
```

The first part is the `Payload` value, either `Enabled` or `Disabled`, and the second is the timestamp on the device clock.

> [!NOTE]
> `MotorState` is reported only when the value changes. Pressing <kbd>A</kbd> twice in a row produces one event, not two.

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
