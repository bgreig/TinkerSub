# Pi Zero 2 W setup (vehicle)

1. **Image**: Raspberry Pi OS Lite (64-bit, Bookworm) with Raspberry Pi Imager. In the Imager settings, set user `pi`, enable SSH, and leave Wi-Fi blank (the tether is Ethernet).
2. **UART to the Pico**: run `sudo raspi-config`, then Interface Options → Serial Port. Answer **No** to the login shell and **Yes** to the serial hardware. Add `dtoverlay=disable-bt` to `/boot/firmware/config.txt` so `/dev/serial0` is the full PL011 UART. Reboot.
   - Wiring: Pi TXD pin 8 → Pico GP1, Pi RXD pin 10 ← Pico GP0, and GND to GND. Both sides are 3.3 V, so they connect directly with no level shifter.
3. **Static IP on the tether** (USB-Ethernet adapter, normally `eth0`):
   `sudo nmcli con add type ethernet ifname eth0 con-name tether ipv4.method manual ipv4.addresses 192.168.2.2/24`
   On the topside laptop, set its tether adapter to 192.168.2.1/24 with no gateway.
4. **Bridge**:
   ```
   sudo apt install -y python3-serial
   mkdir -p ~/rov && cp rov_bridge.py ~/rov/
   sudo cp rov-bridge.service /etc/systemd/system/ && sudo systemctl enable --now rov-bridge
   journalctl -u rov-bridge -f      # prints a 10 s count of commands / telemetry
   ```
5. **Video**: `rpicam-hello --list-cameras` should list the Arducam. If it doesn't, check the camera overlay line for your Arducam model in config.txt. Then download the `linux_arm64` MediaMTX release from github.com/bluenviron/mediamtx, put `mediamtx` and this `mediamtx.yml` in `~/rov`, and run it as a service the same way as the bridge (ExecStart=/home/pi/rov/mediamtx /home/pi/rov/mediamtx.yml).
