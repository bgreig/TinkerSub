#!/usr/bin/env python3
"""
TinkerSub KB-1 topside control: game controller -> UDP commands at 50 Hz, telemetry HUD.

Run:   python3 rov_topside.py --rov 192.168.2.2
Video: open http://192.168.2.2:8889/cam in a browser (WebRTC, lowest latency),
       or:  mpv --profile=low-latency --untimed rtsp://192.168.2.2:8554/cam

Controls (Xbox-style pad; change MAP below for others):
  left stick  : surge (up/down), yaw (left/right)
  right stick : heave (up/down), sway (left/right)
  START       : arm / disarm (arming only with the sticks centred)
  A / B       : lights up / down       X : cycle thrust gain 25-50-75-100 %
  d-pad       : camera tilt (up/down), pan (left/right)      Y : centre the camera
Keyboard: SPACE arm/disarm, L / K lights, G gain, ESC quit.

Needs: pip install pygame
"""
import argparse, socket, time, sys

try:
    import pygame          # only main() needs it; the protocol helpers import without it
except ImportError:
    pygame = None

MAP = dict(surge=(1, -1), yaw=(0, 1), heave=(3, -1), sway=(2, 1),   # (axis index, sign)
           btn_a=0, btn_b=1, btn_x=2, btn_y=3, btn_start=7)
DEADZONE = 0.08
GAINS = [0.25, 0.5, 0.75, 1.0]
PAN_LIMIT, TILT_LIMIT = 90.0, 45.0
CAM_RATE = 90.0          # deg/s while the d-pad is held
FLAGS = {1: "LINK LOST", 2: "BATT WARN", 4: "BATT LOW - SURFACE", 8: "BATT EMPTY", 16: "LEAK",
         32: "CURRENT LIMIT", 64: "BOOT"}


def nmea_xor(s: bytes) -> int:
    x = 0
    for b in s:
        x ^= b
    return x


def make_cmd(seq, arm, surge, sway, heave, yaw, gain, lights, pan, tilt) -> bytes:
    i = lambda v: int(round(max(-1.0, min(1.0, v)) * 1000))
    body = (f"C,{seq & 0xFFFF},{1 if arm else 0},{i(surge)},{i(sway)},{i(heave)},{i(yaw)},"
            f"{int(gain * 1000)},{int(lights * 1000)},{int(round(pan * 10))},{int(round(tilt * 10))}").encode()
    return b"$" + body + b"*%02X\n" % nmea_xor(body)


def parse_telem(line: bytes):
    line = line.strip()
    if not line.startswith(b"$T,") or b"*" not in line:
        return None
    body, _, cs = line[1:].rpartition(b"*")
    try:
        if int(cs[:2], 16) != nmea_xor(body):
            return None
        f = [int(x) for x in body.split(b",")[1:]]
    except ValueError:
        return None
    if len(f) != 14:
        return None
    return dict(seq=f[0], ms=f[1], armed=bool(f[2]), flags=f[3], vbat=f[4] / 1000, duty=[d / 1000 for d in f[5:11]],
                amps=f[11] / 10, pan=f[12] / 10, tilt=f[13] / 10)


