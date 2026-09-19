#!/usr/bin/env python3
"""Wypisuje exynos9820-beyond2lte.dts w wersji na dany etap serii.

Plik plyty rosnie w dwoch krokach: podstawowe wsparcie plyty, a potem potok
wyswietlacza, ktory wlacza DECON, DSI z panelem i magistrale PMIC-a panelu.
Zrodlem prawdy jest ten skrypt, zeby obie wersje nie mogly sie rozjechac.

Wartosci pochodza ze zrodel producenta wymienionych w SOURCES.md:
  klawisze i przerwanie dotyku   ds/exynos9820-beyond2lte_eur_open_26.dts:3934-3956
                                 (funkcja 0xf, pud 0, drv 0)
  szyny panelu i ich napiecia    tamze :6528-6558 (wyjscia S2DOS05)
                                 i :6650-6674 (przypisanie rol)

Sila napedu pinow: producent zapisuje `<0x0>`.  Uzywamy nazwanej stalej
EXYNOS5420_PIN_DRV_LV1, ktora tez rowna sie zero, tej samej co w pliku
pinctrl SoC; wczesniejsza wersja mieszala tu dwie stale z rodzin o innej
szerokosci pola DRV.

Uzycie:
  scripts/gen-dts-beyond2lte.py --etap 1..2 [--zapisz]
"""
import io
import os
import sys

NL = chr(10)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CEL = os.path.join(ROOT, "sources", "linux", "arch", "arm64", "boot", "dts",
                   "exynos", "exynos9820-beyond2lte.dts")

ETAPY = {
    1: "arm64: dts: exynos: Add minimal Exynos9820 SoC and Galaxy S10+ support",
    2: "arm64: dts: exynos: exynos9820: Add the display pipeline",
}

