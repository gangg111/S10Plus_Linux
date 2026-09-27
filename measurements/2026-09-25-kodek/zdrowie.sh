#!/bin/sh
# Kontrola zdrowia po kazdym kroku: jadro, uslugi, ekran, szyny kodeka, PMIC.
echo "== $(date +%T) uptime $(cut -d' ' -f1 /proc/uptime) jadro $(uname -v | cut -d' ' -f1)"
echo "uslugi: $(systemctl is-active plasma-mobile decon9820 s6e3ha9-jasnosc podbicie | tr '\n' ' ')"
for r in /sys/class/regulator/regulator.*; do
	n=$(cat $r/name)
	case $n in vdd_codec_1p2|vdd_pmic_codec_1p8|tsp_io|tsp_avdd)
		echo "szyna $n: $(cat $r/state) $(cat $r/microvolts) uV, uzytkownikow $(cat $r/num_users)";;
	esac
done
echo "jasnosc panelu: $(cat /sys/class/backlight/s6e3ha9/actual_brightness)"
echo "przerwania: $(grep -E 's2mps19|s6sy761|madera|cs35l41' /proc/interrupts | awk '{s=0; for(i=2;i<=9;i++) s+=$i; print $NF":"s}' | tr '\n' ' ')"
dmesg | grep -iE "s2mps|acpm|regulator|spi|madera|cs47|usi" | grep -iE "fail|error|timeout|warn|bring" | tail -5
