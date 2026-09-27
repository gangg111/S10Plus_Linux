#!/usr/bin/env python3
"""Drzewo urzadzen bootloadera wobec drzewa jadra i wobec sterownikow.

Seria bootloadera wnosi do `dts/upstream` KOPIE plikow, ktore seria jadra wnosi
do `arch/arm64/boot/dts/exynos`. Taka kopia jest z natury podatna na cichy
rozjazd: poprawka w jednym drzewie nie zapala niczego w drugim, a przy
nastepnej synchronizacji `dts/upstream` roznica ginie bez sladu.

Bramka sprawdza trzy rzeczy, kazda innego rodzaju:

  1. **Kopia jest kopia.** Trzy pliki z patcha DTS musza byc BAJT W BAJT tym,
     co seria jadra ma w gafazi `series`. Rownowaznosc "wyglada podobnie" nie
     wystarcza, bo to wlasnie z tych plikow powstaje DTB przypiete suma
     kontrolna po stronie jadra.

  2. **Aliasy zgadzaja sie z tablicami sterownika.** W U-Boocie kontroler pinow
     dostaje swoja tablice bankow przez `dev_seq()`, a dla wezla z aliasem jest
     to numer aliasu. Jesli kolejnosc aliasow w drzewie i kolejnosc tablic
     w sterowniku sie rozjada, KAZDY kontroler dostanie cudza tablice i nie
     powie o tym ani slowa: kompilacja przejdzie, drzewo sie zwaliduje,
     a piny beda ustawiane w zlych blokach. Ten rozjazd realnie tu byl.

  3. **Adresy UFS zgadzaja sie z drzewem producenta.** Wezly, ktorych jadro
     jeszcze nie ma, zyja w pliku nakladkowym bootloadera i nie chroni ich
     zadna z bramek serii jadra.

Kody wyjscia: 0 zgodne, 1 rozjazd, 2 bramka NIE URUCHOMIONA (brak zrodel).
"""

import re
import os
import pathlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ufs_cal

GATE = "check-uboot-dts"
LINUX = ufs_cal.ROOT / "sources" / "linux"
BRANCH = "series"

DTS_PATCH = "0007-dts-exynos-add-the-Exynos9820-and-Galaxy-S10-device-.patch"

# Drzewo bootloadera zyje pod WSL, tak samo jak dla check-uboot-clk-order.
UBOOT = pathlib.Path(os.environ.get(
    "UBOOT_TREE", "//wsl.localhost/Debian/home/pm/u-boot-upstream"))
CFG_PATCH = "0008-board-samsung-exynos-mobile-add-the-Samsung-Galaxy-S.patch"
PIN_PATCH = "0001-pinctrl-exynos-add-the-Exynos9820-pin-controller-dri.patch"

# plik w dts/upstream  ->  ten sam plik w drzewie jadra
COPIES = {
    "dts/upstream/src/arm64/exynos/exynos9820.dtsi":
        "arch/arm64/boot/dts/exynos/exynos9820.dtsi",
    "dts/upstream/src/arm64/exynos/exynos9820-pinctrl.dtsi":
        "arch/arm64/boot/dts/exynos/exynos9820-pinctrl.dtsi",
    "dts/upstream/src/arm64/exynos/exynos9820-beyond2lte.dts":
        "arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dts",
}

UBOOT_DTSI = "arch/arm/dts/exynos9820-beyond2lte-u-boot.dtsi"
PINCTRL_DRV = "drivers/pinctrl/exynos/pinctrl-exynos9820.c"


def fail(msg):
    ufs_cal.fail(GATE, msg)


def git(*args):
    return subprocess.run(["git", "-C", str(LINUX), *args],
                          capture_output=True, text=True)


def kernel_file(path):
    r = git("show", "%s:%s" % (BRANCH, path))
    if r.returncode:
        fail("drzewo jadra nie ma %s w galezi %s" % (path, BRANCH))
    return r.stdout


def uboot_file(path):
    """Plik kopii wprost z drzewa bootloadera.

    Kiedys szedl z patcha 0007, bo tamten wnosil go w calosci. Dzis tresc
    dochodzi dwoma patchami (0007 wnosi plik, 0009 dosyla synchronizacje),
    a skladanie pliku z wielu patchy nie jest robota dla tej bramki. Rownosc
    patchy z tym drzewem dowodzi osobno check-uboot-seria.sh, wiec lancuch
    od generatora do wysylanej latki jest pelny i bez tego.
    """
    p = UBOOT / path
    if not p.is_file():
        fail("drzewo bootloadera nie ma %s" % path)
    return p.read_text(encoding="utf-8")


def check_copies():
    """Kopia w dts/upstream musi byc bajt w bajt plikiem z serii jadra."""
    for ub_path, lin_path in COPIES.items():
        ours = uboot_file(ub_path)
        theirs = kernel_file(lin_path)
        # Patch oddaje wiersze bez koncowki, wiec porownujemy po wierszach.
        a = ours.splitlines()
        b = theirs.splitlines()
        if a != b:
            first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y),
                         min(len(a), len(b)))
            fail("kopia %s rozjechala sie z %s w wierszu %d\n"
                 "  bootloader: %s\n  jadro:      %s"
                 % (ub_path, lin_path, first + 1,
                    a[first] if first < len(a) else "(koniec pliku)",
                    b[first] if first < len(b) else "(koniec pliku)"))
    return len(COPIES)


