#!/bin/sh
# pahole jest tylko w WSL (Debian: pakiet dwarves), a Kconfig czyta z niego
# wersje, od ktorej zalezy BTF (PAHOLE_VERSION w lib/Kconfig.debug). Uzywa go
# scripts/check-kconfig.sh, gdy w PATH nie ma wlasnego pahole.
exec wsl.exe -d Debian -- pahole "$@"
