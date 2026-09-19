### Sesja z UART: uporzadkowana procedura zdejmowania pozycji HW-BLOCKED

`docs/HW-BLOCKED.md` mowi, **co** trzeba zmierzyc. Ten plik mowi, **w jakiej kolejnosci**
i **czym**, zeby jedna sesja przy telefonie zamknela ich jak najwiecej.

Zasada nadrzedna zostaje bez zmian: pozycja wypada z HW-BLOCKED dopiero, gdy jest odczyt
z urzadzenia. Kazdy potwierdzony pomiar wchodzi potem do `scripts/verify.sh` jako golden
file, zeby nikt go pozniej nie cofnal.

#### Czego nie robic

Nie zaczynac od naszej serii. Na stockowym Androidzie (etap 0a) zdejmuja sie dwie
pozycje, HW-31 i HW-20, a **piec** kolejnych na **istniejacym, dzialajacym porcie pmOS**
(kernel 7.2.0, boot przez U-Boot/EFI), gdzie jest juz shell i `dmesg`. Te piec to
HW-23 z etapu 1 oraz HW-11, HW-07, HW-08 i HW-09 z etapu 2, czyli dokladnie te,
ktore wymieniaja etapy nizej: liczba jest suma tamtych naglowkow, nie osobnym
twierdzeniem. Wpuszczanie wlasnego DECON-a w system, w ktorym nie wiadomo jeszcze, czy
domena zasilania w ogole wstaje, zamienia jeden nieznany parametr w piec.

#### Etap 0a: mapa pamieci RAM, jeszcze na stockowym Androidzie

Ten odczyt nie potrzebuje ani UART-a, ani naszego jadra, a bez niego nie bylo czego
uruchamiac: plik plyty nie mial wezla `memory@`, bo mapy RAM-u tego egzemplarza nie ma
w zadnym dostepnym zrodle (HW-31), a bootloader by jej nie dolozyl, bo uniLoader trzyma DTB
wkompilowany we wlasny obraz i zmienia w nim tylko adresy initrd.

**Zrobione 11 wrzesnia 2026.** Przebieg i material: `measurements/2026-09-11-etap0a/`.

Planowane polecenia byly takie:

```sh
adb shell su -c 'cat /proc/iomem' | grep -i "System RAM"
adb shell su -c 'dmesg | grep -i "Memory:"'
```

Pierwsze dalo granice bankow, drugie nie dalo nic: bufor `dmesg` na tym telefonie zdazyl
sie przewinac (najstarszy wpis z 38 sekundy pracy), wiec linii `Memory:` z rozruchu juz
tam nie ma. Kontrola sumy wyszla z `/proc/meminfo`.

Mapa wziela sie jednak ze zrodla pewniejszego niz oba te polecenia. Stockowe jadro wystawia
**caly blob drzewa urzadzen**, ktory dostalo od bootloadera:

```sh
adb shell "su -c 'base64 /sys/firmware/fdt'" | tr -d '\r\n' > fdt.b64
# na PC: dekodowanie i kontrola, ze totalsize z naglowka rowna sie rozmiarowi pliku
dtc -I dtb -O dts -o stock-fdt.dts stock-fdt.dtb
```

Nie `adb exec-out`: on psuje dane binarne (przy blobie 371894 B wyszlo 372365 B, zamiana
koncow linii). Blob niesie wprost wezly `memory@`, cale `reserved-memory` i kazdy wezel
producenta dla tej plyty, wiec zamknal HW-31 i HW-34 naraz. Banki przepisane do pliku plyty
przez `scripts/gen-dts-beyond2lte.py`, dziury zachowane.

**HW-19 zamkniete przy okazji.** `/proc/cmdline` niesie `s3cfb.bootloaderfb=0xca000000`,
czyli adres bufora podany przez samego bootloadera, o ktory chodzilo w tej pozycji. Nie
trzeba czekac na etap 1 ani na wzorzec testowy.

