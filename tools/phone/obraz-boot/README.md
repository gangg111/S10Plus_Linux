### Obraz boot Droidiana bez debugu bring-upu

Jadro Droidiana (galaz `droidian` w `~/droidian/kernel/samsung/beyond2lte`, WSL) bez sondy
`s10probe`, znacznikow na obrazie S-Boota i logu na partycje cache (commit fc5c3b7ab) oraz
initramfs bez skryptu `zz-early-debug` (3 wibracje, szum na fb0, telnet roota bez hasla;
commit 7179e925d).

1. `jadro-buduj.sh` (WSL): przyrostowo na kopii `~/droidian/pidfd2`, czyli wyjsciu budowy jadra
   z partycji boot, w kontenerze build-essential z clangiem Androida 17.0-r487747c.
   Nazwa wydania podana wprost (`KERNELRELEASE=4.14.356-samsung-beyond2lte`), bez niej
   wychodzi `openela-rc1`.
2. `bez-early-debug.py <obraz> <wyjscie>`: initramfs obrazu bez skryptu, jadro bit w bit.
3. `podmien-jadro.py <obraz> <Image> <wyjscie>`: nowe jadro w obrazie, ramdysk i naglowek bez zmian.

Oba skrypty Pythona przeliczaja id naglowka v1 tak jak mkbootimg (SHA1 z jadra, ramdysku,
second, recovery_dtbo i dtb, kazdy z dlugoscia) i sprawdzaja wzor na obrazie wejsciowym.

Dowod: `System.map` nowego jadra ma o 11 symboli mniej, wszystkie `s10*`; obraz
`D:\S10Plus-droidian\boot-bez-debugu-2026-10-01.img` (sha256 `2d9f9f8c...`). Po wgraniu
`grep -c s10probe_hit /proc/kallsyms` daje 0.

Drugie wydanie, 02.10.2026: to samo plus galaz `droidian` 15ac51bc9 (`fimc-is2`: zaslepki
`VIDIOC_ENUM_FMT` wezlow kamery zwracaly 0 dla kazdego indeksu, wiec FFmpeg `v4l2m2m` i kazdy
program wyliczajacy kamery krecil sie w nieskonczonosc; teraz `-EINVAL`). Obraz
`D:\S10Plus-droidian\boot-bez-debugu-fimc-2026-10-02.img` (sha256 `35bb8067...`), na telefonie
`~/boot-bez-debugu-fimc.img`. Po wgraniu sprawdzic aparat (HAL producenta korzysta z tych wezlow)
oraz `python3 v4l2-sonda.py`: wezly `exynos-fimc-is-*` bez formatow zamiast `64+`.

Trzecie wydanie, 02.10.2026 (zastepuje drugie): do initramfs doszly `lib/firmware/calliope_sram.bin`
i `calliope_sram_2.bin` z `/vendor/firmware` (`firmware-do-initramfs.py`). ABOX prosi o nie w 16,5 s,
zanim `/vendor` jest zamontowany (18,3 s), a pod Droidianem nikt nie obsluguje zapasowego user
helpera; bez nich kazde wybudzenie ABOX wisi i dzwiek przez HAL producenta nie ruszy. Obraz
`D:\S10Plus-droidian\boot-fimc-abox-2026-10-02.img` (sha256 `ba2cba0d...`), na telefonie
`~/boot-fimc-abox.img`. Po wgraniu: w dmesg brak `firmware load for calliope_sram.bin failed`,
`pactl list sources` i nagranie z `source.primary-in` z probkami roznymi od zera.

Czwarte wydanie, 02.10.2026 (zastepuje trzecie, DO WGRANIA): jadro z galezi `droidian` aa372ecc9
(dekoder MFC przyjmuje bufory MMAP i zglasza `V4L2_CAP_VIDEO_M2M_MPLANE`, wiec dzialac moga
FFmpeg `v4l2m2m` i GStreamer `v4l2h264dec`), initramfs jak w trzecim. Obraz
`D:\S10Plus-droidian\boot-fimc-abox-mfc-2026-10-02.img` (sha256 `5915b04e...`), na telefonie
`~/boot-fimc-abox-mfc.img`. Po restarcie `sh ~/test-po-wgraniu.sh` sprawdza jadro, firmware ABOX,
dzwiek, wezly kamer i dekoder MFC; aparat sprawdza czlowiek.