NAGLOWEK = '''// SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause
/*
 * Samsung Galaxy S10+ (SM-G975F, beyond2lte) device tree source
 *
 * Copyright (C) 2026 Artur Szafraniec <ganggg111@gmail.com>
 *
 * What the board adds on top of the SoC: the crystal rate, the four keys, the
 * touchscreen and its two rails, and the display, which is a S6E3HA9 panel fed
 * over MIPI DSI and powered by a S2DOS05 PMIC on the always-on I2C bus.
 */

/dts-v1/;
#include "exynos9820.dtsi"
#include <dt-bindings/gpio/gpio.h>
#include <dt-bindings/input/input.h>
#include <dt-bindings/soc/samsung,exynos-usi.h>

/ {
\tmodel = "Samsung Galaxy S10+ (SM-G975F)";
\tcompatible = "samsung,beyond2lte", "samsung,exynos9820";
\tchassis-type = "handset";

\t/*
\t * 8 GiB of DRAM in six banks, read from the device tree the boot
\t * loader hands the vendor kernel on this phone (/sys/firmware/fdt).
\t * The two gaps below 4 GiB, 0xbab00000..0xbfffffff and
\t * 0xe0000000..0xe18fffff, are memory the secure firmware keeps, so
\t * they are absent here on purpose; merging the banks across them
\t * would hand the kernel pages it must not touch.
\t */
\tmemory@80000000 {
\t\tdevice_type = "memory";
\t\treg = <0x0 0x80000000 0x3ab00000>;
\t};

\tmemory@c0000000 {
\t\tdevice_type = "memory";
\t\treg = <0x0 0xc0000000 0x20000000>;
\t};

\tmemory@e1900000 {
\t\tdevice_type = "memory";
\t\treg = <0x0 0xe1900000 0x1e700000>;
\t};

\tmemory@880000000 {
\t\tdevice_type = "memory";
\t\treg = <0x8 0x80000000 0x80000000>;
\t};

\tmemory@900000000 {
\t\tdevice_type = "memory";
\t\treg = <0x9 0x00000000 0x80000000>;
\t};

\tmemory@980000000 {
\t\tdevice_type = "memory";
\t\treg = <0x9 0x80000000 0x80000000>;
\t};

\tchosen {
\t\t#address-cells = <2>;
\t\t#size-cells = <1>;
\t\tranges;
\t\tstdout-path = &serial0;

\t\t/*
\t\t * The framebuffer S-Boot leaves behind, so there is a picture
\t\t * before the display driver takes over.  The address is the one
\t\t * the boot loader itself passes on this phone: the vendor kernel
\t\t * receives "s3cfb.bootloaderfb=0xca000000" on its command line.
\t\t */
\t\tframebuffer0: framebuffer@ca000000 {
\t\t\tcompatible = "simple-framebuffer";
\t\t\treg = <0x0 0xca000000 (1440 * 3040 * 4)>;
\t\t\twidth = <1440>;
\t\t\theight = <3040>;
\t\t\tstride = <(1440 * 4)>;
\t\t\tformat = "a8r8g8b8";
\t\t};
\t};

\t/*
\t * Four keys, all wired to always-on banks so they can wake the phone.
\t * Two of them are wakeup sources, the two the vendor marks that way:
\t * the wink key and the power key.
\t */
\tgpio-keys {
\t\tcompatible = "gpio-keys";

\t\tpinctrl-0 = <&key_volup &key_voldown &key_wink &key_power>;
\t\tpinctrl-names = "default";

\t\tkey-volup {
\t\t\tlabel = "Volume Up Key";
\t\t\tlinux,code = <KEY_VOLUMEUP>;
\t\t\tgpios = <&gpa0 3 GPIO_ACTIVE_LOW>;
\t\t};

\t\tkey-voldown {
\t\t\tlabel = "Volume Down Key";
\t\t\tlinux,code = <KEY_VOLUMEDOWN>;
\t\t\tgpios = <&gpa0 4 GPIO_ACTIVE_LOW>;
\t\t};

\t\tkey-wink {
\t\t\tlabel = "Wink Key";
\t\t\tlinux,code = <KEY_COFFEE>;
\t\t\tgpios = <&gpa0 6 GPIO_ACTIVE_LOW>;
\t\t\twakeup-source;
\t\t};

\t\tkey-power {
\t\t\tlabel = "Power Key";
\t\t\tlinux,code = <KEY_POWER>;
\t\t\tgpios = <&gpa2 4 GPIO_ACTIVE_LOW>;
\t\t\twakeup-source;
\t\t};
\t};

\t/*
\t * The touchscreen rails really come from two LDOs of the main PMIC
\t * (LDO19M and LDO27M of the S2MPS19), which mainline cannot reach yet:
\t * that PMIC is behind the ACPM mailbox.  They are on when the bootloader
\t * hands over, so they are described as fixed supplies until the real
\t * regulators can be named.
\t */
\treg_tsp_io: regulator-tsp-io {
\t\tcompatible = "regulator-fixed";
\t\tregulator-name = "tsp_io";
\t\tregulator-min-microvolt = <1800000>;
\t\tregulator-max-microvolt = <1800000>;
\t\tregulator-always-on;
\t};

\treg_tsp_avdd: regulator-tsp-avdd {
\t\tcompatible = "regulator-fixed";
\t\tregulator-name = "tsp_avdd";
\t\tregulator-min-microvolt = <3000000>;
\t\tregulator-max-microvolt = <3000000>;
\t\tregulator-always-on;
\t};

\t/*
\t * Memory the kernel must not hand out.  Every region below is taken
\t * from a tree that describes this board, not from a calculation: the
\t * vendor kernel's own device tree, or the independent port that boots
\t * the same phone.  Leaving one out is not a missing feature, it is a
\t * kernel that eventually writes into the hypervisor, the modem or the
\t * secure firmware and dies without a line on the console.
\t *
\t * The three the vendor's SoC tree carries are sec_debug_magic,
\t * mm_debug and seclog_mem (ds/exynos9820.dts:2885-2892 and :2980-2983);
\t * the modem's three and the secure camera come from its board tree
\t * (ds/exynos9820-beyond2lte_eur_open_26.dts:4490-4503 and :6727-6734).
\t * The remaining three, the KASLR seed page and the two EL2 regions,
\t * exist only in the independent port (ub/exynos9820-common.dtsi:60-112),
\t * which is why they carry their own note.
\t */
\treserved-memory {
\t\t#address-cells = <2>;
\t\t#size-cells = <1>;
\t\tranges;

\t\tsec_debug_magic@80000000 {
\t\t\treg = <0x0 0x80000000 0x1000>;
\t\t\tno-map;
\t\t};

\t\t/*
\t\t * The seed page and the two EL2 regions are not in the vendor
\t\t * source tree, but they are in the device tree the boot loader
\t\t * hands the vendor kernel on this phone, at exactly these
\t\t * addresses and sizes, under the compatibles "kernel-kaslr"
\t\t * and "el2,uh".
\t\t */
\t\tkaslr_seed@80001000 {
\t\t\treg = <0x0 0x80001000 0x1000>;
\t\t\tno-map;
\t\t};

\t\tel2_code@87000000 {
\t\t\treg = <0x0 0x87000000 0x200000>;
\t\t\tno-map;
\t\t};

\t\tmm_debug@91200000 {
\t\t\treg = <0x0 0x91200000 0x1000>;
\t\t\tno-map;
\t\t};

\t\tsecure_camera@96000000 {
\t\t\treg = <0x0 0x96000000 0x2200000>;
\t\t\tno-map;
\t\t};

\t\tseclog_mem@c0000000 {
\t\t\treg = <0x0 0xc0000000 0x80000>;
\t\t\tno-map;
\t\t};

\t\tframebuffer@ca000000 {
\t\t\treg = <0x0 0xca000000 (1440 * 3040 * 4)>;
\t\t\tno-map;
\t\t};

\t\tmodem_spare@d0000000 {
\t\t\treg = <0x0 0xd0000000 0x1600000>;
\t\t\tno-map;
\t\t};

\t\tmodem_if@f0000000 {
\t\t\treg = <0x0 0xf0000000 0xb900000>;
\t\t\tno-map;
\t\t};

\t\tcp_ram_logging@fb900000 {
\t\t\treg = <0x0 0xfb900000 0x2000000>;
\t\t\tno-map;
\t\t};

\t\tel2_earlymem@9fd800000 {
\t\t\treg = <0x9 0xfd800000 0x2800000>;
\t\t\tno-map;
\t\t};
\t};
};
'''

