#!/usr/bin/env python3
"""Porownuje RODZICA kazdej bramki i kazdego dzielnika z tablicami producenta.

Po co osobna bramka: check-clk-parents.py sprawdza tylko, ze nazwa rodzica
istnieje gdziekolwiek w pliku, wiec zamiana rodzicow miedzy dwoma zegarami
zostawia obie nazwy w zbiorze i przechodzi bez sladu. Skutek takiej zamiany
jest cichy: zegar dostaje zla czestotliwosc, nic sie nie wywala, obraz albo
magistrala po prostu nie dzialaja. check-cmu.py tez tego nie zlapie, bo czyta
z wpisu wylacznie symbol offsetu oraz przesuniecie i szerokosc pola.

Zrodlo prawdy: cmucal-node.c producenta.

    CLK_GATE(GOUT_BLK_DPU_UID_DPU_CMU_DPU_IPCLKPORT_PCLK, DIV_CLK_DPU_BUSP, ...)
    CLK_DIV(DIV_CLK_DPU_BUSP, MUX_CLKCMU_DPU_BUS_USER, ...)

Drugi argument to identyfikator rodzica. Nasz sterownik pisze nazwe rodzica
slownie ("dout_dpu_busp"), wiec porownanie idzie po RDZENIU nazwy: z obu stron
zdejmowane sa prefiksy rodzaju (GOUT_BLK_, DIV_CLK_, MUX_CLKCMU_, dout_, mout_,
gout_ i tak dalej) oraz nazwa bloku, a reszta musi sie zgadzac. To wystarcza,
zeby zamiana rodzicow miedzy dwoma zegarami zapalila bramke, bo dwa rozne
zegary maja rozne rdzenie.

Pokrycie jest przypiete w scripts/golden/clk-parents-checked.txt: jesli para
przestaje sie rozwiazywac, to tez jest regresja, a nie ciche zmniejszenie
kontroli.

Exit 0, gdy kazda rozwiazana para sie zgadza i pokrycie sie nie zmniejszylo.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, "sources", "linux", "drivers", "clk", "samsung",
                      "clk-exynos9820.c")
NODE = os.path.join(ROOT, "sources", "ds", "cmucal-node.c")
GOLDEN = os.path.join(ROOT, "scripts", "golden", "clk-parents-checked.txt")

# Prefiksy rodzaju wezla po stronie producenta i po naszej. Zdejmujemy je, zeby
# porownywac rdzen nazwy, a nie sposob zapisu.
PREFIKSY_V = ("GOUT_BLK_", "CLK_BLK_", "GATE_", "DIV_CLKCMU_", "DIV_CLK_",
              "MUX_CLKCMU_", "MUX_CLKMUX_", "MUX_CLK_", "CLKCMU_", "CLKMUX_",
              "MUX_", "DIV_", "PLL_", "OSCCLK_")
PREFIKSY_N = ("gout_", "dout_", "mout_", "fout_", "cmu_", "pll_")

# Pary, ktore ROZNIA SIE od producenta swiadomie, kazda z powodem i pozycja
# w docs/HW-BLOCKED.md. Lista jest zamknieta i kazdy wpis musi dalej byc
# niezgodny: jesli rozjazd zniknie, bramka to zglosi, zeby wyjatek nie zostal
# w skrypcie po tym, jak przestal byc potrzebny.
WYJATKI = {
    "gout_peris_gic_clk":
        "HW-33: producent podpina to pod MUX_CLK_PERIS_GIC, ktory nie ma pola "
        "wyboru w tablicach, wiec nie jest rejestrowany",
    "gout_peris_ad_axi_p_peris_aclkm":
        "HW-33: to samo wejscie co gout_peris_gic_clk",
}

# Nazwy blokow, ktore obie strony wtracaja w roznych miejscach.
BLOKI = ("peris", "peric0", "fsys0a", "fsys1", "apm", "cmgp", "dpu", "cmu")


def bez_prefiksu(s, prefiksy):
    zmiana = True
    while zmiana:
        zmiana = False
        for p in prefiksy:
            if s.startswith(p):
                s = s[len(p):]
                zmiana = True
    return s


def rdzen(nazwa, vendor):
    """Kanoniczny rdzen nazwy zegara, wspolny dla obu zapisow."""
    s = nazwa.strip().strip('"')
    # Producent ma jedna literowke w nazwie wezla: USE13 zamiast USI13. Rejestr
    # i wszystkie sasiednie wezly mowia USI13 (cmucal-node.c:1369, :2590), wiec
    # przekierowujemy ja, zamiast kopiowac do porownania.
    s = s.replace("USE13", "USI13").replace("use13", "usi13")
    # Oscylator: producent nazywa go per blok (OSCCLK_PERIS), my mamy jeden
    # wspolny wezel "oscclk".
    if s.upper().startswith("OSCCLK"):
        return "oscclk"
    s = bez_prefiksu(s, PREFIKSY_V if vendor else PREFIKSY_N)
    s = s.lower()
    # producent wtraca _UID_ i _IPCLKPORT w nazwach bramek
    s = s.replace("_uid_", "_").replace("_ipclkport", "")
    s = bez_prefiksu(s, ("rstnsync_",))
    # nazwa bloku bywa po jednej stronie, po drugiej nie
    for b in BLOKI:
        s = re.sub(r"(^|_)" + b + r"(_|$)", r"\1\2", s, count=1)
    return s.strip("_")


def split_args(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def entries(text, macro):
    for m in re.finditer(r"\b(?:" + macro + r")\(", text):
        i = m.end()
        depth, start = 1, i
        while depth and i < len(text):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
            i += 1
        yield split_args(text[start:i - 1])


def main():
    for p in (DRIVER, NODE):
        if not os.path.exists(p):
            print("check-clk-vendor-parents: brak %s" % p)
            return 2

    vsrc = open(NODE, encoding="utf-8", errors="replace").read()
    dsrc = open(DRIVER, encoding="utf-8", errors="replace").read()

    # id wezla producenta -> id rodzica
    rodzic_v = {}
    for macro in ("CLK_GATE", "CLK_DIV"):
        for a in entries(vsrc, macro):
            if len(a) >= 2:
                rodzic_v.setdefault(a[0].strip(), a[1].strip())

    # nasze: nazwa zegara -> nazwa rodzica, dla GATE i DIV (drugi i trzeci arg)
    pary = []
    for macro, i_naz, i_rodz in (("GATE", 1, 2), ("DIV|DIV_F", 1, 2)):
        for a in entries(dsrc, macro):
            if len(a) < 3:
                continue
            naz, rodz = a[i_naz].strip(), a[i_rodz].strip()
            if not naz.startswith('"') or not rodz.startswith('"'):
                continue
            pary.append((naz.strip('"'), rodz.strip('"')))

    # indeks producenta po rdzeniu nazwy dziecka
    v_po_rdzeniu = {}
    for dziecko, rodzic in rodzic_v.items():
        v_po_rdzeniu.setdefault(rdzen(dziecko, True), set()).add(
            rdzen(rodzic, True))

    zgodne, zle, nierozwiazane, wyjatki = [], [], [], []
    for naz, rodz in sorted(set(pary)):
        r = rdzen(naz, False)
        if r not in v_po_rdzeniu:
            nierozwiazane.append(naz)
            continue
        oczek = v_po_rdzeniu[r]
        nasz = rdzen(rodz, False)
        if nasz in oczek:
            if naz in WYJATKI:
                zle.append("  FAIL %-46s zgadza sie z producentem, a stoi na "
                           "liscie wyjatkow (%s)" % (naz[:46], WYJATKI[naz]))
            else:
                zgodne.append(naz)
        elif naz in WYJATKI:
            wyjatki.append("  WYJATEK %-40s %s" % (naz[:40], WYJATKI[naz]))
        else:
            zle.append("  FAIL %-46s rodzic %-28s, producent: %s"
                       % (naz[:46], rodz[:28], ", ".join(sorted(oczek))))

    for w in wyjatki:
        print(w)
    for b in zle:
        print(b)

    rc = 1 if zle else 0
    mamy = "\n".join(sorted(zgodne)) + "\n"
    if os.path.exists(GOLDEN):
        chcemy = open(GOLDEN, encoding="utf-8").read()
        if mamy != chcemy:
            stracone = sorted(set(chcemy.split()) - set(zgodne))
            nowe = sorted(set(zgodne) - set(chcemy.split()))
            if stracone:
                print("  FAIL pary, ktore przestaly sie rozwiazywac: %s"
                      % ", ".join(stracone[:8]))
                rc = 1
            if nowe:
                print("  UWAGA nowe rozwiazane pary (zaktualizuj golden): %s"
                      % ", ".join(nowe[:8]))
                rc = 1
    else:
        os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
        open(GOLDEN, "w", encoding="utf-8", newline="\n").write(mamy)
        print("check-clk-vendor-parents: zapisano wzorzec %d par" % len(zgodne))

    print("check-clk-vendor-parents: par w sterowniku %d, zgodnych z "
          "producentem %d, udokumentowanych wyjatkow %d, "
          "nierozwiazanych %d, niezgodnych %d"
          % (len(set(pary)), len(zgodne), len(wyjatki),
             len(nierozwiazane), len(zle)))
    return rc


if __name__ == "__main__":
    sys.exit(main())
