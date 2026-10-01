# Logo Debiana na czarne tlo: napis bialy, spirala i romb nad "i" w oryginalnej czerwieni.
# Kolory brzegow (polprzezroczystych pikseli) sa w zrodle przypadkowe (np. 255,31,255),
# wiec kazdy piksel dostaje czysty kolor najblizszego pelnego piksela, a alfa zostaje bez zmian.
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

src, dst = sys.argv[1], sys.argv[2]
a = np.asarray(Image.open(src).convert("RGBA")).astype(np.int32)
rgb, alpha = a[..., :3], a[..., 3]
RED = np.array([215, 7, 81])

solid = alpha >= 200
is_red = solid & (rgb[..., 0] > 100)
is_black = solid & (rgb.max(axis=2) < 60)
print("pelne piksele: czerwone %d, czarne %d, inne %d" % (is_red.sum(), is_black.sum(), (solid & ~is_red & ~is_black).sum()))

# etykieta najblizszego pelnego piksela (czerwony albo czarny)
known = is_red | is_black
_, (iy, ix) = ndimage.distance_transform_edt(~known, return_indices=True)
red_lab = is_red[iy, ix]

out = np.zeros_like(a)
out[..., :3] = np.where(red_lab[..., None], RED, 255)
out[..., 3] = alpha
out[alpha == 0] = 0
Image.fromarray(out.astype(np.uint8), "RGBA").save(dst)

# kontrola: zadnych kolorow poza bialym i czerwonym wsrod widocznych pikseli
vis = out[alpha > 0][:, :3]
kolory = {tuple(c) for c in np.unique(vis, axis=0)}
print("kolory widocznych pikseli:", kolory)
