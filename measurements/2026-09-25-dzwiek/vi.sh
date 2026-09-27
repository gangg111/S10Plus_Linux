#!/bin/sh
# VMON i IMON obu wzmacniaczy, kazdy w swoim slocie, bez kolizji na SDOUT.
for p in Bottom Top; do amixer -c 0 cset name="$p ASP TX2 Source" Zero >/dev/null; done
for zr in VMON IMON; do
  for p in Bottom Top; do amixer -c 0 cset name="$p ASP TX1 Source" $zr >/dev/null; done
  aplay -D hw:0,0 /tmp/dlugi.wav > /dev/null 2>&1 &
  sleep 0.7
  arecord -D hw:0,0 -f S16_LE -r 48000 -c 2 -d 3 /tmp/$zr.wav > /tmp/ar.log 2>&1
  wait
  echo "===== $zr: $(tail -1 /tmp/ar.log)"
  i2ctransfer -f -y 1 w4@0x40 0x00 0x00 0x48 0x00 r4; i2ctransfer -f -y 1 w4@0x41 0x00 0x00 0x48 0x00 r4
  python3 /tmp/analiza.py /tmp/$zr.wav
done
