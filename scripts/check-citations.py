#!/usr/bin/env python3
"""Every vendor file a patch cites must be shipped, and every cited line must exist.

A citation nobody can open is not a citation.  The series used to point at
decon_reg.c:1073, regs-dpp.h and cmucal-sfr.c without those files being part of
sources/, so a reviewer reproducing the work could not check a single one of the
constants that rested on them.  This gate makes that failure loud.

Two rules:

  1. A downstream path mentioned anywhere in a patch (commit message or added
     comment) must resolve to a file under sources/ds or sources/ub.
  2. A citation carrying a line number must point inside the file.

Exit 0 when everything resolves, 1 otherwise.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources")

# Paths that identify a downstream (vendor) file rather than a mainline one.
VENDOR_MARKERS = (
    "/fbdev/exynos/",
    "/cal-if/",
    "/cal_9820/",
    "/sec_ts/",
    "arch/arm64/boot/dts/samsung/",
    "arch/arm64/configs/exynos9820",
)

CITE = re.compile(
    r"((?:[A-Za-z0-9_./-]*/)?[A-Za-z0-9_][A-Za-z0-9_.-]*\.(?:c|h|dts|dtsi|yaml)):"
    r"(\d+)(?:-(\d+))?"
)
# A second range for the same file, written without repeating its name:
#   "... dsim_reg.c:45-90 for the values and :1847-1893 for the order"
ORPHAN = re.compile(r"(?:(?<=\s)|(?<=^)):(\d+)(?:-(\d+))?(?=[\s),.])", re.M)
PATH = re.compile(r"(?<![\w-])((?:drivers|arch|include|Documentation)/[A-Za-z0-9_./{},-]+)")


def lines_of(path):
    with open(path, "rb") as f:
        return f.read().count(b"\n") + 1


def index_sources():
    """basename -> (path, number of lines); vendor trees only.

    Nazwa pliku wystarczy tylko wewnatrz drzew producenta, bo tam pliki leza
    plasko. Cytat do drzewa mainline musi byc pisany PELNA sciezka i jest
    sprawdzany osobno, w resolve_cite: basename "pinctrl-exynos.h" istnieje po
    obu stronach i bez tego rozroznienia cytat do mainline byl sprawdzany
    wzgledem pliku producenta, wiec potrafil przejsc na zlym pliku.
    """
    out = {}
    for sub in ("ds", "ub"):
        d = os.path.join(SRC, sub)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            p = os.path.join(d, name)
            if not os.path.isfile(p):
                continue
            with open(p, "rb") as f:
                n = f.read().count(b"\n") + 1
            out[name] = (os.path.join("sources", sub, name), n)
    return out


def expand_braces(tok):
    """drivers/x/{a.c,b.h} -> [drivers/x/a.c, drivers/x/b.h]"""
    m = re.search(r"\{([^}]*)\}", tok)
    if not m:
        return [tok]
    return [tok[: m.start()] + part + tok[m.end():] for part in m.group(1).split(",")]


def message_and_added(path):
    """Commit message plus added lines: where citations live."""
    keep = []
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith(("diff --git", "index ", "--- ", "+++ ", "@@")):
            continue
        if line.startswith("-"):
            continue
        keep.append(line[1:] if line.startswith("+") else line)
    return "".join(keep)


def main():
    src = index_sources()
    if not src:
        print("check-citations: brak sources/ds, nie mam czego sprawdzac")
        return 2

    targets = []
    pdir = os.path.join(ROOT, "patches")
    for name in sorted(os.listdir(pdir)):
        if name.endswith(".patch"):
            targets.append(os.path.join(pdir, name))
    ddir = os.path.join(ROOT, "docs")
    if os.path.isdir(ddir):
        for name in sorted(os.listdir(ddir)):
            if name.endswith(".md"):
                targets.append(os.path.join(ddir, name))
    # Dokumenty cytujace zrodla leza tez poza docs/: opis jiga w hardware/ i metryki
    # pochodzenia pomiarow w measurements/. Bez tego ich cytaty nie byly sprawdzane,
    # a to ta sama klasa bledu, ktora ta bramka lapie w patchach.
    for extra in ("hardware", "measurements"):
        edir = os.path.join(ROOT, extra)
        if not os.path.isdir(edir):
            continue
        for base, _dirs, files in os.walk(edir):
            for name in sorted(files):
                if name.endswith(".md"):
                    targets.append(os.path.join(base, name))

    bad = []
    n_cite = n_path = 0

    for t in targets:
        rel = os.path.relpath(t, ROOT).replace(os.sep, "/")
        text = message_and_added(t) if t.endswith(".patch") else open(
            t, encoding="utf-8", errors="replace").read()
        # Commit messages wrap long paths after a slash; rejoin them so the path
        # is seen whole instead of as a bare directory plus an orphan basename.
        text = re.sub(r"/[ \t]*\n[ \t*]*", "/", text)

        for tok in PATH.findall(text):
            for one in expand_braces(tok):
                one = one.rstrip(".,;:)")
                if not any(mk in one for mk in VENDOR_MARKERS):
                    continue
                base = one.rsplit("/", 1)[-1]
                if not base or "." not in base:
                    continue  # a directory was named, not a file
                n_path += 1
                if base not in src:
                    bad.append("%s: cytuje %s, ale sources/ nie ma %s"
                               % (rel, one, base))

        # Walk named and orphan citations in the order they appear, so an orphan
        # range is checked against the file named just before it.
        hits = [(m.start(), m.group(1), m.group(2), m.group(3))
                for m in CITE.finditer(text)]
        hits += [(m.start(), None, m.group(1), m.group(2))
                 for m in ORPHAN.finditer(text)]
        hits.sort()

        last = None
        for _, base, a, b in hits:
            if base is not None:
                pelna = os.path.join(ROOT, base.replace("/", os.sep))
                if "/" in base and os.path.isfile(pelna):
                    # Cytat pisany pelna sciezka, takze do drzewa mainline:
                    # sprawdzamy DOKLADNIE ten plik, nie plik o tej nazwie
                    # w drzewie producenta.
                    last = ("plik", base, lines_of(pelna))
                else:
                    # Only vendor basenames are our business; a mainline file
                    # cited by name alone is checked by the doc-ref gate.
                    krotka = base.rsplit("/", 1)[-1]
                    last = ("plik", krotka, src[krotka][1])                         if krotka in src else None
                if last is None:
                    continue
            elif last is None:
                continue  # a bare number, not a continued citation
            base = last[1]
            n_cite += 1
            nlines = last[2]
            for num in (a, b):
                if not num:
                    continue
                if int(num) < 1 or int(num) > nlines:
                    bad.append("%s: cytuje %s:%s, a plik ma %d linii"
                               % (rel, base, num, nlines))

    for b in bad:
        print("  FAIL %s" % b)
    print("check-citations: sciezek downstreamu %d, cytatow z linia %d, bledow %d"
          % (n_path, n_cite, len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
