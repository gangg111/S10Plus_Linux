#!/usr/bin/env python3
"""Porównuje tablice AID dimming w sterowniku panelu z tablicami producenta.

Czyta wiersze `s6e3ha9_brightness_table[]` ze sterownika i zestawia je
z `beyond2_a3_s0_{aor,elvss,vint}_table` (s6e3ha9_beyond2_a3_s0_panel.h)
oraz `beyond2_a3_s0_{brt,lum}_tbl` (…_panel_dimming.h).
"""
import re, sys

DRV = sys.argv[1] if len(sys.argv) > 1 else \
    "sources/linux/drivers/gpu/drm/panel/panel-samsung-s6e3ha9-main.c"
PANEL = "sources/ds/s6e3ha9_beyond2_a3_s0_panel.h"
DIM = "sources/ds/beyond2_dimming.h"

def body(text, decl):
    i = text.index(decl)
    return text[i:text.index('\n};', i)]

def hexes(text, decl):
    b = body(text, decl)
    b = re.sub(r'/\*.*?\*/', ' ', b, flags=re.S)
    b = re.sub(r'//[^\n]*', ' ', b)
    return [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{1,2})', b)]

panel = open(PANEL, encoding='utf8', errors='replace').read()
dim = open(DIM, encoding='utf8', errors='replace').read()

aor = hexes(panel, 'static u8 beyond2_a3_s0_aor_table[')
elvss = hexes(panel, 'static u8 beyond2_a3_s0_elvss_table[')[:90]
vint = hexes(panel, 'static u8 beyond2_a3_s0_vint_table[')[:90]
brt = [int(x) for x in re.findall(r'BRT\((\d+)\)', body(dim, 'static unsigned int beyond2_a3_s0_brt_tbl['))]
lum_body = re.sub(r'/\*.*?\*/', ' ', body(dim, 'static unsigned int beyond2_a3_s0_lum_tbl['), flags=re.S)
lum = [int(x) for x in re.findall(r'\b\d+\b', lum_body.split('=', 1)[1])]

drv = open(DRV, encoding='utf8', errors='replace').read()
rows = re.findall(r'\{\s*(\d+),\s*(\d+),\s*\{\s*0x([0-9a-f]{2}),\s*0x([0-9a-f]{2})\s*\},'
                  r'\s*0x([0-9a-f]{2}),\s*0x([0-9a-f]{2})\s*\}', drv)
if not rows:
    sys.exit("nie znaleziono wierszy tablicy w sterowniku")

# Producent ma 90 wierszy: 74 dla zakresu UI i 16 dla HBM. Sterownik pokrywa
# zakres UI, wiec liczba wierszy MUSI sie zgadzac co do jednego. Bez tej
# kontroli usuniecie ostatniego wiersza przechodzilo, bo porownanie szlo
# po prefiksie.
UI_ROWS = len(brt) - 16
if len(rows) != UI_ROWS:
    sys.exit("wierszy w sterowniku: %d, oczekiwane %d (producent ma %d = %d UI + 16 HBM)"
             % (len(rows), UI_ROWS, len(brt), UI_ROWS))

bad = 0
for i, (b, n, a0, a1, el, vi) in enumerate(rows):
    want = (brt[i], lum[i], aor[2 * i], aor[2 * i + 1], elvss[i], vint[i])
    have = (int(b), int(n), int(a0, 16), int(a1, 16), int(el, 16), int(vi, 16))
    if have != want:
        bad += 1
        print(f"  ZLE wiersz {i}: sterownik {have} != producent {want}")

print(f"# wierszy w sterowniku: {len(rows)} (producent: {len(brt)} = {len(brt)-16} UI + 16 HBM)")
print(f"# zakres jasnosci: {rows[0][0]}..{rows[-1][0]}, nity {rows[0][1]}..{rows[-1][1]}")
print("\n" + ("WSZYSTKIE WIERSZE ZGODNE" if not bad else f"{bad} ROZBIEZNOSCI"))
sys.exit(1 if bad else 0)
