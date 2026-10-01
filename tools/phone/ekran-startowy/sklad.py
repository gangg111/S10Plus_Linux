# Ekran startowy S-Boota z logo Debiana: z FABRYCZNYCH plikow (jedno kodowanie JPEG),
# napis SAMSUNG Galaxy S10+ zostaje, linia "Secured by Knox" i blok "Powered by android"
# zamalowane czernia (tlo oryginalu ma wartosc <= 1), logo wysrodkowane tam, gdzie stal znak pmOS.
# Uzycie: python sklad.py <logo.png> <katalog z org/> <wysokosc logo px>
import sys
import numpy as np
from PIL import Image

logo_path, base, H = sys.argv[1], sys.argv[2], int(sys.argv[3])
logo = Image.open(logo_path).convert("RGBA")
logo = logo.crop(logo.getchannel("A").getbbox())
W = round(logo.width * H / logo.height)
logo = logo.resize((W, H), Image.LANCZOS)

# (plik, przesuniecie y wzgledem svb_orange: logo.jpg ma te same elementy 17 px nizej)
for name, dy in (("svb_orange.jpg", 0), ("logo.jpg", 17)):
    im = Image.open("%s/org/%s" % (base, name))
    im.load()
    q = im.quantization
    a = np.asarray(im.convert("L"))
    # Knox (1449..1499) i android (2602..2758) z zapasem; sprawdz, ze zapas jest czarny
    for y0, y1 in ((1449 - 8, 1499 + 8), (2602 - 8, 2758 + 8)):
        y0 += dy; y1 += dy
        assert a[y0:y0 + 3].max() <= 40 and a[y1 - 3:y1].max() <= 40, (name, y0, y1)
        im.paste((0, 0, 0), (0, y0, im.width, y1))
    cy = 2680 + dy
    x, y = im.width // 2 - W // 2, cy - H // 2
    tlo = im.crop((x, y, x + W, y + H)).convert("RGBA")
    tlo.alpha_composite(logo)
    im.paste(tlo.convert("RGB"), (x, y))
    im.save("%s/debian-%s" % (base, name), quality="keep", subsampling="keep")
    print(name, "logo %dx%d w (%d,%d)" % (W, H, x, y))
