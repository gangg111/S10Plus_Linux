### brcm_sensorhub.ko: hub czujnikow i GNSS Galaxy S10+ na mainline 7.2

Port sterownikow producenta `drivers/sensorhub/brcm` (LineageOS
`android_kernel_samsung_exynos9820` @7d08ec36) jako jeden modul spoza drzewa.
Uklad: BCM47752 (rodzina 4775 B0) za SPI17, protokol SSP nad mostem BBD.
Telefon byl niedostepny, wiec wszystko ponizej sprawdzono tylko kompilacja
i analiza statyczna. Zadnej funkcji nie uruchomiono na sprzecie.

Skroty: `orig/` to nietknieta kopia zrodel producenta obok katalogu `port/`
(ten sam katalog `czujniki`), `L` to drzewo `/home/pm/linux` w WSL (7.2.0).

### Budowa i wynik

```
MSYS_NO_PATHCONV=1 wsl.exe -d Debian -u pm -- sh <czujniki>/build.sh
# albo w WSL: make KDIR=/home/pm/linux          (W=1 jest domyslne)
# wariant z bcm_gps_hostwake.c:  make KDIR=/home/pm/linux BCM_GPS_HOSTWAKE=y
```

- Wynik: `make rc=0`, 0 bledow, 4 ostrzezenia W=1 (lista nizej). Tak samo
  dla wariantu `BCM_GPS_HOSTWAKE=y` (`build-hw.log`).
- `modinfo`: `alias of:N*T*Cssp,BCM4773`, `depends: kfifo_buf`,
  `parm: hw_rev`, licencja GPL.
- Modul zalezy od `kfifo_buf.ko` (`CONFIG_IIO_KFIFO_BUF=m`). Module.symvers
  drzewa nie ma jego eksportow, wiec `Makefile` podaje `kfifo_buf.symvers`
  przez `KBUILD_EXTRA_SYMBOLS` (eksporty: `L/drivers/iio/buffer/kfifo_buf.c:219,225`).
  Na telefonie: `modprobe kfifo_buf` przed `insmod`.

Ostrzezenia, ktore zostaly (celowo):

| Miejsce | Ostrzezenie | Dlaczego zostaje |
|---|---|---|
| `bbdpl/bbd_rpc_lh.c:407-410` (`orig`: 404-407) | `bReliableAckReceived`, `ucReliableAckSeqId`, `bReliableNackReceived`, `ucReliableNackSeqId` set but not used | Jadro producenta wylicza stan ACK/NACK pakietow RELIABLE, ktore samo zjada (RPC 0x21), i nigdy go nie wysyla. To otwarte pytanie z weryfikacji (T6: kto ACK-uje te pakiety). Uciszenie schowaloby jedyny slad tej luki w kodzie. |

### Co przeniesiono

| Plik | Skad | Uwagi |
|---|---|---|
| `ssp_dev.c`, `ssp_i2c.c`, `ssp_data.c`, `ssp_sysfs.c`, `ssp_firmware.c`, `ssp_debug.c`, `ssp_dump.c`, `ssp_dump.h`, `ssp_iio.c`, `ssp_iio.h`, `ssp_iio_ring.c`, `ssp_sensorhub.c`, `ssp_sensorhub.h`, `ssp_misc.c`, `ssp_bbd.c`, `ssp.h`, `sensor_list.h`, `sensors_core.c` | `brcm/` | `ssp_i2c.c` to mimo nazwy warstwa komend SSP; tak kompiluje go producent |
| `factory/accel_lsm6dsl.c`, `gyro_lsm6dsl.c`, `magnetic_common.c`, `pressure_lps22h.c`, `light_tmg399x.c`, `prox_autocal_ams.c`, `light_colorid.c` (+`.h`), `barcode_emul_tmg3992.c`, `thermistor.c`, `mcu_bcm4774.c` | `brcm/factory/` | dokladnie te, ktore wlacza defconfig producenta (LSM6DSO, MAGNETIC_COMMON, LPS22H, TMD4910, PROX_AUTOCAL_AMS, LIGHT_COLORID, MOBEAM, THERMISTOR, SSP_BBD) |
| `bbdpl/bbd.c`, `bbd.h`, `bbd_rpc_lh.c`, `bcm_gps_spi.c`, `bcm_gps_spi.h`, `bcm_gps_regs.c`, `bcm_gps_mem.c` | `brcm/bbdpl/` | |
| `bbdpl/bcm_gps_hostwake.c`, `.h` | `brcm/bbdpl/` | tylko z `BCM_GPS_HOSTWAKE=y`; producent go nie kompiluje (brak `CONFIG_BCM_GPS_HOSTWAKE_DRIVER` w defconfigu, a sam plik mial bledy skladni) |
| `bbdpl/r_os/bbd_patch_file_beyond.h` | `brcm/bbdpl/r_os/` | jedyny potrzebny patch (pkt a) |
| `ssp_port.c`, `ssp_port.h` | nowe | punkt wejscia modulu i zamienniki infrastruktury Samsunga |

