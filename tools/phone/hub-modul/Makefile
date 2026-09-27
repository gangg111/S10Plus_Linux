# SPDX-License-Identifier: GPL-2.0
# Budowa spoza drzewa (WSL Debian, uzytkownik pm):
#   make KDIR=/home/pm/linux
# Wlasciwa lista plikow jest w Kbuild.

KDIR ?= /home/pm/linux
ARCH ?= arm64
CROSS_COMPILE ?= aarch64-linux-gnu-
W ?= 1

# kfifo_buf jest modulem (CONFIG_IIO_KFIFO_BUF=m), a Module.symvers
# drzewa nie zawiera jego eksportow (drivers/iio/buffer/kfifo_buf.c:219,225).
KBUILD_EXTRA_SYMBOLS ?= $(CURDIR)/kfifo_buf.symvers
export KBUILD_EXTRA_SYMBOLS

all:
	$(MAKE) -C $(KDIR) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) M=$(CURDIR) W=$(W) modules

clean:
	$(MAKE) -C $(KDIR) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) M=$(CURDIR) clean

.PHONY: all clean