**Ostrzezenie kupione drogo: debugfs producenta nie jest kanalem tylko do odczytu.**
Proba odczytu `/sys/kernel/debug/vclk/VCLK_BLK_DPU/*` wywrocila jadro i **zresetowala
telefon** (Oops w `vclk_table_dump` przez `ra_get_div_mux`, slad w `/sys/fs/pstore/dmesg-ramoops-0`
po restarcie). Handler `read` tych wezlow chodzi po tablicach i rejestrach bloku. Nie wracac
do `vclk/*`, `decon/dump0`, `decon/event0`, `exynos-ss/*`, `exynos-rgt/*`. Bezpieczne sa
`/proc/*`, `/sys/firmware/fdt`, `/sys/firmware/devicetree`, pojedyncze atrybuty `/sys/class/*`
i `/sys/fs/pstore/*`.

**HW-20, kolejnosc narastania szyn panelu.** Ta sama sesja, ten sam system. Role szyn sa
juz ustalone i to bez sprzetu: instrukcja serwisowa podaje VDD_DDI_3P0, VDD_DDI_1P8
i VDD_DDR_1P6 z punktami pomiarowymi, wiec vci, vdd3 i vddr sa przypisane (szczegoly
w `docs/HW-BLOCKED.md`, HW-20). Otwarte zostaly wylacznie **odstepy czasowe** miedzy
narastaniem szyn. Sonda na pinach zlacza panelu w dzialajacym stockowym Androidzie,
zapisac przebieg. Zla kolejnosc bywa przy panelach OLED przyczyna uszkodzenia, wiec to
pomiar do zrobienia **przed** pierwsza proba zapalenia ekranu, czyli przed etapem 4,
a nie w jego trakcie.

**Zdjelo z listy:** HW-31, HW-34 i HW-19. **HW-20 zostaje otwarte**, bo odstepow czasowych
miedzy szynami nie da sie odczytac przez adb; to pomiar sonda. Zapis sesji:
`docs/S1-sesja-sprzetowa.md`.

#### Etap 0-: czym zbudowac i jak to w ogole dojedzie do telefonu

Dwie rzeczy, ktore trzeba miec zrobione **przed** wyjazdem do telefonu, bo w trakcie
sesji nie ma na nie czasu, a bez nich nie ma czego uruchamiac.

**Konfiguracja jadra.** Seria nie dodaje wpisu w `arch/arm64/configs` i to jest
swiadome: jeden telefon nie jest powodem do dokladania plyty do defconfiga arm64.
Skutek jest jednak taki, ze wszystkie trzy nowe symbole tej serii sa domyslnie `n`,
a defconfig nie ma tez `REGULATOR_S2DOS05`, `PINCTRL_EXYNOS` ani `EXYNOS_PM_DOMAINS`.
Jadro zbudowane z samego defconfiga kompiluje sie bez uwagi i nie zapala ekranu.
Fragment do scalenia lezy w `scripts/exynos9820.config`:

```sh
make ARCH=arm64 defconfig
scripts/kconfig/merge_config.sh -m .config <repo>/scripts/exynos9820.config
make ARCH=arm64 olddefconfig
grep -E "S2DOS05|9820|S6E3HA9" .config
```

Ostatnia linia jest sprawdzeniem: kazdy z tych symboli ma byc `=y`, nie ma go brakowac.
Bramka `scripts/check-kconfig.sh` robi to samo automatycznie i na PC jest zielona.
Fragment zostawia swiadomie wylaczone `EXYNOS_IOMMU` (HW-35) i `DRM_SIMPLEDRM` (HW-36);
oba maja zostac wlaczone dopiero jako osobny krok z osobnym pomiarem.

