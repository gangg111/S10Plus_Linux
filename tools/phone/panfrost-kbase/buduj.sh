#!/bin/sh
# Buduje Mese Panfrost na kbase (github.com/JimVulkan/mali-panfrost, Mesa
# 26.3-devel) NATYWNIE na telefonie z Droidianem (glibc, aarch64), do
# prywatnego prefiksu. Systemowa Mesa i libhybris zostaja nietkniete;
# biblioteki wybiera sie przez glvnd (__EGL_VENDOR_LIBRARY_FILENAMES).
# Zaleznosci (apt): llvm-21-dev libclang-21-dev clang-21 libclc-21-dev
# libllvmspirvlib-21-dev llvm-spirv-21 meson ninja-build python3-mako
# python3-packaging python3-yaml flex bison glslang-tools libexpat1-dev
# zlib1g-dev libdrm-dev libwayland-dev wayland-protocols libzstd-dev
# Uzycie: sh buduj.sh [konfiguruj]   (log: ~/src/panfrost-build.log)
set -e
SRC=$HOME/src/mali-panfrost
B=$SRC/build-glibc
PREFIX=$HOME/.local/panfrost-kbase
[ -d $SRC ] || git clone -q --depth 1 https://github.com/JimVulkan/mali-panfrost.git $SRC
cd $SRC
if [ ! -d $B ] || [ "$1" = konfiguruj ]; then
	rm -rf $B
	meson setup $B --prefix=$PREFIX --libdir=lib -Dbuildtype=release -Db_ndebug=true \
		-Dplatforms=wayland -Dgallium-drivers=panfrost -Dvulkan-drivers= -Dvulkan-layers= \
		-Degl=enabled -Dgles2=enabled -Dgles1=disabled -Dopengl=true -Dglx=disabled \
		-Dgbm=disabled -Dglvnd=enabled -Dllvm=enabled \
		-Dmesa-clc=enabled -Dprecomp-compiler=enabled -Dinstall-mesa-clc=false \
		-Dtools= -Dvideo-codecs= -Dlmsensors=disabled -Dvalgrind=disabled \
		-Dlibunwind=disabled -Dperfetto=false
fi
ninja -C $B
ninja -C $B install
ls -la $PREFIX/lib | head -20
