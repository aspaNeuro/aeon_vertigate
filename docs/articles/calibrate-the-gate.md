## Calibrate the Gate

The gate measures its position against a reference it finds for itself. Calibration drives the gate down to the lower end stop and records that encoder count as home. Every position after that is counted from there. Refer to the [connections](./connections.md?tabs=servo#connections) article to set up the servo, which we will use for the rest of these examples.

This article covers how to run a calibration, how to trim the fully raised position without moving hardware, and how to watch the raw encoder counts in Bonsai.

The complete workflow is shown below. Copy and paste it into Bonsai, or build each section by following the step-by-step instructions.

:::workflow
![Calibrate the Gate](../workflows/calibratethegate-toplevel.bonsai)
:::

### Calibrate the Gate

The `Calibrate` bit of the `Control` register starts the homing routine. The gate drives down until the position stops changing, and records that point as home.

:::workflow
![Calibrate the Gate](../workflows/calibratethegate-calibrate.bonsai)
:::

- Insert a [`KeyDown`] operator and set the `Filter` property to `A`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateControlPayload`.
    - `Control` - Select `EnableMotor` and `Calibrate`.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

Run the workflow and press <kbd>A</kbd>. The gate moves down, stops at the end stop, and `GateState` reports `Calibrating` and then `Down`.

> [!NOTE]
> Calibration needs the motor. The device refuses a `Calibrate` command while the motor is off, unless the same write also sets `EnableMotor`. That is why the example sets both bits together.

> [!TIP]
> The gate calibrates itself at start-up, so a normal session needs no manual calibration. Run one after you move the hardware, after a `Stop` interrupted an earlier calibration, or when the servo reported an error and you have corrected it.

> [!WARNING]
> If the servo does not answer, `GateState` reports `Error` and the gate does not move. Correct the connection, then calibrate again.

### Trim the Fully Raised Position

`CalibrationOffset` shifts the fully raised end of the travel without touching the hardware. One count is one encoder count, which is 25 µm.

:::workflow
![Trim the Fully Raised Position](../workflows/calibratethegate-offset.bonsai)
:::

- Insert a [`KeyDown`] operator and set the `Filter` property to `S`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateCalibrationOffsetPayload`.
    - `CalibrationOffset` - Set it to 10, which raises the top of the travel by 250 µm. Negative values lower it.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

Run the workflow and press <kbd>S</kbd>. The next movement to the top of the travel settles 250 µm higher.

> [!NOTE]
> `CalibrationOffset` is non-volatile, so the value survives a power cycle. The device stores it on the flash when it changes, and a write that changes nothing does not touch the flash.

### Visualize the Raw Encoder Counts

`Position` is clamped to the range 0 to 250, which hides two things: the travel below home, and the moment a calibration records a new home. `RawPosition` reports the two encoder counts that `Position` is built from, so both become visible.

:::workflow
![Visualize the Raw Encoder Counts](../workflows/calibratethegate-visualizeevents.bonsai)
:::

- Insert a [`SubscribeSubject`] operator named `VertiGate Events`. This listens to the [`HarpMessages`] broadcast from the [`PublishSubject`] named `VertiGate Events` in the Harp device pattern.
- Insert a [`Parse`] operator and set the `Register` property to `TimestampedRawPosition`.
- Insert a [`VisualizerWindow`] operator. This opens a window with the parsed events when the workflow starts.

`RawPosition` rides on the same stream as `Position`, so it needs `EnablePositionEvent`. The [Move the Gate](./move-the-gate.md#enable-position-events) article covers how to turn that on.

Run the workflow, turn the position stream on, and press <kbd>A</kbd> to calibrate. The visualizer shows an `Encoder` value and a `Home` value. `Encoder` falls while the gate goes down. `Home` holds its old value throughout, and then changes once at the end of the calibration. **The size of that step is the error in the previous home.**

> [!TIP]
> The gate rests about 400 encoder counts below `Home`, which is 10 mm. `Position` therefore reads 0 for the last 10 mm of travel. This is deliberate, so that the platform sits fully down against the stop. `RawPosition` is the only way to see that part of the movement.

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
