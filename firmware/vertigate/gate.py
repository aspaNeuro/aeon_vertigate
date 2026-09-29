from dynamixel import Dynamixel, DynamixelModel
from dynamixel.table import ControlTableItem
from micropython import const
from asyncio import Event
import asyncio
# TODO: check why we have some hex vs dec values in the constants below. 
# The hex values are from the Dynamixel docs, but the dec values are from the original firmware. 
# They should be equivalent, but we should check that.

TRQ_LIM = const(0x7F)
VEL_LIM = const(0xFF)
VEL_OFFSET = const(60)

TRQ_DEFAULT = const(35)
VEL_DEFAULT = const(255)

LENGTH = const(12000)
# Encoder counts per TargetPosition step. move() and position use the same
# scale, so a commanded value and a measured one can be compared.
POS_SCALE = const(48)

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

def clamp_torque(val):
    """The torque the servo is given, from what the host asked for."""
    return val & TRQ_LIM


def clamp_speed(val):
    """The speed the servo is given, from what the host asked for."""
    return val & VEL_LIM


def clamp_offset(val):
    """The calibration offset the gate keeps, from what the host asked for."""
    return max(min(val, POS_OFFSET_MAX), POS_OFFSET_MIN)


def scale_position(encoder, home):
    """Turn a pair of encoder counts into a TargetPosition step, 0 to 255.

    The task reports Position and RawPosition from one servo read, so it needs
    the same scale the `position` property uses.
    """
    pos = (encoder - home) // POS_SCALE
    return 0 if pos < 0 else 255 if pos > 255 else pos


class Gate(Dynamixel):

    def __init__(self, uart):
        super().__init__(uart, model=DynamixelModel.XM430_W210, id=1)
        self._offset = 0
        self.home_pos = 0
        self.target_pos = 0
        self._ismoving = False
        self._isup = False
        self._isdown = False
        self._iscalibrating = False
        self._iserror = False
        # Disable is a state, not a one-off command. While it is set, the
        # motor stays off and the gate refuses to move. Only enable() clears it.
        self._motor_disabled = False
        self.position_events = False
        self.telemetry_events = False
        self.isr = Event()
        self._task = None

        # The servo may be absent or unpowered. The device must still start,
        # so a failure here only sets the ERROR state. Calibrate retries.
        try:
            self._setup_servo()
        except Exception:
            self._iserror = True

    def _setup_servo(self):
        """Apply the operating mode and the default limits.

        Raises if the servo does not answer.
        """
        self.torque_enabled = False
        self.operating_mode = 5  # current control mode
        self.home_pos = self.present_position - LENGTH
        self.target_pos = self.home_pos
        self.speed = VEL_DEFAULT
        self.torque = TRQ_DEFAULT

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
        val = clamp_torque(val)
        self.torque_enabled = False
        self.current_limit = val
        # Do not switch the motor on if the host disabled it.
        self.torque_enabled = not self._motor_disabled

    @property
    def speed(self):
        return self.profile_velocity - VEL_OFFSET

    @speed.setter
    def speed(self, vel):
        vel = clamp_speed(vel)
        self.torque_enabled = False
        self.profile_velocity = vel + VEL_OFFSET
        # Do not switch the motor on if the host disabled it.
        self.torque_enabled = not self._motor_disabled

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, val):
        self._offset = clamp_offset(val)

    @property
    def max_pos(self):
        return self.home_pos + LENGTH + self._offset

    @property
    def position(self) -> int:
        """Where the gate is now, on the TargetPosition scale of 0 to 255.

        Raises if the servo does not answer.
        """
        return scale_position(self.present_position, self.home_pos)

    @property
    def raw_position(self):
        """The servo count and the recorded home, both in encoder counts.

        Position is built from this pair and then clamped, so the pair is what
        a calibration changes. Raises if the servo does not answer.
        """
        return (self.present_position, self.home_pos)

    @property
    def telemetry(self):
        """Voltage in 0.1 V, temperature in C, current in mA, and the servo
        hardware error status. Raises if the servo does not answer.
        """
        return (
            self._read_value(ControlTableItem.PRESENT_INPUT_VOLTAGE),
            self._read_value(ControlTableItem.PRESENT_TEMPERATURE),
            self.present_current,
            self._read_value(ControlTableItem.HARDWARE_ERROR_STATUS),
        )

    @property
    def motor_enabled(self) -> bool:
        return not self._motor_disabled

    def enable(self):
        self._motor_disabled = False
        self.torque_enabled = True
        self.isr.set()

    def disable(self):
        self._motor_disabled = True
        self.stop()
        self.torque_enabled = False
        self.isr.set()

    def lower_down(self):
        if self.status != DOWN:
            self.move(0)

    def raise_up(self):
        if self.status != UP:
            self.move(255)

    def move(self, pos):
        pos = POS_SCALE * pos + self.home_pos
        pos = self.home_pos if pos < self.home_pos else pos
        pos = self.max_pos if pos > self.max_pos else pos
        self.target_pos = pos
        self._start(self._run())

    def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
            try:
                self.goal_position = self.present_position
            except Exception:
                self._iserror = True
            self._ismoving = False
            self.isr.set()

    def start_calibration(self):
        self._start(self.calibrate())

    def _start(self, coro):
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(coro)

    async def _run(self):
        self._isup = False
        self._isdown = False
        try:
            self._enable()

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
        except Exception:
            # A servo comms error. A CancelledError passes through.
            self._iserror = True
        finally:
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

        Homing drives the gate into the end stop, so `_setup_servo` puts the
        safe default speed and torque on the servo. The values the host set
        are read first and put back at the end, so a calibration does not
        change them.
        """
        self._iserror = False
        self._isup = False
        self._isdown = False
        self._iscalibrating = True
        self.isr.set()
        try:
            speed, torque = self.speed, self.torque
            self._setup_servo()
            await asyncio.wait_for_ms(self._find_home(), CAL_TIMEOUT_MS)
            self.home_pos = self.present_position + CAL_HOME_OFFSET
            self.target_pos = self.home_pos
            self._isdown = True
            # Put the values back before the motor is released. Both setters
            # switch the motor on, so the order matters.
            self.speed = speed
            self.torque = torque
            self.torque_enabled = False
        except Exception:
            # asyncio.TimeoutError, or a servo comms error. A CancelledError
            # from move() or stop() is a BaseException and passes through.
            self._iserror = True
            try:
                self.torque_enabled = False
            except Exception:
                pass
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
