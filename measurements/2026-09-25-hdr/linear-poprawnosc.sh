#!/bin/sh
# Ten sam kadr (nieruchoma tresc, 2,5 s) bez i z PAN_MESA_DEBUG=linear.
export XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0
cd ~/narz/hdr || exit 1
echo 'mp.add_timeout(2.5, function() mp.commandv("screenshot-to-file", os.getenv("ZRZUT"), "window") end)' > /tmp/z.lua
ZRZUT=/tmp/dyn-jasna.png mpv --fs --no-audio --length=4 --script=/tmp/z.lua statyczny.mp4 >/dev/null 2>&1
ZRZUT=/tmp/dyn-ciemna.png PAN_MESA_DEBUG=linear mpv --fs --no-audio --length=4 --script=/tmp/z.lua statyczny.mp4 >/dev/null 2>&1
python3 porownaj_png.py "tiled-vs-linear"
