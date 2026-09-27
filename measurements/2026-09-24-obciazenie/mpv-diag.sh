#!/bin/sh
# Skad 15 kl/s przy wideo: mpv 15 s w kilku wariantach, statystyki co sekunde.
set -u
export XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0
W=$HOME/narz/wideo/test-1080p60.mp4
cat > /tmp/mpv-co-sek.lua <<'LUA'
local f = io.open("/tmp/mpv-co-sek.txt", "w")
mp.add_periodic_timer(1, function()
	f:write(string.format("t=%.0f fps_wyj=%s vo_zgub=%s dek_zgub=%s opozn=%s vo=%s hwdec=%s\n",
		mp.get_property_number("time-pos", -1),
		mp.get_property("estimated-display-fps", "?"),
		mp.get_property("frame-drop-count", "?"), mp.get_property("decoder-frame-drop-count", "?"),
		mp.get_property("vo-delayed-frame-count", "?"), mp.get_property("current-vo", "?"),
		mp.get_property("hwdec-current", "?")))
	f:flush()
end)
LUA
wariant() {
	nazwa=$1; shift
	i=0; while [ "$(cat /sys/class/thermal/thermal_zone1/temp)" -gt 55000 ] && [ $i -lt 120 ]; do sleep 2; i=$((i + 2)); done
	rm -f /tmp/mpv-co-sek.txt
	mpv --fs --hwdec=no --no-audio --really-quiet --length=15 --script=/tmp/mpv-co-sek.lua "$@" "$W" >/tmp/mpv.log 2>&1 &
	M=$!; sleep 4; P=$(pidof mpv); c0=$(awk '{print $14+$15}' /proc/$P/stat 2>/dev/null || echo 0)
	sleep 8; c1=$(awk '{print $14+$15}' /proc/$P/stat 2>/dev/null || echo 0)
	wait $M
	echo "== $nazwa: CPU mpv $(((c1 - c0) / 8))%"
	sed -n '5p;13p' /tmp/mpv-co-sek.txt
	grep -iE "error|fail|fallback" /tmp/mpv.log | head -3
}
wariant domyslny
wariant profile-fast --profile=fast
wariant vo-gpu-fast --vo=gpu --profile=fast
wariant bez-wyswietlania --vo=null
echo "js fault od startu: $(sudo dmesg | grep -c 'js fault')"
