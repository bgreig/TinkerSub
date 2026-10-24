# Security policy

TinkerSub is a machine you build yourself: a lithium-ion battery, motors that spin props, and a tethered network link that drives them. So this policy covers two kinds of problem:

- **Security vulnerabilities** in the firmware and software: the Pico firmware, the Pi bridge, the topside program, the video setup and the build scripts in `Source/`.
- **Safety defects** in the design or the guide: anything that could start a fire, injure someone, flood or crush an enclosure, or let the thrusters run when they shouldn't. Examples: a fuse or wire that is too small for its current, a battery-pack step that could short a cell, a seal or pressure-test step that is wrong, a failsafe that doesn't stop the motors.

## Supported versions

| Version | Supported |
|---|---|
| KB-1, latest commit on `main` | Yes |
| Older commits, forks, modified builds | No (please check whether the problem is still on `main`) |

Fixes go into `main` and are listed in [CHANGELOG.md](CHANGELOG.md). If you built from an older commit, compare your parts and firmware with the changelog.

## Reporting a problem

**Please don't open a public issue for a security vulnerability or a safety defect that someone could be hurt by before it is fixed.** Report it privately instead:

1. Go to the repository's **Security** tab and choose **Report a vulnerability** ([direct link](https://github.com/bgreig/TinkerSub/security/advisories/new)).
2. Say what is affected (file and line, part number, or guide section and page), what happens, and how to reproduce it or how you found it.
3. If you have a fix in mind, describe it. Don't open a public pull request for it until we've agreed on the fix.

Minor problems that can't hurt anyone (a typo in a torque note, a picture that shows the wrong colour) can go straight into a normal issue.

## What to expect

TinkerSub is maintained by one person in their spare time, so these are targets, not guarantees:

- An acknowledgement within 7 days.
- An assessment, and a fix or a published workaround, within 30 days for anything serious.
- Credit in the changelog and the advisory, if you'd like it.

If a defect affects parts people have already printed or built, the fix will say what to do with them (as the [2026-10-23 changelog entry](CHANGELOG.md) does for the belly pan and station tops).

## Security model and known limitations

The control system is designed for a **private, point-to-point Ethernet tether** between your topside computer and the ROV. It has no protection against anyone else on that network:

- **No authentication or encryption on the control link.** The Pi bridge listens for commands on UDP port 5005 on all interfaces and forwards every well-formed command to the Pico. The checksum in the protocol ([Firmware/PROTOCOL.md](Firmware/PROTOCOL.md)) catches corrupted lines; it does not prove who sent them. Anything that can send UDP to the Pi can arm the ROV and drive the thrusters. Telemetry goes back to whichever address sent the last valid command.
- **The camera streams are open.** MediaMTX serves the video on ports 8889 (WebRTC) and 8554 (RTSP) with no login.
- **The Pi runs SSH.** Use a strong password or, better, SSH keys only, and change any default account details before the ROV goes near a shared network.

So:

- Keep the tether a direct cable between the topside computer and the ROV. Don't connect the ROV to a shared network, the internet or a Wi-Fi access point, and don't route or bridge the tether network to one. [Firmware/pi_bridge/SETUP.md](Firmware/pi_bridge/SETUP.md) leaves the Pi's Wi-Fi unconfigured; keep it that way.
- Treat the topside computer as part of the ROV: anything running on it can drive the thrusters.

These are deliberate trade-offs for a simple, low-latency hobby system, not bugs. Reports that only restate them are welcome as feature requests (for example, command authentication), not as vulnerabilities. A way around them on the intended private tether, or a way to run the motors past the failsafes, is a vulnerability.

### Failsafes

These are safety features. A way to defeat any of them is in scope:

- The motor drivers' enable line (ARM, GP15) has a pull-down, so the drivers are off unless the Pico actively arms them.
- The topside program arms only with the sticks centred.
- The Pi bridge sends disarm commands if the topside goes quiet for 0.4 s.
- The Pico disarms if it gets no valid command for 500 ms, and its watchdog resets it if the loop stalls.
- Low-battery limits cut thrust and then disarm (values in `Firmware/pico_rov/config.h`).

## Physical safety

The design has no main power switch: the ROV is live whenever the pack fuse and F1 are in. The battery is a home-built lithium-ion pack. Follow the [Safety section of the README](README.md#safety), [docs/Battery_Pack_Build.md](docs/Battery_Pack_Build.md) and the build guide's leak-test and power-on steps. If you find a step there that is unsafe, report it as described above.
