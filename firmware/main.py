import asyncio
import sys
from machine import Pin, UART
from usb.device.cdc import CDCInterface
import usb.device
from gate import Gate
from register import ADDR_GATE_STATE, ADDR_MOTOR_STATE, setup_register_handlers
from task import setup_user_task


from microharp import HarpDevice, CdcTransport
from microharp.registers import R_HARP_VERSION_H, R_HARP_VERSION_L

# Keep these equal to device.yml. Bonsai reads them on connect.
WHO_AM_I = 3002
FW_VERSION = (0, 1)
HW_VERSION = (0, 1)
# Version of the Harp device specification this firmware follows. Bonsai
# shows it as CoreVersion. 1.13 is the current release of harp-tech/protocol.
HARP_VERSION = (1, 13)


def main():
    Pin(11, Pin.OUT, value=1)
    Pin(12, Pin.OUT, value=0)
    Pin(13, Pin.OUT, value=1)

    myled = Pin(7, Pin.OUT, value=0)
    myCLK = UART(0, baudrate=100_000, rx=Pin(1))
    myGate = Gate(UART(1, baudrate=1_000_000, tx=Pin(8), rx=Pin(9)))
    # builtin_driver=True keeps the MicroPython REPL on its own USB serial port
    # next to the Harp port. mpremote and tracebacks stay available. Set it to
    # False for a release build with a single port.
    cdc = CDCInterface(baudrate=1_000_000, timeout=0, txbuf=2048, rxbuf=512)
    usb.device.get().init(cdc, builtin_driver=True)

    device = HarpDevice(
        transport=CdcTransport(cdc),
        sync_uart=myCLK,
        led_pin=myled,
        who_am_i=WHO_AM_I,
        fw_version=FW_VERSION,
        hw_version=HW_VERSION,
        device_name=b"VertiGate"
    )
    # microharp has no parameter for the core version. Write the registers.
    device.bank.get(R_HARP_VERSION_H).storage[0] = HARP_VERSION[0]
    device.bank.get(R_HARP_VERSION_L).storage[0] = HARP_VERSION[1]

    setup_register_handlers(device, myGate)
    setup_user_task(device, myGate, ADDR_GATE_STATE, ADDR_MOTOR_STATE)

    # Home the gate once the device is running, so USB comes up first.
    # Control.Calibrate runs the same task again on request.
    @device.task
    async def _home_at_boot():
        myGate.start_calibration()

    asyncio.run(device.run())


# Any exception is also written to error.log, because the USB console is
# not connected while the firmware re-initialises USB. Read it with:
#   mpremote connect COMx resume cat :error.log
try:
    main()
except BaseException as e:
    with open("error.log", "w") as f:
        sys.print_exception(e, f)
    raise
