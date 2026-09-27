#!/usr/bin/env python3
"""Przepisuje w latkach serii te czesci, ktore naleza do generatorow.

Po co.  Trzy pliki tej serii maja generatory i to one sa zrodlem prawdy: oba
drzewa urzadzen i sterownik zegarow.  Latki serii sa jednak osobnymi plikami:
gdy ktos poprawi wezel albo regule w generatorze, latka z kroku, do ktorego ta
tresc nalezy, zostaje ze stara wersja.  Rozjazd nie daje zadnego objawu, bo
bramki czytaja pliki drzewa, a nie latki, i wychodzi dopiero przy nakladaniu
serii, kiedy juz nikt nie pamieta, co bylo zamierzone.  Ten skrypt zamyka
petle: bierze roznice miedzy krokiem k-1 a k wprost z generatora i wstawia ja
do latki tego kroku, zostawiajac jej opis i te czesci, ktore dotycza innych
plikow.

Przypisanie latek do krokow jest JAWNE, nie zgadywane z tematu: pierwszy etap
obu generatorow drzewa opisuje jedno zdanie, a seria wnosi te tresc dwiema
latkami, osobno dla pliku SoC i pliku plyty.  Dopasowanie po temacie zgubiloby
wlasnie ten przypadek, i to po cichu.

Porownanie pomija to, czego ten skrypt odtworzyc NIE MOZE, bo liczy roznice
miedzy dwoma plikami tymczasowymi, a nie miedzy obiektami repozytorium:
linie "index <skrot>..<skrot>" oraz kontekst dopisywany przez gita za drugim
"@@" w naglowku fragmentu.  Bez tego pominiecia skrypt uznawalby za rozjazd
kazda latke wyeksportowana przez `git format-patch` i kusil, zeby przepisac ja
swoim ubozszym diffem; tak wlasnie seria doszla do stanu, w ktorym 28 latek
plikow generowanych nie mialo linii "index", a pozostale 60 mialo.

Uzycie:
  scripts/odswiez-latki.py             # pokaz, co by sie zmienilo
  scripts/odswiez-latki.py --zapisz    # przepisz latki

--zapisz jest wyjsciem awaryjnym.  Droga kanoniczna prowadzi przez serie
w sources/linux: wszczep tresc generatora w commit kroku i wyeksportuj calosc
przez `git format-patch`, bo tylko ona daje latke z komplem naglowkow.

Kopii drzew urzadzen w serii bootloadera ten skrypt juz NIE dotyka.
Wnosza je dwa patche (0007 plik, 0009 synchronizacja), a skladania pliku
z wielu patchy tu nie ma. Pokrywaja je dwie inne bramki: check-uboot-dts
porownuje drzewo bootloadera z seria jadra, a check-uboot-seria dowodzi,
ze latki bootloadera daja dokladnie to drzewo.

Kod 0 gdy nie bylo nic do zmiany albo zmiany zapisano, 1 gdy sa rozjazdy
i uruchomiono bez --zapisz, 2 gdy nie da sie dopasowac latki do kroku.
"""
import io
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCHES = os.path.join(ROOT, "patches")
NL = chr(10)

