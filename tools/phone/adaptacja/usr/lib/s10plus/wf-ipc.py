#!/usr/bin/env python3
# Minimalny klient wayfire IPC: wstrzykuje klawisz przez stipc/feed_key.
# Protokol wayfire IPC: [uint32 LE dlugosc][JSON]. Omija libinput/seatd.
import socket, struct, json, sys, os

SOCK = os.environ.get("WAYFIRE_SOCKET", "/run/user/32011/wayfire-wayland-0-.socket")

def rpc(s, method, data=None):
    msg = json.dumps({"method": method, "data": data or {}}).encode()
    s.sendall(struct.pack("=I", len(msg)) + msg)
    hdr = b""
    while len(hdr) < 4:
        chunk = s.recv(4 - len(hdr))
        if not chunk:
            return None
        hdr += chunk
    n = struct.unpack("=I", hdr)[0]
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            break
        buf += chunk
    return json.loads(buf.decode())

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "key"
    s = socket.socket(socket.AF_UNIX)
    s.connect(SOCK)
    if cmd == "list":
        print(json.dumps(rpc(s, "list-methods"), indent=1)[:1500])
    elif cmd == "key":
        key = sys.argv[2] if len(sys.argv) > 2 else "KEY_WAKEUP"
        print("press:", rpc(s, "stipc/feed_key", {"key": key, "state": True}))
        print("release:", rpc(s, "stipc/feed_key", {"key": key, "state": False}))
    s.close()

main()
