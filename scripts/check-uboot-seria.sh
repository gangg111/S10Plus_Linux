#!/bin/sh
# Bramka: seria bootloadera w patches-uboot/ jest tym, co lezy w drzewie.
#
# Po co ona istnieje. Seria jadra ma taka bramke od dawna (verify.sh, punkt 1)
# i to ona pilnuje, ze patche, czyli jedyny artefakt, ktory sie wysyla, niosa
# dokladnie ten kod, ktory sprawdzaja wszystkie pozostale bramki. Seria
# bootloadera nie miala jej wcale, i skonczylo sie dokladnie tak, jak musialo:
# 21.09.2026 w drzewie U-Boota lezalo 2391 linii poza jakimkolwiek commitem
# plus commit opisany jako WIP, ktory sam o sobie pisal, ze przed wysylka
# trzeba go rozlozyc na patche. Przez ten czas patches-uboot/README.md
# twierdzil, ze "port jest kompletny, osiem patchy". Bramki liczbowe tego nie
# widzialy, bo czytaja drzewo robocze, a nie patche.
#
# Cztery rzeczy, kazda osobno:
#   1. seria stosuje sie po kolei na przypieta baze upstreamu;
#   2. drzewo, ktore z tego wychodzi, jest identyczne z drzewem roboczym;
#   3. drzewo robocze nie ma nic poza seria;
#   4. checkpatch U-Boota: zero bledow, reszta pod pulapem.
#
# Uzycie:  scripts/check-uboot-seria.sh
# Kod:     0 w normie, 1 regresja, 2 bramka NIE URUCHOMIONA (to NIE jest
#          zielone swiatlo)
set -u

UB=${UBOOT_TREE:-$HOME/u-boot-upstream}
BAZA=211de43d0f954a00a490220c1aac9db298287c40

# Drzewo bootloadera zyje w WSL, tak samo jak przy bramce analizy statycznej.
if [ ! -d "$UB" ]; then
	if command -v wsl.exe >/dev/null 2>&1; then
		exec wsl.exe -d Debian -u pm -- sh \
			"//mnt/c/Users/Artur/Documents/Serwis/Programowanie/S10Plus_Linux/scripts/check-uboot-seria.sh"
	fi
	echo "check-uboot-seria: BRAMKA NIEURUCHOMIONA, brak drzewa U-Boota (UBOOT_TREE)"
	exit 2
fi

ROOT=/mnt/c/Users/Artur/Documents/Serwis/Programowanie/S10Plus_Linux
[ -d "$ROOT" ] || ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
KAT="$ROOT/patches-uboot"
LOG="$ROOT/build-logs"
GOLD="$ROOT/scripts/golden"
[ -d "$KAT" ] || {
	echo "check-uboot-seria: BRAMKA NIEURUCHOMIONA, brak $KAT"
	exit 2
}
git -C "$UB" cat-file -e "$BAZA^{commit}" 2>/dev/null || {
	echo "check-uboot-seria: BRAMKA NIEURUCHOMIONA, drzewo nie zna bazy $BAZA"
	exit 2
}

