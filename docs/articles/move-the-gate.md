## Move the Gate

The VertiGate moves a gate over 300 mm of travel, in steps of 1.2 mm. One byte commands the position: 0 lowers the gate fully, and 250 raises it fully. Refer to the [connections](./connections.md?tabs=servo#connections) article to set up the servo, which we will use for the rest of these examples.

This article covers how to move the gate, how to turn the position stream on, and how to visualize where the gate is in Bonsai.

The complete workflow is shown below. Copy and paste it into Bonsai, or build each section by following the step-by-step instructions.

:::workflow
![Move the Gate](../workflows/movethegate-toplevel.bonsai)
:::

> [!WARNING]
> You can find and add these operators to the workflow from the Bonsai [Toolbox](https://bonsai-rx.org/docs/articles/editor.html?tabs=mouse-controls#toolbox). Make sure to use the device-specific versions, e.g. `Device (Aeon.VertiGate)` instead of `Device (Harp)`. If correctly selected, the names of these operators in the workflow panel will change to reflect either the name of the device or the selected register/payload.

### Move the Gate

Write a target position to move the gate. The gate travels to that position at the configured speed and holds it.

:::workflow
![Move the Gate](../workflows/movethegate-movegate.bonsai)
:::

- Insert a [`KeyDown`] operator and set the `Filter` property to `A`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateTargetPositionPayload`.
    - `TargetPosition` - Set it to 0, which lowers the gate fully.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

In a separate branch:

- Insert a [`KeyDown`] operator and set the `Filter` property to `S`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateTargetPositionPayload`.
    - `TargetPosition` - Set it to 250, which raises the gate fully.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

In a separate branch:

- Insert a [`KeyDown`] operator and set the `Filter` property to `D`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateTargetPositionPayload`.
    - `TargetPosition` - Set it to 125, which moves the gate to the middle.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

Run the workflow and press <kbd>A</kbd>, <kbd>S</kbd>, or <kbd>D</kbd>. The gate moves to the matching position.

> [!WARNING]
> The gate stops at step 250, although the register accepts up to 255. A write of 251 to 255 moves the gate to the same place as 250. The travel is 12000 encoder counts and one step is 48 counts, so 250 steps already cover the whole range. The [overview](./vertigate-overview.md#the-top-of-the-position-range) explains why the scale is documented rather than corrected.

> [!NOTE]
> The device refuses a write to `TargetPosition` while the motor is off, and answers with an error. The motor is a state, not a one-off command. The [Enable the Motor](./enable-the-motor.md) article covers how to turn it on.

### Enable Position Events

The gate reports its position only when you ask for it. Write the `EnablePositionEvent` bit of the `Control` register to start the stream.

:::workflow
![Enable Position Events](../workflows/movethegate-enablepositionevents.bonsai)
:::

- Insert a [`KeyDown`] operator and set the `Filter` property to `F`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateControlPayload`.
    - `Control` - Select `EnableMotor` and `EnablePositionEvent`.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

Run the workflow and press <kbd>F</kbd>. The device starts to broadcast `Position` events every 50 ms while the gate moves.

> [!NOTE]
> Position events are sent only while the gate moves or homes. A gate that rests at its target sends nothing, so an empty visualizer between movements is the expected result, not a fault.

> [!TIP]
> The `Control` register keeps its state over a power cycle, so the stream is still on after a reboot. A read of `Control` reports the state and never the last command, which means `Stop` and `Calibrate` never appear in a read.

### Visualize Position Events

The VertiGate broadcasts events using the [Harp communication protocol](https://harp-tech.org/protocol/BinaryProtocol-8bit.html). To see where the gate is and what it is doing, decode the [`HarpMessages`] coming from the device with the workflow below.

:::workflow
![Move the Gate Visualize Events](../workflows/movethegate-visualizeevents.bonsai)
:::

- Insert a [`SubscribeSubject`] operator named `VertiGate Events`. This listens to the [`HarpMessages`] broadcast from the [`PublishSubject`] named `VertiGate Events` in the Harp device pattern.
- Insert a [`Parse`] operator and set the `Register` property to `TimestampedPosition`.
- Insert a [`VisualizerWindow`] operator. This opens a window with the parsed events when the workflow starts.

> [!NOTE]
> Every register event can be parsed in two forms, selected in the `Register` property of [`Parse`]. The bare payload (e.g. `Position`, used in [First Steps](./harp-bonsai.md#first-steps)) returns only the register values, while the timestamped variant (e.g. `TimestampedPosition`) returns the same payload wrapped in a `Value` field and adds a `Seconds` field carrying the device timestamp. Use the bare variant if it is enough for live monitoring, or the timestamped variant if you need to visualize the timestamp as well. Regardless of which option is chosen, all data is [logged](./logging-analysis.md) with device timestamps.

In a separate branch:

- Insert a [`SubscribeSubject`] operator named `VertiGate Events`.
- Insert a [`Parse`] operator and set the `Register` property to `TimestampedGateState`.
- Insert a [`VisualizerWindow`] operator.

Run the workflow and press <kbd>S</kbd> to raise the gate. The first visualizer displays:

```text
125@34.7168
```

The first number is the `Payload` value, which is the position of the gate on the same 0 to 250 scale as `TargetPosition`. The second number is the timestamp on the device clock. The second visualizer shows the gate state beside it, which steps through `Moving` and then `Up`.

### Alternative: Move the Gate with Timer

You can replace [`KeyDown`] with other operators to move the gate from other triggers in Bonsai, for instance a [`Timer`].

:::workflow
![Move the Gate Timer](../workflows/movethegate-timer.bonsai)
:::

- Insert a [`Timer`] operator and set the `DueTime` property to the number of seconds to wait before the gate moves, for example 2 seconds.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateTargetPositionPayload`.
    - `TargetPosition` - Set it to 250.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

Run the workflow and observe the gate rise after 2 seconds.

[!INCLUDE [](version-footer.md)]

<!--Reference Style Links -->
[`CreateMessage`]: xref:Aeon.VertiGate.CreateMessage
[`HarpMessages`]: xref:Bonsai.Harp.HarpMessage
[`KeyDown`]: xref:Bonsai.Windows.Input.KeyDown
[`MulticastSubject`]: xref:Bonsai.Expressions.MulticastSubject
[`Parse`]: xref:Aeon.VertiGate.Parse
[`PublishSubject`]: xref:Bonsai.Reactive.PublishSubject
[`SubscribeSubject`]: xref:Bonsai.Expressions.SubscribeSubject
[`Timer`]: xref:Bonsai.Reactive.Timer
[`VisualizerWindow`]: xref:Bonsai.Design.VisualizerWindow
