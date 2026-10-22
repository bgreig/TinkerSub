# TinkerSub KB-1 link protocol

ASCII lines in the NMEA style: `$<body>*HH\n`. `HH` is the XOR of every byte between `$` and `*`, written as two hex digits. Any line that fails the checksum, or has the wrong number of fields, is dropped.

Path: topside → UDP 5005 → Pi bridge → UART 115200 8N1 → Pico, and back the other way with telemetry on UDP 5006.

## Command: topside → Pico, 50 Hz
`$C,seq,arm,surge,sway,heave,yaw,gain,lights,pan,tilt*HH`

| field | units | range |
|---|---|---|
| seq | counter, wraps at 65535 | |
| arm | 0 / 1 | |
| surge, sway, heave, yaw | ‰ (thousandths) | −1000 … 1000 (+surge = forward, +heave = up) |
| gain | ‰ | 0 … 1000 |
| lights | ‰ | 0 … 1000 |
| pan, tilt | 0.1° | pan ±900, tilt ±450 (the Pico clamps) |

Example: `$C,7,1,500,-250,1000,0,800,300,450,-200*HH`

## Telemetry: Pico → topside, 10 Hz
`$T,seq,ms,armed,flags,vbat_mV,d1,d2,d3,d4,d5,d6,i_dA,pan,tilt*HH`

- `d1..d6` are the thruster duties in ‰ after mixing, limits and ramp.
- `i_dA` is the estimated total thruster current in units of 0.1 A.
- `pan` and `tilt` are the servo positions now (after slew), in 0.1°.

Flags (bit values):
| 1 | 2 | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|
| link lost | batt warn (10.5 V) | batt low (10.2 V, thrust capped at 50 %) | batt empty (9.6 V, disarmed) | leak | current limit active | boot (no command yet) |

## Failsafes, in layers
1. **Topside:** arming only works with the sticks centred, and the arm request is dropped if no telemetry arrives for 1 s.
2. **Pi bridge:** if no valid command arrives for 0.4 s, it sends 3 disarm lines and then stops forwarding.
3. **Pico:** if no valid command arrives for 500 ms, it disarms. ARM (GP15) goes low, all PWM goes to 0, the lights switch off and the camera centres. (A flat battery dims the lights to 10 % but keeps them on.)
4. **Pico hardware watchdog (300 ms):** resets the Pico if the loop stalls. The 10 k pull-down on ARM keeps the bridges off while it restarts.
