#!/bin/sh
# Testy funkcjonalne aplikacji aparatu stukaniem (wspolrzedne ekranu, okno od y=67),
# bez ogladania obrazu: metadane zdjecia i filmu, logi ostrosci i zmiany kamery.
# Pliki testowe sa usuwane po odczycie.
B=/sys/class/backlight/panel
obudz() { [ "$(cat $B/brightness)" -le 1 ] && { python3 /tmp/wfkey.py >/dev/null; sleep 3; }; }
tap() { obudz; python3 /tmp/dotyk.py tap $1 $2; sleep ${3:-1.5}; }
LOG=/tmp/aparat-app.log
P=$HOME/Pictures/droidian-camera
V=$HOME/Videos/droidian-camera
mkdir -p $P $V
nowy() { ls -t $1 2>/dev/null | head -1; }

echo "== zdjecie"
tap 148 983 2
przed=$(nowy $P)
tap 240 905 4
f=$(nowy $P)
if [ -n "$f" ] && [ "$f" != "$przed" ]; then
	python3 - "$P/$f" <<'PY'
import sys
from PIL import Image
im = Image.open(sys.argv[1])
ex = im.getexif()
q = im.quantization
print("plik %d B, %dx%d, EXIF Orientation=%s Make=%s Model=%s, tablica kwantyzacji luminancji[0..3]=%s"
      % (__import__('os').path.getsize(sys.argv[1]), im.width, im.height, ex.get(274), ex.get(271), ex.get(272),
         list(q[0])[:4] if q else None))
PY
	rm -f "$P/$f"
else
	echo "BRAK nowego zdjecia"
fi

echo "== stukniecie do ostrosci"
tap 240 400
tap 90 250
grep "Focus/metering area" $LOG | tail -2

echo "== obiektyw .5 i z powrotem 1x"
tap 171 807 3
tap 217 807 3
grep "Camera changed" $LOG | tail -3

echo "== wideo FHD"
tap 243 983 3
przed=$(nowy $V)
tap 240 905 1
sleep 4
tap 240 905 3
f=$(nowy $V)
if [ -n "$f" ] && [ "$f" != "$przed" ]; then
	ls -la "$V/$f" | awk '{print "plik", $5, "B"}'
	ffprobe -v error -show_entries stream=codec_name,width,height,avg_frame_rate:format=duration -of compact "$V/$f" 2>&1 | head -4
	rm -f "$V/$f"
else
	echo "BRAK nowego filmu"
fi
tap 148 983 2
grep -iE "record|error|fail" $LOG | grep -v VDPAU | tail -5
