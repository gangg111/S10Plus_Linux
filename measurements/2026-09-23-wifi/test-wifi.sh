#!/bin/sh
# Pierwsze uruchomienie kontrolera PCIe i Wi-Fi: insmod, potem wszystko,
# co mowi, jak daleko doszlo.
dmesg -C
echo "== regulator przed insmod =="
for r in /sys/class/regulator/regulator.*; do
	[ "$(cat $r/name 2>/dev/null)" = wlan_en ] && echo "$(cat $r/name) state=$(cat $r/state 2>/dev/null) users=$(cat $r/num_users)"
done
echo "== insmod $(date +%T) =="
insmod /tmp/pcie-exynos9820.ko; echo "insmod=$?"
sleep 20
echo "== dmesg =="
dmesg
echo "== pci =="
for d in /sys/bus/pci/devices/*; do
	[ -e "$d" ] && echo "$(basename $d) $(cat $d/vendor):$(cat $d/device) drv=$(basename $(readlink $d/driver 2>/dev/null) 2>/dev/null)"
done
echo "== link_history =="
cat /sys/kernel/debug/13ed0000.pcie/link_history 2>&1 | head -40
echo "== przerwania =="
grep -iE "pcie|brcmf" /proc/interrupts
echo "== interfejsy =="
ip link
for r in /sys/class/regulator/regulator.*; do
	[ "$(cat $r/name 2>/dev/null)" = wlan_en ] && echo "$(cat $r/name) state=$(cat $r/state 2>/dev/null) users=$(cat $r/num_users)"
done
