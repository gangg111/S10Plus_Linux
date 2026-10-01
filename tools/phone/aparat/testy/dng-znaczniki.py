#!/usr/bin/python3
# Wypisuje znaczniki IFD0 pliku DNG (TIFF little endian) bez zadnych bibliotek:
# identyfikator, typ, liczba i wartosci (wymierne jako ulamki dziesietne).
# Uzycie: dng-znaczniki.py plik.dng
import struct
import sys

ROZMIAR = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 10: 8}

with open(sys.argv[1], "rb") as f:
    dane = f.read(1 << 20)
assert dane[:4] == b"II*\0", "to nie TIFF little endian"
ifd = struct.unpack_from("<I", dane, 4)[0]
n = struct.unpack_from("<H", dane, ifd)[0]
for i in range(n):
    tag, typ, ile, war = struct.unpack_from("<HHII", dane, ifd + 2 + 12 * i)
    dl = ROZMIAR.get(typ, 1) * ile
    off = ifd + 2 + 12 * i + 8 if dl <= 4 else war
    if typ == 2:
        v = dane[off:off + ile - 1].decode(errors="replace")
    elif typ == 1:
        v = list(dane[off:off + ile])
    elif typ == 3:
        v = list(struct.unpack_from("<%dH" % ile, dane, off))
    elif typ == 4:
        v = list(struct.unpack_from("<%dI" % ile, dane, off))
    else:
        f = "<%di" if typ == 10 else "<%dI"
        p = struct.unpack_from(f % (2 * ile), dane, off)
        v = [round(p[k] / p[k + 1], 4) if p[k + 1] else None for k in range(0, len(p), 2)]
    print(tag, typ, ile, v)
