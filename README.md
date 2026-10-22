# AeroSim Pro | DJI 3D Drone Flight Simulator

A production-grade, single-file 3D Drone Flight Simulator web application built with Three.js and the HTML5 Gamepad API, featuring realistic multirotor physics, interactive DJI O3 telemetry HUD, and physical DJI RC controller auto-discovery.

Designed for immediate deployment to **Cloudflare Pages**.

---

## Key Features

1. **Dual Flight Perspectives**:
   - **Normal (Third-Person LOS Chase)**: Smooth following chase camera for cinematic perspective.
   - **FPV Cockpit**: Authentic pilot goggles perspective with direct roll/pitch angular banking, wide FOV, and upward camera tilt.

2. **Selectable Aircraft Hangar & Dynamics**:
   - **DJI Mini 4 Pro**: Ultralight (249g), dual obstacle-sensing eyes, gimbal camera, 16 m/s max speed, 2.2:1 thrust ratio. Supports both Normal and FPV flight modes.
   - **DJI Avata 2**: Cinewhoop racer (410g), 4 ducted propeller guard rings, battery cage, 27 m/s max speed, 4.1:1 thrust ratio, 20° camera uptilt. Locked to FPV cockpit mode.

3. **Physical DJI Controller Support**:
   - Zero-configuration local Wi-Fi auto-discovery for DJI RC (screen controller) via `dji_rc_bridge.py`.
   - Native HTML5 Gamepad API Mode 2 stick mapping.
   - Smooth keyboard and mouse controls fallback.

4. **DJI Pilot / O3 Telemetry HUD**:
   - Real-time Artificial Horizon attitude indicator.
   - Pilot orientation radar compass.
   - Horizontal speed (m/s), vertical speed (m/s), distance to home (m), altitude AGL (m), and heading (°).
   - Motor RPM bar, throttle percentage, and flight modes (Normal, Sport, Cine, Acro).
   - Neon FPV slalom gates obstacle course.

---

## Getting Started Locally

### Option A: 1-Click Launch (Recommended)
Double-click `Start_Simulator.bat` in the project folder. This will:
1. Start the local Wi-Fi DJI RC auto-discovery bridge on `ws://localhost:8765`.
2. Launch a local web server and open the simulator in your default browser.

### Option B: Standalone Web Simulator
Simply open `index.html` directly in any modern WebGL-capable browser (Chrome, Edge, Firefox, Safari).

---

## Controls

### Keyboard (Mode 2)
- **Left Stick**: `W`/`S` (Throttle Up/Down), `A`/`D` (Yaw Left/Right)
- **Right Stick**: Arrow Keys `↑`/`↓` (Pitch Forward/Backward), `←`/`→` (Roll Left/Right)
- **Arm / Disarm**: `Spacebar`
- **Reset to Launch Pad**: `R`
- **Toggle View Mode (Normal / FPV)**: `V` or `C`
- **Cycle Flight Mode (Normal / Sport / Cine / Acro)**: `M`

---

## Deployment to Cloudflare Pages

This simulator is fully self-contained in `index.html` with zero external build dependencies:

```bash
# Deploy directly to Cloudflare Pages via Wrangler
npx wrangler pages deploy . --project-name aerosim-pro
```
