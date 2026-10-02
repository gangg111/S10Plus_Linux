# Obraz boot (naglowek Androida v1) z initramfs bez skryptu bring-upu zz-early-debug
# (3 wibracje po 1 s, szum na fb0, telnet roota bez hasla po USB). Jadro, wiersz
# polecen i reszta naglowka bez zmian; cpio newc edytowany wpis po wpisie (te same
# uprawnienia, wlasciciele, czasy), xz -9e z suma crc32 jak w debian/rules.
# Uzycie: python bez-early-debug.py <wejscie.img> <wyjscie.img>
import hashlib
import lzma
import struct
import sys

src, dst = sys.argv[1], sys.argv[2]
img = open(src, "rb").read()
assert img[:8] == b"ANDROID!"
ks, ka, rs, ra, ss, sa, ta, page, ver = struct.unpack_from("<9I", img, 8)
assert ver == 1 and ss == 0, (ver, ss)
ID_OFF = 8 + 36 + 4 + 16 + 512  # po os_version, name, cmdline


def pages(n):
    return (n + page - 1) // page * page


koff = page
roff = koff + pages(ks)
assert not any(img[roff + pages(rs):]), "dane za ramdyskiem"
kernel = img[koff:koff + ks]


def ident(rd):
    # mkbootimg: jadro, ramdysk, second, recovery_dtbo, dtb (puste), kazde z dlugoscia
    sha = hashlib.sha1()
    for blob in (kernel, rd, b"", b"", b""):
        sha.update(blob)
        sha.update(struct.pack("<I", len(blob)))
    return sha.digest()


assert img[ID_OFF:ID_OFF + 20] == ident(img[roff:roff + rs]), "inny wzor id"
cpio = lzma.decompress(img[roff:roff + rs])

USUN = "scripts/init-top/zz-early-debug"
ORDER = "scripts/init-top/ORDER"


def pad4(buf):
    buf += b"\0" * (-len(buf) % 4)


out = bytearray()
pos = 0
usuniete = zmienione = wpisow = 0
while True:
    h = cpio[pos:pos + 110]
    assert h[:6] == b"070701", (pos, h[:6])
    f = [int(h[6 + 8 * i:14 + 8 * i], 16) for i in range(13)]
    namesize, filesize = f[11], f[6]
    name_end = pos + 110 + namesize
    name = cpio[pos + 110:name_end - 1].decode()
    data_off = (name_end + 3) & ~3
    data = cpio[data_off:data_off + filesize]
    nxt = (data_off + filesize + 3) & ~3
    wpisow += 1
    if name == USUN:
        usuniete += 1
    else:
        if name == ORDER:
            lines = data.decode().splitlines(keepends=True)
            i = next(k for k, l in enumerate(lines) if "zz-early-debug" in l)
            # wpis skryptu i nastepujace po nim wczytanie param.conf
            assert "param.conf" in lines[i + 1], lines[i + 1]
            del lines[i:i + 2]
            data = "".join(lines).encode()
            f[6] = len(data)
            zmienione += 1
        out += b"070701" + b"".join(b"%08X" % v for v in f) + cpio[pos + 110:name_end]
        pad4(out)
        out += data
        pad4(out)
    if name == "TRAILER!!!":
        break
    pos = nxt
assert usuniete == 1 and zmienione == 1, (usuniete, zmienione)
out += b"\0" * (-len(out) % 512)
rd = lzma.compress(bytes(out), format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC32,
                   preset=9 | lzma.PRESET_EXTREME)

hdr = bytearray(img[:page])
struct.pack_into("<I", hdr, 16, len(rd))
hdr[ID_OFF:ID_OFF + 32] = ident(rd) + b"\0" * 12
new = bytes(hdr) + kernel + b"\0" * (pages(ks) - ks) + rd
new += b"\0" * (len(img) - len(new))
assert len(new) == len(img)
open(dst, "wb").write(new)
print("wpisow cpio %d, usuniety 1, ORDER zmieniony; ramdysk %d -> %d B" % (wpisow, rs, len(rd)))
