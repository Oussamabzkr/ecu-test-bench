# ECU Test Bench Requirements

| ID | Requirement | Verification |
|---|---|---|
| REQ-001 | ENGINE_STATUS (0x100) mean cycle time is 100 ms ±5 ms over 100 frames | Timing |
| REQ-002 | No interval between two ENGINE_STATUS frames exceeds 130 ms | Timing |
| REQ-003 | AliveCounter increases by 1 (modulo 16) in every frame | Signal |
| REQ-004 | CoolantTemp equals the SENSOR_INPUT value within 200 ms for a valid sensor from -40 to 150 °C | Boundary |
| REQ-005 | Input above 150 °C or SimSensorValid = 0 sets SensorValid = 0 within 200 ms | Boundary, fault |
| REQ-006 | FanState = 1 above 95 °C, 0 below 90 °C, unchanged from 90 to 95 °C inclusive | Boundary, state |
| REQ-007 | While SensorValid = 0, FanState = 1 (fail-safe) | Fault injection |
| REQ-008 | DTC 0x010100 is stored when SensorValid = 0 lasts more than 200 ms | Fault injection |
| REQ-009 | UDS 0x10 (sub-functions 01 and 03) answers positively within 50 ms | Response time |
| REQ-010 | UDS 0x22 DID 0x0100 returns the raw coolant temperature within 50 ms | Functional |
| REQ-011 | UDS 0x19 02 lists the stored DTCs | Functional |
| REQ-012 | Wrong 0x27 key returns NRC 0x35; unsupported service returns NRC 0x11 | Negative |
