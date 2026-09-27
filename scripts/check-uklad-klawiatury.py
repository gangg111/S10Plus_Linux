#!/usr/bin/env python3
"""Sprawdza uklad klawiatury ekranowej: zgodnosc ze wzorcem i kompletnosc.

Po co osobna bramka.  Uklad ma byc przeniesiony JEDEN DO JEDNEGO z klawiatury
Qt uzytkownika (`tools/klawiatura/wzorzec/Layouts.qml`).  Rozjazd miedzy nia
a naglowkiem C nie psuje kompilacji ani nie rzuca sie w oczy w kodzie, a widac
go dopiero na telefonie, w postaci klawisza w innym miejscu albo takiego,
ktorego nie ma we wzorcu.

Sprawdzane:
  1. `tools/klawiatura/uklad.h` rowna sie wyjsciu
     `scripts/gen-uklad-klawiatury.py`, czyli zgadza sie ze wzorcem QML.
  2. Kazdy klawisz jest zywy: albo wstawia znak, albo ma kod, albo akcje;
     odstepy (ROLA_ODSTEP) sa jedynym wyjatkiem i nie moga miec znaku.
  3. Przelaczniki warstw wskazuja na istniejaca warstwe.
  4. Kazdy DRUKOWALNY znak ASCII jest osiagalny: wprost, pod Shiftem albo pod
     przytrzymaniem klawisza.  Bez tego w powloce nagle brakuje znaku i nie ma
     jak go wpisac.

Czego bramka NIE sprawdza i dlaczego: powtorzen znakow.  Wzorzec ma je celowo
(nawiasy sa i w symbolach, i w operatorach), wiec wymaganie "dokladnie raz"
byloby sprzeczne z przeniesieniem jeden do jednego.

Exit 0, gdy wszystko sie zgadza.  Exit 1 przy roznicy albo braku.
Exit 2, gdy bramki NIE DA SIE uruchomic (brak pliku ukladu albo wzorca).
"""
import os
import re
import subprocess
import sys

NL = chr(10)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLIK = os.path.join(ROOT, "tools", "klawiatura", "uklad.h")
WZORZEC = os.path.join(ROOT, "tools", "klawiatura", "wzorzec", "Layouts.qml")
GENERATOR = os.path.join(ROOT, "scripts", "gen-uklad-klawiatury.py")

DRUKOWALNE = "".join(chr(k) for k in range(32, 127))


def znormalizuj(tekst):
    return tekst.replace(chr(13) + chr(10), NL).replace(chr(13), NL)


def rozkoduj(napis):
    """Napis z pliku C na tekst: sklejone czesci i sekwencje \\xNN."""
    wynik = []
    for czesc in re.findall(r'"((?:[^"\\]|\\.)*)"', napis):
        i = 0
        bajty = bytearray()
        while i < len(czesc):
            if czesc[i] == "\\" and i + 1 < len(czesc):
                if czesc[i + 1] == "x":
                    bajty.append(int(czesc[i + 2:i + 4], 16))
                    i += 4
                    continue
                bajty.append(ord(czesc[i + 1]))
                i += 2
                continue
            bajty.append(ord(czesc[i]))
            i += 1
        wynik.append(bajty.decode("utf-8", "replace"))
    return "".join(wynik)


def klawisze(tekst):
    """Lista slownikow opisujacych klawisze z tablicy UKLAD."""
    wzor = re.compile(
        r"\{\s*(?P<etykieta>NULL|(?:\"(?:[^\"\\]|\\.)*\"\s*)+),\s*"
        r"(?P<znak>NULL|(?:\"(?:[^\"\\]|\\.)*\"\s*)+),\s*"
        r"\{\s*(?P<warianty>[^}]*)\}\s*,\s*"
        r"(?P<ikona>\w+),\s*(?P<waga>\d+),\s*(?P<rola>\w+),\s*"
        r"(?P<docel>\d+),\s*(?P<kod>\w+),\s*(?P<powtarza>\d+)\s*\}")
    wynik = []
    for m in wzor.finditer(tekst):
        warianty = [rozkoduj(w) for w in m.group("warianty").split(",")
                    if w.strip() and w.strip() != "NULL"]
        wynik.append({
            "etykieta": None if m.group("etykieta") == "NULL"
                        else rozkoduj(m.group("etykieta")),
            "znak": None if m.group("znak") == "NULL"
                    else rozkoduj(m.group("znak")),
            "warianty": warianty,
            "ikona": m.group("ikona"),
            "waga": int(m.group("waga")),
            "rola": m.group("rola"),
            "docel": int(m.group("docel")),
            "kod": m.group("kod"),
        })
    return wynik


