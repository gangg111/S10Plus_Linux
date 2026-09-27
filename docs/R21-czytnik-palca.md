# R21: czytnik linii papilarnych (QBT2000)

Cel (27.09.2026): czytnik ma działać jak w Androidzie, a w Linuksie ekran odblokowuje
odcisk zamiast PIN-u, z możliwością dodania wielu palców.

## Jak to działa w Androidzie (sprawdzone na telefonie i w źródłach producenta)

- Magistrala SPI czujnika ma w DT `secure-mode`: należy do TEEgris (Trusted OS Samsunga
  w TrustZone), nie do Linuksa. Obraz ultradźwiękowy zbiera i porównuje zaufana
  aplikacja w TEEgris (`/vendor/tee/00000000-0000-0000-0000-46494e474502`, ASCII „FINGE”).
  Linux dostaje tylko wynik. Otwartego algorytmu dla tego czujnika nie ma, więc „1:1”
  oznacza uruchomienie stosu producenta.
- Po stronie jądra Androida: `tzdev` (sterownik TEEgris, `CONFIG_TZDEV=y`, SMC do
  Trusted OS 0, `startup.tzar` wgrywany przez jądro) i `qbt2000` (linie IPC/WUHB,
  `/dev/qbt2000_ipc`, `/dev/qbt2000_fd`, `/dev/qbtspi`).
- W przestrzeni użytkownika (partycja vendor): demony TEEgris `tzdaemon`,
  `tz_message_receiver`, `tzts_daemon` (`teegris_v3.rc`), biblioteki `libbauthtzcommon.so`,
  `libbauthserver.so`, `fingerprint.default.so` i usługa HIDL
  `vendor.samsung.hardware.biometrics.fingerprint@3.0-service` (użytkownik system,
  szablony w `/data/vendor/biometrics` i `/efs/biometrics`).
- Ubuntu Touch na S10 Exynos (Halium, jądro producenta) miał czytnik działający, czyli
  stos producenta da się uruchomić poza Androidem.

## Bramka: TEEgris pod naszym jądrem

Sonda `tz_sonda` (jedno SMC `0xB200000D`, TZDEV_SMC_CHECK_VERSION) zwraca `-22`
(-EINVAL, odpowiedź w stylu errno, czyli od TEEgris; bez Trusted OS monitor EL3 zwraca
SMCCC „not supported” = -1). Oryginalny tzdev traktuje -EINVAL jako niekrytyczne.
**TEEgris żyje pod jądrem 7.2.**

## Etap 1 zrobiony: tzdev na 7.2 (`tools/phone/tzdev`, moduł `teegris.ko`)

Źródła `drivers/misc/tzdev` producenta, opcje jak w defconfigu beyond2lte plus TZLOG.
`startup.tzar` wycięty z jądra Androida 12 tego telefonu (`boot.img` z kopii,
G975FXXSGHWC1), bit w bit równy temu z drzewa exynos9820. Zmiany portu: API 7.2
(`get_user_pages_remote`, `sha1.h`, `class_create`, `mmap_read_lock`, `timespec64`,
`vm_flags_mod`, `sched_set_fifo`), blob w `.rodata` zamiast `.init.data`, trzy initcalle
spięte w `teegris_modul.c`, `panic()` przy starcie zamieniony na błąd, przerwania bez
węzła DT mapowane na GIC SPI 468/469 (hwirq 500/501, jak w configu producenta).

Dowód (dmesg po `insmod`): `SW> startup_loader main() ... waiting for incoming
connection`, `Startuploader complete`, `SW> [TEEgris:SCrypto] SCrypto 2.4 is in FIPS
approved mode`; `tzdev_iwi_event` 77 przerwań. Są `/dev/tzdev` i `/dev/tziwsock`.

## Plan

1. **tzdev** jako moduł spoza drzewa dla 7.2 (port z jądra 4.14 producenta), wgranie
   `startup.tzar`, `/dev/tzdev` i gniazda iwsock. Dowód: stan SWd „up”, dziennik
   rozruchu TEEgris (`TZDEV_SMC_BOOT_LOG_READ`).
2. **Środowisko Androida** w kontenerze z partycji system i vendor telefonu (linker64,
   bionic, servicemanager, hwservicemanager, vndservicemanager; binder z mainline przez
   binderfs). Dowód: `tzdaemon` łączy się z TEEgris.
3. **qbt2000** po stronie AP (przerwania IPC/WUHB). Dowód: zdarzenie przy dotknięciu.
4. **Usługa HAL** i klient testowy: lista palców, dodanie (wymaga tokenu z gatekeepera,
   też w TEEgris), dopasowanie.
5. **Most do Linuksa:** sterownik libfprint/fprintd rozmawiający z HAL, PAM
   `pam_fprintd`, ekran blokady i dodawanie wielu palców w ustawieniach Plasmy.

## Gdzie czytnik trzyma dane: RPMB nie jest potrzebne (pomiar 28.09.2026)

