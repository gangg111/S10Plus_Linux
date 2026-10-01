#!/bin/sh
# Zrzut okna aparatu do /tmp/<nazwa>.png (480 px szerokosci), po opcjonalnych stuknieciach.
# Uzycie: sh ui-zrzut.sh <nazwa> ["tap x y" | "swipe x0 y0 x1 y1" ...]
n=$1; shift
B=/sys/class/backlight/panel
[ "$(cat $B/brightness)" -le 1 ] && { python3 /tmp/wfkey.py >/dev/null; sleep 3; }
for a in "$@"; do
	set -- $a
	case $1 in
	tap) python3 /tmp/dotyk.py tap $2 $3 ;;
	swipe) python3 /tmp/machniecie.py $2 $3 $4 $5 ;;
	wait) sleep $2 ;;
	esac
	sleep 1.2
done
ID=$(python3 /tmp/wfviews.py | awk '/droidian-camera/ && /mapped True/ {print $1; exit}')
python3 /tmp/wfcall.py podglad/capture "{\"view-id\": $ID, \"file\": \"/tmp/$n.ppm\", \"scale\": 2}" >/dev/null
python3 -c "from PIL import Image; im=Image.open('/tmp/$n.ppm'); im.resize((480, round(im.height*480/im.width))).save('/tmp/$n.png')"
rm -f /tmp/$n.ppm
