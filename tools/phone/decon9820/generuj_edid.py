#!/usr/bin/env python3
"""EDID panelu S6E3HA9 (Galaxy S10+) dla sterownika decon9820.

Blok podstawowy 1.4: producent SDC, rozmiar 69 x 147 mm, gamma 2,2, prymarne
Display P3 (natywny gamut panelu, flaga sRGB wylaczona, wiec KWin bierze
kolorymetrie z EDID), tryb 1440x3040@60. Rozszerzenie CTA-861 z blokiem HDR
static metadata: tylko krzywa SDR (bez PQ i BT.2020, ktorych panel nie
dekoduje), luminancje: szczyt 800 nitow (HBM), srednia klatki 420 (maks. SDR),
minimum ~0,0005 (AMOLED).

Wyjscie: plik .bin i naglowek C z tablica.
"""
import math
import sys


def chrom10(v):
    return int(round(v * 1024))


def baza():
    e = bytearray(128)
    e[0:8] = bytes([0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00])
    m = ((ord('S') - 64) << 10) | ((ord('D') - 64) << 5) | (ord('C') - 64)
    e[8], e[9] = m >> 8, m & 0xff
    e[10], e[11] = 0xa9, 0x39          # kod produktu (S6E3HA9)
    e[16], e[17] = 0, 2019 - 1990      # rok produkcji
    e[18], e[19] = 1, 4                # EDID 1.4
    e[20] = 0x80 | (0b010 << 4)        # cyfrowe, 8 bitow na kolor
    e[21], e[22] = 7, 15               # cm
    e[23] = 120                        # gamma 2,2
    e[24] = 0x02                       # RGB 4:4:4, bez sRGB, preferowany tryb natywny
    r, g, b, w = (0.680, 0.320), (0.265, 0.690), (0.150, 0.060), (0.3127, 0.3290)
    rx, ry, gx, gy, bx, by, wx, wy = (chrom10(v) for v in (*r, *g, *b, *w))
    e[25] = ((rx & 3) << 6) | ((ry & 3) << 4) | ((gx & 3) << 2) | (gy & 3)
    e[26] = ((bx & 3) << 6) | ((by & 3) << 4) | ((wx & 3) << 2) | (wy & 3)
    e[27:35] = bytes(v >> 2 for v in (rx, ry, gx, gy, bx, by, wx, wy))
    e[38:54] = bytes([0x01, 0x01] * 8)
    # Szczegolowy tryb: 1440x3040@60 z niewielkim wygaszaniem (tylko opis).
    ha, va, hb, vb, hso, hsw, vso, vsw = 1440, 3040, 32, 8, 8, 8, 2, 2
    zegar = round(60 * (ha + hb) * (va + vb) / 10000)
    d = bytearray(18)
    d[0], d[1] = zegar & 0xff, zegar >> 8
    d[2], d[3] = ha & 0xff, hb & 0xff
    d[4] = ((ha >> 8) << 4) | (hb >> 8)
    d[5], d[6] = va & 0xff, vb & 0xff
    d[7] = ((va >> 8) << 4) | (vb >> 8)
    d[8], d[9] = hso & 0xff, hsw & 0xff
    d[10] = ((vso & 0xf) << 4) | (vsw & 0xf)
    d[11] = ((hso >> 8) << 6) | ((hsw >> 8) << 4) | ((vso >> 4) << 2) | (vsw >> 4)
    d[12], d[13] = 69 & 0xff, 147 & 0xff
    d[14] = ((69 >> 8) << 4) | (147 >> 8)
    d[17] = 0x18                       # cyfrowy, oddzielna synchronizacja
    e[54:72] = d
    nazwa = b'S6E3HA9 S10+'
    e[72:90] = bytes([0, 0, 0, 0xfc, 0]) + (nazwa + b'\n').ljust(13, b' ')
    e[90:108] = bytes([0, 0, 0, 0x10, 0]) + bytes(13)
    e[108:126] = bytes([0, 0, 0, 0x10, 0]) + bytes(13)
    e[126] = 1
    e[127] = (-sum(e[:127])) & 0xff
    return e


def cta():
    e = bytearray(128)
    e[0], e[1] = 0x02, 0x03
    maks = round(32 * math.log2(800 / 50))
    srednia = round(32 * math.log2(420 / 50))
    minimum = 2
    blok = bytes([0x06, 0x01, 0x01, maks, srednia, minimum])   # ext tag 6: HDR static metadata
    vcdb = bytes([0x00, 0x4a])                                  # ext tag 0: VCDB, RGB wybieralna, IT i CE bez overscanu
    dane = bytes([(7 << 5) | len(vcdb)]) + vcdb + bytes([(7 << 5) | len(blok)]) + blok
    e[4:4 + len(dane)] = dane
    e[2] = 4 + len(dane)
    e[3] = 0x80                                                 # obraz bez overscanu (underscan)
    e[127] = (-sum(e[:127])) & 0xff
    return e


def main():
    edid = bytes(baza() + cta())
    assert len(edid) == 256 and sum(edid[:128]) % 256 == 0 and sum(edid[128:]) % 256 == 0
    open(sys.argv[1], 'wb').write(edid)
    wiersze = ['/* Wygenerowane przez generuj_edid.py; szczegoly tam. */',
               'static const u8 decon9820_edid[256] = {']
    for i in range(0, 256, 12):
        wiersze.append('\t' + ' '.join('0x%02x,' % x for x in edid[i:i + 12]))
    wiersze.append('};')
    open(sys.argv[2], 'w', newline='\n').write('\n'.join(wiersze) + '\n')
    print('ok', len(edid))


if __name__ == '__main__':
    main()
