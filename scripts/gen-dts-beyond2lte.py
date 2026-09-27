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
    3: "arm64: dts: exynos: exynos9820-beyond2lte: Enable the embedded storage",
    4: "arm64: dts: exynos: exynos9820-beyond2lte: Enable the USB port",
    5: "arm64: dts: exynos: exynos9820-beyond2lte: Add the fuel gauge",
    6: "arm64: dts: exynos: exynos9820-beyond2lte: Enable Bluetooth",
    7: "arm64: dts: exynos: exynos9820-beyond2lte: Add the main PMIC",
    8: "arm64: dts: exynos: exynos9820-beyond2lte: Describe the whole panel",
    9: "arm64: dts: exynos: exynos9820-beyond2lte: Add the ramoops region",
    10: "arm64: dts: exynos: exynos9820-beyond2lte: Enable Wi-Fi",
    11: "arm64: dts: exynos: exynos9820-beyond2lte: Route Bluetooth SCO over the UART",
    12: "arm64: dts: exynos: exynos9820-beyond2lte: Run the Bluetooth UART at 3 Mbaud",
    13: "arm64: dts: exynos: exynos9820-beyond2lte: Enable the speaker amplifier bus",
    14: "arm64: dts: exynos: exynos9820-beyond2lte: Add the speaker amplifiers",
    15: "arm64: dts: exynos: exynos9820-beyond2lte: Add the audio codec",
    16: "arm64: dts: exynos: exynos9820-beyond2lte: Run the codec bus at 25 MHz",
    17: "arm64: dts: exynos: exynos9820-beyond2lte: Add the sound card",
    18: "arm64: dts: exynos: exynos9820-beyond2lte: Add the sensor hub",
    19: "arm64: dts: exynos: exynos9820-beyond2lte: Add the vibration motor",
    20: "arm64: dts: exynos: exynos9820-beyond2lte: Add the flip cover sensor",
    21: "arm64: dts: exynos: exynos9820-beyond2lte: Enable the microSD slot",
}

NAGLOWEK_A = '''// SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause
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
'''

BUFOR_WASKI = '''\t\tframebuffer0: framebuffer@ca000080 {
\t\t\tcompatible = "simple-framebuffer";
\t\t\t/*
\t\t\t * The panel curves along both long edges, so the outermost
\t\t\t * columns are distorted and hard to hit with a finger.  The
\t\t\t * text console cannot offset its own area, so the buffer is
\t\t\t * described 32 pixels narrower on each side instead: the
\t\t\t * start moves by that many pixels and the line length stays
\t\t\t * as the hardware has it.
\t\t\t */
\t\t\treg = <0x0 0xca000080 ((1440 * 3040 - 32) * 4)>;
\t\t\twidth = <1376>;
\t\t\theight = <3040>;
\t\t\tstride = <(1440 * 4)>;
\t\t\tformat = "a8r8g8b8";
\t\t};
'''

BUFOR_PELNY = '''\t\tframebuffer0: framebuffer@ca000000 {
\t\t\tcompatible = "simple-framebuffer";
\t\t\t/*
\t\t\t * The panel curves along both long edges.  The buffer used to
\t\t\t * be described 32 pixels narrower on each side, because the
\t\t\t * text console cannot offset its own area and its outermost
\t\t\t * columns landed on the curve.  What runs on this phone now is
\t\t\t * an on-screen keyboard that wants the opposite: it fills the
\t\t\t * curved edges with its own background and keeps the keys
\t\t\t * themselves clear of them.  A program cannot paint outside
\t\t\t * the buffer this node describes, so the node describes the
\t\t\t * panel as it physically is.
\t\t\t */
\t\t\treg = <0x0 0xca000000 (1440 * 3040 * 4)>;
\t\t\twidth = <1440>;
\t\t\theight = <3040>;
\t\t\tstride = <(1440 * 4)>;
\t\t\tformat = "a8r8g8b8";
\t\t};
'''

NAGLOWEK_A2 = '''\t};

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

'''

ATRAPY_TSP = '''\t/*
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

'''

NAGLOWEK_B = '''\t/*
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
'''

# Obszar na log jadra przezywajacy reset, dokladany od etapu 9.
#
# Adres i rozmiar sa te same, ktore producent rezerwuje pod
# "debug-snapshot,log_kernel", wiec bramka mapy pamieci je zna,
# a firmware tej pamieci nie rusza.
RAMOOPS = '''
\t\t/*
\t\t * A kernel log that survives a reset.  The vendor reserves this
\t\t * region for "debug-snapshot,log_kernel" and its kernel keeps a
\t\t * ramoops buffer in it, so this memory is known to outlive a warm
\t\t * reset on this phone: the oops this port read back from
\t\t * /sys/fs/pstore after a reboot came from here.
\t\t *
\t\t * Without it a hang leaves nothing behind.  Bringing a secondary
\t\t * CPU online wedges this phone hard enough to take the USB link
\t\t * with it, and the console buffer below is the only way to see
\t\t * what the kernel printed last.
\t\t */
\t\tramoops@fd910000 {
\t\t\tcompatible = "ramoops";
\t\t\treg = <0x0 0xfd910000 0x200000>;
\t\t\tconsole-size = <0x100000>;
\t\t\trecord-size = <0x20000>;
\t\t\tpmsg-size = <0x20000>;
\t\t};
'''

NAGLOWEK_C = '''
\t\tel2_earlymem@9fd800000 {
\t\t\treg = <0x9 0xfd800000 0x2800000>;
\t\t\tno-map;
\t\t};
\t};
'''

