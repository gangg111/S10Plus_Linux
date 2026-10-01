#!/bin/sh
# Ustawienia regionalne telefonu (Droidian) na Polske: jezyk systemu i sesji, strefa
# czasowa Europe/Warsaw, uklad klawiatury fizycznej pl, klawiatura ekranowa pl,
# slowniki pisowni, tlumaczenia Firefoksa i Qt, papier A4. Jednostki metryczne, zegar
# 24 h, przecinek dziesietny i tydzien od poniedzialku wynikaja z pl_PL.
# timedatectl/localectl nie dzialaja (timedated i localed odmawiaja przez D-Bus nawet
# rootowi), wiec pliki sa zapisywane wprost.
# Uzycie: sudo sh region-pl.sh <uzytkownik>   (np. droidian)
# Dowod: date pokazuje CEST/CET, locale pokazuje LANG=pl_PL.UTF-8 w nowym logowaniu,
# dpkg-query -W hunspell-pl firefox-l10n-pl qt6-translations-l10n zwraca wersje.
set -e
U=${1:-droidian}
H=$(getent passwd "$U" | cut -d: -f6)

apt-get install -y hunspell-pl firefox-l10n-pl qt6-translations-l10n manpages-pl

# jezyk systemu (usluga, konsola, logowanie)
grep -q '^pl_PL.UTF-8 UTF-8' /etc/locale.gen || echo 'pl_PL.UTF-8 UTF-8' >> /etc/locale.gen
locale -a | grep -qx pl_PL.utf8 || locale-gen
update-locale LANG=pl_PL.UTF-8 LANGUAGE=pl:en

# strefa czasowa
ln -sf /usr/share/zoneinfo/Europe/Warsaw /etc/localtime
echo Europe/Warsaw > /etc/timezone

# uklad klawiatury fizycznej (USB, Bluetooth) i konsoli
for f in /etc/default/keyboard /etc/vconsole.conf; do
	[ -f $f ] && sed -i 's/^XKBLAYOUT=.*/XKBLAYOUT="pl"/' $f
done

# papier A4 (libpaper)
echo a4 > /etc/papersize

# sesja uzytkownika: formaty i tlumaczenia Plasmy, uklad KWin, slownik KDE,
# klawiatura ekranowa Maliit
sudo -u "$U" sh -s "$H" <<'UZ'
H=$1
C=$H/.config
mkdir -p $C/KDE
kwriteconfig6 --file $C/plasma-localerc --group Formats --key LANG pl_PL.UTF-8
kwriteconfig6 --file $C/plasma-localerc --group Translations --key LANGUAGE pl
kwriteconfig6 --file $C/kxkbrc --group Layout --key LayoutList pl
kwriteconfig6 --file $C/kxkbrc --group Layout --key Use true
kwriteconfig6 --file $C/KDE/Sonnet.conf --group General --key defaultLanguage pl
kwriteconfig6 --file $C/KDE/Sonnet.conf --group General --key preferredLanguages pl
gsettings set org.maliit.keyboard.maliit enabled-languages "['pl']" 2>/dev/null || true
gsettings set org.maliit.keyboard.maliit active-language pl 2>/dev/null || true
UZ
echo "gotowe: $(date '+%Z %z'), $(cat /etc/default/locale | tr '\n' ' ')"
