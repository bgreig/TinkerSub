"""Integration test: topside packets -> bridge (UDP) -> fake Pico on a pseudo-terminal -> telemetry back.
Also checks the bridge drops bad checksums and sends disarm lines when topside goes quiet.
Run: python3 integration.py"""
import os, sys, tty, socket, subprocess, time, select
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../topside"))
from rov_topside import make_cmd, parse_telem, nmea_xor

master, slave = os.openpty(); tty.setraw(slave); tty.setraw(master)
br = subprocess.Popen([sys.executable, os.path.join(HERE, "../pi_bridge/rov_bridge.py"), "--serial", os.ttyname(slave),
                       "--listen", "127.0.0.1:5005", "--telem-port", "5006"], stdout=subprocess.DEVNULL)
time.sleep(0.8)
tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.bind(("127.0.0.1", 5006)); rx.settimeout(0.3)
buf, seen, telem, tseq = b"", [], [], 0

def pico_service(dur):
    """Fake Pico: read lines from the bridge, answer each with a telemetry frame echoing arm and surge."""
    global buf, tseq
    end = time.time() + dur
    while time.time() < end:
        if select.select([master], [], [], 0.01)[0]:
            buf += os.read(master, 512)
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1); seen.append(line)
            f = line[3:line.index(b"*")].split(b",")
            body = f"T,{tseq},{tseq*10},{f[1].decode()},0,11900,{f[2].decode()},0,0,0,0,0,0,0,0".encode()
            os.write(master, b"$" + body + b"*%02X\n" % nmea_xor(body)); tseq += 1

tx.sendto(b"$C,1,1,0,0*00\n", ("127.0.0.1", 5005))                   # bad checksum
for i in range(20):
    tx.sendto(make_cmd(i, True, 0.5, 0, 0, 0, 0.5, 0, 0, 0), ("127.0.0.1", 5005))
    pico_service(0.02)
    try:
        t = parse_telem(rx.recv(512))
        if t: telem.append(t)
    except socket.timeout: pass
n_before = len(seen)
pico_service(1.0)                                                       # topside goes quiet
disarms = [l for l in seen[n_before:] if l.startswith(b"$C,") and l.split(b",")[2] == b"0"]
br.terminate()

checks = {
    "all 20 good commands reached the Pico, bad one dropped": n_before == 20 and all(b"*00" not in l for l in seen),
    "telemetry came back to topside (>=18)": len(telem) >= 18,
    "armed + surge 0.5 echoed": bool(telem) and telem[-1]["armed"] and telem[-1]["duty"][0] == 0.5,
    "bridge sent 3 disarm lines after 0.4 s silence": len(disarms) == 3,
}
for k, v in checks.items(): print(("PASS " if v else "FAIL ") + k)
sys.exit(0 if all(checks.values()) else 1)
