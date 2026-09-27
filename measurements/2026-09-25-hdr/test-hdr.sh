#!/bin/sh
# Odtwarzanie HDR10+ cala sciezka: mpv gpu-next (ST 2094-40), podpowiedz dla
# KWin, EDR (podbicie panelu). Probki jasnosci panelu co 0,5 s.
export XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0
B=/sys/class/backlight/s6e3ha9
cd ~/narz/hdr || exit 1
cat > /tmp/hdr.lua <<'LUA'
local f = io.open("/tmp/hdr-wynik.txt", "w")
local function zrzut(t)
	local vp = mp.get_property_native("video-params") or {}
	local tp = mp.get_property_native("video-target-params") or {}
	f:write(string.format("t=%s gamma=%s prim=%s max-luma=%s scene-max-r=%s scene-max-g=%s scene-max-b=%s scene-avg=%s max-pq-y=%s avg-pq-y=%s | cel: gamma=%s prim=%s max-luma=%s | vo=%s zgub=%s\n",
		t, tostring(vp["gamma"]), tostring(vp["primaries"]), tostring(vp["max-luma"]),
		tostring(vp["scene-max-r"]), tostring(vp["scene-max-g"]), tostring(vp["scene-max-b"]),
		tostring(vp["scene-avg"]), tostring(vp["max-pq-y"]), tostring(vp["avg-pq-y"]),
		tostring(tp["gamma"]), tostring(tp["primaries"]), tostring(tp["max-luma"]),
		mp.get_property("current-vo", "?"), mp.get_property("frame-drop-count", "?")))
	f:flush()
end
mp.add_timeout(2.5, function() zrzut(2.5) end)
mp.add_timeout(7.5, function() zrzut(7.5) end)
LUA
echo "przed: panel $(cat $B/actual_brightness) z $(cat $B/max_brightness)"
${MPV:-mpv} -v --fs --no-audio --length=10 ${MPV_VO:---vo=gpu-next --egl-output-format=rgb10_a2} --target-colorspace-hint=yes \
	--target-colorspace-hint-mode=${MPV_HINT:-source-dynamic} \
	--script=/tmp/hdr.lua hdr10plus.mp4 >/tmp/mpv-hdr.log 2>&1 &
M=$!
for i in $(seq 1 22); do
	printf '%s ' "$(cat $B/actual_brightness)"
	sleep 0.5
done
echo
wait $M
cat /tmp/hdr-wynik.txt
sleep 2
echo "po: panel $(cat $B/actual_brightness)"
grep -iE "error|fail|hdr|color" /tmp/mpv-hdr.log | head -5