# Karta dzwiekowa glosnikow, wezel w korzeniu od etapu 17.  Kolejnosc
# wzmacniaczy to kolejnosc kanalow: sluchawka lewy, dolny glosnik prawy,
# zmierzone VMON/IMON (measurements/2026-09-25-dzwiek).
KARTA = '''
\t/*
\t * The earpiece takes the left channel and the bottom speaker the right
\t * one, the way the vendor card pairs them.
\t */
\tsound {
\t\tcompatible = "samsung,beyond-audio";
\t\tmodel = "Samsung Galaxy S10+";
\t\taudio-routing = "Receiver", "Top SPK",
\t\t\t\t"Speaker", "Bottom SPK",
\t\t\t\t"DMIC1", "MICBIAS1A", "IN1ARN", "DMIC1", "IN1ARP", "DMIC1",
\t\t\t\t"DMIC2", "MICBIAS1B", "IN2ARN", "DMIC2", "IN2ARP", "DMIC2",
\t\t\t\t"Headset Mic", "MICBIAS2A", "IN1BLN", "Headset Mic",
\t\t\t\t"IN1BLP", "Headset Mic",
\t\t\t\t"Headphone", "HPOUT2L", "Headphone", "HPOUT2R";

\t\tcpu {
\t\t\tsound-dai = <&abox 1>;
\t\t};

\t\tcodec {
\t\t\tsound-dai = <&speaker_top 0>, <&speaker_bottom 0>;
\t\t};

\t\t/* the microphones and the headset jack, on UAIF0 */
\t\tcodec-link {
\t\t\tcpu {
\t\t\t\tsound-dai = <&abox 0>;
\t\t\t};

\t\t\tcodec {
\t\t\t\tsound-dai = <&audio_codec 0>;
\t\t\t};
\t\t};
\t};
'''

ZAMKNIECIE = '''};
'''

PIN = '''
\t%(etykieta)s: %(wezel)s {
\t\tsamsung,pins = "%(pin)s";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_EINT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV1>;
\t};
'''

HUB_LDO = '''
\t\t\t/*
\t\t\t * The sensor hub core, vdd_mcu_1p8 in the vendor tree, which keeps
\t\t\t * it always on.  Without it the hub never answers on its bus.
\t\t\t */
\t\t\tldo21m: LDO21M {
\t\t\t\tregulator-name = "vdd_mcu_1p8";
\t\t\t\tregulator-min-microvolt = <1800000>;
\t\t\t\tregulator-max-microvolt = <1800000>;
\t\t\t\tregulator-always-on;
\t\t\t};
'''

PINY = [
    ("key_volup", "key-volup-pins", "gpa0-3"),
    ("key_voldown", "key-voldown-pins", "gpa0-4"),
    ("key_wink", "key-wink-pins", "gpa0-6"),
    ("key_power", "key-power-pins", "gpa2-4"),
    ("ts_int", "ts-int-pins", "gpa1-0"),
]

HSI2C10 = '''
&hsi2c10 {
\tclock-frequency = <400000>;
\tstatus = "okay";

\ttouchscreen@48 {
\t\tcompatible = "samsung,s6sy771";
\t\treg = <0x48>;

\t\tavdd-supply = <&%s>;
\t\tvdd-supply = <&%s>;

\t\tinterrupts-extended = <&gpa1 0 IRQ_TYPE_LEVEL_LOW>;

\t\tpinctrl-0 = <&ts_int>;
\t\tpinctrl-names = "default";
\t};
};
'''

# Etap 11: SCO na UART (latka 0117), etap 12: 3 Mbaud (latka 0118).
SCO_PO_UART = '''\t\t/*
\t\t * The chip comes up routing SCO to its PCM pins, which on this
\t\t * board go to the audio subsystem, not to anything the host can
\t\t * read.  Route it over the UART instead, so that headset calls
\t\t * work without the audio subsystem.  Read back from the chip:
\t\t * 00 02 00 01 01 before, 01 02 00 01 01 after.
\t\t */
\t\tbrcm,bt-pcm-int-params = [01 02 00 01 01];
'''

UART_3M = '''\t\t/*
\t\t * At the default 115200 baud the link carries about 92 kbit/s,
\t\t * less than a single A2DP stream, and the 176 KiB patch takes
\t\t * 18 s to load.  3 Mbaud is the target of the vendor userspace
\t\t * driver; the 200 MHz port clock reaches it within 0.5 %.
\t\t */
\t\tmax-speed = <3000000>;
'''


# Etap 14: wzmacniacze CS35L40 na hsi2c38.
WZMACNIACZE = '''
\t/*
\t * Both amplifiers come out of reset with the boost coefficients of the
\t * 1.0 uH, below 20 uF row of the driver table (K1 0x24, K2 0x24, slope
\t * 0x75), and the vendor driver never changes them, only the peak current.
\t * Describing that row makes this driver program what the phone always
\t * ran with.  The interrupt line is shared and pulled up on the board (it
\t * reads high with both outputs off and the SoC pulling down), so both
\t * drive it open drain rather than push-pull.  The subsystem ID and the
\t * prefix name the speaker protection firmware and tuning each part loads,
\t * cirrus/cs35l41-dsp1-spk-prot-samsung-beyond2lte-{bottom,top}.
\t */
\tspeaker_bottom: amplifier@40 {
\t\tcompatible = "cirrus,cs35l40";
\t\treg = <0x40>;
\t\t#sound-dai-cells = <1>;
\t\tsound-name-prefix = "Bottom";
\t\tcirrus,subsystem-id = "samsung-beyond2lte";
\t\tpinctrl-0 = <&amp_int_pins>;
\t\tpinctrl-names = "default";
\t\tinterrupts-extended = <&gpm24 0 IRQ_TYPE_LEVEL_LOW>;
\t\treset-gpios = <&gph1 1 GPIO_ACTIVE_HIGH>;
\t\tcirrus,boost-type = <0>;
\t\tcirrus,boost-peak-milliamp = <4100>;
\t\tcirrus,boost-ind-nanohenry = <1000>;
\t\tcirrus,boost-cap-microfarad = <15>;
\t\tcirrus,asp-sdout-hiz = <3>;
\t\tcirrus,gpio2-src-select = <2>;
\t\tcirrus,gpio2-output-enable;
\t};

\tspeaker_top: amplifier@41 {
\t\tcompatible = "cirrus,cs35l40";
\t\treg = <0x41>;
\t\t#sound-dai-cells = <1>;
\t\tsound-name-prefix = "Top";
\t\tcirrus,subsystem-id = "samsung-beyond2lte";
\t\tinterrupts-extended = <&gpm24 0 IRQ_TYPE_LEVEL_LOW>;
\t\treset-gpios = <&gph1 2 GPIO_ACTIVE_HIGH>;
\t\tcirrus,boost-type = <0>;
\t\tcirrus,boost-peak-milliamp = <4100>;
\t\tcirrus,boost-ind-nanohenry = <1000>;
\t\tcirrus,boost-cap-microfarad = <15>;
\t\tcirrus,asp-sdout-hiz = <3>;
\t\tcirrus,gpio2-src-select = <2>;
\t\tcirrus,gpio2-output-enable;
\t};
'''


