#!/bin/sh
# Nagrywanie w zadanym kodeku, rozmiarze i klatkazu: ustawia klucze QSettings
# (te same, ktore zapisuja przyciski), uruchamia aplikacje, nagrywa 4 s, sprawdza ffprobe.
# Uzycie: sh aparat-wideo.sh <hevc true|false> <szer> <wys> <fps>
C=$HOME/.config/Droidian/droidian-camera.conf
python3 - "$C" "$1" "$2" "$3" "$4" <<'PY'
import configparser, sys
p, hevc, w, h, fps = sys.argv[1:]
c = configparser.RawConfigParser()
c.optionxform = str
c.read(p)
for s in ("AppSettings", "Camera0"):
    if not c.has_section(s):
        c.add_section(s)
c.set("AppSettings", "hevc", hevc)
c.set("AppSettings", "video-fps", fps)
c.set("Camera0", "lastVideoSize", "@Size(%s %s)" % (w, h))
c.set("AppSettings", "last-camera", "0")
with open(p, "w") as f:
    c.write(f, space_around_delimiters=False)
PY
sh /tmp/aparat-uruchom.sh "" 8 >/dev/null
B=/sys/class/backlight/panel
tap() { [ "$(cat $B/brightness)" -le 1 ] && { python3 /tmp/wfkey.py >/dev/null; sleep 3; }; python3 /tmp/dotyk.py tap $1 $2; sleep ${3:-1.5}; }
V=$HOME/Videos/droidian-camera
tap 243 983 3
przed=$(ls -t $V | head -1)
tap 240 905 1
sleep 4
tap 240 905 3
f=$(ls -t $V | head -1)
if [ -n "$f" ] && [ "$f" != "$przed" ]; then
	echo "plik $(stat -c %s "$V/$f") B"
	ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,avg_frame_rate:format=duration -of compact "$V/$f"
	rm -f "$V/$f"
else
	echo "BRAK filmu"
	grep -iE "record|fail" /tmp/aparat-app.log | tail -3
	echo 1234 | sudo -S -p "" /android/system/bin/logcat -d -t 800 2>/dev/null | grep -E " E (CameraSource|MediaRecorder|StagefrightRecorder|ACodec)" | tail -3
fi
