#!/bin/bash
# Zadaje pytanie Claude (Claude Code CLI w trybie bezokienkowym `claude -p`)
# i wypisuje odpowiedz. Subskrypcja usera, bez klucza API. Uzycie:
#   ask_claude.sh -p "pytanie"
#   ask_claude.sh -f /tmp/pytanie.md -C ~/repo -t read
#   ask_claude.sh -p "a co z X?" -s <id z poprzedniej odpowiedzi>
# Opcje: -p tekst | -f plik z pytaniem, -s sesja, -C katalog roboczy
# (domyslnie biezacy), -t read|none, -m model, -T limit czasu w s (600).
# Wyjscie: pierwsza linia `SESSION: <id>`, potem odpowiedz Claude.
# Kod wyjscia: 0 = odpowiedz, 1 = blad Claude/CLI, 2 = przekroczony czas.
prompt="" file="" session="" cwd="$PWD" tools=read model="" limit=600
while getopts "p:f:s:C:t:m:T:" o; do
	case $o in
	p) prompt=$OPTARG ;; f) file=$OPTARG ;; s) session=$OPTARG ;;
	C) cwd=$OPTARG ;; t) tools=$OPTARG ;; m) model=$OPTARG ;; T) limit=$OPTARG ;;
	*) echo "Nieznana opcja" >&2; exit 1 ;;
	esac
done
[ -n "$file" ] && prompt=$(cat -- "$file")
if [ -z "${prompt// /}" ]; then echo "Podaj -p albo -f." >&2; exit 1; fi

claude=$(command -v claude || echo /usr/local/bin/claude)
[ -x "$claude" ] || { echo "Nie znaleziono claude ($claude)." >&2; exit 1; }

toollist=""
[ "$tools" = read ] && toollist="Read,Grep,Glob"
system="Rozmawiasz z agentem DeepSeek (DeepSeek Harness) pracujacym na telefonie Galaxy S10+ z Droidianem dla Artura. Odpowiadaj po polsku, konkretnie i technicznie, bez dlugich myslnikow. Nie masz uprawnien do zmian w plikach: doradzasz, recenzujesz i odpowiadasz; zmiany wprowadza DeepSeek."

# --strict-mcp-config bez --mcp-config = zero serwerow MCP.
args=(-p --output-format json --strict-mcp-config --tools "$toollist" --append-system-prompt "$system")
[ -n "$toollist" ] && args+=(--allowedTools "$toollist")
[ -n "$session" ] && args+=(--resume "$session")
[ -n "$model" ] && args+=(--model "$model")

out=$(mktemp) err=$(mktemp)
trap 'rm -f "$out" "$err"' EXIT
# zmienne sesji Claude Code rodzica blokowalyby zagniezdzone wywolanie
(cd -- "$cwd" && printf '%s' "$prompt" |
	env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_SSE_PORT \
		timeout -k 5 "$limit" "$claude" "${args[@]}" >"$out" 2>"$err")
rc=$?
if [ $rc -eq 124 ] || [ $rc -eq 137 ]; then
	echo "BLAD: Claude nie odpowiedzial w $limit s (proces ubity)."
	exit 2
fi

python3 - "$out" "$err" "$rc" <<'EOF'
import json, sys
out = open(sys.argv[1], encoding="utf-8", errors="replace").read()
err = open(sys.argv[2], encoding="utf-8", errors="replace").read()
try:
    j = json.loads(out)
except ValueError:
    print("BLAD: niezrozumiala odpowiedz CLI (kod %s)." % sys.argv[3])
    if out: print(out[:2000])
    if err: print(err[:2000])
    sys.exit(1)
print("SESSION: %s" % j.get("session_id"))
if j.get("is_error"):
    print("BLAD (%s): %s" % (j.get("subtype"), j.get("result")))
    sys.exit(1)
print(j.get("result"))
EOF
