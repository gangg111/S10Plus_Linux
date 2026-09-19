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

#include <dt-bindings/clock/samsung,exynos9820.h>
#include <dt-bindings/interrupt-controller/arm-gic.h>

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
\t};

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
%s\t};

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
\t\t\tenable-method = "psci";
\t\t\tcapacity-dmips-mhz = <%(cap)d>;
\t\t\tdynamic-power-coefficient = <%(dpc)d>;
\t\t};
'''

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
WEZLY = [
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
    (1, 0x13030000, '''\t\tpinctrl_fsys0: pinctrl@13030000 {
\t\t\tcompatible = "samsung,exynos9820-pinctrl";
\t\t\treg = <0x13030000 0x1000>;
\t\t\tinterrupts = <GIC_SPI 240 IRQ_TYPE_LEVEL_HIGH>;
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

\t\t\tpoweroff: syscon-poweroff {
\t\t\t\tcompatible = "syscon-poweroff";
\t\t\t\tregmap = <&pmu_system_controller>;
\t\t\t\toffset = <0x030c>; /* PS_HOLD_CONTROL */
\t\t\t\tmask = <0x100>;
\t\t\t\tvalue = <0x0>;
\t\t\t};

\t\t\treboot: syscon-reboot {
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
    (4, 0x15d50000, '''\t\t/*
\t\t * This bus stays awake with the CMGP domain, which is why the
\t\t * display PMIC hangs off it rather than off a PERIC bus: the panel
\t\t * rails have to be reachable while the rest sleeps.
\t\t */
\t\thsi2c2: i2c@15d50000 {
\t\t\tcompatible = "samsung,exynos9820-hsi2c",
\t\t\t\t     "samsung,exynosautov9-hsi2c";
\t\t\treg = <0x15d50000 0x1000>;
\t\t\tinterrupts = <GIC_SPI 81 IRQ_TYPE_LEVEL_HIGH>;
\t\t\t#address-cells = <1>;
\t\t\t#size-cells = <0>;

\t\t\tclocks = <&cmu_cmgp CLK_GOUT_CMGP_I2C_CMGP2_IPCLK>,
\t\t\t\t <&cmu_cmgp CLK_GOUT_CMGP_I2C_CMGP2_PCLK>;
\t\t\tclock-names = "hsi2c", "hsi2c_pclk";
\t\t\tpinctrl-0 = <&hsi2c2_bus>;
\t\t\tpinctrl-names = "default";
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


def emituj(etap):
    rdzenie = "".join(RDZEN % {"n": n, "reg": reg, "compat": c, "cap": cap,
                               "dpc": dpc}
                      for n, reg, c, cap, dpc in RDZENIE)
    czesci = [NAGLOWEK % rdzenie]
    for e, _, tresc in sorted(WEZLY, key=lambda x: x[1]):
        if e <= etap:
            czesci.append(NL + tresc)
    czesci.append(OGON)
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
