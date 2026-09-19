#!/usr/bin/env python3
"""Model tablic CAL producenta: bloki, rejestry, pola i wezly drzewa zegarow.

Sterownik zegarow jest transkrypcja tych tablic do slownika makr mainline, wiec
zanim cokolwiek napiszemy, trzeba miec je jako dane, a nie jako tekst.  Dwa
pliki producenta niosa komplet:

  cmucal-sfr.c   SFR_BLOCK(nazwa, baza, rozmiar)          gdzie stoi blok
                 SFR(nazwa, offset, blok)                  gdzie stoi rejestr
                 SFR_ACCESS(pole, shift, width, rejestr)   gdzie stoi pole

  cmucal-node.c  CLK_MUX(id, tablica_rodzicow, SELECT, BUSY, AUTOGATE)
                 CLK_DIV(id, rodzic, DIVRATIO, BUSY, AUTOGATE)
                 CLK_GATE(id, rodzic, CG_VAL, MANUAL, AUTOGATE)
                 CLK_PLL(typ, id, rodzic, LOCKTIME, ENABLE, STABLE, P, M, S, K, tablica, ...)
                 enum clk_id <nazwa>_parents[] = { ... }

Uruchomiony bez argumentow wypisuje pokrycie: ile wezlow rozwiazuje sie do
kompletu (offset, shift, width) i ile ma luki.  To jest miara tego, czy
sterownik da sie WYGENEROWAC, czy trzeba go przepisywac recznie.

Uzycie: scripts/cmucal-model.py [--json PLIK] [--blok CMU_DPU]
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFR = os.path.join(ROOT, "sources", "ds", "cmucal-sfr.c")
NODE = os.path.join(ROOT, "sources", "ds", "cmucal-node.c")


def czytaj(p):
    if not os.path.exists(p):
        sys.exit("brak pliku: " + p)
    return io.open(p, encoding="utf-8", errors="replace").read()


def liczba(t):
    t = t.strip()
    try:
        return int(t, 0)
    except ValueError:
        return None


def wczytaj_sfr(tekst):
    """Zwraca (bloki, rejestry, pola)."""
    bloki, rejestry, pola = {}, {}, {}
    for m in re.finditer(r"SFR_BLOCK\(\s*([A-Za-z0-9_]+)\s*,\s*([^,]+),\s*([^)]+)\)", tekst):
        baza, rozmiar = liczba(m.group(2)), liczba(m.group(3))
        if baza is not None:
            bloki[m.group(1)] = {"baza": baza, "rozmiar": rozmiar}
    for m in re.finditer(r"(?<!_)SFR\(\s*([A-Za-z0-9_]+)\s*,\s*([^,]+),\s*([A-Za-z0-9_]+)\s*\)", tekst):
        off = liczba(m.group(2))
        if off is not None:
            rejestry[m.group(1)] = {"offset": off, "blok": m.group(3)}
    for m in re.finditer(r"SFR_ACCESS\(\s*([A-Za-z0-9_]+)\s*,\s*([^,]+),\s*([^,]+),\s*([A-Za-z0-9_]+)\s*\)", tekst):
        shift, width = liczba(m.group(2)), liczba(m.group(3))
        if shift is not None and width is not None:
            pola[m.group(1)] = {"shift": shift, "width": width, "rejestr": m.group(4)}
    return bloki, rejestry, pola


def wczytaj_rodzicow(tekst):
    """Tablice `enum clk_id <nazwa>_parents[] = { ... };`."""
    out = {}
    for m in re.finditer(r"enum\s+clk_id\s+([A-Za-z0-9_]+)\[\]\s*=\s*\{(.*?)\}\s*;", tekst, re.S):
        pozycje = [x.strip() for x in m.group(2).split(",")]
        out[m.group(1)] = [x for x in pozycje if x and not x.startswith("/*")]
    return out


def argumenty(tekst, poz):
    """Rozbija liste argumentow makra zaczynajaca sie na '(' pod poz."""
    glebokosc, biezacy, args = 0, [], []
    for znak in tekst[poz:]:
        if znak == "(":
            glebokosc += 1
            if glebokosc == 1:
                continue
        elif znak == ")":
            glebokosc -= 1
            if glebokosc == 0:
                args.append("".join(biezacy).strip())
                return args
        if glebokosc == 1 and znak == ",":
            args.append("".join(biezacy).strip())
            biezacy = []
        else:
            biezacy.append(znak)
    return args


def wczytaj_wezly(tekst):
    out = []
    for m in re.finditer(r"\b(?:CLK_(MUX|DIV|GATE|PLL)|(FIXEDFACTOR|FIXEDRATE))\s*\(", tekst):
        rodzaj = m.group(1) or m.group(2)
        args = argumenty(tekst, m.end() - 1)
        if rodzaj == "MUX" and len(args) >= 3:
            out.append({"rodzaj": "mux", "id": args[0], "rodzice": args[1], "pole": args[2]})
        elif rodzaj == "DIV" and len(args) >= 3:
            out.append({"rodzaj": "div", "id": args[0], "rodzic": args[1], "pole": args[2]})
        elif rodzaj == "GATE" and len(args) >= 3:
            out.append({"rodzaj": "gate", "id": args[0], "rodzic": args[1], "pole": args[2]})
        elif rodzaj == "PLL" and len(args) >= 11:
            out.append({"rodzaj": "pll", "typ": args[0], "id": args[1], "rodzic": args[2],
                        "lock": args[3], "enable": args[4], "stable": args[5],
                        "p": args[6], "m": args[7], "s": args[8], "k": args[9],
                        "tabela": args[10]})
        elif rodzaj == "FIXEDFACTOR" and len(args) >= 4:
            # FIXEDFACTOR(id, rodzic, ratio, enable): dzielnik bez pola
            # DIVRATIO, wiec oprogramowac go nie mozna.  Producent trzyma w
            # `ratio` wartosc, ktora pole DIVRATIO by niosla, czyli dzielnik
            # jest o jeden wiekszy.
            out.append({"rodzaj": "ffactor", "id": args[0], "rodzic": args[1],
                        "ratio": liczba(args[2]), "enable": args[3]})
        elif rodzaj == "FIXEDRATE" and len(args) >= 2:
            out.append({"rodzaj": "frate", "id": args[0],
                        "czestotliwosc": liczba(args[1]), "enable": args[2] if len(args) > 2 else ""})
    return out


def zbuduj():
    bloki, rejestry, pola = wczytaj_sfr(czytaj(SFR))
    tekst_node = czytaj(NODE)
    return {
        "bloki": bloki,
        "rejestry": rejestry,
        "pola": pola,
        "rodzice": wczytaj_rodzicow(tekst_node),
        "wezly": wczytaj_wezly(tekst_node),
    }


def rozwiaz(model, nazwa_pola):
    """Pole -> (blok, offset, shift, width) albo None."""
    if not nazwa_pola:
        return None
    pole = model["pola"].get(nazwa_pola)
    if not pole:
        return None
    rej = model["rejestry"].get(pole["rejestr"])
    if not rej:
        return None
    blok = model["bloki"].get(rej["blok"])
    if not blok:
        return None
    return {"blok": rej["blok"], "baza": blok["baza"], "offset": rej["offset"],
            "shift": pole["shift"], "width": pole["width"]}


def main():
    model = zbuduj()
    if "--json" in sys.argv:
        p = sys.argv[sys.argv.index("--json") + 1]
        io.open(p, "w", encoding="utf-8").write(json.dumps(model, indent=1))
        print("model zapisany:", p)

    filtr = None
    if "--blok" in sys.argv:
        filtr = sys.argv[sys.argv.index("--blok") + 1]

    print("blokow: %d, rejestrow: %d, pol: %d, tablic rodzicow: %d, wezlow: %d"
          % (len(model["bloki"]), len(model["rejestry"]), len(model["pola"]),
             len(model["rodzice"]), len(model["wezly"])))

    licznik = {}
    braki = {}
    for w in model["wezly"]:
        r = rozwiaz(model, w.get("pole") or w.get("enable"))
        if filtr and (not r or r["blok"] != filtr):
            continue
        k = w["rodzaj"]
        licznik.setdefault(k, [0, 0])
        if r:
            licznik[k][0] += 1
        else:
            licznik[k][1] += 1
            braki.setdefault(k, []).append(w["id"])

    for k in sorted(licznik):
        ok, zle = licznik[k]
        print("  %-5s rozwiazanych %4d, z luka %4d" % (k, ok, zle))
    for k in sorted(braki):
        print("  luki %s: %s" % (k, ", ".join(braki[k][:4])))


if __name__ == "__main__":
    main()
