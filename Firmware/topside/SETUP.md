# Raspberry Pi 4 setup (topside)

The topside controller is a Raspberry Pi 4 with a monitor, a game controller and the tether plugged into its Ethernet port. It runs `rov_topside.py` (controller input, 50 Hz commands, telemetry HUD) and shows the camera stream.

## What you need
- Raspberry Pi 4 (2 GB or more), its power supply and a microSD card (16 GB or more)
- A monitor (micro-HDMI to HDMI cable), keyboard and mouse for setup
- An Xbox-style game controller (USB or Bluetooth)
- The Cat6 tether into the Pi 4's built-in Ethernet port

## 1. Image
Raspberry Pi OS (64-bit, Bookworm) **with desktop**, written with Raspberry Pi Imager. The HUD and the video need a screen. In the Imager settings, set user `pi` and enable SSH if you want it.

## 2. Static IP on the tether
The tether is a direct cable to the ROV's Pi Zero 2 W at 192.168.2.2. Give the Pi 4's Ethernet port a fixed address with no gateway:

```
sudo nmcli con add type ethernet ifname eth0 con-name tether ipv4.method manual ipv4.addresses 192.168.2.1/24
sudo nmcli con up tether
ping 192.168.2.2          # with the ROV powered and the bridge running
```

Wi-Fi can stay on for updates, but keep the tether separate: don't enable IP forwarding or bridge `eth0` to Wi-Fi (see `SECURITY.md`).

## 3. Topside program
```
sudo apt install -y python3-venv
python3 -m venv ~/rov-venv
~/rov-venv/bin/pip install -r requirements.txt
mkdir -p ~/rov && cp rov_topside.py ~/rov/
```

## 4. Game controller
- **USB:** plug it in.
- **Bluetooth:** pair it from the Bluetooth icon on the desktop taskbar.

If a stick or button acts on the wrong axis, change `MAP` at the top of `rov_topside.py`.

## 5. Fly
```
~/rov-venv/bin/python ~/rov/rov_topside.py --rov 192.168.2.2
```
The HUD should show `link OK`. For video, open `http://192.168.2.2:8889/cam` in Chromium (WebRTC, lowest latency), or use `mpv --profile=low-latency --untimed rtsp://192.168.2.2:8554/cam` (`sudo apt install mpv`).

Then follow the bench procedure in `../README.md` before the first dive.
