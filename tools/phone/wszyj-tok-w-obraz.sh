#!/bin/sh
# Wszywa tok w obraz pmOS, zeby filtr przetrwal wgranie.
#
# Po co.  Na telefonie da sie tok zainstalowac recznie w minute, ale kazde
# wgranie obrazu kasuje partycje uzytkownika i filtr znika razem z nia.
# Skoro ma dzialac "od strzala", bez proszenia i bez pamietania o nim, to
# musi jechac razem z obrazem.
#
# Co wklada:
#   ~/.local/bin/tok        statyczna binarka aarch64 (musl, bez zaleznosci)
#   ~/.local/bin/tok-ssh    opakowanie polecen przychodzacych po SSH
#   ~/.ssh/authorized_keys  klucz roboczy z wymuszonym filtrem
#                           plus klucz ratunkowy bez filtra
#
# Uruchamiac jako root w WSL, bo montuje obraz przez urzadzenie petlowe:
#   wsl.exe -d Debian -u root -- sh tools/phone/wszyj-tok-w-obraz.sh
set -e

D=/mnt/d/S10Plus-pmos
SUROWY=$D/pmos-nasza-seria.img
ROOT=/mnt/pmos-root
OFS_ROOT=511705088
LEN_ROOT=771751936

# Artefakty przygotowane po stronie Windows: binarka i klucze.
PRZYBORY=${PRZYBORY:?ustaw PRZYBORY na katalog z tok-aarch64, tok-ssh, s10.pub, s10-ratunek.pub}

for p in tok-aarch64 tok-ssh s10.pub s10-ratunek.pub; do
	[ -f "$PRZYBORY/$p" ] || { echo "brak $PRZYBORY/$p"; exit 1; }
done

umount "$ROOT" 2>/dev/null || true
losetup -D 2>/dev/null || true
mkdir -p "$ROOT"
P=$(losetup --find --show --offset $OFS_ROOT --sizelimit $LEN_ROOT "$SUROWY")
trap 'umount "$ROOT" 2>/dev/null || true; losetup -d "$P" 2>/dev/null || true' EXIT
mount "$P" "$ROOT"

DOM="$ROOT/home/user"
[ -d "$DOM" ] || { echo "w obrazie nie ma /home/user"; exit 1; }

# Numer uzytkownika CZYTAMY z obrazu, nigdy nie wpisujemy z palca.
# postmarketOS daje kontu `user` numer 10000, a nie 1000 jak Debian, a sshd
# przy niezgodnym wlascicielu katalogu .ssh po prostu nie czyta pliku
# z kluczami i odpowiada zwyklym "Permission denied (publickey)". Objaw nie
# wskazuje na przyczyne, wiec lepiej, zeby ta liczba w ogole nie byla
# zgadywana.
UID_USER=$(awk -F: '$1 == "user" { print $3 }' "$ROOT/etc/passwd")
GID_USER=$(awk -F: '$1 == "user" { print $4 }' "$ROOT/etc/passwd")
[ -n "$UID_USER" ] && [ -n "$GID_USER" ] || {
	echo "nie umiem odczytac numeru konta user z /etc/passwd obrazu"
	exit 1
}
echo "== konto user w obrazie: $UID_USER:$GID_USER =="

echo "== narzedzie =="
install -d -m 0755 -o "$UID_USER" -g "$GID_USER" \
	"$DOM/.local" "$DOM/.local/bin"
install -m 0755 -o "$UID_USER" -g "$GID_USER" \
	"$PRZYBORY/tok-aarch64" "$DOM/.local/bin/tok"
# CRLF zabilby skrypt powloki i to bez czytelnego bledu, wiec konwersja
# jest tu obowiazkowa, a nie ostroznosciowa.
tr -d '\r' < "$PRZYBORY/tok-ssh" > "$DOM/.local/bin/tok-ssh"
chmod 0755 "$DOM/.local/bin/tok-ssh"
chown "$UID_USER:$GID_USER" "$DOM/.local/bin/tok-ssh"
printf '  tok      %s B\n' "$(stat -c %s "$DOM/.local/bin/tok")"
printf '  tok-ssh  %s B\n' "$(stat -c %s "$DOM/.local/bin/tok-ssh")"

echo
echo "== klucze =="
install -d -m 0700 -o "$UID_USER" -g "$GID_USER" "$DOM/.ssh"
{
	echo "# Klucz roboczy: KAZDE polecenie przechodzi przez tok, bez wiedzy"
	echo "# strony wolajacej. Ominiecie na zadanie: przedrostek TOK_RAW=1."
	printf 'command="/home/user/.local/bin/tok-ssh",no-agent-forwarding,no-port-forwarding,no-X11-forwarding %s\n' \
		"$(cat "$PRZYBORY/s10.pub")"
	echo "# Klucz ratunkowy: BEZ filtra. Do przesylania plikow (sftp/scp),"
	echo "# bo ten telefon nie ma binarki scp i transfer idzie podsystemem"
	echo "# sftp, ktorego wymuszone polecenie nie przepuszcza. Sluzy takze"
	echo "# za wyjscie awaryjne, gdyby opakowanie kiedys sie zepsulo."
	cat "$PRZYBORY/s10-ratunek.pub"
} > "$DOM/.ssh/authorized_keys"
chmod 0600 "$DOM/.ssh/authorized_keys"
chown "$UID_USER:$GID_USER" "$DOM/.ssh/authorized_keys"
printf '  kluczy w pliku: %s\n' "$(grep -c "ssh-ed25519" "$DOM/.ssh/authorized_keys")"

echo
echo "== kontrola =="
zly=0
for p in "$DOM/.ssh" "$DOM/.ssh/authorized_keys" "$DOM/.local/bin/tok" \
	 "$DOM/.local/bin/tok-ssh"; do
	w=$(stat -c '%u:%g' "$p")
	if [ "$w" != "$UID_USER:$GID_USER" ]; then
		echo "  ZLY WLASCICIEL $w (ma byc $UID_USER:$GID_USER): $p"
		zly=1
	fi
done
[ "$zly" = 0 ] && echo "  wlasciciel wszedzie zgodny z kontem user"
[ "$zly" = 0 ] || exit 1
ls -l "$DOM/.local/bin/" | sed 's/^/  /'
head -1 "$DOM/.local/bin/tok-ssh" | sed 's/^/  pierwszy wiersz opakowania: /'
od -c "$DOM/.local/bin/tok-ssh" | head -1 | grep -q '\\r' \
	&& { echo "  BLAD: zostal znak CR"; exit 1; } \
	|| echo "  konce linii czyste"

umount "$ROOT"
losetup -d "$P"
trap - EXIT
echo
echo "tok wszyty w $SUROWY"
