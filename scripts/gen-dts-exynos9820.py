#!/usr/bin/env python3
"""Wypisuje exynos9820.dtsi w wersji odpowiedniej dla danego etapu serii.

Plik rosnie w czterech krokach: podstawowe drzewo SoC, domena zasilania DPU,
zegary i MMU bloku DPU, na koncu potok wyswietlacza.  Gdyby kazdy z tych
commitow trzymal wlasna, recznie utrzymywana kopie, rozjechalyby sie przy
pierwszej poprawce; dlatego zrodlem prawdy jest ten skrypt, a commity dostaja
z niego wersje na swoj etap.

Wezly pod soc@0 sa wypisywane w kolejnosci ADRESU, niezaleznie od tego, ktory
etap je wnosi.  To jest jedyna roznica wobec wczesniejszej wersji pliku,
w ktorej blok wyswietlacza stal przed wlasnym kontrolerem zegarow.  W zbudowanym
drzewie zmieniaja sie przez to wylacznie numery phandle; sprawdzone przez
kanonizacje odwolan: 1039 linii zrzutu po obu stronach, zero roznic w wartosciach.

Uzycie:
  scripts/gen-dts-exynos9820.py --etap 1..4 [--zapisz]
"""
import io
import os
import sys

NL = chr(10)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CEL = os.path.join(ROOT, "sources", "linux", "arch", "arm64", "boot", "dts",
                   "exynos", "exynos9820.dtsi")

ETAPY = {
    1: "arm64: dts: exynos: Add minimal Exynos9820 SoC and Galaxy S10+ support",
    2: "arm64: dts: exynos: exynos9820: Add the DPU power domain",
    3: "arm64: dts: exynos: exynos9820: Add CMU_DPU and the DPU System MMUs",
    4: "arm64: dts: exynos: exynos9820: Add the display pipeline",
    5: "arm64: dts: exynos: exynos9820: Add CMU_FSYS1 and its system registers",
    6: "arm64: dts: exynos: exynos9820: Add the UFS host and its PHY",
    7: "arm64: dts: exynos: exynos9820: Add CMU_FSYS0A and the USB controller",
    8: "arm64: dts: exynos: exynos9820: Add the bus the main PMIC sits on",
    9: "arm64: dts: exynos: exynos9820: Add the APM mailbox and the ACPM firmware",
    10: "arm64: dts: exynos: exynos9820: Add CMU_PERIC1 and the Bluetooth UART",
    11: "arm64: dts: exynos: exynos9820: Add the CPU interrupt generator",
    12: "arm64: dts: exynos: exynos9820: Add the PCIe controller the Wi-Fi chip sits on",
    13: "arm64: dts: exynos: exynos9820: Add the reboot modes of the bootloader",
    14: "arm64: dts: exynos: exynos9820: Add the TMU and the thermal zones",
    15: "arm64: dts: exynos: exynos9820: Add CPU DVFS through ACPM",
    16: "arm64: dts: exynos: exynos9820: Add the Mali-G76 GPU",
    17: "arm64: dts: exynos: exynos9820: Add GPU DVFS through ACPM",
    18: "arm64: dts: exynos: exynos9820: Throttle harder above 92 C",
    19: "arm64: dts: exynos: exynos9820: Add the I2C bus of the speaker amplifiers",
    20: "arm64: dts: exynos: exynos9820: Add the SPI bus of the audio codec",
    21: "arm64: dts: exynos: exynos9820: Add CMU_AUD",
    22: "arm64: dts: exynos: exynos9820: Add the ABOX audio subsystem",
    23: "arm64: dts: exynos: exynos9820: Add the SPI bus of the sensor hub",
    24: "arm64: dts: exynos: exynos9820: Add the PWM timer block",
    25: "arm64: dts: exynos: exynos9820: Add the SD card host",
}

NAGLOWEK = '''// SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause
/*
 * Samsung Exynos9820 SoC device tree source
 *
 * Copyright (C) 2026 Artur Szafraniec <ganggg111@gmail.com>
 *
 * This describes the part of the SoC that the drivers in this series can
 * actually reach: the eight CPUs, the clock controllers, the pin controllers,
 * the system timer, the interrupt controller, the debug UART and the buses the
 * board needs.  Everything else the SoC has is left out rather than described
 * and disabled, because a node nobody drives is a claim nobody checks.
 *
 * Addresses, interrupt numbers and clock indices come from the vendor sources
 * listed in SOURCES.md.  Nodes under soc@0 are ordered by their unit address.
 *
 * UNVERIFIED: every interrupt here is described as level high, the way every
 * other Exynos SoC in this tree describes its own, but that is not the shape
 * the phone runs with: the vendor tree sets no type at all and its kernel ends
 * up with the lines as edge.  The numbers are confirmed against the running
 * system, only the type is open, and getting it wrong gives either a storm or
 * an interrupt that never arrives.  Each block has to be made to raise its
 * line.  Copying the vendor's unset type is not the fix.
 */

%(naglowki)s
/ {
\tcompatible = "samsung,exynos9820";
\t#address-cells = <2>;
\t#size-cells = <1>;

\tinterrupt-parent = <&gic>;

\t/*
\t * The pin controller driver picks its bank tables by this alias, so the
\t * numbering is not cosmetic: pinctrlN has to name the Nth entry of
\t * exynos9820_pin_ctrl[].
\t */
\taliases {
\t\tpinctrl0 = &pinctrl_alive;
\t\tpinctrl1 = &pinctrl_aud;
\t\tpinctrl2 = &pinctrl_cmgp;
\t\tpinctrl3 = &pinctrl_fsys0;
\t\tpinctrl4 = &pinctrl_fsys1;
\t\tpinctrl5 = &pinctrl_peric0;
\t\tpinctrl6 = &pinctrl_peric1;
\t\tpinctrl7 = &pinctrl_vts;
%(aliasy_portow)s\t};

\t/*
\t * Three clusters: four Cortex-A55, two Cortex-A75 and two Mongoose M4.
\t * The M4 pair sits behind its own affinity level, hence the 0x100 in its
\t * MPIDR rather than a flat numbering.
\t */
\tcpus {
\t\t#address-cells = <1>;
\t\t#size-cells = <0>;

\t\tcpu-map {
\t\t\tcluster0 {
\t\t\t\tcore0 {
\t\t\t\t\tcpu = <&cpu0>;
\t\t\t\t};
\t\t\t\tcore1 {
\t\t\t\t\tcpu = <&cpu1>;
\t\t\t\t};
\t\t\t\tcore2 {
\t\t\t\t\tcpu = <&cpu2>;
\t\t\t\t};
\t\t\t\tcore3 {
\t\t\t\t\tcpu = <&cpu3>;
\t\t\t\t};
\t\t\t};

\t\t\tcluster1 {
\t\t\t\tcore0 {
\t\t\t\t\tcpu = <&cpu4>;
\t\t\t\t};
\t\t\t\tcore1 {
\t\t\t\t\tcpu = <&cpu5>;
\t\t\t\t};
\t\t\t};

\t\t\tcluster2 {
\t\t\t\tcore0 {
\t\t\t\t\tcpu = <&cpu6>;
\t\t\t\t};
\t\t\t\tcore1 {
\t\t\t\t\tcpu = <&cpu7>;
\t\t\t\t};
\t\t\t};
\t\t};
%(rdzenie)s\t};

\t/*
\t * The 26 MHz crystal every clock controller takes as its reference.  The
\t * rate is a property of the board, so the board file fills it in.
\t */
\toscclk: osc-clock {
\t\tcompatible = "fixed-clock";
\t\t#clock-cells = <0>;
\t\tclock-output-names = "oscclk";
\t};

\t/* One performance monitor node per core type, as the PMUs differ. */
\tpmu-a55 {
\t\tcompatible = "arm,cortex-a55-pmu";
\t\tinterrupts = <GIC_SPI 141 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t     <GIC_SPI 142 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t     <GIC_SPI 143 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t     <GIC_SPI 144 IRQ_TYPE_LEVEL_HIGH>;
\t\tinterrupt-affinity = <&cpu0>, <&cpu1>, <&cpu2>, <&cpu3>;
\t};

\tpmu-a75 {
\t\tcompatible = "arm,cortex-a75-pmu";
\t\tinterrupts = <GIC_SPI 145 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t     <GIC_SPI 146 IRQ_TYPE_LEVEL_HIGH>;
\t\tinterrupt-affinity = <&cpu4>, <&cpu5>;
\t};

\tpmu-mongoose {
\t\tcompatible = "samsung,mongoose-pmu";
\t\tinterrupts = <GIC_SPI 174 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t     <GIC_SPI 175 IRQ_TYPE_LEVEL_HIGH>;
\t\tinterrupt-affinity = <&cpu6>, <&cpu7>;
\t};

\tpsci {
\t\tcompatible = "arm,psci";
\t\tmethod = "smc";
\t\tcpu_suspend = <0xc4000001>;
\t\tcpu_off = <0x84000002>;
\t\tcpu_on = <0xc4000003>;
\t};

\tsoc: soc@0 {
\t\tcompatible = "simple-bus";
\t\t#address-cells = <1>;
\t\t#size-cells = <1>;
\t\tranges = <0x0 0x0 0x0 0x20000000>;
'''

RDZEN = '''
\t\tcpu%(n)d: cpu@%(reg)s {
\t\t\tdevice_type = "cpu";
\t\t\tcompatible = "%(compat)s";
\t\t\treg = <0x%(reg)s>;
%(zegar)s\t\t\tenable-method = "psci";
\t\t\tcapacity-dmips-mhz = <%(cap)d>;
\t\t\tdynamic-power-coefficient = <%(dpc)d>;
%(opp)s\t\t};
'''

# Etap 15: klaster kazdego rdzenia (0 A55, 1 A75, 2 M4) i jego domena DVFS.
KLASTER = {0: 0, 1: 0, 2: 0, 3: 0, 4: 1, 5: 1, 6: 2, 7: 2}

NAGLOWKI = ["#include <dt-bindings/clock/samsung,exynos9820.h>",
            "#include <dt-bindings/gpio/gpio.h>",
            "#include <dt-bindings/interrupt-controller/arm-gic.h>"]
NAGLOWKI_15 = ["#include <dt-bindings/clock/samsung,exynos9820-acpm.h>",
               "#include <dt-bindings/clock/samsung,exynos9820.h>",
               "#include <dt-bindings/gpio/gpio.h>",
               "#include <dt-bindings/interrupt-controller/arm-gic.h>",
               "#include <dt-bindings/thermal/thermal.h>"]

