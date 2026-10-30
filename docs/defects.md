# Defect log

| ID | Title | Requirement | Severity | Status |
|---|---|---|---|---|
| DEF-001 | UDS response too slow (injected defect, worked example below) | REQ-009 | Major | Closed |
| DEF-002 | _your next defect_ | | | |

Use `docs/defect_template.md` for each entry. Only write numbers you measured.

---

## DEF-001 - UDS 0x10 response time above 50 ms (worked example, injected defect)

| Field | Content |
|---|---|
| Severity / priority | Major / High |
| Requirement | REQ-009 |
| Failing test | tests/test_uds.py::test_session_control_positive |
| Environment | _fill in: Python, WSL version, date_ |
| Steps to reproduce | 1. In `ecu_sim/ecu.py` set `self.uds_delay = 0.08`. 2. Run `pytest tests/test_uds.py -k session_control`. |
| Expected | Positive response 0x50 within 50 ms |
| Actual | _fill in: your measured response time_ ms |

**D2 - Problem description:** the ECU answers 0x10 correctly but too late; the failure is reproducible on every run.
**D3 - Containment:** none needed, the defect was injected on purpose to check that the bench can detect it.
**D4 - Root cause:** a fixed 80 ms sleep before sending the response in the UDS thread. Proof: removing the delay makes the test pass.
**D5 - Corrective action:** remove the delay; keep `test_bench_detects_slow_uds_response` as a permanent self-check.
**D6 - Verification:** `pytest tests/test_uds.py` passes with `uds_delay = 0`.
**D7 - Prevention:** response-time assertion stays in every UDS test; the self-check proves the bench would catch the regression.
**D8 - Closure:** _date and commit hash_.
