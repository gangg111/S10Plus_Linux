# R3 — dotyk

**Odpowiedź:** Kontroler to Samsung **Y771** (rodzina S6SY76x), a mainline **ma** dla niego sterownik —
`drivers/input/touchscreen/s6sy761.c` (544 linie, I2C, compatible `samsung,s6sy761`) — i jest on
**empirycznie potwierdzony na tym SoC**: port pmOS dla exynos9820 włącza `CONFIG_TOUCHSCREEN_S6SY761=y`
i opisuje panel dotykowy pod adresem 0x48 na `hsi2c10`, a autor portu raportuje działający dotyk na
oryginalnym panelu. Downstreamowy odpowiednik ma 12 552 linie — czyli mainline’owy driver jest ~23×
mniejszy i wystarcza.

## Dowody

### Co jest w telefonie (downstream)

- `CONFIG_TOUCHSCREEN_SEC_TS_Y771=y`
  (`LineageOS/android_kernel_samsung_exynos9820@7d08ec36:arch/arm64/configs/exynos9820-beyond2lte_defconfig:2286`).
- Sterownik: katalog `drivers/input/touchscreen/sec_ts/y771/` (jest też wariant `y771_d`).
  Interfejs: **I2C** — `static struct i2c_driver sec_ts_driver` (`…/y771/sec_ts.c:3210`),
  tablica id `{ SEC_TS_I2C_NAME, 0 }` (`:3190`).
- Rozmiar (wc -l, pobrane pliki — log `build-logs/09-r3-y771-wc.log`):

| plik | linie |
|---|---|
| `sec_ts.c` | 3251 |
| `sec_ts.h` | 965 |
| `sec_ts_fn.c` | 6666 |
| `sec_ts_fw.c` | 1013 |
| `sec_ts_ioctl.c` | 333 |
| `sec_ts_only_vendor.c` | 296 |
| Kconfig + Makefile | 28 |
| **razem** | **12 552** |

### Co jest w mainline

- `linux@1200d84f4c0a:drivers/input/touchscreen/s6sy761.c` — 544 linie,
  `{ .compatible = "samsung,s6sy761" }` (`:516`), rejestry protokołu w `:19-57`
  (`S6SY761_DEVICE_ID 0x52`, `S6SY761_READ_ONE_EVENT 0x60`, …), zasilanie przez
  `regulator_bulk` (avdd + vdd).
- Binding: `linux@1200d84f4c0a:Documentation/devicetree/bindings/input/touchscreen/samsung,s6sy761.yaml:17`
  (`const: samsung,s6sy761`), przykład w `:45`.

### Most między Y771 a s6sy761 — dowód, nie analogia

Port mainline dla exynos9820 opisuje ten sam układ przez mainline’owy compatible:

```
chiffathefox/u-boot@c5afa30840d9:dts/upstream/src/arm64/exynos/exynos9820-common.dtsi:151-165
  &hsi2c10 {
      clock-frequency = <400000>;
      touchscreen@48 {
          compatible = "samsung,s6sy761";
          reg = <0x48>;
          avdd-supply = <&ldo27m>;      /* tsp_avdd 3.0 V, s2mps19 */
          vdd-supply  = <&ldo19m>;      /* tsp_io   1.8 V, s2mps19 */
          interrupts-extended = <&gpa1 0 IRQ_TYPE_LEVEL_LOW>;
          pinctrl-0 = <&ts_int>;        /* gpa1-0, EINT */
      };
  };
```

Regulatory: `…/exynos9820-common.dtsi:131-146` (`ldo19m` = `tsp_io` 1.8 V, `ldo27m` = `tsp_avdd` 3.0 V,
PMIC `samsung,s2mps19-pmic` na ACPM).

Konfiguracja jądra pmOS: `CONFIG_TOUCHSCREEN_S6SY761=y`
(`pmaports@78958726:device/testing/linux-postmarketos-exynos9820/config-postmarketos-exynos9820.aarch64:2562`).

Status empiryczny (autor portu, `pmaports!8999`, sekcja *Touchscreen*):
„Works with an original panel. With an aftermarket panels the driver probes and communicates with
the IC, but there are no touch events available. IC seems to report a hardcoded state."
Wiki pmOS dla `samsung-exynos9820`: `status_touch = P`.

### Co to znaczy dla bramki B4

