// ROV Pico firmware - configuration. Everything you tune on the bench lives here.
#pragma once
#include <stdint.h>

// ---------------- pins (see the electronics page pinout; Pico GPIO is 3.3 V ONLY) ----------------
// UART0 to the Pi Zero: GP0 TX -> Pi RXD (pin 10), GP1 RX <- Pi TXD (pin 8)
constexpr uint8_t PIN_UART_TX = 0;
constexpr uint8_t PIN_UART_RX = 1;
// IBT_2 inputs: {RPWM, LPWM} per thruster, each pair on one PWM slice (channel A = RPWM, B = LPWM)
constexpr uint8_t PIN_RPWM[6] = {2, 4, 6, 8, 10, 12};   // T1..T6
constexpr uint8_t PIN_LPWM[6] = {3, 5, 7, 9, 11, 13};
constexpr uint8_t PIN_LIGHTS = 14;   // both LDD-700HW DIM inputs (10 k pull-down on the board)
constexpr uint8_t PIN_ARM    = 15;   // all 12 R_EN / L_EN (10 k pull-down: bridges off until we drive it high)
constexpr uint8_t PIN_PAN    = 16;   // MG90S pan servo signal
constexpr uint8_t PIN_TILT   = 17;   // MG90S tilt servo signal
constexpr uint8_t PIN_LEAK   = 22;   // optional leak probe to GND (input pull-up); reserved
constexpr uint8_t PIN_VBAT   = 26;   // ADC0 through 33 k / 10 k divider from +12 V (12.6 V -> 2.93 V)

// ---------------- thrusters ----------------
// Prop handedness / wiring polarity: +1 or -1 per thruster. Set on the bench so a + command
// pushes thrust toward the nose cone (build guide section 14 mixing convention). 3 RH + 3 LH props.
constexpr int8_t THRUSTER_DIR[6] = {+1, +1, +1, +1, +1, +1};   // SET ON THE BENCH (flip the LH-prop units)
constexpr float THRUSTER_PWM_HZ = 20000.0f;     // IBT_2 / BTS7960 limit is 25 kHz
constexpr float DEADBAND        = 0.03f;        // |duty| below this -> 0 (stops buzzing)
constexpr float RAMP_S          = 0.15f;        // 0 -> full in 150 ms; a full reversal takes 300 ms

// Current budget. 1200 GPH bilge motors with props: ~4 A rated pumping, expect 8-12 A each at full.
// MEASURE one thruster at 100 % in water with a clamp meter and put the figure in I_FULL_A.
constexpr float I_FULL_A        = 10.0f;        // estimated amps per thruster at |duty| = 1
constexpr float I_BUDGET_A      = 28.0f;        // total thruster budget (F1 30 A, pack fuse 35 A, BMS 40 A)

// ---------------- camera servos (MG90S) ----------------
constexpr float SERVO_HZ        = 50.0f;
constexpr float SERVO_CENTER_US = 1500.0f;
constexpr float SERVO_US_PER_DEG = 1000.0f / 90.0f;  // 500..2500 us = -90..+90 deg
constexpr float PAN_LIMIT_DEG   = 90.0f;
constexpr float TILT_LIMIT_DEG  = 45.0f;
constexpr int8_t PAN_DIR        = +1;           // + = look to port
constexpr int8_t TILT_DIR       = +1;           // + = look up. Pushrod + lever 219, 1:1: CHECK ON THE BENCH
constexpr float SERVO_SLEW_DPS  = 120.0f;       // deg per second

// ---------------- lights ----------------
constexpr float LIGHTS_PWM_HZ   = 500.0f;       // LDD-H DIM input: 100 Hz - 1 kHz
constexpr float LIGHTS_MIN      = 0.10f;        // what "lights to minimum" means on an empty battery

// ---------------- battery (3S) ----------------
constexpr float VBAT_DIVIDER    = (33.0f + 10.0f) / 10.0f;
constexpr float VBAT_CAL        = 1.000f;       // trim against a multimeter
constexpr float VBAT_WARN       = 10.5f;        // 3.5 V/cell: warning
constexpr float VBAT_LOW        = 10.2f;        // 3.4 V/cell: surface now, thrust capped at 50 %
constexpr float VBAT_EMPTY      = 9.6f;         // 3.2 V/cell: thrusters off, lights to minimum
constexpr float VBAT_HYST       = 0.2f;
constexpr float VBAT_FILTER_S   = 1.5f;         // averaging time, so thruster sag does not trip early

// ---------------- link ----------------
constexpr uint32_t UART_BAUD    = 115200;
constexpr uint32_t LINK_TIMEOUT_MS = 500;       // no valid command for this long -> disarm
constexpr uint32_t LOOP_HZ      = 100;
constexpr uint32_t TELEM_HZ     = 10;
constexpr bool LEAK_ENABLED     = false;        // set true once a leak probe is fitted on GP22
