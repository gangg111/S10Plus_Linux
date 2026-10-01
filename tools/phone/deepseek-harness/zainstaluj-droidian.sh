#!/bin/sh
# Instalacja DeepSeek Harness na telefonie z Droidianem (Debian, glibc,
# aarch64). Uruchamiac NA TELEFONIE jako droidian, z katalogu tego skryptu;
# polecenia roota ida przez sudo. Wersja pod pmOS (musl): zainstaluj.sh.
#
# Kolejnosc (30.09.2026):
# 1. dsh z npm; na glibc node-pty i koffi maja gotowe binaria arm64, wiec
#    obejscia z pmOS (budowa pty.node, gcompat) sa zbedne.
# 2. Konfiguracja ~/.dsh (AGENTS.md, skille, pamiec, polskie wtyczki,
#    logowanie) przychodzi z PC: synchronizuj.sh -k (uruchamiany na PC).
# 3. Profil web z wtyczkami jak profil desktop na PC. Cztery z nich nie
#    deklaruja zgodnosci z dsh 0.2.0-rc.2; zgoda na ryzyko jest jawna,
#    na dokladne wersje.
# 4. Usluga dsh-web i ikona aplikacji (okno Qt WebEngine przez qmlscene).
set -e
cd "$(dirname "$0")"
V=0.2.0-rc.2
W=$HOME/.dsh/profiles/web

sudo apt-get install -y --no-install-recommends build-essential python3 qmlscene-qt6
sudo npm install -g @deepseek-ai/dsh@$V \
	--allow-scripts=@deepseek-ai/dsh-subprocess-local,koffi,node-pty,@google/genai,protobufjs
sudo npm install -g pnpm
dpkg -S libEGL.so.1 libGLESv2.so.2

[ -d "$HOME/.dsh/plugins-pl" ] || { echo "Brak ~/.dsh/plugins-pl: najpierw na PC synchronizuj.sh -k"; exit 1; }
for p in dsh-locale-pl dsh-hud-pl dsh-file-mentions-pl; do
	dsh plugin --profile web add "file:$HOME/.dsh/plugins-pl/$p"
done
grep -q allowBuilds $W/pnpm-workspace.yaml || cat >> $W/pnpm-workspace.yaml <<'EOF'

# Zgoda na skrypt budowania (tsc) tylko dla przejrzanego commita dsh-rewind (jak na PC).
allowBuilds:
  dsh-rewind-plugin@https://codeload.github.com/SiriLee/dsh-rewind/tar.gz/d640b156633e28ffbd6fe0a27ebd5f388e5fe776: true
EOF
for pv in dsh-skill-picker@0.5.12 dsh-rewind-plugin@0.14.0-beta.3 \
	@michengai/dsh-archive-manager@1.0.7 @michengai/dsh-skills-manager@1.1.5; do
	dsh plugin --profile web allow-version "$pv" --dsh-version $V --accept-risk
done
for p in dshmarket dsh-skill-picker @linxin666/dsh-client-ui-git-graph \
	"github:2002XiaoYu/dsh-session-diff#f5b20d0001bb9955c4eebe0f2037507769e55197" \
	"github:SiriLee/dsh-rewind#d640b156633e28ffbd6fe0a27ebd5f388e5fe776" \
	@michengai/dsh-archive-manager@1.0.7 @michengai/dsh-skills-manager@1.1.5; do
	dsh plugin --profile web add "$p"
done
install -m644 dsh/cordis.patch.web.yml $W/cordis.patch.yml

install -D -m644 dsh-web.service ~/.config/systemd/user/dsh-web.service
install -D -m755 deepseek-harness ~/.local/bin/deepseek-harness
sed "s|/home/user|$HOME|g" deepseek-harness.desktop > /tmp/deepseek-harness.desktop
install -D -m644 /tmp/deepseek-harness.desktop ~/.local/share/applications/deepseek-harness.desktop
install -D -m644 deepseek-harness.qml ~/.local/share/deepseek-harness/deepseek-harness.qml
install -D -m644 icon.png ~/.local/share/icons/hicolor/256x256/apps/deepseek-harness.png

# 5. Okno GPU (WebKitGTK, klatki bez kopii). Wymaga Mesy z ../panfrost-kbase/buduj.sh
#    (z latami lata-*.py) i libhybris z ../hybris-fix/buduj.sh; bez nich launcher
#    zostaje przy oknie Qt. Okno nie moze miec TLS (patrz okno.c).
D=$HOME/.local/lib/deepseek-harness
sudo apt-get install -y --no-install-recommends libwebkitgtk-6.0-dev libgtk-4-dev libdrm-dev
cc -O2 okno.c -o /tmp/deepseek-harness-okno $(pkg-config --cflags --libs gtk4 webkitgtk-6.0 libdrm) \
	-Wl,--export-dynamic-symbol=drmGetDevices2,--export-dynamic-symbol=drmFreeDevices
if readelf -lW /tmp/deepseek-harness-okno | grep -q TLS; then echo "okno ma TLS, Mali by padl"; exit 1; fi
install -D -m755 /tmp/deepseek-harness-okno $D/deepseek-harness-okno
H=$HOME/src/hybris-fix/wynik
[ -d $H/libhybris ] && cp -a $H/libEGL_libhybris.so.0 $H/libhybris $H/hybris-lib $D/
systemctl --user daemon-reload
dsh --version
