"""Wspolne czytanie warstwy kalibracyjnej UFS producenta.

Uzywaja tego dwie bramki: `check-ufs-phy-cal.py` (warstwa PMA, sterownik PHY)
i `check-ufs-host-cal.py` (warstwy PCS i UniPro, sterownik hosta). Parser jest
JEDEN, bo dziura w nim jest dziura w obu bramkach naraz: wzorzec wymagajacy
przedrostka `0x` w polu wartosci nie widzial wpisow zapisanych dziesietnie
i przez to polowa "kompletnosc" nie miala jak ich zazadac. Poprawka w jednym
miejscu jest wtedy poprawka dla obu bramek.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR_CAL = ROOT / "sources" / "ds" / "ufs-cal-9820.c"
VENDOR_HOST = ROOT / "sources" / "ds" / "ufs-exynos.h"

# Wartosc bywa zapisana DZIESIETNIE, nie tylko szesnastkowo: tablica pre-PMC ma
# wpisy w rodzaju {0x2041, 8064, ...}.
VENDOR_ENTRY = re.compile(
    r"^\s*\{\s*(0[xX][0-9A-Fa-f]+)\s*,"          # adres
    r"\s*(0[xX][0-9A-Fa-f]+|\d+)\s*,"            # wartosc, hex albo dziesietnie
    r"\s*([A-Za-z0-9_|^ ]+?)\s*,"                # maska trybu zasilania
    r"\s*([A-Za-z0-9_]+)\s*,"                    # warstwa
    r"\s*([A-Za-z0-9_|^ ]+?)\s*\}\s*,"           # maska plyty
)

# Wiersz, ktory WYGLADA na wpis tablicy. Sluzy wylacznie do sprawdzenia, czy
# wzorzec wyzej rozebral wszystko: wzorzec, ktory czegos nie rozumie, ma
# krzyczec, a nie cicho pomijac.
VENDOR_ENTRY_SHAPE = re.compile(r"^\s*\{\s*0[xX][0-9A-Fa-f]+\s*,")

TABLE_START = re.compile(r"^static\s+(?:const\s+)?struct ufs_cal_phy_cfg (\w+)\[\]")


def fail(gate, msg):
    print("%s: %s" % (gate, msg))
    sys.exit(1)


def skip(gate, msg):
    print("%s: BRAMKA NIEURUCHOMIONA, %s" % (gate, msg))
    sys.exit(2)


def sources_present():
    return VENDOR_CAL.exists() and VENDOR_HOST.exists()


def vendor_text():
    return VENDOR_CAL.read_text(encoding="utf-8", errors="replace")


def parse_vendor_tables(gate, text):
    """Zwraca {nazwa: [(numer_linii, adres, wartosc, pmd, warstwa, plyta)]}."""
    out, name = {}, None
    for no, line in enumerate(text.splitlines(), 1):
        hit = TABLE_START.match(line)
        if hit:
            name = hit.group(1)
            out[name] = []
            continue
        if name is None:
            continue
        if line.startswith("};"):
            name = None
            continue
        hit = VENDOR_ENTRY.match(line)
        if VENDOR_ENTRY_SHAPE.match(line) and not hit:
            fail(gate, "wzorzec nie rozebral wiersza tablicy %s w linii %d, wiec "
                       "kontrola kompletnosci nie zazadalaby go:\n  %s"
                       % (name, no, line.strip()))
        if hit:
            val = hit.group(2)
            out[name].append((
                no,
                int(hit.group(1), 16),
                int(val, 16) if val.lower().startswith("0x") else int(val),
                hit.group(3).replace(" ", ""),
                hit.group(4),
                hit.group(5).replace(" ", ""),
            ))
    return out


def applies_to_board(board):
    """BRD_ZEBU to emulator, nie nasza plyta. brd-for-cal = [01] to BRD_ALL."""
    return board != "BRD_ZEBU"


def read_driver_from_patch(gate, patch_glob, driver_path):
    """Wyciaga tresc sterownika z patcha, bo to patch jest tym, co sie wysyla."""
    hits = sorted((ROOT / "patches-uboot").glob(patch_glob))
    if not hits:
        skip(gate, "brak patcha %s w patches-uboot/" % patch_glob)

    lines, inside = [], False
    for raw in hits[0].read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("diff --git "):
            inside = raw.endswith(" b/" + driver_path)
            continue
        if not inside:
            continue
        if raw.startswith("+++") or raw.startswith("---") or raw.startswith("@@"):
            continue
        if raw.startswith("+"):
            lines.append(raw[1:])
    if not lines:
        fail(gate, "patch nie wnosi pliku %s" % driver_path)
    return lines


def const_from_driver(gate, lines, name):
    rx = re.compile(r"^#define\s+%s\s+(.+?)\s*$" % re.escape(name))
    for line in lines:
        hit = rx.match(line)
        if hit:
            return hit.group(1).strip()
    fail(gate, "w sterowniku nie ma stalej %s" % name)
