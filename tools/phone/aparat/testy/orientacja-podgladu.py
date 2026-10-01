#!/usr/bin/python3
# Porownuje dwa zrzuty wizjera (np. Camera1 i Camera2 przy tej samej scenie):
# korelacja srodka kadru bez zmian i po odbiciach, bez zapisywania obrazu.
# Najwyzsza korelacja "bez zmian" = ta sama orientacja.
# Uzycie: orientacja-podgladu.py a.ppm b.ppm
import sys
from PIL import Image, ImageOps


def wektor(im):
    im = im.convert('L').crop((0, 300, im.width, 1500)).resize((48, 64))
    return list(im.getdata())


def korelacja(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((y - mb) ** 2 for y in b) ** 0.5
    return cov / (va * vb) if va and vb else 0.0


a = Image.open(sys.argv[1])
b = Image.open(sys.argv[2])
wa = wektor(a)
for nazwa, im in (('bez zmian', b), ('odbicie poziome', ImageOps.mirror(b)), ('odbicie pionowe', ImageOps.flip(b)),
                  ('obrot 180', b.rotate(180))):
    print('%-16s %.3f' % (nazwa, korelacja(wa, wektor(im))))
