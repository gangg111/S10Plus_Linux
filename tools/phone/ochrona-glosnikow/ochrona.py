#!/usr/bin/env python3
"""Ochrona glosnikow Galaxy S10+: firmware CSPL obu CS35L40 z kalibracja fabryczna.

Kolejnosc jak w mainline cs35l41_hda i u producenta (cirrus-cal.c): firmware
zaladowany (Preload), kalibracja wpisana, zanim DSP ruszy, potem tor audio
przez DSP.  Po starcie DSP firmware zeruje pola kalibracji, a przyjecie
potwierdza CAL_SET_STATUS = 2 (bez kalibracji 1); zmierzone 26.09.2026.

Kontrolki kalibracji sa ulotne, a cs_dsp odrzuca ich zapis, dopoki DSP nie
pracuje (EPERM), choc wlasnie wtedy firmware ma je dostac.  Dlatego pola
CAL_R, CAL_AMBIENT, CAL_STATUS i CAL_CHECKSUM ida jednym transferem I2C pod
adres producenta 0x02800224 (calibration.h), zaraz po zaladowaniu firmware.
To obejscie; docelowo kalibracje powinien wpisywac sterownik.

Wartosci: sec_efs/cirrus tego egzemplarza (kopia D:\\S10Plus-backup):
rdc_cal 8173 (sluchawka, 0x41), rdc_cal_r 8523 (dolny, 0x40), temp_cal 29.
CAL_CHECKSUM = CAL_STATUS + CAL_R, jak u producenta i w mainline.

Po kalibracji tor dostaje ustawienia Androida dla glosnikow (mixer_gains.xml
z partycji vendor): DSP RX2 Source = ASPRX1, AMP PCM Gain 17 (u nas Analog
PCM Volume, to samo pole), Digital PCM Volume 817 (0 dB, tez to samo pole).
Wzmocnienie idzie dopiero po wlaczeniu ochrony.  Zmierzone 27.09.2026: VMON
+17 dB (107 -> 756), kanaly rozdzielone, CSPL_STATE 0.  Do tego VPBR (ochrona
przed spadkiem napiecia baterii) z tymi samymi wartosciami co Android.

Uzycie (root):  ochrona.py [--karta 0] [--sprawdz]
"""
import argparse
import fcntl
import os
import struct
import subprocess
import sys
import time

KALIBRACJA = {"Bottom": 8523, "Top": 8173}
ADRES_I2C = {"Bottom": 0x40, "Top": 0x41}      # hsi2c38 = /dev/i2c-1
MAGISTRALA = 1
CAL_RDC = 0x02800224                            # RDC, AMBIENT, STATUS, CHECKSUM
OTOCZENIE = 29
ANDROID = [("DSP RX2 Source", "ASPRX1"), ("Digital PCM Volume", "817"),
           ("Analog PCM Volume", "17"),
           # ochrona przed spadkiem napiecia baterii (latka 0139), mixer_paths.xml
           ("VPBR Release Rate", "5ms"), ("VPBR Wait", "10ms"),
           ("VPBR Attack Rate", "2.5us"), ("VPBR Attack Volume", "1dB"),
           ("VPBR Max Attenuation", "2"), ("VPBR Threshold 1", "2.687"),
           ("VPBR Switch", "on")]

IFACE_MIXER = 2
ELEM_VALUE = 1224                      # sizeof(struct snd_ctl_elem_value), aarch64
ELEM_READ = 0xC0000000 | (ELEM_VALUE << 16) | (ord('U') << 8) | 0x12
DANE = 72                              # przesuniecie unii value


def element(nazwa, dane=b""):
    ident = struct.pack("<IiII44sI", 0, IFACE_MIXER, 0, 0, nazwa.encode(), 0)
    buf = bytearray(ELEM_VALUE)
    buf[:len(ident)] = ident
    buf[DANE:DANE + len(dane)] = dane
    return buf


def czytaj(fd, nazwa):
    buf = element(nazwa)
    fcntl.ioctl(fd, ELEM_READ, buf)
    return struct.unpack_from(">I", buf, DANE)[0]


def kalibruj_i2c(wz, rdc):
    slowa = struct.pack(">I4I", CAL_RDC, rdc, OTOCZENIE, 1, rdc + 1)
    subprocess.run(["i2ctransfer", "-f", "-y", str(MAGISTRALA),
                    "w%d@0x%02x" % (len(slowa), ADRES_I2C[wz])] +
                   ["0x%02x" % b for b in slowa], check=True)
    odczyt = subprocess.run(["i2ctransfer", "-f", "-y", str(MAGISTRALA),
                             "w4@0x%02x" % ADRES_I2C[wz]] +
                            ["0x%02x" % b for b in struct.pack(">I", CAL_RDC)] +
                            ["r16"], check=True, capture_output=True, text=True).stdout
    if bytes(int(x, 16) for x in odczyt.split()) != slowa[4:]:
        raise SystemExit("%s: kalibracja nie zapisala sie: %s" % (wz, odczyt.strip()))


def amixer(karta, *arg):
    subprocess.run(["amixer", "-q", "-c", str(karta), "cset"] + list(arg),
                   check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--karta", type=int, default=0)
    p.add_argument("--sprawdz", action="store_true",
                   help="tylko wypisz stan (DSP musi pracowac)")
    a = p.parse_args()
    fd = os.open("/dev/snd/controlC%d" % a.karta, os.O_RDWR)

    if a.sprawdz:
        for wz in KALIBRACJA:
            k = "%s DSP1 Protection cd " % wz
            print("%s: CAL_SET_STATUS=%d CSPL_STATE=%d temp=%.2f" % (
                wz, czytaj(fd, k + "CAL_SET_STATUS"), czytaj(fd, k + "CSPL_STATE"),
                czytaj(fd, k + "CSPL_TEMPERATURE") / 16384))
        return 0

    for wz in KALIBRACJA:
        # swieze zaladowanie: kalibracja musi trafic przed start DSP
        amixer(a.karta, "name=%s PCM Source" % wz, "ASP")
        amixer(a.karta, "name=%s DSP1 Preload Switch" % wz, "0")
    time.sleep(0.5)
    for wz in KALIBRACJA:
        amixer(a.karta, "name=%s DSP1 Firmware" % wz, "Protection")
        amixer(a.karta, "name=%s DSP1 Preload Switch" % wz, "1")
    time.sleep(1.5)
    for wz, rdc in KALIBRACJA.items():
        kalibruj_i2c(wz, rdc)
        amixer(a.karta, "name=%s PCM Source" % wz, "DSP")
        print("%s: firmware zaladowany, kalibracja R=%d, otoczenie %d, tor przez DSP"
              % (wz, rdc, OTOCZENIE))
    for wz in KALIBRACJA:
        for nazwa, wartosc in ANDROID:
            amixer(a.karta, "name=%s %s" % (wz, nazwa), wartosc)
    print("wzmocnienie jak w Androidzie: " +
          ", ".join("%s %s" % k for k in ANDROID))
    return 0


if __name__ == "__main__":
    sys.exit(main())
