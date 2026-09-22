import asyncio
import sys
from machine import Pin, UART
from usb.device.cdc import CDCInterface
import usb.device
from gate import Gate
from register import ADDR_STATUS, setup_register_handlers
from task import setup_user_task


from microharp import HarpDevice, CdcTransport


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
        who_am_i=5350,
        device_name=b"VertiGate"
    )

    setup_register_handlers(device, myGate)
    setup_user_task(device, myGate, ADDR_STATUS)

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
