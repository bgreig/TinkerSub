#!/usr/bin/env python3
"""
ROV Pi Zero bridge (Stage 1).

Topside --UDP 5005--> this bridge --UART 115200--> Pico
Topside <--UDP 5006-- this bridge <--UART-------- Pico (telemetry)

It only forwards lines that pass the checksum, and it is a second failsafe behind the Pico:
if commands from topside stop for 0.4 s it sends a few disarm lines, then goes quiet so the Pico's
own 500 ms timeout also trips (thrusters off, lights off, camera centred).

Needs: python3-serial  (sudo apt install python3-serial)
"""
import argparse, select, socket, sys, time

try:
    import serial
except ImportError:
    sys.exit("pyserial missing: sudo apt install python3-serial")


def nmea_xor(s: bytes) -> int:
    x = 0
    for b in s:
        x ^= b
    return x


def frame_ok(line: bytes) -> bool:
    line = line.strip()
    if len(line) < 5 or line[:1] != b"$" or b"*" not in line:
        return False
    body, _, cs = line[1:].rpartition(b"*")
    try:
        return int(cs[:2], 16) == nmea_xor(body)
    except ValueError:
        return False


def make_line(body: str) -> bytes:
    return b"$" + body.encode() + b"*%02X\n" % nmea_xor(body.encode())


def disarm_line(seq: int) -> bytes:
    return make_line(f"C,{seq & 0xFFFF},0,0,0,0,0,0,0,0,0")


def main():
    ap = argparse.ArgumentParser(description="ROV UDP <-> UART bridge")
    ap.add_argument("--serial", default="/dev/serial0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--listen", default="0.0.0.0:5005", help="UDP address for commands from topside")
    ap.add_argument("--telem-port", type=int, default=5006, help="UDP port on topside for telemetry")
    ap.add_argument("--timeout", type=float, default=0.4, help="seconds without commands before disarming")
    a = ap.parse_args()

    host, port = a.listen.rsplit(":", 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, int(port)))
    ser = serial.Serial(a.serial, a.baud, timeout=0)
    print(f"bridge: UDP {a.listen} <-> {a.serial} @ {a.baud}", flush=True)

    topside = None          # (ip, port) of the last valid command sender
    last_cmd = 0.0
    disarms_left = 0
    seq = 0
    rx = bytearray()
    stats = {"cmd": 0, "bad": 0, "telem": 0}
    last_report = time.monotonic()

    while True:
        r, _, _ = select.select([sock, ser.fileno()], [], [], 0.05)
        now = time.monotonic()
        if sock in r:
            data, addr = sock.recvfrom(512)
            for line in data.splitlines():
                if frame_ok(line):
                    ser.write(line.strip() + b"\n")
                    topside = (addr[0], a.telem_port)
                    last_cmd = now
                    disarms_left = 3
                    stats["cmd"] += 1
                else:
                    stats["bad"] += 1
        if ser.fileno() in r or ser.in_waiting:
            rx += ser.read(ser.in_waiting or 1)
            while b"\n" in rx:
                line, _, rest = rx.partition(b"\n")
                rx = bytearray(rest)
                if topside and frame_ok(line):
                    sock.sendto(line.strip() + b"\n", topside)
                    stats["telem"] += 1
            if len(rx) > 1024:
                rx.clear()
        # failsafe: topside went quiet
        if topside and now - last_cmd > a.timeout and disarms_left > 0:
            ser.write(disarm_line(seq)); seq += 1; disarms_left -= 1
        if now - last_report > 10:
            print(f"bridge: {stats['cmd']} cmds, {stats['bad']} bad, {stats['telem']} telemetry in 10 s", flush=True)
            stats = dict.fromkeys(stats, 0); last_report = now


if __name__ == "__main__":
    main()
