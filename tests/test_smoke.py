import time

import pytest

from bench.helpers import recv_status, send_sensor


@pytest.mark.signals
def test_ecu_sends_engine_status(bus):
    frame = recv_status(bus, timeout=1.0)
    assert frame is not None, "no ENGINE_STATUS received"
    _, sig = frame
    assert sig["CoolantTemp"] == 20
    assert sig["FanState"] == 0
    assert sig["SensorValid"] == 1


@pytest.mark.signals
def test_fan_turns_on_above_95(bus):
    send_sensor(bus, 100)
    deadline = time.monotonic() + 0.5
    fan = 0
    while time.monotonic() < deadline and fan == 0:
        frame = recv_status(bus, timeout=0.2)
        if frame:
            fan = frame[1]["FanState"]
    assert fan == 1