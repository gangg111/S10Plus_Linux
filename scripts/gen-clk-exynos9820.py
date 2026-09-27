#!/usr/bin/env python3
"""Generuje sterownik zegarow Exynos9820 i jego binding z tablic CAL producenta.

Sterownik zegarow jest transkrypcja `cmucal-sfr.c` i `cmucal-node.c` do slownika
makr mainline.  Skoro tak, to niech BEDZIE transkrypcja: ten skrypt czyta obie
tablice przez scripts/cmucal-model.py i wypisuje gotowe pliki, zamiast zeby
ktokolwiek przepisywal 2800 linii recznie.  Dzieki temu kazda liczba w wyniku ma
zrodlo w pliku producenta, a nie w innym porcie.

Co jest wyprowadzone MECHANICZNIE z tablic producenta:
  offsety rejestrow, przesuniecia i szerokosci pol, numery bitow bramek,
  rodzice, wejscia muxow, czestotliwosci oscylatorow i przekladnie dzielnikow
  stalych, podzial na bloki CMU, nazwy i identyfikatory.

Co jest DECYZJA INZYNIERSKA, opisana ponizej przy odpowiedniej tablicy:
  ktore bloki prowadzimy, ktore zegary dostaja CLK_IS_CRITICAL, ktore
  CLK_IGNORE_UNUSED, ktore sciezki maja propagowac zadanie czestotliwosci
  i ktora droga rejestracji idzie dany blok.  Zadnej z tych rzeczy nie ma
  w tablicach CAL i zadna nie jest zweryfikowana na sprzecie.

Uzycie:
  scripts/gen-clk-exynos9820.py                     # statystyka
  scripts/gen-clk-exynos9820.py --blok CMU_PERIS    # podglad jednego bloku
  scripts/gen-clk-exynos9820.py --zapisz            # wpisz oba pliki do drzewa
  scripts/gen-clk-exynos9820.py --naglowek A --sterownik B
"""
import importlib.util
import io
import os
import sys

NL = chr(10)
T = chr(9)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_spec = importlib.util.spec_from_file_location(
    "cmucal_model", os.path.join(ROOT, "scripts", "cmucal-model.py"))
CAL = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CAL)

# Bloki, ktore prowadzimy, w kolejnosci wystepowania w sterowniku.
#
# (blok CAL, przyrostek compatible, zegar wejsciowy z DT, rejestracja, domena)
#
# rejestracja: "wczesna" znaczy CLK_OF_DECLARE, bo blok jest potrzebny zanim
# ruszy sterownik platformy; "platforma" znaczy wpis w of_device_id.
# domena: True, gdy blok siedzi w przelaczalnej domenie zasilania, czyli traci
# rejestry i nie wolno mu przypinac zegarow na sztywno.
BLOKI = [
    ("CMU_PERIS", "peris", "bus", "wczesna", False),
    ("CMU_PERIC0", "peric0", "bus", "platforma", False),
    ("CMU_PERIC1", "peric1", "bus", "platforma", False),
    ("CMU_FSYS0A", "fsys0a", "bus", "platforma", False),
    ("CMU_FSYS1", "fsys1", "bus", "platforma", False),
    ("CMU_APM", "apm", "bus", "platforma", False),
    ("CMU_CMGP", "cmgp", "bus", "platforma", False),
    ("CMU_DPU", "dpu", "bus", "platforma", True),
    # Domena AUD istnieje (PMU 0x1900), ale blok idzie na razie bez niej:
    # bootloader zostawia ja wlaczona, a jedynym odbiorca jest dzis modul
    # spoza drzewa, ktory nie trzyma zadnego zegara, wiec runtime PM zdjalby
    # domene zaraz po starcie.
    ("CMU_AUD", "aud", "cpu", "platforma", False),
    ("CMU_CMU", "top", None, "wczesna", False),
]

# Powody wczesnej rejestracji, wypisywane do sterownika jako komentarz.
POWOD_WCZESNEJ = {
    "CMU_PERIS": "Register CMU_PERIS early, as it's needed for the MCT timer",
    "CMU_CMU": "Register CMU_TOP early, as every other CMU takes its input"
               " clock from it",
}

# Zegar odniesienia calego SoC.  W tablicach producenta kazdy blok ma wlasny
# alias OSCCLK_<BLOK> o tej samej czestotliwosci, w drzewie urzadzen jest to
# jeden zegar wejsciowy.
# Czestotliwosci PLL-i, ktorych rejestrow NIE DA SIE przeczytac.
#
# Okno PLL w CMU_TOP jest zamkniete: odczyt konczy sie synchronicznym abortem
# zewnetrznym (esr 0x96000010, far 0x1a24010c dla apll_shared0). Zmierzone
# w bootloaderze 19.09.2026 i potwierdzone panika jadra 21.09.2026, za kazdym
# razem na PIERWSZYM czytanym rejestrze PLL. Okna muxow, dzielnikow i bramek
# tego samego bloku czytaja sie normalnie, wiec zamkniete jest samo okno PLL.
#
# Rejestracja przez PLL() zawsze konczy sie odczytem, bo rdzen wola
# recalc_rate, zeby poznac czestotliwosc poczatkowa. Dlatego te zegary ida
# jako stale czestotliwosci, a nie jako PLL-e.
#
# Wartosci z tablic CAL producenta (sources/ds/cmucal-node.c), gdzie kazdy
# z tych PLL-i ma dokladnie jeden wpis, czyli sa to stale konstrukcyjne.
# Sprawdzone wobec oscylatora 26 MHz i zgodne z naszym bootloaderem, ktory
# z tymi liczbami na tym telefonie startuje.
PLL_STALE = {
    "fout_apll_shared0": 2132000000,   # 26 MHz * 82
    "fout_apll_shared1": 1865500032,   # 26 MHz * 287 / 4
    "fout_pll_g3d":       650000000,   # jedyny z dwoma wpisami, bierzemy wyzszy
    "fout_pll_shared0":  2132000000,   # 26 MHz * 328 / 4
    "fout_pll_shared1":  1865500032,   # 26 MHz * 287 / 4
    "fout_pll_shared2":   800000000,
    "fout_pll_shared3":   640000000,
    "fout_pll_shared4":   666000000,   # 26 MHz * 333 / 13
    "fout_pll_mmc":        26000000,   # PLL w obejsciu, wprost z oscylatora
    # PLL-e bloku audio czytaja sie (CON0-CON4, odczyt CON5 konczy sie
    # abortem), ale ida tak samo, bo mainline pll0831x bierze K spod
    # con_reg + 8, a tu K lezy w CON3 = CON0 + 0xc.  Tablica producenta dla
    # PLL_AUD0 ma wylacznie wpisy 1179,648 MHz +-840 ppb (korekta dryfu),
    # czyli czestotliwosc jest stala konstrukcyjnie; wartosc zmierzona na
    # telefonie po bootloaderze: M 45, P 1, S 0, K 0x5eff z 26 MHz
    # (measurements/2026-09-25-dzwiek).  PLL_AUD1 bootloader zostawia
    # wylaczony (CON0 = 0), wiec nie udaje czestotliwosci z tablicy.
    "fout_pll_aud0":     1179648010,   # 26 MHz * (45 + 24319/65536)
    "fout_pll_aud1":              0,   # wylaczony
}