**Droga drzewa urzadzen do jadra.** Wczesniejsza wersja tego akapitu stawiala tu warunek
konieczny, ktorego nie ma: twierdzila, ze bez przebudowy uniLoadera nie da sie podmienic DTB.
Dla uniLoadera to prawda, ale **port, na ktorym stoja etapy 1 i 2, nie startuje przez
uniLoader**. Startuje przez EFI: pakiet urzadzenia zalezy od `systemd-boot`
(`sources/pmaports/device/testing/device-samsung-exynos9820/APKBUILD:10-15`), a DT tego portu
zyje w forku U-Boota (`docs/R4-existing-ports.md:43`, zrodlo przypiete w `SOURCES.md`).

W tym lancuchu **jadro samo umie zaladowac wskazany DTB** i nie trzeba do tego ruszac loadera:

1. Pakiet jadra portu instaluje drzewa do `/boot/dtbs`
   (`sources/pmaports/device/testing/linux-postmarketos-exynos9820/APKBUILD:58-64`,
   `dtbs_install` z `INSTALL_DTBS_PATH`), wiec nasz plik plyty trafia tam sam, gdy seria
   jest w drzewie.
2. Konfiguracja tego portu ma `CONFIG_EFI_ARMSTUB_DTB_LOADER=y`
   (`config-postmarketos-exynos9820.aarch64:1713`). Ta opcja dodaje obsluge parametru
   `dtb=` w linii polecen: stub EFI wczytuje wskazany plik z tego samego systemu plikow,
   z ktorego wczytano jadro (`drivers/firmware/efi/libstub/file.c:185-188`), zamieniajac
   po drodze ukosniki na odwrotne (`:50-51`), wiec `dtb=/dtbs/exynos/...` jest poprawne.
3. Podany w ten sposob DTB **wygrywa** z tym, co daje firmware, i stub sam mowi w logu,
   ktorego uzyl: `Using DTB from command line` albo, gdy parametru nie bylo,
   `Using DTB from configuration table` (`drivers/firmware/efi/libstub/fdt.c:261-267`).
   Te jedna linia rozstrzyga na miejscu, czy nasze drzewo doszlo.

**Jeden warunek, ktory trzeba sprawdzic na urzadzeniu.** Stub honoruje `dtb=` tylko wtedy,
gdy secure boot jest zgloszony jako wylaczony; przy stanie nieustalonym zaklada wlaczony
i **ignoruje** parametr, wypisujac `Ignoring DTB from command line.`
(`drivers/firmware/efi/libstub/fdt.c:244-253`). Brak zmiennej `SecureBoot` liczy sie jako
wylaczony (`include/linux/efi.h:1128-1131`, `EFI_NOT_FOUND` zwraca `mode_disabled`), a U-Boot
bez `CONFIG_EFI_SECURE_BOOT` tej zmiennej nie wystawia. Spodziewamy sie wiec, ze zadziala,
ale to jest przewidywanie, nie pomiar: **log startowy rozstrzyga w jednej linii**.

**Jak sprawdzic, ktore drzewo dostalo jadro.** Po boocie `cat /sys/firmware/devicetree/base/model`
ma zwrocic `Samsung Galaxy S10+ (SM-G975F)`, czyli `model` z naszego pliku plyty. Ten sam wezel
dal 11 wrzesnia 2026 mape RAM-u ze stockowego Androida, wiec mechanizm jest juz sprawdzony
na tym telefonie.

**Lista kontrolna pierwszego bootu z naszym drzewem.** Kroki 1 i 2 sa sprawdzone w zrodlach,
kroki 3 do 5 rozstrzygaja sie dopiero przy telefonie.

1. Nasz DTB jest w sciezce budowania: `arch/arm64/boot/dts/exynos/Makefile:19` wymienia
   `exynos9820-beyond2lte.dtb` (wnosi to `patches/0015`), a `arch/arm64/boot/dts/Makefile:20`
   ma `subdir-y += exynos`. Czyli `make dtbs` go buduje, a `dtbs_install` kladzie do
   `/boot/dtbs/<wersja>/exynos/`.
