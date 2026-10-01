#!/bin/sh
# Aparat w tle (zminimalizowany) oraz opcja volumeKeys wylaczona: glosnosc ma dzialac.
E="env -i $(cat /tmp/sesja.env | tr '\n' ' ')"
gl() { $E amixer get Master | grep -o "\[[0-9]*%\]" | head -1; }
C=$HOME/.config/Droidian/droidian-camera.conf
START=$(gl)
minimalizuj() {
	python3 - <<'PY'
import json, socket, struct
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect("/run/user/32011/wayfire-wayland-0-.socket")
def call(m, d=None):
    msg = {"method": m}
    if d is not None:
        msg["data"] = d
    b = json.dumps(msg).encode(); s.sendall(struct.pack("<I", len(b)) + b)
    n = struct.unpack("<I", s.recv(4))[0]; r = b""
    while len(r) < n: r += s.recv(n - len(r))
    return json.loads(r)
for v in call("window-rules/list-views"):
    if v.get("app-id") == "droidian-camera":
        call("wm-actions/set-minimized", {"view_id": v["id"], "state": True})
PY
}
echo "== aparat w tle"
sh /tmp/aparat-uruchom.sh "" 8 >/dev/null 2>&1
minimalizuj; sleep 2
$E amixer -q set Master 50%
echo "przed: $(gl)"; echo 1234 | sudo -S -p "" /tmp/klawisz-glosnosci up; echo "po klawiszu: $(gl)"
pkill -x droidian-camera; sleep 2
echo "== opcja klawiszy glosnosci wylaczona, aparat aktywny"
cp $C /tmp/aparat.conf.kopia
python3 - "$C" <<'PY'
import configparser, sys
c = configparser.RawConfigParser(); c.optionxform = str; c.read(sys.argv[1])
if not c.has_section("Prefs"): c.add_section("Prefs")
c.set("Prefs", "volumeKeys", "false")
with open(sys.argv[1], "w") as f: c.write(f, space_around_delimiters=False)
PY
sh /tmp/aparat-uruchom.sh "" 8 >/dev/null 2>&1
$E amixer -q set Master 50%
echo "przed: $(gl)"; echo 1234 | sudo -S -p "" /tmp/klawisz-glosnosci up; echo "po klawiszu: $(gl)"
pkill -x droidian-camera; sleep 2
cp /tmp/aparat.conf.kopia $C
grep -c "volumeKeys" $C
$E amixer -q set Master "$(echo $START | tr -d '[]')"
echo "przywrocona: $(gl)"
