"""
================================================================================
AeroSim Pro | Automated DJI RC (RM330/RC2) Discovery & Bridge
================================================================================
Zero-configuration bridge that automatically finds DJI screen-based remotes
(DJI RC, DJI RC 2, DJI RC Pro) on your local Wi-Fi or USB-C, connects automatically,
and streams live telemetry to the browser simulator via WebSockets.
================================================================================
"""

import sys
import os
import time
import socket
import struct
import hashlib
import base64
import threading
import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

DEFAULT_WS_PORT = 8765
DJI_TCP_PORT = 40007
DUML_CMD_SET = 0x06
DUML_CMD_ID = 0xAE

# State
bridge_state = {
    "scanning": False,
    "auto_connect": True,
    "discovered_devices": [],
    "active_device": None,
    "source": "None",
    "connected": False,
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 0.0,
    "throttle": -1.0,
    "battery": 100
}

state_lock = threading.Lock()
connected_ws_clients = set()
ws_clients_lock = threading.Lock()
tcp_thread_running = False
tcp_stop_flag = False

# ==============================================================================
# RFC 6455 WEBSOCKET ENGINE (ZERO-DEPENDENCY)
# ==============================================================================
def make_ws_handshake_response(key):
    magic = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    sha1 = hashlib.sha1(key.encode('utf-8') + magic).digest()
    accept = base64.b64encode(sha1).decode('utf-8')
    return (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
    ).encode('utf-8')

def build_ws_frame(message_str):
    payload = message_str.encode('utf-8')
    length = len(payload)
    frame = bytearray([0x81])
    if length <= 125:
        frame.append(length)
    elif length <= 65535:
        frame.append(126)
        frame.extend(struct.pack("!H", length))
    else:
        frame.append(127)
        frame.extend(struct.pack("!Q", length))
    frame.extend(payload)
    return bytes(frame)

def parse_ws_frame(data):
    if len(data) < 2:
        return None
    masked = bool(data[1] & 0x80)
    length = data[1] & 0x7F
    offset = 2
    if length == 126:
        length = struct.unpack("!H", data[offset:offset+2])[0]
        offset += 2
    elif length == 127:
        length = struct.unpack("!Q", data[offset:offset+8])[0]
        offset += 8
    
    if masked:
        masks = data[offset:offset+4]
        offset += 4
        decoded = bytearray(b ^ masks[i % 4] for i, b in enumerate(data[offset:offset+length]))
    else:
        decoded = data[offset:offset+length]
    return decoded.decode('utf-8', errors='ignore')

def handle_ws_client_message(msg_str):
    try:
        data = json.loads(msg_str)
        cmd = data.get("cmd")
        if cmd == "scan":
            threading.Thread(target=run_network_scan, daemon=True).start()
        elif cmd == "connect" and "ip" in data:
            connect_to_rc_ip(data["ip"])
        elif cmd == "set_auto_connect":
            with state_lock:
                bridge_state["auto_connect"] = bool(data.get("value", True))
    except Exception as e:
        pass

def ws_client_handler(client_sock, addr):
    try:
        req = client_sock.recv(4096).decode('utf-8', errors='ignore')
        headers = {}
        for line in req.split("\r\n"):
            if ": " in line:
                k, v = line.split(": ", 1)
                headers[k.strip().lower()] = v.strip()
        
        ws_key = headers.get("sec-websocket-key")
        if not ws_key:
            client_sock.close()
            return
        
        client_sock.sendall(make_ws_handshake_response(ws_key))
        with ws_clients_lock:
            connected_ws_clients.add(client_sock)
        print(f"[WebSocket] Web browser connected: {addr}")

        # Send initial status
        with state_lock:
            init_payload = json.dumps({"type": "status", **bridge_state})
        client_sock.sendall(build_ws_frame(init_payload))

        while True:
            chunk = client_sock.recv(1024)
            if not chunk:
                break
            msg = parse_ws_frame(chunk)
            if msg:
                handle_ws_client_message(msg)
    except Exception:
        pass
    finally:
        with ws_clients_lock:
            connected_ws_clients.discard(client_sock)
        try:
            client_sock.close()
        except Exception:
            pass