Nie przeniesiono:

- `ssp_input.c`, `ssp_spi.c`, `ssp_iio_trigger.c`, `bbdpl/bcm_dbg.c`: producent ich nie kompiluje (Makefile `brcm/` i `brcm/bbdpl/`).
- `ssp_motorcallback.c`, `ssp_motor.h` i opcja `SSP_MOTOR_CALLBACK`: wolaja `getMotorCallback()` i `get_current_motor_state()` ze sterownika wibracji Samsunga. W mainline nie ma tego interfejsu (`max77693-haptic` go nie ma), wiec hub nie dostaje stanu silnika wibracji.
- `sx9330.c`: osobny sterownik czujnika zblizenia SAR, poza zakresem.
- `p_os/`, `q_os/`, `r_os/*_new_old.h`, `*_davinci.h`, `*_f62.h`: patch jest wybrany na sztywno.

Opcje ustawione w `Kbuild` (jak w defconfigu producenta, linie 5450-5523): `SENSORS_SYSFS`, `SENSORS_SSP`, `SENSORS_SSP_BBD`, `SENSORS_SSP_BEYOND`, `SENSORS_SSP_LSM6DSO`, `MAGNETIC_COMMON`, `LPS22H`, `SENSORHUB`, `MOBEAM`, `TMD4910`, `PROX_AUTOCAL_AMS`, `LIGHT_REPORT_LUX`, `LIGHT_ADDING_LUMINANCE`, `LIGHT_MAX_ATIME_2BYTE`, `LIGHT_MAX_GAIN_2BYTE`, `LIGHT_COLORID`, `IRDATA_FOR_CAMERA`, `MULTIPLE_GLASS_TYPE`, `INTERRUPT_GYRO_SENSOR`, `HIFI_BATCHING`, `THERMISTOR`, `SSP_SUPPORT_MAGNETIC_OVERFLOW`, `LIGHT_LUX_RAW`, `BCM_GPS_SPI_DRIVER` oraz `ANDROID_VERSION=110000` (TopMakefile producenta, `PLATFORM_VERSION 11.0`).
Celowo pominiete (brak odpowiednika w mainline): `MUIC_NOTIFIER` (powiadomienia o kablu), `PANEL_NOTIFY` (jasnosc i COPR panelu dla czujnika swiatla pod ekranem), `VIB_NOTIFIER`, `SEC_DEBUG`, `HAS_EARLYSUSPEND`, `BATTERY_SAMSUNG_V2`, `SSP_MOTOR_CALLBACK`.

### Co zmieniono i dlaczego

Wszystkie zmiany sa w `port.diff` (`diff -ruN orig port`), zrobione skryptami `fix1.py`..`fix7.py` oraz kilkoma poprawkami recznymi (dwa zlamane literaly po podstawieniu regex, mutex IIO, miejsce dolaczen w `bbd.h` i `bcm_gps_spi.h`, `MODULE_DEVICE_TABLE(spi, ssp_id)`). Kazde miejsce zmienione z innego powodu niz API ma komentarz `port:` w kodzie.

