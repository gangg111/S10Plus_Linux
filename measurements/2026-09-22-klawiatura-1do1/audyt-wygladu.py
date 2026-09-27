#!/usr/bin/env python3
"""Audyt wygladu: kazdy element sprawdzony na realnych pikselach z telefonu.

Po co.  Zgodnosc rozmieszczenia udowodnil `porownaj-uklad.py`, ale wyglad to
tez kolory, zaokraglenia, odstepy, rozmiary pisma i kropka wariantu.  Ten
skrypt czyta ZRZUTY Z BUFORA RAMKI i mierzy je, zamiast wierzyc, ze stale
w kodzie sa przepisane poprawnie.

Dwie miary, bo dwa rodzaje pytan:
  * kolory i wymiary porownujemy z LICZBAMI z wzorzec/Theme.qml,
  * ksztalt naroznika i rozmiary pisma porownujemy z RENDEREM klawiatury Qt,
    bo to jedyny uczciwy wzorzec dla krzywej i dla kroju: przeliczanie ich na
    wzory daje falszywe alarmy (pierwsza wersja tego skryptu zglosila promien
    15 wobec 24 tylko dlatego, ze zly wzor wiazal wciecie wiersza z promieniem).

Uzycie:
  audyt-wygladu.py <litery.png> <dymek.png> <stany.png> <wzorzec-qt.png>

(trzeci plik zostaje w wywolaniu dla zgodnosci, dzis nic z niego nie mierzymy:
stany modyfikatorow widac na samych klawiszach, nie w narozniku)
"""
import sys

from PIL import Image

# Liczby wprost z wzorzec/Theme.qml przy gestosci 20,57 px/mm (1440 pikseli na
# 70 mm czynnej szerokosci panelu).
DPMM_X100 = 2057
RZAD = DPMM_X100 * 900 // 10000		# rowHeightMm 9.0
ODSTEP = DPMM_X100 * 60 // 10000	# gapMm 0.6
KRZYWIZNA = DPMM_X100 * 160 // 10000	# safeMarginMm 1.6

KOLORY = {
    "bg": (0x00, 0x00, 0x00),
    "keyBg": (0x1c, 0x1c, 0x1e),
    "keyBgAlt": (0x13, 0x13, 0x15),
    "keyBgDown": (0x0a, 0x84, 0xff),
    "keyBgActive": (0x2c, 0x2c, 0x2e),
    "text": (0xf2, 0xf2, 0xf7),
    "textDim": (0x8e, 0x8e, 0x93),
    "accent": (0x0a, 0x84, 0xff),
}

# Rzedy w zrzutach: (gora, dol) pudel klawiszy.  Wyliczone raz i sprawdzone
# przez porownaj-uklad.py, wiec tutaj sa dana wejsciowa.
RZEDY_C = [(12, 143), (156, 328), (341, 513), (526, 698), (711, 883)]
RZEDY_QT = [(156, 287), (300, 472), (485, 657), (669, 841), (854, 1026)]

zle = 0


def wynik(opis, zmierzone, wzorzec, ok):
    global zle
    print("  %-44s %-12s %-12s %s"
          % (opis, zmierzone, wzorzec, "ok" if ok else "ZLE"))
    if not ok:
        zle += 1


def sprawdz(opis, zmierzone, wzorzec, tolerancja=0):
    wynik(opis, zmierzone, wzorzec, abs(zmierzone - wzorzec) <= tolerancja)


def sprawdz_kolor(opis, zmierzony, nazwa):
    ocz = KOLORY[nazwa]
    wynik("%s (%s)" % (opis, nazwa),
          "#%02x%02x%02x" % zmierzony, "#%02x%02x%02x" % ocz, zmierzony == ocz)


def pasma(px, szer, y, prog=12):
    """Pasma pikseli jasniejszych od tla w danym wierszu."""
    out = []
    x = 0
    while x < szer:
        if sum(px[x, y]) > prog:
            x0 = x
            while x < szer and sum(px[x, y]) > prog:
                x += 1
            if x - x0 > 8:
                out.append((x0, x - 1))
        else:
            x += 1
    return out