2. Pakiet jadra portu wola `dtbs_install` z `INSTALL_DTBS_PATH="$pkgdir/boot/dtbs"`
   (`sources/pmaports/device/testing/linux-postmarketos-exynos9820/APKBUILD:58-64`), wiec po
   przebudowie pakietu z nasza seria plik ma sie tam pojawic sam. Sprawdzic:
   `ls /boot/dtbs/*/exynos/exynos9820-beyond2lte.dtb`.
3. Plik musi trafic na **te sama partycje, z ktorej ladowane jest jadro**, bo stub czyta tylko
   stamtad (`drivers/firmware/efi/libstub/file.c:185-188`). Czy `boot-deploy` kopiuje tam caly
   katalog `dtbs`, nie da sie sprawdzic z tego repozytorium: w pmaports jest sam APKBUILD,
   a narzedzie ma osobne zrodlo. Jesli nie kopiuje, skopiowac recznie.
4. Dopisac do wpisu rozruchowego `dtb=/dtbs/<wersja>/exynos/exynos9820-beyond2lte.dtb`
   (ukosniki stub sam zamienia na odwrotne, `file.c:50-51`).
5. W logu startu szukac jednej z dwoch linii: `Using DTB from command line` znaczy, ze weszlo
   nasze drzewo, a `Ignoring DTB from command line.` znaczy, ze stub uznal secure boot za
   wlaczony i parametr odrzucil, czyli trzeba droga zapasowa. Po wstaniu systemu
   `cat /sys/firmware/devicetree/base/model` ma zwrocic `Samsung Galaxy S10+ (SM-G975F)`.

**uniLoader zostaje jako droga zapasowa.** Gdyby przyszlo startowac przez niego, wtedy dopiero
trzeba dopisac `board-beyond2lte.c` i `beyond2lte_defconfig` (`sources/uniLoader/configs` ma
tylko `beyond1lte_defconfig`, `board/samsung/` tylko `board-beyond1lte.c`) i sprawdzic
`fdtdump` sekcji `.dtb` zbudowanego obrazu, bo tam DTB jest wkompilowany w loader
(`sources/uniLoader/arch/aarch64/linker.lds.S:41-42`, adres podawany jadru przez `x0`
w `arch/aarch64/start.S:46-47`). Tej pracy nie ma i **nie jest potrzebna do pierwszego bootu**.

Przy okazji: plik plyty beyond1lte robi rzecz, od ktorej zalezy widoczny obraz, i warto
ja odtworzyc. `board-beyond1lte.c:19-21` zapisuje `0x1281` pod
`DECON_F_BASE + HW_SW_TRIG_CONTROL`, czyli 0x19030000 plus 0x70. To ta sama baza, ktora
ma nasz `decon0` (`patches/0040`), i ten sam offset, ktory nasz sterownik nazywa
`DECON_HW_SW_TRIG_CONTROL`. Ten sam plik podaje tez adres bufora obrazu, `0xca000000`
(`:29`, i to samo w `configs/beyond1lte_defconfig:8`), czyli **trzecie** niezalezne
zrodlo wartosci z HW-19.

#### Etap 0: kanal diagnostyczny

Bez UART cala reszta jest zgadywaniem, bo blad w DECON albo w domenie zasilania nie
zostawia sladu na ekranie.

1. UART wychodzi przez zlacze USB po przelaczeniu MUIC-a (rezystor 619 kR na CC/ID).
   Potwierdzenie: w konsoli widac log S-Boota jeszcze przed zaladowaniem jadra.
2. Zapisac caly log startu do pliku. To jest punkt odniesienia dla wszystkich pozniejszych
   porownan.

