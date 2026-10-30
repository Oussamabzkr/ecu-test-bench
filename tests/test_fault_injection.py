import time

import can
import pytest

from bench.fault_tools import Flooder
from bench.helpers import (INPUT, collect_status, drain, read_after,
                           recv_status, send_sensor)


@pytest.mark.fault
@pytest.mark.req("REQ-014")
@pytest.mark.parametrize("data", [
    bytes([200]),                              # DLC 1: too short
    bytes([140, 1, 0, 0, 0, 0, 0, 0]),         # DLC 8: too long (would mean 100 degC)
], ids=["dlc1", "dlc8"])
def test_wrong_dlc_is_ignored(bus, data):
    drain(bus)
    t_send = time.monotonic()
    bus.send(can.Message(arbitration_id=INPUT.frame_id, data=data, is_extended_id=False))
    frame = read_after(bus, t_send + 0.05)
    assert frame is not None, "ECU stopped transmitting"
    sig = frame[1]
    assert sig["CoolantTemp"] == 20   # unchanged initial value
    assert sig["SensorValid"] == 1
    assert sig["FanState"] == 0


@pytest.mark.fault
@pytest.mark.req("REQ-015")
def test_sensor_input_timeout_and_recovery(bus):
    send_sensor(bus, 60)
    time.sleep(0.2)
    # input is alive: sensor valid
    drain(bus)
    frame = read_after(bus, time.monotonic())
    assert frame[1]["SensorValid"] == 1

    # frame loss on SENSOR_INPUT: stop sending for 0.8 s (> 500 ms timeout)
    time.sleep(0.8)
    drain(bus)
    frame = read_after(bus, time.monotonic())
    assert frame[1]["SensorValid"] == 0
    assert frame[1]["FanState"] == 1   # fail-safe

    # recovery: input is back
    drain(bus)
    t_send = time.monotonic()
    send_sensor(bus, 60)
    frame = read_after(bus, t_send + 0.05)
    assert frame[1]["SensorValid"] == 1
    assert frame[1]["FanState"] == 0


@pytest.mark.fault
@pytest.mark.timing
@pytest.mark.req("REQ-016")
def test_ecu_under_bus_load(bus, uds, channel):
    flooder = Flooder(channel)
    flooder.start()
    try:
        time.sleep(0.3)
        drain(bus)
        resp, elapsed = uds.request(b"\x10\x01")
        frames = collect_status(bus, 30)
    finally:
        flooder.stop()
    assert flooder.rate >= 200, f"load generator too slow: {flooder.rate:.0f} frames/s"
    assert len(frames) == 30, "ENGINE_STATUS frames missing under load"
    times = [f[0] for f in frames]
    worst = max(b - a for a, b in zip(times, times[1:]))
    assert worst <= 0.130, f"max interval {worst * 1000:.1f} ms under load"
    assert resp is not None and resp[0] == 0x50
    assert elapsed < 0.050, f"UDS response time {elapsed * 1000:.1f} ms under load"


@pytest.mark.uds
@pytest.mark.fault
@pytest.mark.req("REQ-017")
@pytest.mark.parametrize("frame", [
    bytes([0x0F, 0x10, 0x01, 0, 0, 0, 0, 0]),   # single frame with impossible length
    bytes([0x00, 0x10, 0x01, 0, 0, 0, 0, 0]),   # single frame with length 0
    bytes([0x30, 0x00, 0x00, 0, 0, 0, 0, 0]),   # flow-control frame, not a request
], ids=["length15", "length0", "flowcontrol"])
def test_malformed_isotp_frame_is_ignored(uds, frame):
    resp, _ = uds.request_raw(frame, timeout=0.3)
    assert resp is None                          # no answer to garbage
    resp, _ = uds.request(b"\x10\x01")           # and the ECU still works
    assert resp is not None and resp[0] == 0x50


@pytest.mark.selfcheck
def test_bench_detects_slow_uds_response(ecu, uds):
    ecu.uds_delay = 0.08                         # injected defect
    resp, elapsed = uds.request(b"\x10\x01")
    assert resp is not None
    assert elapsed > 0.050, "bench did not notice a slow ECU"


@pytest.mark.selfcheck
def test_bench_detects_missing_status_frames(ecu, bus):
    ecu.tx_enabled = False                       # injected defect: ECU goes silent
    time.sleep(0.15)                             # let a frame already in flight arrive
    drain(bus)
    assert recv_status(bus, timeout=0.5) is None, "bench did not notice missing frames"
