#!/bin/sh
# Buduje mpv 0.41.0 na telefonie z latka powierzchni koloru Wayland dla
# gpu-next i instaluje go za opakowaniem /usr/local/bin/mpv (tekstury liniowe
# panfrosta). Wymaga zrodel mpv-0.41.0.tar.gz w ~/narz/mpv-hdr oraz pakietow
# do budowania mpv z Alpine (meson, ffmpeg-dev, libplacebo-dev, luajit-dev,
# wayland-dev, mesa-dev, pipewire-dev, alsa-lib-dev, pulseaudio-dev).
# Uzycie: sh buduj-mpv.sh (log w ~/narz/mpv-hdr/build.log).
exec > /home/user/narz/mpv-hdr/build.log 2>&1 </dev/null
cd /home/user/narz/mpv-hdr || exit 1
rm -rf mpv-0.41.0 && tar xzf mpv-0.41.0.tar.gz && cd mpv-0.41.0 || exit 1
python3 - <<'PY'
p = 'video/out/wayland_common.c'
s = open(p).read()
old = '''        // Only bind color surface to vo_dmabuf_wayland for now to avoid conflicting with graphics drivers
        if (!strcmp(wl->vo->driver->name, "dmabuf-wayland"))'''
new = '''        // Bind the color surface for gpu-next too: on OpenGL (no Vulkan on
        // Mali-G76) nothing else sets the image description, so HDR never
        // reaches the compositor and KWin cannot use EDR headroom.
        if (!strcmp(wl->vo->driver->name, "dmabuf-wayland") ||
            !strcmp(wl->vo->driver->name, "gpu-next"))'''
assert old in s
open(p, 'w').write(s.replace(old, new, 1))
print('latka nalozona')
PY
meson setup build --prefix=/usr/local --bindir=libexec/mpv-hdr --buildtype=release -Dlua=luajit -Dlibmpv=false \
	-Dwayland=enabled -Degl-wayland=enabled -Dgl=enabled \
	-Dx11=disabled -Dvulkan=enabled -Dpipewire=enabled -Dpulse=enabled -Dalsa=enabled -Dmanpage-build=disabled
ninja -C build -j8 && sudo ninja -C build install &&
	sudo install -m 755 /home/user/narz/mpv-hdr/mpv-opakowanie.sh /usr/local/bin/mpv
echo "KONIEC kod=$?"
