# TinkerSub KB-1 firmware

| folder | runs on | what it does |
|---|---|---|
| `pico_rov/` | Raspberry Pi Pico | Mixes the commands into six thrusters and applies the safety limits. Drives the IBT_2 boards, the lights and the pan/tilt servos, and reads the battery voltage. |
| `pi_bridge/` | Pi Zero 2 W | Relays packets between UDP on the tether and the Pico's UART, with a second failsafe. Also holds the MediaMTX camera stream config and the setup notes. |
| `topside/` | laptop | Reads the game controller, sends commands at 50 Hz and shows telemetry on screen. |
| `test/` | your PC | Host unit tests for the Pico logic, plus a bridge integration test. |
| `build/pico_rov.ino.uf2` | | Ready-to-flash Pico image, built with the defaults in `config.h`. |

The protocol is described in `PROTOCOL.md`.

> **The Pico's GPIO is 3.3 V only.** The IBT_2 VCC pins take the Pico's 3V3, not 5 V, so their inputs never see more than 3.3 V. The battery is read through the 33 k / 10 k divider. Keep the 12 V wiring physically separate from the 3.3 V / 5 V logic, with one shared ground at the Wago block.

## Flashing the Pico
- **Pre-built image:** hold BOOTSEL, plug in USB, and drag `build/pico_rov.ino.uf2` onto the RPI-RP2 drive.
- **From source:** use the Arduino IDE with the "Raspberry Pi Pico/RP2040" core by Earle Philhower. Board: Raspberry Pi Pico. Open `pico_rov/pico_rov.ino` and upload.
- **Command line:**
  `arduino-cli compile -b rp2040:rp2040:rpipico pico_rov --output-dir build`

Over USB, the Pico prints a telemetry line 10 times a second. Use any serial monitor at 115200.

## Bench procedure (props OFF, bench supply limited to about 3 A, or the pack through F1)
Change `config.h`, rebuild and reflash after each step that needs it.

1. **Power-up check.** No Pi connected. Telemetry should show `armed 0` and flags `65` (link lost + boot). Measure ARM at the IBT_2 headers: it should read 0 V.
2. **Battery calibration.** Compare `vbat_mV` with a multimeter at the Wago block. Set `VBAT_CAL = meter / reported`. It should come out between 0.97 and 1.03.
3. **Link.** Connect the Pi and start the bridge. Run `python3 topside/rov_topside.py`. The HUD should show `link OK`. Then pull the tether: the HUD shows NO TELEMETRY and the Pico shows flags `1` within 0.5 s.
4. **Thruster direction (props off, gain 25 %).** Arm, then push surge forward gently. Each horizontal thruster should spin the way that pushes water aft, matching the mixing table in section 14 of the build guide. Push heave up: both verticals should push water down. Flip `THRUSTER_DIR[i]` for any that spin the wrong way. Set direction in software only; don't swap motor wires afterwards, or the table and the code will disagree.
5. **Tilt direction.** On the d-pad, press up: the camera must look up. Through the pushrod and lever 219 this can come out reversed. If it does, set `TILT_DIR = -1`. Check that pan right looks to starboard, and use `PAN_DIR` if not. At ±45° tilt and ±90° pan, check that nothing binds and that the ribbon has slack through the window in 216.
6. **Measure `I_FULL_A`.** Mount one thruster with its prop in a bucket of water. Clamp meter on one motor lead, gain 100 %, full surge for 2–3 s. Enter the reading as `I_FULL_A`; 8–12 A is expected for a 1200 GPH motor. The current budget (`I_BUDGET_A = 28`) then keeps the six together under F1 (30 A).
7. **Failsafes in water.** Arm, give gentle surge, then close the topside app. The thrusters must stop within 0.5 s. Also run the battery cutoff test: on a bench supply, turn it down past 10.5 V (warn), then 10.2 V (low: 50 % thrust cap), then 9.6 V (disarmed, lights at 10 %).

## Tests
```
cd test && g++ -std=c++17 -I../pico_rov test_core.cpp -o t && ./t     # Pico logic
python3 test/integration.py                                           # bridge + protocol (needs pyserial)
```