**Stan na 17 wrzesnia 2026: ROZSTRZYGNIETE. Pasywny rezystor na CC nie dziala na tym
telefonie, a wlasciwy kanal to VDM po CC.** Nie potrzeba juz kabla UART, zeby to wiedziec:
telefon sam zapisal decyzje S-Boota do `/proc/last_kmsg` i da sie je zdjac przez adb.
Log tego samego startu z wpietym jigiem pokazuje:
```
FW:1a.10 ST:07 31 00 CC:00 00 PD:00 07 ...
board_ccic_check_uart: jig_adc=1f, cc_adc=07
ifconn_com_to_open:
max77705_set_muic_uart_early: MUIC: SWITCH_COMMAND: 0x3f
init_cmdline: default: console=ram loglevel=4
```
`cc_adc=07` to `RID_OPEN` (dzialajacy jig dalby `06`), a `0x3f` to `COM_OPEN`, czyli S-Boot
sam ROZLACZYL linie danych, bo nie rozpoznal jiga. Trzy warstwy zgadzaja sie co do braku jiga:
jadro przez adb (`rid 7`, `No VPS`), S-Boot (`cc_adc=07`), rejestr CC (`CC:00 00`).
Pelna analiza z dowodami: `measurements/2026-09-17-etap0/sboot-analiza.md`, log:
`measurements/2026-09-17-etap0/sboot-log-z-last_kmsg.txt`.

Powod jest strukturalny: USB-C nie ma pinu ID. Na micro-USB rezystor szedl na ID i uklad
mierzyl go wprost (tak dziala do dzis na S7). Na USB-C konsole bootloadera wlacza sie
komunikatem VDM protokolu USB PD po linii CC, SVID Samsunga 0x04E8, nie rezystancja. Rozklada
to praca Alendal, Axelsson, Dyrkolbotn (2019) na Galaxy S9 z tej samej rodziny, ze slepym
replayem ramek AnyWaya S103. Zrodla zewnetrzne potwierdzaja, ze 300k/523k/619k na CC nie
dziala nikomu na USB-C.

**Wniosek dla portu:** nasza seria tego NIE dziedziczy. Podajemy wlasny `stdout-path` zamiast
`console=ram`, wiec nasze jadro po starcie przez EFI (`dtb=`) bedzie pisac na `serial0`
niezaleznie od S-Boota. Problem jiga dotyczy tylko PODGLADU S-Boota i kernela producenta przed
nasza seria. Do tego celu mamy juz dzialajacy, bezsprzetowy kanal: `/proc/last_kmsg` + pstore
przez adb. Trzy drogi do logu S-Boota, w kolejnosci trudnosci: (1) `/proc/last_kmsg` przez adb
(dziala, zero sprzetu), (2) emulacja VDM AnyWaya kontrolerem PD (np. FUSB302), (3) AnyWay S103
+ kabel GH81-11962W (zamowiony).

**Zdejmuje z listy:** etap 0 jako "znajdz kanal diagnostyczny" jest zamkniety. Kanal do S-Boota
i kernela producenta to `/proc/last_kmsg` przez adb; kanal do naszego jadra to `serial0` przez
`stdout-path`. Pasywny jig odpada z dowodem.

#### Etap 1: shell na porcie pmOS, przed nasza seria

Uruchomic istniejacy port (pmaports, kernel 7.2.0) i sprawdzic, ze dziala `dmesg`
oraz `/sys/kernel/debug` (`CONFIG_DEBUG_FS=y` i `CONFIG_DEBUG_FS_ALLOW_ALL=y`,
`sources/pmaports/device/testing/linux-postmarketos-exynos9820/config-postmarketos-exynos9820.aarch64:7607-7608`).

**Najpierw jedna przeszkoda, ktora unieruchamia caly etap 2.** Ten port jest zbudowany
z `# CONFIG_DEVMEM is not set` (`:2727` tego samego pliku), wiec `/dev/mem` w nim nie
powstaje i **zadne `devmem` nie zadziala**, ani z busyboxa, ani jako `devmem2`. Brak
`CONFIG_STRICT_DEVMEM` (`:7816`) nic tu nie zmienia, bo to ograniczenie wlacza sie
dopiero nad istniejacym `/dev/mem`. Sa dwa wyjscia i oba trzeba przygotowac **przed**
sesja przy telefonie, nie w jej trakcie:

