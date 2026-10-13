#!/usr/bin/env python3
"""Claude Desktop on a 480 pt wide phone screen: main window minWidth 600 -> 300.

The window asks for minWidth:600 (620 with the frame), wider than the S10+ screen.
The change is made in place in resources/app.asar, in the .vite/build chunk that
creates the main window: the same number of bytes, then the SHA-256 of the file and
of the changed 4 MiB block in the asar header are recomputed (hex digests have a
fixed length, so the header keeps its size and no offset moves).  Electron on Linux
accepts it.  A package update restores the original, so run this again after one.

Usage (root): latka-minwidth.py [/usr/lib/claude-desktop/resources/app.asar]
The original is kept as app.asar.orig-<version> next to it, once.
"""
import hashlib
import json
import os
import shutil
import struct
import sys

OLD, NEW = b"minWidth:600", b"minWidth:300"


def find_asar():
    for root in ("/usr/lib/claude-desktop", "/opt/Claude", "/usr/lib/claude"):
        for dp, _, fn in os.walk(root):
            if "app.asar" in fn:
                return os.path.join(dp, "app.asar")
    sys.exit("app.asar not found, give its path")


def walk(node, path=""):
    for name, entry in node.get("files", {}).items():
        p = f"{path}/{name}"
        if "files" in entry:
            yield from walk(entry, p)
        elif "offset" in entry:
            yield p, entry


def main():
    asar = sys.argv[1] if len(sys.argv) > 1 else find_asar()
    data = bytearray(open(asar, "rb").read())
    # Chromium pickle: [4][header pickle size][payload size][json length][json]
    header_size = struct.unpack_from("<I", data, 4)[0]
    json_len = struct.unpack_from("<I", data, 12)[0]
    header = json.loads(data[16:16 + json_len])
    base = 8 + header_size

    patched = []
    swaps = []  # (old hex digest, new hex digest) to replace in the raw header
    for path, entry in walk(header):
        if not (path.startswith("/.vite/build/") and path.endswith(".js")):
            continue
        start, size = base + int(entry["offset"]), entry["size"]
        body = bytes(data[start:start + size])
        n = body.count(OLD)
        if n == 0:
            continue
        if n != 1:
            sys.exit(f"{path}: {OLD.decode()} found {n} times, expected once")
        pos = body.index(OLD)
        data[start + pos:start + pos + len(OLD)] = NEW
        body = bytes(data[start:start + size])
        integ = entry["integrity"]
        swaps.append((integ["hash"], hashlib.sha256(body).hexdigest()))
        bs = integ["blockSize"]
        k = pos // bs
        swaps.append((integ["blocks"][k], hashlib.sha256(body[k * bs:(k + 1) * bs]).hexdigest()))
        patched.append(path)

    if not patched:
        if any(NEW in bytes(data[base + int(e["offset"]):base + int(e["offset"]) + e["size"]])
               for p, e in walk(header) if p.startswith("/.vite/build/")):
            print("already patched")
            return
        sys.exit(f"{OLD.decode()} not found: the app changed, check the window code")
    if len(patched) != 1:
        sys.exit(f"several files matched: {patched}")

    # only the two digests change in the header, byte for byte the rest stays
    # (a file of one block has the same digest for the file and the block)
    raw = bytes(data[16:16 + json_len])
    for old, new in dict(swaps).items():
        expected = sum(1 for o, _ in swaps if o == old)
        if raw.count(old.encode()) != expected:
            sys.exit(f"digest {old[:12]}.. found {raw.count(old.encode())} times in the header, expected {expected}")
        raw = raw.replace(old.encode(), new.encode())
    data[16:16 + json_len] = raw

    version = os.popen("dpkg-query -W -f='${Version}' claude-desktop 2>/dev/null").read() or "unknown"
    backup = f"{asar}.orig-{version}"
    if not os.path.exists(backup):
        shutil.copy2(asar, backup)
    tmp = asar + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    shutil.copymode(asar, tmp)
    os.replace(tmp, asar)
    print(f"patched {patched[0]}, original in {backup}")


if __name__ == "__main__":
    main()
