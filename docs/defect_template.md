# Defect report template (8D style)

Copy this block into `docs/defects.md` for every defect.

## DEF-XXX - short title

| Field | Content |
|---|---|
| Severity / priority | Critical / Major / Minor, High / Medium / Low |
| Requirement | REQ-XXX |
| Failing test | tests/test_xxx.py::test_name |
| Environment | Python and library versions, WSL version, date |
| Steps to reproduce | 1. ... 2. ... 3. ... |
| Expected | value or behavior from the requirement |
| Actual | measured value, log excerpt or assertion message |

**D0 - Symptom and emergency action:** what you saw, and whether a quick action was needed.
**D1 - Team:** who worked on it (you, reviewer).
**D2 - Problem description:** what, where, when, how often (always / sometimes, x out of y runs).
**D3 - Containment:** interim action so testing can continue (for example "test marked xfail until fixed").
**D4 - Root cause:** ask "why" up to five times and say how you proved the cause (experiment, log, code review).
**D5 - Corrective action:** the change chosen to remove the root cause.
**D6 - Verification:** the test that now passes, and the run that shows it (report link or output).
**D7 - Prevention:** regression test added, requirement or design rule updated.
**D8 - Closure:** date, status (fixed in commit abc123, verified by test X).
