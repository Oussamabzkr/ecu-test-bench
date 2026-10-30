import threading
import time
from pathlib import Path

import can
import cantools

from ecu_sim.uds import (DTC_SENSOR_INVALID, UDS_REQ_ID, UDS_RESP_ID,
                         UdsServer)

DBC_PATH = Path(__file__).resolve().parents[1] / "dbc" / "ecu.dbc"


class SimulatedEcu:
    """Coolant temperature / fan ECU simulated in Python (CAN + UDS)."""

    FAN_ON_ABOVE = 95
    FAN_OFF_BELOW = 90
    MAX_VALID_TEMP = 150
    DTC_DEBOUNCE_S = 0.2
    INPUT_TIMEOUT_S = 0.5

    def __init__(self, channel, interface="virtual", cycle_time=0.1):
        self.db = cantools.database.load_file(str(DBC_PATH))
        self.status = self.db.get_message_by_name("ENGINE_STATUS")
        self.sensor_input = self.db.get_message_by_name("SENSOR_INPUT")
        # two bus handles on the same virtual channel: one for signals, one for UDS
        self.bus = can.Bus(interface=interface, channel=channel)
        self.uds_bus = can.Bus(
            interface=interface, channel=channel,
            can_filters=[{"can_id": UDS_REQ_ID, "can_mask": 0x7FF}])
        self.cycle_time = cycle_time
        # ECU state
        self.coolant_temp = 20
        self.sensor_valid = 1
        self.fan_on = 0
        self.alive = 0
        self.dtcs = {}              # dtc number -> status byte
        self.invalid_since = None
        self.last_input = None      # time of the last valid SENSOR_INPUT
        self.timed_out = False
        self.uds = UdsServer(self)
        # knobs used later for fault injection / defect demos
        self.tx_enabled = True
        self.uds_delay = 0.0
        self._stop = threading.Event()
        self._threads = []

    def start(self):
        self._stop.clear()
        self._threads = [
            threading.Thread(target=self._tx_loop, daemon=True),
            threading.Thread(target=self._rx_loop, daemon=True),
            threading.Thread(target=self._uds_loop, daemon=True),
        ]
        for t in self._threads:
            t.start()

    def stop(self):
        self._stop.set()
        for t in self._threads:
            t.join(timeout=1)
        self.bus.shutdown()
        self.uds_bus.shutdown()

    # ---- application logic -------------------------------------------------
    def _apply_input(self, temp, valid):
        self.coolant_temp = int(round(temp))
        if (not valid) or temp > self.MAX_VALID_TEMP:
            self.sensor_valid = 0
            self.fan_on = 1  # fail-safe (REQ-007)
            if self.invalid_since is None:
                self.invalid_since = time.monotonic()
        else:
            self.sensor_valid = 1
            self.invalid_since = None
            if DTC_SENSOR_INVALID in self.dtcs:
                self.dtcs[DTC_SENSOR_INVALID] = 0x08  # no longer failing, still confirmed
            if temp > self.FAN_ON_ABOVE:
                self.fan_on = 1
            elif temp < self.FAN_OFF_BELOW:
                self.fan_on = 0
            # 90..95 inclusive: keep previous state (REQ-006)

    def check_input_timeout(self):
        """REQ-015: after the first SENSOR_INPUT, silence for 500 ms means invalid sensor."""
        if self.last_input is None or self.timed_out:
            return
        if time.monotonic() - self.last_input > self.INPUT_TIMEOUT_S:
            self.timed_out = True
            self.sensor_valid = 0
            self.fan_on = 1  # fail-safe
            if self.invalid_since is None:
                self.invalid_since = time.monotonic()

    def update_dtc(self):
        """Store the DTC once the sensor has been invalid for more than 200 ms (REQ-008)."""
        since = self.invalid_since
        if since is not None and time.monotonic() - since > self.DTC_DEBOUNCE_S:
            self.dtcs[DTC_SENSOR_INVALID] = 0x09  # testFailed + confirmed

    # ---- threads -----------------------------------------------------------
    def _tx_loop(self):
        next_time = time.monotonic()
        while not self._stop.is_set():
            if self.tx_enabled:
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
            self.check_input_timeout()
            self.update_dtc()
            if msg is None or msg.arbitration_id != self.sensor_input.frame_id:
                continue
            if len(msg.data) != self.sensor_input.length:  # REQ-014: wrong DLC is ignored
                continue
            try:
                sig = self.sensor_input.decode(bytes(msg.data))
            except Exception:
                continue
            self.last_input = time.monotonic()
            self.timed_out = False
            self._apply_input(sig["SimCoolantTemp"], sig["SimSensorValid"])

    def _uds_loop(self):
        while not self._stop.is_set():
            msg = self.uds_bus.recv(timeout=0.05)
            if msg is None:
                continue
            payload = self._single_frame_payload(msg.data)
            if payload is None:
                continue
            response = self.uds.handle(payload)
            if response is None:
                continue
            if self.uds_delay:
                time.sleep(self.uds_delay)
            frame = (bytes([len(response)]) + response).ljust(8, b"\x00")
            self.uds_bus.send(can.Message(
                arbitration_id=UDS_RESP_ID, data=frame, is_extended_id=False))

    @staticmethod
    def _single_frame_payload(data):
        """ISO-TP single frame: first byte = 0x0 (type) + length."""
        if not data or (data[0] >> 4) != 0:
            return None
        length = data[0] & 0x0F
        if length == 0 or length > len(data) - 1:
            return None
        return bytes(data[1:1 + length])
