# Frozen modules for the VertiGate firmware image. Paths are relative to this file.

# The standard rp2 set: _boot.py, asyncio and the usual drivers.
include("$(PORT_DIR)/boards/manifest.py")

# USB CDC device support from micropython-lib. microharp's transport needs it.
require("usb-device-cdc")

# The Harp core and the servo driver, installed into lib/ by uv from the commits pinned in
# ../../pyproject.toml. See the libs group there for the command.
package("microharp", base_path="../../lib")
package("dynamixel", base_path="../../lib")

# The application. A frozen main.py runs at boot.
module("main.py", base_path="../../vertigate")
module("gate.py", base_path="../../vertigate")
module("register.py", base_path="../../vertigate")
module("settings.py", base_path="../../vertigate")
module("task.py", base_path="../../vertigate")
module("_version.py", base_path="../../vertigate")
