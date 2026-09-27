#!/usr/bin/env python3
"""Wstrzykuje metadane HDR10+ (SMPTE ST 2094-40) do strumienia HEVC Annex B.

x265 w Alpine jest zbudowany bez HDR10+ (brak --dhdr10-info), wiec metadane
z pliku JSON (format x265/hdr10plus_tool, pole SceneInfo) ida jako prefiksowy
SEI user_data_registered_itu_t_t35 przed pierwszym plastrem kazdej klatki.
Serializacja jak av_dynamic_hdr_plus_to_t35 w FFmpeg (CTA-861-H).

Uzycie: wstrzyknij_hdr10plus.py <we.hevc> <meta.json> <wy.hevc>
"""
import json
import sys


class Bity:
    def __init__(self):
        self.b = bytearray()
        self.akt = 0
        self.n = 0

    def pisz(self, n, v):
        assert 0 <= v < (1 << n), (n, v)
        for i in range(n - 1, -1, -1):
            self.akt = (self.akt << 1) | ((v >> i) & 1)
            self.n += 1
            if self.n == 8:
                self.b.append(self.akt)
                self.akt = self.n = 0

    def bajty(self):
        if self.n:
            self.b.append(self.akt << (8 - self.n))
            self.akt = self.n = 0
        return bytes(self.b)


def t35(scena):
    lp = scena['LuminanceParameters']
    b = Bity()
    b.pisz(8, 0xB5)                    # itu_t_t35_country_code
    b.pisz(16, 0x003C)                 # terminal_provider_code (Samsung)
    b.pisz(16, 0x0001)                 # terminal_provider_oriented_code
    b.pisz(8, 4)                       # application_identifier
    b.pisz(8, 1)                       # application_mode / wersja
    b.pisz(2, 1)                       # num_windows
    b.pisz(27, scena['TargetedSystemDisplayMaximumLuminance'])
    b.pisz(1, 0)                       # targeted_system_display_actual_peak_luminance_flag
    for v in lp['MaxScl']:
        b.pisz(17, v)
    b.pisz(17, lp['AverageRGB'])
    idx = lp['LuminanceDistributions']['DistributionIndex']
    wart = lp['LuminanceDistributions']['DistributionValues']
    b.pisz(4, len(idx))
    for p, v in zip(idx, wart):
        b.pisz(7, p)
        b.pisz(17, v)
    b.pisz(10, 0)                      # fraction_bright_pixels
    b.pisz(1, 0)                       # mastering_display_actual_peak_luminance_flag
    bz = scena['BezierCurveData']
    b.pisz(1, 1)                       # tone_mapping_flag
    b.pisz(12, bz['KneePointX'])
    b.pisz(12, bz['KneePointY'])
    b.pisz(4, len(bz['Anchors']))
    for a in bz['Anchors']:
        b.pisz(10, a)
    b.pisz(1, 0)                       # color_saturation_mapping_flag
    return b.bajty()


def ochrona(rbsp):
    """Ochrona przed emulacja kodu startu (0x000003)."""
    wy = bytearray()
    zera = 0
    for x in rbsp:
        if zera >= 2 and x <= 3:
            wy.append(3)
            zera = 0
        wy.append(x)
        zera = zera + 1 if x == 0 else 0
    return bytes(wy)


def sei(ladunek):
    m = bytearray()
    typ, rozm = 4, len(ladunek)        # user_data_registered_itu_t_t35
    while typ >= 255:
        m.append(255)
        typ -= 255
    m.append(typ)
    while rozm >= 255:
        m.append(255)
        rozm -= 255
    m.append(rozm)
    m += ladunek
    m.append(0x80)                     # rbsp_trailing_bits
    return bytes([39 << 1, 1]) + ochrona(bytes(m))   # PREFIX_SEI_NUT, tid 0


def nale(dane):
    i, n, poz = 0, len(dane), []
    while i < n - 3:
        if dane[i] == 0 and dane[i + 1] == 0 and dane[i + 2] == 1:
            poz.append(i + 3)
            i += 3
        else:
            i += 1
    for k, p in enumerate(poz):
        koniec = poz[k + 1] - 3 if k + 1 < len(poz) else n
        while koniec > p and dane[koniec - 1] == 0:
            koniec -= 1
        yield dane[p:koniec]


def main():
    we = open(sys.argv[1], 'rb').read()
    sceny = json.load(open(sys.argv[2]))['SceneInfo']
    wy = bytearray()
    klatka = 0
    for nal in nale(we):
        typ = (nal[0] >> 1) & 0x3f
        if typ < 32 and (nal[2] & 0x80):       # plaster VCL, first_slice_segment_in_pic_flag
            s = sceny[min(klatka, len(sceny) - 1)]
            wy += b'\x00\x00\x00\x01' + sei(t35(s))
            klatka += 1
        wy += b'\x00\x00\x00\x01' + nal
    open(sys.argv[3], 'wb').write(wy)
    print('klatek z HDR10+:', klatka)


if __name__ == '__main__':
    main()
