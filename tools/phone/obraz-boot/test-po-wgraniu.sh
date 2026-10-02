#!/bin/sh
# Checks after flashing boot-fimc-abox-mfc.img and rebooting: kernel, ABOX firmware, sound,
# MFC decoder (FFmpeg and GStreamer), camera nodes. Run as droidian; nothing audible is played.
E="env -i $(cat /tmp/sesja.env 2>/dev/null | tr '\n' ' ')"
[ -s /tmp/sesja.env ] || { P=$(pgrep -x plasmashell | head -1)
	echo 1234 | sudo -S -p "" cat /proc/$P/environ | tr '\0' '\n' | grep -vE "^(LISTEN_|INVOCATION_ID|JOURNAL_STREAM|SYSTEMD_EXEC_PID|MANAGERPID|NOTIFY_SOCKET)" > /tmp/sesja.env
	E="env -i $(cat /tmp/sesja.env | tr '\n' ' ')"; }
echo "== jadro: $(uname -v)"
echo "   s10probe w kallsyms: $(grep -c s10probe_hit /proc/kallsyms) (oczekiwane 0)"
echo "== ABOX: $(dmesg | grep -c 'firmware load for calliope_sram.bin failed') bledow firmware (oczekiwane 0)"
echo "   audio.primary w pulseaudio: $(grep -oE '/android/[^ ]*audio[^ ]*\.so' /proc/$(pgrep -x pulseaudio)/maps | sort -u | tr '\n' ' ')"
echo "   HAL w kontenerze: $(ps -eo stat,args | grep '[a]ndroid.hardware.audio.service')"
$E timeout 5 parecord --device=source.primary-in --rate=48000 --channels=1 --format=s16le --file-format=wav /tmp/mik.wav
python3 -c "
import wave,struct,math
w=wave.open('/tmp/mik.wav');d=w.readframes(w.getnframes());n=len(d)//2
x=struct.unpack('<%dh'%n,d[:n*2]);r=math.sqrt(sum(v*v for v in x)/n) if n else 0
print('   mikrofon: probek',n,'niezerowych',sum(1 for v in x if v),'RMS %.1f'%r)"
$E paplay --device=sink.primary-out $HOME/testy/cisza.wav 2>/dev/null &
sleep 2
echo "   PCM przy odtwarzaniu: $(grep -l RUNNING /proc/asound/card*/pcm*p/sub0/status 2>/dev/null | tr '\n' ' ')"
wait
echo "== kamery: wezly fimc-is z formatami 64+: $(python3 $HOME/testy/v4l2-sonda.py 2>/dev/null | tr -d '\000' | grep -ac '64+') (oczekiwane 0)"
echo "== MFC przez FFmpeg (bez sudo)"
for c in h264 hevc; do
	timeout 120 ffmpeg -hide_banner -c:v ${c}_v4l2m2m -i $HOME/testy/mfc-$c.mkv -benchmark -f null - > $HOME/testy/mfc-out.txt 2>&1
	echo "   $c: rc=$? klatek=$(grep -oE 'frame= *[0-9]+' $HOME/testy/mfc-out.txt | tail -1 | grep -oE '[0-9]+') $(grep -oE 'bench: utime=.*' $HOME/testy/mfc-out.txt) $(grep -m1 -oE 'Using device /dev/video[0-9]+' $HOME/testy/mfc-out.txt)"
done
echo "== MFC przez GStreamer"
rm -f ~/.cache/gstreamer-1.0/registry*.bin
gst-inspect-1.0 video4linux2 2>/dev/null | grep -E "v4l2[a-z0-9]*dec" | head -5
t0=$(date +%s.%N)
timeout 120 gst-launch-1.0 -q filesrc location=$HOME/testy/mfc-h264.mkv ! matroskademux ! h264parse ! v4l2h264dec ! fakesink sync=false
echo "   gst h264: rc=$? czas $(echo "$(date +%s.%N) - $t0" | bc) s"
