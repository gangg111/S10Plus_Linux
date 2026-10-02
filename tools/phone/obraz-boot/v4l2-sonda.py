#!/usr/bin/env python3
# Which /dev/video* can this user open, and how many formats does ENUM_FMT give per queue
# (capped at 64, a node that never ends the list shows as 64+).
import fcntl, glob, os, struct

VIDIOC_ENUM_FMT = 0xc0405602  # _IOWR('V', 2, struct v4l2_fmtdesc), 64 bytes
TYPES = {1: "CAP", 2: "OUT", 9: "CAP_MPLANE", 10: "OUT_MPLANE"}

def nazwa(dev):
    try:
        return open("/sys/class/video4linux/%s/name" % os.path.basename(dev)).read().strip()
    except OSError:
        return "?"

def formaty(fd, typ):
    wynik = []
    for i in range(64):
        buf = bytearray(struct.pack("II", i, typ) + bytes(56))
        try:
            fcntl.ioctl(fd, VIDIOC_ENUM_FMT, buf)
        except OSError:
            return wynik
        fourcc = bytes(buf[44:48]).decode("ascii", "replace")
        wynik.append(fourcc)
    wynik.append("...64+")
    return wynik

for dev in sorted(glob.glob("/dev/video*"), key=lambda d: int(d[10:])):
    try:
        fd = os.open(dev, os.O_RDWR | os.O_NONBLOCK)
    except OSError as e:
        print("%-14s %-28s brak dostepu (%s)" % (dev, nazwa(dev), e.strerror))
        continue
    opis = []
    for t, n in TYPES.items():
        f = formaty(fd, t)
        if f:
            opis.append("%s=%s" % (n, ",".join(f[:12]) + (" (+%d)" % (len(f) - 12) if len(f) > 12 else "")))
    os.close(fd)
    print("%-14s %-28s %s" % (dev, nazwa(dev), " ".join(opis) or "-"))