OSCYLATOR = "oscclk"
CZESTOTLIWOSC_OSCYLATORA = 26000000

# Producent literowal sie w jednej nazwie rejestru: cmucal-sfr.c:299 nazywa mux
# uzytkownika PERIC0 USI13 "USE13", chociaz wezel w cmucal-node.c i wszystkie
# pozostale rejestry tego bloku pisza "USI13".  Offset jest poprawny, wiec do
# sterownika idzie nazwa poprawna, a nie literowka.  To samo przekierowanie robi
# scripts/check-cmu.py, zeby bramka nadal umiala odnalezc wpis producenta.
POPRAWKI_REJESTROW = {
    "PLL_CON0_MUX_CLKCMU_PERIC0_USE13_USI_USER":
        "PLL_CON0_MUX_CLKCMU_PERIC0_USI13_USI_USER",
}

# Zegary, ktorych wygaszenie odcina procesor od rejestrow bloku.  Lista jest
# WASKA i celowo trzyma sie tego, co robi mainline: sam PCLK kontrolera zegarow
# bloku, porty magistrali i kontroler przerwan (clk-exynos990.c:1273, 1338,
# 1637, 1653, 2195, 2223, 2601 to komplet siedmiu wystapien w tamtym pliku).
# Blok w przelaczalnej domenie zasilania nie dostaje ich w ogole, bo zegar
# krytyczny nie pozwolilby domenie zejsc.
KRYTYCZNE = [
    ("_CMU_", "PCLK samego kontrolera zegarow bloku"),
    ("LHM_AXI_", "port magistrali od strony mastera"),
    ("LHS_", "port magistrali od strony slave"),
    ("_GIC_", "kontroler przerwan"),
]

# Zegary, ktorych nie wolno wygasic przy starcie, ale ktore moga byc pozniej
# sterowane normalnie.  clk_disable_unused wygasza wszystko, czego nikt nie
# zajal, a te zegary maja odbiorcow, ktorych mainline jeszcze nie prowadzi.
# Mainline uzywa do tego CLK_IGNORE_UNUSED (clk-exynos990.c:1024-1053, 1148,
# 1289; clk-exynos850.c ma 24 takie wpisy, clk-gs101.c 18).
IGNORUJ_NIEUZYWANE = [
    ("SYSMMU_", "jednostka MMU peryferium, wlacza ja sterownik iommu"),
    ("GPIO_", "bank wyprowadzen, jego rejestry czyta pinctrl"),
    ("PPMU_", "licznik ruchu na magistrali"),
    ("BTM_", "monitor ruchu na magistrali"),
    ("PUF_", "zrodlo klucza sprzetowego"),
    ("VGEN_", "generator znacznikow ruchu na magistrali"),
    ("TMU_", "czujnik temperatury, bez niego nie ma dlawienia"),
    ("D_TZPC_", "kontrola stref bezpieczenstwa"),
    ("MCT_", "licznik systemowy, zrodlo czasu"),
    ("SYSREG_", "rejestry systemowe bloku"),
    ("_BUSD_", "magistrala danych bloku"),
    ("_BUSP_", "magistrala peryferiow bloku"),
    ("_OSCCLK_", "rozprowadzenie oscylatora wewnatrz bloku"),
    ("AD_AXI_", "most adresowy do magistrali bloku"),
    ("AXI2APB_", "most AXI na APB, za nim stoja rejestry peryferiow"),
    ("XIU_", "przelacznica wewnetrzna bloku"),
]

# Bloki, ktorych KAZDA bramka dostaje CLK_IGNORE_UNUSED.
IGNORUJ_CALE_BLOKI = {
    "CMU_CMU": "CMU_TOP rozdaje zegary do blokow, ktorych mainline jeszcze nie"
               " prowadzi, wiec nikt ich tu nie zajmuje",
    "CMU_APM": "blok always-on: PMU, RTC i skrzynki do modemu oraz VTS chodza"
               " bez sterownikow po stronie mainline",
    "CMU_AUD": "ABOX prowadzi na razie modul spoza drzewa, ktory nie trzyma"
               " zegarow; wygaszona bramka ACLK wiesza kazdy dostep do bloku",
}

# Sciezki, na ktorych odbiorca realnie ustawia czestotliwosc: port szeregowy
# i magistrale I2C/SPI zbudowane na USI.  Tam mux uzytkownika idzie jako nMUX
# (wolno przepiac miedzy oscylatorem a wyjsciem CMU), dzielnik jako DIV_F
# z CLK_SET_RATE_PARENT, a bramka-lisc tez z CLK_SET_RATE_PARENT, bo to ona
# stoi w drzewie urzadzen.  Wzorzec: clk-exynos990.c:1554-1597 (commit
# e11560b050ce, "Fix PERIC0/1 USI clock types") i clk-exynos850.c:1079.
SCIEZKI_ZMIENNEJ_CZESTOTLIWOSCI = ("USI", "UART", "I2C")

# Dwie pary wezlow, ktorych mechaniczna regula nie rozroznia: producent ma
# osobno MUX_CMU_CMUREF i MUX_CLK_CMU_CMUREF, a zdjecie przedrostka rodzaju
# daje z obu to samo.  Ta sama para stoi w clk-exynos990.c (linie 693-696
# i 859-864), wiec bierzemy stamtad nazwy zamiast wymyslac wlasne.
POPRAWKI_NAZW = {
    "MUX_CLK_CMU_CMUREF": "mout_cmu_clk_cmuref",
    "DIV_CLK_CMU_CMUREF": "dout_cmu_clk_cmuref",
    # Literowka producenta: identyfikator wezla mowi USE13, a dzielnik, obie
    # bramki i sam rejestr, ktory ten mux obsluguje, mowia USI13
    # (cmucal-node.c:1209 wobec :1369, :2590, :2596).  Nazwa zegara i makro
    # id sa czescia ABI, wiec literowka nie moze przejsc do naglowka.
    "MUX_CLKCMU_PERIC0_USE13_USI_USER": "mout_peric0_usi13_usi_user",
}

