#!/usr/bin/env python3
"""Bramka: zegar nie moze byc rejestrowany przed swoim rodzicem.

Po co ona istnieje. clk_register (drivers/clk/clk.c:24) szuka rodzica PO NAZWIE
w chwili rejestracji, a gdy go nie znajdzie, NIE PRZERYWA: loguje blad i wiaze
zegar z rodzicem NULL. Taki zegar wyglada potem na dzialajacy, tylko jego
czestotliwosc jest policzona z kodu bledu.

Tak wlasnie padlo lacze UFS na tym telefonie. W CMU_TOP sciezka CLKCMU biegnie
mux, potem bramka, potem dzielnik, a grupy byly rejestrowane po typach
w kolejnosci PLL, MUX, DIV, GATE. Dzielnik dout_cmu_fsys1_ufs_embd powstawal
wiec przed swoja bramka i zwracal DIV_ROUND_UP(-ENODEV, 2), czyli
0x7ffffffffffffff7. Sterownik UFS wzial to za czestotliwosc zegara UniPro
i policzyl z niej wszystkie okresy PCS oraz UniPro. Objawem byly cztery
przekroczenia czasu UIC i "link startup failed -110", czyli komunikat
wskazujacy zupelnie gdzie indziej.

Bramka odtwarza kolejnosc rejestracji z samego zrodla: dla kazdego CMU bierze
jego tablice grup i idzie po nich tak, jak zrobi to samsung_cmu_register_one.
CMU_TOP jest zawsze pierwszy, bo wymusza to makro samsung_register_cmu.

Uzycie:  scripts/check-uboot-clk-order.py
Kod:     0 kolejnosc poprawna, 1 zegar przed rodzicem, 2 bramka NIEURUCHOMIONA
"""

import os
import re
import sys
from pathlib import Path

def _domyslne_drzewo():
    """Gdzie lezy drzewo bootloadera, gdy nikt nie powiedzial tego wprost.

    Python z MSYS2, ktorym verify.sh uruchamia te bramke, nie dostaje HOME
    i `Path.home()` rzuca wtedy RuntimeError, przez co bramka wywala sie
    sladem stosu, zamiast powiedziec, ze nie ma zrodla. Drzewo i tak zyje
    pod WSL, wiec ta sciezka jest sprawdzana jako pierwsza.
    """
    wsl = Path("//wsl.localhost/Debian/home/pm/u-boot-upstream")
    if wsl.is_dir():
        return wsl

    try:
        return Path.home() / "u-boot-upstream"
    except RuntimeError:
        return wsl


UBOOT = Path(os.environ["UBOOT_TREE"]) if os.environ.get("UBOOT_TREE") \
    else _domyslne_drzewo()
ZRODLO = UBOOT / "drivers/clk/exynos/clk-exynos9820.c"

# CMU_TOP rejestruje sie pierwszy, bo samsung_register_cmu wymusza jego
# obecnosc, zanim zarejestruje cokolwiek innego.
PIERWSZY = "top"

TYPY = {
    "S_CLK_PLL": "pll",
    "S_CLK_MUX": "mux",
    "S_CLK_DIV": "div",
    "S_CLK_GATE": "gate",
    # Enum nazywa sie S_CLK_FRATE; druga nazwa zostaje na wypadek zmiany w gorze.
    "S_CLK_FRATE": "frate",
    "S_CLK_FIXED_RATE": "frate",
}


def bez_komentarzy(tekst):
    return re.sub(r"/\*.*?\*/", " ", tekst, flags=re.S)


def tablica(src, nazwa):
    """Zwraca tresc tablicy inicjalizatorow o podanej nazwie."""
    m = re.search(r"\b" + re.escape(nazwa) + r"\[\]\s*=\s*\{(.*?)\n\};", src, re.S)
    return bez_komentarzy(m.group(1)) if m else None


def listy_rodzicow(src):
    """PNAME(x) = { "a", "b" } -> {'x': ['a', 'b']}, z rozwinieciem makr."""
    makra = dict(re.findall(r'#define\s+(\w+)\s+"([^"]+)"', src))
    wynik = {}
    for nazwa, tresc in re.findall(r"PNAME\((\w+)\)\s*=\s*\{([^}]*)\}", src):
        elementy = []
        for e in (x.strip() for x in tresc.split(",")):
            if not e:
                continue
            elementy.append(e.strip('"') if e.startswith('"') else makra.get(e, e))
        wynik[nazwa] = elementy
    return wynik


src_globalny = ""