def main():
    if not os.path.exists(PLIK):
        print("check-uklad: brak %s" % os.path.relpath(PLIK, ROOT))
        return 2
    if not os.path.exists(WZORZEC):
        print("check-uklad: brak wzorca %s" % os.path.relpath(WZORZEC, ROOT))
        return 2

    # 1. Zgodnosc z generatorem, czyli ze wzorcem QML.
    r = subprocess.run([sys.executable, GENERATOR, "--wypisz"],
                       capture_output=True, text=True)
    if r.returncode:
        print("check-uklad: generator padl:%s%s" % (NL, r.stderr.strip()))
        return 2
    with open(PLIK, encoding="utf-8") as f:
        maja = znormalizuj(f.read())
    ma_byc = znormalizuj(r.stdout)
    if maja != ma_byc:
        a = maja.split(NL)
        b = ma_byc.split(NL)
        for i in range(min(len(a), len(b))):
            if a[i] != b[i]:
                print("check-uklad: %s rozni sie od wzorca w wierszu %d"
                      % (os.path.relpath(PLIK, ROOT), i + 1))
                print("  plik:      %s" % a[i][:90])
                print("  generator: %s" % b[i][:90])
                return 1
        print("check-uklad: rozna liczba wierszy: plik %d, generator %d"
              % (len(a), len(b)))
        return 1

    lista = klawisze(maja)
    if not lista:
        print("check-uklad: nie umiem odczytac ani jednego klawisza")
        return 2

    warstw = int(re.search(r"#define WARSTW\s+(\d+)", maja).group(1))
    osiagalne = set()
    for k in lista:
        # 2. Kazdy klawisz zywy.
        if k["rola"] == "ROLA_ODSTEP":
            if k["znak"] or k["etykieta"]:
                print("check-uklad: odstep z trescia: %r" % k)
                return 1
            continue
        if k["rola"] == "ROLA_ZNAK" and not k["znak"]:
            print("check-uklad: klawisz znakowy bez znaku: %r" % k)
            return 1
        if k["rola"] in ("ROLA_NAZWANY", "ROLA_MOD") and k["kod"] == "0":
            print("check-uklad: klawisz systemowy bez kodu: %r" % k)
            return 1
        if (k["rola"] == "ROLA_ZNAK" and not k["etykieta"] and
                not k["znak"] and k["ikona"] == "IKONA_BRAK"):
            print("check-uklad: klawisz bez napisu i bez ikony: %r" % k)
            return 1
        # 3. Przelaczniki warstw.
        if k["rola"] == "ROLA_WARSTWA" and k["docel"] >= warstw:
            print("check-uklad: przelacznik na warstwe %d, a jest ich %d"
                  % (k["docel"], warstw))
            return 1

        if k["znak"]:
            osiagalne.add(k["znak"])
            if len(k["znak"]) == 1 and k["znak"].isalpha():
                osiagalne.add(k["znak"].upper())
        for w in k["warianty"]:
            osiagalne.add(w)

    # 4. Komplet drukowalnego ASCII.
    brak = [z for z in DRUKOWALNE if z not in osiagalne]
    if brak:
        print("check-uklad: nieosiagalne znaki ASCII: %s"
              % " ".join("%r" % z for z in brak))
        return 1

    print("check-uklad: %d klawiszy w %d warstwach zgodnych ze wzorcem QML,"
          " komplet drukowalnego ASCII osiagalny"
          % (len([k for k in lista if k["rola"] != "ROLA_ODSTEP"]), warstw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
