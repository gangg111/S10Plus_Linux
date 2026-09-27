"""Porownanie dwoch zrzutow okna mpv (scena jasna i ciemna, ta sama tresc).

Piksele przez ffmpeg jako rgb48le; liczone tylko w obszarze obrazu (wiersze,
w ktorych cokolwiek nie jest czarne). Wynik: srednia wartosc kanalow (0..65535)
w obu scenach i sredni bezwzgledny rozjazd.
"""
import array
import subprocess
import sys


def surowe(p):
    wy = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-'],
                        capture_output=True, check=True).stdout
    a = array.array('H')
    a.frombytes(wy)
    return a


def main():
    a, b = surowe('/tmp/dyn-jasna.png'), surowe('/tmp/dyn-ciemna.png')
    w = 1440 * 3
    wiersze = [r for r in range(len(a) // w) if max(a[r * w:(r + 1) * w]) > 2000]
    if not wiersze:
        print(sys.argv[1], 'brak obrazu w zrzucie')
        return
    lo, hi = wiersze[0] * w, (wiersze[-1] + 1) * w
    sa = sum(a[lo:hi]) / (hi - lo)
    sb = sum(b[lo:hi]) / (hi - lo)
    rozjazd = sum(abs(x - y) for x, y in zip(a[lo:hi], b[lo:hi])) / (hi - lo)
    print('%s: obraz w wierszach %d..%d, srednia jasna=%.0f ciemna=%.0f, sredni rozjazd=%.1f (%.2f%%)' % (
        sys.argv[1], wiersze[0], wiersze[-1], sa, sb, rozjazd, 100 * rozjazd / max(sa, 1)))


main()
