#!/usr/bin/env python3
"""Generuje exynos9820-pinctrl.dtsi z tablic i drzewa producenta.

Ten plik jest w calosci opisem sprzetu i nie ma w nim ani jednej decyzji
projektowej: 64 banki pinow z nazwami i kolejnoscia z tablic sterownika
producenta (`ds/pinctrl-exynos-arm64.c`) oraz numery przerwan wybudzajacych
z jego drzewa urzadzen (`ds/exynos9820.dts`).  Skoro tak, to niech BEDZIE
wygenerowany, zamiast przepisywany recznie z cudzego portu.

Trzy grupy pinow, ktore ten plik jeszcze niesie, sa wypisane nizej z osobna,
bo kazda ma swoje zrodlo u producenta i swoj powod istnienia:

  hsi2c2_bus     ds/exynos9820.dts:703-708   (u producenta "hsi2c44-bus")
  hsi2c10_bus    ds/exynos9820.dts:1344-1349 (u producenta "hsi2c10-bus")
  decon_te_pins  ds/exynos9820.dts:2037-2041 (u producenta "decon_f_te_on")

Sila napedu pinow: producent zapisuje wszedzie `<0x0>`.  Uzywamy nazwanej
stalej `EXYNOS5420_PIN_DRV_LV1`, ktora tez rowna sie zero i ktora sasiednie
SoC w drzewie (exynos850, exynos990) stosuja w 147 miejscach.  Wczesniejsza
wersja pliku mieszala `EXYNOS5433_PIN_DRV_FAST_SR1` i `EXYNOS7_PIN_DRV_LV1`,
czyli stale z rodzin o innej szerokosci pola DRV.

Uzycie:
  scripts/gen-pinctrl-dts-exynos9820.py            # statystyka
  scripts/gen-pinctrl-dts-exynos9820.py --wypisz   # na standardowe wyjscie
  scripts/gen-pinctrl-dts-exynos9820.py --zapisz   # wpisz do drzewa
  scripts/gen-pinctrl-dts-exynos9820.py --zapisz --grupy hsi2c10_bus
"""
import io
import os
import re
import sys

NL = chr(10)
T = chr(9)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLICE = os.path.join(ROOT, "sources", "ds", "pinctrl-exynos-arm64.c")
DRZEWO = os.path.join(ROOT, "sources", "ds", "exynos9820.dts")
CEL = os.path.join(ROOT, "sources", "linux", "arch", "arm64", "boot", "dts",
                   "exynos", "exynos9820-pinctrl.dtsi")

# (etykieta w naszym drzewie, adres bloku u producenta)
# Kolejnosc jak aliasy pinctrl0..pinctrl7, czyli jak tablica ctrl[] sterownika.
KONTROLERY = [
    ("pinctrl_alive", "15850000"),
    ("pinctrl_aud", "18C60000"),
    ("pinctrl_cmgp", "15C30000"),
    ("pinctrl_fsys0", "13030000"),
    ("pinctrl_fsys1", "13C40000"),
    ("pinctrl_peric0", "10430000"),
    ("pinctrl_peric1", "10830000"),
    ("pinctrl_vts", "15580000"),
]

