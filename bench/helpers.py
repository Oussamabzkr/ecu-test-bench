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


def recv_status(bus, timeout=1.0):
    """Return (timestamp, signals) of the next ENGINE_STATUS frame, or None."""
    end = time.monotonic() + timeout
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            return None
        msg = bus.recv(timeout=remaining)
        if msg is not None and msg.arbitration_id == STATUS.frame_id:
            return msg.timestamp, STATUS.decode(msg.data)