# Plik generowany, jego generator i kroki serii, ktore go buduja.
# Krok to (numer latki, argumenty opisujace stan PO tym kroku); stanem PRZED
# jest krok poprzedni, a dla pierwszego pusty plik.
PLIKI = (
    {
        "plik": "arch/arm64/boot/dts/exynos/exynos9820.dtsi",
        "generator": "gen-dts-exynos9820.py",
        "tryb": "stdout",
        "kroki": [("0014", ["--etap", "1"]),
                  ("0038", ["--etap", "2"]),
                  ("0039", ["--etap", "3"]),
                  ("0040", ["--etap", "4"]),
                  ("0042", ["--etap", "5"]),
                  ("0053", ["--etap", "6"]),
                  ("0058", ["--etap", "7"]),
                  ("0060", ["--etap", "8"]),
                  ("0073", ["--etap", "9"]),
                  ("0079", ["--etap", "10"]),
                  ("0083", ["--etap", "11"]),
                  ("0086", ["--etap", "12"]),
                  ("0088", ["--etap", "13"])],
    },
    {
        "plik": "arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dts",
        "generator": "gen-dts-beyond2lte.py",
        "tryb": "stdout",
        "kroki": [("0015", ["--etap", "1"]),
                  ("0040", ["--etap", "2"]),
                  ("0054", ["--etap", "3"]),
                  ("0059", ["--etap", "4"]),
                  ("0061", ["--etap", "5"]),
                  ("0080", ["--etap", "6"])],
    },
    {
        # Plik wyprowadzen tez nie ma etapow, tylko grupy: seria wnosi je
        # piecioma krokami, a stanem kroku jest lista grup, ktore do tego
        # miejsca juz sa w drzewie.  Same banki wyprowadzen przychodzą
        # z pierwszym krokiem i nie zmieniaja sie pozniej.
        "plik": "arch/arm64/boot/dts/exynos/exynos9820-pinctrl.dtsi",
        "generator": "gen-pinctrl-dts-exynos9820.py",
        "tryb": "stdout",
        "kroki": [("0014", ["--wypisz", "--grupy", "hsi2c10_bus"]),
                  ("0040", ["--wypisz", "--grupy",
                            "hsi2c10_bus,hsi2c2_bus,decon_te_pins"]),
                  ("0052", ["--wypisz", "--grupy",
                            "hsi2c10_bus,hsi2c2_bus,decon_te_pins,"
                            "ufs_refclk_out,ufs_rst_n"]),
                  ("0060", ["--wypisz", "--grupy",
                            "hsi2c10_bus,hsi2c2_bus,decon_te_pins,"
                            "ufs_refclk_out,ufs_rst_n,hsi2c45_bus"]),
                  ("0079", ["--wypisz", "--grupy",
                            "hsi2c10_bus,hsi2c2_bus,decon_te_pins,"
                            "ufs_refclk_out,ufs_rst_n,hsi2c45_bus,"
                            "uart1_bus,bt_hostwake_pins,bt_en_pins,"
                            "bt_btwake_pins"]),
                  ("0086", ["--wypisz", "--grupy",
                            "hsi2c10_bus,hsi2c2_bus,decon_te_pins,"
                            "ufs_refclk_out,ufs_rst_n,hsi2c45_bus,"
                            "uart1_bus,bt_hostwake_pins,bt_en_pins,"
                            "bt_btwake_pins,pcie0_clkreq_pins,"
                            "pcie0_perst_pins"]),
                  ("0119", ["--wypisz", "--grupy",
                            "hsi2c10_bus,hsi2c2_bus,decon_te_pins,"
                            "ufs_refclk_out,ufs_rst_n,hsi2c45_bus,"
                            "uart1_bus,bt_hostwake_pins,bt_en_pins,"
                            "bt_btwake_pins,pcie0_clkreq_pins,"
                            "pcie0_perst_pins,hsi2c38_bus"]),
                  ("0123", ["--wypisz", "--grupy",
                            "hsi2c10_bus,hsi2c2_bus,decon_te_pins,"
                            "ufs_refclk_out,ufs_rst_n,hsi2c45_bus,"
                            "uart1_bus,bt_hostwake_pins,bt_en_pins,"
                            "bt_btwake_pins,pcie0_clkreq_pins,"
                            "pcie0_perst_pins,hsi2c38_bus,spi2_bus"]),
                  ("0134", ["--wypisz", "--grupy",
                            "hsi2c10_bus,hsi2c2_bus,decon_te_pins,"
                            "ufs_refclk_out,ufs_rst_n,hsi2c45_bus,"
                            "uart1_bus,bt_hostwake_pins,bt_en_pins,"
                            "bt_btwake_pins,pcie0_clkreq_pins,"
                            "pcie0_perst_pins,hsi2c38_bus,spi2_bus,"
                            "aud_i2s0_bus,aud_i2s1_bus"]),
                  ("0143", ["--wypisz"])],
    },
    {
        # Sterownik zegarow nie ma etapow, tylko bloki: seria wnosi go
        # w trzech krokach, a kazdy nastepny dokłada bloki, ktorych
        # poprzedni nie mial.  Stan opisuje wiec lista blokow POMINIETYCH.
        "plik": "drivers/clk/samsung/clk-exynos9820.c",
        "generator": "gen-clk-exynos9820.py",
        "tryb": "sterownik",
        "kroki": [("0013", ["--bez", "CMU_DPU,CMU_CMGP,CMU_PERIC1,CMU_AUD"]),
                  ("0022", ["--bez", "CMU_PERIC1,CMU_AUD"]),
                  ("0075", ["--bez", "CMU_AUD"]),
                  ("0127", [])],
    },
)


