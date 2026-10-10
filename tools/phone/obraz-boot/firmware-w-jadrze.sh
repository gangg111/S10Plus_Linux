#!/bin/sh
# ABOX firmware built into the kernel (CONFIG_EXTRA_FIRMWARE): ABOX asks at ~10.3 s,
# before /vendor is mounted, and the user helper fallback ends within ~0.2 s.
set -e
D=/home/pm/droidian
K=$D/kernel/samsung/beyond2lte
FW="calliope_sram.bin calliope_sram_2.bin calliope_dram.bin calliope_dram_2.bin"
# firmware/Makefile emits .incbin "firmware/<name>", resolved from the object tree
mkdir -p $D/czysty/firmware
for f in $FW; do cp /mnt/d/S10Plus-droidian/abox-fw/$f $K/firmware/$f; cp $K/firmware/$f $D/czysty/firmware/$f; done
cd $D/czysty
sed -i 's|^CONFIG_EXTRA_FIRMWARE=.*|CONFIG_EXTRA_FIRMWARE="'"$FW"'"|' .config
sed -i '/^CONFIG_EXTRA_FIRMWARE_DIR=/d' .config
sed -i '/^CONFIG_EXTRA_FIRMWARE=/a CONFIG_EXTRA_FIRMWARE_DIR="/k/firmware"' .config
grep EXTRA_FIRMWARE .config
sh /mnt/c/Users/Artur/Documents/Serwis/Programowanie/S10Plus_Linux/tools/phone/obraz-boot/jadro-buduj.sh
strings $D/czysty/arch/arm64/boot/Image | grep -c "calliope_dram_2.bin" || true