1. Przebudowac pakiet jadra portu z `CONFIG_DEVMEM=y`
   (`pmbootstrap kconfig edit linux-postmarketos-exynos9820`, ustawic
   *Device Drivers, Character devices, /dev/mem virtual device support*). Najkrotsza
   droga, bo caly etap 2 zostaje wtedy taki, jak zapisany nizej.
2. Albo wgrac wlasny modul czytajacy okna przez `ioremap` i wystawiajacy je w debugfs.
   `CONFIG_MODULES=y` (`:820`), wiec modul da sie zaladowac bez przebudowy jadra, ale
   trzeba go napisac i zbudowac pod to samo drzewo.

Polecenia `devmem` nizej zakladaja droge pierwsza.

**Zakres tej blokady: dotyczy TYLKO portu pmOS, nie naszego jadra.** `DEVMEM` ma w mainline
`default y` (`sources/linux/drivers/char/Kconfig:259-261`), wiec jadro zbudowane z arm64
defconfiga i `scripts/exynos9820.config` ma `/dev/mem` samo z siebie; port pmOS wylaczyl je
u siebie jawnie. `STRICT_DEVMEM` jest wprawdzie `default y` na arm64
(`lib/Kconfig.debug:1962-1966`), ale nie zamyka drogi do rejestrow: arm64 bierze wersje
ogolna (`arch/arm64/Kconfig:139` wybiera `GENERIC_LIB_DEVMEM_IS_ALLOWED`), a ta przepuszcza
wszystko, co **nie jest** pamiecia RAM, o ile obszar nie jest wylaczny
(`lib/devmem_is_allowed.c:21-28`). Wylacznosc wlacza dopiero `IO_STRICT_DEVMEM`
(`lib/Kconfig.debug:1982-1992`), ktory nie ma domyslnej wartosci, czyli jest wylaczony,
dopoki ktos go nie wlaczy. Wniosek: odczyty rejestrow z etapu 2 zadzialaja na naszym jadrze
bez zadnej dodatkowej opcji, a przygotowanie przed sesja jest potrzebne tylko po to, zeby
zrobic te pomiary **przed** wpuszczeniem naszego DECON-a.

**HW-23, oryginalnosc panelu dotykowego.** Sterownik `s6sy761` jest w mainline i w tym
porcie dziala, wiec to najtanszy pomiar w calej liscie:

```sh
dmesg | grep -i s6sy761
evtest        # dotknac ekranu i sprawdzic, czy leca zdarzenia
```

Probe bez zdarzen przy dotyku oznacza panel aftermarket, nie blad portu. Wynik zapisac,
bo determinuje interpretacje wszystkich pozniejszych testow ekranu.

**HW-19 jest juz zamkniete** (11 wrzesnia 2026, `s3cfb.bootloaderfb=0xca000000` z linii
polecen stockowego jadra), wiec nie ma tu nic do zmierzenia. Zostaje tania kontrola krzyzowa,
warta minuty, bo sprawdza inna rzecz niz tamten odczyt: czy tego samego adresu uzywa **ten
lancuch startowy**, a nie tylko S-Boot.

```sh
cat /proc/device-tree/chosen/framebuffer*/reg | xxd
dmesg | grep -i simple-framebuffer
```

Rozjazd z `0xca000000` nie podwazalby pomiaru z etapu 0a, tylko znaczyl, ze U-Boot zostawia
bufor gdzie indziej niz S-Boot, i to trzeba by zapisac jako osobna pozycje.

#### Etap 2: odczyty rejestrow, ktore nie wymagaja naszego kodu

Wszystko ponizej to czysty odczyt przez `devmem`, na dzialajacym systemie.

