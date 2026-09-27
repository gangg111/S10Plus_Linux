#!/bin/sh
# Zwykle "mpv plik" bez opcji: profil [hdr] ma sie wlaczyc sam dla PQ, a dla SDR nie.
export XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0
B=/sys/class/backlight/s6e3ha9
cd ~/narz/hdr || exit 1
cat > /tmp/prof.lua <<'LUA'
mp.add_timeout(4, function()
	local tp = mp.get_property_native("video-target-params") or {}
	io.open("/tmp/prof-wynik.txt", "a"):write(string.format("%s: vo=%s cel=%s/%s/%s zgub=%s\n",
		mp.get_property("filename"), mp.get_property("current-vo", "?"), tostring(tp["gamma"]),
		tostring(tp["primaries"]), tostring(tp["max-luma"]), mp.get_property("frame-drop-count", "?")))
end)
LUA
rm -f /tmp/prof-wynik.txt
for f in hdr10plus.mp4 ~/narz/wideo/test-1080p60.mp4; do
	[ -f "$f" ] || continue
	mpv --fs --no-audio --length=6 --script=/tmp/prof.lua "$f" >/tmp/mpv-prof.log 2>&1 &
	M=$!
	sleep 5
	echo "$(basename $f): panel $(cat $B/actual_brightness)"
	wait $M
done
cat /tmp/prof-wynik.txt
grep -iE "error|profile|krzywa" /tmp/mpv-prof.log | head -5
