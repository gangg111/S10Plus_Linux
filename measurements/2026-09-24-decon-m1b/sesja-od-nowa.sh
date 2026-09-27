#!/bin/sh
# Czysty restart sesji Plasmy: bez tego KWin (usluga uzytkownika) przezywa
# restart plasma-mobile, traci mastera DRM albo startuje bez nowego env.
systemctl stop plasma-mobile
systemctl stop user@10000.service
sleep 2
systemctl start plasma-mobile
