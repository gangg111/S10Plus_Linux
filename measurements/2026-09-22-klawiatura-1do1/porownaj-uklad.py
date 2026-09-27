#!/usr/bin/env python3
"""Porownuje rozmieszczenie klawiszy: render Qt kontra zrzut klawiatury w C.

Metoda nie zaklada niczego o ukladzie: w kazdym wierszu obrazu szuka pasm
pikseli jasniejszych od tla (klawisze maja #1c1c1e albo #131315, tlo #000000),
czyli PROSTOKATOW klawiszy, i porownuje ich krawedzie.  Zgodnosc krawedzi
znaczy, ze rzedy, szerokosci i odstepy sa te same.
"""
import sys

from PIL import Image

PROG = 12		# jasnosc powyzej tla


def pasma_w_wierszu(px, szer, y):
    """Lista (x0, x1) pasm klawiszy w danym wierszu obrazu."""
    pasma = []
    x = 0
    while x < szer:
        r, g, b = px[x, y]
        if r + g + b > PROG:
            x0 = x
            while x < szer and sum(px[x, y]) > PROG:
                x += 1
            if x - x0 > 8:
                pasma.append((x0, x - 1))
        else:
            x += 1
    return pasma


def rzedy(im):
    """Rzedy klawiszy: (y0, y1, [(x0, x1), ...]) dla kazdego pasma w pionie."""
    szer, wys = im.size
    px = im.load()
    # Wiersz nalezy do rzedu, gdy ma co najmniej jeden szeroki pas klawisza.
    zajete = []
    for y in range(wys):
        zajete.append(len(pasma_w_wierszu(px, szer, y)) > 0)

    wynik = []
    y = 0
    while y < wys:
        if not zajete[y]:
            y += 1
            continue
        y0 = y
        while y < wys and zajete[y]:
            y += 1
        y1 = y - 1
        if y1 - y0 < 20:
            continue
        srodek = (y0 + y1) // 2
        wynik.append((y0, y1, pasma_w_wierszu(px, szer, srodek)))
    return wynik


def opis(nazwa, im):
    r = rzedy(im)
    print("%s: %dx%d, rzedow %d" % (nazwa, im.width, im.height, len(r)))
    for i, (y0, y1, pasma) in enumerate(r):
        print("  rzad %d: y %d..%d (h=%d), klawiszy %d, x: %s"
              % (i, y0, y1, y1 - y0 + 1, len(pasma),
                 " ".join("%d-%d" % p for p in pasma)))
    return r


def main():
    qt = Image.open(sys.argv[1]).convert("RGB")
    c = Image.open(sys.argv[2]).convert("RGB")
    rq = opis("wzorzec Qt", qt)
    rc = opis("klawiatura C", c)

    print()
    if len(rq) != len(rc):
        print("ROZNA liczba rzedow: Qt %d, C %d" % (len(rq), len(rc)))
        return 1

    zle = 0
    for i, ((qy0, qy1, qp), (cy0, cy1, cp)) in enumerate(zip(rq, rc)):
        if len(qp) != len(cp):
            print("rzad %d: rozna liczba klawiszy (Qt %d, C %d)"
                  % (i, len(qp), len(cp)))
            zle += 1
            continue
        # Porownujemy krawedzie wzgledem lewej krawedzi pierwszego klawisza,
        # zeby nie mierzyc marginesu okna, tylko SAM uklad.
        qbaza = qp[0][0]
        cbaza = cp[0][0]
        for j, ((qx0, qx1), (cx0, cx1)) in enumerate(zip(qp, cp)):
            dx0 = (qx0 - qbaza) - (cx0 - cbaza)
            dw = (qx1 - qx0) - (cx1 - cx0)
            if abs(dx0) > 3 or abs(dw) > 3:
                print("rzad %d klawisz %d: przesuniecie %d px, szerokosc %d px"
                      % (i, j, dx0, dw))
                zle += 1
        qh = qy1 - qy0
        ch = cy1 - cy0
        if abs(qh - ch) > 3:
            print("rzad %d: wysokosc Qt %d, C %d" % (i, qh, ch))
            zle += 1

    print()
    if zle:
        print("ROZNICE: %d" % zle)
        return 1
    print("ZGODNE: te same rzedy, te same szerokosci i wysokosci klawiszy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