def check_pinctrl_order():
    """Numer aliasu wybiera tablice bankow, wiec obie kolejnosci musza byc te same."""
    dtsi = "\n".join(ufs_cal.read_driver_from_patch(
        GATE, DTS_PATCH, "dts/upstream/src/arm64/exynos/exynos9820.dtsi"))
    aliases = re.findall(r"pinctrl(\d+)\s*=\s*&pinctrl_(\w+)\s*;", dtsi)
    if not aliases:
        fail("drzewo nie ma aliasow pinctrl, a sterownik na nich polega")
    by_seq = [name for _n, name in sorted(aliases, key=lambda t: int(t[0]))]

    drv = "\n".join(ufs_cal.read_driver_from_patch(GATE, PIN_PATCH, PINCTRL_DRV))
    start = drv.index("const struct samsung_pin_ctrl exynos9820_pin_ctrl[] = {")
    table = drv[start:drv.index("\n};", start)]
    in_drv = re.findall(r"\.pin_banks\s*=\s*exynos9820_pin_banks_(\w+),", table)

    if by_seq != in_drv:
        fail("kolejnosc tablic bankow nie odpowiada aliasom.\n"
             "  aliasy w drzewie:   %s\n"
             "  tablice w sterowniku: %s\n"
             "  Kontroler o numerze n dostaje n-ta tablice, wiec kazda roznica "
             "oznacza piny ustawiane w zlym bloku." % (by_seq, in_drv))
    return len(by_seq)


def check_ufs_addresses():
    """Wezly, ktorych jadro nie ma, sprawdzamy wobec drzewa producenta."""
    dtsi = "\n".join(ufs_cal.read_driver_from_patch(GATE, CFG_PATCH, UBOOT_DTSI))
    vendor = (ufs_cal.ROOT / "sources" / "ds" / "exynos9820.dts").read_text(
        encoding="utf-8", errors="replace")

    # Cztery okna wezla hosta, w kolejnosci, ktorej wymaga sterownik.
    hit = re.search(r"ufs@13d60000\s*\{.*?reg\s*=\s*(.*?);", dtsi, re.S)
    if not hit:
        fail("nakladka nie ma wezla ufs@13d60000 z wlasciwoscia reg")
    ours = [int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]+)", hit.group(1))]

    hit = re.search(r"ufs@0x13D60000\s*\{.*?reg\s*=\s*<(.*?)>;", vendor, re.S)
    if not hit:
        fail("drzewo producenta nie ma wezla ufs@0x13D60000")
    cells = [int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]+)", hit.group(1))]
    # Producent adresuje dwiema komorkami adresu i jedna rozmiaru, u nas jedna
    # i jedna, wiec z kazdej trojki bierzemy drugi i trzeci wyraz.
    theirs = [v for i, v in enumerate(cells) if i % 3 != 0]

    if ours != theirs:
        fail("okna wezla UFS rozjezdzaja sie z producentem:\n"
             "  nasze:     %s\n  producent: %s"
             % ([hex(v) for v in ours], [hex(v) for v in theirs]))

    # Offset izolacji PHY w bloku PMU, ten sam, ktorego pilnuje bramka PHY.
    hit = re.search(r"samsung,pmu-syscon\s*=\s*<&\w+\s+0x([0-9a-fA-F]+)>", dtsi)
    if not hit:
        fail("wezel PHY nie wskazuje offsetu izolacji w bloku PMU")
    host = ufs_cal.VENDOR_HOST.read_text(encoding="utf-8", errors="replace")
    want = re.search(r"#define\s+EXYNOS_PMU_UFS_PHY_OFFSET\s+0x([0-9a-fA-F]+)", host)
    if int(hit.group(1), 16) != int(want.group(1), 16):
        fail("offset izolacji w drzewie to 0x%s, a producent ma 0x%s"
             % (hit.group(1), want.group(1)))

    # Okno PHY musi pokryc drugi pas; polowa, ktora daje producent, nie pokrywa.
    hit = re.search(r"phy@13d64000\s*\{.*?reg\s*=\s*<0x13d64000\s+0x([0-9a-fA-F]+)>",
                    dtsi, re.S)
    if not hit:
        fail("nakladka nie ma wezla phy@13d64000 z wlasciwoscia reg")
    span = int(hit.group(1), 16)
    if span < 0xc00:
        fail("okno PMA ma 0x%x, a tablice kalibracyjne siegaja 0xbbc" % span)

    return len(ours) // 2


def main():
    if not ufs_cal.sources_present():
        ufs_cal.skip(GATE, "brak zrodel producenta w sources/ds")
    if not (LINUX / ".git").exists():
        ufs_cal.skip(GATE, "brak repozytorium jadra w sources/linux")
    if git("rev-parse", "--verify", BRANCH).returncode:
        ufs_cal.skip(GATE, "drzewo jadra nie ma galezi %s" % BRANCH)

    copies = check_copies()
    pinctrls = check_pinctrl_order()
    windows = check_ufs_addresses()

    print("%s: kopii bajt w bajt z seria jadra %d, kontrolerow pinow zgodnych "
          "z aliasami %d, okien UFS wobec producenta %d"
          % (GATE, copies, pinctrls, windows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
