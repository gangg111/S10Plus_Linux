#!/bin/sh
# Dowod, ze metadane dynamiczne HDR10+ zmieniaja obraz: ta sama NIERUCHOMA
# tresc w obu scenach, rozne metadane. Zrzut okna mpv w scenie jasnej i ciemnej;
# st2094-40 (dynamiczne) ma dac rozne zrzuty, bt.2390 (statyczne) identyczne.
export XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0
cd ~/narz/hdr || exit 1
if [ ! -f statyczny.mp4 ]; then
	ffmpeg -hide_banner -loglevel error -y -f lavfi -i "smptehdbars=size=1920x1080:rate=24,format=yuv420p10le" -t 10 \
		-c:v libx265 -preset fast -x265-params "log-level=error:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:range=limited:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):max-cll=1000,400:hdr10=1:repeat-headers=1" \
		-f hevc stat.hevc
	python3 wstrzyknij_hdr10plus.py stat.hevc meta.json stat10p.hevc
	ffmpeg -hide_banner -loglevel error -y -r 24 -i stat10p.hevc -c copy -tag:v hvc1 -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc statyczny.mp4
fi
cat > /tmp/zrzut.lua <<'LUA'
mp.add_timeout(2.5, function() mp.commandv("screenshot-to-file", "/tmp/dyn-jasna.png", "window") end)
mp.add_timeout(7.5, function() mp.commandv("screenshot-to-file", "/tmp/dyn-ciemna.png", "window") end)
LUA
for tm in st2094-40 bt.2390; do
	rm -f /tmp/dyn-*.png
	/usr/local/bin/mpv --fs --no-audio --length=9 --vo=gpu-next --egl-output-format=rgb10_a2 \
		--target-trc=pq --target-prim=bt.2020 --target-peak=800 --target-colorspace-hint=yes \
		--target-colorspace-hint-strict=no --hdr-compute-peak=no --tone-mapping=$tm \
		--script=/tmp/zrzut.lua statyczny.mp4 >/tmp/mpv-dyn.log 2>&1
	python3 ~/narz/hdr/porownaj_png.py "$tm"
done
