#!/bin/sh
# Krok 1: samo wlaczenie LDO18M (jeden UPDATE przez ACPM), potem zdrowie.
insmod /tmp/kodek/ldo18m_wlacz.ko; echo "insmod kod=$?"
sleep 1
dmesg | grep ldo18m | tail -3
sh /tmp/kodek/zdrowie.sh
