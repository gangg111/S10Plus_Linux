#!/bin/sh
P=/sys/module/s10_dcs/parameters
D=/sys/class/drm/card0-Unknown-1/dpms
i=0
while [ "$(cat $D)" != On ] && [ $i -lt 300 ]; do sleep 1; i=$((i+1)); done
[ $i -ge 300 ] && { echo "ekran nie zostal wlaczony w 300 s"; exit 1; }
echo "ekran zapalony po $i s"
sleep 3
dmesg -C
echo "$(date +%T) wysylam 0x28"
echo 28 > $P/dcs; echo "rc28=$?"
sleep 1; echo 1 > $P/zrzut
sleep 4; echo 1 > $P/zrzut
echo "$(date +%T) wysylam 0x29"
echo 29 > $P/dcs; echo "rc29=$?"
sleep 1; echo 1 > $P/zrzut
echo "dpms=$(cat $D)"
dmesg
