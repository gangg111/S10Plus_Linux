# Obraz boot (naglowek Androida v1) z dodatkowymi plikami firmware w /lib/firmware initramfs.
# ABOX prosi o calliope_sram*.bin w 16,5 s startu, zanim /vendor jest zamontowany (18,3 s),
# a pod Droidianem nikt nie obsluguje zapasowego user helpera; bez tego firmware procesor
# dzwieku nie startuje i kazde pm_runtime_resume ABOX wisi na zawsze (HAL w stanie D).
# Jadro, wiersz polecen i reszta naglowka bez zmian; istniejace wpisy cpio nietkniete.
# Uzycie: python firmware-do-initramfs.py <wejscie.img> <wyjscie.img> <plik> [<plik> ...]
import hashlib
import lzma
import os
import struct
import sys

src, dst, pliki = sys.argv[1], sys.argv[2], sys.argv[3:]
img = open(src, "rb").read()
assert img[:8] == b"ANDROID!"
ks, ka, rs, ra, ss, sa, ta, page, ver = struct.unpack_from("<9I", img, 8)
assert ver == 1 and ss == 0, (ver, ss)
ID_OFF = 8 + 36 + 4 + 16 + 512


def pages(n):
    return (n + page - 1) // page * page


koff = page
roff = koff + pages(ks)
assert not any(img[roff + pages(rs):]), "dane za ramdyskiem"
kernel = img[koff:koff + ks]


def ident(rd):
    sha = hashlib.sha1()
    for blob in (kernel, rd, b"", b"", b""):
        sha.update(blob)
        sha.update(struct.pack("<I", len(blob)))
    return sha.digest()


assert img[ID_OFF:ID_OFF + 20] == ident(img[roff:roff + rs]), "inny wzor id"
cpio = lzma.decompress(img[roff:roff + rs])

wpisy = []  # (pola, nazwa, dane)
pos = 0
while True:
    h = cpio[pos:pos + 110]
    assert h[:6] == b"070701", (pos, h[:6])
    f = [int(h[6 + 8 * i:14 + 8 * i], 16) for i in range(13)]
    namesize, filesize = f[11], f[6]
    name_end = pos + 110 + namesize
    name = cpio[pos + 110:name_end - 1].decode()
    data_off = (name_end + 3) & ~3
    wpisy.append((f, name, cpio[data_off:data_off + filesize]))
    pos = (data_off + filesize + 3) & ~3
    if name == "TRAILER!!!":
        break

po_nazwie = {n: (f, d) for f, n, d in wpisy}
S_IFMT, S_IFLNK, S_IFDIR = 0o170000, 0o120000, 0o040000


def rzeczywista(sciezka):
    # rozwiaz dowiazania w kolejnych skladnikach (lib -> usr/lib)
    czesci, wynik = sciezka.split("/"), []
    for c in czesci:
        kand = "/".join(wynik + [c])
        f = po_nazwie.get(kand)
        if f and (f[0][1] & S_IFMT) == S_IFLNK:
            cel = f[1].decode()
            wynik = cel.strip("/").split("/") if cel.startswith("/") else wynik + cel.split("/")
        else:
            wynik.append(c)
    return "/".join(wynik)


katalog = rzeczywista("lib/firmware")
wzor = next(f for f, n, d in wpisy if n == "init")  # czas i wlasciciel jak u /init
ino = max(f[0] for f, n, d in wpisy) + 1
nowe = []


def wpis(nazwa, tryb, dane, nlink):
    global ino
    f = list(wzor)
    f[0], f[1], f[4], f[6], f[11] = ino, tryb, nlink, len(dane), len(nazwa) + 1
    f[2] = f[3] = 0
    ino += 1
    nowe.append((f, nazwa, dane))


czesci = katalog.split("/")
for i in range(1, len(czesci) + 1):
    k = "/".join(czesci[:i])
    if k not in po_nazwie:
        wpis(k, S_IFDIR | 0o755, b"", 2)
for p in pliki:
    nazwa = katalog + "/" + os.path.basename(p)
    assert nazwa not in po_nazwie, nazwa + " juz jest"
    wpis(nazwa, 0o100644, open(p, "rb").read(), 1)


def pad4(buf):
    buf += b"\0" * (-len(buf) % 4)


out = bytearray()
for f, name, data in wpisy[:-1] + nowe + wpisy[-1:]:
    out += b"070701" + b"".join(b"%08X" % v for v in f) + name.encode() + b"\0"
    pad4(out)
    out += data
    pad4(out)
out += b"\0" * (-len(out) % 512)
rd = lzma.compress(bytes(out), format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC32,
                   preset=9 | lzma.PRESET_EXTREME)

hdr = bytearray(img[:page])
struct.pack_into("<I", hdr, 16, len(rd))
hdr[ID_OFF:ID_OFF + 32] = ident(rd) + b"\0" * 12
new = bytes(hdr) + kernel + b"\0" * (pages(ks) - ks) + rd
assert len(new) <= len(img), "ramdysk nie miesci sie w obrazie"
new += b"\0" * (len(img) - len(new))
open(dst, "wb").write(new)
print("katalog %s, nowe wpisy: %s; ramdysk %d -> %d B" % (
    katalog, ", ".join(n for _, n, _ in nowe), rs, len(rd)))
