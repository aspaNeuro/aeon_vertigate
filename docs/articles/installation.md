## Installation

This page covers the software you need to work with the VertiGate, and how to put firmware on the device.

## Software Packages

These steps are only required the first time you connect the device to a new computer. Install the packages for the functionality you need.

# [Bonsai](#tab/bonsai)

[Bonsai](https://bonsai-rx.org/) is a visual reactive programming language that gives flexible control of the VertiGate.

[placeholder - installation-bonsaipackage.png]{width=650}

- Download and install [Bonsai](https://bonsai-rx.org/docs/articles/installation.html).
- Launch Bonsai and install the `Aeon.VertiGate` package. Search for it in the [Bonsai package manager](https://bonsai-rx.org/docs/articles/packages.html). Select the "Show advanced" checkbox if it does not appear.
- (Optional) Install the `Bonsai.Windows.Input` package to follow the examples in this user guide.

> [!WARNING]
> **TODO**: `Aeon.VertiGate` is not published to a public feed yet. Until the first release, build the package from the repository and start Bonsai with `./bonsai.ps1`, which adds the local build to the library search path. Replace this callout with the feed name once the package is published.

# [Python](#tab/python)

The `swc-aeon-vertigate` package gives a Python interface for the VertiGate and for [loading](logging-analysis.md) recorded data. Install it with:

```cmd
pip install swc-aeon-vertigate
```

> [!NOTE]
> Substitute `uv add` for `pip install` if you use the [uv](https://docs.astral.sh/uv/) package manager.

> [!WARNING]
> **TODO**: `swc-aeon-vertigate` is not published to PyPI yet. Until the first release, install it from a checkout with `uv sync --project software/python`.

***

## Firmware

Each [release](https://github.com/SainsburyWellcomeCentre/aeon_vertigate/releases) attaches one firmware image, named for the versions it carries:

```text
VertiGate-fw0.1-harp1.13-hw0.1-ass0.uf2
```

The image is a MicroPython build with the VertiGate application, `micropython-microharp`, and `micropython-dynamixel` frozen inside. There is nothing else to install. One file makes one working device.

> [!TIP]
> The release tag matches `firmwareVersion` in `device.yml` in its major and minor parts. Continuous integration checks this and stops the release if they differ, so the `fw` part of the file name always states the firmware the device reports.

### Flash the Image

1. Hold **BOOTSEL** and plug the board in. A drive named `RP2350` appears.
2. Copy the `.uf2` to that drive.
3. The board reboots by itself. Two serial ports appear after a few seconds.

To update, flash the new `.uf2` the same way. The settings file and the error log on the board survive, because the image only replaces the firmware region.

> [!WARNING]
> Do not use `flash_nuke.uf2`. That file is an RP2040 image, and this board is an RP2350, so the boot loader ignores it.

### Clear the File System First

Do this once, and only when the board previously held the firmware as loose Python files.

The frozen image and loose files do not mix. MicroPython starts the **frozen** `main.py`, but `import` searches the file system **before** the frozen modules. An old frozen `main.py` then runs against new modules from the file system, or the reverse. This is not a clean fall back. It fails in ways that point nowhere useful:

```text
TypeError: function takes 4 positional arguments but 3 were given
```

Clear the file system from the REPL before you flash:

```bash
uv run --project firmware mpremote connect COM3 resume exec "
import os, rp2
os.umount('/')
os.VfsLfs2.mkfs(rp2.Flash())
os.mount(rp2.Flash(), '/')
print(sorted(os.listdir('/')))
"
```

This removes the firmware files, `lib/`, `settings.json`, and `error.log`. A board straight from the factory needs nothing here.

### Check the Result

Four things say the image is good.

- **The board reports its own name.** This is the real test. A board running the release image names itself `Dynamixel Controller`. A board running a stock MicroPython build names itself after that build, for example `Seeed XIAO RP2350`. Read it over the REPL port:

  ```bash
  uv run --project firmware mpremote connect COM3 resume exec "import os; print(os.uname().machine)"
  ```

- **Two serial ports appear.** Both ports come up either way, because `main.py` creates the second one whether it is frozen or on the file system. Two ports mean the application started. They do not tell you which copy of it started.
- **The hardware test passes.** Use the Harp port, not the REPL port:

  ```bash
  uv run --project software/python --group dev python software/python/tests/hwtest.py --port COM4
  ```

  It runs 39 checks without a servo and reports the `Error` gate state, which the test expects. With a servo connected it also runs the position and telemetry checks. It reboots the board four times to prove that the non-volatile settings survive, so it takes about a minute.

- **The file system holds only `settings.json`.** No `lib/`, no `.py` files. Anything else shadows the image.
- **The device answers on every register.** Read the highest address. A register that the host refuses means the image is older than `device.yml`.

That last check matters. An image built from stale source passes every other check, because older firmware is still correct firmware.

### Develop the Firmware

The image runs its frozen `main.py` even when a `main.py` is on the file system, so you cannot use it to try out changes. For development, run the Python files from the file system of a stock MicroPython build.

> [!WARNING]
> Use the **`SEEED_XIAO_RP2350`** build, v1.29.0 or later. Do not use the `RPI_PICO2` build. The board has 2 MB of flash and `RPI_PICO2` assumes 4 MB, so its file system wraps onto the firmware. The board works for a while, then freezes or corrupts its files.

1. Enter the boot loader, clear the flash as above, then copy the [SEEED_XIAO_RP2350](https://micropython.org/download/SEEED_XIAO_RP2350/) image to the drive.
2. Install the host tools. Install [uv](https://docs.astral.sh/uv/), then create the firmware environment:

   ```bash
   uv sync --project firmware
   ```

3. Install the libraries on the board. Replace `COM3` with your port. The commits are the ones `firmware/pyproject.toml` pins, which is what the release image is built from.
4. Copy the firmware, then reset the board:

   ```bash
   uv run --project firmware mpremote connect COM3 resume cp -r firmware/vertigate/. :
   uv run --project firmware mpremote connect COM3 reset
   ```

The Harp port comes back about 10 seconds after the reset. If it does not come back, unplug the board and plug it in again. The USB stack can stay down after several soft resets.

> [!NOTE]
> `mpremote` stops the running firmware. It enters the raw REPL, which raises `KeyboardInterrupt` inside the device loop, and the Harp port disappears. Add `resume` to attach without a reset, and send `reset` when you finish.

If the device does not start, read the log it writes on the board:

```bash
uv run --project firmware mpremote connect COM3 resume cat :error.log
```

[!INCLUDE [](version-footer.md)]