# Etap 15: kodek CS47L93 na SPI2 i jego szyny w PMIC.
PMIC_OPIS = ''' * Only the two rails the touchscreen needs are described.  The rest of the
 * chip carries the rails the CPU, the memory and the modem run from, and they
 * are left without constraints on purpose, so that nothing in the kernel can
 * be asked to change them.
'''

PMIC_OPIS_15 = ''' * Only the rails the touchscreen and the audio codec need are described.
 * The rest of the chip carries the rails the CPU, the memory and the modem
 * run from, and they are left without constraints on purpose, so that
 * nothing in the kernel can be asked to change them.
'''

# Etap 21: gniazdo microSD i jego dwie szyny w PMIC.
PMIC_OPIS_21 = ''' * Only the rails the touchscreen, the audio codec, the sensor hub and the
 * SD card need are described.  The rest of the chip carries the rails the
 * CPU, the memory and the modem run from, and they are left without
 * constraints on purpose, so that nothing in the kernel can be asked to
 * change them.
'''

SZYNY_KARTY = '''\t\t\t/*
\t\t\t * The SD card slot: vqmmc feeds the signal lines and drops to
\t\t\t * 1.8 V for the UHS modes, vmmc feeds the card.  Both ranges are
\t\t\t * the vendor's, and neither rail is kept on without a card.
\t\t\t */
\t\t\tldo2m: LDO2M {
\t\t\t\tregulator-name = "vqmmc";
\t\t\t\tregulator-min-microvolt = <1700000>;
\t\t\t\tregulator-max-microvolt = <2800000>;
\t\t\t};

\t\t\tldo15m: LDO15M {
\t\t\t\tregulator-name = "vmmc";
\t\t\t\tregulator-min-microvolt = <2800000>;
\t\t\t\tregulator-max-microvolt = <2800000>;
\t\t\t};

'''

SZYNY_KODEKA = '''\t\t\tldo17m: LDO17M {
\t\t\t\tregulator-name = "vdd_pmic_codec_1p8";
\t\t\t\tregulator-min-microvolt = <1800000>;
\t\t\t\tregulator-max-microvolt = <1800000>;
\t\t\t\tregulator-always-on;
\t\t\t\tregulator-boot-on;
\t\t\t};

\t\t\tldo18m: LDO18M {
\t\t\t\tregulator-name = "vdd_codec_1p2";
\t\t\t\tregulator-min-microvolt = <1200000>;
\t\t\t\tregulator-max-microvolt = <1200000>;
\t\t\t\tregulator-enable-ramp-delay = <5000>;
\t\t\t};

'''

KODEK = '''
/*
 * The audio hub, a CS47L93, is the only device on this bus.  AVDD, DBVDD1
 * and CPVDD1 come from LDO17M (1.8 V), DCVDD and CPVDD2 from LDO18M
 * (1.2 V), the only consumer of that rail in the vendor tree.
 *
 * The chip select is a GPIO.  The controller drops its own select after
 * every transfer, and a register read of this codec is two transfers, the
 * address and then the data, that need the select held across both.
 */
&spi_2 {
\tpinctrl-0 = <&spi2_bus>;
\tpinctrl-names = "default";
\tcs-gpios = <&gpp0 7 GPIO_ACTIVE_LOW>;
\tstatus = "okay";

\t%saudio-codec@0 {
\t\tcompatible = "cirrus,cs47l93";
\t\treg = <0>;
\t\tspi-max-frequency = <%s>;
%s
\t\tinterrupts-extended = <&gpa2 2 IRQ_TYPE_LEVEL_LOW>;
\t\tinterrupt-controller;
\t\t#interrupt-cells = <2>;
\t\tgpio-controller;
\t\t#gpio-cells = <2>;

\t\t/*
\t\t * The driver drives this line with raw values, low holding the
\t\t * chip in reset; active high keeps it in reset from the request
\t\t * until the rails are up, as in the vendor tree.  No pin group:
\t\t * requesting the line as an output sets its level first, where
\t\t * switching the pin to output from a group would not.
\t\t */
\t\treset-gpios = <&gpg1 0 GPIO_ACTIVE_HIGH>;
\t\tpinctrl-0 = <&codec_irq>%s;
\t\tpinctrl-names = "default";

\t\tAVDD-supply = <&ldo17m>;
\t\tDBVDD1-supply = <&ldo17m>;
\t\tCPVDD1-supply = <&ldo17m>;
\t\tCPVDD2-supply = <&ldo18m>;
\t\tDCVDD-supply = <&ldo18m>;
%s
\t\tcontroller-data {
\t\t\tsamsung,spi-feedback-delay = <1>;
\t\t};
\t};
};
'''

# Od etapu 17 kodek jest czescia karty: DAI, dwa DMIC na IN3 i IN4 zasilane
# z MICBIAS1, tryby wejsc i wyjsc oraz MICVDD 3,0 V jak w drzewie producenta
# (cs47l93@0: cirrus,dmic-ref, cirrus,inmode, cirrus,out-mono, micvdd), a
# wyprowadzenia AIF1 kodeka przelaczone na port: po resecie sa wolne i do
# 26.09.2026 nagranie przez UAIF0 dawalo same zera.
KODEK_KARTA = '''\t\t#sound-dai-cells = <1>;

\t\t/* the two DMICs on IN3 and IN4 run from MICBIAS1 */
\t\tcirrus,dmic-ref = <0 0 1 1>;
\t\tcirrus,inmode = <0 0 0 0 0 0 1 1>;
\t\tcirrus,out-mono = <0 0 0 1 0 0>;
'''

