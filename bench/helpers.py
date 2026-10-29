import time

import can
import cantools

from ecu_sim.ecu import DBC_PATH

DB = cantools.database.load_file(str(DBC_PATH))
STATUS = DB.get_message_by_name("ENGINE_STATUS")
INPUT = DB.get_message_by_name("SENSOR_INPUT")


def send_sensor(bus, temp, valid=1):
    data = INPUT.encode({"SimCoolantTemp": temp, "SimSensorValid": valid})
    bus.send(can.Message(arbitration_id=INPUT.frame_id,
                         data=data, is_extended_id=False))


def drain(bus):
    """Throw away frames that are already waiting in the receive queue."""
    while bus.recv(timeout=0) is not None:
        pass


def recv_status(bus, timeout=1.0):
    """Return (rx_time, signals) of the next ENGINE_STATUS frame, or None.

    rx_time is time.monotonic() at reception. We do not use msg.timestamp
    (wall clock), because the WSL clock can jump and distort time measurements.
    """
    end = time.monotonic() + timeout
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            return None
        msg = bus.recv(timeout=remaining)
        if msg is not None and msg.arbitration_id == STATUS.frame_id:
            return time.monotonic(), STATUS.decode(msg.data)


def read_after(bus, t_min, timeout=1.0):
    """First ENGINE_STATUS frame received at or after t_min (time.monotonic())."""
    end = time.monotonic() + timeout
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            return None
        frame = recv_status(bus, timeout=remaining)
        if frame is None:
            return None
        if frame[0] >= t_min:
            return frame


def apply_and_read(bus, temp, valid=1, settle=0.05):
    """Send a sensor value and return the first status frame that reflects it."""
    drain(bus)
    t_send = time.monotonic()
    send_sensor(bus, temp, valid)
    frame = read_after(bus, t_send + settle)
    assert frame is not None, "no ENGINE_STATUS received after SENSOR_INPUT"
    return frame[1]


def collect_status(bus, count, timeout=30.0):
    frames = []
    end = time.monotonic() + timeout
    while len(frames) < count and time.monotonic() < end:
        frame = recv_status(bus, timeout=1.0)
        if frame:
            frames.append(frame)
    return frames
