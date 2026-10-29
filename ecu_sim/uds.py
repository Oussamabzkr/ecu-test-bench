import random

UDS_REQ_ID = 0x7E0
UDS_RESP_ID = 0x7E8

SESSION_DEFAULT = 0x01
SESSION_EXTENDED = 0x03

DTC_SENSOR_INVALID = 0x010100
DID_COOLANT_TEMP = 0x0100

NRC_SERVICE_NOT_SUPPORTED = 0x11
NRC_SUBFUNCTION_NOT_SUPPORTED = 0x12
NRC_INCORRECT_LENGTH = 0x13
NRC_REQUEST_SEQUENCE_ERROR = 0x24
NRC_REQUEST_OUT_OF_RANGE = 0x31
NRC_INVALID_KEY = 0x35
NRC_SERVICE_NOT_IN_SESSION = 0x7F


def nrc(sid, code):
    return bytes([0x7F, sid, code])


class UdsServer:
    """UDS services: 0x10, 0x19, 0x22, 0x27. Pure logic: bytes in, bytes out."""

    def __init__(self, ecu, rng=None):
        self.ecu = ecu  # needs .coolant_temp, .dtcs (dict) and .update_dtc()
        self.rng = rng or random.Random()
        self.session = SESSION_DEFAULT
        self.unlocked = False
        self._seed = None

    @staticmethod
    def key_from_seed(seed):
        return (seed ^ 0xA5A5) & 0xFFFF

    def handle(self, req):
        if not req:
            return None
        handlers = {
            0x10: self._session_control,
            0x19: self._read_dtc,
            0x22: self._read_did,
            0x27: self._security_access,
        }
        handler = handlers.get(req[0])
        if handler is None:
            return nrc(req[0], NRC_SERVICE_NOT_SUPPORTED)
        return handler(req)

    def _session_control(self, req):
        if len(req) != 2:
            return nrc(0x10, NRC_INCORRECT_LENGTH)
        sub = req[1]
        if sub not in (SESSION_DEFAULT, SESSION_EXTENDED):
            return nrc(0x10, NRC_SUBFUNCTION_NOT_SUPPORTED)
        self.session = sub
        if sub == SESSION_DEFAULT:  # leaving extended session locks the ECU again
            self.unlocked = False
            self._seed = None
        # P2 = 50 ms (0x0032), P2* = 5000 ms (0x01F4 x 10 ms)
        return bytes([0x50, sub, 0x00, 0x32, 0x01, 0xF4])

    def _read_did(self, req):
        if len(req) != 3:
            return nrc(0x22, NRC_INCORRECT_LENGTH)
        did = (req[1] << 8) | req[2]
        if did == DID_COOLANT_TEMP:
            raw = max(0, min(255, int(self.ecu.coolant_temp) + 40))
            return bytes([0x62, req[1], req[2], raw])
        return nrc(0x22, NRC_REQUEST_OUT_OF_RANGE)

    def _read_dtc(self, req):
        if len(req) != 3:
            return nrc(0x19, NRC_INCORRECT_LENGTH)
        if req[1] != 0x02:  # reportDTCByStatusMask only
            return nrc(0x19, NRC_SUBFUNCTION_NOT_SUPPORTED)
        self.ecu.update_dtc()
        mask = req[2]
        out = bytearray([0x59, 0x02, 0xFF])
        for dtc, status in self.ecu.dtcs.items():
            if status & mask:
                out += bytes([(dtc >> 16) & 0xFF, (dtc >> 8) & 0xFF, dtc & 0xFF, status])
        return bytes(out)  # single frame: at most 1 DTC fits (7 bytes)

    def _security_access(self, req):
        if len(req) < 2:
            return nrc(0x27, NRC_INCORRECT_LENGTH)
        if self.session != SESSION_EXTENDED:
            return nrc(0x27, NRC_SERVICE_NOT_IN_SESSION)
        sub = req[1]
        if sub == 0x01:  # request seed
            if len(req) != 2:
                return nrc(0x27, NRC_INCORRECT_LENGTH)
            if self.unlocked:
                return bytes([0x67, 0x01, 0x00, 0x00])
            self._seed = self.rng.randint(1, 0xFFFF)
            return bytes([0x67, 0x01, self._seed >> 8, self._seed & 0xFF])
        if sub == 0x02:  # send key
            if len(req) != 4:
                return nrc(0x27, NRC_INCORRECT_LENGTH)
            if self._seed is None:
                return nrc(0x27, NRC_REQUEST_SEQUENCE_ERROR)
            key = (req[2] << 8) | req[3]
            expected = self.key_from_seed(self._seed)
            self._seed = None
            if key != expected:
                return nrc(0x27, NRC_INVALID_KEY)
            self.unlocked = True
            return bytes([0x67, 0x02])
        return nrc(0x27, NRC_SUBFUNCTION_NOT_SUPPORTED)
