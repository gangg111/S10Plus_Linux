savedcmd_modem_sonda.mod := printf '%s\n'   modem_sonda.o | awk '!x[$$0]++ { print("./"$$0) }' > modem_sonda.mod