# Komplet blokow, niezalezny od --bez: naglowek bindingu opisuje zawsze
# wszystkie, zeby identyfikatory byly te same w kazdym patchu serii.
PELNE_BLOKI = list(BLOKI)

RANGA = {"pll": 0, "frate": 1, "mux": 2, "div": 3, "ffactor": 4, "gate": 5}


def krotka_nazwa_bloku(blok):
    return blok[len("CMU_"):]


def bez_prefiksu(s, prefiksy):
    for p in prefiksy:
        if s.startswith(p):
            return s[len(p):]
    return s


def na_sciezce_czestotliwosci(vid):
    return any(w in vid for w in SCIEZKI_ZMIENNEJ_CZESTOTLIWOSCI)


def krytyczny(vid, blok, w_domenie):
    if w_domenie:
        return None
    for wzor, powod in KRYTYCZNE:
        if wzor in vid:
            return powod
    return None


def wlasny_pclk_cmu(vid, blok):
    """Czy to bramka zegara APB SAMEGO kontrolera zegarow tego bloku.

    Ksztalt identyfikatora producenta: ..._<BLOK>_CMU_<BLOK>_IPCLKPORT_PCLK.
    Ten zegar jest wyjatkowy, bo jego odbiorca to nie peryferium opisane
    w drzewie urzadzen, tylko ten sterownik: bez niego rejestry CMU sa
    niedostepne, a sciezka runtime PM zapisuje je i odtwarza przy kazdym
    wejsciu i wyjsciu domeny zasilania. Zaden wezel DT go nie zada, wiec
    clk_disable_unused zgasilby go w late_initcall_sync.
    """
    krotki = blok[len("CMU_"):] if blok.startswith("CMU_") else blok
    return vid.endswith("_%s_CMU_%s_IPCLKPORT_PCLK" % (krotki, krotki))


def ignorowany(vid, blok):
    if blok in IGNORUJ_CALE_BLOKI:
        return IGNORUJ_CALE_BLOKI[blok]
    if wlasny_pclk_cmu(vid, blok):
        return ("zegar APB samego kontrolera; nie ma go w drzewie urzadzen,"
                " a sterownik siega przez niego do rejestrow CMU przy kazdym"
                " wejsciu i wyjsciu domeny zasilania")
    for wzor, powod in IGNORUJ_NIEUZYWANE:
        if wzor in vid:
            return powod
    return None


# ------------------------------------------------------------------ nazwy
#
# Nazwa idzie z KSZTALTU identyfikatora producenta, nie z bloku, w ktorym lezy
# rejestr.  CLKCMU w nazwie znaczy "zegar rozdzielany przez kontroler do innych
# blokow" i dostaje wrostek _cmu_ niezaleznie od tego, czy rejestr stoi
# w CMU_TOP, czy w CMU_APM.  Przyrostek _USER znaczy "mux wejsciowy po stronie
# odbiorcy".  Reszta to reguly z clk-gs101.c, jedynego sterownika w drzewie
# wygenerowanego z tych samych tablic Samsunga.


def nazwa_mux(vid, rejestr):
    """O wrostku _cmu_ decyduje REJESTR, a nie sam identyfikator wezla.

    Producent uzywa tego samego ksztaltu identyfikatora po obu stronach:
    MUX_CLKCMU_PERIC0_UART_DBG to mux po stronie ODBIORCY (rejestr PLL_CON0_
    w CMU_PERIC0), a MUX_CLKCMU_MISC_BUS to mux ROZDZIELAJACY w kontrolerze
    (rejestr CLK_CON_MUX_).  Tylko ten drugi dostaje mout_cmu_.  Regula stoi
    wprost w komentarzu clk-gs101.c.
    """
    baza = bez_prefiksu(vid, ("MUX_CLKCMU_", "MUX_CLKMUX_", "MUX_CLK_",
                              "CLKMUX_", "MUX_")).lower()
    if rejestr.startswith("CLK_CON_MUX_"):
        return "mout_cmu_" + baza if "CLKCMU_" in vid else "mout_" + baza
    return "mout_" + baza


def nazwa_div(vid):
    r = bez_prefiksu(vid, ("DIV_CLKCMU_", "CLKCMU_"))
    if r != vid:
        return "dout_cmu_" + r.lower()
    return "dout_" + bez_prefiksu(vid, ("DIV_CLK_", "DIV_")).lower()


def nazwa_gate(vid, blok):
    """GOUT_BLK_PERIS_UID_MCT_IPCLKPORT_PCLK -> gout_peris_mct_pclk

    Regula spisana w clk-gs101.c: dla bramek zdejmujemy _BLK, _UID,
    _IPCLKPORT i RSTNSYNC_, i nic wiecej.
    """
    krotki = krotka_nazwa_bloku(blok)
    r = bez_prefiksu(vid, ("GOUT_BLK_", "CLK_BLK_", "GATE_"))
    if r.startswith(krotki + "_UID_"):
        r = r[len(krotki) + len("_UID_"):]
    r = r.replace("_IPCLKPORT", "")
    r = bez_prefiksu(r, ("RSTNSYNC_",))
    if r.startswith("CLKCMU_"):
        return "gout_cmu_" + r[len("CLKCMU_"):].lower()
    return "gout_%s_%s" % (krotki.lower(), r.lower())


def nazwa_pll(vid):
    """PLL_SHARED0 -> fout_pll_shared0, APLL_SHARED0 -> fout_apll_shared0.

    Identyfikator idzie w calosci, bo "PLL" jest tu czescia nazwy zegara,
    a nie oznaczeniem rodzaju wezla.
    """
    return "fout_" + vid.lower()


def nazwa_frate(vid):
    return bez_prefiksu(vid, ("CLK_",)).lower()


def ident(nazwa):
    return "CLK_" + nazwa.upper()


def nazwa_wezla(w, blok, rejestr=""):
    if w["id"] in POPRAWKI_NAZW:
        return POPRAWKI_NAZW[w["id"]]
    r = w["rodzaj"]
    if r == "mux":
        return nazwa_mux(w["id"], rejestr)
    if r in ("div", "ffactor"):
        return nazwa_div(w["id"])
    if r == "pll":
        return nazwa_pll(w["id"])
    if r == "frate":
        return nazwa_frate(w["id"])
    return nazwa_gate(w["id"], blok)


# ------------------------------------------------------------------ model


def glowny_oscylator(w):
    """Czy ten wezel FIXEDRATE to po prostu oscylator SoC widziany z bloku."""
    return (w["id"].startswith("OSCCLK_")
            and "RCO" not in w["id"]
            and w.get("czestotliwosc") == CZESTOTLIWOSC_OSCYLATORA)


