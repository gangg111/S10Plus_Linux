#!/usr/bin/env python3
"""Zamienia surowy zrzut bufora ramki na PNG, bez bibliotek zewnetrznych.

Po co: jedynym uczciwym dowodem na to, co widac na telefonie, jest zawartosc
bufora ramki, a ta przychodzi jako surowe piksele. Pillow na tej maszynie nie
jest wymagany, a PNG da sie zlozyc samym zlib z biblioteki standardowej.

Uzycie:
  raw-na-png.py <plik.raw> <plik.png> <szerokosc> <wysokosc> [dlugosc_wiersza]

Zaklada 32 bity na piksel. Kolejnosc kanalow: niebieski, zielony, czerwony,
nieuzywany, czyli uklad, ktory daje sterownik drm dla XRGB8888 na tej maszynie.
"""
import struct
import sys
import zlib


def png(sciezka, szer, wys, wiersze):
    """Sklada plik PNG z gotowych wierszy RGB."""
    def kawalek(typ, dane):
        return (struct.pack(">I", len(dane)) + typ + dane +
                struct.pack(">I", zlib.crc32(typ + dane) & 0xffffffff))

    naglowek = struct.pack(">IIBBBBB", szer, wys, 8, 2, 0, 0, 0)
    surowe = b"".join(b"\x00" + w for w in wiersze)

    with open(sciezka, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(kawalek(b"IHDR", naglowek))
        f.write(kawalek(b"IDAT", zlib.compress(surowe, 6)))
        f.write(kawalek(b"IEND", b""))


def main():
    if len(sys.argv) < 5:
        sys.exit(__doc__)

    wejscie, wyjscie = sys.argv[1], sys.argv[2]
    szer, wys = int(sys.argv[3]), int(sys.argv[4])
    dlugosc = int(sys.argv[5]) if len(sys.argv) > 5 else szer * 4

    dane = open(wejscie, "rb").read()
    potrzeba = dlugosc * wys
    if len(dane) < potrzeba:
        sys.exit("plik ma %d bajtow, a przy %d wierszach po %d potrzeba %d"
                 % (len(dane), wys, dlugosc, potrzeba))

    wiersze = []
    for y in range(wys):
        p = dane[y * dlugosc:y * dlugosc + szer * 4]
        # Z czterech bajtow piksela bierzemy trzy i odwracamy kolejnosc.
        wiersze.append(bytes(b for i in range(0, szer * 4, 4)
                             for b in (p[i + 2], p[i + 1], p[i])))

    png(wyjscie, szer, wys, wiersze)
    print("zapisane %s, %dx%d" % (wyjscie, szer, wys))


if __name__ == "__main__":
    main()
