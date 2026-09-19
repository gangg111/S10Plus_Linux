#!/usr/bin/env python3
"""Kazdy PLL() w sterowniku zegarow musi dostac offset CON3, nie CON0.

Sterownik PLL rodziny samsung czyta wspolczynniki M, P i S wprost z rejestru,
na ktory wskazuje con_offset: samsung_pll0822x_recalc_rate robi
readl_relaxed(pll->con_reg), a pll->con_reg to reg_base + con_offset
(clk-pll.c:1760).  Te wspolczynniki nie leza jednak w CON0, tylko w CON3.

Dla tego SoC widac to w mapie rejestrow producenta: dla PLL_AUD0 cmucal podaje
oba wpisy, PLL_CON0_PLL_AUD0 pod 0x120 i PLL_CON3_PLL_AUD0 pod 0x12c
(sources/ds/cmucal-sfr.c:46-47), czyli CON3 = CON0 + 0xc.  Upstreamowy
clk-exynos850.c, ta sama rodzina sterownika i te same typy PLL, przekazuje
do PLL() wlasnie PLL_CON3_*.

Pierwsza wersja tego sterownika przekazywala CON0 dla wszystkich dziewieciu
PLL-i, wiec kazda odczytana z nich czestotliwosc byla liczona z zawartosci
rejestru sterujacego.  Blad nie przeszkadza w starcie, bo zegary ustawia
bootloader, a bledny jest tylko ODCZYT, i wlasnie dlatego nikt go nie zauwazyl.
Ta bramka pilnuje, zeby nie wrocil.

Sprawdza dwie rzeczy:
  1. kazde wywolanie PLL() przekazuje symbol PLL_CON3_*, nigdy PLL_CON0_*,
  2. kazdy PLL_CON3_X rowna sie PLL_CON0_X + 0xc.

Kod 0 gdy dobrze, 1 przy bledzie, 2 gdy nie ma czego sprawdzac.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRV = os.path.join(ROOT, "sources", "linux", "drivers", "clk", "samsung",
                   "clk-exynos9820.c")


def main():
    if not os.path.isfile(DRV):
        print("check-pll-con3: brak sterownika zegarow, nie mam czego sprawdzac")
        return 2

    with open(DRV, encoding="utf-8", errors="replace") as f:
        src = f.read()

    con0 = {}
    con3 = {}
    for m in re.finditer(r"^#define\s+PLL_CON0_([A-Z0-9_]+)\s+(0x[0-9a-fA-F]+)",
                         src, re.M):
        con0[m.group(1)] = int(m.group(2), 16)
    for m in re.finditer(r"^#define\s+PLL_CON3_([A-Z0-9_]+)\s+(0x[0-9a-fA-F]+)",
                         src, re.M):
        con3[m.group(1)] = int(m.group(2), 16)

    # Wywolania PLL(...) potrafia byc lamane na kilka wierszy.
    wywolania = re.findall(r"\bPLL\(\s*pll_[0-9a-zA-Z]+\s*,(.*?)\)\s*,",
                           src, re.S)
    if not wywolania:
        print("check-pll-con3: nie znalazlem zadnego wywolania PLL()")
        return 2

    bad = []
    n_con3 = 0
    for w in wywolania:
        uzyte = re.findall(r"PLL_CON([03])_([A-Z0-9_]+)", w)
        if not uzyte:
            bad.append("wywolanie PLL() bez rozpoznanego offsetu: %s"
                       % " ".join(w.split())[:70])
            continue
        for numer, nazwa in uzyte:
            if numer == "0":
                bad.append("PLL(%s) dostaje PLL_CON0_%s, a M/P/S sa w CON3"
                           % (nazwa, nazwa))
            else:
                n_con3 += 1

    # Kazdy CON3 ma byc dokladnie CON0 + 0xc.
    n_par = 0
    for nazwa, off3 in sorted(con3.items()):
        if nazwa not in con0:
            bad.append("PLL_CON3_%s nie ma odpowiednika PLL_CON0_%s"
                       % (nazwa, nazwa))
            continue
        n_par += 1
        if off3 != con0[nazwa] + 0xc:
            bad.append("PLL_CON3_%s = 0x%x, a PLL_CON0_%s + 0xc = 0x%x"
                       % (nazwa, off3, nazwa, con0[nazwa] + 0xc))

    for b in bad:
        print("  FAIL %s" % b)
    print("check-pll-con3: wywolan PLL() z CON3 %d, par CON0/CON3 %d, bledow %d"
          % (n_con3, n_par, len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
