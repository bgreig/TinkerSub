// Host unit tests for rov_core.h:  g++ -std=c++17 -I../pico_rov test_core.cpp -o t && ./t
#include <cassert>
#include <cstdio>
#include <cmath>
#include "rov_core.h"
using namespace rov;

static int fails = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)
static bool near(float a, float b, float e = 1e-3f) { return fabsf(a - b) < e; }

static void make_cmd(char* buf, int cap, const char* body) {
    int n = snprintf(buf, cap, "$%s", body);
    finish_line(buf, n, cap);
}

int main() {
    // --- mixer: pure surge drives the four horizontals with the table's signs, verticals idle
    Command c; c.gain = 1; c.surge = 1;
    float d[6]; mix(c, d);
    CHECK(near(d[0], -0.71f) && near(d[1], -0.71f) && near(d[2], 0.71f) && near(d[3], 0.71f));
    CHECK(d[4] == 0 && d[5] == 0);
    // surge + yaw saturates and is normalised so max |d| = 1
    c.yaw = 1; mix(c, d);
    float mx = 0; for (int i = 0; i < 4; i++) mx = fmaxf(mx, fabsf(d[i]));
    CHECK(near(mx, 1.0f));
    // heave alone: verticals only, and does not shrink a simultaneous horizontal command
    Command h; h.gain = 1; h.heave = 1; h.sway = 0.5f; mix(h, d);
    CHECK(near(d[4], 1) && near(d[5], 1) && near(fabsf(d[0]), 0.355f));
    // gain scales everything
    h.gain = 0.5f; mix(h, d); CHECK(near(d[4], 0.5f));

    // --- budget: six thrusters at full = 60 A estimated, budget 28 A -> scaled to 28 A
    float all[6] = {1, -1, 1, -1, 1, 1};
    float k = apply_budget(all, 10.0f, 28.0f);
    CHECK(near(k, 28.0f / 60.0f) && near(estimate_current(all, 10.0f), 28.0f));
    float small[6] = {0.2f, 0, 0, 0, 0, 0};
    CHECK(apply_budget(small, 10.0f, 28.0f) == 1.0f && near(small[0], 0.2f));

    // --- ramp: 0 -> 1 takes RAMP_S, a reversal passes through zero
    float r = 0; int ticks = 0;
    while (r < 1.0f && ticks < 1000) { r = ramp(r, 1.0f, 0.01f, 0.15f); ticks++; }
    CHECK(ticks >= 15 && ticks <= 16);   // 150 ms at 100 Hz, float rounding
    r = 1.0f; bool crossed_zero = false;
    for (int i = 0; i < 40; i++) { r = ramp(r, -1.0f, 0.01f, 0.15f); if (fabsf(r) < 0.07f) crossed_zero = true; }
    CHECK(crossed_zero && near(r, -1.0f));

    // --- battery thresholds and hysteresis
    BattState b = BATT_OK;
    b = batt_update(b, 12.0f); CHECK(b == BATT_OK);
    b = batt_update(b, 10.4f); CHECK(b == BATT_WARN);
    b = batt_update(b, 10.6f); CHECK(b == BATT_WARN);          // inside hysteresis: stays
    b = batt_update(b, 10.8f); CHECK(b == BATT_OK);
    b = batt_update(b, 9.5f);  CHECK(b == BATT_EMPTY);          // straight to empty
    b = batt_update(b, 9.7f);  CHECK(b == BATT_EMPTY);
    CHECK(batt_thrust_cap(BATT_LOW) == 0.5f && batt_thrust_cap(BATT_EMPTY) == 0.0f);

    // --- protocol: good line parses, bad checksum / short line rejected, values clamped
    char line[160];
    make_cmd(line, sizeof line, "C,7,1,500,-250,1000,0,800,300,450,-200");
    Command p; CHECK(parse_command(line, p));
    CHECK(p.seq == 7 && p.arm && near(p.surge, 0.5f) && near(p.sway, -0.25f) && near(p.heave, 1.0f));
    CHECK(near(p.gain, 0.8f) && near(p.lights, 0.3f) && near(p.pan, 45.0f) && near(p.tilt, -20.0f));
    line[5] ^= 1; Command q; CHECK(!parse_command(line, q));
    make_cmd(line, sizeof line, "C,1,1,5");           CHECK(!parse_command(line, q));
    make_cmd(line, sizeof line, "C,1,1,0,0,0,0,0,0,1200,900");  // pan 120 deg, tilt 90 deg -> limits
    CHECK(parse_command(line, q) && near(q.pan, 90.0f) && near(q.tilt, 45.0f));
    make_cmd(line, sizeof line, "C,1,1,x,0,0,0,0,0,0,0"); CHECK(!parse_command(line, q));

    // telemetry round trip: frame checks out
    float dd[6] = {0.5f, -0.5f, 0, 0, 1, -1};
    int n = format_telemetry(line, sizeof line, 3, 12345, true, FLAG_BUDGET, 11.9f, dd, 21.0f, 10.0f, -5.0f);
    const char* body; size_t blen;
    CHECK(n > 10 && line[n - 1] == '\n');
    line[n - 1] = 0;
    CHECK(frame_ok(line, &body, &blen) && body[0] == 'T');
    CHECK(strstr(line, ",11900,500,-500,0,0,1000,-1000,210,100,-50*") != nullptr);

    // --- controller: link timeout disarms and zeroes thrust; empty battery disarms; budget flag
    Controller ctl;
    Command a; a.arm = true; a.gain = 1; a.surge = 1; a.yaw = 1; a.heave = 1;
    ctl.on_command(a, 0);
    for (int t = 1; t <= 40; t++) ctl.step(t * 10, 0.01f, 12.0f);
    CHECK(ctl.out.armed);
    CHECK(ctl.out.i_est <= 28.0f + 0.01f && (ctl.out.flags & FLAG_BUDGET));
    ctl.step(1000, 0.01f, 12.0f);             // 1000 ms since the last command -> link lost
    CHECK(!ctl.out.armed && (ctl.out.flags & FLAG_LINK_LOST));
    for (int i = 0; i < 6; i++) CHECK(ctl.out.duty[i] == 0);
    ctl.on_command(a, 1000);
    ctl.step(1010, 0.01f, 9.0f);
    CHECK(!ctl.out.armed && (ctl.out.flags & FLAG_BATT_EMPTY));
    // servo slew limits
    Controller s2; Command sc; sc.pan = 90; s2.on_command(sc, 0);
    s2.step(10, 0.1f, 12.0f); CHECK(near(s2.out.pan, 12.0f));     // 120 deg/s * 0.1 s
    CHECK(near(servo_us(90, 1), 2500) && near(servo_us(-45, 1), 1000));

    printf(fails ? "%d FAILURES\n" : "all tests passed\n", fails);
    return fails ? 1 : 0;
}