# Grupy pinow, ktore opisuje ten plik.  Kazda z odsylaczem do wezla producenta,
# z ktorego pochodzi, i przypisana do kontrolera, w ktorym leza jej piny.
GRUPY = {
    "pinctrl_alive": [
        ("bt_hostwake_pins", "bt-hostwake-pins",
         "/* the line the Bluetooth controller pokes to wake the host */",
         ['"gpa2-3"', "<EXYNOS_PIN_FUNC_INPUT>", "<EXYNOS_PIN_PULL_DOWN>"]),
        ("uart1_bus", "uart1-bus-pins",
         "/* to the Bluetooth controller */",
         ['"gpq0-3", "gpq0-2", "gpq0-1", "gpq0-0"', "<EXYNOS_PIN_FUNC_2>",
          "<EXYNOS_PIN_PULL_UP>", "<EXYNOS5420_PIN_DRV_LV1>"]),
    ],
    "pinctrl_aud": [
        ("aud_i2s0_bus", "aud-i2s0-bus-pins",
         "/* UAIF0 of ABOX, to the audio codec */",
         ['"gpb0-1", "gpb0-2", "gpb0-3", "gpb0-4"', "<EXYNOS_PIN_FUNC_2>",
          "<EXYNOS_PIN_PULL_DOWN>"]),
        ("aud_i2s1_bus", "aud-i2s1-bus-pins",
         "/* UAIF1 of ABOX, to the two speaker amplifiers */",
         ['"gpb1-0", "gpb1-1", "gpb1-2", "gpb1-3"', "<EXYNOS_PIN_FUNC_2>",
          "<EXYNOS_PIN_PULL_DOWN>"]),
    ],
    "pinctrl_cmgp": [
        ("bt_en_pins", "bt-en-pins",
         "/* the line the Bluetooth controller powers up from */",
         ['"gpm8-0"', "<EXYNOS_PIN_FUNC_OUTPUT>", "<EXYNOS_PIN_PULL_NONE>",
          None, "<EXYNOS_PIN_PDN_PREV>", "<EXYNOS_PIN_PULL_NONE>"]),
        ("hsi2c2_bus", "hsi2c2-bus-pins",
         "/* to the S2DOS05 display PMIC */",
         ['"gpm10-0", "gpm11-0"', "<EXYNOS_PIN_FUNC_3>",
          "<EXYNOS_PIN_PULL_NONE>",
          "<EXYNOS5420_PIN_DRV_LV1>"]),
        ("hsi2c45_bus", "hsi2c45-bus-pins",
         "/*" + NL
         + " * To the MAX77705, which carries the charger and the fuel gauge."
         + NL
         + " * This one is a USI in I2C mode, not a dedicated I2C like the bus"
         + NL
         + " * above, which is why its pins take a different function." + NL
         + " */",
         ['"gpm12-0", "gpm13-0"', "<EXYNOS_PIN_FUNC_2>",
          "<EXYNOS_PIN_PULL_NONE>",
          "<EXYNOS5420_PIN_DRV_LV1>"]),
    ],
    "pinctrl_fsys1": [
        ("pcie0_clkreq_pins", "pcie0-clkreq-pins",
         "/* the clock request line of the PCIe endpoint */",
         ['"gpf2-0"', "<EXYNOS_PIN_FUNC_2>", "<EXYNOS_PIN_PULL_UP>",
          "<EXYNOS5420_PIN_DRV_LV4>", "<EXYNOS_PIN_PDN_PREV>",
          "<EXYNOS_PIN_PULL_UP>"]),
        ("pcie0_perst_pins", "pcie0-perst-pins",
         "/* the reset line of the PCIe endpoint */",
         ['"gpf2-2"', "<EXYNOS_PIN_FUNC_OUTPUT>", None,
          "<EXYNOS5420_PIN_DRV_LV4>", "<EXYNOS_PIN_PDN_PREV>"]),
        ("ufs_refclk_out", "ufs-refclk-out-pins",
         "/*" + NL
         + " * The two pins of the embedded storage: the reset line of the"
         + " device" + NL
         + " * and the reference clock going out to it.  Both take their"
         + " second" + NL
         + " * function and keep their level while the domain is down." + NL
         + " */",
         ['"gpf3-0"', "<EXYNOS_PIN_FUNC_2>", "<EXYNOS_PIN_PULL_NONE>",
          None, "<EXYNOS_PIN_PDN_PREV>"]),
        ("ufs_rst_n", "ufs-rst-n-pins", None,
         ['"gpf3-1"', "<EXYNOS_PIN_FUNC_2>", "<EXYNOS_PIN_PULL_NONE>",
          None, "<EXYNOS_PIN_PDN_PREV>"]),
    ],
    "pinctrl_peric0": [
        ("bt_btwake_pins", "bt-btwake-pins",
         "/* the line the host pokes to wake the Bluetooth controller */",
         ['"gpg2-0"', "<EXYNOS_PIN_FUNC_OUTPUT>", "<EXYNOS_PIN_PULL_NONE>",
          None, "<EXYNOS_PIN_PDN_PREV>", "<EXYNOS_PIN_PULL_NONE>"]),
        ("hsi2c10_bus", "hsi2c10-bus-pins",
         "/* to the touchscreen */",
         ['"gpp1-4", "gpp1-5"', "<EXYNOS_PIN_FUNC_2>",
          "<EXYNOS_PIN_PULL_NONE>", "<EXYNOS5420_PIN_DRV_LV1>"]),
        # USI01 w trybie SPI, do kodeka CS47L93 (spi2_bus producenta); CS idzie
        # jako GPIO z plyty, bo sprzetowy CS puszcza linie po kazdym transferze
        ("spi2_bus", "spi2-bus-pins", None,
         ['"gpp0-6", "gpp0-5", "gpp0-4"', "<EXYNOS_PIN_FUNC_2>",
          "<EXYNOS_PIN_PULL_NONE>", "<EXYNOS5420_PIN_DRV_LV1>"]),
    ],
    "pinctrl_peric1": [
        # USI16 w trybie SPI, do huba czujnikow BCM47752 (spi17_bus producenta);
        # CS jako GPIO z plyty, jak przy kodeku
        ("spi17_bus", "spi17-bus-pins", None,
         ['"gph0-2", "gph0-1", "gph0-0"', "<EXYNOS_PIN_FUNC_2>",
          "<EXYNOS_PIN_PULL_NONE>", "<EXYNOS5420_PIN_DRV_LV1>"]),
        # USI17 w trybie I2C, do obu wzmacniaczy CS35L40 (hsi2c38 producenta)
        ("hsi2c38_bus", "hsi2c38-bus-pins", None,
         ['"gph0-6", "gph0-7"', "<EXYNOS_PIN_FUNC_3>",
          "<EXYNOS_PIN_PULL_NONE>", "<EXYNOS5420_PIN_DRV_LV1>"]),
        ("decon_te_pins", "decon-te-pins",
         "/* tearing effect from the panel, the display trigger source */",
         ['"gpd0-0"', "<EXYNOS_PIN_FUNC_F>", None, None]),
    ],
}