**HW-11, rewizja krzemu.** Blok chipid siedzi pod 0x10000000 (wezel w downstreamowym DT,
`sources/ds/exynos9820.dts`). Odczytac i porownac z progiem EVT0. Wynik decyduje, czy
dwa zapisy w `patches/0025` (PLL_CON8 = 0xA28, MC_ANA_CON2 = 0x2) sa dozwolone na tym
egzemplarzu; u producenta sa objete `#if !defined(CONFIG_SOC_EXYNOS9820_EVT0)`.

**HW-07 i HW-08, domena zasilania DPU.** Zrzucic PELNE 32 bity, przed i po probie
wlaczenia domeny, oraz cale okno:

```sh
devmem 0x15861e00 32      # DPU_CONFIGURATION
devmem 0x15861e04 32      # DPU_STATUS
for a in 0x15861e08 0x15861e0c 0x15861e10 0x15861e14 0x15861e18 0x15861e1c; do
        devmem $a 32
done
```

Szukamy dwoch rzeczy: **ktore bity** zmieniaja stan (maska `local_pwr_cfg = 0x1` jest
wywnioskowana, nie odczytana jako szerokosc pola) oraz czy domena w ogole wstaje bez SMC,
bo downstreamowy wezel ma `need_smc = <0x191b0204>`.

**HW-09, wersja SYSMMU.** Dla wszystkich trzech instancji:

```sh
for b in 0x190a0000 0x190b0000 0x190c0000; do
        devmem $((b + 0x034)) 32  # REG_MMU_VERSION
        devmem $((b + 0x870)) 32  # REG_V7_CAPA0
        devmem $((b + 0x874)) 32  # REG_V7_CAPA1
done
```

Wersja lezy pod 0x034, nie pod poczatkiem okna: pod 0x000 stoi MMU_CTRL i odczyt stamtad
daje liczbe, ktora wyglada na wersje, a nia nie jest. Rozklad pola bierze sie z
`sources/linux/drivers/iommu/exynos-iommu.c:151-155`: sterownik wycina najpierw
`(reg >> 21) & 0x7ff`, a z tego major to gorne cztery bity, minor dolne siedem, czyli
w surowym slowie major siedzi w [31:28], a minor w [27:21].

Major >= 7 potwierdza teze, ze mainline'owy `exynos-iommu` wystarczy i sterownika nie
trzeba pisac.

#### Etap 3: nasza seria, ale jeszcze bez obrazu

Zbudowac jadro z seria (`patches/`), wystartowac i **nie ruszac** DECON-a.

**HW-16, HW-17, HW-18, zegary.** Po probe sterownika zegarow:

```sh
cat /sys/kernel/debug/clk/clk_summary > clk_summary.txt
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary
```

Trzy pytania: czy `enable_count` bramek zgadza sie z odczytem rejestrow CMU_DPU przez
`devmem`, na ktorym rodzicu stoja muxy CMU_CMGP (offset 0x100c, jesli RCO to trzeba
zmierzyc SCL i wyliczyc jego czestotliwosc wstecz), i czy `pd_dpu` przechodzi w off,
czy blokuje ja nadmiar bramek `CLK_IS_CRITICAL`.

**HW-15, numery przerwan, czesc bez DECON-a.** `/proc/interrupts` plus wymuszona
aktywnosc tych blokow, ktore da sie ruszyc bez modesetu: transakcja I2C do PMIC-a panelu
i wymuszony page fault SYSMMU. Przerwanie, ktore nigdy nie zlicza, ma zly numer albo zly
typ wyzwalania (port wpisuje `IRQ_TYPE_LEVEL_HIGH`, downstream deklaruje typ 0).
Przerwania samego DECON-a zostaja na etap 4, bo do zliczenia potrzebuja ramki, a ten
etap DECON-a nie rusza.

#### Etap 4: pierwszy modeset

Dopiero teraz wlaczyc DECON i DSIM. Log UART jest tu jedynym zrodlem prawdy.

