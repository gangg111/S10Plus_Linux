#!/bin/sh
# Aplikacja aparatu Droidiana z pelnym wykorzystaniem HAL (patches/) jako paczka .deb,
# budowana NATYWNIE na telefonie (ok. 4 min). Baza: droidian/droidian-camera, galaz
# feature/next/hybris-compat, commit 7071899 (najnowszy na 30.09.2026; wersja w repo
# Droidiana jest ze stycznia 2024 i nie ma tej przepisanej aplikacji).
# Zaleznosci (apt): cmake debhelper dpkg-dev lld-21 clang-21 qt6-base-dev qt6-multimedia-dev
# qt6-declarative-dev qt6-tools-dev qt6-sensors-dev qt6-positioning-dev libavcodec-dev
# libavformat-dev libavutil-dev libswscale-dev libquirc-dev libglib2.0-dev
# fonts-material-design-icons-iconfont
# Uzycie: sh buduj.sh   -> ~/src/droidian-camera_<wersja>_arm64.deb, instalacja: dpkg -i
# Latki: 0001 pelny Camera1 i wyglad One UI, 0002 sciezka Camera2 w libcamx (reczne ISO,
# czas i ostrosc, RAW jako DNG, OIS, seria), 0003 zywa sesja Camera2 w trybach PRO i wideo
# (podglad bez kopii, nagrywanie H.264/HEVC + AAC), 0004 Kelvin, kontrast, szum, wyostrzanie,
# 0005 ustawienia w stylu One UI (QR, histogram, pomiar, siatka, autoportrety, klawisze),
# 0006 znak wodny i automatyczne kl./s w wideo (15..30), 0007 ikony w motywie hicolor
# (w golym /usr/share/icons Plasma ich nie widzi), 0008 klawisze glosnosci zabierane
# kompozytorowi przez wtyczke wayfire podglad (tools/phone/podglad, metoda podglad/volume-keys);
# libcamx linkuje sie z libcamera2ndk,
# libmediandk, libbinder_ndk i libnativewindow z /android/system/lib64.
# Dowod: dpkg-query -W droidian-camera pokazuje 26.1+s10plus8, log aplikacji
# "camx loaded from .../lib/droidian-camera/libcamx.so" (bez "layout mismatch"), w trybie PRO
# "cam2: live session photo", a film ma strumienie h264 i aac (ffprobe).
# Pomiary plynnosci TYLKO przy wlaczonym ekranie (zgaszony dlawi watki RT kamery).
set -e
TU=$(cd "$(dirname "$0")" && pwd)
W=$HOME/src/droidian-camera
[ -d $W ] || git clone -q -b feature/next/hybris-compat https://github.com/droidian/droidian-camera.git $W
cd $W
git checkout -q 7071899
git -c user.name=Artur -c user.email=ganggg111@gmail.com am -q $TU/patches/*.patch
dpkg-buildpackage -b -uc -us -d > $HOME/src/droidian-camera-deb.log 2>&1
ls -la ../droidian-camera_*_arm64.deb
