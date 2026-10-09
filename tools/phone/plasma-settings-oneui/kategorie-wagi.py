#!/usr/bin/env python3
# Copies of the top level plasma-settings categories with One UI order weights, written to
# <out>/plasma-settings/categories (an XDG data dir earlier than /usr/share).
import os, re, sys
WAGI = {"settings-network.desktop": 5, "settings-hardware.desktop": 6, "settings-hardware-input.desktop": 8,
        "settings-applications.desktop": 9, "settings-appearance.desktop": 12, "settings-personalization.desktop": 14}
src, out = sys.argv[1], sys.argv[2]
d = os.path.join(out, "plasma-settings", "categories")
os.makedirs(d, exist_ok=True)
for f, w in WAGI.items():
    s = open(os.path.join(src, f), encoding="utf-8").read()
    s, n = re.subn(r"^X-KDE-Weight=\d+$", "X-KDE-Weight=%d" % w, s, flags=re.M)
    assert n == 1, f
    open(os.path.join(d, f), "w", encoding="utf-8").write(s)
    print(f, w)
