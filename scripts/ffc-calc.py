#!/usr/bin/env python3
"""Kalkulator słowa FFC (DCS 0xC5) dla DDI Samsung S6E3HA9.

Model wyprowadzony empirycznie z tablicy dynamicznej częstotliwości tego samego
DDI (Galaxy Note10+, davinci2), gdzie te same bajty występują dla czterech
różnych zegarów MIPI:

  LineageOS/android_kernel_samsung_exynos9820@7d08ec36:
  drivers/video/fbdev/exynos/panel/s6e3ha9/s6e3ha9_davinci2_a3_s0_panel.h:645-670

Układ ładunku (payload po opkodzie 0xC5), indeksy 0-based:
  [0] 0x0D  - sterowanie (0x08 = FFC off w wariancie dynamicznym)
  [1] 0x10  - stała
  [2] skala - 0x64 (100) w davinci2, 0xB4 (180) w beyond*
  [3][4]    - 16-bitowe słowo kompensacji, big-endian
  [5..]     - w wariancie 19-bajtowym dalsze stałe, niezależne od zegara

Model:  word = round(C * skala / f_Mbps),  C wyznaczone z punktów referencyjnych.

Użycie:  scripts/ffc-calc.py [f_Mbps] [skala_hex]     (domyślnie 898 0xB4)
"""
import sys

# (f w Mbps, słowo 16-bit, bajt skali) — wszystkie z davinci2_a3_s0_dyn_ffc_table
REF = [
    (897.0,  0x2278, 0x64),
    (903.5,  0x2239, 0x64),
    (910.0,  0x21FA, 0x64),
    (929.5,  0x2144, 0x64),
]
# punkt kontrolny: beyond1/beyond2/beyondX @ 898 Mbps (DT: timing,dsi-hs-clk = 0x382)
CHECK = (898.0, 0x3E01, 0xB4)

C = sum(w * f / s for f, w, s in REF) / len(REF)


def word(f_mbps, scale):
    return round(C * scale / f_mbps)


def main():
    f = float(sys.argv[1]) if len(sys.argv) > 1 else 898.0
    scale = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0xB4

    print(f"C (stała modelu) = {C:.1f}   [wyznaczona z {len(REF)} punktów davinci2]\n")
    print("punkty referencyjne (davinci2, skala 0x64):")
    for fr, w, s in REF:
        p = word(fr, s)
        print(f"  {fr:7.1f} Mbps: w tablicy 0x{w:04X} ({w}), model 0x{p:04X} ({p}), "
              f"błąd {p - w:+d} LSB ({(p - w) / w * 100:+.3f}%)")
    fr, w, s = CHECK
    p = word(fr, s)
    print(f"\npunkt kontrolny (beyond*, skala 0x{s:02X}):")
    print(f"  {fr:7.1f} Mbps: w panelu   0x{w:04X} ({w}), model 0x{p:04X} ({p}), "
          f"błąd {p - w:+d} LSB ({(p - w) / w * 100:+.3f}%)")

    p = word(f, scale)
    print(f"\nwynik dla f = {f} Mbps, skala 0x{scale:02X}:")
    print(f"  słowo = 0x{p:04X} ({p})")
    print(f"  pakiet 5-bajtowy (beyond*):  0xC5, 0x0D, 0x10, 0x{scale:02X}, "
          f"0x{p >> 8:02X}, 0x{p & 0xFF:02X}")


if __name__ == "__main__":
    main()
