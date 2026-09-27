#!/usr/bin/env python3
"""Wezel UFS w drzewie urzadzen jadra wobec drzewa producenta.

Trzecia bramka rodziny. `check-ufs-phy-kernel.py` i `check-ufs-host-kernel.py`
pilnuja tego, co sterowniki PISZA do sprzetu; ta pilnuje tego, GDZIE pisza:
adresow okien rejestrow, numeru przerwania, pinow i sposobu, w jaki sterownik
dostaje zegary.

Po co osobna bramka, skoro dt-validate juz przechodzi. Bo schemat sprawdza
KSZTALT, a nie TRESC: wezel z adresem przepisanym o cyfre obok, z przerwaniem
sasiedniego bloku albo z innym pinem przechodzi walidacje bez slowa. Dwie
rzeczy z tej listy sa przy tym ciche podwojnie:

  * nazwy zegarow. Sterownik szuka ich TEKSTEM ("core_clk",
    "sclk_unipro_main") i bez nich konczy probe bledem, a schemat dopuszcza
    kilka wariantow, wiec nazwy z bootloadera ("hci", "unipro") przeszlyby
    walidacje i zabily sterownik;

  * dma-coherent. Producent ma te wlasciwosc, my swiadomie jej NIE MAMY, bo
    deskryptory tego sterownika sa nieskoherentne i bity wspoldzielenia maja
    zostac wyczyszczone. Dopisanie jej nie zepsuje ani kompilacji, ani
    walidacji, a przestawi sprzet w uklad, w ktorym to, co kontroler zapisze
    koherentnie, zostanie uniewaznione przez czyszczenie cache po naszej
    stronie.

Zrodlem jest drzewo robocze; bramka [1] `scripts/verify.sh` osobno pilnuje, ze
jest ono dokladnie tym, co daje seria.

Kody wyjscia: 0 zgodne, 1 rozjazd, 2 bramka NIE URUCHOMIONA (brak zrodel).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ufs_cal

GATE = "check-ufs-dts"
ROOT = Path(__file__).resolve().parent.parent
LINUX = ROOT / "sources/linux"
DTS = LINUX / "arch/arm64/boot/dts/exynos"
SOC = DTS / "exynos9820.dtsi"
PINCTRL = DTS / "exynos9820-pinctrl.dtsi"
BOARD = DTS / "exynos9820-beyond2lte.dts"
HOST_DRIVER = LINUX / "drivers/ufs/host/ufs-exynos.c"
VENDOR_DTS = ROOT / "sources/ds/exynos9820.dts"

# Adres rejestru wspoldzielenia zmierzony na telefonie i uzywany przez
# dzialajacy bootloader. Wezel podaje go jako baze bloku rejestrow systemowych
# plus przesuniecie, wiec bramka sprawdza sume.
IOCC_ADDR = 0x13C10700

PIN_SYMBOLS = {
    "EXYNOS_PIN_FUNC_2": 2,
    "EXYNOS_PIN_PULL_NONE": 0,
    "EXYNOS_PIN_PDN_PREV": 3,
}

# Nazwy zegarow, ktorych sterownik szuka tekstem; patrz exynos_ufs_get_clk_info.
CLOCK_NAMES = ("core_clk", "sclk_unipro_main")


def fail(msg):
    ufs_cal.fail(GATE, msg)


def node(text, label, what):
    """Cialo wezla o podanej etykiecie; etykieta jest WZORCEM, nie tekstem."""
    hit = re.search(r"^\s*%s\s*\{" % label, text, re.M)
    if not hit:
        fail("nie znalazlem wezla %s w %s" % (label, what))
    depth, i = 0, hit.end() - 1
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i:j]
    fail("wezel %s w %s nie ma zamkniecia" % (label, what))


def prop(body, name, where):
    hit = re.search(r"^\s*%s\s*=\s*(.+?);" % re.escape(name), body, re.M | re.S)
    if not hit:
        fail("wezel %s nie ma wlasciwosci %s" % (where, name))
    return re.sub(r"\s+", " ", hit.group(1)).strip()


def numbers(text):
    return [int(x, 0) for x in re.findall(r"0x[0-9a-fA-F]+|\b\d+\b", text)]


def strings(text):
    return re.findall(r'"([^"]*)"', text)


def vendor_pin(text, name):
    body = node(text, re.escape(name), "drzewa producenta")
    return (strings(prop(body, "samsung,pins", name))[0],
            numbers(prop(body, "samsung,pin-function", name))[0],
            numbers(prop(body, "samsung,pin-pud", name))[0],
            numbers(prop(body, "samsung,pin-con-pdn", name))[0])


def our_pin(text, label):
    body = node(text, label + r":\s*[\w-]+", "naszego pinctrl")
    def sym(nazwa):
        raw = prop(body, nazwa, label).strip("<>").strip()
        if raw in PIN_SYMBOLS:
            return PIN_SYMBOLS[raw]
        fail("%s: %s ma wartosc %s, ktorej bramka nie zna, dopisz ja do "
             "PIN_SYMBOLS" % (label, nazwa, raw))
    return (strings(prop(body, "samsung,pins", label))[0],
            sym("samsung,pin-function"), sym("samsung,pin-pud"),
            sym("samsung,pin-con-pdn"))


def main():
    for path in (SOC, PINCTRL, BOARD, HOST_DRIVER):
        if not path.is_file():
            ufs_cal.skip(GATE, "brak %s" % path.name)
    if not VENDOR_DTS.is_file():
        ufs_cal.skip(GATE, "brak drzewa producenta w sources/ds, "
                           "uruchom scripts/fetch-sources.sh")

    soc = SOC.read_text(encoding="utf-8", errors="replace")
    pins = PINCTRL.read_text(encoding="utf-8", errors="replace")
    board = BOARD.read_text(encoding="utf-8", errors="replace")
    nasz_drv = HOST_DRIVER.read_text(encoding="utf-8",
                                     errors="replace")
    ven = VENDOR_DTS.read_text(encoding="utf-8", errors="replace")

    ufs = node(soc, r"ufs_0:\s*ufs@13d60000", "naszego drzewa")
    phy = node(soc, r"ufs_0_phy:\s*phy@13d64000", "naszego drzewa")
    ven_ufs = node(ven, r"ufs@0x13D60000", "drzewa producenta")

    sprawdzone = 0

    # --- okna rejestrow -----------------------------------------------------
    # Producent pisze adresy w dwoch komorkach, wiec kazde okno to trojka
    # (zero, adres, rozmiar); u nas komorka jest jedna.
    vr = numbers(prop(ven_ufs, "reg", "ufs producenta"))
    if len(vr) % 3 or any(vr[i] for i in range(0, len(vr), 3)):
        fail("nie umiem odczytac reg producenta: %s" % vr)
    ich = [(vr[i + 1], vr[i + 2]) for i in range(0, len(vr), 3)]
    nasze = list(zip(*[iter(numbers(prop(ufs, "reg", "ufs_0")))] * 2))
    if nasze != ich:
        fail("okna rejestrow sie rozjechaly\n  nasze:     %s\n  producent: %s"
             % (["0x%x+0x%x" % w for w in nasze],
                ["0x%x+0x%x" % w for w in ich]))
    sprawdzone += len(ich)

    names = strings(prop(ufs, "reg-names", "ufs_0"))
    if names != ["hci", "vs_hci", "unipro", "ufsp"]:
        fail("reg-names to %s, a binding wymaga hci, vs_hci, unipro, ufsp"
             % names)
    sprawdzone += 1

    # --- przerwanie ---------------------------------------------------------
    # Typ przerwania jest osobna sprawa, opisana adnotacja UNVERIFIED w dtsi;
    # tutaj porownuje sie sam numer.
    # Producent pisze trojke liczb, my <GIC_SPI N IRQ_TYPE_...>, wiec po ich
    # stronie numer stoi w srodku, a po naszej jest jedyna liczba.
    ich_irq = numbers(prop(ven_ufs, "interrupts", "ufs producenta"))[1]
    nasze_irq = numbers(prop(ufs, "interrupts", "ufs_0"))
    if len(nasze_irq) != 1:
        fail("interrupts ma %d liczb, oczekiwano jednej obok nazw "
             "symbolicznych: %s" % (len(nasze_irq), nasze_irq))
    nasz_irq = nasze_irq[0]
    if nasz_irq != ich_irq:
        fail("przerwanie %d, a producent ma %d" % (nasz_irq, ich_irq))
    sprawdzone += 1

    # --- zegary -------------------------------------------------------------
    nasze_zegary = strings(prop(ufs, "clock-names", "ufs_0"))
    if tuple(nasze_zegary) != CLOCK_NAMES:
        fail("clock-names to %s, a sterownik szuka tekstem %s i bez nich konczy "
             "probe bledem" % (nasze_zegary, list(CLOCK_NAMES)))
    ile_ich = len(strings(prop(ven_ufs, "clock-names", "ufs producenta")))
    if len(nasze_zegary) != ile_ich:
        fail("mamy %d zegarow, producent %d" % (len(nasze_zegary), ile_ich))
    sprawdzone += 2

    # --- wspoldzielenie i koherencja ---------------------------------------
    sysreg = prop(ufs, "samsung,sysreg", "ufs_0")
    offset = numbers(sysreg)[-1]
    baza = numbers(prop(node(soc, r"sysreg_fsys1:\s*syscon@13c10000",
                             "naszego drzewa"), "reg", "sysreg_fsys1"))[0]
    if baza + offset != IOCC_ADDR:
        fail("bity wspoldzielenia wypadaja pod 0x%x, a zmierzony adres to 0x%x"
             % (baza + offset, IOCC_ADDR))
    sprawdzone += 1

    if re.search(r"^\s*dma-coherent\s*;", ufs, re.M):
        fail("wezel ma dma-coherent, a ten sterownik trzyma deskryptory "
             "nieskoherentnie i bity wspoldzielenia maja byc wyczyszczone")
    sprawdzone += 1

    # --- piny ---------------------------------------------------------------
    for nasza, ich_nazwa in (("ufs_rst_n", "ufs-rst-n"),
                             ("ufs_refclk_out", "ufs-refclk-out")):
        if nasza not in prop(ufs, "pinctrl-0", "ufs_0"):
            fail("pinctrl-0 nie wskazuje na %s" % nasza)
        a, b = our_pin(pins, nasza), vendor_pin(ven, ich_nazwa)
        if a != b:
            fail("pin %s: nasz %s, producent %s" % (nasza, a, b))
        sprawdzone += 1

    # --- PHY ----------------------------------------------------------------
    if strings(prop(phy, "reg-names", "ufs_0_phy")) != ["phy-pma"]:
        fail("reg-names PHY musi byc phy-pma")
    pmu = numbers(prop(phy, "samsung,pmu-syscon", "ufs_0_phy"))[-1]
    host = ufs_cal.VENDOR_HOST.read_text(encoding="utf-8", errors="replace")
    hit = re.search(r"#define\s+EXYNOS_PMU_UFS_PHY_OFFSET\s+(0x[0-9a-fA-F]+)",
                    host)
    if not hit:
        fail("nie znalazlem EXYNOS_PMU_UFS_PHY_OFFSET w ufs-exynos.h")
    if pmu != int(hit.group(1), 16):
        fail("izolacja PHY pod 0x%x, a producent ma 0x%x"
             % (pmu, int(hit.group(1), 16)))
    sprawdzone += 2

    # Okno PMA musi siegac wyzszego pasa, inaczej polowa kalibracji trafia
    # poza odwzorowanie i sterownik pisze w prozne.
    drv = ufs_cal.read_driver_from_patch(
        GATE, "*-phy-samsung-ufs-Add-Exynos9820-support.patch",
        "drivers/phy/samsung/phy-exynos9820-ufs.c", series="patches")
    rejestry = [int(m, 16) for line in drv
                for m in re.findall(r"PHY_(?:COMN_REG_CFG|TRSV_REG_CFG_9820)"
                                    r"\((0x[0-9a-fA-F]+)", line)]
    stride = int(ufs_cal.const_from_driver(GATE, drv, "EXYNOS9820_LANE_OFFSET")
                 .strip("()").split("/")[0].strip(), 16)
    potrzeba = max(rejestry) * 4 + stride + 4
    okno = numbers(prop(phy, "reg", "ufs_0_phy"))[1]
    if okno < potrzeba:
        fail("okno PMA ma 0x%x, a tablice siegaja 0x%x" % (okno, potrzeba))
    sprawdzone += 1

    # Okno protektora musi siegac wszystkiego, co exynos_ufs_config_smu()
    # rusza, albo nasze dane sterownika musza kazac te funkcje POMINAC.
    # Zmierzone na telefonie: rejestr bezpieczenstwa na dole bloku czyta sie
    # i pisze bez slowa skargi, a pierwszy zapis do deskryptora regionu wraca
    # asynchronicznym SError, bo deskryptory naleza do firmware. Okno, ktore
    # deklaruje producent, to dokladnie ta czesc, ktora jest nasza, wiec sama
    # jego szerokosc wystarczy, by rozstrzygnac, czy funkcja ma prawo pisac.
    # Bez tej bramki rozjazd konczy sie panika jadra w tej funkcji, a nie
    # bledem kompilacji ani walidacji.
    smu = re.search(r"static void exynos_ufs_config_smu\(.*?\n\}", nasz_drv,
                    re.S)
    if not smu:
        fail("nie znalazlem exynos_ufs_config_smu w ufs-exynos.c")
    ruszane = sorted(set(re.findall(r"ufsp_(?:readl|writel)\([^)]*,\s*(\w+)\)",
                                    smu.group(0))))
    if not ruszane:
        fail("exynos_ufs_config_smu nie rusza zadnego rejestru, bramka "
             "przestala rozumiec te funkcje")
    linie = nasz_drv.splitlines()
    zasieg = 0
    for nazwa in ruszane:
        surowa = ufs_cal.const_from_driver(GATE, linie, nazwa)
        if not re.match(r"0x[0-9a-fA-F]+$", surowa):
            fail("%s ma wartosc %s, ktorej bramka nie czyta jako przesuniecia"
                 % (nazwa, surowa))
        zasieg = max(zasieg, int(surowa, 16) + 4)
    okno_ufsp = nasze[names.index("ufsp")][1]
    dane = re.search(r"exynos9820_ufs_drvs\s*=\s*\{(.*?)\n\};", nasz_drv, re.S)
    if not dane:
        fail("nie znalazlem exynos9820_ufs_drvs w ufs-exynos.c")
    pomija = "EXYNOS_UFS_OPT_UFSPR_SECURE" in dane.group(1)
    if zasieg > okno_ufsp and not pomija:
        fail("exynos_ufs_config_smu siega 0x%x (%s), a okno ufsp ma 0x%x; "
             "bez EXYNOS_UFS_OPT_UFSPR_SECURE pierwszy zapis do deskryptora "
             "regionu wraca SErrorem i jadro panikuje w tej funkcji"
             % (zasieg, ", ".join(ruszane), okno_ufsp))
    sprawdzone += 1
    # --- stan wezla ---------------------------------------------------------
    if not re.search(r'status\s*=\s*"disabled"', ufs):
        fail("wezel SoC musi byc wylaczony, wlacza go plyta")
    if not re.search(r"&ufs_0\s*\{[^}]*status\s*=\s*\"okay\"", board, re.S):
        fail("plyta nie wlacza wezla ufs_0")
    sprawdzone += 2

    print("%s: sprawdzonych zgodnosci z producentem %d, okien rejestrow %d, "
          "pinow 2, okno PMA 0x%x wobec wymaganych 0x%x, "
          "okno protektora 0x%x wobec zasiegu 0x%x"
          % (GATE, sprawdzone, len(ich), okno, potrzeba,
             okno_ufsp, zasieg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
