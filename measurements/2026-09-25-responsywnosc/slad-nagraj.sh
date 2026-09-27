#!/bin/sh
# Slad calej drogi dotyk -> KWin -> klient -> GPU -> DECON, trace-cmd.
# Uzycie: sh slad-nagraj.sh <nazwa> <sekundy> [palec]   (palec = syntetyczne przesuniecia)
set -u
N=${1:-slad}; T=${2:-20}; P=${3:-}
TR=/sys/kernel/tracing
sudo sh -c "
echo > $TR/kprobe_events
echo 'p:dotyk evdev_events' >> $TR/kprobe_events
echo 'p:commit drm_mode_atomic_ioctl' >> $TR/kprobe_events
echo 'p:flip decon9820_pokaz adres=%x1:u32' >> $TR/kprobe_events
echo 'r:zatrzask decon9820_pokaz ret=\$retval:s32' >> $TR/kprobe_events
echo 'p:vblank drm_crtc_send_vblank_event' >> $TR/kprobe_events
"
ls $TR/events/gpu_scheduler 2>/dev/null | tr '\n' ' '; echo
cd /tmp
sudo trace-cmd record -q -o /tmp/$N.dat -b 20000 \
	-e sched:sched_switch -e sched:sched_wakeup -e sched:sched_waking \
	-e power:cpu_frequency -e gpu_scheduler \
	-e kprobes:dotyk -e kprobes:commit -e kprobes:flip -e kprobes:zatrzask -e kprobes:vblank \
	sleep "$T" &
REC=$!
sleep 2
if [ "$P" = palec ]; then
	sleep 1
	sudo ~/narz/palec /dev/input/event0 5 1200 >/dev/null
fi
wait $REC
sudo sh -c "echo > $TR/kprobe_events"
sudo trace-cmd report -i /tmp/$N.dat 2>/dev/null > /tmp/$N.txt
sudo chown user /tmp/$N.dat
wc -l /tmp/$N.txt
awk '{ for (i = 1; i <= NF; i++) if ($i ~ /:$/ && $i !~ /^\[/) { print $i; break } }' /tmp/$N.txt | sort | uniq -c | sort -rn | head -14
