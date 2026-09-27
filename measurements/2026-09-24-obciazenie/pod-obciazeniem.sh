#!/bin/sh
# Plynnosc pod obciazeniem: 3 scenariusze, odstep klatek z dziennika KWin
# (KWIN_LOG_PERFORMANCE_DATA) i straty klatek mpv.
# Uzycie: sh pod-obciazeniem.sh   (sesja KWin musi logowac klatki)
set -u
export XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0
CSV=$(ls -t "$HOME"/*.csv | head -1)
W=$HOME/narz/wideo/test-1080p60.mp4
cd "$HOME/narz" || exit 1

temp() { printf 'big %s C, gpu %s C' $(($(cat /sys/class/thermal/thermal_zone1/temp) / 1000)) \
	$(($(cat /sys/class/thermal/thermal_zone4/temp) / 1000)); }
ostyg() { i=0; while [ "$(cat /sys/class/thermal/thermal_zone1/temp)" -gt 55000 ] && [ $i -lt 120 ]; do sleep 2; i=$((i + 2)); done; }
linie() { wc -l < "$CSV"; }
# Odstepy klatek z linii CSV od $1 do $2: mediana, p90, p99, udzial jednej ramki.
klatki() {
	tail -n +"$(($1 + 1))" "$CSV" | head -n "$(($2 - $1))" |
	awk -F, 'NR > 1 { d = ($2 - p) / 1e6; if (d < 200) print d } { p = $2 }' | sort -n |
	awk '{ v[NR] = $1; if ($1 < 18.5) a++ } END {
		if (!NR) { print "  brak klatek"; exit }
		printf "  klatek %d, odstep ms: mediana %.2f, p90 %.2f, p99 %.2f, jedna ramka %.1f%%\n",
			NR, v[int((NR - 1) * 0.5) + 1], v[int((NR - 1) * 0.9) + 1], v[int((NR - 1) * 0.99) + 1], 100 * a / NR }'
}
cat > /tmp/mpv-straty.lua <<'LUA'
mp.register_event("shutdown", function()
	local f = io.open("/tmp/mpv-straty.txt", "w")
	f:write(string.format("vo_zgubione=%s dekoder_zgubione=%s opoznione=%s fps=%s\n",
		mp.get_property("frame-drop-count", "?"), mp.get_property("decoder-frame-drop-count", "?"),
		mp.get_property("vo-delayed-frame-count", "?"), mp.get_property("estimated-vf-fps", "?")))
	f:close()
end)
LUA
mpv_start() {
	rm -f /tmp/mpv-straty.txt
	mpv --fs --hwdec=no --really-quiet --no-audio --length=24 --script=/tmp/mpv-straty.lua "$W" >/tmp/mpv.log 2>&1 &
	MPV=$!
	sleep 3
}
mpv_stop() {
	wait $MPV
	echo "  mpv: $(cat /tmp/mpv-straty.txt 2>/dev/null || echo brak wyniku; tail -2 /tmp/mpv.log)"
}

echo "== S1: 8 rdzeni w 100% + szuflada ($(temp))"
ostyg
for n in 1 2 3 4 5 6 7 8; do sh -c 'while :; do :; done' & done
sleep 2
sh ab.sh obciazenie-cpu 5
pkill -f 'while :; do :; done'
echo "  po: $(temp), takty: $(cat /sys/devices/system/cpu/cpufreq/policy*/scaling_cur_freq | tr '\n' ' ')"

echo "== S2: mpv 1080p60 na pelnym ekranie ($(temp))"
ostyg
mpv_start
l0=$(linie); P=$(pidof mpv); c0=$(awk '{print $14+$15}' /proc/$P/stat)
sleep 18
l1=$(linie); c1=$(awk '{print $14+$15}' /proc/$P/stat)
klatki "$l0" "$l1"
echo "  CPU mpv: $(((c1 - c0) / 18))% jednego rdzenia (ticki/s przy HZ=100)"
mpv_stop
echo "  po: $(temp)"

echo "== S3: mpv 1080p60 + szuflada ($(temp))"
ostyg
mpv_start
sh ab.sh wideo-i-szuflada 5
mpv_stop
echo "  po: $(temp)"
echo "js fault od startu: $(sudo dmesg | grep -c 'js fault')"
