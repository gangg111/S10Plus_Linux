#!/usr/bin/env python3
"""Tablica kalibracyjna PHY UFS wobec warstwy CAL producenta.

Sterownik `drivers/phy/phy-exynos9820-ufs.c` z `patches-uboot/0004-*.patch`
przepisuje wpisy warstwy PMA z `drivers/scsi/ufs/ufs-cal-9820.c`. Bez bramki taki
przepis jest nie do sprawdzenia: zla wartosc nie psuje kompilacji, nie rusza
checkpatcha i nie zostawia sladu w logu, tylko daje pamiec, ktora nie startuje
albo startuje niestabilnie.

Bramka idzie w OBIE strony, bo kazda z nich lapie inny rodzaj bledu:

  poprawnosc   kazdy wpis sterownika musi zgadzac sie z linia producenta,
               ktora sam cytuje: adres (nasz numer rejestru razy cztery),
               wartosc, rodzaj wpisu i maska biegow;

  kompletnosc  kazda linia producenta, ktora DOTYCZY naszej plyty, musi byc
               zacytowana dokladnie raz. To jest wazniejsza polowa: fork
               `chiffathefox/u-boot` mial wszystkie przepisane wartosci
               poprawne, a mimo to gubil wpisy calych tablic i czekania,
               czego porownanie "tylko tego, co jest" nigdy by nie pokazalo.

Dodatkowo sprawdzane sa cztery stale, ktorych zle odczytanie ze zrodel
producenta jest latwe i ciche:

  * odstep miedzy bankami rejestrow pasow (producent ma DWA sprzeczne makra
    o tej samej nazwie, zywe jest to z pliku 9820),
  * offset rejestru izolacji PHY w bloku PMU,
  * zasieg okna PMA, ktore musi pokryc wyzszy pas,
  * rownosc tablic serii HS-A i HS-B, na ktorej sterownik opiera brak
    rozroznienia serii.

Parser tablic producenta jest wspolny z bramka hosta, patrz `scripts/ufs_cal.py`.

Kody wyjscia: 0 zgodne, 1 rozjazd, 2 bramka NIE URUCHOMIONA (brak zrodel).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ufs_cal

GATE = "check-ufs-phy-cal"
PATCH_GLOB = "0004-phy-samsung-add-the-UFS-PHY-driver-for-Exynos9820.patch"
DRIVER = "drivers/phy/phy-exynos9820-ufs.c"

# Nasza plyta, wedlug wezla ufs@0x13D60000 w sources/ds/exynos9820.dts:
#   evt-ver = [01]            druga rewizja krzemu  -> tablice *_evt1
#   ufs,pmd-attr-gear = [03]  bieg 3                -> wariant *_g3
#   brd-for-cal = [01]        BRD_ALL               -> bez linii BRD_ZEBU
#   ufs,pmd-attr-lane = [02]  dwa pasy
TABLES = {
    "exynos9820_pre_link_cfg": "init_cfg_evt1",
    "exynos9820_post_link_cfg": "post_init_cfg_evt1_g3",
    "exynos9820_pre_pwr_hs_cfg": "calib_of_hs_rate_b",
    "exynos9820_post_pwr_hs_cfg": "post_calib_of_hs_rate_b",
}

# Warstwy producenta, ktore nalezą do sterownika PHY. Reszta (PHY_PCS_*,
# UNIPRO_*) idzie przez DME i przez okno UniPro, wiec jest robota sterownika
# hosta i pilnuje jej bramka check-ufs-host-cal.py.
PHY_LAYERS = {
    "PHY_PMA_COMN": "COMN",
    "PHY_PMA_TRSV": "TRSV",
    "COMMON_WAIT": "DELAY",
    "PHY_EMB_CAL_WAIT": "WAIT_CAL",
    "PHY_EMB_CDR_WAIT": "WAIT_CDR",
}

# Maski trybu zasilania producenta przelozone na maske biegow sterownika.
# Producent koduje w jednej masce tryb, bieg i liczbe pasow, ale jego wlasny
# dopasowywacz (__match_mode_by_cfg) liczby pasow nie rozroznia: dla biegu N
# sprawdza (PMD_HS_GN_L1 | PMD_HS_GN_L2) niezaleznie od tego, ile pasow jest
# podlaczonych. Dlatego po naszej stronie zostaje sam bieg.
PMD_TO_GEAR = {
    "PMD_ALL": "PHY_GEAR_ANY",
    "PMD_HS": "PHY_GEAR_ANY",
    "PMD_HS_G1_L2": "PHY_GEAR(1)",
    "PMD_HS_G2_L2|PMD_HS_G3_L2|PMD_HS_G4_L2": "PHY_GEAR_2_TO_4",
}

ENTRY_RX = {
    "COMN": re.compile(r"^\s*PHY_COMN_REG_CFG\((0x[0-9a-fA-F]+),\s*"
                       r"(0x[0-9a-fA-F]+)\)"),
    "TRSV": re.compile(r"^\s*PHY_TRSV_CFG\((0x[0-9a-fA-F]+),\s*"
                       r"(0x[0-9a-fA-F]+)\)"),
    "TRSV_GEAR": re.compile(r"^\s*PHY_TRSV_CFG_GEAR\((0x[0-9a-fA-F]+),\s*"
                            r"(0x[0-9a-fA-F]+),\s*(.+)\)\s*,"),
    "DELAY": re.compile(r"^\s*PHY_DELAY_CFG\((\d+)\)"),
    "WAIT_CAL": re.compile(r"^\s*PHY_WAIT_CAL_CFG\((0x[0-9a-fA-F]+),\s*"
                           r"(0x[0-9a-fA-F]+)\)"),
    "WAIT_CDR": re.compile(r"^\s*PHY_WAIT_CDR_CFG\((0x[0-9a-fA-F]+),\s*"
                           r"(0x[0-9a-fA-F]+)\)"),
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
                "kind": "TRSV" if kind == "TRSV_GEAR" else kind,
                "gear": (hit.group(3).strip() if kind == "TRSV_GEAR"
                         else "PHY_GEAR_ANY"),
                "line": int(ref.group(1)),
                "src": line.strip(),
            }
            if kind == "DELAY":
                item["reg"] = None
                item["val"] = int(hit.group(1))
            else:
                item["reg"] = int(hit.group(1), 16)
                item["val"] = int(hit.group(2), 16)
            tables[name].append(item)
            break
    return tables


def main():
    if not ufs_cal.sources_present():
        ufs_cal.skip(GATE, "brak zrodel producenta w sources/ds, "
                           "uruchom scripts/fetch-sources.sh")

    drv_lines = ufs_cal.read_driver_from_patch(GATE, PATCH_GLOB, DRIVER)
    drv = parse_driver_tables(drv_lines)
    cal_text = ufs_cal.vendor_text()
    cal_lines = cal_text.splitlines()
    ven = ufs_cal.parse_vendor_tables(GATE, cal_text)

    checked = 0
    for our_name, their_name in TABLES.items():
        if our_name not in drv:
            fail("sterownik nie ma tablicy %s" % our_name)
        if their_name not in ven:
            fail("producent nie ma tablicy %s" % their_name)

        by_line = {row[0]: row for row in ven[their_name]}
        wanted = {no for (no, _a, _v, _p, layer, board) in ven[their_name]
                  if layer in PHY_LAYERS and ufs_cal.applies_to_board(board)}
        cited = set()

        for item in drv[our_name]:
            row = by_line.get(item["line"])
            if row is None:
                fail("%s: cytat ufs-cal-9820.c:%d nie jest wpisem tablicy %s\n  %s"
                     % (our_name, item["line"], their_name, item["src"]))
            no, addr, val, pmd, layer, board = row

            if layer not in PHY_LAYERS:
                fail("%s: cytowana linia %d jest warstwy %s, nalezy do hosta\n  %s"
                     % (our_name, no, layer, item["src"]))
            if PHY_LAYERS[layer] != item["kind"]:
                fail("%s: linia %d jest %s, a wpis jest %s\n  %s"
                     % (our_name, no, PHY_LAYERS[layer], item["kind"], item["src"]))
            if not ufs_cal.applies_to_board(board):
                fail("%s: linia %d ma maske plyty %s, nie dotyczy naszej\n  %s"
                     % (our_name, no, board, item["src"]))
            if no in cited:
                fail("%s: linia %d zacytowana dwa razy\n  %s"
                     % (our_name, no, item["src"]))
            cited.add(no)

            if item["kind"] == "DELAY":
                # Producent trzyma opoznienie w polu wartosci, adres jest pusty.
                if val != item["val"]:
                    fail("%s: opoznienie %d us, producent %d us (linia %d)\n  %s"
                         % (our_name, item["val"], val, no, item["src"]))
            else:
                if item["reg"] * 4 != addr:
                    fail("%s: rejestr 0x%x to bajt 0x%x, producent ma 0x%x "
                         "(linia %d)\n  %s"
                         % (our_name, item["reg"], item["reg"] * 4, addr, no,
                            item["src"]))
                if item["val"] != val:
                    fail("%s: wartosc 0x%02x, producent 0x%02x (linia %d)\n  %s"
                         % (our_name, item["val"], val, no, item["src"]))

            want_gear = PMD_TO_GEAR.get(pmd)
            if want_gear is None:
                fail("%s: nieznana maska trybu %s w linii %d, dopisz ja do "
                     "PMD_TO_GEAR razem z uzasadnieniem" % (our_name, pmd, no))
            if want_gear != item["gear"]:
                fail("%s: maska %s znaczy %s, a wpis ma %s (linia %d)\n  %s"
                     % (our_name, pmd, want_gear, item["gear"], no, item["src"]))
            checked += 1

        missing = sorted(wanted - cited)
        if missing:
            detail = "\n".join("    ufs-cal-9820.c:%d  %s"
                               % (no, cal_lines[no - 1].strip())
                               for no in missing)
            fail("%s: pominieto %d linii producenta z tablicy %s:\n%s"
                 % (our_name, len(missing), their_name, detail))

    # Odstep pasow. Producent ma dwa sprzeczne makra o tej samej nazwie:
    # zywe jest to z pliku 9820, martwe to z ufs-exynos.h (0x140, bez ani
    # jednego wolania w drzewie).
    hit = re.search(r"#define\s+PHY_PMA_TRSV_ADDR\(reg,\s*lane\)\s*"
                    r"\(\(reg\)\s*\+\s*\((0x[0-9a-fA-F]+)\s*\*\s*\(lane\)\)\)",
                    cal_text)
    if not hit:
        fail("nie znalazlem PHY_PMA_TRSV_ADDR w ufs-cal-9820.c")
    stride_bytes = int(hit.group(1), 16)
    ours = ufs_cal.const_from_driver(GATE, drv_lines, "EXYNOS9820_LANE_STRIDE")
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

    # Okno PMA musi pokryc wyzszy pas.
    top = max(item["reg"] * 4 for tab in drv.values() for item in tab
              if item["reg"] is not None)
    need = top + stride_bytes + 4
    span = int(ufs_cal.const_from_driver(GATE, drv_lines,
                                         "EXYNOS9820_PMA_SPAN"), 16)
    if span < need:
        fail("zasieg PMA 0x%x, a tablice siegaja 0x%x" % (span, need))

    # Sterownik nie rozroznia serii HS, bo tablice producenta sa identyczne.
    for a, b in (("calib_of_hs_rate_a", "calib_of_hs_rate_b"),
                 ("post_calib_of_hs_rate_a", "post_calib_of_hs_rate_b")):
        if [row[1:] for row in ven[a]] != [row[1:] for row in ven[b]]:
            fail("tablice %s i %s NIE sa identyczne, sterownik musi rozrozniac "
                 "serie HS" % (a, b))

    print("%s: wpisow zgodnych z producentem %d, tablic %d, zasieg PMA 0x%x "
          "wobec wymaganych 0x%x, serie HS identyczne"
          % (GATE, checked, len(TABLES), span, need))
    return 0


if __name__ == "__main__":
    sys.exit(main())