def uruchom(args):
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode not in (0, 1):
        sys.exit("blad: %s%s%s" % (" ".join(args), NL, r.stderr.strip()))
    return r.stdout


def stan(opis, argumenty):
    """Tresc pliku generowanego w danym stanie."""
    if argumenty is None:
        return ""
    if opis["tryb"] == "kopia":
        # Kopia nie ma stanow posrednich: bierze sie w calosci z drzewa jadra.
        return io.open(os.path.join(ROOT, "sources", "linux", argumenty[0]),
                       encoding="utf-8").read()
    generator = os.path.join(ROOT, "scripts", opis["generator"])
    if opis["tryb"] == "stdout":
        return uruchom([sys.executable, generator] + argumenty)
    kat = tempfile.mkdtemp()
    cel = os.path.join(kat, "wynik")
    uruchom([sys.executable, generator] + argumenty + ["--sterownik", cel])
    tresc = io.open(cel, encoding="utf-8").read()
    os.remove(cel)
    os.rmdir(kat)
    return tresc


def roznica(sciezka, przed, po):
    """Roznica w postaci, ktorej uzywa git, razem z naglowkiem nowego pliku."""
    kat = tempfile.mkdtemp()
    a = os.path.join(kat, "a")
    b = os.path.join(kat, "b")
    io.open(a, "w", encoding="utf-8", newline=NL).write(przed)
    io.open(b, "w", encoding="utf-8", newline=NL).write(po)
    out = uruchom(["git", "diff", "--no-index", "--no-color", "-U3", a, b])
    os.remove(a)
    os.remove(b)
    os.rmdir(kat)

    wynik = []
    for l in out.split(NL):
        if l.startswith("diff --git"):
            wynik.append("diff --git a/%s b/%s" % (sciezka, sciezka))
        elif l.startswith("--- "):
            wynik.append("--- /dev/null" if not przed else "--- a/%s" % sciezka)
        elif l.startswith("+++ "):
            wynik.append("+++ b/%s" % sciezka)
        elif l.startswith("index ") or l.startswith("new file mode"):
            continue
        else:
            wynik.append(l)
    if not przed:
        wynik.insert(1, "new file mode 100644")
    return NL.join(wynik).rstrip(NL) + NL


def sekcje(diff):
    """Diff rozbity na czesci: jedna na plik, w kolejnosci wystepowania."""
    out = []
    biezaca = None
    for l in diff.split(NL):
        if l.startswith("diff --git "):
            if biezaca is not None:
                out.append(biezaca)
            biezaca = [l]
        elif biezaca is not None:
            biezaca.append(l)
    if biezaca is not None:
        out.append(biezaca)
    return [NL.join(s).rstrip(NL) + NL for s in out]


def sciezka_sekcji(sekcja):
    m = re.match(r"diff --git a/(\S+) b/", sekcja)
    return m.group(1) if m else None