# Poziomy z tablic fvmap firmware tego egzemplarza (kHz, uV), odczytane
# 24.09.2026 (measurements/2026-09-24-termika/fvmap-dvfs.txt), w granicach
# min/max domen cpufreq producenta.  Bez poziomow, ktore u producenta
# wymagaja podniesienia MIF (CL1 2314 i 2400, CL2 od 2236): jadro MIF nie
# steruje.  CL2 konczy sie na 2080 MHz, domyslnym maksimum producenta.
OPP = {
    0: [(442000, 568750), (546000, 587500), (650000, 612500), (806000, 656250),
        (949000, 687500), (1053000, 718750), (1157000, 750000),
        (1300000, 793750), (1456000, 837500), (1586000, 887500),
        (1742000, 968750), (1846000, 1018750), (1950000, 1062500)],
    1: [(507000, 581250), (650000, 587500), (754000, 612500), (845000, 625000),
        (962000, 637500), (1066000, 662500), (1222000, 700000),
        (1404000, 731250), (1508000, 756250), (1586000, 768750),
        (1690000, 793750), (1794000, 831250), (1898000, 862500),
        (2002000, 893750), (2106000, 925000), (2210000, 968750)],
    2: [(520000, 581250), (624000, 587500), (728000, 593750), (819000, 600000),
        (936000, 618750), (1040000, 631250), (1144000, 662500),
        (1248000, 668750), (1378000, 693750), (1456000, 706250),
        (1560000, 725000), (1664000, 750000), (1820000, 775000),
        (1976000, 818750), (2080000, 850000)],
}

OPP_WPIS = '''
\t\topp-%(hz)d {
\t\t\topp-hz = /bits/ 64 <%(hz)d>;
\t\t\topp-microvolt = <%(uv)d>;
\t\t\tclock-latency-ns = <1000000>;
\t\t};
'''

OPP_TABELA = '''
\tcpucl%(k)d_opp_table: opp-table-%(k)d {
\t\tcompatible = "operating-points-v2";
\t\topp-shared;
%(wpisy)s\t};
'''

OPP_KOMENTARZ = '''
\t/*
\t * The levels the DVFS firmware on the APM keeps for each cluster, within
\t * the limits the vendor gives its cpufreq domains.  The firmware sets the
\t * voltage of a level itself; the voltages here are the ones it reports
\t * for this unit and only feed the energy model.  The levels the vendor
\t * allows only with the memory clock raised are left out, because nothing
\t * in the kernel moves that clock.  A request is acknowledged within 1 ms.
\t */'''

# Etap 17: poziomy GPU (kHz) z tabeli producenta (gpu_dvfs_table, 156-702
# MHz), z czestotliwosciami z fvmap tego egzemplarza (433, nie 432).  Fvmap
# ma jeszcze 100, 598 i 676 MHz; producent ich nie uzywa, wiec tu tez nie.
# Zmierzone 24.09.2026: 156 -> 325 MHz daje 1,90x w glmark2 texture.
GPU_OPP = [156000, 200000, 260000, 325000, 377000, 433000, 572000, 650000,
           702000]

GPU_OPP_TABELA = '''
\t/*
\t * The levels the vendor gives the GPU, at the frequencies the DVFS
\t * firmware keeps for them.  The firmware sets the voltage of a level
\t * itself.
\t */
\tgpu_opp_table: opp-table-gpu {
\t\tcompatible = "operating-points-v2";
%s\t};
'''

GPU_OPP_WPIS = '''
\t\topp-%(hz)d {
\t\t\topp-hz = /bits/ 64 <%(hz)d>;
\t\t};
'''

GPU_KOMENTARZ_16 = '''\t\t * 0x00770077 on this phone.  The firmware on the APM owns its clock
\t\t * and voltage, and with no operating points the GPU stays at the
\t\t * level the firmware starts it at.  The power domain is left out:
'''

GPU_KOMENTARZ_17 = '''\t\t * 0x00770077 on this phone.  The firmware on the APM owns its clock
\t\t * and voltage; panfrost picks the level through devfreq and the GPU
\t\t * thermal zone throttles it.  The power domain is left out:
'''


def dvfs_gpu(etap):
    """Wstawki wezla GPU: komentarz i wiersze DVFS; DVFS od etapu 17."""
    if etap < 17:
        return {"gpu_komentarz": GPU_KOMENTARZ_16, "gpu_dvfs": ""}
    return {"gpu_komentarz": GPU_KOMENTARZ_17,
            "gpu_dvfs": "\t\t\toperating-points-v2 = <&gpu_opp_table>;" + NL +
                        "\t\t\t#cooling-cells = <2>;" + NL}


RDZENIE = [
    (0, "0", "arm,cortex-a55", 272, 160),
    (1, "1", "arm,cortex-a55", 272, 160),
    (2, "2", "arm,cortex-a55", 272, 160),
    (3, "3", "arm,cortex-a55", 272, 160),
    (4, "4", "arm,cortex-a75", 531, 320),
    (5, "5", "arm,cortex-a75", 531, 320),
    (6, "100", "samsung,mongoose-m4", 785, 760),
    (7, "101", "samsung,mongoose-m4", 785, 760),
]

OGON = '''\t};
%s
\ttimer {
\t\tcompatible = "arm,armv8-timer";

\t\t/*
\t\t * Hypervisor Virtual Timer interrupt is not wired to the GIC
\t\t * and S-Boot leaves CNTFRQ_EL0 unconfigured.
\t\t */
\t\tinterrupts = <GIC_PPI 13 (GIC_CPU_MASK_SIMPLE(8) | IRQ_TYPE_LEVEL_LOW)>,
\t\t\t     <GIC_PPI 14 (GIC_CPU_MASK_SIMPLE(8) | IRQ_TYPE_LEVEL_LOW)>,
\t\t\t     <GIC_PPI 11 (GIC_CPU_MASK_SIMPLE(8) | IRQ_TYPE_LEVEL_LOW)>,
\t\t\t     <GIC_PPI 10 (GIC_CPU_MASK_SIMPLE(8) | IRQ_TYPE_LEVEL_LOW)>;
\t\tclock-frequency = <26000000>;
\t};
};

#include "exynos9820-pinctrl.dtsi"
'''

# (etap, adres, tresc wezla).  Adres decyduje o kolejnosci w pliku, etap o tym,
# ktory commit serii go wnosi.
FIRMWARE = '''
\t/*
\t * The firmware on the Active Power Manager, and the only way to reach the
\t * main PMIC of this board: it is not on a bus of the processor at all.
\t * The vendor describes it as sitting on a SPEEDY channel of this firmware
\t * rather than of the CPU, and leaves the SPEEDY controllers disabled.
\t * Everything the board powers, the touchscreen rails among it, hangs off
\t * the other end of this mailbox.
\t */
\tfirmware {
\t\tacpm_ipc: power-management {
\t\t\tcompatible = "samsung,exynos9820-acpm-ipc";
\t\t\t#clock-cells = <1>;
\t\t\tmboxes = <&ap2apm_mailbox>;
\t\t\tshmem = <&apm_sram>;
\t\t};
\t};
'''


# Etap 14.  Strefy w kolejnosci nazw: (nazwa, blok, numer strefy firmware).
# Blok TOP ma klastry CPU (0 big, 1 mid, 2 little), SUB GPU (3) i ISP (4).
# Prog krytyczny 100 C: 15 C pod sprzetowym tripem 115 C, ktory S-Boot
# uzbraja w obu blokach (zmierzone 24.09.2026, CONTROL 0x00009503, poziom 7
# = kod 0x17b).
STREFY = [("big", "tmu_top", 0), ("gpu", "tmu_sub", 3), ("isp", "tmu_sub", 4),
          ("little", "tmu_top", 2), ("mid", "tmu_top", 1)]

STREFA = '''
\t\t%(n)s-thermal {
\t\t\tpolling-delay = <1000>;
\t\t\tthermal-sensors = <&%(blok)s %(id)d>;

\t\t\ttrips {
\t\t\t\t%(n)s-critical {
\t\t\t\t\ttemperature = <100000>;
\t\t\t\t\thysteresis = <0>;
\t\t\t\t\ttype = "critical";
\t\t\t\t};
\t\t\t};
\t\t};
'''

TERMIKA = '''
\t/*
\t * Nothing can be throttled yet: without cpufreq or cpuidle there is no
\t * cooling device.  What is left is a critical trip 15 C below the
\t * hardware trip of the TMU, so the kernel powers the phone off in order
\t * before the TMU removes the power.
\t */
\tthermal-zones {%s\t};
'''

# Etap 15: strefy klastrow dostaja prog pasywny i dlawienie wlasnego klastra.
# 85 C: tuz nad 83 C, na ktorych producent zaczyna dlawic big i mid.
# Zmierzone 24.09.2026: przy zegarach maksymalnych i pelnym obciazeniu big
# szedl z 45 do 99 C w okolo minute, wiec odpytywanie co 100 ms po progu.
STREFA_RDZENIE = {"big": (6, 7), "little": (0, 1, 2, 3), "mid": (4, 5)}

STREFA_KLASTRA = '''
\t\t%(n)s-thermal {
\t\t\tpolling-delay-passive = <100>;
\t\t\tpolling-delay = <1000>;
\t\t\tthermal-sensors = <&%(blok)s %(id)d>;

\t\t\ttrips {
\t\t\t\t%(n)s_alert: %(n)s-alert {
\t\t\t\t\ttemperature = <85000>;
\t\t\t\t\thysteresis = <2000>;
\t\t\t\t\ttype = "passive";
\t\t\t\t};

\t\t\t\t%(n)s-critical {
\t\t\t\t\ttemperature = <100000>;
\t\t\t\t\thysteresis = <0>;
\t\t\t\t\ttype = "critical";
\t\t\t\t};
\t\t\t};

\t\t\tcooling-maps {
\t\t\t\tmap0 {
\t\t\t\t\ttrip = <&%(n)s_alert>;
\t\t\t\t\tcooling-device = %(chlodzenie)s;
\t\t\t\t};
\t\t\t};
\t\t};
'''

TERMIKA_15 = '''
\t/*
\t * Each CPU cluster is throttled through cpufreq from 85 C on.  The
\t * critical trip stays 15 C below the hardware trip of the TMU, so the
\t * kernel powers the phone off in order before the TMU removes the power;
\t * the GPU and ISP zones have nothing to throttle yet.
\t */
\tthermal-zones {%s\t};
'''


# Etap 17: strefa GPU dostaje ten sam prog co klastry.  Producent reguluje
# GPU od 88 C (gpu-control-temp), 85 C jest ponizej.
TERMIKA_17 = '''
\t/*
\t * Each CPU cluster is throttled through cpufreq and the GPU through
\t * devfreq from 85 C on.  The critical trip stays 15 C below the hardware
\t * trip of the TMU, so the kernel powers the phone off in order before the
\t * TMU removes the power; the ISP zone has nothing to throttle yet.
\t */
\tthermal-zones {%s\t};
'''


# Etap 18: drugi prog pasywny 92 C z dolna granica chlodzenia, jako siatka
# miedzy progiem 85 C a krytycznym 100 C.  step_wise podnosi stan tylko przy
# rosnacej temperaturze, a czujnik ma krok 1 C.  Kompilacja Mesy na 8
# rdzeniach dala raz odczyt big 95 C (24.09.2026); powtorka 240 s z tym
# etapem: max 91 C, prog 85 C doszedl do stanow 8-10, nowy prog nie musial
# dzialac.  Stan 8: big 1144, mid 1404, little 949 MHz; GPU stan 4: 377 MHz.
STREFA_GORACA_MIN = {"big": 8, "mid": 8, "little": 8, "gpu": 4}