POLA = ["samsung,pins", "samsung,pin-function", "samsung,pin-pud",
        "samsung,pin-drv", "samsung,pin-con-pdn",
        "samsung,pin-pud-pdn"]

NAGLOWEK = """// SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause
/*
 * Samsung Exynos9820 SoC pin-mux and pin-config device tree source
 *
 * Copyright (C) 2026 Artur Szafraniec <ganggg111@gmail.com>
 *
 * The bank names and their order are the ones the pin controller driver
 * expects, and the wakeup interrupt numbers are the ones the SoC wires to the
 * GIC; both are transcribed from the vendor sources rather than from another
 * port.  Only the banks that can wake the system carry an interrupt list: the
 * rest reach the CPU through their own controller.
 *
 * The three pin groups at the end are the ones this SoC needs before anything
 * can talk: the two I2C buses and the panel tearing effect line.
 */

#include <dt-bindings/interrupt-controller/arm-gic.h>
#include "exynos-pinctrl.h"
"""


def banki_z_tablic():
    """Nazwy bankow w kolejnosci, osobno dla kazdego kontrolera."""
    if not os.path.exists(TABLICE):
        sys.exit("brak %s, uruchom scripts/fetch-sources.sh" % TABLICE)
    tekst = io.open(TABLICE, encoding="utf-8", errors="replace").read()
    out = []
    for i in range(len(KONTROLERY)):
        m = re.search(r"exynos9820_pin_banks%d\[\]\s*=\s*\{(.*?)\n\};" % i,
                      tekst, re.S)
        if not m:
            sys.exit("nie znalazlem tablicy exynos9820_pin_banks%d" % i)
        out.append(re.findall(r'"([a-z0-9]+)"', m.group(1)))
    return out


def przerwania_z_drzewa():
    """Nazwa banku -> lista numerow SPI, z drzewa urzadzen producenta."""
    if not os.path.exists(DRZEWO):
        sys.exit("brak %s, uruchom scripts/fetch-sources.sh" % DRZEWO)
    tekst = io.open(DRZEWO, encoding="utf-8", errors="replace").read()
    out = {}
    # wezly bankow leza dwa tabulatory gleboko, jako dzieci wezla pinctrl@
    for m in re.finditer(r"\n\t\t([a-z0-9]+) \{\n(.*?)\n\t\t\};", tekst, re.S):
        nazwa, cialo = m.group(1), m.group(2)
        if not nazwa.startswith("gp") and not nazwa.startswith("etc"):
            continue
        w = re.search(r"interrupts = <([^>]*)>", cialo)
        if not w:
            continue
        liczby = [int(x, 0) for x in w.group(1).split()]
        # trojki (typ, numer, flagi); bierzemy numery przy typie 0 (SPI)
        out[nazwa] = [liczby[i + 1] for i in range(0, len(liczby), 3)
                      if liczby[i] == 0]
    return out


