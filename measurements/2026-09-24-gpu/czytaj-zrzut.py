#!/usr/bin/env python3
# Parser zrzutu devcoredump panfrosta (PANFROSTDUMP 1.0, uapi panfrost_drm.h).
import struct
import sys

d = open(sys.argv[1], "rb").read()
HDR = 2000  # 16 B pol stalych + unia 496 x u32
MAGIC = 0x464E4150
TYPY = {0: "REG", 1: "BOMAP", 2: "BO", 3: "TRAILER"}

naglowki = []
i = 0
while True:
    magic, typ, fsize, foff = struct.unpack_from("<IIII", d, i * HDR)
    if magic != MAGIC:
        break
    naglowki.append((i, typ, fsize, foff))
    if typ == 3:
        break
    i += 1

reg = naglowki[0]
jc, gpu_id, major, minor, _pad, nbos = struct.unpack_from("<QIIIIQ", d, 16)
print("obiektow %d, jc=0x%x gpu_id=0x%x wersja %d.%d, bo=%d" % (len(naglowki), jc, gpu_id, major, minor, nbos))
print("rejestry:")
for k in range(reg[2] // 8):
    r, v = struct.unpack_from("<II", d, reg[3] + 8 * k)
    print("  0x%04x = 0x%08x" % (r, v))

bomap_off = naglowki[1][3] if naglowki[1][1] == 1 else None
bo = []
for (n, typ, fsize, foff) in naglowki:
    if typ != 2:
        continue
    base = n * HDR + 16
    valid, = struct.unpack_from("<I", d, base)
    iova, = struct.unpack_from("<Q", d, base + 8)
    idx, = struct.unpack_from("<I", d, base + 16)
    strony = [struct.unpack_from("<Q", d, bomap_off + 8 * (idx + s))[0] for s in range(fsize // 4096)] if valid else []
    bo.append((iova, fsize, foff, valid, strony))

bo.sort()
print("\nbufory (iova, rozmiar, niezerowych bajtow):")
for iova, fsize, foff, valid, strony in bo:
    blob = d[foff:foff + fsize]
    nz = fsize - blob.count(0)
    print("  0x%010x %9d  %s  niezerowe %d  strony fiz. %s" % (
        iova, fsize, "ok" if valid else "BRAK", nz,
        ",".join("0x%x" % s for s in strony[:3]) + ("..." if len(strony) > 3 else "")))


def czytaj(va, n):
    for iova, fsize, foff, valid, strony in bo:
        if iova <= va < iova + fsize:
            o = foff + (va - iova)
            return d[o:o + n], iova
    return None, None


cel = int(sys.argv[2], 0) if len(sys.argv) > 2 else jc
blob, iova = czytaj(cel, 256)
print("\nzadanie pod 0x%x (w buforze 0x%x):" % (cel, iova if iova else 0))
if blob is None:
    print("  ADRES POZA WSZYSTKIMI BUFORAMI ZRZUTU")
    sys.exit()
w = struct.unpack_from("<8I", blob, 0)
exc, fit = w[0], w[1]
fault = w[2] | (w[3] << 32)
typ = (w[4] >> 1) & 0x7f
idx = w[4] >> 16
nast = w[6] | (w[7] << 32)
print("  exception_status 0x%08x  first_incomplete_task 0x%x  fault_pointer 0x%x" % (exc, fit, fault))
print("  typ %d  job_index %d  zaleznosci %d/%d  nastepne 0x%x" % (typ, idx, w[5] & 0xffff, w[5] >> 16, nast))
for k in range(0, 256, 32):
    print("  +%03x: %s" % (k, " ".join("%08x" % x for x in struct.unpack_from("<8I", blob, k))))
