# Temperatura SoC, taktowanie rdzeni i koszt kopii klatki (24.09.2026)

Jadro #56 (seria do 0104), postmarketOS edge z Plasma Mobile 6.7.5 na
simpledrm, telefon na kablu, bateria pelna. Wszystko ponizej to odczyt
z telefonu, nie wartosc z dokumentacji.

## Taktowanie rdzeni bez cpufreq (`takt.c`)

Lancuch zaleznych `ADD` (1 cykl na A55, A75 i M4), czas procesora watku,
wiec obciazenie przez Plasme nie zaniza wyniku. Najlepszy z 5 przebiegow.

| rdzenie | klaster | zmierzone | maksimum ukladu |
|---|---|---|---|
| cpu0-3 | Cortex-A55 | 1047-1053 MHz | 1950 MHz |
| cpu4-5 | Cortex-A75 | 1222 MHz | 2314 MHz |
| cpu6-7 | Samsung M4 | 1378 MHz | 2730 MHz |

1378 MHz dla M4 to dokladnie `boot-freq` wezla `exynos-hiu` producenta
(0x1506d0 kHz), czyli taktowanie zostawione przez S-Boot i firmware APM.

## Kopia pelnej klatki (`kopia.c`)

`memcpy` 1440x3040x4 = 17,5 MB, najlepszy z 20, pamiec zwykla (cache):

| rdzen | czas | przepustowosc kopii |
|---|---|---|
| cpu0 (A55) | 5,20 ms | 3,37 GB/s |
| cpu4 (A75) | 2,49 ms | 7,03 GB/s |
| cpu6 (M4) | 1,33 ms | 13,12 GB/s |

Pamiec nie jest waskim gardlem interfejsu: kopia simpledrm zajmuje co
najwyzej 8 % budzetu klatki 60 Hz na duzym rdzeniu. Zastrzezenie: simpledrm
pisze do pamieci write-combined, a tej sciezki z przestrzeni uzytkownika
nie zmierzylem.

## Temperatura przez firmware APM (`tmu_proba.c`)

Modul jednorazowy wola `acpm_tmu_init` i `acpm_tmu_read_temp` z mainline
na kanale 9 (wezel `acpm_tmu` producenta). Strefy firmware: 0 BIG, 1 MID,
2 LITTLE, 3 G3D, 4 ISP.

```
tmu-proba: kanal 9, INIT -> 0
bezczynnosc:           BIG 46  MID 44  LITTLE 44  G3D 43  ISP 44   (C)
po 20 s x 8 x `yes`:   BIG 58  MID 55  LITTLE 55  G3D 49  ISP 50
20 s po obciazeniu:    BIG 46  MID 45  LITTLE 44  G3D 44  ISP 45
```

Wartosci zyja: +12 C na klastrze BIG w 20 s przy zegarach z bootloadera.

Stan MMIO obu blokow wedlug ukladu 9820 producenta (tylko odczyt):

```
TOP TRIMINFO0 0082b91e CONTROL 00009503 (CORE_EN 1 THERM_TRIP_EN 1 TRIP_MODE 4)
    CONTROL1 000a0000 STATUS 07ff0130 TEMP 01300131
    THD_TEMP0 017b016d 01680163 015e0159 0154014f
SUB TRIMINFO0 0082b71e CONTROL 00009503 (CORE_EN 1 THERM_TRIP_EN 1 TRIP_MODE 4)
    CONTROL1 000a0000 STATUS 07ff0370 TEMP 01310132
    THD_TEMP0 0179016d 01680163 015e0159 0154014f
```

Kalibracja TOP z TRIMINFO0: kod 286 (bity 8:0) dla 25 C, kod 348
(bity 17:9) dla 85 C, wzor dwupunktowy producenta. Poziom 7 progow
(bity 24:16 rejestru 0xd0) = 0x17b = 379, czyli **115 C**. Biezacy kod
304-305 to 42-43 C, zgodnie z odczytem przez ACPM. **S-Boot uzbraja
sprzetowy trip przy 115 C w obu blokach.** To tlumaczy "twarde odciecie
zasilania" opisane przez port pmOS przy obciazeniu 8 rdzeni.

Wnioski wpiete w serie: latki 0106-0108 (binding, sterownik, DT z progiem
krytycznym 100 C) i `CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS=5000`.

## Jak powtorzyc

Modul buduje sie pod dzialajace jadro poza drzewem
(`make -C /home/pm/linux ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- M=<katalog> W=1 modules`),
potem `sudo insmod tmu_proba.ko; sudo rmmod tmu_proba; dmesg | grep tmu-proba`.
Programy `takt.c` i `kopia.c` kompiluja sie na telefonie (`apk add gcc musl-dev`)
i ida z `sudo nice -n -20`.