PIN = '''
\t%(etykieta)s: %(wezel)s {
\t\tsamsung,pins = "%(pin)s";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_EINT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV1>;
\t};
'''

PINY = [
    ("key_volup", "key-volup-pins", "gpa0-3"),
    ("key_voldown", "key-voldown-pins", "gpa0-4"),
    ("key_wink", "key-wink-pins", "gpa0-6"),
    ("key_power", "key-power-pins", "gpa2-4"),
    ("ts_int", "ts-int-pins", "gpa1-0"),
]

# (etap, klucz sortowania, tresc).  Klucz to nazwa wezla, ktory nadpisujemy,
# zeby kolejnosc byla alfabetyczna i niezalezna od etapu.
BLOKI = [
    (2, "decon0", '''
&decon0 {
\tstatus = "okay";
};
'''),
    (2, "dsim0", '''
&dsim0 {
\tstatus = "okay";

\tpanel@0 {
\t\tcompatible = "samsung,s6e3ha9";
\t\treg = <0>;

\t\tvdd3-supply = <&panel_vdd3>;
\t\tvci-supply = <&panel_vci>;
\t\tvddr-supply = <&panel_vddr>;

\t\treset-gpios = <&gpa3 4 GPIO_ACTIVE_LOW>;

\t\tport {
\t\t\tpanel_in: endpoint {
\t\t\t\tremote-endpoint = <&dsim0_out>;
\t\t\t};
\t\t};
\t};
};
'''),
    (2, "hsi2c2", '''
/*
 * The display PMIC.  Its three rails are the panel's, and the names below are
 * the roles the vendor gives them: ddi-3p0 is vci, ddi-1p8 is vdd3 and
 * ddr-1p6 is vddr.  The buck can also run at 1.5 V in the vendor's low power
 * mode, which is not modelled here.
 *
 * The bus is not a guess.  The vendor keeps this chip in a device tree
 * overlay whose target is a label rather than a path, and the fixup table
 * resolves it: hsi2c_44 owns the fragment that holds s2dos05_pmic@60
 * (ds/exynos9820-beyond2lte_eur_open_26.dts:8271), and hsi2c_44 is the node
 * at 0x15d50000 (ds/exynos9820.dts:11537), which is this one.
 */
&hsi2c2 {
\tstatus = "okay";

\tpmic@60 {
\t\tcompatible = "samsung,s2dos05";
\t\treg = <0x60>;

\t\tregulators {
\t\t\tpanel_vddr: buck {
\t\t\t\tregulator-name = "panel_vddr";
\t\t\t\tregulator-min-microvolt = <1600000>;
\t\t\t\tregulator-max-microvolt = <1600000>;
\t\t\t\tregulator-boot-on;
\t\t\t};

\t\t\tpanel_vdd3: ldo1 {
\t\t\t\tregulator-name = "panel_vdd3";
\t\t\t\tregulator-min-microvolt = <1800000>;
\t\t\t\tregulator-max-microvolt = <1800000>;
\t\t\t\tregulator-boot-on;
\t\t\t};

\t\t\tpanel_vci: ldo4 {
\t\t\t\tregulator-name = "panel_vci";
\t\t\t\tregulator-min-microvolt = <3000000>;
\t\t\t\tregulator-max-microvolt = <3000000>;
\t\t\t\tregulator-boot-on;
\t\t\t};
\t\t};
\t};
};
'''),
    (1, "hsi2c10", '''
&hsi2c10 {
\tclock-frequency = <400000>;
\tstatus = "okay";

\ttouchscreen@48 {
\t\tcompatible = "samsung,s6sy761";
\t\treg = <0x48>;

\t\tavdd-supply = <&reg_tsp_avdd>;
\t\tvdd-supply = <&reg_tsp_io>;

\t\tinterrupts-extended = <&gpa1 0 IRQ_TYPE_LEVEL_LOW>;

\t\tpinctrl-0 = <&ts_int>;
\t\tpinctrl-names = "default";
\t};
};
'''),
    (1, "oscclk", '''
&oscclk {
\tclock-frequency = <26000000>;
};
'''),
    (1, "pinctrl_alive", None),   # wypelniane z tablicy PINY
    (1, "serial0", '''
&serial0 {
\tstatus = "okay";
};
'''),
    (1, "usi3", '''
/* This USI instance is wired as the touchscreen I2C master on this board. */
&usi3 {
\tsamsung,mode = <USI_V2_I2C>;
\tstatus = "okay";
};
'''),
]


