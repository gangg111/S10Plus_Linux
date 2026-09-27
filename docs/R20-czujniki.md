# R20: hub czujników i obracanie ekranu

Stan na 27.09.2026 (jądro #87, łatki 0142-0144, moduł spoza drzewa `tools/phone/hub-modul`,
demon `tools/phone/hubd`).

## Układ

Wszystkie czujniki ruchu i otoczenia (LSM6DSO akcelerometr i żyroskop, magnetometr, ciśnienie,
światło, zbliżeniowy) siedzą za mikrokontrolerem Cortex-M4 w układzie GNSS BCM47752. Host
rozmawia z nim przez SPI17 (USI16 w PERIC1) z liniami uzgadniania host-req, mcu-req, mcu-resp,
shub-int, batch-wake i gps-pwr-en (nStdby). Rdzeń huba zasila LDO21M głównego PMIC-a
(`vdd_mcu_1p8`), który Android trzyma zawsze włączony; u nas po S-Boocie był wyłączony, a bez
niego hub milczy.

## Co działa, z dowodem

| Element | Dowód |
|---|---|
| zasilanie huba | `vdd_mcu_1p8: enabled 1800000` po starcie (LDO21M `regulator-always-on`, łatka 0144) |
| SPI17 i urządzenie | `spi1.0` z modaliasem `spi:bcm47752`, moduł tworzy `/dev/ttyBCM` i `/dev/bbd_*` |
| rozruch huba (`hubd`) | ROM po 113 ms, firmware 486 RPC / 445 094 B w 0,9 s, aplikacja po 1,2 s, ramki RELIABLE 512/512 potwierdzone |
| akcelerometr | `accel_3d` w IIO: płasko 64, 53, 4106 przy skali 0,002394 m/s² (4096 na g), odczyty zmieniają się z ruchem |
| orientacja | `iio-sensor-proxy` (tryb `iio-poll-accel`) i KWin z polityką `always`: wszystkie cztery położenia potwierdzone przy telefonie |
| start bez człowieka | zimny restart: `hubd`, `iio-sensor-proxy` aktywne, akcelerometr włączony sam, zero nieudanych jednostek |

## Pułapki, każda kosztowała iterację

1. **Zawieszenie przy `poll_delay`.** `set_sensor_delay` producenta zwracał 0, a zapis sysfs
   zwracający 0 `echo` powtarza bez końca, za każdym razem wysyłając do huba komunikat SPI.
   Telefon odpowiadał na ping, ale SSH stał, potrzebny był reset przyciskami. Po `return size`
   zapis wraca od razu.
2. **Demon musi żyć.** `hubd` uruchomiony z krótkotrwałego skryptu przez `systemd-run` ginie
   razem z nim (systemd zamyka grupę procesów jednostki). Po zamknięciu `/dev/ttyBCM` jądro pisze
   `lhd is NULL`, a hub przestaje wysyłać dane: akcelerometr stoi na pierwszej próbce. Stąd
   osobna usługa `hubd.service`.
3. **Znak osi.** Hub raportuje w układzie Androida (telefon pionowo: +1 g na y). Dla
   `iio-sensor-proxy` to `bottom-up`, więc `accel_3d` ma macierz montażu `-1` na przekątnej
   (`in_accel_mount_matrix`). Sprawdzone we wszystkich czterech położeniach.
4. **IIO producenta jest nietypowe.** Każdy czujnik to urządzenie z jednym kanałem „timestamp”
   i surowym blokiem danych, czego ogólne czytniki nie rozumieją. `accel_3d` wystawia ostatnią
   próbkę jako zwykłe `in_accel_{x,y,z}_raw` ze skalą.
5. **KWin obraca tylko w trybie tabletu.** Polityka `autoRotation` w
   `~/.config/kwinoutputconfig.json` była `InTabletMode`; zmiana na `Always` działa tylko przy
   zatrzymanej sesji, bo KWin przy zamykaniu nadpisuje plik swoim stanem.