def nieprogramowalne(model):
    """Muxy, ktorym producent nie daje pola wyboru: EMPTY_CAL_ID zamiast pola.

    Rejestr taki mux ma (CLK_CON_MUX_MUX_CLK_PERIS_GIC stoi w cmucal-sfr.c:348),
    ale tablice opisuja przy nim tylko pola BUSY i automatycznego bramkowania,
    bez pola wyboru. Sterownik nie ma wiec czego czytac ani pisac, wiec go nie
    rejestrujemy, a odbiorcow podpinamy pod PIERWSZE wejscie.

    To jest zalozenie, nie fakt z tablic: ktore wejscie wybiera sprzet, nie
    wynika z niczego, co mamy. Stad adnotacja UNVERIFIED w naglowku pliku
    i pozycja w docs/HW-BLOCKED.md. Blokow, ktorych to dotyczy, sa dwa w calym
    SoC (MUX_CLK_PERIS_GIC i MUX_HCHGEN_CLK_AUD_CPU) i sterownik obejmuje oba.
    """
    out = {}
    for w in model["wezly"]:
        if w["rodzaj"] != "mux" or w.get("pole") != "EMPTY_CAL_ID":
            continue
        wejscia = model["rodzice"].get(w.get("rodzice"), [])
        if wejscia:
            out[w["id"]] = wejscia[0]
    return out


def rodzice_wezla(model, w):
    if w["rodzaj"] == "mux":
        return model["rodzice"].get(w.get("rodzice"), [])
    if w["rodzaj"] == "frate":
        return []
    return [w.get("rodzic", "")]


def rozwin(vid, pomijane):
    widziane = set()
    while vid in pomijane and vid not in widziane:
        widziane.add(vid)
        vid = pomijane[vid]
    return vid


def zbierz(model):
    """Wezly pogrupowane po bloku CMU, z rozwiazanym rejestrem.

    Wezly FIXEDRATE nie maja rejestru, wiec ida do bloku, ktory je konsumuje.
    Bez tego oscylatory RCO i DLL zniknelyby z modelu, a ich odbiorcy dostaliby
    podstawionego oscylatora SoC, co robi obecny port i co jest po prostu
    nieprawda.
    """
    pomijane = nieprogramowalne(model)
    prowadzone = set(b[0] for b in BLOKI)
    per = {}
    wg_id = {}
    for w in model["wezly"]:
        r = CAL.rozwiaz(model, w.get("pole") or w.get("enable"))
        if not r or r["blok"] not in prowadzone:
            continue
        per.setdefault(r["blok"], []).append((w, r))
        wg_id[w["id"]] = r["blok"]

    stale = dict((w["id"], w) for w in model["wezly"] if w["rodzaj"] == "frate")
    for blok in [b[0] for b in BLOKI]:
        for w, _ in list(per.get(blok, [])):
            for vid in rodzice_wezla(model, w):
                vid = rozwin(vid, pomijane)
                if vid in wg_id or vid not in stale:
                    continue
                if glowny_oscylator(stale[vid]):
                    continue
                per[blok].append((stale[vid], {"offset": 0, "shift": 0,
                                               "width": 0, "blok": blok}))
                wg_id[vid] = blok
    return per


def rejestry_wezla_surowe(w):
    """Nazwa rejestru wprost z identyfikatora pola producenta.

    Uzywana przy nazywaniu, gdzie liczy sie KSZTALT nazwy rejestru
    (PLL_CON0_ kontra CLK_CON_MUX_), a nie jej offset.
    """
    pole = w.get("pole") or w.get("enable") or ""
    for przyrostek in ("_SELECT", "_DIVRATIO", "_CG_VAL", "_ENABLE",
                       "_PLL_LOCK_TIME"):
        if pole.endswith(przyrostek):
            return pole[:-len(przyrostek)]
    return pole


def mapa_nazw(per):
    """Identyfikator producenta -> nazwa zegara w sterowniku.

    Kolizja nazw jest bledem generatora, nie rzecza do przemilczenia: dwa rozne
    rejestry pod jedna nazwa to zegar, ktorego nie da sie zaadresowac.
    """
    out = {}
    zajete = {}
    for blok, _, _, _, _ in BLOKI:
        for w, _ in per.get(blok, []):
            rej = rejestry_wezla_surowe(w)
            n = nazwa_wezla(w, blok, rej)
            if n in zajete and zajete[n] != w["id"]:
                raise SystemExit("kolizja nazw: %s <- %s oraz %s"
                                 % (n, zajete[n], w["id"]))
            zajete[n] = w["id"]
            out[w["id"]] = n
    return out


def rodzic_na_nazwe(vid, nazwy, pomijane):
    vid = rozwin(vid, pomijane)
    if vid in nazwy:
        return nazwy[vid]
    if vid.startswith("OSCCLK") or vid == "EMPTY_CAL_ID" or not vid:
        return OSCYLATOR
    raise SystemExit("rodzic bez nazwy: " + vid)


def uporzadkuj(wezly):
    """Kolejnosc w pliku i numeracja identyfikatorow.

    Deterministyczna i niezalezna od kolejnosci w tablicach producenta:
    najpierw rodzaj, potem offset rejestru, potem identyfikator.  Dzieki temu
    ponowne uruchomienie generatora daje bajt w bajt ten sam plik.
    """
    return sorted(wezly,
                  key=lambda x: (RANGA[x[0]["rodzaj"]], x[1]["offset"],
                                 x[0]["id"]))


def rejestry_wezla(model, w):
    """Nazwy rejestrow, ktorych dotyka wezel, w kolejnosci uzycia."""
    out = []
    for klucz in ("lock", "enable", "pole"):
        pole = model["pola"].get(w.get(klucz))
        if pole:
            n = pole["rejestr"]
            out.append((POPRAWKI_REJESTROW.get(n, n),
                        model["rejestry"][n]["offset"]))
    return out


# ------------------------------------------------------------------ emisja


def do_kolumny(tekst, kolumna):
    """Dociaga tekst tabulatorami do zadanej kolumny (tabulator co 8)."""
    dlugosc = len(tekst.expandtabs(8))
    if dlugosc >= kolumna:
        return tekst + T
    braki = (kolumna - dlugosc + 7) // 8
    return tekst + T * braki


