#!/usr/bin/env python3
"""Compare every register constant in the driver with the vendor header it came from.

Five wrong register constants survived review, checkpatch, W=1, dt-validate and a
byte-identical DTB: BLENDER_BG_IMAGE_SIZE at 0x0204 instead of 0x0200, ESCCLK_EN
on bit 19 instead of 16, RGB24 as 0x7 instead of 0x3e, PKT_GO_EN on bit 8 instead
of 16, and WIN_FUNC_COPY as 0x0, which is CLEAR.  None of them breaks a build.
All of them break the display in a way that leaves no log line.

This gate does what a human reviewer cannot do reliably: it resolves every one of
our defines against the vendor definition of the same register and compares the
values.

The set of names that resolve is pinned in scripts/golden/regs-matched.txt, so a
rename cannot quietly drop a constant out of the comparison.

Exit 0 when every resolved constant agrees and the resolved set is unchanged.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OURS = os.path.join(ROOT, "sources", "linux", "drivers", "gpu", "drm",
                    "exynos", "exynos9820_regs.h")
VENDOR = ["regs-dsim.h", "regs-decon.h", "regs-dpp.h", "dsim.h", "decon_cal.h"]
GOLDEN = os.path.join(ROOT, "scripts", "golden", "regs-matched.txt")
GOLDEN_NIE = os.path.join(ROOT, "scripts", "golden", "regs-unmatched.txt")

DEFINE = re.compile(r"^#define\s+(\w+)(\([^)]*\))?\s+(.+?)\s*$", re.M)
ENUM = re.compile(r"^\s*(\w+)\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*,", re.M)


def logical_lines(text):
    """Join backslash continuations, keeping the line number of the first line."""
    out = []
    buf, start = None, 0
    for i, line in enumerate(text.split("\n"), 1):
        if buf is None:
            buf, start = line, i
        else:
            buf += " " + line.strip()
        if buf.endswith("\\"):
            buf = buf[:-1].rstrip()
        else:
            out.append((start, buf))
            buf = None
    if buf is not None:
        out.append((start, buf))
    return out


def parse(path):
    """name -> (expression, line).  Both #define and enumerator constants."""
    out = {}
    text = open(path, encoding="utf-8", errors="replace").read()
    for i, line in logical_lines(text):
        m = re.match(r"#define\s+(\w+)(\([^)]*\))?\s+(.+?)\s*$", line)
        if m:
            out.setdefault(m.group(1), (m.group(3).strip(), i))
    for m in ENUM.finditer(text):
        line = text[: m.start()].count("\n") + 1
        out.setdefault(m.group(1), (m.group(2), line))
    return out


def value(expr):
    """Evaluate a constant expression, or None when it is parameterised."""
    e = expr.replace("BIT(", "(1 << ")
    e = re.sub(r"\b(\d+)[UL]+\b", r"\1", e)
    # A hex literal carries an "x", so look for identifiers only after the
    # literals are out of the way.
    if re.search(r"[A-Za-z_]", re.sub(r"0[xX][0-9a-fA-F]+", "0", e)):
        return None
    try:
        return eval(e, {"__builtins__": {}}, {})
    except Exception:
        return None


def literals(expr):
    """Shifts and masks of a parameterised macro, W KOLEJNOSCI ZAPISU.

    Argumenty i nazwy pol roznia sie miedzy nami a producentem; zgadzac ma sie
    arytmetyka. Zera sa pomijane, bo "<< 0" bywa pisane po obu stronach.

    Kolejnosc ma znaczenie i to jest zmiana wobec pierwszej wersji tej bramki,
    ktora porownywala posortowany multizbior. Przy sortowaniu zamiana przesuniec
    miedzy dwoma polami tego samego rejestru byla niewidoczna: DSC_SWAP(b, c, w)
    i DSC_SWAP(c, b, w) daja ten sam zbior [8, 9, 10]. Porownanie pozycyjne
    przechodzi mimo to w calosci: wszystkie 94 makra parametryczne, ktore ta
    bramka rozwiazuje, maja u nas te sama kolejnosc liczb co u producenta.
    """
    e = expr.replace("BIT(", "(1 << ")
    nums = [int(x, 0) for x in re.findall(r"0[xX][0-9a-fA-F]+|\d+", e)]
    return [n for n in nums if n != 0]


