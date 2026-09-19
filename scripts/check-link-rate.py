#!/usr/bin/env python3
"""Predkosc lacza, ktora wyliczy host DSI, musi istniec w tablicy timingow D-PHY.

Ta bramka powstala po tym, jak audyt cytowan znalazl blad, ktorego NIE widzi
zadna inna: po przejsciu na samsung-dsim host liczyl predkosc lacza z zegara
pikseli i NIESKOMPRESOWANYCH 24 bitow na piksel, ignorujac DSC. Wychodzilo
1592 Mbps, a sterownik D-PHY ma wiersz timingow wylacznie dla 898 Mbps, wiec
.validate odrzucalby kazde zadanie, PLL nigdy by sie nie skonfigurowal i ekran
nigdy by nie ruszyl. Wszystko kompilowalo sie czysto, checkpatch byl zielony,
dt-validate nie mial zastrzezen, a DTB zgadzal sie z wzorcem.

Bramka odtwarza sciezke wyboru predkosci z samsung_dsim_enable_clock():

    burst_clk_rate jesli podane w DT, inaczej pix_clk * bpp / lanes

i sprawdza trzy rzeczy:

  1. wynik jest jedna z predkosci, dla ktorych D-PHY ma wiersz timingow,
  2. miesci sie pod max_freq wariantu,
  3. dzielnik zegara escape liczy sie z podstawy zadeklarowanej w driver_data.

Exit 0 gdy lancuch sie domyka.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIN = os.path.join(ROOT, "sources", "linux")

PHY = os.path.join(LIN, "drivers", "phy", "samsung", "phy-exynos9820-dsim.c")
DSIM = os.path.join(LIN, "drivers", "gpu", "drm", "bridge", "samsung-dsim.c")
PANEL = os.path.join(LIN, "drivers", "gpu", "drm", "panel",
                     "panel-samsung-s6e3ha9-main.c")
DTSI = os.path.join(LIN, "arch", "arm64", "boot", "dts", "exynos",
                    "exynos9820.dtsi")


def fail(msg):
    print("FAIL " + msg)
    sys.exit(1)


def read(p):
    if not os.path.exists(p):
        fail("brak %s" % p)
    return open(p, encoding="utf-8", errors="replace").read()


phy = read(PHY)
dsim = read(DSIM)
panel = read(PANEL)
dtsi = read(DTSI)

# 1. predkosci, dla ktorych PHY ma wiersz
rates = [int(x) for x in re.findall(r"\.hs_clk_rate\s*=\s*(\d+)UL?\s*,", phy)]
if not rates:
    fail("nie znalazlem ani jednego wiersza timingow w sterowniku D-PHY")

# 2. wezel DSIM: liczba linii i zadana predkosc
m = re.search(r"dsim0:\s*dsi@[0-9a-f]+\s*\{(.*?)\n\t\t\};", dtsi, re.S)
if not m:
    fail("nie znalazlem wezla dsim0 w device tree")
node = m.group(1)

mb = re.search(r"samsung,burst-clock-frequency\s*=\s*<(\d+)>", node)

# liczba linii jest wlasciwoscia peryferium, wiec czytana ze sterownika panelu
ml = re.search(r"dsi->lanes\s*=\s*(\d+)\s*;", panel)
if not ml:
    fail("nie znalazlem liczby linii w sterowniku panelu")
lanes = int(ml.group(1))

if mb:
    target = int(mb.group(1))
    zrodlo = "samsung,burst-clock-frequency z device tree"
else:
    # ta sama arytmetyka co samsung_dsim_enable_clock()
    mc = re.search(r"\.clock\s*=\s*([^,;]+),", panel)
    if not mc:
        fail("nie znalazlem zegara pikseli w trybie panelu")
    expr = re.sub(r"\s+", " ", mc.group(1))
    if re.search(r"[A-Za-z_]", expr):
        fail("zegar pikseli nie jest wyrazeniem liczbowym: %s" % expr)
    # jadro liczy na liczbach calkowitych, wiec dzielenie tez calkowite
    pix_khz = eval(expr.replace("/", "//"), {"__builtins__": {}}, {})
    mf = re.search(r"dsi->format\s*=\s*MIPI_DSI_FMT_RGB888", panel)
    bpp = 24 if mf else None
    if bpp is None:
        fail("nie znalazlem formatu piksela w sterowniku panelu")
    target = -(-(pix_khz * 1000 * bpp) // lanes)
    zrodlo = ("wyliczone z zegara pikseli %d kHz, %d bpp i %d linii, bo device "
              "tree nie podaje samsung,burst-clock-frequency"
              % (pix_khz, bpp, lanes))

if target not in rates:
    fail("host zazada %d Hz (%s), a D-PHY ma wiersze tylko dla: %s"
         % (target, zrodlo, ", ".join(str(r) for r in rates)))

# 3. sufit wariantu
blok = re.search(r"exynos9820_dsi_driver_data\s*=\s*\{(.*?)\n\};", dsim, re.S)
if not blok:
    fail("nie znalazlem driver_data wariantu 9820")
mm = re.search(r"\.max_freq\s*=\s*(\d+)\s*,", blok.group(1))
if mm:
    max_hz = int(mm.group(1)) * 1000000
    if target > max_hz:
        fail("predkosc %d Hz przekracza max_freq wariantu (%d Hz)"
             % (target, max_hz))

# 4. zegar escape liczony z podstawy zadeklarowanej w driver_data
md = re.search(r"\.esc_ref_div\s*=\s*(\d+)\s*,", blok.group(1))
div_base = int(md.group(1)) if md else 8
me = re.search(r"samsung,esc-clock-frequency\s*=\s*<(\d+)>", node)
if not me:
    fail("device tree nie podaje samsung,esc-clock-frequency")
esc_want = int(me.group(1))
ref = target // div_base
esc_div = -(-ref // esc_want)
esc_real = ref // esc_div

print("check-link-rate: lacze %d Hz (%s), wiersz D-PHY jest" % (target, zrodlo))
print("check-link-rate: escape %d Hz zadane, dzielnik %d z podstawy %d, "
      "realnie %d Hz" % (esc_want, esc_div, ref, esc_real))
