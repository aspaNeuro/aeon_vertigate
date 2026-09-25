# swc-aeon-vertigate

The Python interface for the VertiGate Harp device, generated from
[`device.yml`](../../device.yml) with `harp.toolkit`.

```python
from swc.aeon.device.vertigate import GateState, Position, TargetPosition
```

`swc`, `swc.aeon` and `swc.aeon.device` are namespace packages, laid out the
same way as [`aeon_api`](https://github.com/SainsburyWellcomeCentre/aeon_api).

## The hardware test

```bash
uv run --extra test vertigate-test --port COM4
```

It checks the device against `device.yml` on a live board: the identity, the
register map, the motor latch, the event streams and the non-volatile settings.
Pass `--scale` to also measure the top of the `TargetPosition` range, and
`--no-reboot` to skip the checks that restart the board.

## Regenerating

Do not edit `__init__.py`. It is generated:

```bash
dotnet harp.toolkit generate interface python device.yml --package \
  --output software/python/src/swc/aeon/device/vertigate
```

CI regenerates it and fails if the committed file differs.
