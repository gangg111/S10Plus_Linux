cd ~/narz/hdr || exit 1
# 10 s 1080p24 HEVC Main10, PQ/BT.2020, statyczne HDR10 (mastering 1000 nitow, MaxCLL 1000/400).
ffmpeg -hide_banner -loglevel error -y -f lavfi -i "testsrc2=size=1920x1080:rate=24,format=yuv420p10le" -t 10 \
	-c:v libx265 -preset fast -x265-params "log-level=error:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:range=limited:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):max-cll=1000,400:hdr10=1:repeat-headers=1" \
	-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc -f hevc baza.hevc
python3 wstrzyknij_hdr10plus.py baza.hevc meta.json hdr10plus.hevc
ffmpeg -hide_banner -loglevel error -y -r 24 -i hdr10plus.hevc -c copy -tag:v hvc1 -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc hdr10plus.mp4
ls -la baza.hevc hdr10plus.hevc hdr10plus.mp4
echo "== ffprobe klatka 0 (scena jasna)"
ffprobe -hide_banner -loglevel error -select_streams v -show_frames -read_intervals "%+#1" hdr10plus.mp4 | grep -iE "side_data_type|targeted_system|maxscl|average_maxrgb|num_distribution|knee|bezier_curve_anchors=|color_transfer|color_primaries|pix_fmt" | head -14
echo "== ffprobe klatka 130 (scena ciemna)"
ffprobe -hide_banner -loglevel error -select_streams v -show_frames -read_intervals "5.4%+#1" hdr10plus.mp4 | grep -iE "maxscl|average_maxrgb" | head -4
