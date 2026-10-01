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

### Powtórka 28.09.2026: moduł zbudowany od zera i załadowany na żywym telefonie

Modułu nie było ani w repo, ani na telefonie (znika po restarcie), więc zbudowałem go
ponownie. Przepis, żeby nie szukać tego drugi raz:

1. Drzewo 7.2 z repo skopiowane do WSL (`/root/k7`), `.config` z żywego telefonu
   (`zcat /proc/config.gz`, TOK_RAW), potem `make modules_prepare`.
2. `make modules` **jest konieczne**: bez `Module.symvers` modpost wywala 111
   nierozwiązanych symboli i moduł nie powstaje.
3. **Wersja musi się zgadzać co do znaku.** Samo `.scmversion` i `CONFIG_LOCALVERSION`
   nie wystarczyły, bo Kbuild trzyma wersję w `include/config/kernel.release`.
   Zadziałało dopisanie wprost: `printf '7.2.0-01001-ga9d566a524be-dirty\n' >
   include/config/kernel.release` plus `include/generated/utsrelease.h` i kasacja `*.o`.
   Bez tego `vermagic` wychodzi `7.2.0` i jądro odmawia ładowania.
4. Budowa: `make M=tools/phone/tzdev modules` z `ARCH=arm64
   CROSS_COMPILE=aarch64-linux-gnu-`. Wynik 9,2 MB (xz 2,0 MB), wysyłka przez
   `ssh ... "cat > /tmp/tg.ko.xz"` (stdin przechodzi przez filtr bajt w bajt).

Dowód z 28.09 (`insmod rc=0`, telefon `up 13 min`, nic się nie zrestartowało):

```
teegris              5148672  0
crw------- 1 root root 506, 0 /dev/tzdev
crw------- 1 root root 504, 0 /dev/tziwshmem
crw------- 1 root root 505, 0 /dev/tziwsock
141: GIC-0 500 Level tzdev_iwi_event   (55 przerwań)
142: GIC-0 501 Level tzdev_iwi_panic
SW> SECUREOS VERSION: Samsung Secure OS Release Version 3.1.0.0 built on: 2022-08-29
SW> Reset RTC to 1/1/2017 12:00:00
SW> set_fp_tzpc result : 0x7
SW> [TEEgris:SCrypto] SCrypto 2.4 is in FIPS approved mode
TZDEV> ERR tz_deploy_handler: Startuploader complete
```

`set_fp_tzpc result : 0x7` to ślad ochrony TZPC dla czytnika. W całym dmesg **nie ma
ani jednej linii o RPMB**. `tzdev_resolve_iwis_id: no teegris node, GIC SPI 468/469 ->
IRQ 141/142` to znany, obsłużony przypadek: brak węzła DT, więc numery są wpisane na
sztywno, tak jak w configu producenta. Pełny log:
`D:\S10Plus-backup\czytnik-2026-09-28\teegris-dmesg-2026-09-28.txt`.

## Zawieszenie 28.09.2026: moduł sam kładzie telefon po ~35 s

Fakt zmierzony, nie wniosek: po `insmod` telefon **wisi**, bez paniki i bez śladu
w logu. Pierwszy raz o 02:31:18 (zamarł ~02:32), drugi raz w teście kontrolnym
o 02:36:44, gdzie **nie dotknąłem niczego związanego z TEE**, tylko pingowałem:
`t+35s ping 0/3`. Objaw: jądro żyje, gadżet USB zarejestrowany, ARP `Incomplete`,
`/sys/fs/pstore/` pusty, `/proc/reset_reason` nie istnieje, a `journalctl -k -b -1`
urywa się kilka sekund po załadowaniu.

Odrzucone jako przyczyna: panika (`panic=30` dałoby restart co 30 s, a telefon wisi),
usypianie systemu (znana pułapka działa po ~27 min bezczynności, tu były 2 minuty),
oraz ścieżki klienta TEE (test kontrolny wykluczył je wprost).

**Kandydat wskazany w kodzie:** `tz_iwlog.c`, wątek `tzlog`:

```c
while (1) {
	if (!wait_event_interruptible(tz_iwlog_wq,
			atomic_xchg(&tz_iwlog_request, TZ_IWLOG_WAIT) == TZ_IWLOG_BUSY))
		tz_iwlog_read_buffers_do();
}
```