def porownywalna(sekcja):
    """Sekcja bez tego, czego ten skrypt nie jest w stanie odtworzyc."""
    out = []
    for l in sekcja.split(NL):
        if l.startswith("index "):
            continue
        m = re.match(r"(@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@)", l)
        out.append(m.group(1) if m else l)
    return NL.join(out)


def statystyka(sekcje_diffu):
    pliki = []
    for s in sekcje_diffu:
        d = u = 0
        for l in s.split(NL):
            if l.startswith("+") and not l.startswith("+++"):
                d += 1
            elif l.startswith("-") and not l.startswith("---"):
                u += 1
        pliki.append((sciezka_sekcji(s), d, u))
    szer = max(len(p[0]) for p in pliki)
    out = []
    for nazwa, d, u in pliki:
        out.append(" %-*s | %3d %s" % (szer, nazwa, d + u,
                                       "+" * min(d, 40) + "-" * min(u, 20)))
    dod = sum(p[1] for p in pliki)
    usu = sum(p[2] for p in pliki)
    out.append(" %d file%s changed, %d insertion%s(+)%s"
               % (len(pliki), "" if len(pliki) == 1 else "s",
                  dod, "" if dod == 1 else "s",
                  "" if not usu else ", %d deletion%s(-)"
                  % (usu, "" if usu == 1 else "s")))
    return NL.join(out) + NL


def znajdz_latke(numer, katalog=None):
    katalog = katalog or PATCHES
    for f in sorted(os.listdir(katalog)):
        if f.startswith(numer + "-") and f.endswith(".patch"):
            p = os.path.join(katalog, f)
            return p, io.open(p, encoding="utf-8", errors="replace").read()
    return None, None


def main():
    zapisz = "--zapisz" in sys.argv
    rozjazdy = 0
    zapisane = 0

    for opis in PLIKI:
        plik = opis["plik"]
        poprzedni = None
        for numer, argumenty in opis["kroki"]:
            sciezka, tekst = znajdz_latke(numer, opis.get("katalog"))
            if sciezka is None:
                print("  BRAK latki %s dla %s" % (numer, plik))
                return 2

            nowa_sekcja = roznica(plik, stan(opis, poprzedni),
                                  stan(opis, argumenty))
            poprzedni = argumenty

            glowa, _, ogon = tekst.partition(NL + "---" + NL)
            czesci = sekcje(ogon)
            podmienione = []
            trafione = False
            for s in czesci:
                if sciezka_sekcji(s) == plik:
                    podmienione.append(nowa_sekcja)
                    trafione = True
                else:
                    podmienione.append(s)
            if not trafione:
                print("  BRAK sekcji %s w %s"
                      % (plik, os.path.basename(sciezka)))
                return 2

            # Porownujemy SAMA sekcje pliku generowanego, a nie cala latke:
            # blok statystyki nad diffem tez jest tu odtwarzany i jego
            # wyrownanie kolumn rozni sie od gitowego, wiec porownanie calosci
            # zglaszalo rozjazd tam, gdzie tresc jest identyczna.
            stara = next(s for s in czesci if sciezka_sekcji(s) == plik)
            if porownywalna(stara) == porownywalna(nowa_sekcja):
                continue

            nowa_tresc = (glowa + NL + "---" + NL + statystyka(podmienione)
                          + NL + "".join(podmienione))
            rozjazdy += 1
            print("  %s  %s  (%d -> %d linii sekcji)"
                  % (os.path.basename(sciezka)[:52], os.path.basename(plik),
                     stara.count(NL), nowa_sekcja.count(NL)))
            if zapisz:
                io.open(sciezka, "w", encoding="utf-8",
                        newline=NL).write(nowa_tresc)
                zapisane += 1

    print("odswiez-latki: rozjazdow %d%s"
          % (rozjazdy, ", zapisanych %d" % zapisane if zapisane else ""))
    if rozjazdy and not zapisz:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
