import threading
import time
from pathlib import Path

import can
import cantools

DBC_PATH = Path(__file__).resolve().parents[1] / "dbc" / "ecu.dbc"


class SimulatedEcu:
    """Coolant temperature / fan ECU simulated in Python (CAN part)."""

    FAN_ON_ABOVE = 95
    FAN_OFF_BELOW = 90
    MAX_VALID_TEMP = 150

    def __init__(self, channel, interface="virtual", cycle_time=0.1):
        self.db = cantools.database.load_file(str(DBC_PATH))
        self.status = self.db.get_message_by_name("ENGINE_STATUS")
        self.sensor_input = self.db.get_message_by_name("SENSOR_INPUT")
        self.bus = can.Bus(interface=interface, channel=channel)
        self.cycle_time = cycle_time
        self.coolant_temp = 20
        self.sensor_valid = 1
        self.fan_on = 0
        self.alive = 0
        self._stop = threading.Event()
        self._threads = []

    def start(self):
        self._stop.clear()
        self._threads = [
            threading.Thread(target=self._tx_loop, daemon=True),
            threading.Thread(target=self._rx_loop, daemon=True),
        ]
        for t in self._threads:
            t.start()

    def stop(self):
        self._stop.set()
        for t in self._threads:
            t.join(timeout=1)
        self.bus.shutdown()

    def _apply_input(self, temp, valid):
        self.coolant_temp = int(round(temp))
        if (not valid) or temp > self.MAX_VALID_TEMP:
            self.sensor_valid = 0
            self.fan_on = 1  # fail-safe (REQ-007)
        else:
            self.sensor_valid = 1
            if temp > self.FAN_ON_ABOVE:
                self.fan_on = 1
            elif temp < self.FAN_OFF_BELOW:
                self.fan_on = 0
            # between 90 and 95 inclusive: keep previous state (REQ-006)

    def _tx_loop(self):
        next_time = time.monotonic()
        while not self._stop.is_set():
            data = self.status.encode({
                "CoolantTemp": self.coolant_temp,
                "FanState": self.fan_on,
                "SensorValid": self.sensor_valid,
                "AliveCounter": self.alive,
            })
            self.bus.send(can.Message(
                arbitration_id=self.status.frame_id,
                data=data, is_extended_id=False))
            self.alive = (self.alive + 1) % 16
            next_time += self.cycle_time
            self._stop.wait(max(0.0, next_time - time.monotonic()))

    def _rx_loop(self):
        while not self._stop.is_set():
            msg = self.bus.recv(timeout=0.05)
            if msg is None or msg.arbitration_id != self.sensor_input.frame_id:
                continue
            try:
                sig = self.sensor_input.decode(msg.data)
            except Exception:  # e.g. wrong length; handled in fault injection step
                continue
            self._apply_input(sig["SimCoolantTemp"], sig["SimSensorValid"])