import pytest

from bench.helpers import apply_and_read, collect_status


@pytest.mark.signals
@pytest.mark.req("REQ-004")
@pytest.mark.req("REQ-005")
@pytest.mark.parametrize("temp, expected_valid", [
    (-40, 1),   # lower limit
    (0, 1),     # nominal
    (150, 1),   # upper limit
    (151, 0),   # just above the limit
])
def test_temperature_boundaries(bus, temp, expected_valid):
    sig = apply_and_read(bus, temp)
    assert sig["SensorValid"] == expected_valid
    assert sig["CoolantTemp"] == temp


@pytest.mark.signals
@pytest.mark.req("REQ-006")
def test_fan_hysteresis_sequence(bus):
    # (input temperature, expected FanState): state-transition test
    steps = [(20, 0), (90, 0), (95, 0), (96, 1),
             (95, 1), (90, 1), (89, 0), (95, 0)]
    for temp, expected_fan in steps:
        sig = apply_and_read(bus, temp)
        assert sig["FanState"] == expected_fan, f"at {temp} degC"


@pytest.mark.fault
@pytest.mark.req("REQ-005")
@pytest.mark.req("REQ-007")
@pytest.mark.parametrize("temp, valid", [
    (60, 0),    # sensor reports invalid
    (151, 1),   # value out of range
])
def test_invalid_sensor_sets_flag_and_fan_failsafe(bus, temp, valid):
    sig = apply_and_read(bus, temp, valid)
    assert sig["SensorValid"] == 0
    assert sig["FanState"] == 1


@pytest.mark.signals
@pytest.mark.req("REQ-003")
def test_alive_counter_increments(bus):
    frames = collect_status(bus, 40)
    assert len(frames) == 40
    counters = [f[1]["AliveCounter"] for f in frames]
    for previous, current in zip(counters, counters[1:]):
        assert (current - previous) % 16 == 1


@pytest.mark.timing
@pytest.mark.req("REQ-001")
@pytest.mark.req("REQ-002")
def test_cycle_time(bus):
    frames = collect_status(bus, 100)
    assert len(frames) == 100
    times = [f[0] for f in frames]
    intervals = [b - a for a, b in zip(times, times[1:])]
    mean = sum(intervals) / len(intervals)
    assert abs(mean - 0.100) <= 0.005, f"mean cycle time {mean * 1000:.1f} ms"
    assert max(intervals) <= 0.130, f"max interval {max(intervals) * 1000:.1f} ms"
