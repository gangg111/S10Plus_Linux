#!/usr/bin/python3
# Liczby z JPEG-ow trybu "pp" cam2s-test: srednie R, G, B, stosunek R/B, rozrzut
# jasnosci (kontrast) i rozmiar pliku (redukcja szumu). Bez ogladania obrazu.
# Uzycie: pp-pomiar.py katalog
import os
import sys
from PIL import Image, ImageStat

for nazwa in ('auto', 'k3000', 'k8000', 'kontrast-2', 'kontrast2', 'szum0', 'szum2'):
    p = os.path.join(sys.argv[1], 'pp-' + nazwa, 'sesja-0.jpg')
    if not os.path.exists(p):
        print('%-11s brak pliku' % nazwa)
        continue
    im = Image.open(p).convert('RGB').reduce(8)
    r, g, b = ImageStat.Stat(im).mean
    sd = ImageStat.Stat(im.convert('L')).stddev[0]
    print('%-11s R %.1f G %.1f B %.1f  R/B %.3f  rozrzut %.1f  plik %d kB' % (nazwa, r, g, b, r / max(b, 0.1), sd,
                                                                            os.path.getsize(p) // 1024))