def zawin(makro, argumenty, wciecie=T, szer=80):
    """Lamie wywolanie makra na kolumnie 80, wcinajac ciag dalszy pod nawias."""
    poczatek = wciecie + makro + "("
    # Ciag dalszy stoi pod nawiasem otwierajacym, ale tabulatorami tak daleko,
    # jak sie da: spacje na poczatku linii sa dla checkpatch bledem wciecia.
    kolumna = len(wciecie.expandtabs(8)) + len(makro) + 1
    ciag = T * (kolumna // 8) + " " * (kolumna % 8)
    linie = []
    biezaca = poczatek
    for i, a in enumerate(argumenty):
        kawalek = a + ("," if i < len(argumenty) - 1 else ")")
        laczik = " " if biezaca.rstrip().endswith(",") else ""
        proba = biezaca + laczik + kawalek
        if len(proba.expandtabs(8)) > szer and biezaca != poczatek:
            linie.append(biezaca)
            biezaca = ciag + kawalek
        else:
            biezaca = proba
    linie.append(biezaca)
    return NL.join(linie)


def emituj_pname(nazwa, rodzice, szer=80):
    naglowek = "PNAME(%s) = { " % nazwa
    # Ciag dalszy wyrownany pod pierwszy wpis, ale wciety TABULATORAMI:
    # checkpatch traktuje wiodace spacje jako blad wciecia.
    ciag = T * (len(naglowek) // 8) + " " * (len(naglowek) % 8)
    linie = []
    biezaca = naglowek
    for i, r in enumerate(rodzice):
        kawalek = '"%s"' % r + ("," if i < len(rodzice) - 1 else " };")
        laczik = " " if biezaca.rstrip().endswith(",") else ""
        proba = biezaca + laczik + kawalek
        if len(proba.expandtabs(8)) > szer and biezaca != naglowek:
            linie.append(biezaca)
            biezaca = ciag + kawalek
        else:
            biezaca = proba
    linie.append(biezaca)
    return NL.join(linie)


def tablice_rodzicow(model, blok, wezly, nazwy, pomijane):
    """Tablice PNAME dla muxow bloku, ze scaleniem identycznych list.

    Opiekun podsystemu zazadal tego wprost w commicie e11560b050ce
    ("Consolidate identical USI parent arrays"), wiec generator ma to robic
    z zalozenia, a nie dopiero po recenzji.
    """
    grupy = {}
    for w, _ in wezly:
        if w["rodzaj"] != "mux":
            continue
        klucz = tuple(rodzic_na_nazwe(x, nazwy, pomijane)
                      for x in rodzice_wezla(model, w))
        grupy.setdefault(klucz, []).append(nazwy[w["id"]])

    przypisanie = {}
    tablice = []
    uzyte = set()
    for klucz in sorted(grupy, key=lambda k: sorted(grupy[k])[0]):
        czlonkowie = sorted(grupy[klucz])
        # Grupa wspoldzielona bierze nazwe pierwszego swojego czlonka:
        # zadnych wymyslanych slow, a nazwy sa unikalne z definicji.
        nazwa = czlonkowie[0] + "_p"
        uzyte.add(nazwa)
        tablice.append((nazwa, list(klucz)))
        for c in czlonkowie:
            przypisanie[c] = nazwa
    return tablice, przypisanie


def flagi_bramki(vid, blok, w_domenie, rodzic):
    """Flagi bramki.  Propagacja czestotliwosci tylko przez zegar funkcyjny.

    Peryferium na USI ma dwie bramki: IPCLK, ktory wisi na wlasnym dzielniku
    i ktorego czestotliwosc odbiorca ustawia, oraz PCLK, ktory wisi na
    wspolnej magistrali bloku.  Gdyby CLK_SET_RATE_PARENT trafil na PCLK,
    zadanie czestotliwosci od jednego peryferium przestrajaloby magistrale
    calego bloku.  Stad warunek na RODZICU, a nie tylko na nazwie bramki.
    """
    if krytyczny(vid, blok, w_domenie):
        return "CLK_IS_CRITICAL"
    if na_sciezce_czestotliwosci(vid) and na_sciezce_czestotliwosci(
            rodzic.upper()):
        return "CLK_SET_RATE_PARENT"
    if ignorowany(vid, blok):
        return "CLK_IGNORE_UNUSED"
    return "0"


def emituj_blok(model, blok, przyrostek, zegar_dt, rejestracja, w_domenie,
                per, nazwy, pomijane):
    krotki = krotka_nazwa_bloku(blok)
    kod = przyrostek
    wezly = uporzadkuj(per.get(blok, []))
    baza = model["bloki"][blok]["baza"]

    out = []
    naglowek_sekcji = "/* ---- %s " % blok
    out.append(naglowek_sekcji + "-" * max(4, 78 - len(naglowek_sekcji) - 3)
               + " */")
    out.append("")
    out.append("/* Register offsets for %s (0x%08x) */" % (blok, baza))

    rejestry = {}
    for w, _ in wezly:
        for n, off in rejestry_wezla(model, w):
            rejestry.setdefault(n, off)
    kolejnosc = sorted(rejestry, key=lambda n: (rejestry[n], n))

    # Sterownik PLL rodziny samsung czyta M, P i S wprost z rejestru, na ktory
    # wskazuje con_offset, a te wspolczynniki leza w CON3, nie w CON0 (CON0 to
    # rejestr sterujacy).  Tablice CAL wymieniaja PLL_CON3_* tylko tam, gdzie
    # uklad uzywa dzielnika K, czyli dla trzech PLL-i z dziewieciu; te trzy
    # wpisy potwierdzaja regule mapy rejestrow tej rodziny, CON3 = CON0 + 0xc,
    # i z niej biora sie offsety dla pozostalych.  Gdzie producent podaje
    # offset, jest on brany wprost i tylko sprawdzany wobec reguly.
    # Pilnuje tego scripts/check-pll-con3.py.
    definicje = dict(rejestry)
    for w, _ in wezly:
        if w["rodzaj"] != "pll":
            continue
        con0 = model["pola"][w["enable"]]["rejestr"]
        con3 = con0.replace("PLL_CON0_", "PLL_CON3_", 1)
        if con3 == con0:
            sys.exit("%s: %s nie wyglada na rejestr sterujacy PLL"
                     % (blok, con0))
        liczony = rejestry[con0] + 0xc
        wpis = model["rejestry"].get(con3)
        if wpis and wpis["offset"] != liczony:
            sys.exit("%s: %s pod 0x%x, a %s pod 0x%x, roznica nie wynosi 0xc"
                     % (blok, con0, rejestry[con0], con3, wpis["offset"]))
        definicje[con3] = wpis["offset"] if wpis else liczony

    kolejnosc_def = sorted(definicje, key=lambda n: (definicje[n], n))
    szer = max([len(n) for n in kolejnosc_def] or [0])
    kolumna = ((8 + szer) // 8 + 1) * 8
    for n in kolejnosc_def:
        out.append(do_kolumny("#define " + n, kolumna)
                   + "0x%04x" % definicje[n])
    out.append("")

    out.append("static const unsigned long %s_clk_regs[] __initconst = {" % kod)
    for n in kolejnosc:
        out.append(T + n + ",")
    out.append("};")
    out.append("")

    rodzaje = {}
    for w, r in wezly:
        rodzaje.setdefault(w["rodzaj"], []).append((w, r))

    stale = []
    for w, _ in rodzaje.get("frate", []):
        n = nazwy[w["id"]]
        stale.append((n, w["czestotliwosc"], False))
    for w, _ in rodzaje.get("pll", []):
        n = nazwy[w["id"]]
        if n not in PLL_STALE:
            sys.exit("gen-clk: brak stalej czestotliwosci dla %s; okna PLL"
                     " nie da sie odczytac, wiec trzeba ja wziac z tablic"
                     " CAL producenta" % n)
        stale.append((n, PLL_STALE[n], True))

    if stale:
        out.append("/*")
        out.append(" * Clocks the vendor tables give a rate for but this SoC"
                   " gives no readable")
        out.append(" * register.  Two kinds sit here.  The on-chip"
                   " oscillators have no register")
        out.append(" * at all and cmucal-node.c carries them as FIXEDRATE"
                   " entries.  The PLLs do")
        out.append(" * have registers, but the window holding them answers"
                   " no read: every attempt")
        out.append(" * ends in a synchronous external abort, both from the"
                   " boot loader and from")
        out.append(" * here, always on the first one touched.  Registering"
                   " them as PLLs is not an")
        out.append(" * option either, because the core reads the register to"
                   " learn the starting")
        out.append(" * rate.  Their tables in cmucal-node.c hold exactly one"
                   " entry each, so these")
        out.append(" * are fixed by construction rather than tuned at"
                   " runtime.")
        out.append(" */")
        out.append("static const struct samsung_fixed_rate_clock"
                   " %s_fixed_clks[] __initconst = {" % kod)
        for n, hz, _ in stale:
            out.append(zawin("FRATE", [ident(n), '"%s"' % n, "NULL", "0",
                                       "%d" % hz]) + ",")
        out.append("};")
        out.append("")

    tablice, przypisanie = tablice_rodzicow(model, blok, wezly, nazwy, pomijane)
    if tablice:
        out.append("/* List of parent clocks for muxes in %s */" % blok)
        for nazwa, rodzice in tablice:
            out.append(emituj_pname(nazwa, rodzice))
        out.append("")

    if rodzaje.get("mux"):
        out.append("static const struct samsung_mux_clock %s_mux_clks[]"
                   " __initconst = {" % kod)
        for w, r in rodzaje["mux"]:
            n = nazwy[w["id"]]
            makro = "nMUX" if na_sciezce_czestotliwosci(w["id"]) else "MUX"
            rej = rejestry_wezla(model, w)[0][0]
            out.append(zawin(makro, [ident(n), '"%s"' % n, przypisanie[n], rej,
                                     str(r["shift"]), str(r["width"])]) + ",")
        out.append("};")
        out.append("")

    if rodzaje.get("div"):
        out.append("static const struct samsung_div_clock %s_div_clks[]"
                   " __initconst = {" % kod)
        for w, r in rodzaje["div"]:
            n = nazwy[w["id"]]
            rodzic = rodzic_na_nazwe(w.get("rodzic", ""), nazwy, pomijane)
            rej = rejestry_wezla(model, w)[0][0]
            args = [ident(n), '"%s"' % n, '"%s"' % rodzic, rej,
                    str(r["shift"]), str(r["width"])]
            if na_sciezce_czestotliwosci(w["id"]):
                out.append(zawin("DIV_F", args + ["CLK_SET_RATE_PARENT", "0"])
                           + ",")
            else:
                out.append(zawin("DIV", args) + ",")
        out.append("};")
        out.append("")

    if rodzaje.get("ffactor"):
        out.append("/*")
        out.append(" * Dividers with a fixed ratio: the vendor tables carry the"
                   " ratio as a")
        out.append(" * FIXEDFACTOR entry and give the register no DIVRATIO"
                   " field, so there is")
        out.append(" * nothing to program.  The stored value is what such a"
                   " field would hold,")
        out.append(" * hence a divider one larger; clk-gs101.c:1258 spells the"
                   " same /8 out.")
        out.append(" */")
        out.append("static const struct samsung_fixed_factor_clock"
                   " %s_fixed_factor_clks[] __initconst = {" % kod)
        for w, _ in rodzaje["ffactor"]:
            n = nazwy[w["id"]]
            rodzic = rodzic_na_nazwe(w.get("rodzic", ""), nazwy, pomijane)
            out.append(zawin("FFACTOR", [ident(n), '"%s"' % n, '"%s"' % rodzic,
                                         "1", str(w["ratio"] + 1), "0"]) + ",")
        out.append("};")
        out.append("")

    if rodzaje.get("gate"):
        out.append("static const struct samsung_gate_clock %s_gate_clks[]"
                   " __initconst = {" % kod)
        for w, r in rodzaje["gate"]:
            n = nazwy[w["id"]]
            rodzic = rodzic_na_nazwe(w.get("rodzic", ""), nazwy, pomijane)
            rej = rejestry_wezla(model, w)[0][0]
            out.append(zawin("GATE", [ident(n), '"%s"' % n, '"%s"' % rodzic,
                                      rej, str(r["shift"]),
                                      flagi_bramki(w["id"], blok, w_domenie,
                                                   rodzic),
                                      "0"]) + ",")
        out.append("};")
        out.append("")

    ostatni = ident(nazwy[wezly[-1][0]["id"]])
    out.append(do_kolumny("#define CLKS_NR_" + krotki, 40)
               + "(%s + 1)" % ostatni)
    out.append("")

    out.append("static const struct samsung_cmu_info %s_cmu_info __initconst"
               " = {" % kod)
    pola = []
    if rodzaje.get("mux"):
        pola += [(".mux_clks", "%s_mux_clks" % kod),
                 (".nr_mux_clks", "ARRAY_SIZE(%s_mux_clks)" % kod)]
    if rodzaje.get("div"):
        pola += [(".div_clks", "%s_div_clks" % kod),
                 (".nr_div_clks", "ARRAY_SIZE(%s_div_clks)" % kod)]
    if rodzaje.get("gate"):
        pola += [(".gate_clks", "%s_gate_clks" % kod),
                 (".nr_gate_clks", "ARRAY_SIZE(%s_gate_clks)" % kod)]
    if rodzaje.get("frate") or rodzaje.get("pll"):
        pola += [(".fixed_clks", "%s_fixed_clks" % kod),
                 (".nr_fixed_clks", "ARRAY_SIZE(%s_fixed_clks)" % kod)]
    if rodzaje.get("ffactor"):
        pola += [(".fixed_factor_clks", "%s_fixed_factor_clks" % kod),
                 (".nr_fixed_factor_clks",
                  "ARRAY_SIZE(%s_fixed_factor_clks)" % kod)]
    pola.append((".nr_clk_ids", "CLKS_NR_%s" % krotki))
    pola += [(".clk_regs", "%s_clk_regs" % kod),
             (".nr_clk_regs", "ARRAY_SIZE(%s_clk_regs)" % kod)]
    if zegar_dt:
        pola.append((".clk_name", '"%s"' % zegar_dt))
    for klucz, wartosc in pola:
        out.append(do_kolumny(T + klucz, 32) + "= " + wartosc + ",")
    out.append("};")
    out.append("")

    if rejestracja == "wczesna":
        out.append("static void __init exynos9820_cmu_%s_init(struct"
                   " device_node *np)" % kod)
        out.append("{")
        out.append(T + "exynos_arm64_register_cmu(NULL, np, &%s_cmu_info);"
                   % kod)
        out.append("}")
        out.append("")
        out.append("/* %s */" % POWOD_WCZESNEJ[blok])
        out.append('CLK_OF_DECLARE(exynos9820_cmu_%s,'
                   ' "samsung,exynos9820-cmu-%s",' % (kod, przyrostek))
        out.append(T + "       exynos9820_cmu_%s_init);" % kod)
        out.append("")
    return NL.join(out)


NAGLOWEK_STEROWNIKA = '''// SPDX-License-Identifier: GPL-2.0-only
/*
 * Copyright (C) 2026 Artur Szafraniec <ganggg111@gmail.com>
 *
 * Common Clock Framework support for Exynos9820.
 *
 * The register offsets, field positions, gate bits, parents, oscillator rates
 * and fixed divider ratios below are a transcription of the clock tables that
 * ship with the vendor kernel, cmucal-sfr.c and cmucal-node.c.  The file is
 * produced by a generator, so every number in it can be traced back to a line
 * of those tables rather than to another port.
 *
 * What the tables do not describe, and what is therefore a decision taken here:
 * which clocks carry CLK_IS_CRITICAL, which carry CLK_IGNORE_UNUSED, which
 * paths propagate a rate request, and which CMU is registered early.  None of
 * those has been checked against running hardware yet.
 *
 * UNVERIFIED: one mux of a block this driver covers has a register but no
 * selector field in the tables, MUX_CLK_PERIS_GIC, which feeds the interrupt
 * controller and one of the bus ports.  A mux the driver cannot read or write
 * is not registered; its consumers are given its first input, the bus clock,
 * rather than its second, the oscillator.  Which one the hardware actually
 * selects has not been read off a device, and the answer changes the rate
 * those two clocks report, not whether they are gated.
 *
 * Register name to clock name mangling strategy used in this file
 *
 * Replace PLL_CON0_MUX_CLKCMU     with CLK_MOUT and mout
 * Replace CLK_CON_MUX_MUX_CLKCMU  with CLK_MOUT_CMU and mout_cmu
 * Replace CLK_CON_DIV_CLKCMU      with CLK_DOUT_CMU and dout_cmu
 * Replace CLK_CON_DIV_DIV_CLKCMU  with CLK_DOUT_CMU and dout_cmu
 * Replace CLK_CON_GAT_CLKCMU      with CLK_GOUT_CMU and gout_cmu
 * Replace CLK_CON_GAT_GATE_CLKCMU with CLK_GOUT_CMU and gout_cmu
 *
 * For gates remove _UID _BLK _IPCLKPORT and _RSTNSYNC
 */

#include <linux/clk-provider.h>
#include <linux/mod_devicetable.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/pm_runtime.h>

#include <dt-bindings/clock/samsung,exynos9820.h>

#include "clk.h"
#include "clk-exynos-arm64.h"
'''

OGON_STEROWNIKA = '''/*
 * A CMU that sits inside a switchable power domain loses its registers whenever
 * the domain goes down, so registration has to allocate the save area described
 * by .clk_regs and hook up the suspend and resume callbacks.  The CMUs that
 * never lose power take the same path without any downside.
 */
static const struct dev_pm_ops exynos9820_cmu_pm_ops = {
\tSET_RUNTIME_PM_OPS(exynos_arm64_cmu_suspend, exynos_arm64_cmu_resume,
\t\t\t   NULL)
\tSET_NOIRQ_SYSTEM_SLEEP_PM_OPS(pm_runtime_force_suspend,
\t\t\t\t      pm_runtime_force_resume)
};

static int __init exynos9820_cmu_probe(struct platform_device *pdev)
{
\treturn exynos_arm64_register_cmu_pm(pdev, true);
}

static const struct of_device_id exynos9820_cmu_of_match[] = {
%s
\t{ }
};

static struct platform_driver exynos9820_cmu_driver __refdata = {
\t.driver = {
\t\t.name = "exynos9820-cmu",
\t\t.of_match_table = exynos9820_cmu_of_match,
\t\t.suppress_bind_attrs = true,
\t\t.pm = &exynos9820_cmu_pm_ops,
\t},
\t.probe = exynos9820_cmu_probe,
};

static int __init exynos9820_cmu_init(void)
{
\treturn platform_driver_register(&exynos9820_cmu_driver);
}
core_initcall(exynos9820_cmu_init);
'''

NAGLOWEK_BINDINGU = '''/* SPDX-License-Identifier: (GPL-2.0-only OR BSD-2-Clause) */
/*
 * Copyright (C) 2026 Artur Szafraniec <ganggg111@gmail.com>
 *
 * Device Tree binding constants for the Exynos9820 clock controller.
 *
 * The numbering follows the vendor clock tables: within every CMU the
 * identifiers run from 1 in the order PLL, fixed rate, mux, divider,
 * fixed factor, gate, and inside each of those by register offset.
 */

#ifndef _DT_BINDINGS_CLOCK_EXYNOS_9820_H
#define _DT_BINDINGS_CLOCK_EXYNOS_9820_H
'''


def emituj_naglowek(per, nazwy, bloki=None):
    bloki = bloki if bloki is not None else BLOKI
    linie = [NAGLOWEK_BINDINGU.rstrip(NL)]
    wszystkie = []
    for blok, _, _, _, _ in bloki:
        for w, _ in uporzadkuj(per.get(blok, [])):
            wszystkie.append(ident(nazwy[w["id"]]))
    szer = max(len(x) for x in wszystkie)
    kolumna = ((8 + szer) // 8 + 1) * 8
    for blok, _, _, _, _ in bloki:
        linie.append("")
        linie.append("/* %s */" % blok)
        for i, (w, _) in enumerate(uporzadkuj(per.get(blok, [])), start=1):
            linie.append(do_kolumny("#define " + ident(nazwy[w["id"]]), kolumna)
                         + str(i))
    linie.append("")
    linie.append("#endif /* _DT_BINDINGS_CLOCK_EXYNOS_9820_H */")
    return NL.join(linie) + NL


def emituj_sterownik(model, per, nazwy, pomijane):
    czesci = [NAGLOWEK_STEROWNIKA]
    for blok, przyrostek, zegar_dt, rejestracja, w_domenie in BLOKI:
        czesci.append(emituj_blok(model, blok, przyrostek, zegar_dt,
                                  rejestracja, w_domenie, per, nazwy,
                                  pomijane))
    wpisy = []
    for blok, przyrostek, _, rejestracja, _ in BLOKI:
        if rejestracja != "platforma":
            continue
        wpisy.append(T + "{")
        wpisy.append(T * 2 + '.compatible = "samsung,exynos9820-cmu-%s",'
                     % przyrostek)
        wpisy.append(T * 2 + ".data = &%s_cmu_info," % przyrostek)
        wpisy.append(T + "},")
    czesci.append(OGON_STEROWNIKA % NL.join(wpisy))
    return NL.join(czesci)


# ------------------------------------------------------------------ wejscie


def podglad(model, blok, per, nazwy, pomijane):
    wpis = [b for b in BLOKI if b[0] == blok]
    if not wpis:
        sys.exit("nieznany blok: " + blok)
    w_domenie = wpis[0][4]
    print("# %s: %d wezlow" % (blok, len(per.get(blok, []))))
    for w, r in uporzadkuj(per.get(blok, [])):
        n = nazwy[w["id"]]
        if w["rodzaj"] == "mux":
            rod = [rodzic_na_nazwe(x, nazwy, pomijane)
                   for x in rodzice_wezla(model, w)]
            print("  MUX  %-38s off=0x%04x s=%2d w=%d  <- %s"
                  % (n, r["offset"], r["shift"], r["width"], rod))
        elif w["rodzaj"] == "gate":
            rod = rodzic_na_nazwe(w.get("rodzic", ""), nazwy, pomijane)
            print("  GATE %-38s off=0x%04x bit=%2d  <- %-26s %s"
                  % (n, r["offset"], r["shift"], rod,
                     flagi_bramki(w["id"], blok, w_domenie, rod)))
        elif w["rodzaj"] == "div":
            rod = rodzic_na_nazwe(w.get("rodzic", ""), nazwy, pomijane)
            print("  DIV  %-38s off=0x%04x s=%2d w=%d  <- %s"
                  % (n, r["offset"], r["shift"], r["width"], rod))
        elif w["rodzaj"] == "ffactor":
            rod = rodzic_na_nazwe(w.get("rodzic", ""), nazwy, pomijane)
            print("  FF   %-38s /%d  <- %s" % (n, w["ratio"] + 1, rod))
        elif w["rodzaj"] == "frate":
            print("  FRAT %-38s %d Hz" % (n, w["czestotliwosc"]))
        else:
            print("  PLL  %-38s off=0x%04x" % (n, r["offset"]))


def main():
    global BLOKI
    if "--bez" in sys.argv:
        # Seria dodaje CMU_DPU i CMU_CMGP osobnym patchem, wiec generator musi
        # umiec wypisac sterownik takze bez nich.  Naglowek bindingu zostaje
        # pelny: numeracja jest per blok, wiec nic sie w nim nie przesuwa.
        pomin = set(sys.argv[sys.argv.index("--bez") + 1].split(","))
        nieznane = pomin - set(b[0] for b in BLOKI)
        if nieznane:
            sys.exit("nieznane bloki: " + ", ".join(sorted(nieznane)))
        BLOKI = [b for b in BLOKI if b[0] not in pomin]

    model = CAL.zbuduj()
    per = zbierz(model)
    nazwy = mapa_nazw(per)
    pomijane = nieprogramowalne(model)

    if "--blok" in sys.argv:
        podglad(model, sys.argv[sys.argv.index("--blok") + 1], per, nazwy,
                pomijane)
        return

    # naglowek zawsze opisuje komplet blokow, zeby identyfikatory nie zmienialy
    # sie miedzy patchami serii
    pelny_model = CAL.zbuduj()
    zapamietane = BLOKI
    BLOKI = PELNE_BLOKI
    pelny_per = zbierz(pelny_model)
    pelne_nazwy = mapa_nazw(pelny_per)
    BLOKI = zapamietane

    naglowek = emituj_naglowek(pelny_per, pelne_nazwy, PELNE_BLOKI)
    sterownik = emituj_sterownik(model, per, nazwy, pomijane)

    cele = []
    if "--zapisz" in sys.argv:
        cele.append((os.path.join(ROOT, "sources", "linux", "include",
                                  "dt-bindings", "clock",
                                  "samsung,exynos9820.h"), naglowek))
        cele.append((os.path.join(ROOT, "sources", "linux", "drivers", "clk",
                                  "samsung", "clk-exynos9820.c"), sterownik))
    if "--naglowek" in sys.argv:
        cele.append((sys.argv[sys.argv.index("--naglowek") + 1], naglowek))
    if "--sterownik" in sys.argv:
        cele.append((sys.argv[sys.argv.index("--sterownik") + 1], sterownik))
    for sciezka, tresc in cele:
        io.open(sciezka, "w", encoding="utf-8", newline=NL).write(tresc)
        print("zapisano %s (%d linii)" % (sciezka, tresc.count(NL)))
    if cele:
        return

    print("blokow prowadzonych: %d" % len(BLOKI))
    razem = 0
    for blok, _, _, _, _ in BLOKI:
        wezly = per.get(blok, [])
        razem += len(wezly)
        rodzaje = {}
        for w, _ in wezly:
            rodzaje[w["rodzaj"]] = rodzaje.get(w["rodzaj"], 0) + 1
        print("  %-11s %3d  %s" % (blok, len(wezly),
                                   " ".join("%s=%d" % (k, rodzaje[k])
                                            for k in sorted(rodzaje))))
    print("zegarow razem: %d" % razem)
    print("muxow bez pola wyboru (pomijanych): %d" % len(pomijane))
    print("naglowek: %d linii, sterownik: %d linii"
          % (naglowek.count(NL), sterownik.count(NL)))


if __name__ == "__main__":
    main()
