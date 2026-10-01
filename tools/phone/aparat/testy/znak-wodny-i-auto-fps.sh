#!/bin/sh
# Test znaku wodnego (zdjecie) i automatycznych kl./s (wideo w ciemnosci).
# Bez ogladania obrazu: tylko statystyki pikseli i metadane; pliki kasowane.
# Uzycie: sh wm-fps-test.sh <watermark true|false> <autoFps true|false>
C=$HOME/.config/Droidian/droidian-camera.conf
python3 - "$C" "$1" "$2" <<'PY'
import configparser, sys
p, wm, af = sys.argv[1:]
c = configparser.RawConfigParser()
c.optionxform = str
c.read(p)
for s in ("Prefs", "AppSettings"):
    if not c.has_section(s):
        c.add_section(s)
c.set("Prefs", "watermark", wm)
c.set("Prefs", "autoFps", af)
c.set("AppSettings", "last-camera", "0")
c.set("AppSettings", "video-fps", "30")
with open(p, "w") as f:
    c.write(f, space_around_delimiters=False)
PY
sh /tmp/aparat-uruchom.sh "" 8 | grep srednia
B=/sys/class/backlight/panel
tap() { [ "$(cat $B/brightness)" -le 1 ] && { python3 /tmp/wfkey.py >/dev/null; sleep 3; }; python3 /tmp/dotyk.py tap $1 $2; sleep ${3:-1.5}; }
P=$HOME/Pictures/droidian-camera
V=$HOME/Videos/droidian-camera
mkdir -p $P $V

echo "== zdjecie (watermark=$1)"
tap 148 983 2
przed=$(ls -t $P | head -1)
s=$(date +%s%N)
tap 240 905 4
f=$(ls -t $P | head -1)
if [ -n "$f" ] && [ "$f" != "$przed" ]; then
	python3 - "$P/$f" <<'PY'
import os, sys
from PIL import Image, ImageOps, ImageStat
im = Image.open(sys.argv[1])
ex = im.getexif()
up = ImageOps.exif_transpose(im).convert("L")
w, h = up.size
side = min(w, h)
def frac(box):
    reg = up.crop(box)
    hist = reg.histogram()
    return sum(hist[245:]) / float(reg.width * reg.height)
lo = (int(side * 0.04), h - int(side * 0.12), int(side * 0.4), h - int(side * 0.035))
hi = (w - int(side * 0.4), h - int(side * 0.12), w - int(side * 0.04), h - int(side * 0.035))
print("plik %d B, %dx%d, EXIF Orientation=%s Make=%s Model=%s DateTime=%s, ExifIFD=%s"
      % (os.path.getsize(sys.argv[1]), im.width, im.height, ex.get(274), ex.get(271), ex.get(272),
         ex.get(306), bool(ex.get_ifd(0x8769))))
print("piksele >=245 w lewym dolnym rogu %.4f, w prawym dolnym %.4f" % (frac(lo), frac(hi)))
PY
	rm -f "$P/$f"
else
	echo "BRAK nowego zdjecia"
	grep -iE "fail|error" /tmp/aparat-app.log | grep -v VDPAU | tail -3
fi

echo "== wideo 6 s (autoFps=$2)"
tap 243 983 3
przed=$(ls -t $V | head -1)
tap 240 905 1
sleep 6
tap 240 905 3
f=$(ls -t $V | head -1)
if [ -n "$f" ] && [ "$f" != "$przed" ]; then
	ffprobe -v error -select_streams v -count_frames -show_entries stream=nb_read_frames:format=duration -of compact "$V/$f"
	ffprobe -v error -select_streams v -show_entries packet=pts_time -of csv=p=0 "$V/$f" | sort -g | python3 -c '
import sys
t = [float(x) for x in sys.stdin if x.strip()]
d = [round((b - a) * 1000) for a, b in zip(t, t[1:])]
from collections import Counter
print("odstepy klatek ms (najczestsze):", Counter(d).most_common(4))
'
	rm -f "$V/$f"
else
	echo "BRAK filmu"
fi
tap 148 983 2