6. **DT zgodne z dtschema.** Właściwości producenta (`ssp-acc-position`, bajtowe tablice bez
   typu, compatible `ssp,BCM4773`) nie przechodzą walidacji; w serii są `brcm,*`, linie jako
   zwykłe `*-gpios`, tablice termistorów jako `/bits/ 16`. Bajty wszystkich wartości porównane
   z drzewem testowym: zgodne.

## Światło i zbliżeniowy

Moduł huba wystawia dwa zwykłe urządzenia IIO obok `accel_3d`: `als` (`in_illuminance_input`,
luksy liczone przez hub z TCS3407 pod panelem) i `proximity` (`in_proximity_raw` plus
`in_proximity_nearlevel`, parametr modułu `prox_near`, domyślnie 3200). Hub zgłasza
zbliżeniowy tylko przy zmianie swojej decyzji blisko/daleko, więc o stronie progu decyduje
jego flaga wykrycia, a nie próg hosta. `hubd` włącza przy starcie akcelerometr i światło
(maska 513). Zbliżeniowy zostaje wyłączony, bo bez rozmów nikt go nie czyta.

| Test (ręka i latarka, 27.09.2026) | Światło | Zbliżeniowy |
|---|---|---|
| pokój | 41-44 lux | daleko |
| zasłonięcie | 10 lux | blisko, 3532 |
| odsłonięcie | 42 lux | daleko, 3051 |
| latarka | do 4454 lux | daleko |

`iio-sensor-proxy`: `HasAmbientLight`, `HasProximity`, `HasAccelerometer` = true.

Pułapki:

1. **Maska włączała tylko jeden czujnik.** `set_sensors_enable` producenta kończył pętlę na
   pierwszym zmienionym bicie (Android zmienia po jednym), a zapisywał całą maskę. Przy
   przejściu 1 → 641 hub dostał tylko zbliżeniowy, światło było „włączone” bez `ADD = 9`
   (w linii stanu huba `Light:0`). Pętla idzie teraz po wszystkich bitach.
2. **`lux` i `raw_data` w `/sys/class/sensors/light_sensor` czytają bufor UNCAL_LIGHT (typ 40)**,
   nie LIGHT (typ 9), więc przy włączonym tylko typie 9 pokazują zera.
3. **`poll_delay` surowych urządzeń producenta czyta się jako puste** (`show_sensor_delay`
   zwraca 0), co nie znaczy, że zapis się nie udał.
4. **Fałszywe „blisko” po włączeniu (rozwiązane).** Pierwszy raport huba ma flagę wykrycia
   255 (nieustalone), potem hub melduje tylko zmiany (1 blisko, 0 daleko; w jego logu
   `Sensor_Proxi-x,STAN` to 1, 3, 2). Każda niezerowa flaga dawała „blisko”, a odsłonięty
   telefon zostawał przy 255 na zawsze. Teraz przy 255 decyduje sam odczyt względem
   `prox_near`. Druga połowa: bufor przeżywał wyłączenie i po ponownym włączeniu pokazywał
   stan poprzedniej sesji; wyłączenie ustawia teraz 255 i odczyt 0. Sprawdzone: trzy
   włączenia odsłonięte 3050/3070/3066 (daleko), włączenie przy zasłoniętym 3941 (blisko),
   po wyłączeniu i ponownym włączeniu 0, po 2 s świeże 3055.
5. **Mignięcie „daleko” przy ruchu ręki (rozwiązane).** Hub potrafi zgłosić daleko i po
   0,94 s znów blisko (3137 → 3430), co przy uchu zapaliłoby ekran. Przejście w blisko jest
   natychmiastowe, w daleko dopiero po `prox_far_ms` (parametr modułu, domyślnie 1500 ms).
   Sprawdzone ręką: mignięcie huba 86,23 → 87,17 s nie wyszło poza IIO (ciągłe blisko),
   prawdziwe odsłonięcie dało daleko po 1,46 s.