Piate wydanie, 03.10.2026 (zastepuje czwarte; wgrane, firmware dziala, ale HAL sie zakleszczal): firmware ABOX wbudowany w jadro
(`CONFIG_EXTRA_FIRMWARE` z czterema plikami `calliope_*` z `/vendor/firmware`, 2,58 MB,
`firmware-w-jadrze.sh`). Trzecie i czwarte wydanie nie dzialaly: to jadro nie rozpakowuje
initramfs (Droidian robi to w przestrzeni uzytkownika), a ABOX laduje firmware bez zapasowego
user helpera (w logu robi to tylko VTS), wiec ani pliki w initramfs, ani obsluga
`/sys/class/firmware` przez `audio-hidl-compat.sh` nie mialy szans. Initramfs wziety z drugiego
wydania (bez zbednych kopii firmware), jadro z galezi `droidian` jak w czwartym. Obraz
`D:\S10Plus-droidian\boot-abox-wbudowany-2026-10-03.img` (sha256 `605bf829...`), na telefonie
`~/boot-abox-wbudowany.img`, zajete 57 451 220 z 57 671 680 B. Po wgraniu `audio-hidl-compat`
w dzienniku melduje `built into the kernel: calliope_sram.bin calliope_dram.bin`, a
`sh ~/test-po-wgraniu.sh` ma pokazac `audio.hidl_compat` w pulseaudio i probki mikrofonu rozne od zera.

Szoste wydanie, 03.10.2026 (zastepuje piate, WGRANE, dzwiek dziala): jak piate plus galaz `droidian`
244bf3095 (`0001-ASoC-abox-register-extra-firmware-controls-from-work.patch`). Pierwsze wybudzenie
ABOX po resecie rejestrowalo kontrolki dodatkowego firmware (`snd_ctl_add`, blokada `controls_rwsem`
do zapisu) wprost w `abox_runtime_resume`; gdy to wybudzenie wywolal odczyt kontrolki przez HAL
(`abox_ctl_get` trzyma ta sama blokade do odczytu i czeka w `pm_runtime_get_sync`), oba watki czekaly
na siebie: HAL w stanie D, pulseaudio zawieszony. Wybudzenie z `audio-hidl-compat.sh` przed startem
HAL-u (adaptacja 12) wygrywalo wyscig tylko czasem (1 z 2 rozruchow), teraz rejestracje robi
`register_component_work`. Obraz `D:\S10Plus-droidian\boot-abox-bez-zakleszczenia-2026-10-03.img`
(sha256 `78598177...`), na telefonie `~/boot-abox-bez-zakleszczenia.img`. Dowod z dwoch kolejnych
rozruchow: `calliope_version MUL0`, HAL w stanie `Sl`, mikrofon 349 440 z 364 800 probek niezerowych
(RMS 15), przy odtwarzaniu dzialaja `pcmC0D0p`, `pcmC0D7p` i VDMA `pcmC1D0p`. Glosnik sprawdza ucho.

Siodme wydanie, 03.10.2026 (zastepuje szoste, WGRANE): jak szoste plus dekoder MFC dzialajacy dla
FFmpeg, GStreamera i mpv. Latki galezi `droidian` od fimc-is do konca serii MFC sa w `latki-mfc/`
(0001-0009). Kazda naprawia blad zmierzony na telefonie: panika przy pierwszym QBUF (vb2-dma-sg nie
ustawial `dma_address` buforom MMAP), `mmap` bufora wyjsciowego trafial w kolejke wejsciowa
(przesuniecie 2^38 w 32-bitowym `mem_offset`), `poll` nie zglaszal gotowych klatek przy masce
POLLIN|POLLOUT, brak konca strumienia (`DECODER_CMD STOP`, `V4L2_BUF_FLAG_LAST`), za malo buforow
i zerowy rozmiar DPB bez `S_FMT` (GStreamer), oraz `debug_mode` z DT producenta, przez ktory kazdy
blad MFC (osiagalny z przestrzeni uzytkownika) restartowal telefon (teraz tylko z
`exynos_mfc.panic_on_error=1`). Parametry debugowania w `/sys/module/exynos_mfc/parameters/`
(debugfs w tym jadrze nie ma). Obraz `D:\S10Plus-droidian\boot-mfc-2026-10-03.img` (sha256
`49d42aa6...`), na telefonie `~/boot-mfc.img`. Dowod (20 s 1080p, 600 klatek): FFmpeg H.264 84 kl/s
przy 0,66 s CPU (programowo 1,3 s czasu, ale 6 s CPU), HEVC 115 kl/s przy 0,57 s CPU (programowo
10,9 s CPU), klatka sprzetowa identyczna z programowa (PSNR inf), GStreamer `v4l2h264dec` kod 0
w 6,8 s, mpv `--hwdec=v4l2m2m-copy` uzywa dekodera sprzetowego, zero bledow MFC w dmesg.
