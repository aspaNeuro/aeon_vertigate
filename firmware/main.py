import asyncio
from machine import Pin, UART
from usb.device.cdc import CDCInterface
import usb.device
from gate import Gate
from register import ADDR_STATUS, setup_register_handlers
from task import setup_user_task


from microharp import HarpDevice, CdcTransport

Pin(11, Pin.OUT, value=1)
Pin(12, Pin.OUT, value=0)
Pin(13, Pin.OUT, value=1)

myled = Pin(7, Pin.OUT, value=0)
myCLK = UART(0, baudrate=100_000, rx=Pin(1))
myGate = Gate(UART(1, baudrate=1_000_000, tx=Pin(8), rx=Pin(9)))
cdc = CDCInterface(baudrate=1_000_000, timeout=0, txbuf=2048, rxbuf=512)
usb.device.get().init(cdc, builtin_driver=False)

device = HarpDevice(
    transport=CdcTransport(cdc),
    sync_uart=myCLK,
    led_pin=myled,
    who_am_i=5350,
    device_name=b"VertiGate"
)

setup_register_handlers(device, myGate)
setup_user_task(device, myGate, ADDR_STATUS)

asyncio.run(device.run())

