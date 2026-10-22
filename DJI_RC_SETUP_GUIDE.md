# DJI RC (Built-in Screen) Connection & Bridge Guide

This guide explains how to connect and use your physical **DJI RC (Model RM330)** or **DJI RC 2 (Model RC331)** with the AeroSim Pro simulator on your laptop.

---

## 1. Why Doesn't the DJI RC Work Out-of-the-Box?

Unlike the phone-clamp **DJI RC-N1** or standard USB gamepads, the **DJI RC (with built-in screen)**:
1. Runs an **internal customized Android operating system**.
2. Does **not** expose a standard USB HID Gamepad descriptor when connected via USB-C (Windows only detects it as an Android / MTP file device or ADB interface).
3. Transmits its stick, wheel, and button telemetry via **DJI's internal DUML protocol** over an internal network daemon listening on **TCP port 40007**, or through Linux kernel input devices (`/dev/input/event*`).

To make it control PC simulators, a **bridge tool** is required to read those raw telemetry packets and stream them into the simulator.

---

## 2. Solution: Two Working Methods

You have two ways to connect your DJI RC to this simulator:

### Method A: Zero-Driver Local Bridge (`dji_rc_bridge.py`) — Recommended
We built a dedicated Python bridge script ([`dji_rc_bridge.py`](file:///c:/Users/admin/OneDrive/Desktop/DJI%20sim/dji_rc_bridge.py)) directly into this workspace:
- Uses a **lightweight, zero-dependency WebSocket server** running on `ws://localhost:8765`.
- The web simulator automatically listens for this stream. When active, it immediately displays **`DJI RC Bridge: Active`** in the Telemetry & Calibration HUD.
- No virtual joystick kernel drivers (ViGEmBus or vJoy) are needed.

#### How to use it:

#### Option 1: Over Wi-Fi (Wireless)
1. Turn on your DJI RC and connect it to the **same Wi-Fi network** as your laptop (or connect your DJI RC to your laptop's mobile hotspot).
2. Check your DJI RC's IP address (on the DJI RC screen: swipe down $\rightarrow$ Settings $\rightarrow$ Wi-Fi $\rightarrow$ tap connected network to see IP, e.g. `192.168.1.145`).
3. Open a terminal in this project folder and run:
   ```bash
   python dji_rc_bridge.py --ip <YOUR_DJI_RC_IP>
   ```
4. Open the simulator in your browser: `http://localhost:8080/index.html` (or your deployed Cloudflare Pages URL).
5. Open the **CALIBRATE** modal — you will see the sticks responding live in real-time!

#### Option 2: Over USB-C via ADB (Wired)
1. On your DJI RC, enable **Developer Options & USB Debugging** (Settings $\rightarrow$ About $\rightarrow$ tap Build Number 7 times $\rightarrow$ Developer Options $\rightarrow$ Enable USB Debugging).
2. Plug the DJI RC into your PC via USB-C.
3. In terminal, run:
   ```bash
   python dji_rc_bridge.py --adb
   ```

#### Option 3: Verification / Test Mode
To verify the bridge and simulator interface without hardware:
```bash
python dji_rc_bridge.py --test
```
You will see the twin gimbals in the calibration modal move automatically in sinusoidal sync!

---

### Method B: Precompiled GUI Tool (`voluminor/dji-rc-joystick`)
If you prefer a pre-built graphical application or want to use your DJI RC with other PC simulators (like *Liftoff*, *Velocidrone*, or *Uncrashed*):

1. Download **`dji-rc-joystick`** (Open-source on GitHub by *voluminor*):
   - [GitHub: voluminor/dji-rc-joystick Releases](https://github.com/voluminor/dji-rc-joystick/releases)
2. Install the **ViGEmBus driver** (Virtual Gamepad Emulation Bus for Windows) if prompted.
3. Connect your DJI RC to the same Wi-Fi network.
4. Launch `dji-rc-joystick.exe`. It will discover your DJI RC on the network, connect to TCP port 40007, and create a virtual Xbox 360 controller in Windows.
5. AeroSim Pro's HTML5 Gamepad API will automatically detect it as a hardware controller.

---

## 3. Flight Check & Calibration

Once connected:
1. Open the **CALIBRATE** modal in AeroSim Pro.
2. Confirm the stick indicators move smoothly from `-1.0` to `+1.0`.
3. Adjust the **Deadband** slider (default `0.05`) to prevent stick drift.
4. Adjust the **Expo Curve** slider (default `0.35`) for smooth precision hovering.
5. If the pitch or throttle directions are reversed, click the **INV PITCH** or **INV THROTTLE** toggle buttons.