Gdy warunek jest prawdziwy, `wait_event_interruptible` zwraca 0 **nie śpiąc**, więc
wątek kręci się bez przerwy. TZLOG to opcja dodana przy porcie (dziennik świata
bezpiecznego do dmesg), czytnikowi niepotrzebna. Pozostałe miejsca czekania bez
timeoutu, które trzeba mieć na oku: `teec/shared_memory.c:101`
(`wait_for_completion(&shm->released)` czeka na odpowiedź TA) oraz
`teec/session.c:142`. `BUG_ON` w `session.c:137/202` i `shared_memory.c:100` dałyby
panikę, a nie ciszę, więc do tego objawu nie pasują.

**Wariant do przetestowania:** `Kbuild` bez `-DCONFIG_TZLOG=1`,
`-DCONFIG_TZLOG_PG_CNT=1` i bez obiektu `tz_iwlog.o` (`tz_iwlog.h` daje wtedy
zaślepki). Buduje się, `vermagic` bez zmian, rozmiar 9 011 056 B.
NIE UTRWALONE: czy to usuwa zawieszenie. Sprawdzać po każdej zmianie.

### Co wyszło z trzech kolejnych testów (28.09)

| Przebieg | Wynik |
|---|---|
| moduł z TZLOG, z tzarem | świat bezpieczny wstaje (`Startuploader complete`), po ~35 s system pada |
| moduł bez TZLOG, z tzarem | pada tak samo, po 35 s → **TZLOG nie jest przyczyną** |
| moduł bez tzara (`wgraj_tzar=0`) | **żyje 6 minut**, 101 zdarzeń IWI, zero panik, `/dev/tz*` są; load ~10, bo wątki `tz_worker_handler`, `tz_iwsock_kthread`, `tz_ree_time_kthread` czekają na gniazdo, którego nikt nie obsługuje |
| moduł z „cichą paniką" (panic→log), tzar | żył 5 minut, ale w dmesg **brak śladu wgrania tzara** |

Ten ostatni przebieg nie był tym, czym się wydawał: skoro nie ma `Startuploader
complete`, świat bezpieczny prawdopodobnie w ogóle nie wystartował, więc telefon
przeżył z tego samego powodu co w wariancie bez tzara. Licznik `tzdev_iwi_panic`
miał 0 zdarzeń, czyli **mechanizmem nie jest panika SWd**, wbrew pierwszemu
wrażeniu z `dump_kernel_panic_bh`.

**Przyczyna niepełnego obrazu, znaleziona w kodzie:** `tzdev_deploy_tzar()` nie
wgrywa tzara, tylko odpala wątek i wraca:

```c
t = kthread_run(tz_deploy_handler, NULL, "tzdev_deploy_tzar");
```

Wynik wgrania **nie jest nigdzie sprawdzany**, a cała diagnostyka idzie do tego
wątku. Dlatego raz widać `Startuploader complete`, a raz nic. Do tego `tzdev.c`
po nieudanym wgraniu idzie prosto do `out:` i nie czyta dziennika rozruchu SWd.

Wniosek dla kolejnych prób: najpierw trzeba mieć **pewny i obserwowalny** start
świata bezpiecznego. Zbudowany wariant robi `tz_deploy_handler(NULL)` synchronicznie
w wątku init, loguje wynik i zaraz potem czyta `tz_iw_boot_log_read()`.
Dopiero na takiej podstawie ma sens szukanie, czego TEEgris potrzebuje po stronie
AP (patrz plan, etap 2), bo to tam leży prawdziwa przeszkoda.

### Przebieg rozstrzygający (28.09, moduł `teegris-sync`): panika SWd po dokładnie 30 s

Wariant z synchronicznym wgraniem tzara dał pełny, uporządkowany obraz. Log leci
wtedy po kolei (`sync4-strumien.txt`):

