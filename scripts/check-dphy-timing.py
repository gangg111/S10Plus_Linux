#!/usr/bin/env python3
"""Nasze wartosci D-PHY, PLL, escape i rewizja krzemu wobec logu S-Boota telefonu.

Blok wyswietlacza serii jest przepisany z tablic producenta, a ich jednostki i
dokladny zegar lacza nie sa nigdzie udokumentowane (HW-01, HW-02, HW-03). Log
S-Boota tego egzemplarza (measurements/2026-09-17-etap0/) niesie natomiast to,
co bootloader NAPRAWDE programuje przy starcie, gdy panel realnie zaswieca:
dziesiec licznikow D-PHY, b_dphyctl, P/M/S PLL-a, zegar slowa i lancuch escape,
oraz rewizje krzemu (HW-11). Ta bramka przypina wartosci serii do tego pomiaru,
wielkosc po wielkosci, zeby nikt ich pozniej nie ruszyl w bok od sprzetu.

Zrodlo pomiaru: log S-Boota z /proc/last_kmsg, linie dsim_set_clocks,
dsim_get_dphy_timing, dsim_set_pll_freq oraz baner "EXYNOS9820 EVT".
Zrodlo serii: struktura exynos9820_dsim_phy_timings w sterowniku PHY i
wlasciwosc samsung,esc-clock-frequency w DTSI.

Kod 0 gdy wszystko sie zgadza, 1 przy rozjezdzie, 2 gdy brak ktoregos wejscia
(wtedy verify.sh liczy bramke jako nieuruchomiona, nie zielona).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "measurements", "2026-09-17-etap0",
                   "sboot-log-z-last_kmsg.txt")
PHY = os.path.join(ROOT, "sources", "linux", "drivers", "phy", "samsung",
                   "phy-exynos9820-dsim.c")
DTSI = os.path.join(ROOT, "sources", "linux", "arch", "arm64", "boot", "dts",
                    "exynos", "exynos9820.dtsi")


def read(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_log(text):
    """Wielkosci, ktore bootloader wypisuje przy inicjalizacji DSIM."""
    out = {}
    m = re.search(r"EXYNOS9820 EVT ([0-9.]+)", text)
    if m:
        out["evt"] = m.group(1)
    m = re.search(r"word clock is (\d+) MHz", text)
    if m:
        out["word_mhz"] = int(m.group(1))
    m = re.search(r"requested escape clock (\d+) MHz", text)
    if m:
        out["esc_req_mhz"] = int(m.group(1))
    m = re.search(r"escape clock divider is (0x[0-9a-fA-F]+|\d+)", text)
    if m:
        out["esc_div"] = int(m.group(1), 0)
    m = re.search(r"escape clock is (\d+) MHz", text)
    if m:
        out["esc_mhz"] = int(m.group(1))
    for name in ("clk_prepare", "clk_zero", "clk_post", "clk_trail",
                 "hs_prepare", "hs_zero", "hs_trail", "lpx", "hs_exit",
                 "b_dphyctl"):
        m = re.search(r"%s\((\d+)\)" % name, text)
        if m:
            out[name] = int(m.group(1))
    m = re.search(r"bps\((\d+)\)", text)
    if m:
        out["bps"] = int(m.group(1))
    m = re.search(r"dsim_set_pll_freq:\s*p\s*:\s*(\d+),\s*m\s*:\s*(\d+),"
                  r"\s*s\s*:\s*(\d+),\s*k\s*:\s*(\d+)", text)
    if m:
        out["pll"] = tuple(int(x) for x in m.groups())
    return out


def parse_series(phy_text, dtsi_text):
    """Wielkosci, ktore programuje nasza seria."""
    out = {}
    # Jedyny wiersz struktury czasowej, etykieta 898 Mbps.
    blok = re.search(r"\.hs_clk_rate\s*=\s*(\d+)UL,(.*?)\.pll_p", phy_text,
                     re.S)
    if blok:
        out["bps"] = int(blok.group(1)) // 1000000
        body = blok.group(2)
        for name in ("clk_prepare", "clk_zero", "clk_post", "clk_trail",
                     "hs_prepare", "hs_zero", "hs_trail", "lpx", "hs_exit",
                     "ulps_exit"):
            m = re.search(r"\.%s\s*=\s*(0x[0-9a-fA-F]+|\d+)" % name, body)
            if m:
                out[name] = int(m.group(1), 0)
    m = re.search(r"\.pll_p\s*=\s*(\d+),\s*\.pll_m\s*=\s*(\d+),"
                  r"\s*\.pll_s\s*=\s*(\d+),\s*\.pll_k\s*=\s*(\d+)", phy_text)
    if m:
        out["pll"] = tuple(int(x) for x in m.groups())
    if dtsi_text is not None:
        m = re.search(r"samsung,esc-clock-frequency\s*=\s*<(\d+)>", dtsi_text)
        if m:
            out["esc_req_mhz"] = int(m.group(1)) // 1000000
    return out


def main():
    log_text = read(LOG)
    phy_text = read(PHY)
    dtsi_text = read(DTSI)
    if log_text is None or phy_text is None:
        print("check-dphy-timing: brak logu S-Boota albo pliku PHY, nie mam "
              "czego porownac")
        return 2

    lg = parse_log(log_text)
    sr = parse_series(phy_text, dtsi_text)

    # Bez tych kluczy pomiar jest niepelny: to nie jest zielone, to nieuruchomione.
    must_log = ("evt", "bps", "pll", "clk_prepare", "b_dphyctl", "esc_req_mhz",
                "esc_div", "esc_mhz")
    must_sr = ("bps", "pll", "clk_prepare", "ulps_exit", "esc_req_mhz")
    braki = [k for k in must_log if k not in lg] + \
            [("series:" + k) for k in must_sr if k not in sr]
    if braki:
        print("check-dphy-timing: pomiar niepelny, brakuje: %s" %
              ", ".join(braki))
        return 2

    bad = []

    # Rewizja krzemu (HW-11): cokolwiek nie-EVT0 znosi warunkowe zapisy producenta.
    if lg["evt"].startswith("0"):
        bad.append("rewizja krzemu %s to EVT0, a seria zapisuje PLL_CON8/"
                   "MC_ANA_CON2 bezwarunkowo" % lg["evt"])

    # Dziesiec licznikow D-PHY plus b_dphyctl (HW-01).
    pary = [
        ("clk_prepare", "clk_prepare"), ("clk_zero", "clk_zero"),
        ("clk_post", "clk_post"), ("clk_trail", "clk_trail"),
        ("hs_prepare", "hs_prepare"), ("hs_zero", "hs_zero"),
        ("hs_trail", "hs_trail"), ("lpx", "lpx"), ("hs_exit", "hs_exit"),
        ("b_dphyctl", "ulps_exit"),
    ]
    for lkey, skey in pary:
        if lkey in lg and skey in sr and lg[lkey] != sr[skey]:
            bad.append("%s: S-Boot %d, seria %d" % (lkey, lg[lkey], sr[skey]))

    # PLL i etykieta lacza (HW-02).
    if lg["pll"] != sr["pll"]:
        bad.append("PLL p/m/s/k: S-Boot %s, seria %s" % (lg["pll"], sr["pll"]))
    if lg["bps"] != sr["bps"]:
        bad.append("bps: S-Boot %d, seria %d" % (lg["bps"], sr["bps"]))

    # Lancuch escape (HW-03): zadanie zgodne, a dzielnik daje deklarowany wynik.
    if lg["esc_req_mhz"] != sr["esc_req_mhz"]:
        bad.append("escape zadany: S-Boot %d MHz, DT %d MHz" %
                   (lg["esc_req_mhz"], sr["esc_req_mhz"]))
    # word_clk / dzielnik ma dac zaokraglony w dol wynik z logu.
    if "word_mhz" in lg and lg["esc_div"]:
        wyliczony = lg["word_mhz"] // lg["esc_div"]
        if wyliczony != lg["esc_mhz"]:
            bad.append("escape: %d MHz / %d != %d MHz z logu" %
                       (lg["word_mhz"], lg["esc_div"], lg["esc_mhz"]))
    # b_dphyctl serii musi byc wpisem tablicy dla wlasnie tego escape.
    # 0x1c2 = wpis dla 18 MHz; jesli log mowi 18, a seria ma 0x1c2, zgadza sie.
    if lg.get("esc_mhz") == 18 and sr.get("ulps_exit") != 0x1c2:
        bad.append("escape 18 MHz w logu, a b_dphyctl serii to 0x%x, nie 0x1c2"
                   % sr.get("ulps_exit", 0))

    for b in bad:
        print("  FAIL %s" % b)
    print("check-dphy-timing: rewizja EVT%s, licznikow D-PHY 10, PLL 1, "
          "escape 1, rozjazdow %d" % (lg["evt"], len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
