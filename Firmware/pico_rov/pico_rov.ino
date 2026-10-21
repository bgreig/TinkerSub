// ROV Stage 1 firmware for the Raspberry Pi Pico (RP2040), Arduino-Pico core (Earle Philhower).
// Board: "Raspberry Pi Pico". Library: none beyond the core.
//
// The Pico's GPIO is 3.3 V ONLY. Nothing here ever touches 12 V: the IBT_2 logic runs from the
// Pico's 3V3 pin, the battery is read through a 33 k / 10 k divider, and the LDD DIM inputs are 3.3 V PWM.
//
// What it does, 100 times a second:
//   read commands from the Pi on UART0 -> mix 4 axes into 6 thrusters -> battery and current limits
//   -> ramp -> PWM to six IBT_2 boards; drive the light dimmer and the two camera servos.
// Safety: ARM (GP15) is low at boot, on any link loss over 500 ms, when the battery is empty, or on a leak.
// The hardware watchdog resets the Pico if the loop ever stalls; the ARM pull-down keeps the bridges off.

#include <Arduino.h>
#include "hardware/pwm.h"
#include "hardware/clocks.h"
#include "config.h"
#include "rov_core.h"

using namespace rov;

static Controller ctl;
static uint32_t thr_wrap, light_wrap, servo_wrap;
static float servo_ticks_per_us;
static float vbat_f = 12.0f;
static bool vbat_init = false;
static uint16_t telem_seq = 0;

// ---------- PWM helpers (per slice, so thrusters, lights and servos can each have their own frequency)
static uint32_t setup_slice(uint8_t pin_a, int pin_b, float hz, float* ticks_per_us = nullptr) {
    uint slice = pwm_gpio_to_slice_num(pin_a);
    float sys = (float)clock_get_hz(clk_sys);
    float div = 1.0f;
    while (sys / div / hz > 65535.0f) div *= 2.0f;          // keep wrap in 16 bits
    uint32_t wrap = (uint32_t)(sys / div / hz) - 1;
    gpio_set_function(pin_a, GPIO_FUNC_PWM);
    if (pin_b >= 0) gpio_set_function((uint)pin_b, GPIO_FUNC_PWM);
    pwm_set_clkdiv(slice, div);
    pwm_set_wrap(slice, wrap);
    pwm_set_chan_level(slice, PWM_CHAN_A, 0);
    pwm_set_chan_level(slice, PWM_CHAN_B, 0);
    pwm_set_enabled(slice, true);
    if (ticks_per_us) *ticks_per_us = sys / div / 1e6f;
    return wrap;
}

static void set_level(uint8_t pin, uint32_t level) { pwm_set_gpio_level(pin, (uint16_t)level); }

static void write_thruster(int i, float duty) {
    duty *= THRUSTER_DIR[i];
    uint32_t lvl = (uint32_t)(fabsf(duty) * (thr_wrap + 1));
    if (lvl > thr_wrap + 1) lvl = thr_wrap + 1;
    if (duty > 0) { set_level(PIN_LPWM[i], 0); set_level(PIN_RPWM[i], lvl); }       // never both at once
    else if (duty < 0) { set_level(PIN_RPWM[i], 0); set_level(PIN_LPWM[i], lvl); }
    else { set_level(PIN_RPWM[i], 0); set_level(PIN_LPWM[i], 0); }
}

static void write_servo(uint8_t pin, float us) {
    us = clampf(us, 500.0f, 2500.0f);
    set_level(pin, (uint32_t)(us * servo_ticks_per_us));
}

static float read_vbat() {
    uint32_t sum = 0;
    for (int i = 0; i < 8; i++) sum += analogRead(PIN_VBAT);
    float v_adc = (sum / 8.0f) * 3.3f / 4095.0f;
    return v_adc * VBAT_DIVIDER * VBAT_CAL;
}

// ---------- serial line reader
static char rxbuf[160];
static size_t rxlen = 0;

static void poll_uart(uint32_t now) {
    while (Serial1.available()) {
        char ch = (char)Serial1.read();
        if (ch == '\r') continue;
        if (ch == '\n') {
            rxbuf[rxlen] = 0;
            Command c;
            if (parse_command(rxbuf, c)) ctl.on_command(c, now);
            rxlen = 0;
        } else if (rxlen < sizeof(rxbuf) - 1) {
            rxbuf[rxlen++] = ch;
        } else {
            rxlen = 0;   // overlong line: drop it
        }
    }
}

void setup() {
    // ARM low first: the bridges stay disabled until we have a valid, armed command
    pinMode(PIN_ARM, OUTPUT);
    digitalWrite(PIN_ARM, LOW);

    for (int i = 0; i < NT; i++) thr_wrap = setup_slice(PIN_RPWM[i], PIN_LPWM[i], THRUSTER_PWM_HZ);
    light_wrap = setup_slice(PIN_LIGHTS, -1, LIGHTS_PWM_HZ);          // slice 7 A; GP15 stays plain GPIO
    servo_wrap = setup_slice(PIN_PAN, PIN_TILT, SERVO_HZ, &servo_ticks_per_us);  // slice 0 (GP0/1 are UART)
    write_servo(PIN_PAN, servo_us(0, PAN_DIR));
    write_servo(PIN_TILT, servo_us(0, TILT_DIR));

    analogReadResolution(12);
    if (LEAK_ENABLED) pinMode(PIN_LEAK, INPUT_PULLUP);

    Serial1.setTX(PIN_UART_TX);
    Serial1.setRX(PIN_UART_RX);
    Serial1.begin(UART_BAUD);
    Serial.begin(115200);                 // USB: debug only

    rp2040.wdt_begin(300);
}

void loop() {
    static uint32_t last_us = micros();
    static uint32_t next_telem = 0;
    const uint32_t period_us = 1000000UL / LOOP_HZ;

    uint32_t now_us = micros();
    if ((uint32_t)(now_us - last_us) < period_us) { poll_uart(millis()); return; }
    float dt = (now_us - last_us) / 1e6f;
    last_us = now_us;
    uint32_t now = millis();

    rp2040.wdt_reset();
    poll_uart(now);

    // battery: first-order filter so thruster sag does not trip the thresholds
    float v = read_vbat();
    if (!vbat_init) { vbat_f = v; vbat_init = true; }
    vbat_f += (v - vbat_f) * fminf(1.0f, dt / VBAT_FILTER_S);

    ctl.leak = LEAK_ENABLED && digitalRead(PIN_LEAK) == LOW;
    ctl.step(now, dt, vbat_f);

    // outputs: disarm cuts ARM before anything else
    if (!ctl.out.armed) digitalWrite(PIN_ARM, LOW);
    for (int i = 0; i < NT; i++) write_thruster(i, ctl.out.duty[i]);
    if (ctl.out.armed) digitalWrite(PIN_ARM, HIGH);

    set_level(PIN_LIGHTS, (uint32_t)(ctl.out.lights * (light_wrap + 1)));
    write_servo(PIN_PAN, servo_us(ctl.out.pan, PAN_DIR));
    write_servo(PIN_TILT, servo_us(ctl.out.tilt, TILT_DIR));

    if ((int32_t)(now - next_telem) >= 0) {
        next_telem = now + 1000 / TELEM_HZ;
        char buf[160];
        int n = format_telemetry(buf, sizeof(buf), telem_seq++, now, ctl.out.armed, ctl.out.flags, vbat_f,
                                 ctl.out.duty, ctl.out.i_est, ctl.out.pan, ctl.out.tilt);
        Serial1.write((const uint8_t*)buf, n);
        if (Serial) Serial.write((const uint8_t*)buf, n);
    }
}