STREFA_KLASTRA_18 = '''
\t\t%(n)s-thermal {
\t\t\tpolling-delay-passive = <100>;
\t\t\tpolling-delay = <1000>;
\t\t\tthermal-sensors = <&%(blok)s %(id)d>;

\t\t\ttrips {
\t\t\t\t%(n)s_alert: %(n)s-alert {
\t\t\t\t\ttemperature = <85000>;
\t\t\t\t\thysteresis = <2000>;
\t\t\t\t\ttype = "passive";
\t\t\t\t};

\t\t\t\t%(n)s_hot: %(n)s-hot {
\t\t\t\t\ttemperature = <92000>;
\t\t\t\t\thysteresis = <2000>;
\t\t\t\t\ttype = "passive";
\t\t\t\t};

\t\t\t\t%(n)s-critical {
\t\t\t\t\ttemperature = <100000>;
\t\t\t\t\thysteresis = <0>;
\t\t\t\t\ttype = "critical";
\t\t\t\t};
\t\t\t};

\t\t\tcooling-maps {
\t\t\t\tmap0 {
\t\t\t\t\ttrip = <&%(n)s_alert>;
\t\t\t\t\tcooling-device = %(chlodzenie)s;
\t\t\t\t};

\t\t\t\tmap1 {
\t\t\t\t\ttrip = <&%(n)s_hot>;
\t\t\t\t\tcooling-device = %(chlodzenie_gorace)s;
\t\t\t\t};
\t\t\t};
\t\t};
'''

TERMIKA_18 = '''
\t/*
\t * Each CPU cluster and the GPU are throttled through cpufreq or devfreq
\t * from 85 C on, and from 92 C on at least to about half of their top
\t * clock: step_wise raises the cooling state only while the temperature
\t * keeps rising, so with the 1 C steps of the TMU a steady load can sit
\t * above the first trip without the state moving.  The critical trip stays
\t * 15 C below the hardware trip of the TMU, so the kernel powers the phone
\t * off in order before the TMU removes the power; the ISP zone has nothing
\t * to throttle yet.
\t */
\tthermal-zones {%s\t};
'''


def strefa(n, blok, i, etap):
    if etap >= 18 and n in STREFA_GORACA_MIN:
        dol = STREFA_GORACA_MIN[n]
        wcieta = "," + NL + "\t" * 7 + " "
        rdzenie = ["gpu"] if n == "gpu" else ["cpu%d" % r for r in STREFA_RDZENIE[n]]
        chl = wcieta.join("<&%s THERMAL_NO_LIMIT THERMAL_NO_LIMIT>" % c
                          for c in rdzenie)
        chl_g = wcieta.join("<&%s %d THERMAL_NO_LIMIT>" % (c, dol)
                            for c in rdzenie)
        return STREFA_KLASTRA_18 % {"n": n, "blok": blok, "id": i,
                                    "chlodzenie": chl,
                                    "chlodzenie_gorace": chl_g}
    if n == "gpu" and etap >= 17:
        chl = "<&gpu THERMAL_NO_LIMIT THERMAL_NO_LIMIT>"
        return STREFA_KLASTRA % {"n": n, "blok": blok, "id": i,
                                 "chlodzenie": chl}
    if etap < 15 or n not in STREFA_RDZENIE:
        return STREFA % {"n": n, "blok": blok, "id": i}
    wcieta = "," + NL + "\t" * 7 + " "
    chl = wcieta.join("<&cpu%d THERMAL_NO_LIMIT THERMAL_NO_LIMIT>" % r
                      for r in STREFA_RDZENIE[n])
    return STREFA_KLASTRA % {"n": n, "blok": blok, "id": i, "chlodzenie": chl}

