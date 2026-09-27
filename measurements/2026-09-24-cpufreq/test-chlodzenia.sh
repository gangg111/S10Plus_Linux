#!/bin/sh
# Test dlawienia: pelne obciazenie 8 rdzeni, odczyt co 2 s, przerwanie
# obciazenia, gdy ktorakolwiek strefa CPU przekroczy LIMIT (m C).
LIMIT=${1:-93000}
CZAS=${2:-150}
T=/sys/class/thermal
C=/sys/devices/system/cpu/cpufreq
for i in 1 2 3 4 5 6 7 8; do yes > /dev/null & done
start=$(cut -d. -f1 /proc/uptime)
echo "   s  big  mid  lit |  cl0  cl1  cl2 MHz | chlodz 0/4/6"
while :; do
	t=$(( $(cut -d. -f1 /proc/uptime) - start ))
	b=$(cat $T/thermal_zone1/temp); m=$(cat $T/thermal_zone2/temp); l=$(cat $T/thermal_zone3/temp)
	printf '%4d %4d %4d %4d | %4d %4d %4d     | %s/%s/%s\n' "$t" $((b/1000)) $((m/1000)) $((l/1000)) \
		$(( $(cat $C/policy0/scaling_cur_freq) / 1000 )) \
		$(( $(cat $C/policy4/scaling_cur_freq) / 1000 )) \
		$(( $(cat $C/policy6/scaling_cur_freq) / 1000 )) \
		"$(cat $T/cooling_device0/cur_state)" "$(cat $T/cooling_device1/cur_state)" \
		"$(cat $T/cooling_device2/cur_state)"
	if [ "$b" -gt "$LIMIT" ] || [ "$m" -gt "$LIMIT" ] || [ "$l" -gt "$LIMIT" ]; then
		echo "PRZERWANE: przekroczony limit $LIMIT"
		break
	fi
	[ "$t" -ge "$CZAS" ] && break
	sleep 2
done
kill $(jobs -p) 2>/dev/null
wait 2>/dev/null
sleep 5
echo "po 5 s: big $(( $(cat $T/thermal_zone1/temp) / 1000 )) C, chlodzenie $(cat $T/cooling_device2/cur_state)"