Sprawdzone na żywo przez SSH, wyłącznie odczyt (nic nie ładowane, nic nie montowane,
nic nie uruchamiane). Wynik zmienia ocenę ryzyka z R21:

- `tzdaemon` trzyma magazyn zaufany w **`/efs/tee/srt`**: 18 zaszyfrowanych obiektow
  (`<uuid>/<id>/data_chunk` + `obj_info`), razem 304 KB. To zwykly ext4 na `sda3`,
  wiec jest w kopiach.
- Obiekty w `srt` sa **zaszyfrowane kluczem z TEE**, wiec pliki sa bezuzyteczne bez
  TEEgris. Ale struktura katalogow tego magazynu sama w sobie nie wymaga RPMB.
- Kalibracja czytnika: **`sec_efs/biometrics/meta`**, `sensor_id` = `S940040996FG2G1F8C15227E3`
  (25 B, 26.02.2019), `bg_estimation/` i `bg_estimation0/bg_basis.dat` (368024 B),
  `cbge_0.dat` (368096 B), `cbge_8.dat` (368024 B), `bg_metadata.dat` (72 B).
  To dane fabryczne z pierwszej konfiguracji, w `sec_efs`, ktora jest w kopii.
- Szablony palcow (po stronie Androida) leza w **`/data/vendor/misc/qti_fp/database/finger_id.dat`**,
  `ffd_persistant_data`, `image_quality/templates`, `wakeup/templates`. Partycja danych
  **nie jest** w zadnej kopii, wiec to jedyny element, ktorego nie da sie odtworzyc.
- `CONFIG_RPMB is not set` w naszym 7.2, nie ma `/dev/mmcblk0rpmb` ani `/dev/rpmb`.
  W jadrze 4.14 producenta sa symbole `mmc_rpmb_ioctl` i `mmc_raw_rpmb_size_mult_show`,
  ale to warstwa AP, nie secure world.
- Log S-Boot z 17.09 (`measurements/2026-09-17-etap0/sboot-log-z-last_kmsg.txt`) pokazuje,
  ze **licznik zapisu RPMB wynosi `0x1b1c` = 6940**, blok magiczny zapisany i zgodny,
  `[EFUSE] warranty bit is already set`, `WARRANTY = 0x1`, `ENABLE_ANTIRBK = 0x1`.
  Te zapisy wykonuje S-Boot (`RPMB: Magic Block Write: success`), nie TEEgris i nie my.
  W naszym U-Boot nie ma ani jednego patcha dotykajacego RPMB (sprawdzone w `patches-uboot`).
- TA `FINGE` po wypakowaniu z vendor: w `.text` **zero** wystapien `rpmb`, natomiast
  sciezki `/data/vendor/misc/qti_fp/...` i klucze konfiguracji QFP (`BARE_SENSOR_SNR`,
  `CBGE_IGNORE_SENSOR_ID_DIFF`, `ENROLL_FINGER_LIFT_*`).

Wniosek: **doprowadzenie sterownika nie wymaga zmian w RPMB.** Nieodwracalny jest tylko
pierwszy zapis szablonu palca w `/data/vendor/misc/qti_fp` (partycja bez kopii), a nie
obszar chroniony. RPMB dotyka S-Boot przy starcie Androida, czego nasz lancuch nie robi.

## Gdzie lezy sterownik (zrodla)

- Wezel DT (zrzut producenta, `sources/ds/exynos9820-beyond2lte_eur_open_26.dts`):
  `qbt2000 { compatible = "qcom,qbt2000"; }`, do tego `qcom,ipc-gpio`, `qcom,wuhb-gpio`,
  `qcom,ldo-gpio` i pinctrl na `spi1_bus`; linia 7047 to `secure-mode`.
- Implementacja jest w drzewie jadra Samsunga (GPL) i wkompilowana na stale, nie jako modul:
  symbole `qbt2000_probe`, `qbt2000_dev_register`, `qbt2000_read_device_tree`,
  `qbt2000_sec_spi_prepare`, `qbt2000_ipc_irq_handler` sa w `Image` z `boot.img`
  (kopia z 17.09). Katalogu zrodel tego sterownika nie ma ani w repo, ani na telefonie,
  wiec nazwy pliku nie podaje bez drzewa producenta.
- Warstwa TEE: `tools/phone/tzdev` (port) + `startup.tzar` wyciagniety z `boot.img`.
- Algorytm dopasowania: podpisany TA `vendor/tee/00000000-0000-0000-0000-46494e474502`
  („FINGE”). Otwartego odpowiednika nie ma i nie bedzie.

## Ryzyka

- TA może wymagać tokenu uwierzytelnienia (HAT) od gatekeepera przy dodawaniu palca.
- TEEgris może sprawdzać wersję lub integralność jądra (na razie `-EINVAL` przy
  sprawdzaniu wersji, co oryginalny sterownik przepuszcza).
- `tzdev` z 4.14 korzysta z API jądra, które od tego czasu się zmieniły (pamięć CMA,
  kthready, ION).
