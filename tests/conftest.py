from pathlib import Path

import can
import pytest

from bench.uds_client import UdsClient, response_filter
from ecu_sim.ecu import SimulatedEcu

CHANNEL = "bench_channel"
TRACE = []  # (requirement, test id, outcome)


@pytest.fixture
def channel():
    return CHANNEL


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


@pytest.fixture
def uds(ecu):
    b = can.Bus(interface="virtual", channel=CHANNEL, can_filters=response_filter())
    yield UdsClient(b)
    b.shutdown()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        for marker in item.iter_markers("req"):
            TRACE.append((marker.args[0], item.nodeid, report.outcome))


def pytest_sessionfinish(session, exitstatus):
    if not TRACE:
        return
    lines = ["| Requirement | Test | Result |", "|---|---|---|"]
    lines += [f"| {r} | {n} | {o} |" for r, n, o in sorted(TRACE)]
    out = Path(session.config.rootpath) / "reports"
    out.mkdir(exist_ok=True)
    (out / "traceability.md").write_text("\n".join(lines) + "\n")
