#!/bin/sh
# Firefox na Droidianie: pasek adresu u gory. mobile-config-firefox 4.3 sklada
# userChrome.css przy kazdym starcie z fragmentow z userChrome.files, wiec nasz
# fragment dopisujemy na koniec tej listy. Uruchamiac jako user z sudo.
set -eu
K=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
M=/etc/mobile-config-firefox
sudo install -m644 "$K/s10plus-pasek-u-gory.css" "$M/userChrome/s10plus-pasek-u-gory.css"
grep -qx "userChrome/s10plus-pasek-u-gory.css" "$M/userChrome.files" ||
	echo "userChrome/s10plus-pasek-u-gory.css" | sudo tee -a "$M/userChrome.files" >/dev/null
echo "gotowe; zmiana po ponownym uruchomieniu Firefoksa"
