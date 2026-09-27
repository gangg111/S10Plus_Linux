#!/bin/sh
# Wlacza akcelerometr i czujnik swiatla, gdy hub jest gotowy.  Zapis do
# enable przed koncem rozruchu huba jadro odrzuca, wiec proba powtarza sie
# do 30 s.  Maska: bit 0 akcelerometr, bit 9 swiatlo (513).  Zblizeniowy
# (bit 7) zostaje wylaczony: bez rozmow nikt go nie czyta, a dioda IR pobiera
# prad.  Okres akcelerometru 60 ms jak u Androida przy obracaniu ekranu
# (SENSOR_DELAY_UI).
MASKA=513
for i in $(seq 60); do
	echo $MASKA > /sys/class/sensors/ssp_sensor/enable 2>/dev/null
	[ "$(cat /sys/class/sensors/ssp_sensor/enable 2>/dev/null)" = $MASKA ] && break
	sleep 0.5
done
for d in /sys/bus/iio/devices/iio:device*; do
	[ "$(cat $d/name)" = accelerometer_sensor ] && echo 60000000 > $d/poll_delay
done
echo "czujniki: enable=$(cat /sys/class/sensors/ssp_sensor/enable)"