| Producent | Port | Powod |
|---|---|---|
| `r_os`/`q_os`/`p_os` wybierane przez `ANDROID_VERSION` i `get_patch_version(ap_type, hw_rev)` | jedna tablica `bbd_patch[]` z `r_os/bbd_patch_file_beyond.h`, `get_patch_version()` zwraca zawsze `bbd_current` | pkt (a): `androidboot.revision` nie dociera z naszego bootloadera, a hw_rev=0 dawalby `p_os/..._old.h`. `get_module_rev()` (`ssp_firmware.c`) zglasza przez to wersje zgodna z podanym patchem |
| `early_param("androidboot.revision")`, `__setup("bootmode=")` | odczyt `androidboot.revision=` z `/chosen/bootargs`, w razie braku parametr modulu `hw_rev` (domyslnie 26); `bootmode` usuniety | w module `early_param`/`__setup` sa puste (`L/include/linux/init.h:382-383`). 26 to wartosc z `measurements/2026-09-11-etap0a/cmdline.txt` tego egzemplarza. `ap_rev` wybiera tez wspolczynniki swiatla (`light_colorid.c`) i idzie do huba (`ssp_i2c.c`, `MSG2SSP` AP REV) |
| `struct wake_lock`, `wake_lock*()` | `struct wakeup_source *`, `wakeup_source_register()`, `__pm_stay_awake()`, `__pm_relax()`, `__pm_wakeup_event()`; `wake_lock_active()` jako `ssp_ws_active()` | API wakelockow Androida nie istnieje w mainline |
| `sec_device_create()` (klasa `sec` Samsunga) | `ssp_sec_device_create()` w `ssp_port.c`, wlasna klasa `sec` | zachowuje `/sys/class/sec/sensorhub`, `/sys/class/sec/gps`, `/sys/class/sec/sec_barcode_emul` |
| `sensors_core.c` jako osobny `subsys_initcall` z eksportami | te same funkcje wolane z `brcm_sensorhub_init()`, `class_create(name)`, bez eksportow, `sysfs_delete_link()` zamienione na `sysfs_remove_link()` | jeden modul ma jeden `module_init`; `sysfs_delete_link` nie jest eksportowany |
| `module_init(bcm_spi_init)`, `module_spi_driver(ssp_driver)` | `ssp_port.c`: klasa `sec`, potem `sensors_class_init()`, potem `bcm_spi_init()`. `ssp_driver` nie jest rejestrowany na magistrali (probe woluje `bbd_init()` jak u producenta) | u producenta `ssp_driver` i tak nie pasowal do zadnego wezla DT (id `ssp-spi`, wezel ma `ssp,BCM4773`) |
| `device_register(&dummy_spi.dev)` | brak rejestracji, `dummy_spi` tylko nosi drvdata SSP | statyczny `struct device` bez `release()` daje w mainline WARN przy zwolnieniu, a rejestracja do niczego nie sluzyla |
| `bbd_exit()` nigdy nie wolany | wolany z `bcm_spi_remove()`, plus `kobject_put()` dla `/sys/bbd` | modul musi sie dac zdjac bez wycieku klasy `bbd` |
| `of_get_named_gpio()` + `gpio_request()` + `gpio_*_value()` | `devm_gpiod_get[_optional]()` + `gpiod_*_raw_value()` + `gpiod_direction_output_raw()` | `of_gpio.h` nie istnieje w 7.2. Wartosci surowe, jak w legacy API, niezaleznie od flagi aktywnosci w DT |
| `gpio_export()` + `gpio_export_link(gps_dev, "GPS_PWR_EN")` | nazwana grupa atrybutow `GPS_PWR_EN` z plikiem `value` (0664) na `/sys/class/sec/gps` | ta sama sciezka `GpioNStdbyPath` z `lhd.conf`; mainline ma tylko `gpiod_export*()` i to pod `CONFIG_GPIO_SYSFS`, ktorego nasze jadro nie ma |
| `regulator_get(NULL, "vdd_mcu_1p8")` | `regulator_get_optional(dev, ...)`, blad lub brak daje `NULL` | pkt (c); LDO21M jest za ACPM, bez sterownika w porcie |
| `set_fs(KERNEL_DS)` + `vfs_read()`/`vfs_write()` | `kernel_read()`/`kernel_write()` | `set_fs` usuniete z jadra (sprawdzone: zadna usunieta linia nie stala pod `if`/`else` bez klamer) |
| `setup_timer()`, `del_timer*()` | `timer_setup()` + `timer_container_of()`, `timer_delete*()` | API timerow 7.2 |
| `struct timespec`/`timeval`, `do_gettimeofday()`, `getnstimeofday()`, `rtc_time_to_tm()`, `rtc_tm_to_time()`, `timespec_sub()` | wersje 64-bitowe | usuniete z jadra (y2038) |
| IIO: `iio_device_alloc(0)`, `.driver_module`, `currentmode`, `indio_dev->mlock`, `iio_device_id` przez `->id` | `iio_device_alloc(&spi->dev, 0)`, bez `driver_module`/`currentmode`, wlasny mutex `ssp_iio_push_lock`, `iio_device_id()` | pola prywatne od 5.x |
| VLA `u8 buf[data_len + 8]` w `ssp_push_iio_buffer()` | stala tablica 256 B z zerami i kontrola dlugosci | W=1 `-Wvla-larger-than`; zera chronia przed odczytem poza danymi |
| `spi_driver.remove` zwraca `int`, `misc_deregister()` zwraca `int` | `void` | API 7.2 |
| `bcm_spi_id[]` tylko `ssp-spi` | dodany `BCM4773` | rdzen SPI wymaga wpisu id dla compatible |
| `spu_firmware_signature_verify()` dla `/dev/bbd_urgent_patch` | zawsze `-EOPNOTSUPP` | SPU Samsunga nie istnieje; zachowanie jak przy nieudanej weryfikacji (pilny patch odrzucony) |
| `psy_do_property("battery", ..., POWER_SUPPLY_EXT_PROP_OVERHEAT_NOTIFY)` | usuniete | wlasnosc sterownika baterii Samsunga |
| `kstat_irqs_cpu()` w `bcm4773_debug_info()` | `-1` | nieeksportowane, tylko log |
| `send_hall_ic_status()` w bloku `CONFIG_PANEL_NOTIFY` | wyjete z bloku | wolane bezwarunkowo przy starcie MCU; hub dostaje ten sam komunikat co u producenta |
| sciezka `platform_data` w `ssp_probe()` | `-ENODEV` bez wezla DT | arm64 mainline jest tylko DT |
| `MODULE_DEVICE_TABLE(spi, ssp_id)` | usuniete | alias `spi:ssp-spi` ladowalby modul bez sensu |

