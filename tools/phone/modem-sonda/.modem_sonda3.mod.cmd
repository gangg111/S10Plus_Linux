savedcmd_modem_sonda3.mod := printf '%s\n'   modem_sonda3.o | awk '!x[$$0]++ { print("./"$$0) }' > modem_sonda3.mod
