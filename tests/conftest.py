import can
import pytest

from ecu_sim.ecu import SimulatedEcu

CHANNEL = "bench_channel"


@pytest.fixture
def ecu():
    e = SimulatedEcu(channel=CHANNEL)
    e.start()
    yield e
    e.stop()


@pytest.fixture
def bus(ecu):
    b = can.Bus(interface="virtual", channel=CHANNEL)
    yield b
    b.shutdown()