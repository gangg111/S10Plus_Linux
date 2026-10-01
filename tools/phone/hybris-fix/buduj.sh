#!/bin/sh
# Buduje poprawiona libhybris NA TELEFONIE (Droidian, aarch64) z opcjami paczki
# Droidiana (debian/rules galezi feature/next/lindroid-drm) i wyciaga z niej
# modul EGL dla glvnd: ~/src/hybris-fix/wynik/libEGL_libhybris.so.0
# Wymaga: autoconf automake libtool libwayland-egl-backend-dev libx11-xcb-dev
# libxcb-dri3-dev libxcb-present-dev libxext-dev libvulkan-dev libgbm-dev
# libdrm-dev patchelf; naglowki android-headers-30 rozpakowane (apt-get
# download + dpkg -x) do ~/src/hybris-fix/ah30, bez instalacji.
set -e
TU=$(cd "$(dirname "$0")" && pwd)
W=$HOME/src/hybris-fix
cd $W
[ -d src ] || git clone -q --depth 1 -b feature/next/lindroid-drm https://github.com/droidian/libhybris.git src
[ -d ah30 ] || { apt-get download android-headers-30; dpkg -x android-headers-30_*.deb ah30; }
cd src
git checkout -q -- hybris/egl/egl.c hybris/egl/glvnd/eglglvnd.cpp hybris/egl/platforms/wayland/eglplatform_wayland.cpp
python3 $TU/lata-egl.py hybris/egl/egl.c
python3 $TU/lata-dmabuf-wayland.py hybris/egl/platforms/wayland/eglplatform_wayland.cpp
cd hybris
[ -f configure ] || ./autogen.sh > $W/autogen.log 2>&1
./configure --prefix=/usr --libdir=/usr/lib/aarch64-linux-gnu \
	--enable-wayland --with-android-headers=$W/ah30/usr/include/android \
	--enable-property-cache --enable-experimental --enable-glvnd \
	--enable-lindroid-drm --enable-clicd \
	--enable-arch=arm64 --enable-mali-quirks --enable-adreno-quirks > $W/configure.log 2>&1
make -j8 > $W/make.log 2>&1
mkdir -p $W/wynik
cp -L egl/.libs/libEGL_libhybris.so.0 $W/wynik/libEGL_libhybris.so.0
# wtyczki platform do prywatnego katalogu (HYBRIS_EGLPLATFORM_DIR), system nietkniety
mkdir -p $W/wynik/libhybris
cp -L egl/platforms/wayland/.libs/eglplatform_wayland.so egl/platforms/null/.libs/eglplatform_null.so $W/wynik/libhybris/
# libtool zostawia RUNPATH do katalogu budowania; zaleznosci z tego samego drzewa
# ida obok (wynik/hybris-lib), a RUNPATH wskazuje je wzgledem pliku ($ORIGIN)
mkdir -p $W/wynik/hybris-lib
cp -L egl/platforms/common/.libs/libhybris-eglplatformcommon.so.1 platforms/common/.libs/libhybris-platformcommon.so.1 \
	gralloc/.libs/libgralloc.so.1 libsync/.libs/libsync.so.2 $W/wynik/hybris-lib/
patchelf --set-rpath '$ORIGIN/hybris-lib' $W/wynik/libEGL_libhybris.so.0
patchelf --set-rpath '$ORIGIN/../hybris-lib' $W/wynik/libhybris/*.so
patchelf --set-rpath '$ORIGIN' $W/wynik/hybris-lib/*
ls -la $W/wynik $W/wynik/libhybris $W/wynik/hybris-lib
