#!/usr/bin/env python3
"""Tablica kalibracyjna PHY UFS w JADRZE wobec warstwy CAL producenta.

Blizniacza bramka do `check-ufs-phy-cal.py`. Tamta pilnuje sterownika
bootloadera z `patches-uboot/`, ta pilnuje sterownika jadra
`drivers/phy/samsung/phy-exynos9820-ufs.c` z `patches/`.

Po co osobna bramka, skoro wartosci sa te same. Bo przepisanie tablic z jednego
drzewa do drugiego jest dokladnie ta operacja, w ktorej literowka nie zostawia
sladu: kompilacja przechodzi, checkpatch przechodzi, a pamiec masowa albo nie
staje, albo staje niestabilnie. Do tego przy przepisaniu zmienil sie DIALEKT
makr (trzy argumenty zamiast dwoch, maska trybu zamiast maski biegu) i ksztalt
sekwencji (dwa oczekiwania wyszly z tablic do hakow sterownika), wiec porownanie
jednego sterownika z drugim nie wystarczy: obie wersje musza zgadzac sie
z producentem osobno.

Bramka idzie w obie strony:

  poprawnosc   kazdy wpis sterownika zgadza sie z linia producenta, ktora sam
               cytuje: adres (nasz numer rejestru razy cztery), wartosc, rodzaj
               wpisu i maska trybu zasilania;

  kompletnosc  kazda linia producenta nalezaca do warstw PHY i dotyczaca naszej
               plyty musi byc pokryta dokladnie raz, przy czym oczekiwania
               (PHY_EMB_CAL_WAIT, PHY_EMB_CDR_WAIT) sa pokryte nie wpisem
               tablicy, tylko stala sterownika, bo w jadrze wykonuja je haki.

Trzy rzeczy, ktore ta bramka pilnuje, a ktorych wersja bootloaderowa nie zna:

  * jedna linia producenta obejmujaca biegi 2 do 4 jest w jadrze rozpisana na
    trzy wpisy, bo kodowanie trybu w rdzeniu mainline trzyma jeden bieg na wpis.
    Bramka wymaga, zeby te trzy wpisy pokrywaly DOKLADNIE te biegi, ktore nazywa
    maska producenta, i zeby mialy te sama wartosc;

  * sterownik oznacza wpisy z maska PMD_HS jako PWR_MODE_ANY. To jest legalne
    tylko dlatego, ze takie linie wystepuja wylacznie w tablicach, ktore biegna
    przy przejsciu na tryb szybki. Bramka to SPRAWDZA, zamiast zakladac: linia
    PMD_HS w tablicy startu lacza zapala ja;

  * oba oczekiwania musza miec w sterowniku stala o tym samym rejestrze i tej
    samej masce co u producenta.

Kody wyjscia: 0 zgodne, 1 rozjazd, 2 bramka NIE URUCHOMIONA (brak zrodel).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ufs_cal

GATE = "check-ufs-phy-kernel"
SERIES = "patches"
PATCH_GLOB = "*-phy-samsung-ufs-Add-Exynos9820-support.patch"
DRIVER = "drivers/phy/samsung/phy-exynos9820-ufs.c"

# Nasza plyta, wedlug wezla ufs@0x13D60000 w sources/ds/exynos9820.dts:
#   evt-ver = [01]            druga rewizja krzemu  -> tablice *_evt1
#   ufs,pmd-attr-gear = [03]  bieg 3                -> wariant *_g3
#   brd-for-cal = [01]        BRD_ALL               -> bez linii BRD_ZEBU
TABLES = {
    "exynos9820_pre_init_cfg": "init_cfg_evt1",
    "exynos9820_post_init_cfg": "post_init_cfg_evt1_g3",
    "exynos9820_pre_pwr_hs_cfg": "calib_of_hs_rate_b",
    "exynos9820_post_pwr_hs_cfg": "post_calib_of_hs_rate_b",
    "exynos9820_post_h8_enter_cfg": "post_h8_enter",
    "exynos9820_pre_h8_exit_cfg": "pre_h8_exit",
}

# Tablice, ktore biegna dopiero przy przejsciu na tryb szybki. Tylko w nich
# maska PMD_HS wolno przelozyc na PWR_MODE_ANY, bo tam "dowolny" i "szybki"
# znacza to samo.
HS_ONLY_TABLES = {"calib_of_hs_rate_b", "post_calib_of_hs_rate_b"}

# Warstwy producenta nalezace do sterownika PHY.
PHY_LAYERS = {
    "PHY_PMA_COMN": "COMN",
    "PHY_PMA_TRSV": "TRSV",
    # Zapis na kazdy PODLACZONY pas odbiorczy; na tej plycie podlaczone sa
    # oba, wiec to zwykly wpis na pas.
    "PHY_PMA_TRSV_SQ": "TRSV",
    "COMMON_WAIT": "DELAY",
    "PHY_EMB_CAL_WAIT": "WAIT_CAL",
    "PHY_EMB_CDR_WAIT": "WAIT_CDR",
}

# Warstwy, ktorych w jadrze NIE MA w tablicy: wykonuja je haki sterownika,
# a pokrywa je stala wymieniona nizej.
WAIT_LAYERS = {
    "PHY_EMB_CAL_WAIT": "EXYNOS9820_CAL_DONE_STATUS",
    "PHY_EMB_CDR_WAIT": "EXYNOS9820_CDR_LOCK_STATUS",
}

# Maski trybu producenta przelozone na zbior oznaczen wpisow sterownika.
# Producent koduje w jednej masce tryb, bieg i liczbe pasow, ale jego wlasny
# dopasowywacz liczby pasow nie rozroznia, wiec po naszej stronie zostaje tryb
# i bieg.
PMD_TO_MODES = {
    "PMD_ALL": {"PWR_MODE_ANY"},
    "PMD_HS": {"PWR_MODE_ANY"},
    "PMD_HS_G1_L2": {"PWR_MODE_HS_G1_ANY"},
    "PMD_HS_G2_L2|PMD_HS_G3_L2|PMD_HS_G4_L2": {
        "PWR_MODE_HS_G2_ANY", "PWR_MODE_HS_G3_ANY", "PWR_MODE_HS_G4_ANY",
    },
}

HEX = r"(0x[0-9a-fA-F]+)"
ENTRY_RX = {
    "COMN": re.compile(r"^\s*PHY_COMN_REG_CFG\(%s,\s*%s,\s*(\w+)\)" % (HEX, HEX)),
    "TRSV": re.compile(r"^\s*PHY_TRSV_REG_CFG_9820\(%s,\s*%s,\s*(\w+)\)"
                       % (HEX, HEX)),
    "DELAY": re.compile(r"^\s*PHY_DELAY_CFG\((\d+)\)"),
}

TABLE_RX = re.compile(r"^static const struct samsung_ufs_phy_cfg (\w+)\[\]\s*=\s*\{")
CITE_RX = re.compile(r"/\*\s*:(\d+)\b")


def fail(msg):
    ufs_cal.fail(GATE, msg)


def parse_driver_tables(lines):
    """Zwraca {nazwa_tablicy: [wpis, ...]} razem z cytatem linii producenta."""
    tables, name = {}, None
    for line in lines:
        hit = TABLE_RX.match(line)
        if hit:
            name = hit.group(1)
            tables[name] = []
            continue
        if name is None:
            continue
        if line.startswith("};"):
            name = None
            continue

        for kind, rx in ENTRY_RX.items():
            hit = rx.match(line)
            if not hit:
                continue
            ref = CITE_RX.search(line)
            if not ref:
                fail("wpis bez cytatu linii producenta w %s: %s"
                     % (name, line.strip()))
            item = {
                "kind": kind,
                "line": int(ref.group(1)),
                "src": line.strip(),
            }
            if kind == "DELAY":
                item["reg"] = None
                item["val"] = int(hit.group(1))
                item["mode"] = "PWR_MODE_ANY"
            else:
                item["reg"] = int(hit.group(1), 16)
                item["val"] = int(hit.group(2), 16)
                item["mode"] = hit.group(3).strip()
            tables[name].append(item)
            break
    return tables


def sprawdz_oczekiwania(drv_lines, ven, cal_lines):
    """Oczekiwania nie sa w jadrze wpisami tablicy, tylko stalymi hakow."""
    maska = ufs_cal.const_from_driver(GATE, drv_lines, "EXYNOS9820_LOCK_BIT")
    hit = re.match(r"BIT\((\d+)\)$", maska.strip())
    if not hit:
        fail("EXYNOS9820_LOCK_BIT ma postac %s, oczekiwano BIT(n)" % maska)
    maska = 1 << int(hit.group(1))

    pokryte = set()
    for tabela, wiersze in ven.items():
        if tabela not in TABLES.values():
            continue
        for no, addr, val, pmd, layer, board in wiersze:
            if layer not in WAIT_LAYERS:
                continue
            if not ufs_cal.applies_to_board(board):
                continue
            stala = WAIT_LAYERS[layer]
            reg = int(ufs_cal.const_from_driver(GATE, drv_lines, stala), 16)
            if reg * 4 != addr:
                fail("%s to rejestr 0x%x, czyli bajt 0x%x, a producent czeka "
                     "na 0x%x (linia %d)" % (stala, reg, reg * 4, addr, no))
            if val != maska:
                fail("%s: producent czeka na maske 0x%02x, a sterownik ma "
                     "0x%02x (linia %d)" % (stala, val, maska, no))
            pokryte.add(no)

    for layer, stala in WAIT_LAYERS.items():
        if not any(w[4] == layer for t in ven.values() for w in t):
            fail("producent nie ma ani jednej linii warstwy %s, a sterownik "
                 "trzyma dla niej stala %s" % (layer, stala))
    return pokryte


def main():
    if not ufs_cal.sources_present():
        ufs_cal.skip(GATE, "brak zrodel producenta w sources/ds, "
                           "uruchom scripts/fetch-sources.sh")

    drv_lines = ufs_cal.read_driver_from_patch(GATE, PATCH_GLOB, DRIVER,
                                               series=SERIES)
    drv = parse_driver_tables(drv_lines)
    cal_text = ufs_cal.vendor_text()
    cal_lines = cal_text.splitlines()
    ven = ufs_cal.parse_vendor_tables(GATE, cal_text)

    pokryte_stalymi = sprawdz_oczekiwania(drv_lines, ven, cal_lines)

    checked = 0
    rozpisane = 0
    for our_name, their_name in TABLES.items():
        if our_name not in drv:
            fail("sterownik nie ma tablicy %s" % our_name)
        if their_name not in ven:
            fail("producent nie ma tablicy %s" % their_name)

        by_line = {row[0]: row for row in ven[their_name]}
        wanted = {no for (no, _a, _v, _p, layer, board) in ven[their_name]
                  if layer in PHY_LAYERS and ufs_cal.applies_to_board(board)}

        # Wpisy zebrane po cytowanej linii, bo jedna linia producenta moze byc
        # rozpisana na kilka wpisow roznych biegow.
        wg_linii = {}
        for item in drv[our_name]:
            wg_linii.setdefault(item["line"], []).append(item)

        for no, items in sorted(wg_linii.items()):
            row = by_line.get(no)
            if row is None:
                fail("%s: cytat ufs-cal-9820.c:%d nie jest wpisem tablicy %s\n  %s"
                     % (our_name, no, their_name, items[0]["src"]))
            _no, addr, val, pmd, layer, board = row

            if layer not in PHY_LAYERS:
                fail("%s: cytowana linia %d jest warstwy %s, nalezy do hosta\n  %s"
                     % (our_name, no, layer, items[0]["src"]))
            if layer in WAIT_LAYERS:
                fail("%s: linia %d jest oczekiwaniem, w jadrze robi to hak, "
                     "a nie wpis tablicy\n  %s"
                     % (our_name, no, items[0]["src"]))
            if PHY_LAYERS[layer] != items[0]["kind"]:
                fail("%s: linia %d jest %s, a wpis jest %s\n  %s"
                     % (our_name, no, PHY_LAYERS[layer], items[0]["kind"],
                        items[0]["src"]))
            if not ufs_cal.applies_to_board(board):
                fail("%s: linia %d ma maske plyty %s, nie dotyczy naszej\n  %s"
                     % (our_name, no, board, items[0]["src"]))

            want_modes = PMD_TO_MODES.get(pmd)
            if want_modes is None:
                fail("%s: nieznana maska trybu %s w linii %d, dopisz ja do "
                     "PMD_TO_MODES razem z uzasadnieniem" % (our_name, pmd, no))
            # Poza tablicami trybu szybkiego PWR_MODE_ANY byloby za szerokie:
            # tam linia PMD_HS musi byc ograniczona do trybu szybkiego wprost.
            if pmd == "PMD_HS" and their_name not in HS_ONLY_TABLES:
                want_modes = {"PWR_MODE_HS_ANY"}

            have_modes = {it["mode"] for it in items}
            if have_modes != want_modes:
                fail("%s: linia %d ma maske %s, czyli %s, a sterownik pokrywa "
                     "ja przez %s\n  %s"
                     % (our_name, no, pmd, ", ".join(sorted(want_modes)),
                        ", ".join(sorted(have_modes)), items[0]["src"]))
            if len(items) != len(have_modes):
                fail("%s: linia %d zacytowana %d razy, a roznych oznaczen jest "
                     "%d\n  %s" % (our_name, no, len(items), len(have_modes),
                                   items[0]["src"]))
            if len(items) > 1:
                rozpisane += 1

            for item in items:
                if item["kind"] == "DELAY":
                    # Producent trzyma opoznienie w polu wartosci.
                    if val != item["val"]:
                        fail("%s: opoznienie %d us, producent %d us (linia %d)"
                             "\n  %s" % (our_name, item["val"], val, no,
                                         item["src"]))
                else:
                    if item["reg"] * 4 != addr:
                        fail("%s: rejestr 0x%x to bajt 0x%x, producent ma 0x%x "
                             "(linia %d)\n  %s"
                             % (our_name, item["reg"], item["reg"] * 4, addr,
                                no, item["src"]))
                    if item["val"] != val:
                        fail("%s: wartosc 0x%02x, producent 0x%02x (linia %d)"
                             "\n  %s" % (our_name, item["val"], val, no,
                                         item["src"]))
                checked += 1

        missing = sorted(wanted - set(wg_linii) - pokryte_stalymi)
        if missing:
            detail = "\n".join("    ufs-cal-9820.c:%d  %s"
                               % (no, cal_lines[no - 1].strip())
                               for no in missing)
            fail("%s: pominieto %d linii producenta z tablicy %s:\n%s"
                 % (our_name, len(missing), their_name, detail))

    # Odstep pasow, ta sama liczba co u producenta, tylko liczona w rejestrach.
    hit = re.search(r"#define\s+PHY_PMA_TRSV_ADDR\(reg,\s*lane\)\s*"
                    r"\(\(reg\)\s*\+\s*\((0x[0-9a-fA-F]+)\s*\*\s*\(lane\)\)\)",
                    cal_text)
    if not hit:
        fail("nie znalazlem PHY_PMA_TRSV_ADDR w ufs-cal-9820.c")
    stride_bytes = int(hit.group(1), 16)
    ours = ufs_cal.const_from_driver(GATE, drv_lines, "EXYNOS9820_LANE_OFFSET")
    if ours != "(0x%x / 4)" % stride_bytes:
        fail("odstep pasow: sterownik ma %s, producent %s bajtow"
             % (ours, hex(stride_bytes)))

    # Offset izolacji PHY w bloku PMU.
    host = ufs_cal.VENDOR_HOST.read_text(encoding="utf-8", errors="replace")
    hit = re.search(r"#define\s+EXYNOS_PMU_UFS_PHY_OFFSET\s+(0x[0-9a-fA-F]+)", host)
    if not hit:
        fail("nie znalazlem EXYNOS_PMU_UFS_PHY_OFFSET w ufs-exynos.h")
    if int(ufs_cal.const_from_driver(GATE, drv_lines, "EXYNOS9820_PHY_CTRL"), 16) \
            != int(hit.group(1), 16):
        fail("offset izolacji PMU rozjezdza sie z ufs-exynos.h")

    # Sterownik nie rozroznia serii HS, bo tablice producenta sa identyczne.
    for a, b in (("calib_of_hs_rate_a", "calib_of_hs_rate_b"),
                 ("post_calib_of_hs_rate_a", "post_calib_of_hs_rate_b")):
        if [row[1:] for row in ven[a]] != [row[1:] for row in ven[b]]:
            fail("tablice %s i %s NIE sa identyczne, sterownik musi rozrozniac "
                 "serie HS" % (a, b))

    print("%s: wpisow zgodnych z producentem %d, tablic %d, linii rozpisanych "
          "na biegi %d, oczekiwan pokrytych stalymi %d, serie HS identyczne"
          % (GATE, checked, len(TABLES), rozpisane, len(pokryte_stalymi)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
