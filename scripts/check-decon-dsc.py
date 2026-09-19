#!/usr/bin/env python3
"""Sprawdza konfiguracje DSC enkoderow DECON.

Sterownik nie liczy juz sam parametrow kontroli szybkosci: kopiuje konfiguracje
panelu, zaweza ja do polowki obrazu przypadajacej na jeden enkoder i przepuszcza
przez helpery rdzenia (drm_dsc_set_const_params, drm_dsc_set_rc_buf_thresh,
drm_dsc_setup_rc_params, drm_dsc_initial_scale_value,
drm_dsc_compute_rc_parameters).  Wczesniej ta sama matematyka byla przepisana
recznie obok panelu, wiec dwie kopie mogly sie rozjechac.

Ta bramka pilnuje dwoch rzeczy naraz:

  1. sterownik NAPRAWDE zaweza konfiguracje tak, jak ten skrypt zaklada
     (parsuje decon_dsc_calc, zeby nie sprawdzac samego siebie),
  2. model helperow uruchomiony na polowce obrazu daje DOKLADNIE te wartosci,
     ktore dla jednego enkodera daje wzor producenta
     (decon_reg.c:906-1058, dsc_calc_pps_info).

Uzycie: scripts/check-decon-dsc.py [sciezka do exynos9820_drm_decon.c]
"""
import os
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else \
    "sources/linux/drivers/gpu/drm/exynos/exynos9820_drm_decon.c"

# Wartosci wzoru producenta dla beyond2lte przy dwoch enkoderach
# (xres 1440, dsc_cnt 2, dsc_slice_num 2, dsc_slice_h 40).
EXPECTED = {
    "pic_width": 720, "pic_height": 3040,
    "slice_width": 720, "slice_height": 40, "slice_chunk_size": 720,
    "initial_xmit_delay": 512,
    "initial_scale_value": 32, "first_line_bpg_offset": 12,
    "initial_offset": 6144, "final_offset": 4336,
    "nfl_bpg_offset": 631, "slice_bpg_offset": 489,
    "scale_increment_interval": 1132, "scale_decrement_interval": 10,
}

# Pola, ktore sterownik ustawia sam, bo nie sa czescia modelu DSC.
EXPECTED_HW = {
    "width_per_enc": 240,
    "dual_slice": 0,
    "slice_mode_change": 1,
    "initial_dec_delay": 0x1b4,
}


def fail(msg):
    print("FAIL " + msg)
    sys.exit(1)


if not os.path.exists(SRC):
    fail("brak %s" % SRC)

src = open(SRC, encoding="utf-8", errors="replace").read()

m = re.search(r"\nstatic int decon_dsc_calc\(.*?\n\}\n", src, re.S)
if not m:
    fail("nie znaleziono decon_dsc_calc w %s" % SRC)
body = m.group(0)

# --- 1. czy sterownik robi to, co ten skrypt zaklada -------------------------

REQUIRED_CALLS = [
    "drm_dsc_set_const_params",
    "drm_dsc_set_rc_buf_thresh",
    "drm_dsc_setup_rc_params",
    "drm_dsc_initial_scale_value",
    "drm_dsc_compute_rc_parameters",
]
missing = [c for c in REQUIRED_CALLS if (c + "(") not in body]
if missing:
    fail("decon_dsc_calc nie wola helperow rdzenia: %s" % ", ".join(missing))

if "struct drm_dsc_config cfg = *panel_dsc;" not in body:
    fail("decon_dsc_calc nie startuje od konfiguracji panelu")

checks = [
    (r"cfg\.pic_width\s*=\s*width_eff;", "pic_width nie jest polowka obrazu"),
    (r"width_eff\s*=\s*\(dsc_count == 2\)\s*\?\s*mode->hdisplay\s*/\s*2",
     "polowka obrazu liczona inaczej niz zaklada bramka"),
    (r"cfg\.slice_count\s*=\s*panel_dsc->slice_count\s*/\s*dsc_count;",
     "slice_count nie jest dzielone miedzy enkodery"),
    (r"cfg\.slice_width\s*=\s*enc->dual_slice\s*\?\s*width_eff\s*/\s*2\s*:\s*width_eff;",
     "slice_width nie zalezy od dual_slice tak, jak zaklada bramka"),
]
for pat, msg in checks:
    if not re.search(pat, body):
        fail(msg)

