## Tune the Motion

Speed and torque shape how the gate moves. Lower the speed for slower, smoother motion. Raise the torque if the gate stalls, or lower it if the gate pushes too hard against the end stops. Refer to the [connections](./connections.md?tabs=servo#connections) article to set up the servo, which we will use for the rest of these examples.

This article covers how to set the speed, how to set the torque, and how to read back the value the device actually applied in Bonsai.

The complete workflow is shown below. Copy and paste it into Bonsai, or build each section by following the step-by-step instructions.

:::workflow
![Tune the Motion](../workflows/tunethemotion-toplevel.bonsai)
:::

> [!WARNING]
> Writing `Speed` or `Torque` switches the motor off and on. If the gate is holding a position, it drops for a moment. Set both before a session rather than during one, and never while the gate carries something you care about.

### Set the Speed

`Speed` maps onto the profile velocity of the servo. Each count adds 0.38 mm/s.

:::workflow
![Set the Speed](../workflows/tunethemotion-speed.bonsai)
:::

- Insert a [`KeyDown`] operator and set the `Filter` property to `A`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateSpeedPayload`.
    - `Speed` - Set it to 120, which is about half of the range.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

Run the workflow and press <kbd>A</kbd>. The next movement runs at the new speed.

> [!NOTE]
> `Speed` 0 is the slowest motion, not a stop. The device adds a fixed offset of 60 before it reaches the servo, so the gate always keeps moving. To halt a movement, use the `Stop` bit of `Control`, which [Enable the Motor](./enable-the-motor.md#stop-the-gate) covers.

### Set the Torque

`Torque` is applied as a current limit on the servo. One count is 0.36 kgf·mm. The default is 35.

:::workflow
![Set the Torque](../workflows/tunethemotion-torque.bonsai)
:::

- Insert a [`KeyDown`] operator and set the `Filter` property to `S`.
- Insert a [`CreateMessage`] operator and configure these properties:
    - `Payload` - Select `CreateTorquePayload`.
    - `Torque` - Set it to 200, which the device masks to 72. The next section shows how to see that.
- Insert a [`MulticastSubject`] operator and set the `Name` property to `VertiGate Commands`.

Run the workflow and press <kbd>S</kbd>. The gate now pushes with the new limit.

> [!WARNING]
> `Torque` is masked to seven bits. A write of 200 is applied as 72, because 200 and 0x7F is 72. The register accepts 0 to 127. Anything above 127 wraps rather than saturates, so a large value can give a much smaller limit than you expect.

> [!NOTE]
> Both `Speed` and `Torque` are non-volatile. They survive a power cycle, and the device writes them to the flash only when the value changes.

### Visualize the Applied Value

The device answers every write with a reply carrying the value it actually applied, not the value you sent. That is how you confirm the masking described above. `Speed` and `Torque` broadcast no events of their own, so this section decodes the write replies instead.

:::workflow
![Visualize the Applied Value](../workflows/tunethemotion-visualizeevents.bonsai)
:::

- Insert a [`SubscribeSubject`] operator named `VertiGate Events`. This listens to the [`HarpMessages`] broadcast from the [`PublishSubject`] named `VertiGate Events` in the Harp device pattern.
- Insert a [`Parse`] operator and set the `Register` property to `TimestampedTorque`.
- Insert a [`VisualizerWindow`] operator. This opens a window with the parsed replies when the workflow starts.

[`Parse`] matches messages by register address and ignores the message type, so it picks up the write reply without a filter. That is what we want here.

Run the workflow and press <kbd>S</kbd> to write 200. The visualizer displays:

```text
72@41.5520
```

The first number is the value the device applied, and the second is the timestamp on the device clock. You sent 200 and the device applied 72.

> [!TIP]
> The device does not read the value back from the servo to build this reply. The current limit lives in the servo EEPROM, and a read straight after a write can still return the old value. The device reports the number it computed and stored, which is the number it sent to the servo.

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
