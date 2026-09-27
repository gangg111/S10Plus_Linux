#!/bin/sh
# Krok 0 po rozruchu: nic nie wlaczamy, tylko stan magistrali SPI i szyn.
sh /tmp/kodek/zdrowie.sh
echo "== SPI"
ls /sys/class/spi_master/ 2>&1
for d in /sys/bus/spi/devices/*; do echo "$(basename $d) modalias=$(cat $d/modalias) sterownik=$(basename $(readlink $d/driver 2>/dev/null) 2>/dev/null)"; done
dmesg | grep -iE "10470000|104700c0|s3c64xx|spi" | head -8
cat /sys/kernel/debug/clk/clk_summary 2>/dev/null | grep -iE "usi01" | head -4