**HW-21, czasy resetu panelu.** Sonda na `gpa3-4` i na szynach `vdd3`, `vci`, `vddr`.
Najpierw odtworzyc sekwencje ze stockowego Androida, potem skracac czasy w sterowniku,
az panel przestanie startowac, zeby poznac realny margines. Wartosc 10 ms nie pochodzi
z zadnego zrodla.

**HW-02, HW-03, zegar lacza i escape.** Czestosciomierz na linii zegarowej D-PHY przy
zaprogramowanym P/M/S = 2/138/2 rozstrzyga spor 898 kontra 897,0 kontra 897,6 Mbps.
Osobno zmierzyc wyjscie dzielnika escape (18 kontra 20 MHz). **Dopiero ten pomiar ustala
jedna wartosc wejsciowa**, z ktorej trzeba przeliczyc wszystkie liczniki pochodne.

**HW-01, jednostka licznikow D-PHY.** Oscyloskop albo analizator MIPI: zmierzyc realne
T-CLK-PREPARE, T-CLK-ZERO, T-HS-PREPARE i T-HS-ZERO przy zaprogramowanym wierszu 900
i wyliczyc stosunek do zapisanych licznikow. Bez oscyloskopu: zmieniac po jednym liczniku
o znana delte i szukac granicy, przy ktorej panel przestaje odpowiadac.

**HW-12, HW-13, DSC.** Wyswietlic wzorzec testowy przy `initial_dec_delay` 436 i 616
(bledna wartosc daje przesuniecie albo poszarpanie pierwszych linii slice), a nastepnie
zrzucic cale okna enkoderow (0x4000 i 0x5000 wzgledem bazy DECON) i porownac slowo po
slowie z tym, co programuje stockowy kernel.

**HW-04, TE.** Sonda na `gpd0-0`: odstep zbocza TE od poczatku transferu ramki przy
3041, 3042 i 3053, plus obserwacja tearingu.

**HW-14 i reszta HW-15, przerwania DECON.** Zarejestrowac wszystkie cztery jako handler
zliczajacy i porownac czestotliwosci przy ciaglym scan-oucie. To zamyka takze te czesc
HW-15, ktorej etap 3 nie mogl zliczyc, bo nie bylo ramki.

#### Etap 5: dane panelu

**HW-06, MTP.** Gdy lacze DSI odpowiada, odczytac 34 bajty komenda 0xC8 i **zrzucic je
przez UART**. Ten zrzut jest cenniejszy niz sam obraz: pozwala uruchomic
`scripts/check-dimming-engine.sh` na realnych danych zamiast na losowych, a zapisany
w repo staje sie golden file i bramka przestaje byc losowa.

**HW-05, FFC.** Porownac zaklocenia przy slowie firmowym 0x3E01 i modelowym 0x3DFA
(898 Mbps), a potem sprawdzic model na innym zegarze, np. 950 Mbps ze slowem 0x3A96.

**HW-22, wysokosc matrycy.** Suwmiarka na aktywnym obszarze, dokladnosc lepsza niz
0,5 mm. Trzy zrodla podaja 148, 147 i 121 mm.

#### Co zrobic z wynikami

Dla kazdej zamknietej pozycji, w tej samej sesji:

1. usunac komentarz `UNVERIFIED: HW-nn` z kodu albo z DT,
2. usunac pozycje z `docs/HW-BLOCKED.md`,
3. dopisac pomiar do `scripts/verify.sh` jako golden file (zrzut rejestru, odczyt MTP,
   zmierzona czestotliwosc), zeby regresja zapalila sie sama,
4. uruchomic `scripts/verify.sh` i sprawdzic, ze konczy sie kodem 0.

Bramka spojnosci w `verify.sh` pilnuje, ze kazde `UNVERIFIED: HW-nn` w serii ma pozycje
w dokumencie, wiec usuniecie tylko jednej z dwoch stron zapali sie od razu.
