#!/usr/bin/env python3
"""Porownuje mape pamieci w NASZYM DTB z ta, ktora zdjeto z telefonu.

Po co. Trzy pozycje HW-BLOCKED (HW-31 mapa RAM-u, HW-34 trzy obszary reserved-memory,
HW-19 adres framebuffera) zamknal odczyt z urzadzenia: blob z /sys/firmware/fdt stockowego
Androida, czyli drzewo, ktore bootloader tej plyty podaje jadru producenta. Regula 3
z docs/HW-BLOCKED.md mowi, ze zamknieta pozycja wchodzi do verify.sh jako bramka, zeby nikt
jej pozniej nie cofnal. Sama suma kontrolna DTB tego nie robi dobrze: zmienia sie przy KAZDEJ
zmianie drzewa, wiec przy nastepnej przebudowie kusi, zeby ja po prostu nadpisac, a wtedy zla
mapa RAM-u przeszlaby niezauwazona. Ta bramka porownuje wartosci, nie hasze, wiec mowi wprost,
ktory bank sie rozjechal.

Co jest sprawdzane:
  * banki `memory@` musza byc DOKLADNIE te same (adres i rozmiar) co w blobie z telefonu,
  * kazdy obszar `reserved-memory`, ktory deklarujemy, musi istniec w blobie z telefonu pod
    tym samym adresem i rozmiarem; wyjatkiem jest framebuffer, ktorego producent nie trzyma
    w reserved-memory, tylko podaje jadru w linii polecen (s3cfb.bootloaderfb), wiec jego
    adres sprawdzany jest wzgledem zapisanego /proc/cmdline.

Czego NIE sprawdza, po pierwsze: obszarow zagniezdzonych glebiej niz jeden poziom pod
`reserved-memory`. Drzewo producenta trzyma tak cala rodzine `debug_snapshot`, ktorej my nie
deklarujemy; gdyby kiedys doszla, trzeba tu poprawic `zbierz()`, bo dzis taki obszar byl(by)
zgloszony jako nieistniejacy po stronie telefonu.

Czego NIE sprawdza, po drugie: tego, czy nie brakuje nam obszarow, ktore ma producent. Jego drzewo ma
ich wiecej (debug_snapshot, sterty ION kamery, sec_rdx_bootdev) i czesc z nich to pamiec
zwykla, oddawana jadru przez sam stockowy kernel. Dobor obszarow jest decyzja portu i opisuje
go komentarz w pliku plyty; bramka pilnuje tylko, zeby zadna zadeklarowana wartosc nie byla
zmyslona.

Uzycie: scripts/check-memory-map.py [nasz.dtb]   (domyslnie .pc-tools/b2.dtb)
Exit 0, gdy wszystko sie zgadza. Exit 1 przy niezgodnosci. Exit 2, gdy bramki NIE DA SIE
uruchomic, bo brakuje materialu: to nie jest zielone swiatlo i verify.sh liczy to jako
nieuruchomiona bramke, a nie jako OK.
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POMIAR = os.path.join(ROOT, "measurements", "2026-09-11-etap0a")
STOCK = os.path.join(POMIAR, "stock-fdt.dtb")
CMDLINE = os.path.join(POMIAR, "cmdline.txt")
NASZ = os.path.join(ROOT, ".pc-tools", "b2.dtb")

MAGIC = 0xD00DFEED
FDT_BEGIN_NODE, FDT_END_NODE, FDT_PROP, FDT_NOP, FDT_END = 1, 2, 3, 4, 9


def czytaj_fdt(sciezka):
    """Zwraca {sciezka wezla: {nazwa wlasciwosci: bajty}} plus komorki adresu i rozmiaru."""
    blob = open(sciezka, "rb").read()
    magic, totalsize = struct.unpack(">II", blob[:8])
    if magic != MAGIC:
        sys.exit("%s: to nie jest DTB (magic %08x)" % (sciezka, magic))
    if totalsize != len(blob):
        sys.exit("%s: totalsize %d, a plik ma %d bajtow" % (sciezka, totalsize, len(blob)))
    off_struct, off_strings = struct.unpack(">II", blob[8:16])
    size_struct = struct.unpack(">I", blob[36:40])[0]
    wezly = {}
    stos = []
    i = off_struct
    koniec = off_struct + size_struct
    while i < koniec:
        (token,) = struct.unpack(">I", blob[i:i + 4])
        i += 4
        if token == FDT_BEGIN_NODE:
            k = blob.index(b"\0", i)
            nazwa = blob[i:k].decode("utf-8", "replace")
            i = (k + 4) & ~3
            stos.append(nazwa)
            wezly.setdefault("/" + "/".join(x for x in stos if x), {})
        elif token == FDT_END_NODE:
            stos.pop()
        elif token == FDT_PROP:
            dlugosc, nameoff = struct.unpack(">II", blob[i:i + 8])
            i += 8
            k = blob.index(b"\0", off_strings + nameoff)
            nazwa = blob[off_strings + nameoff:k].decode("utf-8", "replace")
            wartosc = blob[i:i + dlugosc]
            i = (i + dlugosc + 3) & ~3
            wezly["/" + "/".join(x for x in stos if x)][nazwa] = wartosc
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            break
        else:
            sys.exit("%s: nieznany token %d na pozycji %d" % (sciezka, token, i - 4))
    return wezly


def komorki(wezly, sciezka_wezla, domyslny_adres=2, domyslny_rozmiar=1):
    w = wezly.get(sciezka_wezla, {})
    a = w.get("#address-cells")
    s = w.get("#size-cells")
    return (struct.unpack(">I", a)[0] if a else domyslny_adres,
            struct.unpack(">I", s)[0] if s else domyslny_rozmiar)


def rozbij_reg(dane, ac, sc):
    """reg jako lista (adres, rozmiar), komorki po 4 bajty, big endian."""
    krok = (ac + sc) * 4
    out = []
    for p in range(0, len(dane) - krok + 1, krok):
        pola = struct.unpack(">%dI" % (ac + sc), dane[p:p + krok])
        adres = 0
        for c in pola[:ac]:
            adres = (adres << 32) | c
        rozmiar = 0
        for c in pola[ac:]:
            rozmiar = (rozmiar << 32) | c
        out.append((adres, rozmiar))
    return out


def zbierz(wezly, prefiks, rodzic):
    """Mapa (adres, rozmiar) -> nazwa wezla dla dzieci danego rodzica."""
    ac, sc = komorki(wezly, rodzic)
    out = {}
    for sciezka, w in wezly.items():
        if not sciezka.startswith(prefiks) or "reg" not in w:
            continue
        reszta = sciezka[len(prefiks):]
        if "/" in reszta:
            continue
        for para in rozbij_reg(w["reg"], ac, sc):
            out[para] = sciezka
    return out


def banki(wezly):
    ac, sc = komorki(wezly, "/")
    out = []
    for sciezka, w in sorted(wezly.items()):
        if not re.fullmatch(r"/memory(@[0-9a-fA-F]+)?", sciezka):
            continue
        if w.get("device_type", b"").rstrip(b"\0") != b"memory":
            continue
        out.extend(rozbij_reg(w["reg"], ac, sc))
    return sorted(out)


def main():
    nasz_plik = sys.argv[1] if len(sys.argv) > 1 else NASZ
    for p in (STOCK, CMDLINE):
        if not os.path.exists(p):
            print("NIEURUCHOMIONA: brak materialu pomiarowego %s" % p)
            return 2
    if not os.path.exists(nasz_plik):
        print("NIEURUCHOMIONA: brak %s, zbuduj DTB (bramka [3] verify.sh)" % nasz_plik)
        return 2

    stock = czytaj_fdt(STOCK)
    nasz = czytaj_fdt(nasz_plik)
    bledy = 0

    nasze_banki, stock_banki = banki(nasz), banki(stock)
    if nasze_banki != stock_banki:
        bledy += 1
        print("BLAD: banki memory@ nie zgadzaja sie z telefonem")
        for para in sorted(set(nasze_banki) | set(stock_banki)):
            gdzie = ("my i telefon" if para in nasze_banki and para in stock_banki
                     else "tylko my" if para in nasze_banki else "tylko telefon")
            print("  0x%09x + 0x%-9x  %s" % (para[0], para[1], gdzie))
    else:
        suma = sum(r for _a, r in nasze_banki)
        print("OK: %d bankow memory@ identycznych z telefonem, razem %d MiB"
              % (len(nasze_banki), suma // (1024 * 1024)))

    stock_rez = zbierz(stock, "/reserved-memory/", "/reserved-memory")
    nasze_rez = zbierz(nasz, "/reserved-memory/", "/reserved-memory")
    cmdline = open(CMDLINE, encoding="utf-8", errors="replace").read()
    m = re.search(r"s3cfb\.bootloaderfb=(0x[0-9a-fA-F]+)", cmdline)
    fb = int(m.group(1), 16) if m else None
    zgodne = 0
    for (adres, rozmiar), sciezka in sorted(nasze_rez.items()):
        nazwa = sciezka.rsplit("/", 1)[-1]
        if nazwa.startswith("framebuffer"):
            if fb is None:
                bledy += 1
                print("BLAD: %s: w zapisanym cmdline nie ma s3cfb.bootloaderfb" % nazwa)
            elif adres != fb:
                bledy += 1
                print("BLAD: %s pod 0x%x, a bootloader podaje 0x%x" % (nazwa, adres, fb))
            else:
                zgodne += 1
            continue
        if (adres, rozmiar) in stock_rez:
            zgodne += 1
            continue
        bledy += 1
        blisko = [p for p in stock_rez if p[0] == adres]
        if blisko:
            print("BLAD: %s ma rozmiar 0x%x, a telefon 0x%x pod tym samym adresem"
                  % (nazwa, rozmiar, blisko[0][1]))
        else:
            print("BLAD: %s (0x%x + 0x%x) nie wystepuje w drzewie z telefonu"
                  % (nazwa, adres, rozmiar))
    print("%s: %d z %d rezerwacji potwierdzonych odczytem z telefonu"
          % ("OK" if zgodne == len(nasze_rez) else "podsumowanie", zgodne, len(nasze_rez)))
    return 1 if bledy else 0


if __name__ == "__main__":
    sys.exit(main())
