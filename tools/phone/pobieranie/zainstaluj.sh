#!/bin/sh
# Install Pobieranie on the phone. Run ON THE PHONE as droidian, from a directory with:
#   pobieranie (binary), jdapi-proxy.py, jdapi-proxy.service, jdapi-firewall.service,
#   jdownloader.service, pl.s10plus.pobieranie.desktop
# JDownloader 2 itself: ~/jd2/JDownloader.jar, Java in /opt/java (see README.md).
set -e
cd "$(dirname "$0")"
su_() { echo 1234 | sudo -S -p "" "$@"; }

# 1. the group whose sockets may reach JD2's API port
getent group jdapi >/dev/null || su_ groupadd --system jdapi

# 2. proxy and firewall (system units)
su_ install -m 755 jdapi-proxy.py /usr/lib/s10plus/jdapi-proxy.py
su_ install -m 644 jdapi-proxy.service jdapi-firewall.service /etc/systemd/system/
su_ systemctl daemon-reload
su_ systemctl enable --now jdapi-firewall.service jdapi-proxy.service

# 3. JD2 as a user service: the API on, localhost only
python3 - <<'EOF'
import json, os
p = os.path.expanduser("~/jd2/cfg/org.jdownloader.api.RemoteAPIConfig.json")
c = json.load(open(p)) if os.path.exists(p) else {}
c.update({"deprecatedapienabled": True, "deprecatedapilocalhostonly": True, "deprecatedapiport": 3128})
json.dump(c, open(p, "w"))
EOF
for p in $(pgrep -f "bin/java.*JDownloader.jar"); do kill "$p"; done
for i in $(seq 30); do pgrep -f "bin/java.*JDownloader.jar" >/dev/null || break; sleep 1; done
mkdir -p ~/.config/systemd/user
install -m 644 jdownloader.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user start jdownloader.service

# 4. the app; the Swing launcher leaves the menu (its window is unusable on the phone)
su_ install -m 755 pobieranie /usr/local/bin/pobieranie
mkdir -p ~/.local/share/applications
install -m 644 pl.s10plus.pobieranie.desktop ~/.local/share/applications/
# JD2's original logo (512x512 file, "256" only in its name) from its own theme
LOGO=$HOME/jd2/themes/standard/org/jdownloader/images/logo
install -D -m 644 "$LOGO/jd_logo_256_256.png" ~/.local/share/icons/hicolor/512x512/apps/jdownloader.png
install -D -m 644 "$LOGO/jd_logo_128_128.png" ~/.local/share/icons/hicolor/128x128/apps/jdownloader.png
install -D -m 644 "$LOGO/jd_logo_64_64.png" ~/.local/share/icons/hicolor/64x64/apps/jdownloader.png
touch ~/.local/share/icons/hicolor
rm -f ~/.local/share/applications/jdownloader2.desktop
echo "zainstalowane"
