# The single file firmware image

There are two ways to put VertiGate firmware on a board.

**For development**, copy the Python files with `mpremote`, as the
[README](../README.md) describes. The files live on the board file system. You
change one file and copy it again in a second.

**For a release**, flash one `.uf2`. The image holds MicroPython, the VertiGate
firmware, `micropython-microharp` and `micropython-dynamixel`, all frozen in.
There is nothing to `mip install` and no file to forget. One file makes one
working device.

This page covers the second way.

## What the image is

The file is named for the versions it carries, for example:

```
VertiGate-fw0.1-harp1.13-hw0.1-ass0.uf2
```

A valid image for this board reads like this:

| Property | Value |
| --- | --- |
| Family | `0xE48BFF59`, RP2350 ARM-S |
| Blocks | about 1500 |
| Size | about 800 kB |

The family matters. The NeuroPico uses an **RP2350**. A UF2 built for an RP2040
has family `0xE48BFF56`, and the boot loader ignores it.

To read those values from any `.uf2`:

```bash
uv run python - <<'EOF'
import struct, sys
d = open(sys.argv[1] if len(sys.argv) > 1 else "image.uf2", "rb").read()
fams = set()
for i in range(len(d) // 512):
    m0, m1, fl, addr, sz, bno, nb, fam = struct.unpack("<8I", d[i*512:i*512+32])
    assert m0 == 0x0A324655 and m1 == 0x9E5D5157, "not a UF2"
    fams.add(fam)
print(len(d)//512, "blocks, families:", [hex(f) for f in fams])
EOF
```

## Do not use flash_nuke.uf2

The README used to send you to
[flash_nuke.uf2](https://datasheets.raspberrypi.com/soft/flash_nuke.uf2). That
file is an **RP2040** image, family `0xE48BFF56`. It does nothing on an RP2350.

You do not need it. The step it was there for is to clear the file system, and
MicroPython can do that itself.

## Why the file system must be cleared first

MicroPython imports from the file system **before** it looks at frozen modules.
It also runs a file system `main.py` in place of a frozen one.

So a board that already has the loose files keeps running them after you flash
the image. The device works, and none of the frozen code runs. Nothing warns
you.

Clear the file system before you flash:

```bash
uv run mpremote connect COM3 resume exec "
import os, rp2
os.umount('/')
os.VfsLfs2.mkfs(rp2.Flash())
os.mount(rp2.Flash(), '/')
print(sorted(os.listdir('/')))
"
```

This removes the firmware files, `lib/`, `settings.json` and `error.log`. The
board then has bare MicroPython and no VertiGate firmware until you flash.

## Flashing

1. Clear the file system, as above.
2. Hold **BOOTSEL** and plug the board in. A drive named `RP2350` appears.
3. Copy the `.uf2` to that drive.
4. The board reboots by itself. Two COM ports appear after a few seconds.

## Checking the result

```bash
uv run --all-extras vertigate-test --port COM4
dotnet harp.toolkit verify --port COM4 --metadata device.yml --report artifacts/verify.html
```

Four things say the image is good:

- **Two COM ports.** This is the real test. A frozen `main.py` starts
  differently from a file system `main.py`, so two ports prove the frozen code
  runs.
- **The hardware test passes**, 28 of 28.
- **The file system holds only `settings.json`.** No `lib/`, no `.py` files. If
  you see any, they are shadowing the image.
- **Every register in `device.yml` answers.** Read the highest address. A
  register that the host refuses means the image is older than `device.yml`.

That last check matters. An image built from stale source passes every other
check, because the older firmware is still correct firmware. Read a register
that only the new code has:

```bash
uv run --all-extras python -c "
from harp.serial import open_device
from aeon.vertigate.device import MotorState
with open_device(port='COM4', raise_on_error=False) as dev:
    print(dev.read(MotorState).payload)
"
```

## Going back to the development files

The frozen image stays on the board. To work on the firmware again, copy the
files over it. They shadow the frozen modules, which is what you want here:

```bash
uv run mpremote connect COM3 resume cp -r firmware/. :
uv run mpremote connect COM3 reset
```

## What we measured

Tested on 2026-09-23, on a NeuroPico with MicroPython v1.29.0:

| Check | Result |
| --- | --- |
| Frozen `main.py` runs at boot from an empty file system | yes, both ports appeared |
| microharp and dynamixel frozen in | yes, no `lib/` on the board |
| Hardware test on the frozen build | 28 of 28 |
| `settings.json` created on a blank file system | yes, survived a reboot and restored to defaults |

The non-volatile settings had never started from an empty file system before.
That path works.

## Open item: the build is not reproducible

There is no script in this repository that builds the `.uf2`. The image was
built by hand. A release image that nobody can rebuild is not a release.

The recipe belongs here, as a script under `tools/`, and the image should carry
the commit it was built from. Until then, treat any `.uf2` as unverified: read a
register that only the current `device.yml` declares, as above, before you trust
it.
