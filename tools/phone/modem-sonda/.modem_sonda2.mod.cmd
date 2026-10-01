savedcmd_modem_sonda2.mod := printf '%s\n'   modem_sonda2.o | awk '!x[$$0]++ { print("./"$$0) }' > modem_sonda2.mod