WEZLY = [
    (9, 0x02039000, '''\t\t/*
\t\t * The memory the firmware and the processor pass messages through.
\t\t * Its size is the one the vendor states for this SoC; the channel
\t\t * configuration sits at an offset inside it that the protocol driver
\t\t * knows from the compatible.
\t\t */
\t\tapm_sram: sram@2039000 {
\t\t\tcompatible = "mmio-sram";
\t\t\treg = <0x2039000 0x30000>;
\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <1>;
\t\t\tranges = <0x0 0x2039000 0x30000>;
\t\t};
'''),
    (9, 0x15900000, '''\t\t/*
\t\t * The doorbell the processor rings to make the firmware look at the
\t\t * memory above.  It carries no payload of its own, which is why the
\t\t * driver needs no channel number here.
\t\t */
\t\tap2apm_mailbox: mailbox@15900000 {
\t\t\tcompatible = "samsung,exynos9820-mbox";
\t\t\treg = <0x15900000 0x1000>;
\t\t\tinterrupts = <GIC_SPI 40 IRQ_TYPE_LEVEL_HIGH>;
\t\t\tclocks = <&cmu_apm CLK_GOUT_APM_MAILBOX_APM_AP_PCLK>;
\t\t\tclock-names = "pclk";
\t\t\t#mbox-cells = <0>;
\t\t};
'''),
    (1, 0x10000000, '''\t\tchipid@10000000 {
\t\t\tcompatible = "samsung,exynos9820-chipid",
\t\t\t\t     "samsung,exynos850-chipid";
\t\t\treg = <0x10000000 0x100>;
\t\t};
'''),
    (1, 0x10020000, '''\t\tcmu_peris: clock-controller@10020000 {
\t\t\tcompatible = "samsung,exynos9820-cmu-peris";
\t\t\treg = <0x10020000 0x8000>;
\t\t\t#clock-cells = <1>;

\t\t\tclocks = <&oscclk>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_PERIS_BUS>;
\t\t\tclock-names = "oscclk", "bus";
\t\t};
'''),
    (1, 0x10040000, '''\t\t/*
\t\t * Twelve comparators, one per core plus four global ones; the
\t\t * driver takes them in that order.
\t\t */
\t\ttimer@10040000 {
\t\t\tcompatible = "samsung,exynos9820-mct",
\t\t\t\t     "samsung,exynos4210-mct";
\t\t\treg = <0x10040000 0x800>;
\t\t\tclocks = <&oscclk>,
\t\t\t\t <&cmu_peris CLK_GOUT_PERIS_MCT_PCLK>;
\t\t\tclock-names = "fin_pll", "mct";
\t\t\tinterrupts = <GIC_SPI 466 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 467 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 468 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 469 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 470 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 471 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 472 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 473 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 474 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 475 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 476 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 477 IRQ_TYPE_LEVEL_HIGH>;
\t\t};
'''),
    (1, 0x10101000, '''\t\tgic: interrupt-controller@10101000 {
\t\t\tcompatible = "arm,gic-400";
\t\t\t#interrupt-cells = <3>;
\t\t\t#address-cells = <0>;
\t\t\tinterrupt-controller;
\t\t\treg = <0x10101000 0x1000>,
\t\t\t      <0x10102000 0x1000>,
\t\t\t      <0x10104000 0x2000>,
\t\t\t      <0x10106000 0x2000>;
\t\t\tinterrupts = <GIC_PPI 9 (GIC_CPU_MASK_SIMPLE(8) |
\t\t\t\t\t\t IRQ_TYPE_LEVEL_HIGH)>;
\t\t};
'''),
    (1, 0x10400000, '''\t\tcmu_peric0: clock-controller@10400000 {
\t\t\tcompatible = "samsung,exynos9820-cmu-peric0";
\t\t\treg = <0x10400000 0x8000>;
\t\t\t#clock-cells = <1>;

\t\t\tclocks = <&oscclk>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_PERIC0_BUS>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_PERIC0_IP>;
\t\t\tclock-names = "oscclk", "bus", "ip";
\t\t};
'''),
    (1, 0x10420000, '''\t\t/* Holds the mode register the USI blocks of this domain use. */
\t\tsysreg_peric0: syscon@10420000 {
\t\t\tcompatible = "samsung,exynos9820-peric0-sysreg",
\t\t\t\t     "syscon";
\t\t\treg = <0x10420000 0x2000>;
\t\t\tclocks = <&cmu_peric0 CLK_GOUT_PERIC0_SYSREG_PERIC0_PCLK>;
\t\t};
'''),
    (1, 0x10430000, '''\t\tpinctrl_peric0: pinctrl@10430000 {
\t\t\tcompatible = "samsung,exynos9820-pinctrl";
\t\t\treg = <0x10430000 0x1000>;
\t\t\tinterrupts = <GIC_SPI 380 IRQ_TYPE_LEVEL_HIGH>;
\t\t};
'''),
    (1, 0x10440000, '''\t\tserial0: serial@10440000 {
\t\t\tcompatible = "samsung,exynos9820-uart",
\t\t\t\t     "samsung,exynos8895-uart";
\t\t\treg = <0x10440000 0x100>;
\t\t\tinterrupts = <GIC_SPI 381 IRQ_TYPE_LEVEL_HIGH>;
\t\t\tclocks = <&cmu_peric0 CLK_GOUT_PERIC0_UART_DBG_PCLK>,
\t\t\t\t <&cmu_peric0 CLK_GOUT_PERIC0_UART_DBG_IPCLK>;
\t\t\tclock-names = "uart", "clk_uart_baud0";
\t\t\tsamsung,uart-fifosize = <256>;
\t\t\tstatus = "disabled";
\t\t};
'''),
    (20, 0x104700c0, '''\t\t/*
\t\t * The second full USI block of PERIC0, vendor usi_1, mode register
\t\t * at 0x100c.  Its SPI master is the vendor spi_2: the vendor counts
\t\t * SPI masters from one in PERIC1, so the SPI index runs one ahead of
\t\t * the USI index.  The 64 byte FIFO of the vendor node is the one of
\t\t * the Exynos850 controller.
\t\t */
\t\tusi1: usi@104700c0 {
\t\t\tcompatible = "samsung,exynos9820-usi",
\t\t\t\t     "samsung,exynos850-usi";
\t\t\treg = <0x104700c0 0x20>;
\t\t\tranges;
\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <1>;

\t\t\tclocks = <&cmu_peric0 CLK_GOUT_PERIC0_USI01_USI_PCLK>,
\t\t\t\t <&cmu_peric0 CLK_GOUT_PERIC0_USI01_USI_IPCLK>;
\t\t\tclock-names = "pclk", "ipclk";
\t\t\tsamsung,sysreg = <&sysreg_peric0 0x100c>;
\t\t\tsamsung,clkreq-on;
\t\t\tstatus = "disabled";

\t\t\tspi_2: spi@10470000 {
\t\t\t\tcompatible = "samsung,exynos9820-spi",
\t\t\t\t\t     "samsung,exynos850-spi";
\t\t\t\treg = <0x10470000 0x30>;
\t\t\t\tinterrupts = <GIC_SPI 384 IRQ_TYPE_LEVEL_HIGH>;
\t\t\t\t#address-cells = <1>;
\t\t\t\t#size-cells = <0>;

\t\t\t\tclocks = <&cmu_peric0 CLK_GOUT_PERIC0_USI01_USI_PCLK>,
\t\t\t\t\t <&cmu_peric0 CLK_GOUT_PERIC0_USI01_USI_IPCLK>;
\t\t\t\tclock-names = "spi", "spi_busclk0";
\t\t\t\tpinctrl-0 = <&spi2_bus>;
\t\t\t\tpinctrl-names = "default";
\t\t\t\tstatus = "disabled";
\t\t\t};
\t\t};
'''),
    (1, 0x104b00c0, '''\t\t/*
\t\t * A USI block is one piece of hardware that can be a UART, an SPI
\t\t * master or an I2C master; the mode lives in the PERIC0 system
\t\t * register, and the child node below is the mode this board picks.
\t\t * The USI configuration window sits above the peripheral window,
\t\t * which is why the parent address is the higher of the two.
\t\t */
\t\tusi3: usi@104b00c0 {
\t\t\tcompatible = "samsung,exynos9820-usi",
\t\t\t\t     "samsung,exynos850-usi";
\t\t\treg = <0x104b00c0 0x20>;
\t\t\tranges;
\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <1>;

\t\t\tclocks = <&cmu_peric0 CLK_GOUT_PERIC0_USI03_USI_PCLK>,
\t\t\t\t <&cmu_peric0 CLK_GOUT_PERIC0_USI03_USI_IPCLK>;
\t\t\tclock-names = "pclk", "ipclk";
\t\t\tsamsung,sysreg = <&sysreg_peric0 0x101c>;
\t\t\t/*
\t\t\t * Without this the block keeps its automatic clock stop, and
\t\t\t * a master that has no clock cannot drive the line it is
\t\t\t * supposed to clock.  Measured on the phone: with the property
\t\t\t * the bus raises interrupts and the controller reports the
\t\t\t * result of a transfer; without it the block is silent.
\t\t\t */
\t\t\tsamsung,clkreq-on;
\t\t\tstatus = "disabled";

\t\t\thsi2c10: i2c@104b0000 {
\t\t\t\tcompatible = "samsung,exynos9820-hsi2c",
\t\t\t\t\t     "samsung,exynosautov9-hsi2c";
\t\t\t\treg = <0x104b0000 0xc0>;
\t\t\t\tinterrupts = <GIC_SPI 388 IRQ_TYPE_LEVEL_HIGH>;
\t\t\t\t#address-cells = <1>;
\t\t\t\t#size-cells = <0>;

\t\t\t\tclocks = <&cmu_peric0 CLK_GOUT_PERIC0_USI03_USI_IPCLK>,
\t\t\t\t\t <&cmu_peric0 CLK_GOUT_PERIC0_USI03_USI_PCLK>;
\t\t\t\tclock-names = "hsi2c", "hsi2c_pclk";
\t\t\t\tpinctrl-0 = <&hsi2c10_bus>;
\t\t\t\tpinctrl-names = "default";
\t\t\t\tstatus = "disabled";
\t\t\t};
\t\t};
'''),
    (1, 0x10830000, '''\t\tpinctrl_peric1: pinctrl@10830000 {
\t\t\tcompatible = "samsung,exynos9820-pinctrl";
\t\t\treg = <0x10830000 0x1000>;
\t\t\tinterrupts = <GIC_SPI 407 IRQ_TYPE_LEVEL_HIGH>;
\t\t};
'''),
    (7, 0x10a00000, '''\t\tcmu_fsys0a: clock-controller@10a00000 {
\t\t\tcompatible = "samsung,exynos9820-cmu-fsys0a";
\t\t\treg = <0x10a00000 0x8000>;
\t\t\t#clock-cells = <1>;

\t\t\tclocks = <&oscclk>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_FSYS0A_BUS>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_FSYS0A_USB31DRD>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_FSYS0A_USBDP_DEBUG>;
\t\t\tclock-names = "oscclk", "bus", "usb31drd", "usbdp_debug";
\t\t};
'''),
    (7, 0x10b00000, '''\t\t/*
\t\t * Only the USB 2.0 window of this PHY is described.  The vendor
\t\t * gives the block three windows and calls it a combined PHY: the
\t\t * other two carry the SuperSpeed lanes and the DisplayPort side,
\t\t * and driving them needs calibration tables that are in none of
\t\t * the sources this series is built from.  A port that enumerates
\t\t * at high speed is worth more than a window nobody writes.
\t\t */
\t\tusbdrd_phy: phy@10b00000 {
\t\t\tcompatible = "samsung,exynos9820-usbdrd-phy";
\t\t\treg = <0x10b00000 0x200>;
\t\t\t#phy-cells = <1>;

\t\t\tclocks = <&cmu_fsys0a CLK_GOUT_FSYS0A_USB31DRD_ACLK_PHYCTRL>,
\t\t\t\t <&oscclk>;
\t\t\tclock-names = "phy", "ref";

\t\t\tsamsung,pmu-syscon = <&pmu_system_controller>;
\t\t\tstatus = "disabled";
\t\t};
'''),
    (7, 0x10c00000, '''\t\tusbdrd: usb@10c00000 {
\t\t\tcompatible = "samsung,exynos9820-dwusb3",
\t\t\t\t     "samsung,exynos850-dwusb3";
\t\t\tranges = <0x0 0x10c00000 0x10000>;
\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <1>;

\t\t\tclocks = <&cmu_fsys0a CLK_GOUT_FSYS0A_USB31DRD_BUS_CLK_EARLY>,
\t\t\t\t <&cmu_fsys0a CLK_GOUT_FSYS0A_USB31DRD_I_USB31DRD_REF_CLK_40>;
\t\t\tclock-names = "bus_early", "ref";
\t\t\tstatus = "disabled";

\t\t\tusbdrd_dwc3: usb@0 {
\t\t\t\tcompatible = "snps,dwc3";
\t\t\t\treg = <0x0 0x10000>;
\t\t\t\tinterrupts = <GIC_SPI 241 IRQ_TYPE_LEVEL_HIGH>;
\t\t\t\tphys = <&usbdrd_phy 0>;
\t\t\t\tphy-names = "usb2-phy";
\t\t\t\t/*
\t\t\t\t * A suspended PHY stops driving the line, and this
\t\t\t\t * board has nothing to wake it up: the port runs as
\t\t\t\t * a peripheral with no Type-C driver, so nothing
\t\t\t\t * tells the controller that a cable is attached.
\t\t\t\t * Measured on a Galaxy S10+: after a reboot, with
\t\t\t\t * the cable never touched, the controller sits in
\t\t\t\t * "not attached" and the host sees no device at all,
\t\t\t\t * while unplugging and replugging brings it back.
\t\t\t\t * The Exynos-derived port in tree, Google gs101,
\t\t\t\t * disables the suspend for the same reason.
\t\t\t\t */
\t\t\t\tsnps,has-lpm-erratum;
\t\t\t\tsnps,dis_u2_susphy_quirk;
\t\t\t};
\t\t};
'''),
    (1, 0x13030000, '''\t\tpinctrl_fsys0: pinctrl@13030000 {
\t\t\tcompatible = "samsung,exynos9820-pinctrl";
\t\t\treg = <0x13030000 0x1000>;
\t\t\tinterrupts = <GIC_SPI 240 IRQ_TYPE_LEVEL_HIGH>;
\t\t};
'''),
    (5, 0x13c00000, '''\t\tcmu_fsys1: clock-controller@13c00000 {
\t\t\tcompatible = "samsung,exynos9820-cmu-fsys1";
\t\t\treg = <0x13c00000 0x8000>;
\t\t\t#clock-cells = <1>;

\t\t\tclocks = <&oscclk>,
\t\t\t\t <&cmu_top CLK_GOUT_CMU_FSYS1_BUS>,
\t\t\t\t <&cmu_top CLK_GOUT_CMU_FSYS1_MMC_CARD>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_FSYS1_PCIE>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_FSYS1_UFS_CARD>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_FSYS1_UFS_EMBD>;
\t\t\tclock-names = "oscclk", "bus", "mmc_card", "pcie",
\t\t\t\t      "ufs_card", "ufs_embd";
\t\t};
'''),
    (25, 0x13d00000, '''\t\tmmc_2: mmc@13d00000 {
\t\t\tcompatible = "samsung,exynos7870-dw-mshc-smu";
\t\t\treg = <0x13d00000 0x2000>;
\t\t\tinterrupts = <GIC_SPI 250 IRQ_TYPE_LEVEL_HIGH>;
\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <0>;

\t\t\tclocks = <&cmu_fsys1 CLK_GOUT_FSYS1_MMC_CARD_I_ACLK>,
\t\t\t\t <&cmu_fsys1 CLK_GOUT_FSYS1_MMC_CARD_SDCLKIN>;
\t\t\tclock-names = "biu", "ciu";
\t\t\t/*
\t\t\t * The card clock mux comes up on the MMC PLL, which the boot
\t\t\t * loader leaves in bypass at 26 MHz.  The vendor feeds this host
\t\t\t * 800 MHz instead, from CMU_TOP through the user mux; the gate in
\t\t\t * front of the host does not pass rate requests up, so the rate
\t\t\t * set here stays and the host divides the card clock itself.
\t\t\t */
\t\t\tassigned-clocks = <&cmu_fsys1 CLK_MOUT_FSYS1_MMC_CARD>,
\t\t\t\t\t  <&cmu_fsys1 CLK_DOUT_FSYS1_MMC_CARD>;
\t\t\tassigned-clock-parents = <&cmu_fsys1 CLK_MOUT_FSYS1_MMC_CARD_USER>,
\t\t\t\t\t\t <0>;
\t\t\tassigned-clock-rates = <0>, <800000000>;
\t\t\tclock-frequency = <800000000>;
\t\t\tfifo-depth = <64>;

\t\t\tstatus = "disabled";
\t\t};
'''),
    (6, 0x13d60000, '''\t\tufs_0: ufs@13d60000 {
\t\t\tcompatible = "samsung,exynos9820-ufs";
\t\t\treg = <0x13d60000 0x200>,
\t\t\t      <0x13d61100 0x200>,
\t\t\t      <0x13d50000 0x8000>,
\t\t\t      <0x13d70000 0x100>;
\t\t\treg-names = "hci", "vs_hci", "unipro", "ufsp";
\t\t\tinterrupts = <GIC_SPI 249 IRQ_TYPE_LEVEL_HIGH>;

\t\t\tclocks = <&cmu_fsys1 CLK_GOUT_FSYS1_UFS_EMBD_I_ACLK>,
\t\t\t\t <&cmu_fsys1 CLK_GOUT_FSYS1_UFS_EMBD_I_CLK_UNIPRO>;
\t\t\tclock-names = "core_clk", "sclk_unipro_main";
\t\t\t/*
\t\t\t * Without this the core never puts the two clocks above on the
\t\t\t * list the host driver reads them from: the parser that fills it
\t\t\t * returns early when no table is given, the driver then finds an
\t\t\t * empty list and reports success without having read a single
\t\t\t * rate, and the link is asked to start on a period of zero.  A
\t\t\t * pair of zeroes means no scaling, which is what every other SoC
\t\t\t * of this family writes here.
\t\t\t */
\t\t\tfreq-table-hz = <0 0>, <0 0>;

\t\t\tpinctrl-names = "default";
\t\t\tpinctrl-0 = <&ufs_rst_n &ufs_refclk_out>;

\t\t\tphys = <&ufs_0_phy>;
\t\t\tphy-names = "ufs-phy";

\t\t\t/*
\t\t\t * The bits that would put this controller on the coherent
\t\t\t * path.  Without a dma-coherent property beside them the
\t\t\t * driver clears them, which is what the descriptors of this
\t\t\t * driver are kept for.
\t\t\t */
\t\t\tsamsung,sysreg = <&sysreg_fsys1 0x700>;

\t\t\tstatus = "disabled";
\t\t};
'''),
    (6, 0x13d64000, '''\t\tufs_0_phy: phy@13d64000 {
\t\t\tcompatible = "samsung,exynos9820-ufs-phy";
\t\t\t/*
\t\t\t * The vendor gives this window 0x800, which covers the first
\t\t\t * lane only, while its own calibration reaches past that on
\t\t\t * the second one.  A page is asked for here instead.
\t\t\t */
\t\t\treg = <0x13d64000 0x1000>;
\t\t\treg-names = "phy-pma";
\t\t\t#phy-cells = <0>;

\t\t\t/*
\t\t\t * UNVERIFIED: the reference this PHY locks to is taken to be
\t\t\t * the board oscillator, which is what the pin beside it
\t\t\t * carries out to the device.  The vendor describes no phy of
\t\t\t * its own, so there is nothing to read this off; confirm it
\t\t\t * by reading the lock status of the PHY with that oscillator
\t\t\t * gated away.
\t\t\t */
\t\t\tclocks = <&oscclk>;
\t\t\tclock-names = "ref_clk";

\t\t\tsamsung,pmu-syscon = <&pmu_system_controller 0x724>;
\t\t};
'''),
    (5, 0x13c10000, '''\t\tsysreg_fsys1: syscon@13c10000 {
\t\t\tcompatible = "samsung,exynos9820-fsys1-sysreg",
\t\t\t\t     "syscon";
\t\t\treg = <0x13c10000 0x2000>;
\t\t\tclocks = <&cmu_fsys1 CLK_GOUT_FSYS1_SYSREG_FSYS1_PCLK>;
\t\t};
'''),
    (1, 0x13c40000, '''\t\tpinctrl_fsys1: pinctrl@13c40000 {
\t\t\tcompatible = "samsung,exynos9820-pinctrl";
\t\t\treg = <0x13c40000 0x1000>;
\t\t\tinterrupts = <GIC_SPI 251 IRQ_TYPE_LEVEL_HIGH>;
\t\t};
'''),
    (1, 0x15580000, '''\t\t/*
\t\t * The VTS and AUD pin controllers sit inside power domains that can
\t\t * be off, so they carry no interrupt and the driver leaves their
\t\t * registers alone until something claims a pin.
\t\t */
\t\tpinctrl_vts: pinctrl@15580000 {
\t\t\tcompatible = "samsung,exynos9820-pinctrl";
\t\t\treg = <0x15580000 0x1000>;
\t\t};
'''),
    (1, 0x15800000, '''\t\tcmu_apm: clock-controller@15800000 {
\t\t\tcompatible = "samsung,exynos9820-cmu-apm";
\t\t\treg = <0x15800000 0x8000>;
\t\t\t#clock-cells = <1>;

\t\t\tclocks = <&oscclk>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_APM_BUS>;
\t\t\tclock-names = "oscclk", "bus";
\t\t};
'''),
    (1, 0x15850000, '''\t\t/*
\t\t * The banks of this controller and of CMGP keep their pads alive
\t\t * across suspend, so they are the two that can wake the system.  The
\t\t * interrupt lists live with the banks, in the pin controller file.
\t\t */
\t\tpinctrl_alive: pinctrl@15850000 {
\t\t\tcompatible = "samsung,exynos9820-pinctrl";
\t\t\treg = <0x15850000 0x1000>;

\t\t\twakeup-interrupt-controller {
\t\t\t\tcompatible = "samsung,exynos9820-wakeup-eint",
\t\t\t\t\t     "samsung,exynos850-wakeup-eint",
\t\t\t\t\t     "samsung,exynos7-wakeup-eint";
\t\t\t};
\t\t};
'''),
    (1, 0x15860000, '''\t\tpmu_system_controller: system-controller@15860000 {
\t\t\tcompatible = "samsung,exynos9820-pmu",
\t\t\t\t     "samsung,exynos7-pmu",
\t\t\t\t     "syscon";
\t\t\treg = <0x15860000 0x10000>;
%(wskaznik_intr_gen)s
\t\t\tpoweroff: syscon-poweroff {
\t\t\t\tcompatible = "syscon-poweroff";
\t\t\t\tregmap = <&pmu_system_controller>;
\t\t\t\toffset = <0x030c>; /* PS_HOLD_CONTROL */
\t\t\t\tmask = <0x100>;
\t\t\t\tvalue = <0x0>;
\t\t\t};

%(tryby_restartu)s\t\t\treboot: syscon-reboot {
\t\t\t\tcompatible = "syscon-reboot";
\t\t\t\tregmap = <&pmu_system_controller>;
\t\t\t\toffset = <0x3a00>; /* SWRESET */
\t\t\t\tmask = <0x2>; /* SWRESET_TRIGGER */
\t\t\t\tvalue = <0x2>;
\t\t\t};
\t\t};
'''),
    (2, 0x15861e00, '''\t\t/*
\t\t * UNVERIFIED: The mask is the vendor's own
\t\t * (flexpmu_cal_local_exynos9820.h:287-288 writes 0x15860000 +
\t\t * 0x1e00 with (0x1 << 0) and waits on + 0x1e04 with the same
\t\t * mask), but exynos_pd_power writes the whole word, so the other
\t\t * 31 bits are zeroed and no source says what they hold.  The
\t\t * vendor node also carries need_smc = <0x191b0204>, which this
\t\t * binding has no way to express.
\t\t */
\t\tpd_dpu: power-domain@15861e00 {
\t\t\tcompatible = "samsung,exynos9820-pd";
\t\t\treg = <0x15861e00 0x20>;
\t\t\t#power-domain-cells = <0>;
\t\t\tlabel = "DPU";
\t\t};
'''),
    (4, 0x15c00000, '''\t\tcmu_cmgp: clock-controller@15c00000 {
\t\t\tcompatible = "samsung,exynos9820-cmu-cmgp";
\t\t\treg = <0x15c00000 0x8000>;
\t\t\t#clock-cells = <1>;

\t\t\tclocks = <&oscclk>,
\t\t\t\t <&cmu_apm CLK_DOUT_CMU_CMGP_BUS>;
\t\t\tclock-names = "oscclk", "bus";
\t\t};
'''),
    (1, 0x15c30000, '''\t\tpinctrl_cmgp: pinctrl@15c30000 {
\t\t\tcompatible = "samsung,exynos9820-pinctrl";
\t\t\treg = <0x15c30000 0x1000>;

\t\t\twakeup-interrupt-controller {
\t\t\t\tcompatible = "samsung,exynos9820-wakeup-eint",
\t\t\t\t\t     "samsung,exynos850-wakeup-eint",
\t\t\t\t\t     "samsung,exynos7-wakeup-eint";
\t\t\t};
\t\t};
'''),
    (4, 0x15d500c0, '''\t\t/*
\t\t * This bus stays awake with the CMGP domain, which is why the
\t\t * display PMIC hangs off it rather than off a PERIC bus: the panel
\t\t * rails have to be reachable while the rest sleeps.
\t\t *
\t\t * The controller below is the dedicated I2C half of a CMGP
\t\t * channel, not the USI half, but it is wrapped the same way and
\t\t * has its own mode register, named usi_02_cmgp_i2c by the vendor.
\t\t * Mainline describes every such controller like this, dedicated or
\t\t * not; see the three hsi2c blocks of exynos850.  Measured on the
\t\t * phone without this node: the block stays in reset, the driver's
\t\t * writes never land, and the bus raises no interrupt at all.
\t\t */
\t\tusi_cmgp2: usi@15d500c0 {
\t\t\tcompatible = "samsung,exynos9820-usi",
\t\t\t\t     "samsung,exynos850-usi";
\t\t\treg = <0x15d500c0 0x20>;
\t\t\tranges;
\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <1>;

\t\t\tclocks = <&cmu_cmgp CLK_GOUT_CMGP_I2C_CMGP2_PCLK>,
\t\t\t\t <&cmu_cmgp CLK_GOUT_CMGP_I2C_CMGP2_IPCLK>;
\t\t\tclock-names = "pclk", "ipclk";
\t\t\tsamsung,sysreg = <&sysreg_cmgp 0x24>;
\t\t\tsamsung,clkreq-on;
\t\t\tstatus = "disabled";

\t\t\thsi2c2: i2c@15d50000 {
\t\t\t\tcompatible = "samsung,exynos9820-hsi2c",
\t\t\t\t\t     "samsung,exynosautov9-hsi2c";
\t\t\t\treg = <0x15d50000 0xc0>;
\t\t\t\tinterrupts = <GIC_SPI 81 IRQ_TYPE_LEVEL_HIGH>;
\t\t\t\t#address-cells = <1>;
\t\t\t\t#size-cells = <0>;

\t\t\t\tclocks = <&cmu_cmgp CLK_GOUT_CMGP_I2C_CMGP2_IPCLK>,
\t\t\t\t\t <&cmu_cmgp CLK_GOUT_CMGP_I2C_CMGP2_PCLK>;
\t\t\t\tclock-names = "hsi2c", "hsi2c_pclk";
\t\t\t\tpinctrl-0 = <&hsi2c2_bus>;
\t\t\t\tpinctrl-names = "default";
\t\t\t\tstatus = "disabled";
\t\t\t};
\t\t};
'''),
    (4, 0x15c22000, '''\t\t/*
\t\t * Holds the mode registers the USI blocks of this domain use.
\t\t * The address is read, not worked out: the vendor tree names
\t\t * these registers one by one, usi_00_cmgp at 0x15c22000 through
\t\t * usi_03_cmgp_i2c at 0x15c22034, each as its own node.  That
\t\t * matters here, because on this SoC a write to a wrong system
\t\t * register is how an external abort is earned.
\t\t *
\t\t * The window starts at the first of those registers rather than
\t\t * at the start of the block, because where the block starts is
\t\t * exactly the part no source states.
\t\t */
\t\tsysreg_cmgp: syscon@15c22000 {
\t\t\tcompatible = "samsung,exynos9820-cmgp-sysreg",
\t\t\t\t     "syscon";
\t\t\treg = <0x15c22000 0x1000>;
\t\t\tclocks = <&cmu_cmgp CLK_GOUT_CMGP_SYSREG_CMGP_PCLK>;
\t\t};
'''),
    (8, 0x15d600c0, '''\t\t/*
\t\t * The bus the main PMIC's companion sits on.  Like the display
\t\t * PMIC's bus above it, it stays awake with the CMGP domain, which
\t\t * is what a fuel gauge needs: the charge it counts has to go on
\t\t * being counted while the rest of the chip sleeps.
\t\t *
\t\t * This block is a USI, not a dedicated I2C like the one before
\t\t * it, so a register outside it picks whether it speaks I2C, SPI
\t\t * or UART, and the driver behind that register is also the one
\t\t * that releases the block from reset.  Without the node below
\t\t * nothing does either, and it shows: measured on the phone, this
\t\t * bus raised not one interrupt, while the touchscreen bus, which
\t\t * does have such a node, raised two.
\t\t */
\t\tusi_cmgp3: usi@15d600c0 {
\t\t\tcompatible = "samsung,exynos9820-usi",
\t\t\t\t     "samsung,exynos850-usi";
\t\t\treg = <0x15d600c0 0x20>;
\t\t\tranges;
\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <1>;

\t\t\tclocks = <&cmu_cmgp CLK_GOUT_CMGP_USI_CMGP3_PCLK>,
\t\t\t\t <&cmu_cmgp CLK_GOUT_CMGP_USI_CMGP3_IPCLK>;
\t\t\tclock-names = "pclk", "ipclk";
\t\t\tsamsung,sysreg = <&sysreg_cmgp 0x30>;
\t\t\tsamsung,clkreq-on;
\t\t\tstatus = "disabled";

\t\t\thsi2c45: i2c@15d60000 {
\t\t\t\tcompatible = "samsung,exynos9820-hsi2c",
\t\t\t\t\t     "samsung,exynosautov9-hsi2c";
\t\t\t\treg = <0x15d60000 0xc0>;
\t\t\t\tinterrupts = <GIC_SPI 82 IRQ_TYPE_LEVEL_HIGH>;
\t\t\t\t#address-cells = <1>;
\t\t\t\t#size-cells = <0>;

\t\t\t\tclocks = <&cmu_cmgp CLK_GOUT_CMGP_USI_CMGP3_IPCLK>,
\t\t\t\t\t <&cmu_cmgp CLK_GOUT_CMGP_USI_CMGP3_PCLK>;
\t\t\t\tclock-names = "hsi2c", "hsi2c_pclk";
\t\t\t\tpinctrl-0 = <&hsi2c45_bus>;
\t\t\t\tpinctrl-names = "default";
\t\t\t\tstatus = "disabled";
\t\t\t};
\t\t};
'''),
    (16, 0x18500000, '''\t\t/*
\t\t * A Mali-G76 MP12: GPU_ID reads 0x72110000 and SHADER_PRESENT
%(gpu_komentarz)s\t\t * the bootloader leaves it on, and the vendor saves and restores
\t\t * the TrustZone setup of the block with an SMC around every power
\t\t * cycle, which the power domain driver does not do.
\t\t */
\t\tgpu: gpu@18500000 {
\t\t\tcompatible = "samsung,exynos9820-mali", "arm,mali-bifrost";
\t\t\treg = <0x18500000 0x5000>;
\t\t\tinterrupts = <GIC_SPI 288 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 287 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 289 IRQ_TYPE_LEVEL_HIGH>;
\t\t\tinterrupt-names = "job", "mmu", "gpu";
\t\t\tclocks = <&acpm_ipc EXYNOS9820_CLK_ACPM_DVFS_G3D>;
%(gpu_dvfs)s\t\t};
'''),
    (21, 0x18c00000, '''\t\t/*
\t\t * No power-domains yet: the boot loader leaves the AUD domain on
\t\t * and nothing in this series holds a clock of the block, so runtime
\t\t * PM would switch the domain off right after boot.
\t\t */
\t\tcmu_aud: clock-controller@18c00000 {
\t\t\tcompatible = "samsung,exynos9820-cmu-aud";
\t\t\treg = <0x18c00000 0x8000>;
\t\t\t#clock-cells = <1>;

\t\t\tclocks = <&oscclk>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_AUD_CPU>;
\t\t\tclock-names = "oscclk", "cpu";
\t\t};
'''),
    (22, 0x18c50000, '''\t\t/*
\t\t * Driven from the AP with the DSP core of the block left off; the
\t\t * DMA interrupts go to the controller inside the block, so none is
\t\t * described.
\t\t */
\t\tabox: audio-controller@18c50000 {
\t\t\tcompatible = "samsung,exynos9820-abox";
\t\t\treg = <0x18c50000 0x10000>;
\t\t\tclocks = <&cmu_aud CLK_GOUT_AUD_ABOX_ACLK>,
\t\t\t\t <&cmu_aud CLK_GOUT_AUD_ABOX_BCLK_UAIF1>,
\t\t\t\t <&cmu_aud CLK_DOUT_AUD_UAIF1>,
\t\t\t\t <&cmu_aud CLK_GOUT_AUD_ABOX_BCLK_UAIF0>,
\t\t\t\t <&cmu_aud CLK_DOUT_AUD_UAIF0>;
\t\t\tclock-names = "aclk", "bclk_uaif1", "div_uaif1",
\t\t\t\t      "bclk_uaif0", "div_uaif0";
\t\t\tpinctrl-0 = <&aud_i2s1_bus>, <&aud_i2s0_bus>;
\t\t\tpinctrl-names = "default";
\t\t\t#sound-dai-cells = <1>;

\t\t\tstatus = "disabled";
\t\t};
'''),
    (1, 0x18c60000, '''\t\tpinctrl_aud: pinctrl@18c60000 {
\t\t\tcompatible = "samsung,exynos9820-pinctrl";
\t\t\treg = <0x18c60000 0x1000>;
\t\t};
'''),
    (3, 0x19000000, '''\t\tcmu_dpu: clock-controller@19000000 {
\t\t\tcompatible = "samsung,exynos9820-cmu-dpu";
\t\t\treg = <0x19000000 0x8000>;
\t\t\t#clock-cells = <1>;

\t\t\tclocks = <&oscclk>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_DPU_BUS>;
\t\t\tclock-names = "oscclk", "bus";
\t\t\tpower-domains = <&pd_dpu>;
\t\t};
'''),
    (4, 0x19030000, '''\t\t/*
\t\t * The display controller and one of its window pipelines.  This
\t\t * panel runs in command mode, so nothing scans out on its own: the
\t\t * panel raises the tearing effect line and the controller sends one
\t\t * frame in answer.
\t\t */
\t\tdecon0: display-controller@19030000 {
\t\t\tcompatible = "samsung,exynos9820-decon";
\t\t\treg = <0x19030000 0x10000>, <0x19070000 0x10000>;
\t\t\treg-names = "decon", "dma";

\t\t\tinterrupts = <GIC_SPI 183 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 184 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t     <GIC_SPI 189 IRQ_TYPE_LEVEL_HIGH>;
\t\t\tinterrupt-names = "frame-start", "frame-done", "extra";

\t\t\t/* the panel drives the frame trigger over this line */
\t\t\tpinctrl-names = "default";
\t\t\tpinctrl-0 = <&decon_te_pins>;

\t\t\tclocks = <&cmu_dpu CLK_GOUT_DPU_DPU_ACLK_DECON>,
\t\t\t\t <&cmu_dpu CLK_GOUT_DPU_DPU_ACLK_DMA>,
\t\t\t\t <&cmu_dpu CLK_GOUT_DPU_DPU_ACLK_DPP>;
\t\t\tclock-names = "aclk", "aclk-dma", "aclk-dpp";

\t\t\tpower-domains = <&pd_dpu>;
\t\t\tiommus = <&sysmmu_dpud0>, <&sysmmu_dpud1>,
\t\t\t\t <&sysmmu_dpud2>;
\t\t\tstatus = "disabled";

\t\t\tport {
\t\t\t\tdecon0_out: endpoint {
\t\t\t\t\tremote-endpoint = <&dsim0_in>;
\t\t\t\t};
\t\t\t};
\t\t};
'''),
    (4, 0x19080000, '''\t\tdsim0: dsi@19080000 {
\t\t\tcompatible = "samsung,exynos9820-mipi-dsi";
\t\t\treg = <0x19080000 0x300>;

\t\t\tphys = <&dsim0_dphy>;
\t\t\tphy-names = "dsim";

\t\t\tinterrupts = <GIC_SPI 190 IRQ_TYPE_LEVEL_HIGH>;

\t\t\tclocks = <&cmu_dpu CLK_GOUT_DPU_AD_APB_MIPI_DSIM0_PCLKS>;
\t\t\tclock-names = "bus";

\t\t\t/*
\t\t\t * The link runs at a rate the panel and the D-PHY timing table
\t\t\t * agree on.  Without this the host would derive it from the
\t\t\t * pixel clock and the uncompressed 24 bpp, which ignores DSC
\t\t\t * and asks the PHY for a rate it has no timings for.
\t\t\t */
\t\t\tsamsung,burst-clock-frequency = <898000000>;

\t\t\t/*
\t\t\t * UNVERIFIED: the sources give both 18 and 20 MHz for
\t\t\t * this link.  The prescaler rounds whatever is asked for down
\t\t\t * to a divider of the word clock, so the number that actually
\t\t\t * reaches the lanes has to be measured.
\t\t\t */
\t\t\tsamsung,esc-clock-frequency = <20000000>;

\t\t\tpower-domains = <&pd_dpu>;
\t\t\tstatus = "disabled";

\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <0>;

\t\t\tports {
\t\t\t\t#address-cells = <1>;
\t\t\t\t#size-cells = <0>;

\t\t\t\tport@0 {
\t\t\t\t\treg = <0>;

\t\t\t\t\tdsim0_in: endpoint {
\t\t\t\t\t\tremote-endpoint = <&decon0_out>;
\t\t\t\t\t};
\t\t\t\t};

\t\t\t\tport@1 {
\t\t\t\t\treg = <1>;

\t\t\t\t\tdsim0_out: endpoint {
\t\t\t\t\t\tremote-endpoint = <&panel_in>;
\t\t\t\t\t};
\t\t\t\t};
\t\t\t};
\t\t};
'''),
    (3, 0x190a0000, '''\t\t/*
\t\t * One system MMU per display data path.  All three have to be
\t\t * listed by the controller, because a frame is fetched through
\t\t * whichever of them the window happens to use.
\t\t */
\t\tsysmmu_dpud0: iommu@190a0000 {
\t\t\tcompatible = "samsung,exynos-sysmmu";
\t\t\treg = <0x190a0000 0x9000>;
\t\t\tinterrupts = <GIC_SPI 212 IRQ_TYPE_LEVEL_HIGH>;
\t\t\tclocks = <&cmu_dpu CLK_GOUT_DPU_SYSMMU_DPUD0_CLK>;
\t\t\tclock-names = "sysmmu";
\t\t\tpower-domains = <&pd_dpu>;
\t\t\t#iommu-cells = <0>;
\t\t};
'''),
    (3, 0x190b0000, '''\t\tsysmmu_dpud1: iommu@190b0000 {
\t\t\tcompatible = "samsung,exynos-sysmmu";
\t\t\treg = <0x190b0000 0x9000>;
\t\t\tinterrupts = <GIC_SPI 214 IRQ_TYPE_LEVEL_HIGH>;
\t\t\tclocks = <&cmu_dpu CLK_GOUT_DPU_SYSMMU_DPUD1_CLK>;
\t\t\tclock-names = "sysmmu";
\t\t\tpower-domains = <&pd_dpu>;
\t\t\t#iommu-cells = <0>;
\t\t};
'''),
    (3, 0x190c0000, '''\t\tsysmmu_dpud2: iommu@190c0000 {
\t\t\tcompatible = "samsung,exynos-sysmmu";
\t\t\treg = <0x190c0000 0x9000>;
\t\t\tinterrupts = <GIC_SPI 216 IRQ_TYPE_LEVEL_HIGH>;
\t\t\tclocks = <&cmu_dpu CLK_GOUT_DPU_SYSMMU_DPUD2_CLK>;
\t\t\tclock-names = "sysmmu";
\t\t\tpower-domains = <&pd_dpu>;
\t\t\t#iommu-cells = <0>;
\t\t};
'''),
    (4, 0x19011000, '''\t\t/*
\t\t * The window of the display unit system registers that carries the
\t\t * reset of the D-PHY and the choice of what drives it.  This is the
\t\t * window the vendor maps, sixteen bytes at this address rather than
\t\t * the whole block, so the offsets are the ones its sources use.
\t\t */
\t\tsysreg_dpu: syscon@19011000 {
\t\t\tcompatible = "samsung,exynos9820-dpu-sysreg",
\t\t\t\t     "syscon";
\t\t\treg = <0x19011000 0x10>;
\t\t};
'''),
    (4, 0x19160000, '''\t\t/*
\t\t * The bias generator of the display D-PHY.  The vendor sources
\t\t * describe it as a block of its own rather than part of a link
\t\t * (dphy_m4s4_dsim0 next to dphy_m4s0_dsim0), so the link nodes
\t\t * point at it instead of each mapping it themselves.
\t\t */
\t\tdphy_top: syscon@19160000 {
\t\t\tcompatible = "samsung,exynos9820-dphy-top", "syscon";
\t\t\treg = <0x19160000 0x100>;
\t\t};
'''),
    (4, 0x19161000, '''\t\tdsim0_dphy: phy@19161000 {
\t\t\tcompatible = "samsung,exynos9820-mipi-dphy";
\t\t\treg = <0x19161000 0x800>;
\t\t\tsamsung,dphy-top-syscon = <&dphy_top>;
\t\t\tsamsung,dpu-sysreg = <&sysreg_dpu>;

\t\t\tclocks = <&cmu_dpu CLK_GOUT_DPU_AD_APB_MIPI_DSIM0_PCLKS>;
\t\t\tclock-names = "apb";

\t\t\tpower-domains = <&pd_dpu>;
\t\t\t#phy-cells = <0>;
\t\t};
'''),
    (24, 0x10510000, '''\t\t/*
\t\t * The PWM timer block of PERIC0, vendor pwm@10510000.  The vendor
\t\t * binds it as the S3C6400 variant; the Exynos4210 fallback is the
\t\t * same 32 bit timer without the external TCLK mux, and nothing on
\t\t * this phone feeds a TCLK.  The vendor names a second clock,
\t\t * pwm_sclk, that the mainline driver has no use for: it counts from
\t\t * the bus clock through its own prescaler.  The vendor lists all
\t\t * five channels as outputs; channel 1 drives the vibration motor.
\t\t */
\t\tpwm: pwm@10510000 {
\t\t\tcompatible = "samsung,exynos9820-pwm",
\t\t\t\t     "samsung,exynos4210-pwm";
\t\t\treg = <0x10510000 0x1000>;
\t\t\tclocks = <&cmu_peric0 CLK_GOUT_PERIC0_PWM_I_PCLK_S0>;
\t\t\tclock-names = "timers";
\t\t\tsamsung,pwm-outputs = <0>, <1>, <2>, <3>, <4>;
\t\t\t#pwm-cells = <3>;
\t\t\tstatus = "disabled";
\t\t};
'''),
    (10, 0x10800000, '''\t\tcmu_peric1: clock-controller@10800000 {
\t\t\tcompatible = "samsung,exynos9820-cmu-peric1";
\t\t\treg = <0x10800000 0x8000>;
\t\t\t#clock-cells = <1>;

\t\t\tclocks = <&oscclk>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_PERIC1_BUS>,
\t\t\t\t <&cmu_top CLK_DOUT_CMU_PERIC1_IP>;
\t\t\tclock-names = "oscclk", "bus", "ip";
\t\t};
'''),
    (10, 0x10820000, '''\t\t/* Holds the mode register the USI blocks of this domain use. */
\t\tsysreg_peric1: syscon@10820000 {
\t\t\tcompatible = "samsung,exynos9820-peric1-sysreg",
\t\t\t\t     "syscon";
\t\t\treg = <0x10820000 0x2000>;
\t\t\tclocks = <&cmu_peric1 CLK_GOUT_PERIC1_SYSREG_PERIC1_PCLK>;
\t\t};
'''),
    (10, 0x108400c0, '''\t\t/*
\t\t * The Bluetooth controller hangs off a serial port, and that port is
\t\t * one mode of a USI block, the same kind of block the I2C buses above
\t\t * use.  The mode register sits in the PERIC1 system register at
\t\t * offset 0x1000, the window the vendor tree calls usi_uart_bt.
\t\t */
\t\tusi_uart_bt: usi@108400c0 {
\t\t\tcompatible = "samsung,exynos9820-usi",
\t\t\t\t     "samsung,exynos850-usi";
\t\t\treg = <0x108400c0 0x20>;
\t\t\tranges;
\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <1>;

\t\t\tclocks = <&cmu_peric1 CLK_GOUT_PERIC1_UART_BT_PCLK>,
\t\t\t\t <&cmu_peric1 CLK_GOUT_PERIC1_UART_BT_IPCLK>;
\t\t\tclock-names = "pclk", "ipclk";
\t\t\tsamsung,sysreg = <&sysreg_peric1 0x1000>;
\t\t\t/*
\t\t\t * The same reason as on the I2C blocks above: without this the
\t\t\t * block keeps its automatic clock stop.  Carried over from
\t\t\t * those buses, where it was measured on the phone.
\t\t\t */
\t\t\tsamsung,clkreq-on;
\t\t\tstatus = "disabled";

\t\t\tserial1: serial@10840000 {
\t\t\t\tcompatible = "samsung,exynos9820-uart",
\t\t\t\t\t     "samsung,exynos8895-uart";
\t\t\t\t/*
\t\t\t\t * The window stops where the USI one starts: were
\t\t\t\t * it any longer, both drivers would request the
\t\t\t\t * same memory and the second one would be turned
\t\t\t\t * away.
\t\t\t\t */
\t\t\t\treg = <0x10840000 0xc0>;
\t\t\t\tinterrupts = <GIC_SPI 408 IRQ_TYPE_LEVEL_HIGH>;
\t\t\t\tclocks = <&cmu_peric1 CLK_GOUT_PERIC1_UART_BT_PCLK>,
\t\t\t\t\t <&cmu_peric1 CLK_GOUT_PERIC1_UART_BT_IPCLK>;
\t\t\t\tclock-names = "uart", "clk_uart_baud0";
\t\t\t\tsamsung,uart-fifosize = <256>;
\t\t\t\tpinctrl-0 = <&uart1_bus>;
\t\t\t\tpinctrl-names = "default";
\t\t\t\tstatus = "disabled";
\t\t\t};
\t\t};
'''),
    (23, 0x109700c0, '''\t\t/*
\t\t * The full USI block the vendor tree calls usi_16, the one without
\t\t * an I2C-only partner: the next block up, 0x10990000, is usi_17 and
\t\t * 0x109a0000 its I2C-only partner.  The mode register sits in the
\t\t * PERIC1 system register at 0x1048.  Its SPI master is the vendor
\t\t * spi_17, one ahead of the USI index as in PERIC0.
\t\t */
\t\tusi16: usi@109700c0 {
\t\t\tcompatible = "samsung,exynos9820-usi",
\t\t\t\t     "samsung,exynos850-usi";
\t\t\treg = <0x109700c0 0x20>;
\t\t\tranges;
\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <1>;

\t\t\tclocks = <&cmu_peric1 CLK_GOUT_PERIC1_USI16_USI_PCLK>,
\t\t\t\t <&cmu_peric1 CLK_GOUT_PERIC1_USI16_USI_IPCLK>;
\t\t\tclock-names = "pclk", "ipclk";
\t\t\tsamsung,sysreg = <&sysreg_peric1 0x1048>;
\t\t\tsamsung,clkreq-on;
\t\t\tstatus = "disabled";

\t\t\tspi_17: spi@10970000 {
\t\t\t\tcompatible = "samsung,exynos9820-spi",
\t\t\t\t\t     "samsung,exynos850-spi";
\t\t\t\treg = <0x10970000 0x30>;
\t\t\t\tinterrupts = <GIC_SPI 426 IRQ_TYPE_LEVEL_HIGH>;
\t\t\t\t#address-cells = <1>;
\t\t\t\t#size-cells = <0>;

\t\t\t\tclocks = <&cmu_peric1 CLK_GOUT_PERIC1_USI16_USI_PCLK>,
\t\t\t\t\t <&cmu_peric1 CLK_GOUT_PERIC1_USI16_USI_IPCLK>;
\t\t\t\tclock-names = "spi", "spi_busclk0";
\t\t\t\tpinctrl-0 = <&spi17_bus>;
\t\t\t\tpinctrl-names = "default";
\t\t\t\tstatus = "disabled";
\t\t\t};
\t\t};
'''),
    (19, 0x109a00c0, '''\t\t/*
\t\t * An I2C-only USI block, the one the vendor tree calls usi_17_i2c.
\t\t * Its mode register sits in the PERIC1 system register at offset
\t\t * 0x1050: the vendor lists the PERIC1 blocks in address order,
\t\t * each full USI followed by its I2C-only partner 0x10000 above it,
\t\t * and the same rule gives the 0x101c of usi3 in PERIC0.
\t\t */
\t\tusi17_i2c: usi@109a00c0 {
\t\t\tcompatible = "samsung,exynos9820-usi",
\t\t\t\t     "samsung,exynos850-usi";
\t\t\treg = <0x109a00c0 0x20>;
\t\t\tranges;
\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <1>;

\t\t\tclocks = <&cmu_peric1 CLK_GOUT_PERIC1_USI17_I2C_PCLK>,
\t\t\t\t <&cmu_peric1 CLK_GOUT_PERIC1_USI17_I2C_IPCLK>;
\t\t\tclock-names = "pclk", "ipclk";
\t\t\tsamsung,sysreg = <&sysreg_peric1 0x1050>;
\t\t\tsamsung,clkreq-on;
\t\t\tstatus = "disabled";

\t\t\thsi2c38: i2c@109a0000 {
\t\t\t\tcompatible = "samsung,exynos9820-hsi2c",
\t\t\t\t\t     "samsung,exynosautov9-hsi2c";
\t\t\t\treg = <0x109a0000 0xc0>;
\t\t\t\tinterrupts = <GIC_SPI 428 IRQ_TYPE_LEVEL_HIGH>;
\t\t\t\t#address-cells = <1>;
\t\t\t\t#size-cells = <0>;

\t\t\t\tclocks = <&cmu_peric1 CLK_GOUT_PERIC1_USI17_I2C_IPCLK>,
\t\t\t\t\t <&cmu_peric1 CLK_GOUT_PERIC1_USI17_I2C_PCLK>;
\t\t\t\tclock-names = "hsi2c", "hsi2c_pclk";
\t\t\t\tpinctrl-0 = <&hsi2c38_bus>;
\t\t\t\tpinctrl-names = "default";
\t\t\t\tstatus = "disabled";
\t\t\t};
\t\t};
'''),
    (11, 0x15870000, '''\t\t/*
\t\t * Where the per-core interrupt block sits.  The firmware does not
\t\t * bring a core up on the PSCI call alone: the host has to lift the
\t\t * block of that core here first, which is what the vendor power
\t\t * sequences do before every core they start.
\t\t */
\t\tpmu_intr_gen: syscon@15870000 {
\t\t\tcompatible = "samsung,exynos9820-pmu-intr-gen",
\t\t\t\t     "syscon";
\t\t\treg = <0x15870000 0x10000>;
\t\t};
'''),
    (12, 0x13ed0000, '''\t\t/*
\t\t * The first of the two PCIe controllers of this SoC, and the only
\t\t * one wired on this board: the combined Wi-Fi and Bluetooth chip
\t\t * answers on it, one lane at Gen1.  The second controller is left
\t\t * out, because nothing is attached to it here.
\t\t *
\t\t * Five windows, of which the DesignWare core claims three by name
\t\t * and the driver maps the two halves of the PHY itself.  The
\t\t * addresses are the ones the vendor tree gives.
\t\t */
\t\tpcie0: pcie@13ed0000 {
\t\t\tcompatible = "samsung,exynos9820-pcie";
\t\t\treg = <0x13ed0000 0x1000>,
\t\t\t      <0x13f00000 0x1000>,
\t\t\t      <0x14ffe000 0x2000>,
\t\t\t      <0x13ee0000 0x11000>;
\t\t\treg-names = "elbi", "dbi", "config", "phy";
\t\t\tinterrupts = <GIC_SPI 253 IRQ_TYPE_LEVEL_HIGH>;

\t\t\tdevice_type = "pci";
\t\t\t#address-cells = <3>;
\t\t\t#size-cells = <2>;
\t\t\tranges = <0x82000000 0 0x14000000 0x14000000 0 0x00ff0000>;
\t\t\tbus-range = <0x00 0xff>;
\t\t\tnum-lanes = <1>;
\t\t\tmax-link-speed = <1>;

\t\t\t#interrupt-cells = <1>;
\t\t\tinterrupt-map-mask = <0 0 0 0>;
\t\t\tinterrupt-map = <0 0 0 0 &gic GIC_SPI 253
\t\t\t\t\t IRQ_TYPE_LEVEL_HIGH>;

\t\t\tclocks = <&cmu_fsys1 CLK_GOUT_FSYS1_PCIE_GEN2_DBI_ACLK>,
\t\t\t\t <&cmu_fsys1 CLK_GOUT_FSYS1_PCIE_GEN2_MSTR_ACLK>,
\t\t\t\t <&cmu_fsys1 CLK_GOUT_FSYS1_PCIE_GEN2_SLV_ACLK>,
\t\t\t\t <&cmu_fsys1 CLK_GOUT_FSYS1_PCIE_GEN2_PHY_REFCLK_IN>,
\t\t\t\t <&cmu_fsys1 CLK_GOUT_FSYS1_PCIE_IA_GEN2_I_CLK>;

\t\t\tsamsung,pmu-syscon = <&pmu_system_controller>;
\t\t\tsamsung,fsys-sysreg = <&sysreg_fsys1>;

\t\t\tpinctrl-0 = <&pcie0_clkreq_pins>, <&pcie0_perst_pins>;
\t\t\tpinctrl-names = "default";
\t\t\treset-gpios = <&gpf2 2 GPIO_ACTIVE_HIGH>;

\t\t\tstatus = "disabled";
\t\t};
'''),
    (14, 0x10090000, '''\t\t/*
\t\t * The first of the two blocks of the thermal management unit, with
\t\t * the probes of the three CPU clusters.  The firmware on the APM
\t\t * owns them and answers for the zones over ACPM; the bootloader has
\t\t * armed the hardware trip of the block at 115 C.
\t\t */
\t\ttmu_top: thermal-sensor@10090000 {
\t\t\tcompatible = "samsung,exynos9820-tmu-top";
\t\t\treg = <0x10090000 0x800>;
\t\t\tinterrupts = <GIC_SPI 478 IRQ_TYPE_LEVEL_HIGH>;
\t\t\tclocks = <&cmu_peris CLK_GOUT_PERIS_TMU_TOP_PCLK>;
\t\t\t#thermal-sensor-cells = <1>;
\t\t\tsamsung,acpm-ipc = <&acpm_ipc>;
\t\t};
'''),
    (14, 0x100a0000, '''\t\t/* The second block, with the probes of the GPU and the ISP. */
\t\ttmu_sub: thermal-sensor@100a0000 {
\t\t\tcompatible = "samsung,exynos9820-tmu-sub";
\t\t\treg = <0x100a0000 0x800>;
\t\t\tinterrupts = <GIC_SPI 479 IRQ_TYPE_LEVEL_HIGH>;
\t\t\tclocks = <&cmu_peris CLK_GOUT_PERIS_TMU_SUB_PCLK>;
\t\t\t#thermal-sensor-cells = <1>;
\t\t\tsamsung,acpm-ipc = <&acpm_ipc>;
\t\t};
'''),
    (1, 0x1a240000, '''\t\t/*
\t\t * Every other clock controller takes its input from this one, so it
\t\t * is registered before them.
\t\t */
\t\tcmu_top: clock-controller@1a240000 {
\t\t\tcompatible = "samsung,exynos9820-cmu-top";
\t\t\treg = <0x1a240000 0x8000>;
\t\t\t#clock-cells = <1>;

\t\t\tclocks = <&oscclk>;
\t\t\tclock-names = "oscclk";
\t\t};
'''),
]


