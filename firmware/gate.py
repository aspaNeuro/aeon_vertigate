from dynamixel import Dynamixel, DynamixelModel
import time
from micropython import const
from asyncio import Event
import asyncio

TRQ_LIM = const(0x7F)
VEL_LIM = const(0xFF)
VEL_OFFSET = const(60)

TRQ_DEFAULT = const(35)
VEL_DEFAULT = const(255)

LENGTH = const(12000)

IDLE = const(0x00)
UP = const(0x01)
DOWN = const(0x02)
MOVING = const(0x03)

TOLERANCE = const(20)

POS_OFFSET_MAX = const(127)
POS_OFFSET_MIN = const(-128)

class Gate(Dynamixel):

    def __init__(self, uart):
        super().__init__(uart, model=DynamixelModel.XM430_W210, id=1)
        self._offset = 0
        self.torque_enabled = False
        self.operating_mode = 5  # current control mode
        self.home_pos = self.present_position - LENGTH
        self.speed = VEL_DEFAULT
        self.torque = TRQ_DEFAULT
        self._calibrate_home()

        self.target_pos = self.home_pos
        self._ismoving = False
        self._isup = False
        self._isdown = False
        self.isr = Event()
        self._task = None

    @property
    def status(self) -> int:
        if self._ismoving:
            return MOVING
        elif self._isup:
            return UP
        elif self._isdown:
            return DOWN
        return IDLE

    @property
    def torque(self):
        return self.current_limit

    @torque.setter
    def torque(self, val):
        val &= TRQ_LIM
        self.torque_enabled = False
        self.current_limit = val
        self.torque_enabled = True

    @property
    def speed(self):
        return self.profile_velocity - VEL_OFFSET

    @speed.setter
    def speed(self, vel):
        vel &= VEL_LIM
        self.torque_enabled = False
        self.profile_velocity = vel + VEL_OFFSET
        self.torque_enabled = True

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, val):
        val = max(min(val, POS_OFFSET_MAX), POS_OFFSET_MIN)
        self._offset = val

    @property
    def max_pos(self):
        return self.home_pos + LENGTH + self._offset

    def lower_down(self):
        if self.status != DOWN:
            self.move(0)

    def raise_up(self):
        if self.status != UP:
            self.move(255)

    def move(self, pos):
        pos = 48 * pos + self.home_pos
        pos = self.home_pos if pos < self.home_pos else pos
        pos = self.max_pos if pos > self.max_pos else pos
        self.target_pos = pos
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(self._run())

    def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
            self.goal_position = self.present_position
            self._ismoving = False
            self.isr.set()

    async def _run(self):
        self._enable()

        self._isup = False
        self._isdown = False

        if self.target_pos > self.present_position:
            while self.present_position < self.target_pos - TOLERANCE:
                await asyncio.sleep_ms(50)
        else:
            while self.present_position > self.target_pos + TOLERANCE:
                await asyncio.sleep_ms(50)

        if self.target_pos == self.home_pos:
            await asyncio.sleep_ms(100)
            self.torque_enabled = False
            await asyncio.sleep_ms(500)
            self._isdown = True
        elif self.target_pos == self.max_pos:
            self._isup = True

        self._disable()

    def _disable(self):
        self._ismoving = False
        self.isr.set()

    def _enable(self):
        self.torque_enabled = True
        self.goal_extend_position = self.target_pos
        self._ismoving = True
        self.isr.set()

    def _calibrate_home(self):
        self.torque_enabled = True
        self.goal_extend_position = self.home_pos
        last_pos = self.present_position
        time.sleep(0.2)
        conuter = 0
        while True:
            pos = self.present_position
            if abs(last_pos - pos) < 10:  # Check if the motor is close to the home position
                conuter += 1
            if conuter > 10:
                break
            last_pos = pos
            time.sleep(0.01)
        self.torque_enabled = False
        self.home_pos = self.present_position + 400  # Add a small offset to ensure the platform is fully lowered
