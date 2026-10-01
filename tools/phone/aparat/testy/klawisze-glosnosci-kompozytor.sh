#!/bin/sh
# Czy kompozytor zmienia glosnosc klawiszem: na pulpicie (ma zmieniac) i w aparacie (nie ma).
# Glosnosc z amixer (ten sam Master, ktory zmienia skrot wayfire). Na koniec poziom wraca.
echo 1234 | sudo -S -p "" cat /proc/$(pgrep -x plasmashell)/environ | tr '\0' '\n' | grep -vE "^(LISTEN_|INVOCATION_ID|JOURNAL_STREAM|SYSTEMD_EXEC_PID|MANAGERPID|NOTIFY_SOCKET)" > /tmp/sesja.env
E="env -i $(cat /tmp/sesja.env | tr '\n' ' ')"
gl() { $E amixer get Master | grep -o "\[[0-9]*%\]" | head -1; }
B=/sys/class/backlight/panel/brightness
[ "$(cat $B)" -le 1 ] && { python3 /tmp/wfkey.py >/dev/null; sleep 3; }
START=$(gl)
echo "glosnosc na start: $START"
$E amixer -q set Master 50%
echo "== pulpit (bez aparatu)"
echo "przed: $(gl)"; echo 1234 | sudo -S -p "" /tmp/klawisz-glosnosci up; echo "po klawiszu: $(gl)"
$E amixer -q set Master 50%
echo "== aparat aktywny"
sh /tmp/aparat-uruchom.sh "" 8 >/dev/null 2>&1
python3 /tmp/wf-wyjscie.py | grep droidian-camera | cut -c1-60
grep -i "volume keys" /tmp/aparat-app.log | head -2
echo "przed: $(gl)"; echo 1234 | sudo -S -p "" /tmp/klawisz-glosnosci up; echo "po klawiszu: $(gl)"
echo "przed: $(gl)"; echo 1234 | sudo -S -p "" /tmp/klawisz-glosnosci down; echo "po klawiszu w dol: $(gl)"
echo "== aparat zamkniety"
pkill -x droidian-camera; sleep 2
$E amixer -q set Master 50%
echo "przed: $(gl)"; echo 1234 | sudo -S -p "" /tmp/klawisz-glosnosci up; echo "po klawiszu: $(gl)"
$E amixer -q set Master "$(echo $START | tr -d '[]')"
echo "przywrocona: $(gl)"
