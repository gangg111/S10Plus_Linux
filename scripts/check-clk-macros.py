#!/usr/bin/env python3
"""Sprawdza, czy kazde uzyte makro zegara istnieje w naglowku bindingu.

Nieistniejace makro w drzewie urzadzen zatrzymuje kompilacje, wiec tam widac je
od razu.  W PRZYKLADZIE w pliku bindingu YAML nie widac go wcale: przyklady
kompiluje dopiero `make dt_binding_check` w pelnym drzewie jadra, a lokalna
bramka `dt-validate` sprawdza zbudowane DTB, nie przyklady.

Tak wlasnie przeszly niezauwazone cztery makra po przenumerowaniu zegarow:
przyklad DECON-a wolal CLK_GOUT_DPU_ACLK_DECON, a naglowek definiuje
CLK_GOUT_DPU_DPU_ACLK_DECON, i tak samo w bindingu D-PHY.  Znalazl to dopiero
audyt cytowan.

Skrypt zbiera kazde makro postaci CLK_* z naszych plikow drzewa urzadzen i z
przykladow w naszych bindingach, po czym sprawdza je w naglowku bindingu zegarow.

Wyjscie 0, gdy kazde uzyte makro jest zdefiniowane.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINUX = os.path.join(ROOT, "sources", "linux")
NAGLOWEK = os.path.join(LINUX, "include", "dt-bindings", "clock",
                        "samsung,exynos9820.h")
DTS = os.path.join(LINUX, "arch", "arm64", "boot", "dts", "exynos")
BINDINGI = os.path.join(LINUX, "Documentation", "devicetree", "bindings")

MAKRO = re.compile(r"\bCLK_[A-Z0-9_]+\b")

# Makra, ktore nie pochodza z naszego naglowka i maja wlasne zrodlo.
OBCE = {
    "CLK_NR_CLKS",          # inne SoC
}


def nasze_pliki():
    """Pliki, ktore MY wnosimy i ktore moga uzywac makr zegarow."""
    out = []
    if os.path.isdir(DTS):
        for n in sorted(os.listdir(DTS)):
            if "exynos9820" in n:
                out.append(os.path.join(DTS, n))
    for katalog, _, pliki in os.walk(BINDINGI):
        for n in sorted(pliki):
            if "exynos9820" in n and n.endswith(".yaml"):
                out.append(os.path.join(katalog, n))
    return out


def main():
    if not os.path.exists(NAGLOWEK):
        print("check-clk-macros: brak %s" % NAGLOWEK)
        return 2

    tekst = io.open(NAGLOWEK, encoding="utf-8", errors="replace").read()
    zdefiniowane = set(re.findall(r"#define\s+(CLK_[A-Z0-9_]+)", tekst))

    zle = []
    uzytych = 0
    for p in nasze_pliki():
        rel = os.path.relpath(p, LINUX).replace(os.sep, "/")
        for i, linia in enumerate(io.open(p, encoding="utf-8",
                                          errors="replace"), 1):
            for m in MAKRO.finditer(linia):
                nazwa = m.group(0)
                if nazwa in OBCE:
                    continue
                uzytych += 1
                if nazwa not in zdefiniowane:
                    zle.append((rel, i, nazwa))

    for rel, i, nazwa in zle:
        print("  FAIL %s:%d uzywa %s, ktorego naglowek nie definiuje"
              % (rel, i, nazwa))
    print("check-clk-macros: uzyc %d, zdefiniowanych w naglowku %d, brakow %d"
          % (uzytych, len(zdefiniowane), len(zle)))
    return 1 if zle else 0


if __name__ == "__main__":
    sys.exit(main())
