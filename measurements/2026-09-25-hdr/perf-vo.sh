#!/bin/sh
export XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0
cd ~/narz/hdr || exit 1
mpv --fs --no-audio --length=9 hdr10plus-3840x2160.mp4 >/dev/null 2>&1 &
sleep 2
M=$(pgrep -n -x mpv)
V=$(for t in /proc/$M/task/*; do [ "$(cat $t/comm)" = vo ] && basename $t; done)
sudo perf record -q -e cpu-clock -t $V -o /tmp/vo.perf -- sleep 4 2>/dev/null
while kill -0 $M 2>/dev/null; do sleep 0.3; done
sudo perf report -i /tmp/vo.perf --stdio --sort dso,sym 2>/dev/null | grep -v "^#" | grep -v "^$" | head -18
