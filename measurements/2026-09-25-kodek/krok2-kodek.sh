#!/bin/sh
# Krok 2: oddajemy szyne sterownikowi kodeka i ladujemy stos Madera.
rmmod ldo18m_wlacz; dmesg | grep ldo18m | tail -1
for m in madera irq-madera pinctrl-madera madera-spi; do
	insmod /tmp/kodek/$m.ko; echo "insmod $m kod=$?"
done
sleep 2
dmesg | grep -iE "madera|cs47|spi" | tail -15
sh /tmp/kodek/zdrowie.sh