```
631.643  TZDEV> wgrywam tzar synchronicznie (diagnostyka)
631.643  [debug] tzar size = 5044890, old_tzar size = 5044890
631.707  [debug] Startuploader complete
631.707  TZDEV> tz_deploy_handler zwrocil 0
631.707  TZDEV> tzar wgrany, czytam dziennik rozruchu SWd
631.707  SW> RTC time: 12:22:53  1. 1.2017
631.707  SW> set_fp_tzpc result : 0x7
631.707  SW> s_hash_vaddr->magic_string : TIMA 3.0
631.707  SW> s_hash_vaddr->warranty_string : warranty violation
631.707  SW> CSMC: bl_secure_info.warranty_bit (1)
631.708  SW> CSMC: rot_secure_info.boot_patch_level (94a) / vendor_patch_level (94a)
661.661  [ree_time] ERR : failed to fetch request, err = -19
661.662  TZDEV> IWI_PANIC raised by SWd - NIE panikuje (tryb diagnostyczny)
```

Cztery fakty, wszystkie zmierzone:

1. **Tzar wgrywa się poprawnie** i to widać, bo wariant robi to synchronicznie
   i loguje wynik. Wcześniejsze „braki śladu" brały się z `kthread_run`
   w `tzdev_deploy_tzar()` i z niezerowego `pr_info` w `tzdev_print(0, ...)`.
2. **Świat bezpieczny panikuje sam, dokładnie 30 s po wgraniu tzara.** Nie jest to
   nasz moduł ani brak przerwania: licznik `tzdev_iwi_panic` to potwierdza, a po
   podmianie `panic()` na log **AP żyje dalej** (po 661 nadal lecą linie z czujników).
3. **Świat bezpieczny sam się do nas łączy** po gniazdo `ree_time_socket` (wątek
   `tz_ree_time.c` je obsługuje), ale dostaje `-ENODEV`, bo stan `tz_iwsock` nie
   osiągnął `READY`. Czyli kanał jest, brakuje uzgodnienia stanu.
4. **TIMA 3.0 raportuje `warranty violation`**, `warranty_bit (1)`, a vPCR2..vPCR8
   są po `ffffffff`. To pomiar integralności zrobiony po wgraniu tzara.

**Wniosek:** na tym telefonie łańcuch rozruchu nie jest firmowy (U-Boot, własne
jądro, `vbmeta` z `--disable-verification`), więc TEEgris po starcie tzarów widzi
naruszenie integralności i po 30 s sam kończy pracę. Ścieżka „świat bezpieczny
pod naszym jądrem" jest tym zablokowana i nie da się tego obejść w naszym module:
to decyzja świata bezpiecznego, nie brakujący krok po stronie Linuksa.

Co pozostaje nieustalone: czy 30 s to watchdog TEEgris oczekujący konkretnego
uzgodnienia z warstwą AP (wtedy trzeba by odtworzyć ten handshake), czy reakcja
TIMA na przerwany łańcuch zaufania (wtedy droga jest zamknięta bez przywrócenia
firmowego rozruchu). Rozstrzygnięcie wymagałoby logu TEEgris z wnętrza świata
bezpiecznego, którego nie mamy.

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

## Kopia danych czytnika (28.09.2026)

`D:\S10Plus-backup\czytnik-2026-09-28\` zawiera `dane-czytnika.tar.gz` (1 498 338 B,
SHA256 `7357ccd60bebccd9431e3e99e01a61def09236696ef7f74fd729cdd259bd9795`), rozpakowane
drzewo `run/media/user/...` oraz `SHA256SUMS` z 25 pozycjami. W środku `efs/tee/srt`
(18 obiektow magazynu zaufanego, w tym TA `GATEKEEPER` i `VLTKPR`) i
`sec_efs/biometrics/meta` (cala kalibracja czytnika).

Przesyl: klucz SSH na telefonie ma wymuszone `command="tok-ssh"`, ale ten wrapper
przepuszcza dane bajt w bajt, gdy polecenie ma przedrostek `TOK_RAW=1`. Dziala wiec
wprost i szybko:

```
ssh -i <klucz> user@192.168.0.109 "TOK_RAW=1 cat /tmp/fp-backup/dane-czytnika.tar.gz" > plik
```

**`/data/vendor/misc/qti_fp` przepadlo.** Partycja `userdata` (`/dev/sda31`, 119 GB,
`PARTLABEL="userdata"`) nie ma systemu plikow (offset 1024 pusty, mount konczy sie
`bad superblock`), a `/data` nie istnieje w dzialajacym systemie. Szablonow palcow
Androida nie ma wiec ani na telefonie, ani w kopiach. To jedyna nieodwracalna strata
w danych czytnika.

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
