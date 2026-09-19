#!/usr/bin/env python3
"""Generuje tablice banków pinów Exynos9820 z tablic producenta.

Sterownik pinctrl Samsunga trzyma geometrie banków w statycznych tablicach
w kodzie, a nie w drzewie urządzeń: `samsung_pinctrl_get_soc_data()` bierze
`of_data->ctrl[id]`, gdzie `id` to numer aliasu `pinctrlN`. Bez tych tablic
kompatybilne `samsung,exynos9820-pinctrl` nie ma z czym się zestawić i żaden
z ośmiu kontrolerów nie wystartuje, a wraz z nimi żaden pin i żadne GPIO.

Producent ma te same tablice w `ds/pinctrl-exynos-arm64.c` (sekcja
"pin banks of exynos9820", 8 tablic, 64 banki). Ten skrypt je czyta i wypisuje
w formie mainline'a. Przełożenie jest jedno do jednego, bo:

  - typy banków są identyczne bajt w bajt: producent ma
    `exynos9810_bank_type_off = { .fld_width = {4,1,4,4,2,4},
    .reg_offset = {0x00,0x04,0x08,0x0c,0x10,0x14} }` i
    `exynos9810_bank_type_alive = { {4,1,4,4}, {0x00,0x04,0x08,0x0c} }`,
    a mainline dokładnie to samo pod nazwami `exynos850_bank_type_off`
    i `exynos850_bank_type_alive`,
  - makra różnią się tylko szóstym argumentem: producenckie
    `EXYNOS9_PIN_BANK_EINT*(typ, piny, reg, nazwa, offs, fltcon_offs)`
    niesie dodatkowo `fltcon_offset`, którego struktura mainline'a
    (`samsung_pin_bank_data`) w ogóle nie ma. Reszta argumentów mapuje się
    wprost na `EXYNOS850_PIN_BANK_EINT*(piny, reg, nazwa, offs)`.

Kolejność tablic w `exynos9820_pin_ctrl[]` musi zgadzać się z aliasami
`pinctrl0..pinctrl7` w drzewie urządzeń: ALIVE, AUD, CMGP, FSYS0, FSYS1,
PERIC0, PERIC1, VTS.

Użycie:
  scripts/gen-pinctrl-exynos9820.py            # statystyka
  scripts/gen-pinctrl-exynos9820.py --blok     # wypisz wygenerowany kod
  scripts/gen-pinctrl-exynos9820.py --zapisz   # wstaw do drzewa
"""
import io
import os
import re
import sys

NL = chr(10)
T = chr(9)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZRODLO = os.path.join(ROOT, "sources", "ds", "pinctrl-exynos-arm64.c")
CEL = os.path.join(ROOT, "sources", "linux", "drivers", "pinctrl", "samsung",
                   "pinctrl-exynos-arm64.c")
NAGLOWEK = os.path.join(ROOT, "sources", "linux", "drivers", "pinctrl",
                        "samsung", "pinctrl-samsung.h")
DOPASOWANIA = os.path.join(ROOT, "sources", "linux", "drivers", "pinctrl",
                           "samsung", "pinctrl-samsung.c")

# Kolejność musi odpowiadać aliasom pinctrl0..pinctrl7 w exynos9820.dtsi.
# Producent numeruje instancje 0,1,3,4,5,6,7,8 (dwójki nie ma), ale jego
# tablica ctrl[] i tak idzie po kolei, więc liczy się pozycja, nie etykieta.
INSTANCJE = ["ALIVE", "AUD", "CMGP", "FSYS0", "FSYS1", "PERIC0", "PERIC1",
             "VTS"]

# Które instancje dostają które wywołania zwrotne.  To NIE wynika z typu banków,
# tylko z tego, czy blok jest zasilany przy starcie: producent ma dla AUD i VTS
# cały komplet ZAKOMENTOWANY (`ds/pinctrl-exynos-arm64.c`, tablica
# `exynos9820_pin_ctrl[]`), bo te dwa bloki bywają wyłączone i sięgnięcie do ich
# rejestrów wiesza magistralę.  Przepisujemy jego wybór wprost.
CALLBACKI = {
    "ALIVE": ("eint_gpio_init", "eint_wkup_init", "suspend", "resume"),
    "AUD": (),
    "CMGP": ("eint_gpio_init", "eint_wkup_init", "suspend", "resume"),
    "FSYS0": ("eint_gpio_init", "suspend", "resume"),
    "FSYS1": ("eint_gpio_init", "suspend", "resume"),
    "PERIC0": ("eint_gpio_init", "suspend", "resume"),
    "PERIC1": ("eint_gpio_init", "suspend", "resume"),
    "VTS": (),
}

# Wartości, które te pola przyjmują w mainline.
WARTOSCI = {
    "eint_gpio_init": "exynos_eint_gpio_init",
    "eint_wkup_init": "exynos_eint_wkup_init",
    "suspend": "exynos_pinctrl_suspend",
    "resume": "exynos_pinctrl_resume",
}

MAKRA = {
    "EXYNOS9_PIN_BANK_EINTN": "EXYNOS850_PIN_BANK_EINTN",
    "EXYNOS9_PIN_BANK_EINTG": "EXYNOS850_PIN_BANK_EINTG",
    "EXYNOS9_PIN_BANK_EINTW": "EXYNOS850_PIN_BANK_EINTW",
}


