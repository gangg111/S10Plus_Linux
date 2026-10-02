#!/bin/sh
# Bind audio.hidl_compat over the AOSP stub audio.primary.default, so pulseaudio reaches the
# 32-bit Samsung audio HAL through its vendor HIDL service (android.hardware.audio@5.0).
#
# Only when ABOX got its firmware at boot: calliope_sram*.bin must come from the initramfs,
# because ABOX asks for it at 16.5 s, before /vendor is mounted.  Without it every runtime
# resume of ABOX hangs, the HAL sits in D state and pulseaudio would hang at start, so the
# stub (silence, but a working session) stays.
STUB=/android/vendor/lib64/hw/audio.primary.default.so
COMPAT=/android/system/lib64/hw/audio.hidl_compat.default.so

if dmesg | grep -q "firmware load for calliope_sram.bin failed"; then
	echo "audio-hidl-compat: ABOX firmware missing at boot, keeping the stub HAL"
	exit 0
fi
[ -f "$COMPAT" ] || { echo "audio-hidl-compat: $COMPAT missing"; exit 0; }
mountpoint -q "$STUB" || mount --bind "$COMPAT" "$STUB"
echo "audio-hidl-compat: $STUB -> audio.hidl_compat"