def wpisy(tresc, rodzaj, pnames):
    """Lista (nazwa, [rodzice]) w kolejnosci wystapienia w tablicy."""
    wynik = []
    if rodzaj == "frate":
        for nazwa in re.findall(r'FRATE\(\s*[^,]+,\s*"([^"]+)"', tresc):
            wynik.append((nazwa, []))
        return wynik

    if rodzaj == "mux":
        wzor = r'MUX(?:_F)?\(\s*[^,]+,\s*"([^"]+)",\s*(\w+)'
        for nazwa, lista in re.findall(wzor, tresc):
            wynik.append((nazwa, pnames.get(lista, [])))
        return wynik

    if rodzaj == "pll":
        # PLL(_typ, _id, _name, _pname, _con): nazwa jest TRZECIM argumentem,
        # a rodzic bywa podany makrem (OSCCLK), nie lancuchem.
        makra = dict(re.findall(r'#define\s+(\w+)\s+"([^"]+)"', src_globalny))
        wzor = r'PLL\(\s*\w+,\s*[^,]+,\s*"([^"]+)",\s*(?:"([^"]*)"|(\w+))'
        for nazwa, rodzic_str, rodzic_sym in re.findall(wzor, tresc):
            rodzic = rodzic_str or makra.get(rodzic_sym, rodzic_sym)
            wynik.append((nazwa, [rodzic] if rodzic else []))
        return wynik

    slowo = {"div": "DIV", "gate": "GATE"}[rodzaj]
    wzor = slowo + r'(?:_F)?\(\s*[^,]+,\s*"([^"]+)",\s*"([^"]*)"'
    for nazwa, rodzic in re.findall(wzor, tresc):
        wynik.append((nazwa, [rodzic] if rodzic else []))
    return wynik


def kolejnosc_cmu(src, cmu, pnames):
    """Zegary jednego CMU w tej kolejnosci, w ktorej beda rejestrowane."""
    grupy = tablica(src, cmu + "_cmu_clks")
    if grupy is None:
        return None

    wynik = []
    for typ, nazwa_tablicy in re.findall(r"\{\s*(S_CLK_\w+),\s*(\w+),", grupy):
        rodzaj = TYPY.get(typ)
        if not rodzaj:
            continue
        tresc = tablica(src, nazwa_tablicy)
        if tresc is None:
            continue
        wynik.extend(wpisy(tresc, rodzaj, pnames))
    return wynik


def main():
    if not ZRODLO.exists():
        print(f"check-uboot-clk-order: BRAMKA NIEURUCHOMIONA, brak {ZRODLO}")
        return 2

    global src_globalny
    src = bez_komentarzy(ZRODLO.read_text())
    src_globalny = ZRODLO.read_text()
    pnames = listy_rodzicow(ZRODLO.read_text())

    cmus = sorted(set(re.findall(r"(\w+)_cmu_clks\[\]", src)))
    if PIERWSZY not in cmus:
        print(f"check-uboot-clk-order: BRAMKA NIEURUCHOMIONA, brak {PIERWSZY}_cmu_clks")
        return 2
    cmus = [PIERWSZY] + [c for c in cmus if c != PIERWSZY]

    zarejestrowane = set()
    zle = []
    razem = 0

    for cmu in cmus:
        lista = kolejnosc_cmu(src, cmu, pnames)
        if lista is None:
            print(f"check-uboot-clk-order: BRAMKA NIEURUCHOMIONA, brak grup dla {cmu}")
            return 2
        for nazwa, rodzice in lista:
            for rodzic in rodzice:
                # zegary spoza tego pliku (oscylator plyty) nie sa tu rejestrowane
                if not rodzic.startswith(("mout_", "dout_", "gout_", "fout_")):
                    continue
                if rodzic not in zarejestrowane:
                    zle.append((cmu, nazwa, rodzic))
            zarejestrowane.add(nazwa)
            razem += 1

    if zle:
        print(f"check-uboot-clk-order: {len(zle)} zegarow rejestrowanych PRZED rodzicem")
        for cmu, nazwa, rodzic in zle:
            print(f"  CMU {cmu}: {nazwa} wisi na {rodzic}, ktorego jeszcze nie ma")
        print("  clk_register zwiaze je z rodzicem NULL i ich czestotliwosc")
        print("  bedzie policzona z kodu bledu, bez ani jednego komunikatu")
        return 1

    print(f"check-uboot-clk-order: kolejnosc poprawna, zegarow {razem} "
          f"w {len(cmus)} CMU")
    return 0


if __name__ == "__main__":
    sys.exit(main())
