#!/bin/sh
# HDR10+ w 2160p24 i 1440p24: czy programowy dekoder HEVC Main10 nadaza.
export XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0
cd ~/narz/hdr || exit 1
python3 hdr10plus_json.py 240 meta240.json >/dev/null
for r in 3840x2160 2560x1440; do
	f=hdr10plus-$r.mp4
	if [ ! -f $f ]; then
		ffmpeg -hide_banner -loglevel error -y -f lavfi -i "testsrc2=size=$r:rate=24,format=yuv420p10le" -t 10 \
			-c:v libx265 -preset ultrafast -x265-params "log-level=error:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:range=limited:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):max-cll=1000,400:hdr10=1:repeat-headers=1" \
			-f hevc t.hevc
		python3 wstrzyknij_hdr10plus.py t.hevc meta240.json t10p.hevc >/dev/null
		ffmpeg -hide_banner -loglevel error -y -r 24 -i t10p.hevc -c copy -tag:v hvc1 -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc $f
		rm -f t.hevc t10p.hevc
	fi
	cat > /tmp/k.lua <<'LUA'
mp.add_timeout(9.5, function()
	io.open("/tmp/k-wynik.txt", "a"):write(string.format("%s: vo=%s zgub-vo=%s zgub-dek=%s opoznienie=%s hwdec=%s\n",
		mp.get_property("filename"), mp.get_property("current-vo", "?"), mp.get_property("frame-drop-count", "?"),
		mp.get_property("decoder-frame-drop-count", "?"), mp.get_property("avsync", "?"), mp.get_property("hwdec-current", "?")))
end)
LUA
	mpv --fs --no-audio --script=/tmp/k.lua $f >/tmp/mpv-k.log 2>&1
done
cat /tmp/k-wynik.txt; rm -f /tmp/k-wynik.txt