Bledy producenta poprawione przy okazji (kazdy maly, kazdy z komentarzem `port:`):

- `bbd_rpc_lh.c` deklarowal lokalnie `bbd_sensor_write(const char *, unsigned int)` i `bcm_on_packet_received(void *, unsigned char *, size_t)`, a definicje maja odwrotne typy (`size_t`/`unsigned int`). Deklaracje usuniete, prototypy z definicji sa w `ssp_port.h`.
- `bcm_gps_mem.c`: `strlen(str_type)` w logu bledu, gdy `str_type` bywa `NULL` (wywolanie z 0); teraz drukuje `size`, o ktorym mowi komunikat.
- `ssp_bbd.c`: `IsNoRespCnt++` na zmiennej `bool` zamienione na `= true` (ten sam wynik).
- `bcm_gps_hostwake.c`: `IRQF_ONESHOTa` i napis przelamany w srodku (plik nie dal sie skompilowac).
- Po zamianie na deskryptory porownania `data->shub_en >= 0` staly sie zawsze prawdziwe; zamienione na test wskaznika (semantyka producenta: "GPIO jest").

Porzadki pod W=1 bez zmiany dzialania: 42 funkcje uzywane tylko we wlasnym pliku dostaly `static`, 17 funkcji wolanych miedzy plikami dostalo prototypy w `ssp_port.h`, formaty `printk` poprawione, trzy zmienne tylko do debugowania dostaly `__maybe_unused`.

Celowo NIE zmieniono (pkt d): `bcm_gps_spi.c:279` (`orig`: 282) nadal porownuje `ssi_mode == SSI_MODE_FULL_DUPLEX` (1 z 0x40), wiec RX idzie z bajtem 0x70, a TX z 0x58, jak na stocku.

### ABI przestrzeni uzytkownika

Zachowane nazwy i sciezki:

- `/dev/ttyBCM` (misc, wylaczny `open`, ktory wlacza IRQ host-req);
- `/dev/bbd_sensor`, `/dev/bbd_control`, `/dev/bbd_patch`, `/dev/bbd_urgent_patch` (klasa `bbd`, `bbd_shmd` jak u producenta nie jest tworzony);
- `/sys/bbd/{bbd,pl,lk_timeout,lk_enable}`;
- `/sys/class/sec/sensorhub/*` (w tym `mcu_power`), `/sys/class/sec/gps/GPS_PWR_EN/value`, `/sys/class/sec/sec_barcode_emul/*`;
- `/sys/class/sensors/<czujnik>/*` (atrybuty fabryczne) i `/sys/class/sensor_event/symlink/<wejscie>`;
- misc `/dev/ssp_sensorhub`, `/dev/batch_io`, `/dev/ssp_data_injection`;
- urzadzenia input `meta_event` i `ssp_context`;
- urzadzenia IIO o nazwach z `sensor_list.h` (m.in. `accelerometer_sensor`, `gyro_sensor`, `geomagnetic_sensor`, `pressure_sensor`, `light_sensor`, `proximity_sensor`, `meta_event`, `scontext_iio`), kanal typu `IIO_TIMESTAMP` z `repeat` jak u producenta;
- tresc `/dev/bbd_patch`: 909780 B, sha256 `dd0f3ef0a61ef22a6ebcbef3bf555e51e41efa9d4b7b94892c8a71b10e6518b9`, rowna `bloby/kernel-bbd-patch/bbd_patch_beyond_r_os.txt` + NUL. Sprawdzone dwa razy: z naglowka (`verify.py`) i z sekcji `.data` zbudowanego `.ko` (symbol `bbd_patch`, 0xde1d4 B).