## Żyroskop, magnetometr, ciśnienie

Trzy kolejne zwykłe urządzenia IIO w module huba: `gyro_3d` (LSM6DSO, `in_anglvel_*`),
`magn_3d` (AK09916C, `in_magn_*`, dane „skalibrowane” huba) i `baro` (LPS22H,
`in_pressure_*` w kPa, `in_temp_*`). Włączane maską huba (bity 1, 4, 5); domyślnie
wyłączone, bo nikt ich jeszcze nie czyta.

Hub nie podaje liczników układów, więc skale z not nie pasują (70 m°/s na jednostkę dawało
31 °/s na leżącym telefonie). Zmierzone na telefonie:

| Czujnik | Skala | Dowód |
|---|---|---|
| ciśnienie | 1/4096 hPa, temperatura 1/100 °C | 4163479 → 101,647 kPa (1016,5 hPa) |
| żyroskop | 603,6 nrad/s | cztery obroty o 90° płasko na stole: 2 609 039, 2 575 653, 2 609 296, 2 615 750 jedn.·s, razem 2π; w spoczynku potem ~0,0006 rad/s |
| magnetometr | ~0,0714 µT (±10-15 %) | spoczynki między obrotami na okręgu o promieniu 267,4 jedn., pole poziome 19,1 µT (środkowa Polska); środek (1177, −269) to przesunięcie od magnesów telefonu |

Skale są parametrami modułu (`gyro_skala_nano`, `magn_skala_nano`, zmienialne w locie).
Magnetometr nie nadaje się jeszcze na kompas: hub zgłasza dokładność 0 i nie odejmuje
przesunięcia (~84 µT).

## Wibracja i czujnik etui (jądro #91, łatki 0145-0148)

Poza hubem, więc osobno. Silnik to aktuator liniowy sterowany blokiem haptycznym max77705
z kanału 1 PWM w PERIC0 (gpp3-1), okres 48828 ns, czyli 160 Hz za dzielnikiem 128 układu.
Zasilanie to MOTOR_BOOST_EN na gpg1-7 opisane jako regulator stały `vdd_motor`. Etui wykrywa
czujnik Halla na gpa3-6 (gpio-keys, `SW_LID`, linia aktywna niska).

| Element | Dowód |
|---|---|
| sondy | `input: max77693-haptic`, `input: Hall Effect Sensor`, `pwmchip0` z 5 kanałami, pwm-1 `requested` przez `haptic` |
| wibracja | efekt FF_RUMBLE 1,5 s o sile 0xc000: MCONFIG (0x10) 0x82 → 0xc2 → 0x82, BIASEN w MAINCTRL1 = 0x81, pwm-1 `enabled 42724/48828 ns` (87,5 %, bo sterownik mapuje 0..0xffff na 50..100 %) |
| etui otwarte | linia gpa3-6 wysoka, `SW_LID` = 0, hub zgodnie: `SSP_HALL_IC = 0`; zamknięcia jeszcze nie sprawdzono |

**Pułapka:** sterownik włącza `vdd_motor` przy otwarciu urządzenia wejścia, a nie przy efekcie.
Demon `podbicie` otwierał wszystkie `/dev/input/event*` i trzymał boost silnika stale
(`users=1`). Teraz pomija urządzenia bez EV_KEY/EV_ABS/EV_REL: `vdd_motor disabled users=0`.

## Czego jeszcze nie ma

Żyroskop, magnetometr i ciśnienie hub już obsługuje, ale nie mają zwykłych kanałów IIO.
Automatycznej jasności jeszcze nie ma: czujnik światła jest gotowy, brakuje czytelnika,
który przełoży luksy na jasność panelu. GNSS wymaga zamkniętego silnika pozycji (`gpsd`
producenta). Akcelerometr jest włączony stale z okresem 60 ms (jak Android przy obracaniu).