def czytaj_banki():
    """Zwraca listę list: dla każdej instancji lista wpisów (makro, argumenty).

    Argumenty są w postaci mainline'a, czyli bez typu banku i bez
    `fltcon_offs`.
    """
    if not os.path.exists(ZRODLO):
        sys.exit("brak %s, uruchom scripts/fetch-sources.sh" % ZRODLO)
    tekst = io.open(ZRODLO, encoding="utf-8", errors="replace").read()

    out = []
    for i in range(len(INSTANCJE)):
        m = re.search(r"exynos9820_pin_banks%d\[\]\s*=\s*\{(.*?)\n\};"
                      % i, tekst, re.S)
        if not m:
            sys.exit("nie znalazłem tablicy exynos9820_pin_banks%d" % i)
        wpisy = []
        for w in re.finditer(r"(EXYNOS9_PIN_BANK_EINT[NGW])\(([^)]*)\)",
                             m.group(1)):
            makro = w.group(1)
            args = [x.strip() for x in w.group(2).split(",")]
            # producent: (typ, piny, reg, nazwa[, offs, fltcon_offs])
            if makro == "EXYNOS9_PIN_BANK_EINTN":
                if len(args) < 4:
                    sys.exit("zły wpis EINTN: " + w.group(0))
                nowe = [args[1], args[2], args[3]]
            else:
                if len(args) < 5:
                    sys.exit("zły wpis: " + w.group(0))
                nowe = [args[1], args[2], args[3], args[4]]
            wpisy.append((MAKRA[makro], nowe))
        if not wpisy:
            sys.exit("pusta tablica exynos9820_pin_banks%d" % i)
        out.append(wpisy)
    return out


def pole(nazwa, wartosc):
    """Wiersz inicjalizatora wyrownany tak jak w mainline: znak rownosci
    stoi na szesnastej kolumnie za wcieciem, wyrownany spacjami."""
    lewa = "." + nazwa
    return T * 2 + lewa + " " * max(1, 16 - len(lewa)) + "= " + wartosc + ","


def emituj(banki):
    linie = []
    for i, (nazwa, wpisy) in enumerate(zip(INSTANCJE, banki)):
        linie.append("/* pin banks of exynos9820 pin-controller %d (%s) */"
                     % (i, nazwa))
        linie.append("static const struct samsung_pin_bank_data"
                     " exynos9820_pin_banks%d[] __initconst = {" % i)
        for makro, args in wpisy:
            linie.append(T + "%s(%s)," % (makro, ", ".join(args)))
        linie.append("};")
        linie.append("")

    linie.append("static const struct samsung_pin_ctrl exynos9820_pin_ctrl[]"
                 " __initconst = {")
    for i, nazwa in enumerate(INSTANCJE):
        czolo = T + "{" if i == 0 else T + "}, {"
        linie.append(czolo)
        linie.append(T * 2 + "/* pin-controller instance %d %s data */"
                     % (i, nazwa))
        linie.append(pole("pin_banks", "exynos9820_pin_banks%d" % i))
        linie.append(pole("nr_banks",
                          "ARRAY_SIZE(exynos9820_pin_banks%d)" % i))
        for k in CALLBACKI[nazwa]:
            linie.append(pole(k, WARTOSCI[k]))
    linie.append(T + "},")
    linie.append("};")
    linie.append("")
    linie.append("const struct samsung_pinctrl_of_match_data"
                 " exynos9820_of_data __initconst = {")
    linie.append(T + ".ctrl" + T * 2 + "= exynos9820_pin_ctrl,")
    linie.append(T + ".num_ctrl" + T + "= ARRAY_SIZE(exynos9820_pin_ctrl),")
    linie.append("};")
    return NL.join(linie)


def wstaw(sciezka, kotwica, tresc, sprawdz):
    s = io.open(sciezka, encoding="utf-8", newline="").read()
    if sprawdz in s:
        return False
    if kotwica not in s:
        sys.exit("brak kotwicy w %s" % sciezka)
    s = s.replace(kotwica, tresc + kotwica, 1)
    io.open(sciezka, "w", encoding="utf-8", newline="").write(s)
    return True


def main():
    banki = czytaj_banki()
    kod = emituj(banki)

    if "--blok" in sys.argv:
        print(kod)
        return

    if "--zapisz" in sys.argv:
        # Tablice wstawiamy przed sasiadem alfabetycznym, zeby plik zostal
        # uporzadkowany tak jak dotad.
        ruch = wstaw(
            CEL,
            "/* pin banks of exynos9810 pin-controller 0 (ALIVE) */",
            kod + NL + NL,
            "exynos9820_pin_ctrl")
        ruch |= wstaw(
            NAGLOWEK,
            "extern const struct samsung_pinctrl_of_match_data"
            " exynos990_of_data;",
            "extern const struct samsung_pinctrl_of_match_data"
            " exynos9820_of_data;" + NL,
            "exynos9820_of_data")
        ruch |= wstaw(
            DOPASOWANIA,
            T + '{ .compatible = "samsung,exynos990-pinctrl",',
            T + '{ .compatible = "samsung,exynos9820-pinctrl",' + NL +
            T * 2 + ".data = &exynos9820_of_data }," + NL,
            "samsung,exynos9820-pinctrl")
        print("zapisano" if ruch else "nic do zmiany")
        return

    print("instancji: %d" % len(banki))
    razem = 0
    for nazwa, wpisy in zip(INSTANCJE, banki):
        razem += len(wpisy)
        rodzaje = {}
        for m, _ in wpisy:
            rodzaje[m[-5:]] = rodzaje.get(m[-5:], 0) + 1
        print("  %-7s bankow %2d  %s" % (nazwa, len(wpisy),
                                         " ".join("%s=%d" % (k, rodzaje[k])
                                                  for k in sorted(rodzaje))))
    print("bankow razem: %d" % razem)
    print("pinow razem: %d" % sum(int(a[0]) for w in banki for _, a in w))


if __name__ == "__main__":
    main()