def blok_pinow():
    czesci = [NL + "&pinctrl_alive {"]
    for etykieta, wezel, pin in PINY:
        czesci.append(PIN % {"etykieta": etykieta, "wezel": wezel, "pin": pin})
    czesci.append("};" + NL)
    return "".join(czesci)


def emituj(etap):
    czesci = [NAGLOWEK]
    for e, klucz, tresc in sorted(BLOKI, key=lambda x: x[1]):
        if e > etap:
            continue
        czesci.append(tresc if tresc is not None else blok_pinow())
    return "".join(czesci)


def main():
    if "--etap" not in sys.argv:
        for e in sorted(ETAPY):
            t = emituj(e)
            print("etap %d: %3d linii  (%s)" % (e, t.count(NL), ETAPY[e]))
        return
    etap = int(sys.argv[sys.argv.index("--etap") + 1])
    if etap not in ETAPY:
        sys.exit("etap poza 1..2")
    tresc = emituj(etap)
    if "--zapisz" in sys.argv:
        io.open(CEL, "w", encoding="utf-8", newline=NL).write(tresc)
        print("zapisano %s (etap %d, %d linii)" % (CEL, etap, tresc.count(NL)))
    else:
        sys.stdout.write(tresc)


if __name__ == "__main__":
    main()
