import threading
import time

import can


class Flooder:
    """Software load generator: sends unrelated CAN frames at a fixed target rate."""

    def __init__(self, channel, arbitration_id=0x555, period=0.002, interface="virtual"):
        self.bus = can.Bus(interface=interface, channel=channel)
        self.arbitration_id = arbitration_id
        self.period = period
        self.sent = 0
        self._t_start = None
        self._t_stop = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._t_start = time.monotonic()
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1)
        self._t_stop = time.monotonic()
        self.bus.shutdown()

    @property
    def rate(self):
        """Average frames per second actually sent."""
        return self.sent / (self._t_stop - self._t_start)

    def _run(self):
        msg = can.Message(arbitration_id=self.arbitration_id,
                          data=bytes(8), is_extended_id=False)
        while not self._stop.is_set():
            self.bus.send(msg)
            self.sent += 1
            self._stop.wait(self.period)
