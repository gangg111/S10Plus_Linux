#!/bin/sh
# Sound through the 32-bit Samsung audio HAL (android.hardware.audio@5.0 HIDL service),
# run from android-mount.service once /vendor is mounted (about 12 s after boot).
#
# 1. ABOX asks for calliope_sram*.bin and calliope_dram.bin at about 10.3 s, before
#    /vendor exists; the kernel then waits 60 s for user space (firmware user helper
#    fallback), which on Android is ueventd and here nobody. Serve every pending request
#    from /vendor/firmware, for a few seconds, since some requests only come after others.
#    (Putting the files into the initramfs does not help: this kernel does not unpack it,
#    Droidian treats it as an initrd and unpacks it later in user space.)
# 2. Only when ABOX got both firmware images, bind audio.hidl_compat over the AOSP stub
#    audio.primary.default, so pulseaudio reaches the vendor HAL. Without the firmware every
#    runtime resume of ABOX hangs, the HAL sits in D state and pulseaudio would hang at start,
#    so the stub (silence, but a working session) stays.
STUB=/android/vendor/lib64/hw/audio.primary.default.so
COMPAT=/android/system/lib64/hw/audio.hidl_compat.default.so
FW=/vendor/firmware
podane=""

# Kernel with the images built in (CONFIG_EXTRA_FIRMWARE, boot image of 03.10.2026): request_firmware
# is answered from the kernel itself, nothing waits in /sys/class/firmware.
for n in calliope_sram.bin calliope_dram.bin; do
	s=_fw_$(echo "$n" | tr . _)_bin
	grep -q " $s\$" /proc/kallsyms && podane="$podane $n"
done
[ -n "$podane" ] && echo "audio-hidl-compat: built into the kernel:$podane"
for v in /sys/devices/platform/*abox*/calliope_version; do
	[ -r "$v" ] && echo "audio-hidl-compat: calliope_version $(cat "$v" 2>/dev/null)"
done

for proba in 1 2 3 4 5 6 7 8 9 10; do
	for d in /sys/class/firmware/*/; do
		n=$(basename "$d")
		# only the ABOX images; other drivers (Wi-Fi CLM, VTS) keep their current behaviour
		case "$n" in calliope_*) ;; *) continue ;; esac
		[ -e "$d/loading" ] || continue
		[ -f "$FW/$n" ] || continue
		echo 1 > "$d/loading" && cat "$FW/$n" > "$d/data" && echo 0 > "$d/loading" && {
			podane="$podane $n"
			echo "audio-hidl-compat: firmware $n served from $FW"
		}
	done
	case "$podane" in *calliope_sram.bin*calliope_dram.bin*|*calliope_dram.bin*calliope_sram.bin*) break ;; esac
	sleep 0.5
done

case "$podane" in
	*calliope_sram.bin*) ;;
	*) echo "audio-hidl-compat: ABOX did not get calliope_sram.bin, keeping the stub HAL"; exit 0 ;;
esac
case "$podane" in
	*calliope_dram.bin*) ;;
	*) echo "audio-hidl-compat: ABOX did not get calliope_dram.bin, keeping the stub HAL"; exit 0 ;;
esac
[ -f "$COMPAT" ] || { echo "audio-hidl-compat: $COMPAT missing"; exit 0; }

# 3. Wake ABOX once ourselves, before the HAL starts. The first runtime resume registers the
#    firmware's ALSA controls (snd_ctl_add, takes the card's controls_rwsem for writing); when that
#    first resume is triggered by the HAL reading a control (abox_ctl_get holds the same rwsem for
#    reading and waits for the resume), both sides wait forever: HAL in D state, pulseaudio hung.
#    Measured 03.10.2026, stacks abox_runtime_resume > snd_ctl_add and abox_ctl_get > rpm_resume.
ABOX=/sys/devices/platform/18c50000.abox/power
if [ -w "$ABOX/control" ]; then
	# in the background: should the HAL be first after all, the writer sleeps in D state and
	# must not hold up android-mount.service
	( echo on > "$ABOX/control" ) &
	for proba in 1 2 3 4 5 6 7 8 9 10; do
		stan=$(cat "$ABOX/runtime_status")
		[ "$stan" = active ] && break
		sleep 0.5
	done
	echo "audio-hidl-compat: ABOX runtime $stan"
	[ "$stan" = active ] || { echo "audio-hidl-compat: ABOX did not wake, keeping the stub HAL"; exit 0; }
	wait
	echo auto > "$ABOX/control"
fi
mountpoint -q "$STUB" || mount --bind "$COMPAT" "$STUB"
echo "audio-hidl-compat: $STUB -> audio.hidl_compat"
