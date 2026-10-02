#!/bin/sh
# Jadro bez debugu bring-upu: przyrostowo na kopii pidfd2 (ta sama .config co jadro na sda14),
# ten sam kompilator co pakiet Droidiana (clang Androida 17.0-r487747c, LLVM, aarch64-linux-gnu).
set -e
D=/home/pm/droidian
[ -d $D/czysty ] || cp -a $D/pidfd2 $D/czysty

docker run --rm -v $D/kernel/samsung/beyond2lte:/k -v $D/czysty:/o -w /o \
	quay.io/droidian/build-essential:next-amd64 bash -c '
set -e
apt-get -qq update >/dev/null 2>&1
apt-get -qq install -y clang-android-17.0-r487747c binutils-aarch64-linux-gnu bc bison flex libssl-dev >/dev/null 2>&1 || { echo "instalacja narzedzi nie poszla"; exit 1; }
export PATH=/usr/lib/llvm-android-17.0-r487747c/bin:$PATH
s=$(date +%s)
make -C /k O=/o ARCH=arm64 CC=clang CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu- \
	LD=ld.lld AR=llvm-ar NM=llvm-nm OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump STRIP=llvm-strip \
	KERNELRELEASE=4.14.356-samsung-beyond2lte -j$(nproc) Image > /o/budowa.log 2>&1 || { tail -30 /o/budowa.log; exit 1; }
echo "budowa $(( $(date +%s) - s )) s"
'
I=$D/czysty/arch/arm64/boot/Image
ls -la $I
strings $I | grep -m1 "Linux version 4.14"
echo "slady debugu w Image: $(strings $I | grep -c 's10probe\|S10+ probe\|S10+ diag\|S10+ panic')"
echo "slady w starym: $(strings $D/pidfd2/arch/arm64/boot/Image | grep -c 's10probe\|S10+ probe\|S10+ diag\|S10+ panic')"
cp $I /mnt/c/Users/Artur/AppData/Local/Temp/claude/C--Users-Artur-Documents-Serwis-Programowanie-S10Plus-Linux/5ee327dd-1f6c-4e5e-9fb7-af3549eb8bde/scratchpad/boot/Image-czysty