def candidates(name):
    """Our name -> the names the vendor could have used for the same register."""
    yield name
    if name.startswith("DECON_"):
        stem = name[len("DECON_"):]
        yield stem
        yield stem + "_0"
        # Blend function and data path constants are enums, not defines.
        yield stem.replace("WIN_FUNC_", "PD_FUNC_")
        yield stem.replace("DPATH_DSCC_ENC01_", "DPATH_DSCC_DSCENC01_")
        yield stem
    if name.startswith("DSIM_CONFIG_PIXEL_FORMAT_"):
        yield "DSIM_PIXEL_FORMAT_" + name[len("DSIM_CONFIG_PIXEL_FORMAT_"):]
    yield name + "_0"


def main():
    if not os.path.exists(OURS):
        print("check-regs: brak %s" % OURS)
        return 2
    vend = {}
    for name in VENDOR:
        p = os.path.join(ROOT, "sources", "ds", name)
        if not os.path.exists(p):
            print("check-regs: brak sources/ds/%s" % name)
            return 2
        for k, v in parse(p).items():
            vend.setdefault(k, v + (name,))

    ours = parse(OURS)
    matched, bad, unmatched = [], [], []
    for name in sorted(ours):
        expr, _ = ours[name]
        hit = next((c for c in candidates(name) if c in vend), None)
        if hit is None:
            unmatched.append(name)
            continue
        vexpr, vline, vfile = vend[hit]
        a, b = value(expr), value(vexpr)
        if a is None or b is None:
            # Parameterised macro: compare the arithmetic, not the spelling.
            a, b = literals(expr), literals(vexpr)
        matched.append(name)
        if a != b:
            bad.append("%-40s nasze %-18s vs %s = %-18s (ds/%s:%d)"
                       % (name[:40], str(expr)[:18], hit[:34], str(vexpr)[:18],
                          vfile, vline))

    for b in bad:
        print("  FAIL %s" % b)

    rc = 1 if bad else 0
    have = "\n".join(matched) + "\n"
    if os.path.exists(GOLDEN):
        want = open(GOLDEN, encoding="utf-8").read()
        if have != want:
            lost = sorted(set(want.split()) - set(matched))
            new = sorted(set(matched) - set(want.split()))
            if lost:
                print("  FAIL stale, ktore przestaly sie rozwiazywac: %s"
                      % ", ".join(lost))
                rc = 1
            if new:
                print("  UWAGA nowe rozwiazane stale (zaktualizuj golden): %s"
                      % ", ".join(new))
                rc = 1
    else:
        os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
        open(GOLDEN, "w", encoding="utf-8", newline="\n").write(have)
        print("check-regs: zapisano wzorzec %d nazw" % len(matched))

    # Druga strona tej samej monety: stala, ktorej nazwa nie trafia w zadnego
    # kandydata u producenta, nie jest z niczym porownywana. Wzorzec wyzej lapie
    # tylko regres. Bez tego wzorca NOWA nierozwiazana stala wchodzi do serii
    # bez sladu, a nowe stale sa najswiezsze i najmniej sprawdzone.
    brak = "\n".join(sorted(unmatched)) + "\n"
    if os.path.exists(GOLDEN_NIE):
        chcemy = open(GOLDEN_NIE, encoding="utf-8").read()
        if brak != chcemy:
            nowe = sorted(set(unmatched) - set(chcemy.split()))
            znikly = sorted(set(chcemy.split()) - set(unmatched))
            if nowe:
                print("  FAIL stale bez odpowiednika u producenta, nowe: %s"
                      % ", ".join(nowe))
                rc = 1
            if znikly:
                print("  UWAGA stale, ktore zaczely sie rozwiazywac "
                      "(zaktualizuj golden): %s" % ", ".join(znikly))
                rc = 1
    else:
        open(GOLDEN_NIE, "w", encoding="utf-8", newline="\n").write(brak)
        print("check-regs: zapisano wzorzec %d nierozwiazanych nazw"
              % len(unmatched))

    print("check-regs: nasze stale %d, rozwiazane wobec producenta %d, "
          "nierozwiazane %d, niezgodne %d"
          % (len(ours), len(matched), len(unmatched), len(bad)))
    return rc


if __name__ == "__main__":
    sys.exit(main())