rc=0
n=$(ls "$KAT"/*.patch 2>/dev/null | wc -l | tr -d ' ')

# --- 1. seria stosuje sie na przypieta baze ------------------------------
# Przez wlasny indeks, zeby nie dotykac drzewa roboczego: bramka ma tylko
# patrzec, nigdy niczego nie przestawiac.
IDX=$(mktemp); rm -f "$IDX"
GIT_INDEX_FILE="$IDX" git -C "$UB" read-tree "$BAZA" 2>/dev/null
nalozone=0
padlo=""
for p in "$KAT"/*.patch; do
	if GIT_INDEX_FILE="$IDX" git -C "$UB" apply --cached \
	   --whitespace=nowarn "$p" 2>/dev/null; then
		nalozone=$((nalozone + 1))
	else
		padlo=$(basename "$p")
		break
	fi
done

if [ -z "$padlo" ] && [ "$nalozone" = "$n" ]; then
	echo "check-uboot-seria: seria stosuje sie na $nalozone/$n"
else
	echo "check-uboot-seria: seria PADLA na $padlo ($nalozone/$n)"
	rc=1
fi

# --- 2. to, co z serii wychodzi, kontra drzewo robocze -------------------
# Porownujemy TRESC plikow, ktore rusza seria. Samo porownanie skrotow drzew
# nie zadziala, bo czesc plikow ma na tym systemie inne prawa niz w bazie.
if [ -z "$padlo" ]; then
	DRZEWO=$(GIT_INDEX_FILE="$IDX" git -C "$UB" write-tree 2>/dev/null)
	rozjazd=""
	for f in $(git -C "$UB" diff --name-only "$BAZA" "$DRZEWO"); do
		a=$(git -C "$UB" rev-parse "$DRZEWO:$f" 2>/dev/null)
		b=$(git -C "$UB" hash-object "$UB/$f" 2>/dev/null)
		[ "$a" = "$b" ] || rozjazd="$rozjazd $f"
	done
	if [ -z "$rozjazd" ]; then
		echo "check-uboot-seria: seria daje dokladnie drzewo robocze"
	else
		echo "check-uboot-seria: seria kontra drzewo, rozjazd:$rozjazd"
		rc=1
	fi
fi
rm -f "$IDX"

# --- 3. drzewo robocze nie ma nic poza seria -----------------------------
brud=$(git -C "$UB" status --porcelain 2>/dev/null)
if [ -z "$brud" ]; then
	echo "check-uboot-seria: drzewo robocze nie ma nic poza seria"
else
	echo "check-uboot-seria: poza seria lezy:"
	printf '%s\n' "$brud" | sed 's/^/    /' | head -20
	rc=1
fi

# --- 4. checkpatch -------------------------------------------------------
if command -v perl >/dev/null 2>&1 && [ -f "$UB/scripts/checkpatch.pl" ]; then
	CP="$LOG/78-uboot-checkpatch.log"
	: > "$CP"
	for p in "$KAT"/*.patch; do
		echo "########## $(basename "$p")" >> "$CP"
		( cd "$UB" && perl scripts/checkpatch.pl --strict --no-signoff \
		  "$p" ) >> "$CP" 2>&1
	done
	# Martwy checkpatch wypisuje zero wszystkiego i zaliczalby bramke,
	# wiec najpierw liczymy podsumowania.
	suma=$(grep -c "^total: " "$CP" 2>/dev/null); suma=${suma:-0}
	if [ "$suma" != "$n" ]; then
		echo "check-uboot-seria: checkpatch przeliczyl $suma z $n latek"
		rc=1
	fi
	err=$(grep -c "^ERROR:" "$CP" 2>/dev/null); err=${err:-0}
	war=$(grep -c "^WARNING:" "$CP" 2>/dev/null); war=${war:-0}
	chk=$(grep -c "^CHECK:" "$CP" 2>/dev/null); chk=${chk:-0}
	echo "check-uboot-seria: checkpatch errors=$err warnings=$war checks=$chk"
	if [ "$err" != 0 ]; then
		echo "check-uboot-seria: checkpatch ma $err bledow, pulap 0"
		rc=1
	fi
	for para in "warnings:$war:checkpatch-uboot-warnings.max" \
		    "checks:$chk:checkpatch-uboot-checks.max"; do
		nazwa=$(echo "$para" | cut -d: -f1)
		ile=$(echo "$para" | cut -d: -f2)
		plik=$(echo "$para" | cut -d: -f3)
		if [ "${1:-}" = "--update-golden" ]; then
			echo "$ile" > "$GOLD/$plik"
			echo "check-uboot-seria: ZAPIS $nazwa -> $ile"
			continue
		fi
		if [ ! -f "$GOLD/$plik" ]; then
			echo "check-uboot-seria: brak scripts/golden/$plik"
			rc=1
			continue
		fi
		max=$(cat "$GOLD/$plik")
		if [ "$ile" -gt "$max" ]; then
			echo "check-uboot-seria: $nazwa $ile, pulap $max"
			rc=1
		fi
	done
	# Log zostaje takze po zielonym przebiegu: te 19 ostrzezen i 8 uwag to
	# tlo, ktore trzeba miec jak obejrzec, zeby wiedziec, co wolno jeszcze
	# z niego zdjac. Seria jadra trzyma swoj log checkpatcha tak samo.
else
	echo "check-uboot-seria: BRAMKA NIEURUCHOMIONA, brak perla albo checkpatcha"
	exit 2
fi

[ "$rc" = 0 ] && echo "check-uboot-seria: latek $n, wszystko w normie"
exit $rc
