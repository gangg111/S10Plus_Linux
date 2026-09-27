#!/bin/sh
# Instalacja DeepSeek Harness na telefonie (pmOS, musl, aarch64).  Jako user;
# polecenia wymagajace roota ida przez sudo.
#
# Dlaczego tyle krokow (27.09.2026):
# - npm 11 blokuje skrypty instalacyjne; bez nich node-pty i
#   dsh-subprocess-local nie maja swoich natywnych czesci.
# - node-pty nie ma gotowego pty.node dla linux-arm64, budujemy go.
# - node-addon-require-builtin jest wydany tylko dla glibc (bez zrodel,
#   "fail closed"); binarium linux-arm64-gnu dziala na musl przez gcompat,
#   polozone tam, gdzie loader szuka wersji musl.
set -e
cd "$(dirname "$0")"
V=0.1.7-rc.2
M=/usr/local/lib/node_modules/@deepseek-ai/dsh/node_modules
sudo apk add gcompat build-base linux-headers python3
sudo npm install -g @deepseek-ai/dsh@$V \
	--allow-scripts=@deepseek-ai/dsh-subprocess-local,koffi,node-pty,@google/genai,protobufjs
(cd $M/node-pty && sudo node /usr/lib/node_modules/npm/node_modules/node-gyp/bin/node-gyp.js rebuild --nodedir=/usr)
t=$(mktemp -d)
(cd $t && npm pack node-addon-require-builtin-linux-arm64-gnu@0.1.6 >/dev/null && tar xzf *.tgz)
sudo install -D -m755 $t/package/prebuilt/linux-arm64-gnu-napi-v9.node \
	$M/node-addon-require-builtin/build/napi/napi-v9-linux-arm64-musl/require_builtin.node
rm -rf $t
install -D -m644 dsh-web.service ~/.config/systemd/user/dsh-web.service
install -D -m755 deepseek-harness ~/.local/bin/deepseek-harness
install -D -m644 deepseek-harness.desktop ~/.local/share/applications/deepseek-harness.desktop
install -D -m644 deepseek-harness.qml ~/.local/share/deepseek-harness/deepseek-harness.qml
install -D -m644 icon.png ~/.local/share/icons/hicolor/256x256/apps/deepseek-harness.png
systemctl --user daemon-reload
dsh --version