def dvfs_rdzenia(n, etap):
    """Wiersze zegara i OPP rdzenia n; od etapu 15, wczesniej puste."""
    if etap < 15:
        return {"zegar": "", "opp": ""}
    k = KLASTER[n]
    return {"zegar": ("\t\t\tclocks = <&acpm_ipc EXYNOS9820_CLK_ACPM_DVFS_CPUCL%d>;"
                      % k) + NL,
            "opp": ("\t\t\toperating-points-v2 = <&cpucl%d_opp_table>;" % k + NL +
                    "\t\t\t#cooling-cells = <2>;" + NL)}


def tabele_opp(etap):
    if etap < 15:
        return ""
    tabele = [OPP_KOMENTARZ]
    for k in sorted(OPP):
        wpisy = "".join(OPP_WPIS % {"hz": khz * 1000, "uv": uv}
                        for khz, uv in OPP[k])
        tabele.append(OPP_TABELA % {"k": k, "wpisy": wpisy})
    # opp-table-gpu idzie po opp-table-2: wezly korzenia sa alfabetycznie.
    if etap >= 17:
        tabele.append(GPU_OPP_TABELA % "".join(
            GPU_OPP_WPIS % {"hz": khz * 1000} for khz in GPU_OPP))
    return "".join(tabele)