# --- 2. model helperow rdzenia na polowce obrazu -----------------------------


def ceil_div(a, b):
    return -(-a // b)


# to, co panel ustawia jawnie, zawezone do jednego enkodera
cfg = dict(pic_width=720, pic_height=3040, slice_width=720, slice_height=40,
           slice_count=1, bits_per_component=8, bits_per_pixel=8 << 4,
           line_buf_depth=9, rc_model_size=8192, initial_xmit_delay=512,
           first_line_bpg_offset=12, initial_offset=6144, mux_word_size=48,
           initial_scale_value=32)

gpl = ceil_div(cfg["slice_width"], 3)
cfg["slice_chunk_size"] = ceil_div(cfg["slice_width"] * cfg["bits_per_pixel"],
                                   8 * 16)
extra = 3 * (cfg["mux_word_size"] + (4 * cfg["bits_per_component"] + 4) - 2)
slice_bits = 8 * cfg["slice_chunk_size"] * cfg["slice_height"]
while extra > 0 and (slice_bits - extra) % cfg["mux_word_size"]:
    extra -= 1
if gpl < cfg["initial_scale_value"] - 8:
    cfg["initial_scale_value"] = gpl + 8
cfg["scale_decrement_interval"] = gpl // (cfg["initial_scale_value"] - 8)
cfg["final_offset"] = (cfg["rc_model_size"]
                       - (cfg["initial_xmit_delay"] * cfg["bits_per_pixel"] + 8) // 16
                       + extra)
final_scale = (cfg["rc_model_size"] * 8) // (cfg["rc_model_size"] - cfg["final_offset"])
cfg["nfl_bpg_offset"] = ceil_div(cfg["first_line_bpg_offset"] << 11,
                                 cfg["slice_height"] - 1)
groups_total = gpl * cfg["slice_height"]
cfg["slice_bpg_offset"] = ceil_div(
    (cfg["rc_model_size"] - cfg["initial_offset"] + extra) << 11, groups_total)
cfg["scale_increment_interval"] = (
    (cfg["final_offset"] << 11) //
    ((cfg["nfl_bpg_offset"] + cfg["slice_bpg_offset"]) * (final_scale - 9))
) if final_scale > 9 else 0

bad = []
for key, want in sorted(EXPECTED.items()):
    got = cfg.get(key)
    if got != want:
        bad.append("  %-26s model %-8s wzor producenta %s" % (key, got, want))

# --- 3. pola sprzetowe, ktorych model nie ma ---------------------------------

if "enc->comp_cfg = 0x30;" not in body:
    bad.append("  comp_cfg nie jest 0x30")
if "enc->rc_range_parameters = 0x0102;" not in body:
    bad.append("  rc_range_parameters nie jest 0x0102")
if ("enc->initial_dec_delay = 0x%x;" % EXPECTED_HW["initial_dec_delay"]) not in body:
    bad.append("  initial_dec_delay nie jest nadpisane na 0x%x"
               % EXPECTED_HW["initial_dec_delay"])
if "UNVERIFIED: The vendor writes 0x1b4" not in body:
    bad.append("  brak adnotacji UNVERIFIED przy initial_dec_delay")

# width_per_enc: skompresowana szerokosc, podwojona przy dual_slice.
#
# Sprawdzenie "czy w ciele wystepuje 3" bylo za slabe i przepuscilo realny
# rozjazd: producent w galezi z niezerowa reszta uzywa petli, ktora
# INKREMENTUJE PRZED sprawdzeniem warunku (decon_reg.c:1016-1021), wiec
# dla parzystej liczby pikseli dodaje dwa, a nasza wersja z `while (pixel_unit % 2)`
# nie dodawala nic. Dla tego panelu (slice_width 720) obie dawaly to samo.
#
# Teraz bramka odtwarza OBA wzory w Pythonie i porownuje je na calym
# zakresie szerokosci plastra, a cialo funkcji C jest przypiete.
def wzor_producenta(slice_width):
    """decon_reg.c:992-1028, przepisane wprost, razem z petla do-while."""
    comp_byte = slice_width * 3 // 3
    comp_pixel = comp_byte // 3
    i = comp_byte % 3
    j = comp_pixel % 2
    if i == 0 and j == 0:
        return comp_pixel
    if i == 0 and j != 0:
        return comp_pixel + 1
    while True:
        comp_pixel += 1
        if comp_pixel % 2 == 0:
            return comp_pixel


def wzor_nasz(slice_width):
    """Rownowaznik ze sterownika: round_up(slice_width / 3 [+1], 2)."""
    pixels = slice_width // 3
    if slice_width % 3:
        pixels += 1
    return pixels + (pixels % 2)


rozjazd = [w for w in range(1, 8193)
           if wzor_producenta(w) != wzor_nasz(w)]
if rozjazd:
    bad.append("  decon_dsc_compressed_width rozjezdza sie ze wzorem "
               "producenta dla %d szerokosci, pierwsza %d"
               % (len(rozjazd), rozjazd[0]))

CIALO_OCZEKIWANE = (
    "\n\tu32 pixels = slice_width / 3;\n"
    "\n"
    "\tif (slice_width % 3)\n"
    "\t\tpixels++;\n"
    "\n"
    "\treturn round_up(pixels, 2);")
wpe = re.search(r"decon_dsc_compressed_width\(u32 slice_width\)\s*\{(.*?)\n\}", src,
                re.S)
if not wpe:
    bad.append("  nie znaleziono decon_dsc_compressed_width")
elif wpe.group(1) != CIALO_OCZEKIWANE:
    bad.append("  cialo decon_dsc_compressed_width nie jest tym, ktore "
               "porownano ze wzorem producenta")

# --- 4. pola, ktore sterownik ustawia sam --------------------------------

# Wartosci EXPECTED_HW byly do tej pory tylko zadeklarowane, a bramka
# liczyla dlugosc slownika. Teraz kazda z nich jest porownana z tym, co
# realnie wynika ze sterownika dla tego panelu: dwa plastry na dwa enkodery.
SLICE_COUNT_PANELU = 2
ENKODEROW = 2

hw = {
    "width_per_enc": wzor_nasz(EXPECTED["slice_width"]),
    "dual_slice": int(SLICE_COUNT_PANELU // ENKODEROW == 2),
    "slice_mode_change": int(ENKODEROW == 2 and SLICE_COUNT_PANELU == 2),
    "initial_dec_delay": EXPECTED_HW["initial_dec_delay"],
}

# Wyrazenia, z ktorych te dwie wartosci wychodza, musza stac w sterowniku
# w tej postaci, inaczej liczba policzona wyzej opisywalaby inny kod.
for pat, msg in (
        (r"enc->dual_slice = \(panel_dsc->slice_count / dsc_count == 2\);",
         "dual_slice liczone inaczej niz zaklada bramka"),
        (r"enc->slice_mode_change = \(dsc_count == 2 &&\s*panel_dsc->slice_count == 2\);",
         "slice_mode_change liczone inaczej niz zaklada bramka")):
    if not re.search(pat, src, re.S):
        bad.append('  ' + msg)

for k, v in EXPECTED_HW.items():
    if hw[k] != v:
        bad.append("  %s: sterownik daje %s, bramka oczekuje %s"
                   % (k, hw[k], v))

if bad:
    print("check-decon-dsc: niezgodnosci")
    for b in bad:
        print(b)
    sys.exit(1)

print("check-decon-dsc: %d pol modelu zgodnych ze wzorem producenta, "
      "%d pol sprzetowych sprawdzonych w zrodle"
      % (len(EXPECTED), len(EXPECTED_HW)))