KODEK_PINY = '''
\t\tcodec_pins: pin-settings {
\t\t\taif1-pins {
\t\t\t\tgroups = "aif1";
\t\t\t\tfunction = "aif1";
\t\t\t\tbias-bus-hold;
\t\t\t};
\t\t};

\t\tmicvdd {
\t\t\tregulator-min-microvolt = <3000000>;
\t\t\tregulator-max-microvolt = <3000000>;
\t\t};
'''


def kodek(etap):
    karta = etap >= 17
    return KODEK % ("audio_codec: " if karta else "",
                    "25000000" if etap >= 16 else "5000000",
                    KODEK_KARTA if karta else "",
                    ", <&codec_pins>" if karta else "",
                    KODEK_PINY if karta else "")


def bluetooth_dodatki(etap):
    return (SCO_PO_UART if etap >= 11 else "") + (UART_3M if etap >= 12 else "")


# (etap, klucz sortowania, tresc).  Klucz to nazwa wezla, ktory nadpisujemy,
# zeby kolejnosc byla alfabetyczna i niezalezna od etapu.
BLOKI = [
    (4, "regulator_usb", '''
/ {
\treg_usb_dummy: regulator-usb-dummy {
\t\tcompatible = "regulator-fixed";
\t\tregulator-name = "usb_dummy";
\t};
};
'''),
    (4, "usbdrd", '''
/*
 * The port is described as peripheral only.  It is wired as dual role and
 * the phone changes roles with a USB-C controller sitting on the max77705,
 * which nothing in this series can reach; a dual role port without that
 * controller waits for a role that never arrives.  Peripheral is the half
 * that works with a plain cable to a PC, and it is the half this series
 * needs to be able to report anything about itself.
 *
 * The supplies are named against a stand-in.  They really come from rails
 * of the main PMIC, which sits behind the ACPM mailbox and which nothing
 * here can reach, and the driver would be happy with the dummy the
 * regulator core hands out for a supply nobody names.  The binding is not:
 * it lists both as required, so they are named, and named honestly as what
 * they are rather than as rails this series pretends to drive.
 */
&usbdrd {
\tstatus = "okay";
\tvdd10-supply = <&reg_usb_dummy>;
\tvdd33-supply = <&reg_usb_dummy>;
};
'''),
    (4, "usbdrd_dwc3", '''
/*
 * The port is wired to the only connector this phone has, so it has to work
 * both ways: as a device, which is how the machine is reached from a computer,
 * and as a host, so that a keyboard can be plugged into the phone.
 *
 * There is no Type-C driver here to sense which way the cable goes, so the
 * role is switched by hand through the role switch dwc3 registers, and the
 * default is spelled out: a board that came up as a host would drop the
 * connection to the computer and leave no way back in.
 */
&usbdrd_dwc3 {
\tdr_mode = "otg";
\tusb-role-switch;
\trole-switch-default-mode = "peripheral";
};
'''),
    (4, "usbdrd_phy", '''
&usbdrd_phy {
\tstatus = "okay";
};
'''),
    (5, "battery", '''
/*
 * The cell, described because the charger has to be told what it is
 * charging.  Every number here is read from the vendor tree of this exact
 * phone rather than from a datasheet of a similar one: the end of charge
 * voltage is battery,chg_float_voltage, the capacity is
 * battery,battery_full_capacity, the charge current is
 * battery,max_charging_current and the current at which the charge counts
 * as finished is full_check_current_1st.
 *
 * The cell itself agrees: an EB-BG975ABU is labelled 4000 mAh rated,
 * 3.85 V nominal, and a charging limit of 4.40 V.  The limit is what the
 * cell survives, not what it is charged to, and the vendor stops at 4.35 V;
 * that margin is where the life of the cell comes from, so the lower number
 * is the one described here and it is not a rounding to fix later.
 *
 * voltage-min-design-microvolt is left out.  The vendor tree never states a
 * cutoff as a voltage, and a number invented here would be the one thing in
 * this node that nothing measured.
 */
/ {
\tbattery: battery {
\t\tcompatible = "simple-battery";
\t\tdevice-chemistry = "lithium-ion";
\t\tcharge-full-design-microamp-hours = <4000000>;
\t\tvoltage-max-design-microvolt = <4350000>;
\t\tconstant-charge-voltage-max-microvolt = <4350000>;
\t\tconstant-charge-current-max-microamp = <2850000>;
\t\tcharge-term-current-microamp = <400000>;
\t};
};
'''),
    (5, "hsi2c45", '''
/*
 * The companion chip of the main PMIC: the fuel gauge, which answers how
 * much charge is left, and the charger, which puts it back.  The charger
 * needs a cell to charge against, so it points at the battery node above,
 * whose numbers come from the vendor tree of this phone.
 *
 * The address of the fuel gauge started out as an analogy with the only
 * other board in mainline carrying this chip, a Galaxy S9, because the
 * vendor sources for this phone never put the fuel gauge on a bus at all:
 * they hang it in the root of the tree with no address and bind it to the
 * battery by name.  It has since been measured on the phone, by driving
 * this bus by hand over its own pins: 0x36 answers, and so do 0x66 for the
 * companion chip and 0x69 beside them.  The analogy held.
 *
 * maxim,rsns-microohm is not guessed either, it is derived from what the
 * gauge itself reports.  The vendor gives the resistor as a plain index
 * rather than as a resistance, so the value comes from the measurement:
 * with the driver default of 10 mohm the gauge reported a design capacity
 * of 1979 mAh for a cell labelled 4000 mAh, and that ratio is the resistor.
 * Half the assumed resistance gives twice the reported capacity, so 5 mohm
 * it is, and the reported capacity then lands on the printed one.
 */
&hsi2c45 {
\tstatus = "okay";

\tmax77705: pmic@66 {
\t\tcompatible = "maxim,max77705";
\t\treg = <0x66>;
\t\tinterrupt-parent = <&gpa1>;
\t\tinterrupts = <6 IRQ_TYPE_LEVEL_LOW>;
\t\tinterrupt-controller;
\t\t#interrupt-cells = <1>;
\t\tpinctrl-0 = <&pmic_irq>;
\t\tpinctrl-names = "default";
\t};

\tfuel-gauge@36 {
\t\tcompatible = "maxim,max77705-battery";
\t\treg = <0x36>;
\t\tmaxim,rsns-microohm = <5000>;
\t\tinterrupt-parent = <&max77705>;
\t\tinterrupts = <2>;
\t};

\tcharger@69 {
\t\tcompatible = "maxim,max77705-charger";
\t\treg = <0x69>;
\t\tmonitored-battery = <&battery>;
\t\tinterrupt-parent = <&max77705>;
\t\tinterrupts = <0>;
\t};
};
'''),
    (3, "ufs_0", '''
&ufs_0 {
	status = "okay";
};
'''),
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
    (1, "hsi2c10", lambda etap: HSI2C10 % (
        "ldo27m" if etap >= 7 else "reg_tsp_avdd",
        "ldo19m" if etap >= 7 else "reg_tsp_io")),
    (7, "acpm_pmic", lambda etap: '''
/*
 * The main PMIC of this board.  It does not answer on any bus of the CPU: it
 * hangs off a SPEEDY link of the power management firmware, so the node sits
 * under that firmware and every register access travels as an ACPM command.
 *
%s */
&acpm_ipc {
\tpmic-1 {
\t\tcompatible = "samsung,s2mps19-pmic";
\t\tinterrupts-extended = <&gpa0 1 IRQ_TYPE_LEVEL_LOW>;
\t\tpinctrl-names = "default";
\t\tpinctrl-0 = <&main_pmic_irq>;
\t\twakeup-source;

\t\tregulators {
%s\t\t\tldo19m: LDO19M {''' % ((PMIC_OPIS_21, SZYNY_KARTY + SZYNY_KODEKA)
                             if etap >= 21 else
                             (PMIC_OPIS_15, SZYNY_KODEKA) if etap >= 15
                             else (PMIC_OPIS, "")) + '''
\t\t\t\tregulator-name = "tsp_io";
\t\t\t\tregulator-min-microvolt = <1800000>;
\t\t\t\tregulator-max-microvolt = <1800000>;
\t\t\t};
''' + (HUB_LDO if etap >= 18 else '') + '''
\t\t\tldo27m: LDO27M {
\t\t\t\tregulator-name = "tsp_avdd";
\t\t\t\tregulator-min-microvolt = <3000000>;
\t\t\t\tregulator-max-microvolt = <3000000>;
\t\t\t};
\t\t};
\t};
};
'''),
    (7, "pinctrl_alive_main_pmic", '''
&pinctrl_alive {
\tmain_pmic_irq: main-pmic-irq-pins {
\t\tsamsung,pins = "gpa0-1";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_EINT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_UP>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV4>;
\t};
};
'''),
    (1, "oscclk", '''
&oscclk {
\tclock-frequency = <26000000>;
};
'''),
    (1, "pinctrl_alive", None),
    (5, "pinctrl_alive_pmic", '''
&pinctrl_alive {
\tpmic_irq: pmic-irq-pins {
\t\tsamsung,pins = "gpa1-6";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_EINT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV1>;
\t};
};
'''),   # wypelniane z tablicy PINY
    (1, "serial0", '''
&serial0 {
\tstatus = "okay";
};
'''),
    (6, "serial1", lambda etap: '''
/*
 * The Bluetooth controller answers on the serial port of the PERIC1 USI
 * block.  Three lines go with the port: the one the chip powers up from, the
 * one the host pokes to wake the controller, and the one the controller pokes
 * to wake the host.  The last one is an interrupt, so it is described as one
 * rather than as the deprecated gpio property.
 */
&serial1 {
\tstatus = "okay";

\tbluetooth {
\t\tcompatible = "brcm,bcm4375-bt";
\t\tpinctrl-names = "default";
\t\tpinctrl-0 = <&bt_en_pins>, <&bt_btwake_pins>,
\t\t\t    <&bt_hostwake_pins>;
\t\tshutdown-gpios = <&gpm8 0 GPIO_ACTIVE_HIGH>;
\t\tdevice-wakeup-gpios = <&gpg2 0 GPIO_ACTIVE_HIGH>;
\t\tinterrupts-extended = <&gpa2 3 IRQ_TYPE_EDGE_RISING>;
\t\tinterrupt-names = "host-wakeup";
%s\t};
};
''' % bluetooth_dodatki(etap)),
    (17, "abox", '''
&abox {
	status = "okay";
};
'''),
    (13, "hsi2c38", lambda etap: '''
/*
 * The two speaker amplifiers answer on this bus, CS35L40 at 0x40 (the bottom
 * speaker) and at 0x41 (the earpiece, which doubles as the second speaker).
 */
&hsi2c38 {
\tclock-frequency = <400000>;
\tstatus = "okay";
%s};
''' % (WZMACNIACZE if etap >= 14 else "")),
    (15, "spi_2", kodek),
    (15, "usi1", '''
/* This USI instance is wired as the SPI master the audio codec answers on. */
&usi1 {
\tsamsung,mode = <USI_V2_SPI>;
\tstatus = "okay";
};
'''),
    (15, "pinctrl_alive_kodek", '''
&pinctrl_alive {
\tcodec_irq: codec-irq-pins {
\t\tsamsung,pins = "gpa2-2";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_EINT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t};
};
'''),
    (14, "pinctrl_cmgp", '''
&pinctrl_cmgp {
\tamp_int_pins: amp-int-pins {
\t\tsamsung,pins = "gpm24-0";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_EINT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV1>;
\t};
};
'''),
    (13, "usi17_i2c", '''
/*
 * This I2C-only USI instance carries the bus of the speaker amplifiers.
 * Picking the mode here is also what releases the block from reset.
 */
&usi17_i2c {
\tsamsung,mode = <USI_V2_I2C>;
\tstatus = "okay";
};
'''),
    (6, "usi_uart_bt", '''
/* This USI instance is wired as the serial port the Bluetooth chip uses. */
&usi_uart_bt {
\tsamsung,mode = <USI_V2_UART>;
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
    (2, "usi_cmgp2", '''
/*
 * This one is wired as the I2C master the display PMIC answers on.  Picking
 * the mode here is also what releases the block from reset, so the bus below
 * cannot work without it.
 */
&usi_cmgp2 {
\tsamsung,mode = <USI_V2_I2C>;
\tstatus = "okay";
};
'''),
    (5, "usi_cmgp3", '''
/*
 * This USI instance is wired as the I2C master the main PMIC's companion
 * answers on.  Picking the mode here is also what releases the block from
 * reset, so the bus below cannot work without it.
 */
&usi_cmgp3 {
\tsamsung,mode = <USI_V2_I2C>;
\tstatus = "okay";
};
'''),
    (18, "pinctrl_alive_hub", '''
/*
 * The sensor hub and GNSS receiver, a Broadcom BCM47752 the vendor tree
 * still calls BCM4773, answers on the vendor spi_17.  The groups below carry
 * the pull, drive and sleep settings of the vendor tree.  The output lines
 * get no pin function from their groups: requesting a line as an output sets
 * its level first, where switching the pin to output from a group would not.
 * The ALIVE banks have no sleep fields, so the vendor sleep setting of the
 * batch wake line is left out.
 */
&pinctrl_alive {
\tssp_batch_wake_pins: ssp-batch-wake-pins {
\t\tsamsung,pins = "gpa0-5";
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t};

\tssp_host_req_pins: ssp-host-req-pins {
\t\tsamsung,pins = "gpa1-7";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_EINT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_DOWN>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV4>;
\t};

\tssp_shub_int_pins: ssp-shub-int-pins {
\t\tsamsung,pins = "gpa4-0";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_EINT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV4>;
\t};
};
'''),
    (18, "pinctrl_peric0_hub", '''
&pinctrl_peric0 {
\tssp_gps_pwr_en_pins: ssp-gps-pwr-en-pins {
\t\tsamsung,pins = "gpg0-2";
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_DOWN>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV4>;
\t\tsamsung,pin-con-pdn = <EXYNOS_PIN_PDN_PREV>;
\t\tsamsung,pin-pud-pdn = <EXYNOS_PIN_PULL_NONE>;
\t};

\tssp_mcu_req_pins: ssp-mcu-req-pins {
\t\tsamsung,pins = "gpg4-1";
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV4>;
\t\tsamsung,pin-con-pdn = <EXYNOS_PIN_PDN_PREV>;
\t\tsamsung,pin-pud-pdn = <EXYNOS_PIN_PULL_NONE>;
\t};

\tssp_mcu_resp_pins: ssp-mcu-resp-pins {
\t\tsamsung,pins = "gpg4-2";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_INPUT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV4>;
\t\tsamsung,pin-con-pdn = <EXYNOS_PIN_PDN_INPUT>;
\t\tsamsung,pin-pud-pdn = <EXYNOS_PIN_PULL_NONE>;
\t};
};
'''),
    (18, "spi_17", '''
/*
 * The chip select is a GPIO, as in the vendor tree and on the codec bus.
 * The select this controller drives by itself is automatic, and an SSI
 * frame is one transfer longer than the 64 byte FIFO.
 */
&spi_17 {
\tcs-gpios = <&gph0 3 GPIO_ACTIVE_LOW>;
\tstatus = "okay";

\tsensorhub@0 {
\t\tcompatible = "brcm,bcm47752";
\t\treg = <0>;
\t\tspi-max-frequency = <25000000>;
\t\tspi-cpol;
\t\tspi-cpha;

\t\t/* raw levels, the way the vendor driver reads and drives them */
\t\thost-req-gpios = <&gpa1 7 GPIO_ACTIVE_HIGH>;
\t\tmcu-req-gpios = <&gpg4 1 GPIO_ACTIVE_HIGH>;
\t\tmcu-resp-gpios = <&gpg4 2 GPIO_ACTIVE_HIGH>;
\t\tbatch-wake-gpios = <&gpa0 5 GPIO_ACTIVE_HIGH>;
\t\tshub-int-gpios = <&gpa4 0 GPIO_ACTIVE_HIGH>;
\t\tgps-pwr-en-gpios = <&gpg0 2 GPIO_ACTIVE_HIGH>;

\t\tinterrupts-extended = <&gpa1 7 IRQ_TYPE_LEVEL_HIGH>,
\t\t\t\t      <&gpa4 0 IRQ_TYPE_EDGE_FALLING>;
\t\tinterrupt-names = "host-req", "shub-int";

\t\tpinctrl-0 = <&ssp_host_req_pins>, <&ssp_mcu_req_pins>,
\t\t\t    <&ssp_mcu_resp_pins>, <&ssp_batch_wake_pins>,
\t\t\t    <&ssp_shub_int_pins>, <&ssp_gps_pwr_en_pins>;
\t\tpinctrl-names = "default";

\t\tbrcm,ap-type = <2>;
\t\tbrcm,acc-position = <4>;
\t\tbrcm,mag-position = <7>;
\t\tbrcm,mag-type = <1>;
\t\tbrcm,glass-type = <0>;
\t\tbrcm,mag-array = /bits/ 8 <0xc1 0x52 0xa9 0xed 0x9e 0x42 0x00 0x35 0xd4
\t\t\t\t\t  0x38 0xcd 0x98 0xa7 0x8d 0x01 0xcb 0xff 0xb4
\t\t\t\t\t  0xbe 0x9c 0xc1 0xfc 0x7f 0x64 0x0c 0xee 0xd4>;
\t\tbrcm,thermi-up = /bits/ 16 <0x0bce 0x0bb0 0x0b8a 0x0b5b 0x0b21 0x0ad8
\t\t\t\t\t   0x0a86 0x0a20 0x09a7 0x0927 0x0894 0x0806
\t\t\t\t\t   0x0765 0x06c2 0x061d 0x0577 0x04e1 0x0453
\t\t\t\t\t   0x03f0 0x0372 0x0303 0x02a1 0x0254>;
\t\tbrcm,thermi-sub = /bits/ 16 <0x0bc7 0x0ba9 0x0b85 0x0b59 0x0b1b 0x0ad4
\t\t\t\t\t    0x0a7d 0x0a15 0x099d 0x091e 0x088b 0x07fb
\t\t\t\t\t    0x0761 0x06ba 0x0618 0x056e 0x04da 0x044c
\t\t\t\t\t    0x03e7 0x0369 0x02fb 0x02a0 0x024d>;
\t};
};
'''),
    (18, "usi16", '''
/* This USI instance is wired as the SPI master of the sensor hub. */
&usi16 {
\tsamsung,mode = <USI_V2_SPI>;
\tstatus = "okay";
};
'''),
    (19, "max77705_haptic", '''
/*
 * Vibration.  The motor is a linear resonant actuator driven by the haptic
 * block of the max77705, which takes its drive signal from channel 1 of the
 * PERIC0 PWM block on gpp3-1, in the pin function the vendor gives that pin.
 *
 * The period is the first of the seven the vendor lists, 48828 ns.  The
 * driver programs the chip to divide the PWM rate by 128, the same divider
 * the vendor programs, so the motor sees 20480 Hz / 128 = 160 Hz.  The other
 * six vendor periods land between 120 and 200 Hz; the mainline driver takes
 * one period only.
 *
 * The vendor never lets the duty cycle past 75 % (its duty 36621 ns of the
 * 48828 ns period), 95 % when it overdrives.  The mainline driver maps an
 * effect magnitude of 0..0xffff onto 50..100 %, so 0x8000 is the vendor's
 * normal strength and 0xe666 its overdrive.
 */
&max77705 {
\thaptic {
\t\tcompatible = "maxim,max77705-haptic";
\t\thaptic-supply = <&vdd_motor>;
\t\tpwms = <&pwm 1 48828 0>;
\t};
};
'''),
    (19, "pinctrl_peric0_vib", '''
&pinctrl_peric0 {
\tvib_pwm: vib-pwm-pins {
\t\tsamsung,pins = "gpp3-1";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_2>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_DOWN>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV1>;
\t};

\tmotor_boost_en: motor-boost-en-pins {
\t\tsamsung,pins = "gpg1-7";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_OUTPUT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-con-pdn = <EXYNOS_PIN_PDN_OUT0>;
\t\tsamsung,pin-pud-pdn = <EXYNOS_PIN_PULL_NONE>;
\t};
};
'''),
    (19, "pwm", '''
&pwm {
\tpinctrl-names = "default";
\tpinctrl-0 = <&vib_pwm>;
\tstatus = "okay";
};
'''),
    (19, "regulator_motor", '''
/ {
\t/*
\t * MOTOR_BOOST_EN on gpg1-7.  The vendor raises it from pinctrl the
\t * moment the max77705 probes and never touches it again: its boost
\t * callback does nothing.  Its haptic node names a supply VDD_MOTOR_3P3
\t * that no node of the vendor tree provides.  Here the line is the
\t * supply of the haptic block, switched on while the input device is
\t * open.  The voltage is the one in the vendor name, not a measurement.
\t */
\tvdd_motor: regulator-vdd-motor {
\t\tcompatible = "regulator-fixed";
\t\tregulator-name = "vdd_motor";
\t\tregulator-min-microvolt = <3300000>;
\t\tregulator-max-microvolt = <3300000>;
\t\tgpio = <&gpg1 7 GPIO_ACTIVE_HIGH>;
\t\tenable-active-high;
\t\tpinctrl-names = "default";
\t\tpinctrl-0 = <&motor_boost_en>;
\t};
};
'''),
    (20, "pinctrl_alive_hall", '''
/*
 * The flip cover sensor on gpa3-6.  The vendor hall driver reports SW_LID as
 * the inverse of the line (CONFIG_HALL_EVENT_REVERSE=y) and logs a high line
 * as "open", so the line goes low under the magnet of a closed cover and the
 * switch is active low.
 *
 * The second sensor, certify_hall on gpa0-2, recognizes the vendor's own
 * covers and reports SW_CERTIFYHALL, a switch code that exists only in the
 * vendor kernel.  Its pin is set up as an input here and left for user space
 * to read through the GPIO character device, rather than mapped onto an
 * unrelated mainline switch code.
 */
&pinctrl_alive {
\thall_irq: hall-irq-pins {
\t\tsamsung,pins = "gpa3-6";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_EINT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV1>;
\t};

\tcertify_hall_irq: certify-hall-irq-pins {
\t\tsamsung,pins = "gpa0-2";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_EINT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV1>;
\t};
};
'''),
    (20, "hall", '''
/ {
\tgpio-hall-effect-sensor {
\t\tcompatible = "gpio-keys";
\t\tlabel = "Hall Effect Sensor";

\t\tpinctrl-0 = <&hall_irq &certify_hall_irq>;
\t\tpinctrl-names = "default";

\t\tevent-hall-effect-sensor {
\t\t\tlabel = "Flip Cover";
\t\t\tgpios = <&gpa3 6 GPIO_ACTIVE_LOW>;
\t\t\tlinux,input-type = <EV_SW>;
\t\t\tlinux,code = <SW_LID>;
\t\t\tlinux,can-disable;
\t\t\twakeup-source;
\t\t};
\t};
};
'''),
    (21, "pinctrl_fsys1_sd", '''
/*
 * The SD card lines.  The vendor names six drive strengths of this bank from
 * 1x to 4x and writes their index, which is how the HSI bank of the Exynos850
 * is described: the clock is driven at 3x, the command and data lines at
 * 2.5x, and those carry pull-ups.
 */
&pinctrl_fsys1 {
\tsd2_clk: sd2-clk-pins {
\t\tsamsung,pins = "gpf1-0";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_2>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS850_HSI_PIN_DRV_LV3>;
\t};

\tsd2_cmd: sd2-cmd-pins {
\t\tsamsung,pins = "gpf1-1";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_2>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_UP>;
\t\tsamsung,pin-drv = <EXYNOS850_HSI_PIN_DRV_LV2_5>;
\t};

\tsd2_bus1: sd2-bus-width1-pins {
\t\tsamsung,pins = "gpf1-2";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_2>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_UP>;
\t\tsamsung,pin-drv = <EXYNOS850_HSI_PIN_DRV_LV2_5>;
\t};

\tsd2_bus4: sd2-bus-width4-pins {
\t\tsamsung,pins = "gpf1-3", "gpf1-4", "gpf1-5";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_2>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_UP>;
\t\tsamsung,pin-drv = <EXYNOS850_HSI_PIN_DRV_LV2_5>;
\t};
};
'''),
    (21, "pinctrl_alive_sd", '''
/*
 * The slot is a hybrid one: its tray takes either a second SIM or a microSD
 * card, and the switch on gpa1-5 senses the tray, not the card.  The line is
 * low with the tray in and high with it out; the vendor host logs a high
 * line as "tray Removed" and does not invert it on this board.  Whether a
 * card sits in the tray the host finds out itself, by trying to bring one
 * up, so with an empty tray it probes the slot and powers it down again.
 */
&pinctrl_alive {
\tsd2_cd: sd2-cd-pins {
\t\tsamsung,pins = "gpa1-5";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_EINT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV1>;
\t};
};
'''),
    (21, "mmc_2", '''
&mmc_2 {
\tpinctrl-names = "default";
\tpinctrl-0 = <&sd2_clk &sd2_cmd &sd2_bus1 &sd2_bus4 &sd2_cd>;

\tvmmc-supply = <&ldo15m>;
\tvqmmc-supply = <&ldo2m>;
\tcd-gpios = <&gpa1 5 GPIO_ACTIVE_LOW>;
\tcard-detect-delay = <200>;

\tbus-width = <4>;
\tcap-sd-highspeed;
\tsd-uhs-sdr50;
\tsd-uhs-sdr104;
\tdisable-wp;

\t/*
\t * The vendor host reads four numbers here, the divider, a fine drive
\t * phase, the drive phase and the sample phase, while this one reads the
\t * sample and the drive phase only.  Its <3 0 2 0> and <3 0 2 1> are
\t * therefore a divider of 3 with these pairs.
\t */
\tsamsung,dw-mshc-ciu-div = <3>;
\tsamsung,dw-mshc-sdr-timing = <0 2>;
\tsamsung,dw-mshc-ddr-timing = <1 2>;

\tstatus = "okay";
};
'''),
    (10, "pcie0", '''
/*
 * The Wi-Fi half of the BCM4375 sits on this controller.  It answers only
 * once the line below has powered it up, so that line is the supply the
 * controller switches on before it releases the chip from reset.
 */
&pcie0 {
\tvpcie3v3-supply = <&wlan_reg_on>;
\tstatus = "okay";
};
'''),
    (10, "pinctrl_peric0_wlan", '''
&pinctrl_peric0 {
\twlan_en_pins: wlan-en-pins {
\t\tsamsung,pins = "gpg0-5";
\t\tsamsung,pin-function = <EXYNOS_PIN_FUNC_OUTPUT>;
\t\tsamsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
\t\tsamsung,pin-drv = <EXYNOS5420_PIN_DRV_LV4>;
\t\tsamsung,pin-con-pdn = <EXYNOS_PIN_PDN_PREV>;
\t\tsamsung,pin-pud-pdn = <EXYNOS_PIN_PULL_NONE>;
\t};
};
'''),
    (10, "regulator_wlan", '''
/ {
\t/*
\t * WL_REG_ON, the line that powers up the Wi-Fi half of the BCM4375.
\t * The Bluetooth half has a line of its own.  The vendor raises this
\t * one and waits 100 ms before the controller may train the link, and
\t * keeps its level through sleep.
\t */
\twlan_reg_on: regulator-wlan-en {
\t\tcompatible = "regulator-fixed";
\t\tregulator-name = "wlan_en";
\t\tgpio = <&gpg0 5 GPIO_ACTIVE_HIGH>;
\t\tenable-active-high;
\t\tstartup-delay-us = <100000>;
\t\tpinctrl-names = "default";
\t\tpinctrl-0 = <&wlan_en_pins>;
\t};
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
    czesci = [NAGLOWEK_A]
    czesci.append(BUFOR_WASKI if etap < 8 else BUFOR_PELNY)
    czesci.append(NAGLOWEK_A2)
    if etap < 7:
        czesci.append(ATRAPY_TSP)
    czesci.append(NAGLOWEK_B)
    if etap >= 9:
        czesci.append(RAMOOPS)
    czesci.append(NAGLOWEK_C)
    if etap >= 17:
        czesci.append(KARTA)
    czesci.append(ZAMKNIECIE)
    for e, klucz, tresc in sorted(BLOKI, key=lambda x: x[1]):
        if e > etap:
            continue
        if tresc is None:
            czesci.append(blok_pinow())
        elif callable(tresc):
            czesci.append(tresc(etap))
        else:
            czesci.append(tresc)
    return "".join(czesci)


def main():
    if "--etap" not in sys.argv:
        for e in sorted(ETAPY):
            t = emituj(e)
            print("etap %d: %3d linii  (%s)" % (e, t.count(NL), ETAPY[e]))
        return
    etap = int(sys.argv[sys.argv.index("--etap") + 1])
    if etap not in ETAPY:
        sys.exit("etap poza 1..%d" % max(ETAPY))
    tresc = emituj(etap)
    if "--zapisz" in sys.argv:
        io.open(CEL, "w", encoding="utf-8", newline=NL).write(tresc)
        print("zapisano %s (etap %d, %d linii)" % (CEL, etap, tresc.count(NL)))
    else:
        sys.stdout.write(tresc)


if __name__ == "__main__":
    main()
