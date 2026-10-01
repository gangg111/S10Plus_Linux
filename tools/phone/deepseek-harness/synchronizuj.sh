#!/bin/bash
# Przenosi konfiguracje DeepSeek Harness z PC na telefon (Droidian), jako
# KOPIE, bo lacza do katalogow Windows (junctiony w ~/.dsh na PC) nie
# przejda przez siec. Uruchamiac na PC w Git Bashu, po kazdej zmianie
# skilli albo pamieci Claude, ktora ma trafic na telefon:
#   bash tools/phone/deepseek-harness/synchronizuj.sh
# Co jedzie:
#   ~/.dsh/AGENTS.md          wersja telefonu z tego katalogu (dsh/AGENTS.md)
#   ~/.dsh/skills/            skille z PC (bez PC-owego ask-claude) + ask-claude telefonu
#   ~/.dsh/memory/global,projects  pamiec Claude z PC (nadpisywana w calosci)
#   ~/.dsh/plugins-pl/        polskie wtyczki (locale, hud, file-mentions) bez node_modules
#   ~/.dsh/.credentials.yaml  logowanie do konta DeepSeek (tylko przy -k)
# Nie rusza ~/.dsh/memory/nowe (wpisy zapisane przez DeepSeeka na telefonie)
# ani sesji, profili i ustawien na telefonie.
set -e
TEL=${TEL:-droidian@192.168.0.35}
KLUCZ=${KLUCZ:-$HOME/.ssh/id_s10_phone}
DSH=$HOME/.dsh
HARNESS="$HOME/Documents/Serwis/Programowanie/DeepSeek Harness"
TU=$(cd "$(dirname "$0")" && pwd)
Z_KLUCZEM=0
[ "$1" = -k ] && Z_KLUCZEM=1

S=$(mktemp -d)
trap 'rm -rf "$S"' EXIT
mkdir -p "$S/.dsh/memory" "$S/.dsh/plugins-pl"

# skille: -h rozwija junctiony do realnej tresci
tar -chf - -C "$DSH" --exclude=skills/ask-claude skills | tar -xf - -C "$S/.dsh"
cp -r "$TU/dsh/skills/ask-claude" "$S/.dsh/skills/"
chmod 755 "$S/.dsh/skills/ask-claude/ask_claude.sh"
tar -chf - -C "$DSH/memory" global projects | tar -xf - -C "$S/.dsh/memory"
cp "$TU/dsh/AGENTS.md" "$S/.dsh/AGENTS.md"
for p in dsh-locale-pl dsh-hud-pl dsh-file-mentions-pl; do
	tar -cf - -C "$HARNESS" --exclude=node_modules --exclude=.git "$p" | tar -xf - -C "$S/.dsh/plugins-pl"
done
[ $Z_KLUCZEM = 1 ] && cp "$DSH/.credentials.yaml" "$S/.dsh/.credentials.yaml"

echo "skille: $(ls "$S/.dsh/skills" | wc -l), pamiec projektow: $(ls "$S/.dsh/memory/projects" | wc -l)"
# wysylka przez stdin (odbior plikow przez stdout filtruje tok na telefonie)
tar -czf - -C "$S" .dsh | TOK_RAW=1 ssh -i "$KLUCZ" -o StrictHostKeyChecking=no \
	-o UserKnownHostsFile=/dev/null -o BatchMode=yes "$TEL" '
	set -e
	mkdir -p ~/.dsh/memory/nowe
	rm -rf ~/.dsh/skills ~/.dsh/memory/global ~/.dsh/memory/projects ~/.dsh/plugins-pl
	tar -xzf - -C ~ --no-same-owner
	[ -f ~/.dsh/.credentials.yaml ] && chmod 600 ~/.dsh/.credentials.yaml
	# pnpm kopiuje wtyczki file: do node_modules; odswiez kopie w profilu web
	if [ -f ~/.dsh/profiles/web/package.json ]; then
		for p in dsh-locale-pl dsh-hud-pl dsh-file-mentions-pl; do
			dsh plugin --profile web add "file:$HOME/.dsh/plugins-pl/$p" >/dev/null
		done
		echo "wtyczki PL odswiezone w profilu web (restart aplikacji je wczyta)"
	fi
	echo "telefon: skille $(ls ~/.dsh/skills | wc -l), projekty $(ls ~/.dsh/memory/projects | wc -l), wtyczki PL $(ls ~/.dsh/plugins-pl | tr "\n" " ")"
' 2>/dev/null
