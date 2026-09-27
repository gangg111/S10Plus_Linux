#!/usr/bin/env python3
"""Sekwencja hosta UFS w JADRZE wobec warstwy CAL producenta.

Blizniacza bramka do `check-ufs-host-cal.py`. Tamta pilnuje sterownika
bootloadera, ktory trzyma warstwy hosta jako TABLICE. Jadro ich nie ma:
mainline nie zna zadnej struktury tego rodzaju, wiec te same zapisy sa
w wariancie 9820 jawnymi wywolaniami w hakach. Dlatego bramka nie moze
porownywac wpis po wpisie wedlug cytatu, tak jak tamta, i porownuje ZBIORY
par (atrybut, wartosc, rodzaj).

Swiadoma decyzja: do kodu jadra NIE wstawiamy cytatow linii pliku producenta.
W sterowniku bootloadera maja sens, bo tam tablica jest przepisem linia po
linii. Tutaj kod idzie na liste mailingowa, gdzie odsylacz `/* :229 */` do
pliku, ktorego nikt poza tym projektem nie ma, nic nie znaczy. Cena jest taka,
ze bramka nie powie "linia 236 sie rozjechala", tylko "tego zapisu nie ma
u producenta" albo "tego zapisu producenta nie ma w sterowniku". Na literowke
w numerze rejestru albo w wartosci to wystarczy, a o to tu chodzi.

Zrodlem jest DRZEWO ROBOCZE, nie patch. Sterownik hosta jest plikiem, ktory
istnial wczesniej i dotyka go kilka patchy serii, wiec z samych dodanych linii
nie da sie odtworzyc jego tresci; jedna z porownywanych funkcji w ogole nie
zostala dodana, tylko przemianowana. Bramka [1] `scripts/verify.sh` osobno
pilnuje, ze drzewo robocze jest dokladnie tym, co daje seria, wiec czytanie
drzewa nie jest luka.

Co jest sprawdzane:

  poprawnosc   kazdy zapis sterownika ma swoj wiersz u producenta: ten sam
               adres, ta sama wartosc i ten sam rodzaj. Rodzaje, ktorych
               wartosc jest LICZONA z czestotliwosci zegara, porownuje sie bez
               wartosci, bo u producenta stoi tam atrapa;

  kompletnosc  kazdy wiersz producenta nalezacy do warstw hosta i dotyczacy
               naszej plyty musi byc zapisany. To wazniejsza polowa: sama
               zgodnosc tego, co jest, nie lapie GUBIENIA linii.

Kody wyjscia: 0 zgodne, 1 rozjazd, 2 bramka NIE URUCHOMIONA (brak zrodel).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ufs_cal

GATE = "check-ufs-host-kernel"
ROOT = Path(__file__).resolve().parent.parent
LINUX = ROOT / "sources/linux"
DRIVER = LINUX / "drivers/ufs/host/ufs-exynos.c"
HEADERS = (
    LINUX / "include/ufs/unipro.h",
    LINUX / "drivers/ufs/host/ufs-exynos.h",
    DRIVER,
)

# Funkcja sterownika -> tablica producenta, ktora odtwarza.
FUNCTIONS = {
    "exynos9820_ufs_pre_link": "init_cfg_evt1",
    "exynos9820_ufs_pre_phy_cal": "post_init_cfg_evt1_g3",
    "exynos9820_ufs_post_link": "post_init_cfg_evt1_g3",
    "exynos_ufs_set_pwr_mode_timers": "calib_of_hs_rate_b",
}

# Tablice producenta, ktore musza byc pokryte w calosci.
TABLES = ("init_cfg_evt1", "post_init_cfg_evt1_g3", "calib_of_hs_rate_b",
          "post_calib_of_hs_rate_b")

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

# Rodzaje, ktorych wartosc liczy kod z czestotliwosci zegara UniPro; u
# producenta pole wartosci jest dla nich atrapa, wiec porownuje sie sam adres.
COMPUTED = {"DME_RX_PRD", "DME_TX_PRD", "DME_RX_LR", "DME_TX_LR", "UNIPRO_PRD",
            "ADAPT_LEN"}

# Nasza plyta pracuje w trybie szybkim, wiec wpisy wspolne i szybkie ida.
PMD_OURS = {"PMD_ALL", "PMD_HS"}

# Wartosci, ktore nie sa stala preprocesora, tylko wyliczeniem. Trzymane tutaj
# jawnie, zeby bramka nie musiala parsowac enumow.
ENUMS = {"CPORT_CONNECTED": 1}

DEFINE_RX = re.compile(r"^#define\s+([A-Z][A-Z0-9_]*)\s+(0x[0-9a-fA-F]+|\d+)\s*$")


def fail(msg):
    ufs_cal.fail(GATE, msg)


def build_names():
    """Mapa nazwa -> liczba, zebrana z naglowkow, ktorych uzywa sterownik."""
    out = dict(ENUMS)
    for path in HEADERS:
        if not path.is_file():
            ufs_cal.skip(GATE, "brak %s" % path.name)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            hit = DEFINE_RX.match(line)
            if hit and hit.group(1) not in out:
                out[hit.group(1)] = int(hit.group(2), 0)
    return out


def value_of(names, text):
    text = text.strip()
    if text in names:
        return names[text]
    try:
        return int(text, 0)
    except ValueError:
        return None


def function_body(text, name):
    start = text.find("\nstatic int %s(" % name)
    if start < 0:
        fail("w sterowniku nie ma funkcji %s" % name)
    end = text.find("\n}\n", start)
    if end < 0:
        fail("nie znalazlem konca funkcji %s" % name)
    return text[start:end]


def statements(body):
    """Cialo funkcji pociete na instrukcje.

    Wywolania lamia sie na dwie i trzy linie, wiec parser liniowy widzialby
    polowe z nich bez nawiasu zamykajacego i po cichu je pomijal. Dlatego
    ciecie idzie po sredniku, a nie po koncu linii.
    """
    plaski = re.sub(r"\s+", " ", body)
    return [s.strip() + ";" for s in plaski.split(";") if s.strip()]


def parse_function(names, text, name):
    """Zwraca liste (adres, wartosc_albo_None, rodzaj, zrodlo)."""
    out = []
    lane = None
    lr_pending = {}

    for line in statements(function_body(text, name)):
        # Pas bierze sie z ostatniej napotkanej petli. Wystarczy, bo rodzaj
        # zalezny od pasa maja wylacznie zapisy z UIC_ARG_MIB_SEL, a te stoja
        # zawsze wewnatrz takiej petli.
        if "for_each_ufs_rx_lane" in line:
            lane = "RX"
        elif "for_each_ufs_tx_lane" in line:
            lane = "TX"

        hit = re.search(r"exynos_ufs_(enable|disable)_dbg_mode\(hba\)", line)
        if hit:
            out.append((names["PA_DBG_MODE"],
                        1 if hit.group(1) == "enable" else 0, "DME", line))
            continue

        hit = re.search(r"exynos9820_ufs_set_adapt_length\(ufs,\s*([^)]+)\)", line)
        if hit:
            addr = value_of(names, hit.group(1))
            if addr is None:
                fail("nie umiem rozwiazac adresu %s w %s" % (hit.group(1), name))
            out.append((addr, None, "ADAPT_LEN", line))
            continue

        hit = re.search(r"unipro_writel\(ufs,\s*(.+?),\s*([A-Z][A-Z0-9_]*)\)", line)
        if hit:
            addr = value_of(names, hit.group(2))
            if addr is None:
                fail("nie umiem rozwiazac rejestru %s w %s" % (hit.group(2), name))
            val = value_of(names, hit.group(1))
            out.append((addr, val, "UNIPRO_PRD" if val is None else "UNIPRO",
                        line))
            continue

        hit = re.search(r"UIC_ARG_MIB(_SEL)?\(\s*([A-Za-z0-9_]+)\s*(?:,[^)]*)?\)"
                        r"\s*,\s*(.+?)\)\s*;", line)
        if not hit:
            continue

        nazwa = hit.group(2)
        addr = value_of(names, nazwa)
        if addr is None:
            fail("nie umiem rozwiazac atrybutu %s w %s" % (nazwa, name))
        val = value_of(names, hit.group(3))

        if "LINERESET" in nazwa:
            # Producent ma na to jeden wiersz, pod adresem najnizszego z trzech
            # bajtow; sterownik pisze wszystkie trzy.
            kind = "DME_%s_LR" % lane
            lr_pending.setdefault(kind, []).append(addr)
            continue

        if val is None:
            # Jedyna wartosc, ktorej nie da sie policzyc, to okres zegara.
            if hit.group(3).strip() != "clk_period":
                fail("%s: nieznana wartosc %s przy atrybucie %s"
                     % (name, hit.group(3).strip(), nazwa))
            kind = "DME_%s_PRD" % lane
        elif hit.group(1):
            kind = "DME_%s" % lane
        else:
            kind = "DME"

        out.append((addr, val, kind, line))

    for kind, addrs in lr_pending.items():
        if len(addrs) != 3 or sorted(addrs) != list(range(min(addrs),
                                                          min(addrs) + 3)):
            fail("%s: %s pisze %d bajtow pod adresami %s, oczekiwano trzech "
                 "kolejnych" % (name, kind, len(addrs),
                                ", ".join(hex(a) for a in sorted(addrs))))
        out.append((min(addrs), None, kind, "%s (trzy bajty)" % kind))

    return out


def main():
    if not ufs_cal.sources_present():
        ufs_cal.skip(GATE, "brak zrodel producenta w sources/ds, "
                           "uruchom scripts/fetch-sources.sh")
    if not DRIVER.is_file():
        ufs_cal.skip(GATE, "brak %s" % DRIVER.name)

    names = build_names()
    text = DRIVER.read_text(encoding="utf-8", errors="replace")
    ven = ufs_cal.parse_vendor_tables(GATE, ufs_cal.vendor_text())

    for tab in TABLES:
        if tab not in ven:
            fail("producent nie ma tablicy %s" % tab)

    nasze = {}
    for func, tab in FUNCTIONS.items():
        for addr, val, kind, src in parse_function(names, text, func):
            nasze.setdefault(tab, []).append((addr, val, kind, src, func))

    ich = {}
    for tab in TABLES:
        for no, addr, val, pmd, layer, board in ven[tab]:
            if layer not in HOST_LAYERS or not ufs_cal.applies_to_board(board):
                continue
            if pmd not in PMD_OURS:
                fail("tablica %s, linia %d ma maske trybu %s, ktorej bramka nie "
                     "zna, dopisz ja do PMD_OURS razem z uzasadnieniem"
                     % (tab, no, pmd))
            kind = HOST_LAYERS[layer]
            ich.setdefault(tab, []).append(
                (addr, None if kind in COMPUTED else val, kind, no))

    sprawdzone = 0
    for tab in TABLES:
        moje = nasze.get(tab, [])
        theirs = ich.get(tab, [])

        klucz_ich = {}
        for addr, val, kind, no in theirs:
            klucz_ich.setdefault((addr, val, kind), []).append(no)

        pokryte = set()
        for addr, val, kind, src, func in moje:
            szukane = (addr, None if kind in COMPUTED else val, kind)
            if szukane not in klucz_ich or not klucz_ich[szukane]:
                fail("%s (%s): zapis 0x%x = %s rodzaju %s nie ma odpowiednika "
                     "w tablicy %s producenta\n  %s"
                     % (func, tab, addr,
                        "liczony" if val is None else hex(val), kind, tab, src))
            pokryte.add(klucz_ich[szukane].pop(0))
            sprawdzone += 1

        brakuje = [no for reszta in klucz_ich.values() for no in reszta]
        if brakuje:
            cal_lines = ufs_cal.vendor_text().splitlines()
            detail = "\n".join("    ufs-cal-9820.c:%d  %s"
                               % (no, cal_lines[no - 1].strip())
                               for no in sorted(brakuje))
            fail("tablica %s: %d wierszy producenta nie ma w sterowniku:\n%s"
                 % (tab, len(brakuje), detail))

    print("%s: wpisow zgodnych z producentem %d, tablic %d, funkcji %d"
          % (GATE, sprawdzone, len(TABLES), len(FUNCTIONS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
