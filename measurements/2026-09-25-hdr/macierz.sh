#!/bin/sh
# Zgubione klatki: 4 pliki x (domyslnie, PAN_MESA_DEBUG=linear). Profil HDR
# wlacza sie sam (hdr-auto.lua), SDR idzie przez vo=gpu.
export XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0
cd ~/narz/hdr || exit 1
cat > /tmp/k.lua <<'LUA'
mp.add_timeout(9.5, function()
	io.open("/tmp/k-wynik.txt", "a"):write(string.format("%-28s %-6s vo=%-8s klatek=%s zgub-vo=%s zgub-dek=%s\n",
		mp.get_property("filename"), os.getenv("PAN_MESA_DEBUG") or "-", mp.get_property("current-vo", "?"),
		mp.get_property("estimated-frame-number", "?"), mp.get_property("frame-drop-count", "?"),
		mp.get_property("decoder-frame-drop-count", "?")))
end)
LUA
rm -f /tmp/k-wynik.txt
for f in hdr10plus-3840x2160.mp4 hdr10plus-2560x1440.mp4 hdr10plus.mp4 ../wideo/test-1080p60.mp4; do
	mpv --fs --no-audio --length=10 --script=/tmp/k.lua $f >/dev/null 2>&1
	PAN_MESA_DEBUG=linear mpv --fs --no-audio --length=10 --script=/tmp/k.lua $f >/dev/null 2>&1
done
cat /tmp/k-wynik.txt