def emituj(etap):
    rdzenie = "".join(RDZEN % dict({"n": n, "reg": reg, "compat": c,
                                    "cap": cap, "dpc": dpc},
                                   **dvfs_rdzenia(n, etap))
                      for n, reg, c, cap, dpc in RDZENIE)
    # Port debugowy jest od pierwszego etapu, port Bluetootha od dziesiatego,
    # a alias nie moze wskazywac etykiety, ktorej jeszcze nie ma.
    aliasy = ["\t\tserial0 = &serial0;"]
    if etap >= 10:
        aliasy.append("\t\tserial1 = &serial1;")
    naglowki = NAGLOWKI_15 if etap >= 15 else NAGLOWKI
    czesci = [NAGLOWEK % {"rdzenie": rdzenie,
                          "aliasy_portow": NL.join(aliasy) + NL,
                          "naglowki": NL.join(naglowki) + NL}]
    wskaznik = ("\t\t\tsamsung,pmu-intr-gen-syscon = <&pmu_intr_gen>;" + NL
                if etap >= 11 else "")
    # Wartosci sa te, ktore wpisuje sterownik producenta: prefiks 0x1234567
    # i numer trybu.  Bootloader czyta to slowo raz, zaraz po starcie.
    tryby = ("""\t\t\t/*
\t\t\t * What the bootloader reads after a reset to learn where it
\t\t\t * should go.  The values are the ones the vendor driver
\t\t\t * writes: a fixed prefix and the number of the mode.
\t\t\t */
\t\t\treboot_mode: reboot-mode {
\t\t\t\tcompatible = "syscon-reboot-mode";
\t\t\t\toffset = <0x080c>;
\t\t\t\tmode-download = <0x12345671>;
\t\t\t\tmode-upload = <0x12345672>;
\t\t\t\tmode-charging = <0x12345673>;
\t\t\t\tmode-recovery = <0x12345674>;
\t\t\t\tmode-bootloader = <0x1234567d>;
\t\t\t};

""" if etap >= 13 else "")
    for e, _, tresc in sorted(WEZLY, key=lambda x: x[1]):
        if e <= etap:
            if "%(" in tresc:
                tresc = tresc % dict({"wskaznik_intr_gen": wskaznik,
                                      "tryby_restartu": tryby},
                                     **dvfs_gpu(etap))
            czesci.append(NL + tresc)
    # Strefy termiczne siedza w korzeniu, alfabetycznie po firmware, a przed
    # timerem; tresc jest ta sama dla kazdej strefy poza nazwa i numerem.
    termika = ""
    if etap >= 14:
        szablon = (TERMIKA_18 if etap >= 18 else
                   TERMIKA_17 if etap >= 17 else
                   TERMIKA_15 if etap >= 15 else TERMIKA)
        termika = szablon % "".join(strefa(n, b, i, etap) for n, b, i in STREFY)
    firmware = FIRMWARE
    czesci.append(OGON % ((firmware if etap >= 9 else "") + tabele_opp(etap) +
                          termika))
    return "".join(czesci)


def main():
    if "--etap" not in sys.argv:
        for e in sorted(ETAPY):
            t = emituj(e)
            print("etap %d: %3d linii, wezlow pod soc@0 %2d  (%s)"
                  % (e, t.count(NL),
                     sum(1 for x in WEZLY if x[0] <= e), ETAPY[e]))
        return
    etap = int(sys.argv[sys.argv.index("--etap") + 1])
    if etap not in ETAPY:
        sys.exit("etap poza 1..4")
    tresc = emituj(etap)
    if "--zapisz" in sys.argv:
        io.open(CEL, "w", encoding="utf-8", newline=NL).write(tresc)
        print("zapisano %s (etap %d, %d linii)" % (CEL, etap, tresc.count(NL)))
    else:
        sys.stdout.write(tresc)


if __name__ == "__main__":
    main()
