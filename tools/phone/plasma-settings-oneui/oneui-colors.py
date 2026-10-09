#!/usr/bin/env python3
# One UI Dark colour scheme for plasma-settings, derived from Breeze Dark: only the
# backgrounds and the accent change (black page, #171719 cards, One UI blue).
# Usage: oneui-colors.py BreezeDark.colors OneUiDark.colors
import re, sys

TLA = {
    "Window": (("BackgroundNormal", "1,1,1"), ("BackgroundAlternate", "23,23,25")),
    "View": (("BackgroundNormal", "23,23,25"), ("BackgroundAlternate", "23,23,25")),
    "Header": (("BackgroundNormal", "1,1,1"), ("BackgroundAlternate", "1,1,1")),
    "Header][Inactive": (("BackgroundNormal", "1,1,1"), ("BackgroundAlternate", "1,1,1")),
    "Button": (("BackgroundNormal", "42,42,46"), ("BackgroundAlternate", "30,70,150")),
    "Complementary": (("BackgroundNormal", "1,1,1"), ("BackgroundAlternate", "23,23,25")),
    "Tooltip": (("BackgroundNormal", "35,35,37"), ("BackgroundAlternate", "23,23,25")),
    "Selection": (("BackgroundNormal", "55,122,255"), ("BackgroundAlternate", "30,70,150")),
}
AKCENT = "55,122,255"

src, dst = sys.argv[1], sys.argv[2]
out, sekcja = [], None
for line in open(src, encoding="utf-8").read().splitlines():
    m = re.match(r"^\[Colors:(.+)\]$", line)
    if m:
        sekcja = m.group(1)
    elif line.startswith("["):
        sekcja = None
    k = line.split("=", 1)[0]
    if sekcja in TLA and dict(TLA[sekcja]).get(k):
        line = "%s=%s" % (k, dict(TLA[sekcja])[k])
    elif sekcja and k in ("DecorationFocus", "DecorationHover"):
        line = "%s=%s" % (k, AKCENT)
    elif line.startswith("Name="):
        line = "Name=One UI Dark"
    elif line.startswith("Name["):
        continue
    out.append(line)
open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("zapisano", dst)