def start_ws_server(port=DEFAULT_WS_PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(5)
    print(f"[WebSocket] Listening on ws://localhost:{port}")
    while True:
        client, addr = server.accept()
        threading.Thread(target=ws_client_handler, args=(client, addr), daemon=True).start()

def broadcast_loop():
    while True:
        time.sleep(1.0 / 60.0)
        with state_lock:
            payload = json.dumps({"type": "telemetry", **bridge_state})
        frame = build_ws_frame(payload)

        with ws_clients_lock:
            dead = []
            for c in connected_ws_clients:
                try:
                    c.sendall(frame)
                except Exception:
                    dead.append(c)
            for d in dead:
                connected_ws_clients.discard(d)

# ==============================================================================
# AUTOMATIC WI-FI & USB DISCOVERY SCANNER
# ==============================================================================
def get_local_subnets():
    subnets = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                parts = ip.split(".")
                if len(parts) == 4:
                    base = f"{parts[0]}.{parts[1]}.{parts[2]}"
                    if base not in subnets:
                        subnets.append(base)
    except Exception:
        pass
    if not subnets:
        subnets = ["192.168.0", "192.168.1"]
    return subnets

def probe_dji_ip(ip):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.22)
        res = s.connect_ex((ip, DJI_TCP_PORT))
        s.close()
        if res == 0:
            return {
                "ip": ip,
                "port": DJI_TCP_PORT,
                "model": "DJI RC (RM330 / RC2)",
                "type": "wifi",
                "status": "ready"
            }
    except Exception:
        pass
    return None

def check_adb_devices():
    found = []
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=2)
        for line in res.stdout.splitlines():
            line = line.strip()
            if line and not line.startswith("List of") and "device" in line:
                dev_id = line.split()[0]
                found.append({
                    "ip": dev_id,
                    "port": 0,
                    "model": "DJI RC (USB-C ADB)",
                    "type": "usb",
                    "status": "ready"
                })
    except Exception:
        pass
    return found

def run_network_scan():
    global bridge_state
    with state_lock:
        if bridge_state["scanning"]:
            return
        bridge_state["scanning"] = True

    print("[Discovery] Scanning local Wi-Fi and USB for DJI controllers...")
    discovered = []

    # 1. Check USB ADB first
    adb_devs = check_adb_devices()
    discovered.extend(adb_devs)

    # 2. Fast parallel scan on local Wi-Fi subnets
    subnets = get_local_subnets()
    candidates = [f"{base}.{i}" for base in subnets for i in range(1, 255)]

    with ThreadPoolExecutor(max_workers=75) as executor:
        results = executor.map(probe_dji_ip, candidates)
        for r in results:
            if r:
                discovered.append(r)

    with state_lock:
        bridge_state["scanning"] = False
        bridge_state["discovered_devices"] = discovered
        auto_conn = bridge_state["auto_connect"]
        curr_active = bridge_state["active_device"]

    print(f"[Discovery] Scan complete. Found {len(discovered)} DJI controller(s).")
    for d in discovered:
        print(f" -> Found: {d['model']} at {d['ip']} ({d['type'].upper()})")

    # Auto-connect if not currently connected
    if auto_conn and not curr_active and discovered:
        first = discovered[0]
        print(f"[Discovery] Auto-connecting to {first['model']} ({first['ip']})...")
        connect_to_rc_ip(first["ip"])

# ==============================================================================
# TELEMETRY RECEIVER & DECODER
# ==============================================================================
def decode_duml_payload(data):
    if len(data) < 18:
        return None
    try:
        idx = 10
        ch1 = struct.unpack_from("<h", data, idx)[0]
        ch2 = struct.unpack_from("<h", data, idx + 2)[0]
        ch3 = struct.unpack_from("<h", data, idx + 4)[0]
        ch4 = struct.unpack_from("<h", data, idx + 6)[0]
        scale = 32767.0
        return {
            "roll": max(-1.0, min(1.0, ch1 / scale)),
            "pitch": max(-1.0, min(1.0, ch2 / scale)),
            "throttle": max(-1.0, min(1.0, ch3 / scale)),
            "yaw": max(-1.0, min(1.0, ch4 / scale))
        }
    except Exception:
        return None

