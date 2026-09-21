from dynamixel import Dynamixel, DynamixelModel
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
CALIBRATING = const(0x04)
ERROR = const(0xFF)

TOLERANCE = const(20)

POS_OFFSET_MAX = const(127)
POS_OFFSET_MIN = const(-128)

# Homing: the motor is at the end stop when the position changes by less
# than CAL_STEP for CAL_STABLE_COUNT samples in a row.
CAL_STEP = const(10)
CAL_STABLE_COUNT = const(10)
CAL_SAMPLE_MS = const(10)
CAL_SETTLE_MS = const(200)
CAL_TIMEOUT_MS = const(10_000)
CAL_HOME_OFFSET = const(400)  # Small offset so the platform is fully lowered

class Gate(Dynamixel):

    def __init__(self, uart):
        super().__init__(uart, model=DynamixelModel.XM430_W210, id=1)
        self._offset = 0
        self.torque_enabled = False
        self.operating_mode = 5  # current control mode
        self.home_pos = self.present_position - LENGTH
        self.speed = VEL_DEFAULT
        self.torque = TRQ_DEFAULT

        self.target_pos = self.home_pos
        self._ismoving = False
        self._isup = False
        self._isdown = False
        self._iscalibrating = False
        self._iserror = False
        self.position_events = False
        self.telemetry_events = False
        self.isr = Event()
        self._task = None

    @property
    def status(self) -> int:
        if self._iserror:
            return ERROR
        elif self._iscalibrating:
            return CALIBRATING
        elif self._ismoving:
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

    def enable(self):
        self.torque_enabled = True

    def disable(self):
        self.torque_enabled = False

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
        self._start(self._run())

    def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
            self.goal_position = self.present_position
            self._ismoving = False
            self.isr.set()

    def start_calibration(self):
        self._start(self.calibrate())

    def _start(self, coro):
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(coro)

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

    async def calibrate(self):
        """Drive the gate to the lower end stop and record it as home.

        Runs as a task, so the device stays on the bus while homing.
        On timeout or a servo error the gate enters the ERROR state.
        """
        self._iserror = False
        self._isup = False
        self._isdown = False
        self._iscalibrating = True
        self.isr.set()
        try:
            await asyncio.wait_for_ms(self._find_home(), CAL_TIMEOUT_MS)
            self.home_pos = self.present_position + CAL_HOME_OFFSET
            self.target_pos = self.home_pos
            self._isdown = True
            self.torque_enabled = False
        except Exception:
            # asyncio.TimeoutError, or a servo comms error. A CancelledError
            # from move() or stop() is a BaseException and passes through.
            self._iserror = True
            self.torque_enabled = False
        finally:
            self._iscalibrating = False
            self.isr.set()

    async def _find_home(self):
        self.torque_enabled = True
        self.goal_extend_position = self.home_pos
        last_pos = self.present_position
        await asyncio.sleep_ms(CAL_SETTLE_MS)
        stable = 0
        while stable <= CAL_STABLE_COUNT:
            pos = self.present_position
            if abs(last_pos - pos) < CAL_STEP:
                stable += 1
            last_pos = pos
            await asyncio.sleep_ms(CAL_SAMPLE_MS)
