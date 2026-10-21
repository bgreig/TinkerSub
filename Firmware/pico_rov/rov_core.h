// ROV core logic: mixer, current budget, ramping, battery state, protocol.
// Pure C++ with no Arduino calls, so the same code compiles on the Pico and in the host unit tests.
#pragma once
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "config.h"

namespace rov {

constexpr int NT = 6;

// Mixing table (mechanical handoff): columns surge, sway, heave, yaw. T1 FP, T2 FS, T3 RP, T4 RS, T5 VP, T6 VS.
constexpr float MIX[NT][4] = {
    {-0.71f, -0.71f, 0.0f, +1.0f},
    {-0.71f, +0.71f, 0.0f, -1.0f},
    {+0.71f, -0.71f, 0.0f, -1.0f},
    {+0.71f, +0.71f, 0.0f, +1.0f},
    { 0.0f,   0.0f,  1.0f,  0.0f},
    { 0.0f,   0.0f,  1.0f,  0.0f},
};

inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

// Command from topside, all axes -1..1
struct Command {
    uint16_t seq = 0;
    bool arm = false;
    float surge = 0, sway = 0, heave = 0, yaw = 0;
    float gain = 0.5f;      // 0..1 master thrust gain
    float lights = 0;       // 0..1
    float pan = 0, tilt = 0; // degrees
};

// Mix the four axes into six thruster demands (-1..1). Horizontals and verticals are normalised
// separately so a full heave never steals authority from the horizontals.
inline void mix(const Command& c, float out[NT]) {
    float ax[4] = {clampf(c.surge, -1, 1), clampf(c.sway, -1, 1), clampf(c.heave, -1, 1), clampf(c.yaw, -1, 1)};
    for (int i = 0; i < NT; i++) {
        float s = 0;
        for (int k = 0; k < 4; k++) s += MIX[i][k] * ax[k];
        out[i] = s;
    }
    float mh = 0, mv = 0;
    for (int i = 0; i < 4; i++) mh = fmaxf(mh, fabsf(out[i]));
    for (int i = 4; i < 6; i++) mv = fmaxf(mv, fabsf(out[i]));
    if (mh > 1.0f) for (int i = 0; i < 4; i++) out[i] /= mh;
    if (mv > 1.0f) for (int i = 4; i < 6; i++) out[i] /= mv;
    float g = clampf(c.gain, 0, 1);
    for (int i = 0; i < NT; i++) out[i] *= g;
}

// Scale all demands down together so the estimated total current stays inside the budget.
// Returns the scale applied (1 = not limited).
inline float apply_budget(float d[NT], float i_full_a, float budget_a) {
    float est = 0;
    for (int i = 0; i < NT; i++) est += fabsf(d[i]) * i_full_a;
    if (est <= budget_a || est <= 0) return 1.0f;
    float k = budget_a / est;
    for (int i = 0; i < NT; i++) d[i] *= k;
    return k;
}

inline float estimate_current(const float d[NT], float i_full_a) {
    float est = 0;
    for (int i = 0; i < NT; i++) est += fabsf(d[i]) * i_full_a;
    return est;
}

// Move cur toward target by at most dt/ramp_s (full scale per ramp_s), so reversals pass through zero.
inline float ramp(float cur, float target, float dt, float ramp_s) {
    float step = dt / ramp_s;
    float diff = target - cur;
    if (diff > step) return cur + step;
    if (diff < -step) return cur - step;
    return target;
}

inline float slew(float cur, float target, float dt, float rate_per_s) {
    float step = rate_per_s * dt;
    float diff = target - cur;
    if (diff > step) return cur + step;
    if (diff < -step) return cur - step;
    return target;
}

// ---------------- battery state with hysteresis ----------------
enum BattState : uint8_t { BATT_OK = 0, BATT_WARN = 1, BATT_LOW = 2, BATT_EMPTY = 3 };

inline BattState batt_update(BattState s, float v) {
    // falling thresholds
    BattState f = BATT_OK;
    if (v < VBAT_EMPTY) f = BATT_EMPTY;
    else if (v < VBAT_LOW) f = BATT_LOW;
    else if (v < VBAT_WARN) f = BATT_WARN;
    if (f > s) return f;                  // getting worse: act at once
    // recovering: only step back up with hysteresis
    const float up[4] = {0, VBAT_WARN, VBAT_LOW, VBAT_EMPTY};
    while (s > BATT_OK && v > up[s] + VBAT_HYST) s = (BattState)(s - 1);
    return s;
}

inline float batt_thrust_cap(BattState s) {
    return s == BATT_EMPTY ? 0.0f : (s == BATT_LOW ? 0.5f : 1.0f);
}

// ---------------- protocol ----------------
// Lines, NMEA style: $<body>*HH\n, HH = XOR of every byte between '$' and '*', two hex digits.
// Command   (topside -> Pi -> Pico): $C,seq,arm,surge,sway,heave,yaw,gain,lights,pan,tilt*HH
//   surge..yaw -1000..1000, gain/lights 0..1000, pan/tilt in tenths of a degree.
// Telemetry (Pico -> Pi -> topside): $T,seq,ms,armed,flags,vbat_mV,d1..d6,i_dA,pan,tilt*HH
//   d1..d6 -1000..1000 (actual duty after ramp), i_dA estimated thruster current in 0.1 A,
//   pan/tilt in tenths of a degree. flags: see FLAG_*.
enum : uint16_t {
    FLAG_LINK_LOST = 1, FLAG_BATT_WARN = 2, FLAG_BATT_LOW = 4, FLAG_BATT_EMPTY = 8,
    FLAG_LEAK = 16, FLAG_BUDGET = 32, FLAG_BOOT = 64,
};

inline uint8_t nmea_xor(const char* s, size_t n) {
    uint8_t x = 0;
    for (size_t i = 0; i < n; i++) x ^= (uint8_t)s[i];
    return x;
}

inline int hexval(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

// Check framing + checksum. On success points body/len at the text between '$' and '*'.
inline bool frame_ok(const char* line, const char** body, size_t* len) {
    if (!line || line[0] != '$') return false;
    const char* star = strchr(line, '*');
    if (!star || hexval(star[1]) < 0 || hexval(star[2]) < 0) return false;
    size_t n = (size_t)(star - line - 1);
    uint8_t want = (uint8_t)(hexval(star[1]) * 16 + hexval(star[2]));
    if (nmea_xor(line + 1, n) != want) return false;
    *body = line + 1; *len = n;
    return true;
}

// Parse a command line. Returns false (and leaves out untouched) on any error.
inline bool parse_command(const char* line, Command& out) {
    const char* body; size_t n;
    if (!frame_ok(line, &body, &n) || n < 2 || body[0] != 'C' || body[1] != ',') return false;
    char buf[128];
    if (n >= sizeof(buf)) return false;
    memcpy(buf, body + 2, n - 2); buf[n - 2] = 0;
    long v[10]; int k = 0;
    char* p = buf;
    while (k < 10) {
        char* end;
        v[k] = strtol(p, &end, 10);
        if (end == p) return false;
        k++;
        if (*end == ',') p = end + 1;
        else if (*end == 0) break;
        else return false;
    }
    if (k != 10) return false;
    Command c;
    c.seq = (uint16_t)v[0];
    c.arm = v[1] != 0;
    c.surge = clampf(v[2] / 1000.0f, -1, 1);
    c.sway  = clampf(v[3] / 1000.0f, -1, 1);
    c.heave = clampf(v[4] / 1000.0f, -1, 1);
    c.yaw   = clampf(v[5] / 1000.0f, -1, 1);
    c.gain  = clampf(v[6] / 1000.0f, 0, 1);
    c.lights = clampf(v[7] / 1000.0f, 0, 1);
    c.pan  = clampf(v[8] / 10.0f, -PAN_LIMIT_DEG, PAN_LIMIT_DEG);
    c.tilt = clampf(v[9] / 10.0f, -TILT_LIMIT_DEG, TILT_LIMIT_DEG);
    out = c;
    return true;
}

// Append "*HH\n" to a body that starts with '$'. Returns total length.
inline int finish_line(char* buf, int len, int cap) {
    uint8_t x = nmea_xor(buf + 1, (size_t)(len - 1));
    return len + snprintf(buf + len, (size_t)(cap - len), "*%02X\n", x);
}

inline int format_telemetry(char* buf, int cap, uint16_t seq, uint32_t ms, bool armed, uint16_t flags,
                            float vbat, const float d[NT], float i_est, float pan, float tilt) {
    int n = snprintf(buf, (size_t)cap, "$T,%u,%lu,%d,%u,%d", (unsigned)seq, (unsigned long)ms, armed ? 1 : 0,
                     (unsigned)flags, (int)lroundf(vbat * 1000.0f));
    for (int i = 0; i < NT; i++) n += snprintf(buf + n, (size_t)(cap - n), ",%d", (int)lroundf(d[i] * 1000.0f));
    n += snprintf(buf + n, (size_t)(cap - n), ",%d,%d,%d", (int)lroundf(i_est * 10.0f),
                  (int)lroundf(pan * 10.0f), (int)lroundf(tilt * 10.0f));
    return finish_line(buf, n, cap);
}

// ---------------- the controller (state machine, no hardware) ----------------
struct Outputs {
    float duty[NT] = {0, 0, 0, 0, 0, 0};   // to the bridges, after ramp
    bool armed = false;
    float lights = 0;
    float pan = 0, tilt = 0;                 // degrees, after slew
    uint16_t flags = FLAG_BOOT;
    float i_est = 0;
};

class Controller {
public:
    Command cmd;
    Outputs out;
    BattState batt = BATT_OK;
    uint32_t last_cmd_ms = 0;
    bool have_cmd = false;
    bool leak = false;

    void on_command(const Command& c, uint32_t now_ms) {
        cmd = c; last_cmd_ms = now_ms; have_cmd = true;
        out.flags &= (uint16_t)~FLAG_BOOT;
    }

    // dt in seconds, vbat filtered volts
    void step(uint32_t now_ms, float dt, float vbat) {
        batt = batt_update(batt, vbat);
        bool link = have_cmd && (now_ms - last_cmd_ms) <= LINK_TIMEOUT_MS;
        bool arm = link && cmd.arm && batt != BATT_EMPTY && !leak;

        float target[NT];
        if (arm) {
            mix(cmd, target);
            float cap = batt_thrust_cap(batt);
            for (int i = 0; i < NT; i++) target[i] *= cap;
        } else {
            for (int i = 0; i < NT; i++) target[i] = 0;
        }
        float k = apply_budget(target, I_FULL_A, I_BUDGET_A);
        for (int i = 0; i < NT; i++) {
            float t = fabsf(target[i]) < DEADBAND ? 0.0f : target[i];
            out.duty[i] = ramp(out.duty[i], t, dt, RAMP_S);
        }
        // a disarm cuts the bridges at once (ARM low); ramps only shape armed motion
        if (!arm) for (int i = 0; i < NT; i++) out.duty[i] = 0;
        out.armed = arm;
        out.i_est = estimate_current(out.duty, I_FULL_A);

        float lt = link ? cmd.lights : 0.0f;
        if (batt == BATT_EMPTY) lt = fminf(lt, LIGHTS_MIN);
        out.lights = lt;

        float pt = link ? cmd.pan : 0.0f, tt = link ? cmd.tilt : 0.0f;
        out.pan = slew(out.pan, clampf(pt, -PAN_LIMIT_DEG, PAN_LIMIT_DEG), dt, SERVO_SLEW_DPS);
        out.tilt = slew(out.tilt, clampf(tt, -TILT_LIMIT_DEG, TILT_LIMIT_DEG), dt, SERVO_SLEW_DPS);

        uint16_t f = out.flags & FLAG_BOOT;
        if (!link) f |= FLAG_LINK_LOST;
        if (batt >= BATT_WARN) f |= FLAG_BATT_WARN;
        if (batt >= BATT_LOW) f |= FLAG_BATT_LOW;
        if (batt >= BATT_EMPTY) f |= FLAG_BATT_EMPTY;
        if (leak) f |= FLAG_LEAK;
        if (k < 0.999f) f |= FLAG_BUDGET;
        out.flags = f;
    }
};

inline float servo_us(float deg, int8_t dir) {
    return SERVO_CENTER_US + dir * deg * SERVO_US_PER_DEG;
}

}  // namespace rov
