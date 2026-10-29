import time

import pytest

from bench.helpers import send_sensor
from ecu_sim.uds import UdsServer


def enter_extended(uds):
    resp, _ = uds.request(b"\x10\x03")
    assert resp is not None and resp[0] == 0x50


@pytest.mark.uds
@pytest.mark.req("REQ-009")
@pytest.mark.parametrize("sub", [0x01, 0x03])
def test_session_control_positive(uds, sub):
    resp, elapsed = uds.request(bytes([0x10, sub]))
    assert resp is not None, "no response"
    assert resp[:2] == bytes([0x50, sub])
    assert elapsed < 0.050, f"response time {elapsed * 1000:.1f} ms"


@pytest.mark.uds
@pytest.mark.req("REQ-010")
def test_read_coolant_temperature(bus, uds):
    send_sensor(bus, 80)
    time.sleep(0.15)
    resp, elapsed = uds.request(b"\x22\x01\x00")
    assert resp == bytes([0x62, 0x01, 0x00, 80 + 40])  # raw = temp + 40
    assert elapsed < 0.050


@pytest.mark.uds
@pytest.mark.fault
@pytest.mark.req("REQ-008")
@pytest.mark.req("REQ-011")
def test_dtc_not_stored_before_debounce(bus, uds):
    send_sensor(bus, 60, valid=0)
    time.sleep(0.1)  # shorter than the 200 ms debounce time
    resp, _ = uds.request(b"\x19\x02\xFF")
    assert resp == bytes([0x59, 0x02, 0xFF])  # no DTC yet


@pytest.mark.uds
@pytest.mark.fault
@pytest.mark.req("REQ-008")
@pytest.mark.req("REQ-011")
def test_dtc_stored_after_debounce(bus, uds):
    send_sensor(bus, 60, valid=0)
    time.sleep(0.5)
    resp, _ = uds.request(b"\x19\x02\xFF")
    assert resp == bytes([0x59, 0x02, 0xFF, 0x01, 0x01, 0x00, 0x09])


@pytest.mark.uds
@pytest.mark.req("REQ-013")
def test_security_access_locked_in_default_session(uds):
    resp, _ = uds.request(b"\x27\x01")
    assert resp == bytes([0x7F, 0x27, 0x7F])


@pytest.mark.uds
@pytest.mark.req("REQ-013")
def test_security_access_correct_key(uds):
    enter_extended(uds)
    seed_resp, _ = uds.request(b"\x27\x01")
    assert seed_resp[:2] == bytes([0x67, 0x01]) and len(seed_resp) == 4
    seed = (seed_resp[2] << 8) | seed_resp[3]
    key = UdsServer.key_from_seed(seed)
    resp, _ = uds.request(bytes([0x27, 0x02, key >> 8, key & 0xFF]))
    assert resp == bytes([0x67, 0x02])


@pytest.mark.uds
@pytest.mark.req("REQ-012")
def test_security_access_wrong_key(uds):
    enter_extended(uds)
    seed_resp, _ = uds.request(b"\x27\x01")
    seed = (seed_resp[2] << 8) | seed_resp[3]
    wrong = (UdsServer.key_from_seed(seed) + 1) & 0xFFFF
    resp, _ = uds.request(bytes([0x27, 0x02, wrong >> 8, wrong & 0xFF]))
    assert resp == bytes([0x7F, 0x27, 0x35])


@pytest.mark.uds
@pytest.mark.req("REQ-013")
def test_send_key_without_seed(uds):
    enter_extended(uds)
    resp, _ = uds.request(b"\x27\x02\x12\x34")
    assert resp == bytes([0x7F, 0x27, 0x24])


@pytest.mark.uds
@pytest.mark.req("REQ-012")
@pytest.mark.parametrize("request_bytes, sid, nrc", [
    (b"\x31\x01", 0x31, 0x11),          # unsupported service
    (b"\x22\x01", 0x22, 0x13),          # incorrect length
    (b"\x22\x09\x99", 0x22, 0x31),      # unknown data identifier
    (b"\x10\x05", 0x10, 0x12),          # unsupported session
])
def test_negative_responses(uds, request_bytes, sid, nrc):
    resp, _ = uds.request(request_bytes)
    assert resp == bytes([0x7F, sid, nrc])