def tcp_stream_worker(ip):
    global bridge_state, tcp_thread_running, tcp_stop_flag
    tcp_thread_running = True
    print(f"[Stream] Connecting to DJI RC telemetry at {ip}:{DJI_TCP_PORT}...")
    
    while not tcp_stop_flag:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((ip, DJI_TCP_PORT))
            s.settimeout(None)
            
            with state_lock:
                bridge_state["connected"] = True
                bridge_state["active_device"] = ip
                bridge_state["source"] = f"DJI RC ({ip})"
            print(f"[Stream] Successfully connected to DJI RC at {ip}!")

            buf = bytearray()
            while not tcp_stop_flag:
                chunk = s.recv(1024)
                if not chunk:
                    break
                buf.extend(chunk)
                while len(buf) >= 14:
                    if buf[0] == 0x55:
                        pkt_len = buf[1] & 0x3F
                        if len(buf) < pkt_len:
                            break
                        packet = buf[:pkt_len]
                        buf = buf[pkt_len:]
                        if len(packet) > 9 and packet[8] == DUML_CMD_SET and packet[9] == DUML_CMD_ID:
                            dec = decode_duml_payload(packet)
                            if dec:
                                with state_lock:
                                    bridge_state.update(dec)
                    else:
                        buf.pop(0)
            s.close()
        except Exception as e:
            with state_lock:
                bridge_state["connected"] = False
            time.sleep(2)
            if tcp_stop_flag:
                break

    tcp_thread_running = False

def connect_to_rc_ip(ip):
    global tcp_stop_flag
    tcp_stop_flag = True
    time.sleep(0.3)
    tcp_stop_flag = False
    threading.Thread(target=tcp_stream_worker, args=(ip,), daemon=True).start()

def auto_discovery_daemon():
    """Background daemon that scans periodically until a controller is connected"""
    while True:
        with state_lock:
            connected = bridge_state["connected"]
            auto_conn = bridge_state["auto_connect"]
        if auto_conn and not connected:
            run_network_scan()
        time.sleep(6)

# ==============================================================================
# TEST EMULATION MODE
# ==============================================================================
def run_test_emulation():
    global bridge_state
    with state_lock:
        bridge_state["connected"] = True
        bridge_state["active_device"] = "Synthetic Test RC"
        bridge_state["source"] = "Simulated DJI RC (Test Mode)"
        bridge_state["discovered_devices"] = [{
            "ip": "127.0.0.1",
            "port": 40007,
            "model": "DJI RC RM330 (Simulated)",
            "type": "wifi",
            "status": "connected"
        }]
    print("[Test Mode] Generating synthetic stick movements...")
    import math
    t = 0.0
    while True:
        time.sleep(1.0 / 60.0)
        t += 0.02
        with state_lock:
            bridge_state["roll"] = math.sin(t * 1.5) * 0.6
            bridge_state["pitch"] = math.cos(t * 1.2) * 0.4
            bridge_state["yaw"] = math.sin(t * 0.8) * 0.5
            bridge_state["throttle"] = 0.45 + math.sin(t * 0.5) * 0.15

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="AeroSim Pro Automatic DJI RC Bridge")
    parser.add_argument("--test", action="store_true", help="Run in test simulation mode")
    parser.add_argument("--ip", type=str, help="Manually connect to specific DJI RC IP")
    args = parser.parse_args()

    # 1. Start WebSocket Server & Broadcaster
    threading.Thread(target=start_ws_server, daemon=True).start()
    threading.Thread(target=broadcast_loop, daemon=True).start()

    if args.test:
        run_test_emulation()
    elif args.ip:
        connect_to_rc_ip(args.ip)
        while True:
            time.sleep(1)
    else:
        print("\n==================================================================")
        print(" AeroSim Pro | Automatic DJI Remote Discovery & Bridge")
        print("==================================================================")
        print(" * Automatically scanning your local Wi-Fi for DJI RC (RM330/RC2)...")
        print(" * As soon as your DJI RC is turned on, it will connect automatically.")
        print(" * Web simulator will receive live stick telemetry on ws://localhost:8765")
        print("==================================================================\n")
        
        # Start automatic continuous discovery daemon
        threading.Thread(target=auto_discovery_daemon, daemon=True).start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down bridge...")

if __name__ == "__main__":
    main()