def dz(v):
    return 0.0 if abs(v) < DEADZONE else (v - DEADZONE * (1 if v > 0 else -1)) / (1 - DEADZONE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rov", default="192.168.2.2")
    ap.add_argument("--port", type=int, default=5005)
    ap.add_argument("--telem-port", type=int, default=5006)
    a = ap.parse_args()
    if pygame is None:
        sys.exit("pygame missing: pip install pygame")

    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("0.0.0.0", a.telem_port)); rx.setblocking(False)

    pygame.init(); pygame.joystick.init()
    screen = pygame.display.set_mode((560, 330))
    pygame.display.set_caption("ROV topside")
    font = pygame.font.SysFont("monospace", 18); big = pygame.font.SysFont("monospace", 28, bold=True)
    js = pygame.joystick.Joystick(0) if pygame.joystick.get_count() else None
    if js: js.init()

    armed = False; gain_i = 1; lights = 0.0; pan = tilt = 0.0
    seq = 0; telem = None; telem_t = 0.0
    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(50) / 1000.0
        ax = dict(surge=0.0, sway=0.0, heave=0.0, yaw=0.0)
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                tx.sendto(make_cmd(seq, False, 0, 0, 0, 0, 0, 0, 0, 0), (a.rov, a.port)); return
            if e.type == pygame.JOYDEVICEADDED and js is None:
                js = pygame.joystick.Joystick(e.device_index); js.init()
            press = e.button if e.type == pygame.JOYBUTTONDOWN else None
            key = e.key if e.type == pygame.KEYDOWN else None
            if press == MAP["btn_start"] or key == pygame.K_SPACE:
                if armed: armed = False
                else:
                    centred = js is None or all(abs(dz(js.get_axis(MAP[k][0]))) < 0.05 for k in ax)
                    armed = centred
            if press == MAP["btn_x"] or key == pygame.K_g: gain_i = (gain_i + 1) % len(GAINS)
            if press == MAP["btn_a"] or key == pygame.K_l: lights = min(1.0, lights + 0.25)
            if press == MAP["btn_b"] or key == pygame.K_k: lights = max(0.0, lights - 0.25)
            if press == MAP["btn_y"]: pan = tilt = 0.0
        if js:
            for k in ax:
                idx, sign = MAP[k]
                if idx < js.get_numaxes(): ax[k] = sign * dz(js.get_axis(idx))
            if js.get_numhats():
                hx, hy = js.get_hat(0)
                pan = max(-PAN_LIMIT, min(PAN_LIMIT, pan - hx * CAM_RATE * dt))
                tilt = max(-TILT_LIMIT, min(TILT_LIMIT, tilt + hy * CAM_RATE * dt))
        tx.sendto(make_cmd(seq, armed, ax["surge"], ax["sway"], ax["heave"], ax["yaw"], GAINS[gain_i], lights,
                           pan, tilt), (a.rov, a.port))
        seq += 1
        try:
            while True:
                t = parse_telem(rx.recv(512))
                if t: telem, telem_t = t, time.monotonic()
        except BlockingIOError:
            pass

        # ---- HUD
        age = time.monotonic() - telem_t
        screen.fill((18, 22, 26))
        ok = telem is not None and age < 1.0
        rov_armed = ok and telem["armed"]
        screen.blit(big.render("ARMED" if rov_armed else ("arm requested" if armed else "DISARMED"), True,
                               (255, 90, 80) if rov_armed else (200, 200, 200)), (16, 12))
        lines = [f"link      {'OK' if ok else 'NO TELEMETRY'}" + (f"  ({age*1000:.0f} ms)" if ok else ""),
                 f"gain      {GAINS[gain_i]*100:.0f} %     lights {lights*100:.0f} %",
                 f"camera    pan {pan:+.0f}   tilt {tilt:+.0f}",
                 f"pad       {'connected: ' + js.get_name()[:28] if js else 'none (keyboard only)'}"]
        if ok:
            lines += [f"battery   {telem['vbat']:.2f} V   thrusters ~{telem['amps']:.1f} A",
                      "duty      " + " ".join(f"{d:+.2f}" for d in telem["duty"])]
            warn = [n for b, n in FLAGS.items() if telem["flags"] & b and b != 64]
            if warn: lines.append("!! " + ", ".join(warn))
        for i, s in enumerate(lines):
            col = (255, 200, 80) if s.startswith("!!") else (220, 225, 230)
            screen.blit(font.render(s, True, col), (16, 60 + 30 * i))
        if not ok and armed:
            armed = False      # no telemetry for a second: drop the arm request too
        pygame.display.flip()


if __name__ == "__main__":
    main()