Roznice wzgledem stocku:

- `GPS_PWR_EN/` ma tylko `value` (bez `direction`, `edge`, `active_low` z gpiolib sysfs). lhd uzywa tylko `value` (`lhd.conf`, `GpioNStdbyPath`).
- Mainline IIO odrzuca wlaczenie bufora przy pustej masce kanalow: `L/drivers/iio/industrialio-buffer.c:919-924` ("At least one scan element must be enabled first"). Kanal producenta jest typu `IIO_TIMESTAMP`, a ten w mainline przestawia tylko `scan_timestamp`, nie maske. Jadro producenta tej kontroli nie ma (`iio_verify_update` w `drivers/iio/industrialio-buffer.c` @7d08ec3). Wlaczenie `buffer/enable` moze wiec zwrocic `EINVAL`; do sprawdzenia na telefonie (nizej, pkt 9).

### Wlasciwosci DT czytane przez sterownik

Wezel: dziecko kontrolera SPI17, `compatible = "ssp,BCM4773"` (`bcm_gps_spi.c`, `of_match_table`). Wszystkie wlasciwosci czyta ten sam wezel (SSP dostaje `&spi->dev` z `bbd_init()`).

| Wlasciwosc w porcie | U producenta (`sources/ds/exynos9820-beyond2lte_eur_open_26.dts:93-117`) | Obowiazkowa | Czyta |
|---|---|---|---|
| `ssp-host-req-gpios` | `ssp-host-req` (gpa1-7) | tak | `bcm_spi_probe` |
| `ssp-mcu-req-gpios` | `ssp-mcu-req` (gpg4-1) | tak | `bcm_spi_probe` |
| `ssp-mcu-resp-gpios` | `ssp-mcu-resp` (gpg4-2) | tak | `bcm_spi_probe` |
| `ssp-gps-pwr-en-gpios` | `ssp-gps-pwr-en` (gpg0-2) | tak | `bcm_spi_probe` |
| `ssp-batch-wake-irq-gpios` | `ssp-batch-wake-irq` (gpa0-5) | nie | `ssp_parse_dt` |
| `ssp-shub-int-gpios` | `ssp-shub-int` (gpa4-0) | nie; bez niego `request_irq` w probe SSP zawodzi (log `[SSP_IRQ]: request_irq(...) failed`), probe idzie dalej bez znacznikow czasu HIFI_BATCHING, jak u producenta | `ssp_parse_dt` |
| `ssp-pwr-en-gpios` | `ssp-pwr-en` (brak w DT producenta) | nie | `ssp_parse_dt` |
| `ssp-vdd-mcu-1p8` (napis, np. `"vdd_mcu_1p8"`) | to samo | nie | `ssp_parse_dt`; potem `regulator_get_optional(dev, <napis>)`, czyli najpierw `<napis>-supply` w tym wezle, potem regulator o tej nazwie |
| `ssp-acc-position`, `ssp-mag-position`, `ssp-acc-type`, `ssp-mag-type`, `ssp-ap-type` (u32) | to samo | nie (domyslne 0) | `ssp_parse_dt` |
| `ssp-glass-type` (u32) | to samo | nie | `ssp_parse_dt` (`MULTIPLE_GLASS_TYPE`) |
| `ssp-mag-array` (u8 albo u32 na element) | to samo | nie | `ssp_parse_dt` |
| `ssp-thermi-up`, `ssp-thermi-sub`, `ssp-hall-threshold` (u16) | to samo | nie | `ssp_parse_dt` |
| `spi-max-frequency`, `spi-cpol`, `spi-cpha` | to samo (25 MHz, tryb 3) | tak | rdzen SPI; `ssp_probe` i tak wymusza `SPI_MODE_3` |

