#!/usr/bin/env python3
"""Check the clock driver against the vendor CAL tables.

The clock driver is the foundation the rest of the series stands on, and until
cmucal-sfr.c was part of sources/ none of it could be checked against Samsung:
the only corroboration was another unverified port, so a register offset, a gate
bit or a divider width could be wrong everywhere at once and still look
self-consistent.

cmucal-sfr.c carries the machine-generated truth:

    SFR_BLOCK(CMU_DPU, 0x19000000, 0x8000)          base and window
    SFR(CLK_CON_DIV_DIV_CLK_DPU_BUSP, 0x1800, CMU_DPU)          offset
    SFR_ACCESS(..._DIVRATIO, 0, 3, CLK_CON_DIV_DIV_CLK_DPU_BUSP)  field

so every offset, every gate bit and every mux/divider (shift, width) in the
driver can be compared with it directly.

Coverage is pinned in scripts/golden/cmu-checked.txt: if a symbol stops
resolving, that is a regression too, not a silent loss of a check.

Exit 0 when everything that resolves agrees and coverage has not shrunk.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, "sources", "linux", "drivers", "clk", "samsung",
                      "clk-exynos9820.c")
SFR = os.path.join(ROOT, "sources", "ds", "cmucal-sfr.c")
GOLDEN = os.path.join(ROOT, "scripts", "golden", "cmu-checked.txt")

# One vendor entry is misspelled: cmucal-sfr.c:299 names the PERIC0 USI13 user
# mux "USE13".  The offset there is right, so the driver keeps the correct name
# and the lookup is redirected rather than the typo being copied into mainline.
ALIAS = {
    "PLL_CON0_MUX_CLKCMU_PERIC0_USI13_USI_USER":
        "PLL_CON0_MUX_CLKCMU_PERIC0_USE13_USI_USER",
}

# The field of a gate register that actually gates the clock.
GATE_FIELD = "_CG_VAL"
# Mux selector and divider ratio fields, in the order we prefer to match them.
MUX_FIELDS = ("_MUX_SEL", "_SELECT", "_SEL")
DIV_FIELDS = ("_DIVRATIO",)


def load_sfr():
    offs, acc = {}, {}
    for i, line in enumerate(open(SFR, encoding="utf-8", errors="replace"), 1):
        m = re.match(r"\s*SFR\((\w+),\s*(0x[0-9a-fA-F]+),\s*(\w+)\)", line)
        if m:
            offs.setdefault(m.group(1), (int(m.group(2), 16), m.group(3), i))
            continue
        m = re.match(r"\s*SFR_ACCESS\((\w+),\s*(\d+),\s*(\d+),\s*(\w+)\)", line)
        if m:
            acc.setdefault(m.group(4), []).append(
                (m.group(1), int(m.group(2)), int(m.group(3)), i))
    return offs, acc


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
    """Yield the argument list of each MUX(/DIV(/GATE( invocation.

    `macro` may be an alternation, so that variants such as nMUX
    and DIV_F are matched by the same pass.
    """
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


def field(acc, offset_sym, suffixes):
    for f, shift, width, line in acc.get(offset_sym, []):
        for suf in suffixes:
            if f.endswith(suf):
                return shift, width, line
    return None


def main():
    for p in (DRIVER, SFR):
        if not os.path.exists(p):
            print("check-cmu: brak %s" % p)
            return 2

    offs, acc = load_sfr()
    text = open(DRIVER, encoding="utf-8", errors="replace").read()
    bad, checked = [], []

    # 1. Register offsets.
    ours = {}
    for m in re.finditer(r"^#define\s+((?:CLK_CON|PLL_CON|CLK_LOCKTIME|QCH)\w*)\s+"
                         r"(0x[0-9a-fA-F]+)\s*$", text, re.M):
        ours[m.group(1)] = int(m.group(2), 16)
    for name, val in sorted(ours.items()):
        key = ALIAS.get(name, name)
        if key not in offs:
            continue
        want, block, line = offs[key]
        checked.append("offset " + name)
        if val != want:
            bad.append("offset %s: nasze %#06x, cmucal-sfr.c:%d = %#06x (%s)"
                       % (name, val, line, want, block))

    # 2. Gate bits, 3. mux and divider fields.
    for macro, argi, suffixes, kind in (
            # Wzorce lapia tez warianty makr z clk.h: nMUX/MUX_F pozwalaja
            # przepiac mux przy zmianie czestotliwosci, DIV_F/DIV_T niosa
            # dodatkowe flagi.  Bez nich zegar wypadal ze sprawdzania po samej
            # zmianie makra, choc offset i pole zostawaly te same.
            ("GATE", (3, 4, None), (GATE_FIELD,), "bramka"),
            ("n?MUX_F|n?MUX", (3, 4, 5), MUX_FIELDS, "mux"),
            ("DIV_F|DIV_T|DIV", (3, 4, 5), DIV_FIELDS, "dzielnik")):
        for args in entries(text, macro):
            oi, si, wi = argi
            if len(args) <= si:
                continue
            sym = ALIAS.get(args[oi], args[oi])
            if sym not in acc:
                continue
            try:
                shift = int(args[si], 0)
            except ValueError:
                continue
            f = field(acc, sym, suffixes)
            if f is None:
                continue
            vshift, vwidth, vline = f
            checked.append("%s %s" % (kind, sym))
            if shift != vshift:
                bad.append("%s %s: nasze przesuniecie %d, cmucal-sfr.c:%d = %d"
                           % (kind, sym, shift, vline, vshift))
            if wi is not None and len(args) > wi:
                try:
                    width = int(args[wi], 0)
                except ValueError:
                    continue
                if width != vwidth:
                    bad.append("%s %s: nasza szerokosc %d, cmucal-sfr.c:%d = %d"
                               % (kind, sym, width, vline, vwidth))

    for b in bad:
        print("  FAIL %s" % b)

    rc = 1 if bad else 0
    checked = sorted(set(checked))
    have = "\n".join(checked) + "\n"
    if os.path.exists(GOLDEN):
        want = set(open(GOLDEN, encoding="utf-8").read().split("\n")) - {""}
        lost = sorted(want - set(checked))
        if lost:
            print("  FAIL przestaly byc sprawdzane: %s" % ", ".join(lost[:8]))
            rc = 1
        new = sorted(set(checked) - want)
        if new:
            print("  UWAGA nowe sprawdzane symbole (zaktualizuj golden): %d"
                  % len(new))
            rc = 1
    else:
        os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
        open(GOLDEN, "w", encoding="utf-8", newline="\n").write(have)
        print("check-cmu: zapisano wzorzec %d pozycji" % len(checked))

    n_off = len([c for c in checked if c.startswith("offset")])
    print("check-cmu: offsetow %d/%d, pol mux/div/bramek %d, niezgodnych %d"
          % (n_off, len(ours), len(checked) - n_off, len(bad)))
    return rc


if __name__ == "__main__":
    sys.exit(main())