B4 **przestaje być otwartym pytaniem**: nie trzeba pisać drivera. Zakres pracy to (1) węzeł
`hsi2c10` + `touchscreen@48` w DT (już zrobione w artefakcie tej fazy —
`patches/0012-arm64-dts-exynos-*.patch`), (2) zasilanie TSP: docelowo s2mps19/ACPM, tymczasowo
`regulator-fixed`, (3) sprawdzenie, czy nasz egzemplarz ma **oryginalny** panel — bo aftermarket
nie generuje zdarzeń mimo poprawnego probe’a.

## Czego nie udało się ustalić

- Czy Y771 i S6SY761 to ten sam krzem, czy tylko zgodny protokół — w `sec_ts.c` nie ma stringa
  „S6SY" (grep: `build-logs/09-r3-y771-wc.log`). Ustalono to **funkcjonalnie** (driver działa), nie
  z dokumentacji.
- Czy oryginalny panel w naszym SM-G975F jest oryginalny — **do sprawdzenia na sprzęcie** (B4).
- Wariant `y771_d` (drugi katalog w downstreamie) — nie ustalono, dla której płyty jest przeznaczony.

## Jak ten dotyk dziala u nas (stan 20.09.2026)

Caly lancuch jest juz w serii. Ponizej ogniwo po ogniwie, kazde z plikiem.

### Droga od palca do zdarzenia

| ogniwo | co to jest | gdzie u nas |
|---|---|---|
| panel | Samsung Y771, rodzina S6SY76x | firmware producenta `tsp_sec/y771_beyond2_phole.bin` |
| adres | `0x48` na magistrali | wezel `touchscreen@48` w naszym `exynos9820-beyond2lte.dts` |
| magistrala | `hsi2c10` = `i2c@104b0000`, 400 kHz | `hsi2c10` w naszym `exynos9820.dtsi`, czestotliwosc w pliku plyty |
| tryb bloku | ten sam krzem obsluguje UART, SPI i I2C; wybiera go USI | wezel `usi3: usi@104b00c0` w naszym `exynos9820.dtsi` |
| piny magistrali | `gpp1-4` = SCL, `gpp1-5` = SDA, funkcja 2 | pinctrl `hsi2c10-bus` |
| przerwanie | `gpa1-0` jako EINT, wyzwalanie poziomem NISKIM | `interrupts-extended = <&gpa1 0 IRQ_TYPE_LEVEL_LOW>` |
| zasilanie | `tsp_io` 1,8 V i `tsp_avdd` 3,0 V | atrapy `regulator-fixed` w naszym pliku plyty |
| sterownik | `samsung,s6sy761`, 544 linie | `CONFIG_TOUCHSCREEN_S6SY761=y` |
| wyjscie | `/dev/input/eventN`, zdarzenia `ABS_MT_*` | `CONFIG_INPUT_EVDEV=y` |

Zasilanie jest **atrapa i to jest swiadome**. Prawdziwe szyny wisza na PMIC-u
S2MPS19, ktorego mainline nie obsluguje i ktory chodzi po wlasnym transporcie
(ACPM/SPEEDY). Producent oznacza obie szyny `regulator-boot-on`, wiec zakladamy,
ze bootloader zostawia je wlaczone. `regulator-fixed` bez GPIO nie ma czego
wylaczyc, a `regulator-always-on` i tak nie wpuszcza rdzenia do wylaczania,
wiec sterownik moze wolac `regulator_disable` do woli i nic sie nie stanie.

**To zalozenie nie jest jeszcze zmierzone** i ma pulapke diagnostyczna: rdzen
regulatora bez `ops->is_enabled` zwraca „wlaczone" ZAWSZE, wiec zaden log jadra
nie wykryje zgaszonej szyny. Gdy dotyk nie odpowie, najpierw napiecia, dopiero
potem magistrala.

### Czego brakowalo i co zmienilem

Sterownik i drzewo byly kompletne od poprzedniej sesji. Dotyku nie dalo sie
jednak ZOBACZYC, bo brakowalo dwoch rzeczy po stronie userlandu. Oba objawy
widac wprost w logu z telefonu:

1. `modprobe: FATAL: Module uinput not found`. Klawiatura ekranowa buffyboard
   wstrzykuje zdarzenia przez `/dev/uinput`. Dodane `CONFIG_INPUT_UINPUT=y`.
   Musi byc `=y`, bo ten build robi tylko `Image dtbs`, nigdy `modules`, wiec
   kazde `=m` w tym drzewie jest martwe.