- GPIO: w mainline nazwy konczy przyrostek `-gpios`. Flagi ustaw na `GPIO_ACTIVE_HIGH`: sterownik czyta i pisze wartosci surowe, jak `gpio_get_value()` u producenta.
- Nieczytane, choc sa w DT producenta: `ssp-ap-rev` (weryfikacja T5), `ssp-sns-combination`. Tak samo `ssp,prox-*`: przy `PROX_AUTOCAL_AMS` i `LIGHT_COLORID` (oba wlaczone) ta galaz `ssp_parse_dt` jest wykompilowana.
- `cs-gpio` z podwezla `controller-data` producenta to wlasnosc jego kontrolera SPI; w mainline `cs-gpios` na kontrolerze (albo CS sprzetowy).
- `bcm_gps_hostwake.c` (opcjonalny): GPIO `hostwake` (DT `hostwake-gpios` albo tablica `gpiod_lookup`), urzadzenie platformowe `bcm-gps-hostwake`, bez `of_match_table` (producent tez nie mial).
- Parametr modulu `hw_rev` (0444) i `androidboot.revision=` w `/chosen/bootargs`.

### Co trzeba sprawdzic na telefonie

1. Wezel DT SPI17: instancja USI dla `spi@10970000` i jej tryb (weryfikacja pkt 10). Bez tego probe nie ruszy.
2. `modprobe kfifo_buf; insmod brcm_sensorhub.ko`, w dmesg: `[SSPBBD]: Probe OK. ssp-host-req=...`, `BBD:bbd_init(...) registered /dev/bbd_*`, `[SSP] ap-rev = 26`.
3. Uzgadnianie mcu-req/mcu-resp: brak `MCU_REQ_RESP timeout` w dmesg przy pierwszym transferze (`bcm4773_hello`). Timeout znaczy zle GPIO albo odwrocona flaga w DT.
4. IRQ host-req wyzwalany poziomem wysokim (`IRQF_TRIGGER_HIGH`) na gpa1-7 przez pinctrl Exynosa: licznik w `/proc/interrupts` rosnie tylko przy otwartym `/dev/ttyBCM`.
5. `sha256sum /dev/bbd_patch` ma dac `dd0f3ef0...18b9` (909780 B).
6. `echo 1 > /sys/class/sec/gps/GPS_PWR_EN/value` przelacza gpg0-2 (odczyt `value`, pomiar albo reakcja ukladu).
7. `mcu_power`: bez regulatora (LDO21M za ACPM) i bez `ssp-pwr-en` atrybut nic nie przelacza; sprawdzic, czy lhd to toleruje (`GpioNPowerPath`).
8. Wakeup sources `bbd_wake_lock`, `ssp_wake_lock` i inne widoczne w `/sys/class/wakeup/`, zwalniane po transferach.
9. IIO: `echo 1 > .../scan_elements/in_timestamp_en; echo 1 > .../buffer/enable`. `EINVAL` potwierdzi roznice z mainline opisana wyzej; wtedy trzeba zdecydowac o kanale nietypu `IIO_TIMESTAMP` (zmiana ABI).
10. Urzadzenia input `meta_event`, `ssp_context` i dowiazania w `/sys/class/sensor_event/symlink/`.
11. Zrzut `SSI:DEBUG=1` (`bcm_gps_spi.c`) jako wyrocznia bajtow 0x58 i 0x70 oraz ramek ACK dla pakietow RELIABLE.
12. Pliki kalibracji `/efs/FactoryApp/*` (accel, gyro, prox, baro, hw_offset, predefine, version) i `/sys/class/lcd/panel/window_type` w pmOS nie istnieja; odczyty zawioda jak na stocku bez `/efs`. Zrzuty MCU ida do `/data/log/`.
13. Suspend/resume: PM notifier `bbd.c` wola `ssp_suspend`/`ssp_resume` przez `dummy_spi`; w porcie usypianie jest zamaskowane (UFS nie wraca z s2idle), wiec test pozniej.
14. `rmmod`: nieprzetestowane. `sensors_class_exit()` producenta niszczy klasy bez usuwania urzadzen, a `ssp_shutdown()` nie jest pelnym `remove`. Do czasu testu nie zdejmowac modulu.

### Pliki pomocnicze (katalog `czujniki`)

- `orig/`: kopia zrodel producenta przed zmianami; `port.diff`: pelna roznica.
- `fix1.py`..`fix7.py`: kolejne przebiegi przerobek (kazdy konczy sie bledem, gdy wzorzec nie trafi).
- `build.sh`, `build-hw.sh`, `build.log`, `build-hw.log`: budowa w WSL w `/home/pm/brcm_port`.
- `verify.py`: zgodnosc patcha z blobem, kontrola usunietych `set_fs`, linia `ssi_mode`, lista wlasciwosci DT.
