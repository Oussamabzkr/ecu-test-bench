import time

import can

from ecu_sim.uds import UDS_REQ_ID, UDS_RESP_ID


def response_filter():
    return [{"can_id": UDS_RESP_ID, "can_mask": 0x7FF}]


class UdsClient:
    """Minimal UDS client over ISO-TP single frames (enough for our short messages)."""

    def __init__(self, bus, timeout=1.0):
        self.bus = bus
        self.timeout = timeout

    def request(self, payload):
        """Send a request. Returns (response bytes or None, elapsed seconds)."""
        while self.bus.recv(timeout=0) is not None:  # drop stale responses
            pass
        frame = (bytes([len(payload)]) + bytes(payload)).ljust(8, b"\x00")
        t0 = time.monotonic()
        self.bus.send(can.Message(arbitration_id=UDS_REQ_ID,
                                  data=frame, is_extended_id=False))
        msg = self.bus.recv(timeout=self.timeout)
        elapsed = time.monotonic() - t0
        if msg is None:
            return None, elapsed
        length = msg.data[0] & 0x0F
        return bytes(msg.data[1:1 + length]), elapsed
