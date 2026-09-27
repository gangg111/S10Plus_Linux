#!/bin/sh
# gpu-next kontra vo=gpu: czas GPU w kazdym takcie (devfreq trans_stat) i odstep klatek KWin.
set -u
export XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0
W=$HOME/narz/wideo/test-1080p60.mp4
DF=$(ls -d /sys/class/devfreq/*gpu* | head -1)
CSV=$(ls -t "$HOME"/*.csv | head -1)
echo "devfreq: $DF, governor $(cat $DF/governor), takty $(cat $DF/available_frequencies)"
czasy() { sudo cat "$DF/trans_stat" | awk '/^[ *]*[0-9]+:/ { gsub(/\*/, ""); f = $1; sub(/:/, "", f); print f, $NF }'; }
klatki() {
	tail -n +"$(($1 + 1))" "$CSV" | head -n "$(($2 - $1))" |
	awk -F, 'NR > 1 { d = ($2 - p) / 1e6; if (d < 200) print d } { p = $2 }' | sort -n |
	awk '{ v[NR] = $1; if ($1 < 18.5) a++ } END { if (NR) printf "  KWin: klatek %d, mediana %.2f ms, p90 %.2f ms, jedna ramka %.1f%%\n", NR, v[int((NR-1)*0.5)+1], v[int((NR-1)*0.9)+1], 100*a/NR }'
}
wariant() {
	nazwa=$1; shift
	i=0; while [ "$(cat /sys/class/thermal/thermal_zone1/temp)" -gt 55000 ] && [ $i -lt 120 ]; do sleep 2; i=$((i + 2)); done
	mpv --fs --hwdec=no --no-audio --really-quiet --length=15 "$@" "$W" >/dev/null 2>&1 &
	M=$!; sleep 4
	czasy > /tmp/t0; l0=$(wc -l < "$CSV")
	sleep 8
	czasy > /tmp/t1; l1=$(wc -l < "$CSV")
	wait $M
	echo "== $nazwa"
	klatki "$l0" "$l1"
	printf '  GPU czas w takcie (ms z 8000): '
	paste /tmp/t0 /tmp/t1 | awk '{ d = $4 - $2; if (d > 0) printf "%d MHz: %d  ", $1 / 1000000, d } END { print "" }'
}
wariant gpu-next-domyslny
wariant vo-gpu-fast --vo=gpu --profile=fast
