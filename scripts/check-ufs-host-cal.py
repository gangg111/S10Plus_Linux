#!/usr/bin/env python3
"""Tablice kalibracyjne hosta UFS wobec warstwy CAL producenta.

Blizniacza bramka do `check-ufs-phy-cal.py`. Tamta pilnuje warstwy PMA, ktora
trafila do sterownika PHY; ta pilnuje warstw, ktore ida przez DME i przez okno
UniPro, czyli tego, co trafilo do sterownika hosta
`drivers/ufs/ufs-exynos.c` z `patches-uboot/0005-*.patch`.

Sprawdza trzy rzeczy:

  poprawnosc   kazdy wpis sterownika zgadza sie z linia producenta, ktora sam
               cytuje: adres, rodzaj wpisu i, dla wpisow z wartoscia wprost,
               takze wartosc. Wpisy o wartosci LICZONEJ z czestotliwosci zegara
               maja u producenta w tym polu zero jako atrape i wartosci sie im
               nie porownuje, za to sprawdza sie, ze atrapa nadal jest zerem;

  kompletnosc  kazda linia producenta nalezaca do warstw hosta i dotyczaca
               naszej plyty musi byc zacytowana dokladnie raz;

  kolejnosc    przekazanie sterowania do PHY musi stac dokladnie tam, gdzie
               u producenta stoi jego blok zapisow PMA. Bez tego wpisy hosta,
               ktore u producenta OTACZAJA ten blok, moglyby wyladowac po zlej
               jego stronie. Dotyczy to zwlaszcza pary zapisow atrybutu 0xA006
               w tablicy po-linkowej, ktora blok PMA ma miec w srodku.

Parser tablic producenta jest wspolny z bramka PHY, patrz `scripts/ufs_cal.py`.

Kody wyjscia: 0 zgodne, 1 rozjazd, 2 bramka NIE URUCHOMIONA (brak zrodel).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ufs_cal

GATE = "check-ufs-host-cal"
PATCH_GLOB = "0005-ufs-exynos-add-the-host-controller-driver-for-Exynos.patch"
DRIVER = "drivers/ufs/ufs-exynos.c"

# Tablica sterownika, tablica producenta, oraz punkt kalibracji, ktory ta
# tablica przekazuje sterownikowi PHY.
TABLES = {
    "exynos9820_pre_link_cfg": ("init_cfg_evt1", "UFS_PHY_PRE_LINK"),
    "exynos9820_post_link_cfg": ("post_init_cfg_evt1_g3", "UFS_PHY_POST_LINK"),
    "exynos9820_pre_pwr_cfg": ("calib_of_hs_rate_b", "UFS_PHY_PRE_PWR_HS"),
    "exynos9820_post_pwr_cfg": ("post_calib_of_hs_rate_b", "UFS_PHY_POST_PWR_HS"),
}

# Warstwy producenta nalezace do hosta, przelozone na rodzaj wpisu sterownika.
# Celowo NIE MA tu PHY_PCS_RX_PRD ani PHY_PCS_TX_PRD (bez zaokraglenia): nasze
# tablice ich nie zawieraja, a licza sie innym wzorem niz warianty
# ROUND_OFF, wiec gdyby kiedys doszly, bramka ma o nie zapytac, a nie
# domyslnie potraktowac je jak tamte.
HOST_LAYERS = {
    "PHY_PCS_COMN": "DME",
    "UNIPRO_STD_MIB": "DME",
    "UNIPRO_DBG_MIB": "DME",
    "PHY_PCS_RX": "DME_RX",
    "PHY_PCS_TX": "DME_TX",
    "PHY_PCS_RX_PRD_ROUND_OFF": "DME_RX_PRD",
    "PHY_PCS_TX_PRD_ROUND_OFF": "DME_TX_PRD",
    "PHY_PCS_RX_LR_PRD": "DME_RX_LR",
    "PHY_PCS_TX_LR_PRD": "DME_TX_LR",
    "UNIPRO_DBG_APB": "UNIPRO",
    "UNIPRO_DBG_PRD": "UNIPRO_PRD",
    "UNIPRO_ADAPT_LENGTH": "ADAPT_LEN",
}

# Warstwy, ktore naleza do sterownika PHY. Tu sluza tylko do wyznaczenia,
# gdzie u producenta zaczyna sie i konczy blok PMA.
PMA_LAYERS = {
    "PHY_PMA_COMN", "PHY_PMA_TRSV", "PHY_PMA_TRSV_SQ",
    "PHY_PMA_TRSV_LANE1_SQ_OFF", "COMMON_WAIT", "PHY_EMB_CAL_WAIT",
    "PHY_EMB_CDR_WAIT", "PHY_PLL_WAIT", "PHY_CDR_WAIT", "PHY_CDR_AFC_WAIT",
}

# Rodzaje, ktorych wartosc jest LICZONA z czestotliwosci zegara UniPro.
# U producenta pole wartosci jest dla nich atrapa.
COMPUTED = {"DME_RX_PRD", "DME_TX_PRD", "DME_RX_LR", "DME_TX_LR",
            "UNIPRO_PRD", "ADAPT_LEN"}

# Maski trybu zasilania, ktore dotycza naszej plyty. Nasza plyta pracuje
# w trybie szybkim (FAST_MODE), wiec zarowno wpisy wspolne, jak i wpisy
# oznaczone jako szybkie sa wykonywane.
PMD_OURS = {"PMD_ALL", "PMD_HS"}

NUM = r"(0x[0-9a-fA-F]+|\d+)"
ENTRY_RX = {
    "DME": re.compile(r"^\s*DME_CFG\(%s,\s*%s\)" % (NUM, NUM)),
    "DME_RX": re.compile(r"^\s*DME_RX_CFG\(%s,\s*%s\)" % (NUM, NUM)),
    "DME_TX": re.compile(r"^\s*DME_TX_CFG\(%s,\s*%s\)" % (NUM, NUM)),
    "DME_RX_PRD": re.compile(r"^\s*DME_RX_PRD_CFG\(%s\)" % NUM),
    "DME_TX_PRD": re.compile(r"^\s*DME_TX_PRD_CFG\(%s\)" % NUM),
    "DME_RX_LR": re.compile(r"^\s*DME_RX_LR_CFG\(%s\)" % NUM),
    "DME_TX_LR": re.compile(r"^\s*DME_TX_LR_CFG\(%s\)" % NUM),
    "UNIPRO": re.compile(r"^\s*UNIPRO_CFG\(%s,\s*%s\)" % (NUM, NUM)),
    "UNIPRO_PRD": re.compile(r"^\s*UNIPRO_PRD_CFG\(%s\)" % NUM),
    "ADAPT_LEN": re.compile(r"^\s*ADAPT_LEN_CFG\(%s\)" % NUM),
}
PHY_RX = re.compile(r"^\s*PHY_CFG\((\w+)\)")

TABLE_RX = re.compile(r"^static const struct exynos_ufs_cfg (\w+)\[\]\s*=\s*\{")
CITE_RX = re.compile(r"/\*\s*:(\d+)\b")


def fail(msg):
    ufs_cal.fail(GATE, msg)


def num(text):
    return int(text, 16) if text.lower().startswith("0x") else int(text)


def parse_driver_tables(lines):
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

        hit = PHY_RX.match(line)
        if hit:
            tables[name].append({"kind": "PHY", "step": hit.group(1),
                                 "src": line.strip()})
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
                "addr": num(hit.group(1)),
                "val": num(hit.group(2)) if kind not in COMPUTED else None,
                "line": int(ref.group(1)),
                "src": line.strip(),
            }
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

    checked, computed = 0, 0
    for our_name, (their_name, step) in TABLES.items():
        if our_name not in drv:
            fail("sterownik nie ma tablicy %s" % our_name)
        if their_name not in ven:
            fail("producent nie ma tablicy %s" % their_name)

        rows = ven[their_name]
        by_line = {row[0]: row for row in rows}
        ours_rows = [r for r in rows if ufs_cal.applies_to_board(r[5])
                     and r[3] in PMD_OURS]
        wanted = {r[0] for r in ours_rows if r[4] in HOST_LAYERS}
        pma_lines = [r[0] for r in ours_rows if r[4] in PMA_LAYERS]

        # Maski, o ktorych bramka nic nie wie, maja zatrzymac przeglad,
        # a nie zostac po cichu odsiane.
        for r in rows:
            if ufs_cal.applies_to_board(r[5]) and r[3] not in PMD_OURS:
                if r[4] in HOST_LAYERS:
                    fail("%s: linia %d ma maske trybu %s, ktorej bramka nie zna; "
                         "rozstrzygnij, czy dotyczy naszej plyty"
                         % (our_name, r[0], r[3]))

        cited, phy_seen, phy_at = set(), 0, None
        for pos, item in enumerate(drv[our_name]):
            if item["kind"] == "PHY":
                if item["step"] != step:
                    fail("%s: przekazanie do PHY ma punkt %s, a tablica "
                         "odpowiada punktowi %s" % (our_name, item["step"], step))
                phy_seen += 1
                phy_at = pos
                continue

            row = by_line.get(item["line"])
            if row is None:
                fail("%s: cytat ufs-cal-9820.c:%d nie jest wpisem tablicy %s\n  %s"
                     % (our_name, item["line"], their_name, item["src"]))
            no, addr, val, pmd, layer, board = row

            if layer not in HOST_LAYERS:
                fail("%s: cytowana linia %d jest warstwy %s, nalezy do PHY\n  %s"
                     % (our_name, no, layer, item["src"]))
            if HOST_LAYERS[layer] != item["kind"]:
                fail("%s: linia %d jest %s, a wpis jest %s\n  %s"
                     % (our_name, no, HOST_LAYERS[layer], item["kind"],
                        item["src"]))
            if not ufs_cal.applies_to_board(board):
                fail("%s: linia %d ma maske plyty %s, nie dotyczy naszej\n  %s"
                     % (our_name, no, board, item["src"]))
            if pmd not in PMD_OURS:
                fail("%s: linia %d ma maske trybu %s, nie dotyczy naszej\n  %s"
                     % (our_name, no, pmd, item["src"]))
            if no in cited:
                fail("%s: linia %d zacytowana dwa razy\n  %s"
                     % (our_name, no, item["src"]))
            cited.add(no)

            if addr != item["addr"]:
                fail("%s: adres 0x%x, producent 0x%x (linia %d)\n  %s"
                     % (our_name, item["addr"], addr, no, item["src"]))

            if item["kind"] in COMPUTED:
                # Producent trzyma tu atrape, a wartosc podstawia dyspozytor.
                # Gdyby atrapa przestala byc zerem, znaczyloby to, ze wpis
                # jednak niesie dane i nasz sterownik je gubi.
                if val != 0:
                    fail("%s: linia %d jest liczona, a producent ma w niej "
                         "0x%x zamiast atrapy\n  %s"
                         % (our_name, no, val, item["src"]))
                computed += 1
            elif val != item["val"]:
                fail("%s: wartosc %d, producent %d (linia %d)\n  %s"
                     % (our_name, item["val"], val, no, item["src"]))
            checked += 1

        missing = sorted(wanted - cited)
        if missing:
            detail = "\n".join("    ufs-cal-9820.c:%d  %s"
                               % (no, cal_lines[no - 1].strip())
                               for no in missing)
            fail("%s: pominieto %d linii producenta z tablicy %s:\n%s"
                 % (our_name, len(missing), their_name, detail))

        # Przekazanie do PHY: dokladnie jedno, i w tym samym miejscu
        # sekwencji, w ktorym u producenta lezy blok PMA.
        if not pma_lines:
            if phy_seen:
                fail("%s: tablica producenta %s nie ma wpisow PMA, a sterownik "
                     "przekazuje sterowanie do PHY" % (our_name, their_name))
            continue
        if phy_seen != 1:
            fail("%s: przekazan do PHY jest %d, ma byc dokladnie jedno"
                 % (our_name, phy_seen))

        first_pma, last_pma = min(pma_lines), max(pma_lines)
        for pos, item in enumerate(drv[our_name]):
            if item["kind"] == "PHY":
                continue
            if pos < phy_at and item["line"] > first_pma:
                fail("%s: wpis z linii %d stoi PRZED przekazaniem do PHY, "
                     "a u producenta jest PO bloku PMA (od linii %d)\n  %s"
                     % (our_name, item["line"], first_pma, item["src"]))
            if pos > phy_at and item["line"] < last_pma:
                fail("%s: wpis z linii %d stoi PO przekazaniu do PHY, "
                     "a u producenta jest PRZED blokiem PMA (do linii %d)\n  %s"
                     % (our_name, item["line"], last_pma, item["src"]))

    print("%s: wpisow zgodnych z producentem %d (w tym liczonych z zegara %d), "
          "tablic %d, przekazania do PHY na wlasciwych miejscach"
          % (GATE, checked, computed, len(TABLES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
