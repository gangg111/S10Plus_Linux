#!/usr/bin/env python3
"""Zaden PLL tego SoC nie moze byc rejestrowany jako PLL.

Okno rejestrow PLL w CMU_TOP jest ZAMKNIETE: odczyt konczy sie synchronicznym
abortem zewnetrznym.  Zmierzone dwa razy, niezaleznie od siebie:

  19.09.2026, bootloader: esr 0x96000010, far 0x1a24010c (apll_shared0).
    Okna muxow (0x10xx), dzielnikow (0x18xx) i bramek (0x20xx) TEGO SAMEGO
    bloku czytaja sie bez zarzutu, wiec nie chodzi o caly CMU, tylko o samo
    okno PLL.  Cokolwiek chodzi przed nami, zostawia je sobie.
  21.09.2026, jadro: panika w samsung_pll0822x_recalc_rate wolanym
    z __clk_register przy rejestracji CMU_TOP.  Ten sam kod bledu, ten sam
    rejestr, telefon nie wstaje.

Rejestracja przez PLL() ZAWSZE konczy sie odczytem, bo rdzen wola recalc_rate,
zeby poznac czestotliwosc poczatkowa.  Nie da sie wiec zarejestrowac tych
zegarow jako PLL i nie dotknac zamknietego okna.  Dlatego ida jako stale
czestotliwosci, wziete z tablic CAL producenta, gdzie kazdy z nich ma
dokladnie jeden wpis, czyli sa to stale konstrukcyjne.

Ta bramka zastapila poprzednia, ktora pilnowala, zeby PLL() dostawal offset
CON3 zamiast CON0.  Tamta bronila poprawnego ODCZYTU rejestru, ktorego, jak
sie okazalo, przeczytac sie nie da.  Zostala tu jej czesc arytmetyczna, bo
definicje offsetow nadal opisuja sprzet i nadal maja byc poprawne.

Sprawdza trzy rzeczy:
  1. sterownik nie ma ANI JEDNEGO wywolania PLL(),
  2. kazdy zegar z listy stalych jest w sterowniku jako FRATE z dokladnie ta
     czestotliwoscia, ktora ma nasz bootloader dzialajacy na tym telefonie,
  3. kazdy PLL_CON3_X, ktory w sterowniku zostal, rowna sie PLL_CON0_X + 0xc.

Kod 0 gdy dobrze, 1 przy bledzie, 2 gdy nie ma czego sprawdzac.
"""
import os
import re
import sys

GATE = "check-pll-con3"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, "sources", "linux", "drivers", "clk", "samsung",
                      "clk-exynos9820.c")

# Te same liczby, ktore jezdza w naszym bootloaderze (drivers/clk/exynos/
# clk-exynos9820.c, tablice *_frate_clks) i z ktorymi telefon startuje.
STALE = {
    "fout_apll_shared0": 2132000000,
    "fout_apll_shared1": 1865500032,
    "fout_pll_g3d":       650000000,
    "fout_pll_shared0":  2132000000,
    "fout_pll_shared1":  1865500032,
    "fout_pll_shared2":   800000000,
    "fout_pll_shared3":   640000000,
    "fout_pll_shared4":   666000000,
    "fout_pll_mmc":        26000000,
}


def main():
    if not os.path.isfile(DRIVER):
        print("%s: BRAMKA NIEURUCHOMIONA, brak %s" % (GATE, DRIVER))
        return 2

    with open(DRIVER, encoding="utf-8") as f:
        tresc = f.read()

    zle = 0

    # 1. Zadnego PLL().
    plle = re.findall(r"^\tPLL\(", tresc, re.M)
    if plle:
        print("%s: sterownik ma %d wywolan PLL(), a nie moze miec ani jednego:"
              " okno rejestrow PLL nie odpowiada na odczyt i rejestracja"
              " konczy sie abortem przy starcie" % (GATE, len(plle)))
        zle += 1

    # 2. Stale czestotliwosci zgodne z bootloaderem.
    frate = dict()
    for nazwa, hz in re.findall(
            r'FRATE\([A-Z0-9_]+,\s*"([a-z0-9_]+)",\s*NULL,\s*0,\s*(\d+)\)',
            tresc):
        frate[nazwa] = int(hz)

    for nazwa, hz in sorted(STALE.items()):
        if nazwa not in frate:
            print("%s: brak stalej czestotliwosci dla %s" % (GATE, nazwa))
            zle += 1
        elif frate[nazwa] != hz:
            print("%s: %s ma %d Hz, a bootloader uzywa %d Hz"
                  % (GATE, nazwa, frate[nazwa], hz))
            zle += 1

    # 3. Arytmetyka offsetow, ktore w sterowniku zostaly.
    con0 = dict(re.findall(r"#define PLL_CON0_(\w+)\s+0x([0-9a-fA-F]+)", tresc))
    con3 = dict(re.findall(r"#define PLL_CON3_(\w+)\s+0x([0-9a-fA-F]+)", tresc))
    sprawdzonych = 0
    for nazwa, wart in sorted(con3.items()):
        if nazwa not in con0:
            continue
        sprawdzonych += 1
        if int(wart, 16) != int(con0[nazwa], 16) + 0xc:
            print("%s: PLL_CON3_%s = 0x%s, a PLL_CON0_%s + 0xc = 0x%x"
                  % (GATE, nazwa, wart, nazwa, int(con0[nazwa], 16) + 0xc))
            zle += 1

    if zle:
        return 1

    print("%s: wywolan PLL() 0, stalych czestotliwosci %d zgodnych"
          " z bootloaderem, par offsetow sprawdzonych %d"
          % (GATE, len(STALE), sprawdzonych))
    return 0


sys.exit(main())
