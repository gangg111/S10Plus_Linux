#!/bin/sh
# Firefox na Galaxy S10+: pasek adresu u gory, pasek 30% wiekszy, pelny ekran,
# przyciski omijaja wyciecie aparatu.  Uruchamiac jako user; Firefox zamknac.
set -eu
K=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for p in "$HOME"/.config/mozilla/firefox/*.default*; do
	install -m644 "$K/user.js" "$p/user.js"
	install -D -m644 "$K/userChrome.css" "$p/chrome/userChrome.css"
done
install -m644 "$K/kwinrulesrc" "$HOME/.config/kwinrulesrc"
qdbus6 org.kde.KWin /KWin org.kde.KWin.reconfigure
echo gotowe