2. `setfont: ioctl 0x4b72 failed: Function not implemented` oraz
   `/dev/tty0 is not available`. Terminale wirtualne SA wlaczone, ale siedza na
   `dummycon`, bo NIKT nie przejmowal wezla `/chosen/framebuffer@ca000000`.
   `CONFIG_FB_EFI` jest tu bezuzyteczne: gdy bufor jest opisany w drzewie
   urzadzen, `of_platform` wola `sysfb_disable()` i urzadzenie `efi-framebuffer`
   nigdy nie powstaje. Dodane `CONFIG_DRM_SIMPLEDRM=y`, a `/dev/fb0` daje juz
   wlaczone `CONFIG_DRM_FBDEV_EMULATION=y`.

Oba symbole siedza w **fragmencie uruchomieniowym**, nie w konfiguracji serii.
SIMPLEDRM seria wylacza swiadomie (HW-36: razem z `drm/exynos` powstalyby dwa
urzadzenia DRM na jeden ekran, bo w `drivers/gpu/drm/exynos` nie ma ani jednego
`aperture_remove_conflicting_devices`). W jadrze uruchomieniowym `drm/exynos`
jest wylaczony, wiec konfliktu nie ma, ale decyzja jest tymczasowa i tam wlasnie
jej miejsce.

Adres bufora sprawdzony po obu stronach: jadro ma `framebuffer@ca000000`
1440x3040x4 (wezel `framebuffer0` w naszym pliku plyty), U-Boot ten sam wezel i
`CONFIG_VIDEO_SIMPLE=y`. W wierszu rozruchowym zostaje `keep_bootcon`, wiec
gdyby przejecie konsoli zawiodlo, `earlycon` nadal pisze.

### Dowod dzialania, do wykonania na telefonie

Bez tego nie oglaszac sukcesu. Poprawny probe NIE jest dowodem dzialajacego
dotyku: autor portu pmOS raportuje, ze na panelu ZAMIENNYM sterownik probuje
i rozmawia z ukladem, a zdarzen nie ma, bo uklad zglasza zamrozony stan.

```sh
dmesg | grep -iE 'simpledrm|simple-framebuffer|fbcon|Console: switching'
ls -l /dev/fb0 /dev/uinput
dmesg | grep -i s6sy761
grep -A4 s6sy761 /proc/bus/input/devices
evtest /dev/input/eventN      # przesun palec wolno po przekatnej
```

Dowodem jest dopiero `ABS_MT_POSITION_X` i `_Y` zmieniajace sie plynnie.

### Piec pulapek, ktore czekaja

1. **Moment wyslania SENSE_ON.** Mainline wysyla je dopiero w `input_open`,
   czyli gdy przestrzen uzytkownika otworzy `/dev/input/eventN`. Producent
   wysyla juz na koncu probe. Objaw: sterownik zaladowany, urzadzenie widoczne,
   przerwan ZERO, dopoki nie uruchomi sie `evtest` albo kompozytor. Wyglada
   identycznie jak martwy dotyk. Nie diagnozowac jako awarii sprzetu, zanim nie
   otworzy sie urzadzenia.

2. **Uklad bajtow zdarzenia.** Rozmieszczenie polbajtow X i Y w bajcie 3 jest
   w mainline zgodne z tym, co widac w `sec_ts.c` (pola `x_11_4`, `x_3_0`,
   `y_11_4`, `y_3_0` sklejane przesunieciem o 4 bity), ale ktora polowka jest
   ktora, nie da sie z repozytorium rozstrzygnac, bo brakuje `sec_ts.h`. Objaw
   pomylki: wspolrzedne skacza skokami po 15 jednostek albo dotyk jest
   przesuniety o ulamek szerokosci ekranu. Sprawdzenie jest tanie: wolny ruch
   palcem po przekatnej w `evtest`.

3. **Maska licznika zaleglych zdarzen.** Producent maskuje bajt 7 wartoscia
   `0x1F`, mainline `0x3f`. Jesli Y771 uzywa gornego bitu na cos innego,
   mainline przy dotyku dlonia albo mokrym palcem policzy zaleglosci ZA DUZO
   i zrobi odczyt dluzszy niz bufor. Objaw: sporadyczne smieci albo bledy I2C
   przy dotyku wieksza powierzchnia. Maske producenta uznac za wzorcowa.

4. **Liczba slotow multitouch.** `s6sy761` inicjalizuje sloty liczba kanalow TX
   z informacji o panelu, a nie liczba palcow. Objaw: jeden i dwa palce dzialaja,
   przy wiekszej liczbie czesc palcow znika.

5. **Brak resetu awaryjnego.** Producent nie ma `reset-gpio` i resetuje uklad
   wylacznie cyklem zasilania z przerwa 30 ms. Przy atrapach `regulator-fixed`
   ta droga jest zamknieta: gdy kontroler dotyku zawiesi sie albo zostanie
   w bootloaderze, jedynym wyjsciem jest restart calego telefonu.