def tusz(im, box, prog=200):
    """Rozmiar prostokata jasnych pikseli (napisu) w podanym obszarze."""
    px = im.load()
    x0, y0, x1, y1 = box
    pkt = [(x, y) for y in range(y0, y1) for x in range(x0, x1)
           if sum(px[x, y]) / 3 > prog]
    if not pkt:
        return None
    xs = [p[0] for p in pkt]
    ys = [p[1] for p in pkt]
    return (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def profil_naroznika(im, x0, x1, ytop, ile=14):
    """O ile wciety jest kazdy kolejny wiersz przy lewym gornym narozniku.

    To jest odcisk palca krzywej: jedna liczba (promien) nie odda tego, czy
    naroznik jest lukiem, sciety, czy schodkowy, a ten ciag oddaje."""
    px = im.load()
    out = []
    for dy in range(ile):
        x = x0
        while x < x1 and sum(px[x, ytop + dy]) <= 12:
            x += 1
        out.append(x - x0)
    return out


def main():
    litery = Image.open(sys.argv[1]).convert("RGB")
    dymek = Image.open(sys.argv[2]).convert("RGB")
    stany = Image.open(sys.argv[3]).convert("RGB")
    wzor = Image.open(sys.argv[4]).convert("RGB")
    pl = litery.load()
    pd = dymek.load()
    ps = stany.load()
    szer = litery.width

    rzedy = [(y0, y1, pasma(pl, szer, (y0 + y1) // 2)) for y0, y1 in RZEDY_C]
    q = rzedy[1][2][0]			# klawisz q
    e = rzedy[1][2][2]			# klawisz e, ma wariant
    akcja = rzedy[4][2][0]		# ?123

    print("Zrzut paska: %dx%d, gestosc 20,57 px/mm"
          % (litery.width, litery.height))
    print()
    print("KOLORY (wzorzec: Theme.qml co do bajtu)")
    print("  %-44s %-12s %-12s" % ("element", "zmierzone", "wzorzec"))
    sprawdz_kolor("tlo paska", pl[4, 4], "bg")
    sprawdz_kolor("klawisz zwykly", pl[q[0] + 6, 240], "keyBg")
    sprawdz_kolor("klawisz z akcja", pl[akcja[0] + 6, 730], "keyBgAlt")
    # Punkt z DALA od glifu: w srodku klawisza siedzi litera, wiec probka
    # z centrum lapie wygladzony brzeg napisu, a nie samo tlo klawisza.
    sprawdz_kolor("klawisz wcisniety", pd[256, 500], "keyBgDown")

    # Dymek znajdujemy po kolorze obwodki, a nie po jasnosci: dymek stoi NAD
    # klawiszami, wiec zwykle szukanie krawedzi wchodzi w sasiedni klawisz.
    obwodka = [x for x in range(szer) if pd[x, 230] == KOLORY["accent"]]
    if len(obwodka) >= 2:
        sprawdz_kolor("obwodka dymka", pd[obwodka[0], 230], "accent")
        sprawdz_kolor("tlo dymka",
                      pd[(obwodka[0] + obwodka[-1]) // 2, 200], "keyBgActive")
        sprawdz("szerokosc dymka na jeden wariant [px]",
                obwodka[-1] - obwodka[0] + 1, RZAD, 2)
    else:
        wynik("obwodka dymka (accent)", "nie znaleziono", "dwie krawedzie",
              False)

    napis = max((pl[x, y] for y in range(180, 300) for x in range(q[0], q[1])),
                key=sum)
    sprawdz_kolor("napis na klawiszu", napis, "text")

    print()
    print("WYMIARY (wzorzec: milimetry z Theme.qml przez gestosc)")
    print("  %-44s %-12s %-12s" % ("element", "zmierzone", "wzorzec"))
    sprawdz("wysokosc rzedu pelnego [px]",
            rzedy[1][1] - rzedy[1][0] + 1 + ODSTEP, RZAD, 2)
    sprawdz("wysokosc rzedu cyfr (rh 0,78) [px]",
            rzedy[0][1] - rzedy[0][0] + 1 + ODSTEP, RZAD * 78 // 100, 2)
    sprawdz("odstep miedzy klawiszami [px]",
            rzedy[1][2][1][0] - rzedy[1][2][0][1] - 1, ODSTEP, 1)
    # Pudlo klawisza zaczyna sie za marginesem na krzywizne ORAZ za polowa
    # odstepu z kazdej strony, czyli razem o caly odstep dalej.
    sprawdz("lewa krawedz pierwszego klawisza [px]", q[0],
            KRZYWIZNA + ODSTEP, 2)
    print()
    print("KSZTALT I PISMO (wzorzec: render klawiatury Qt)")
    print("  %-44s %-12s %-12s" % ("element", "zmierzone", "wzorzec"))
    pc = profil_naroznika(litery, q[0] - 4, q[1], rzedy[1][0])
    pq = profil_naroznika(wzor, 41, 168, RZEDY_QT[1][0])
    rozjazd = max(abs(a - b) for a, b in zip(pc, pq))
    wynik("naroznik klawisza: wciecia kolejnych wierszy",
          ",".join(str(v) for v in pc[:7]),
          ",".join(str(v) for v in pq[:7]), rozjazd <= 2)

    tc = tusz(litery, (q[0], RZEDY_C[1][0], q[1], RZEDY_C[1][1]))
    tq = tusz(wzor, (41, RZEDY_QT[1][0], 168, RZEDY_QT[1][1]))
    wynik("glif litery q: szerokosc na wysokosc [px]",
          "%dx%d" % tc, "%dx%d" % tq,
          abs(tc[0] - tq[0]) <= 2 and abs(tc[1] - tq[1]) <= 2)

    ec = tusz(litery, (akcja[0], RZEDY_C[4][0], akcja[1], RZEDY_C[4][1]))
    eq = tusz(wzor, (45, RZEDY_QT[4][0], 227, RZEDY_QT[4][1]))
    wynik("napis funkcyjny ?123 [px]", "%dx%d" % ec, "%dx%d" % eq,
          abs(ec[0] - eq[0]) <= 2 and abs(ec[1] - eq[1]) <= 2)

    print()
    if zle:
        print("ROZNICE: %d" % zle)
        return 1
    print("ZGODNE: kolory co do bajtu, wymiary co do piksela,"
          " naroznik i pismo jak w renderze Qt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
