# Requirements - Coolant temperature and fan ECU

| ID | Requirement | Verification |
|---|---|---|
| REQ-001 | ENGINE_STATUS (0x100) mean cycle time is 100 ms +/-5 ms over 100 frames | Timing |
| REQ-002 | No interval between two ENGINE_STATUS frames exceeds 130 ms | Timing |
| REQ-003 | AliveCounter increases by 1 (modulo 16) in every frame | Signal |
| REQ-004 | CoolantTemp equals the SENSOR_INPUT value within 200 ms for a valid sensor from -40 to 150 degC | Boundary |
| REQ-005 | Input above 150 degC or SimSensorValid = 0 sets SensorValid = 0 within 200 ms | Boundary, fault |
| REQ-006 | FanState = 1 above 95 degC, 0 below 90 degC, unchanged from 90 to 95 degC inclusive | Boundary, state |
| REQ-007 | While SensorValid = 0, FanState = 1 (fail-safe) | Fault injection |
| REQ-008 | DTC 0x010100 is stored when SensorValid = 0 lasts more than 200 ms | Fault injection (UDS) |
| REQ-009 | UDS 0x10 (sub-functions 01 and 03) answers positively within 50 ms | Response time |
| REQ-010 | UDS 0x22 DID 0x0100 returns the raw coolant temperature (temp + 40) within 50 ms | Functional |
| REQ-011 | UDS 0x19 02 lists the stored DTCs (3 bytes DTC + 1 byte status) | Functional |
| REQ-012 | UDS negative responses: unsupported service 0x11, wrong length 0x13, unknown DID 0x31, unsupported sub-function 0x12, wrong key 0x35 | Negative |
| REQ-013 | UDS 0x27 only in extended session (else NRC 0x7F); correct key returns 67 02; key without seed returns NRC 0x24 | Negative, state |
| REQ-014 | SENSOR_INPUT frames with a DLC other than 2 shall be ignored; ECU state and transmission are unchanged | Fault injection |
| REQ-015 | After the first SENSOR_INPUT, if none is received for 500 ms the ECU sets SensorValid = 0 and FanState = 1; it recovers when input returns | Fault injection (frame loss) |
| REQ-016 | With at least 200 unrelated frames/s on the bus, ENGINE_STATUS max interval stays at or below 130 ms and UDS 0x10 answers within 50 ms | Robustness, timing |
| REQ-017 | Malformed ISO-TP frames (invalid length, flow-control frame) shall get no UDS response, and the ECU keeps working | Negative, fault |