Osobno, na pozniej: `s6sy761_suspend` gasi zasilanie, a `s6sy761_resume`
po 140 ms zada swiezego `BOOT_COMPLETE`. Przy atrapach uklad nie zgasnie, wiec
go nie wystawi i dotyk moze nie wrocic po uspieniu. Na etapie uruchamiania
nieistotne, bo nie usypiamy telefonu.

## Wynik na sprzecie, 20 wrzesnia 2026

Dotyk dziala. Sterownik `s6sy761` wiaze sie z ukladem pod 0x48 i wystawia
urzadzenie wejsciowe:

```
input: s6sy761 as /devices/platform/soc@0/104b00c0.usi/104b0000.i2c/i2c-0/0-0048/input/input0
```

Zmierzone przy przesuwaniu palcem: 2696 zdarzen, sledzenie slotu, nacisk
i rozmiar plamki, zakres objety palcem X od 586 do 2788, Y od 1432 do 3222.
Zakresy osi prosto z jadra: `ABS_MT_POSITION_X` i `ABS_MT_POSITION_Y` od 0 do
4096, `ABS_MT_SLOT` od 0 do 16, nacisk i plamka od 0 do 255.

### Co naprawde stalo na drodze

Diagnoza z tego dokumentu trafila w uklad (Y771), ale przyczyny niezwiazania
sie sterownika byly inne niz piec przewidzianych pulapek. Byly trzy.

1. **Kontroler magistrali stal na wysylaniu adresu.** Stan `MASTER_ST_ADDR1`
   przed transferem nie mija sam i nie kasuje sie przy nastepnym transferze,
   wiec kazdy kolejny konczyl sie natychmiast, a uklad wygladal na nieobecny.
   Skan, ktory resetowal blok przed kazdym adresem, znajdowal 0x48; ten sam
   adres przez sterownik odpowiadal bledem braku urzadzenia. Poprawka w serii:
   reset kontrolera, gdy przed transferem stoi on w tym stanie.

2. **Rejestr stanu wgrania 0x21 w tym ukladzie nie istnieje.** Odpowiada
   bledem braku urzadzenia przy kazdej probie i kazdej dlugosci, podczas gdy
   0x20, 0x22 i 0x24 czytaja sie normalnie (0x00, 0x53, 0x02). Sterownik zadal
   z niego wartosci 0x80 i konczyl sondowanie porazka. Identyfikator ukladu to
   `ac 37 71`, czyli Y771, wiec roznica jedzie w serii jako osobna zgodnosc
   `samsung,s6sy771` z wlasnymi danymi dopasowania.

3. **Pulapka numer 5 z tego dokumentu okazala sie do obejscia.** Sterownik
   czeka na zdarzenie zakonczenia rozruchu, ktore uklad wystawia po cyklu
   zasilania, a przy atrapach `regulator-fixed` cyklu nie ma i w stosie leza
   stare zdarzenia (odczyt dawal `1d 61 02 02 03 00 00 1f`). Uklad ma jednak
   wlasna komende restartu, 0x12, po ktorej odczyt daje
   `09 00 40 00 00 00 00 00`, czyli dokladnie to zdarzenie. Zmierzony czas:
   po 20 ms uklad jeszcze nie odpowiada, po 50 ms juz tak. To zamyka rowniez
   uwage o powrocie po uspieniu, bo `s6sy761_resume` idzie ta sama droga.

Pulapki 1 i 2 z listy powyzej nie wystapily: wspolrzedne przy wolnym ruchu po
przekatnej rosna plynnie, wiec uklad polbajtow jest dobry, a `SENSE_ON`
wychodzi z `input_open` i wystarczy otworzyc `/dev/input/event0`.

### Co poszlo do serii

| plik | co robi |
|---|---|
| `0067` | reset kontrolera magistrali stojacego na adresie |
| `0068` | restart ukladu, gdy nie zglasza zakonczenia rozruchu |
| `0069` | zgodnosc `samsung,s6sy771` w opisie wiazania |
| `0070` | obsluga Y771, czyli pominiecie nieistniejacego rejestru |
| `0071` | ostrzezenie o osiach patrzy na osie, ktore sterownik ustawia |

Narzedzia pomiarowe uzyte po drodze, wszystkie wlasne i budowane krzyzowo:
`i2cblk` (odczyt blokowy z magistrali), `i2cw` (zapis komend), `evread`
(podglad zdarzen wejscia), `evabs` (zakresy osi prosto z jadra).