# Banki typu EINTN nie maja wlasnej domeny przerwan, wiec nie sa kontrolerami
# przerwan.  Ten sam podzial ma exynos2200-pinctrl.dtsi, gdzie jedyne banki bez
# tych dwoch wlasciwosci to gpq0, gpq1 i gpq2, czyli komplet EINTN tamtego SoC.
BEZ_PRZERWAN = ("gpq0", "etc0")


def emituj_bank(nazwa, spi):
    linie = [T + "%s: %s-gpio-bank {" % (nazwa, nazwa),
             T * 2 + "gpio-controller;",
             T * 2 + "#gpio-cells = <2>;"]
    if nazwa not in BEZ_PRZERWAN:
        linie += ["",
                  T * 2 + "interrupt-controller;",
                  T * 2 + "#interrupt-cells = <2>;"]
    if spi:
        linie.append(T * 2 + "interrupt-parent = <&gic>;")
        # ciag dalszy pod pierwszym wpisem, tabulatorami tak daleko, jak
        # sie da: wiodace spacje sa dla checkpatch bledem wciecia
        kolumna = 16 + len("interrupts = ")
        wciecie = T * (kolumna // 8) + " " * (kolumna % 8)
        for i, n in enumerate(spi):
            czolo = T * 2 + "interrupts = " if i == 0 else wciecie
            koniec = ";" if i == len(spi) - 1 else ","
            linie.append(czolo + "<GIC_SPI %d IRQ_TYPE_LEVEL_HIGH>%s"
                         % (n, koniec))
    linie.append(T + "};")
    return linie


def emituj_grupe(etykieta, wezel, komentarz, wartosci):
    linie = []
    if komentarz:
        linie += [T + w if w else T.rstrip() for w in komentarz.split(NL)]
    linie.append(T + "%s: %s {" % (etykieta, wezel))
    for pole, w in zip(POLA, wartosci):
        if w is None:
            continue
        linie.append(T * 2 + "%s = %s;" % (pole, w))
    linie.append(T + "};")
    return linie


def wybrane_grupy():
    """Etykiety grup pinow do wypisania.

    Seria dodaje je w dwoch krokach: podstawowe drzewo niesie tylko magistrale
    panelu dotykowego, a hsi2c2 i sygnal TE dochodza razem z potokiem
    wyswietlacza.  Bez tego rozroznienia pozniejszy commit dopisalby te same
    wezly po raz drugi, a dtc scala wezly o tej samej nazwie po cichu, wiec
    duplikat nie dalby o sobie znac ani jednym ostrzezeniem.
    """
    if "--grupy" not in sys.argv:
        return None
    return set(sys.argv[sys.argv.index("--grupy") + 1].split(","))


def emituj():
    wybor = wybrane_grupy()
    banki = banki_z_tablic()
    spi = przerwania_z_drzewa()
    linie = [NAGLOWEK.rstrip(NL)]
    brakujace = []
    for (etykieta, _), nazwy in zip(KONTROLERY, banki):
        linie.append("")
        linie.append("&%s {" % etykieta)
        pierwszy = True
        for n in nazwy:
            if n not in spi and n.startswith("gpa"):
                brakujace.append(n)
            if not pierwszy:
                linie.append("")
            pierwszy = False
            linie += emituj_bank(n, spi.get(n))
        for grupa in GRUPY.get(etykieta, []):
            if wybor is not None and grupa[0] not in wybor:
                continue
            linie.append("")
            linie += emituj_grupe(*grupa)
        linie.append("};")
    if brakujace:
        sys.exit("banki wybudzajace bez przerwan w drzewie producenta: %s"
                 % ", ".join(brakujace))
    return NL.join(linie) + NL


def main():
    tresc = emituj()
    if "--wypisz" in sys.argv:
        sys.stdout.write(tresc)
        return
    if "--zapisz" in sys.argv:
        io.open(CEL, "w", encoding="utf-8", newline=NL).write(tresc)
        print("zapisano %s (%d linii)" % (CEL, tresc.count(NL)))
        return

    banki = banki_z_tablic()
    spi = przerwania_z_drzewa()
    print("kontrolerow: %d" % len(KONTROLERY))
    for (etykieta, adres), nazwy in zip(KONTROLERY, banki):
        zwyk = sum(1 for n in nazwy if n not in spi)
        print("  %-15s @%s  bankow %2d, z przerwaniami %2d"
              % (etykieta, adres, len(nazwy), len(nazwy) - zwyk))
    print("bankow razem: %d, linii wyniku: %d"
          % (sum(len(n) for n in banki), tresc.count(NL)))


if __name__ == "__main__":
    main()
