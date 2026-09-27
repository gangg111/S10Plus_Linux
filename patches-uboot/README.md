# Wlasny bootloader: port U-Boota dla Exynos 9820

Ten katalog trzyma **nasza** seria patchy dla U-Boota, na tych samych zasadach co
`patches/` dla jadra: baza to czysty upstream, kazdy patch jest nasz, a cudzy kod
sluzy najwyzej za punkt odniesienia w dokumentacji, nigdy do przepisania.

## Po co wlasny bootloader

S-Boot Samsunga **nie przyjmuje DTB zgodnych z mainline** i ignoruje `cmdline`
oraz offsety z `boot.img` (wiki pmOS, strona `samsung-exynos9820`). Nasze jadro
z naszym DTB nie ma wiec jak wystartowac bezposrednio. Potrzebna jest warstwa
posrednia, ktora poda jadru wlasciwy DTB przez EFI.

Istnieje gotowy fork (`chiffathefox/u-boot`, galaz `exynos9820`), ale jest cudzy.
Skoro caly sens tego projektu to wlasny port, bootloader tez ma byc nasz. Przy
okazji zyskujemy rzecz, ktorej fork nie da: **mozemy dolozyc do niego, co chcemy**,
na przyklad wlasne wyjscie diagnostyczne (patrz `docs/UART-BRINGUP.md`, gdzie
pasywny jig okazal sie slepa uliczka) albo zrzuty rejestrow zamykajace pozycje
z `docs/HW-BLOCKED.md` jeszcze przed startem jadra.

## Co upstream daje za darmo (zmierzone 18.09.2026)

Na przypietym commicie upstream ma juz:

| element | stan |
|---|---|
| `ARCH_EXYNOS9` w `arch/arm/mach-exynos/Kconfig` | jest |
| plyta `board/samsung/exynos-mobile` | jest, z `debug-exynos7870.config` jako wzorcem |
| `exynos-mobile_defconfig` | jest, celuje w `exynos7870-a2corelte` |
| framework pinctrl (`pinctrl-exynos.c`) + warianty 7420, 78x0, 850 | jest |
| framework clk (`clk-pll.c`) + warianty 7420, 7870, 850 | jest |
| framework UFS (`ufs-uclass.c`, `ufshcd-dwc.c`) + 9 sterownikow obcych | jest |
| EFI loader | kompletny |

Baza zbudowana i sprawdzona: `make CROSS_COMPILE=aarch64-linux-gnu- exynos-mobile_defconfig`
plus `make -j` daje `u-boot.bin` 730 000 B w 11 sekund.

**Czego upstream NIE ma:** zadnego sterownika UFS dla Exynosa oraz niczego dla 9820.
Nie ma tez DT dla `exynos9820` (sa `exynos8895`, `exynos9810`, `exynos990`,
`exynos2200`), bo nasze DTS jeszcze nie trafily do mainline.

## Zakres do napisania

| plik | linie | stan |
|---|---|---|
| `drivers/pinctrl/exynos/pinctrl-exynos9820.c` | 196 | **gotowe, patch 0001** (8 kontrolerow, 62 banki) |
| typy `PLL_0817X`, `PLL_0818X`, `PLL_1018X` w `clk-pll` | 8 | **gotowe, patch 0002** |
| `drivers/clk/exynos/clk-exynos9820.c` | 322 | **gotowe, patch 0003** (CMU_TOP, CMU_PERIC0, CMU_FSYS1) |
| `include/dt-bindings/clock/samsung,exynos9820.h` | 564 | **gotowe, patch 0003** (kopia z naszego jadra, znika po synchronizacji dts/upstream) |
| `drivers/phy/phy-samsung-ufs.c` + `.h` | 447 | **gotowe, patch 0004** (warstwa wspolna rodziny) |
| `drivers/phy/phy-exynos9820-ufs.c` | 262 | **gotowe, patch 0004** (tablice i czekania 9820) |
| `include/samsung-ufs-phy.h` | 52 | **gotowe, patch 0004** (punkty kalibracji dla hosta) |
| `drivers/ufs/ufs-exynos.c` + `.h` | 785 | **gotowe, patch 0005** (cztery punkty kalibracji, rejestry firmowe) |
| DTS `exynos9820*` w `dts/upstream/src/arm64/exynos/` | 1719 | **gotowe, patch 0007** (kopia bajt w bajt z serii jadra) |
| `configs/exynos9820-beyond2lte_defconfig` | 52 | **gotowe, patch 0008** |
| nakladka `exynos9820-beyond2lte-u-boot.dtsi` | 114 | **gotowe, patch 0008** (UFS i CMU_FSYS1) |
| `board/samsung/exynos-mobile` bez wymogu eMMC | 40 | **gotowe, patch 0006** |

Kazdy gotowy patch zweryfikowany kompilacja skrosna (`aarch64-linux-gnu-gcc` 14)
na przypietej bazie upstreamu.

**Znalezisko z tej pracy:** przenoszenie wiedzy o PLL-ach do bootloadera ujawnilo blad
w NASZEJ serii jadra, gdzie wszystkie dziewiec wywolan `PLL()` dostawalo offset CON0
zamiast CON3, czyli czytalo rejestr sterujacy zamiast wspolczynnikow M/P/S. Naprawione
w `patches/0013`, pilnuje `scripts/check-pll-con3.py`. Szczegoly w `docs/00-summary.md`.
Cudzy fork ma ten sam blad, wiec wziecie go zakonserwowaloby usterke.

**Pierwszy etap portu, czyli rozruch z pamieci masowej, zamknal sie w osmiu
patchach**: 1740 linii kodu i konfiguracji plus 1719 linii drzewa urzadzen
przeniesionego z serii jadra. Szacunki linii pochodza z pomiaru forka i sluza
za skale zadania, nie za wzorzec do przepisania.

## Stan serii: 28 patchy (22.09.2026)

Osiem patchy wyzej to **nie jest** cala seria. Po uruchomieniu bootloadera na
telefonie doszlo dwanascie kolejnych, ktore przez pewien czas zyly poza seria:
jeden commit opisany jako WIP oraz 2391 linii, ktorych zaden commit nie obejmowal.
Ten akapit istnieje, bo przez caly ten czas README twierdzil, ze port jest
kompletny w osmiu patchach, a zadna bramka tego nie widziala: wszystkie czytaja
drzewo robocze, a nie patche.

| patch | co wnosi |
|---|---|
| 0009 | kopie drzew urzadzen zsynchronizowane z seria jadra |
| 0010 | pozostale piec CMU: FSYS0A, PERIS, APM, CMGP, DPU |
| 0011 | dzielniki CMU_PERIC0 rejestrowane po swoich bramkach |
| 0012 | bufory transferu UFS niewyrownane do DMA ida przez bufor posredni |
| 0013 | odczyt stanu protektora pamieci masowej i spojnosc pamieci podrecznej |
| 0014 | ochrona dzielnika konsoli przed niedorzeczna czestotliwoscia |
| 0015 | czcionka 32x64 z polskimi literami |
| 0016 | przejecie framebuffera zostawionego przez S-Boota |
| 0017 | `bootmenu` z rysowaniem po stronie plyty |
| 0018 | menu BEYOND BOOT w czterech jezykach |
| 0019 | wariant Exynos9820 w PHY USB |
| 0020 | fastboot po kablu |
| 0021 | sterta na tyle duza, zeby fastboot przyjal caly obraz |
| 0022 | drzewo telefonu zsynchronizowane z glownym ukladem zasilania |
| 0023 | opis calego panelu przeniesiony z serii jadra |
| 0024 | obszar ramoops wziety z drzewa jadra |
| 0025 | sterownik trybu rozruchu trzymanego w kontrolerze systemowym |
| 0026 | plyta czyta ten tryb i przy bootloader wchodzi w fastboot |
| 0027 | czyszczenie jednego pola bloku sterujacego z poziomu kodu |
| 0028 | plyta czyta tez blok z partycji misc, i tedy to dziala |

Cala seria: zero bledow checkpatcha `--strict`, stosuje sie 28/28 na przypieta
baze, a **kazdy z dwunastu nowych punktow buduje sie osobno**, z wlasna
konfiguracja z defconfiga, wiec serie da sie przepolowic przy szukaniu usterki.
Pilnuje tego `scripts/check-uboot-seria.sh`, wpiety w `scripts/verify.sh`:
sprawdza, ze seria stosuje sie na baze, ze daje DOKLADNIE to drzewo, ktore
czytaja pozostale bramki, ze poza seria nie lezy nic, i ze checkpatch nie
przybiera. Bramka ma przetestowane negatywnie trzy sposoby zepsucia: plik
zmieniony poza seria, latka rozjechana z drzewem i plik nieznany gitowi.

Rozruch, menu i fastboot byly uruchomione na telefonie. Wejscie w fastboot
na zadanie z dzialajacego systemu **jest potwierdzone na sprzecie**
(`measurements/2026-09-22-tryb-rozruchu`): dziala przez blok na partycji
`misc` (patch 0028), natomiast przez rejestr jednostki zasilania (patche
0025 i 0026) **dzialac nie moze**, bo pierwszy stopien rozruchu czyta ten
rejestr wczesniej i zabiera slowo dla siebie; to tez jest zmierzone. Nie
byly na telefonie uruchomione:
poprawka kolejnosci zegarow (patch 0011, pozycja HW-45), fastboot ani sciezka
USB.

## Zasady (te same co przy jadrze)

1. Baza przypieta w `SOURCES.md`, zadnych niepinowanych zaleznosci.
2. Kazdy patch ma udokumentowane zrodlo kazdej stalej: pomiar z urzadzenia,
   dokumentacja producenta albo nasz wlasny sterownik jadra. Cudzy kod wolno
   **czytac i cytowac**, nie kopiowac.
3. Kazda niepewna wartosc dostaje adnotacje `UNVERIFIED` i pozycje w `docs/HW-BLOCKED.md`.
4. Bramki w `scripts/verify.sh`, kod 2 = bramka nieuruchomiona, nie zielona.

## Korekta zakresu przy patchu 0004 (PHY UFS)

Tabela wyzej szacowala PHY na ~190 linii, bo tyle ma plik forka. Szacunek byl
zanizony o warstwe wspolna: upstream **nie ma zadnej czesci** PHY UFS Samsunga,
w `drivers/phy/` lezy jeden sterownik Exynosa i jest to USB. Realnie wyszlo
761 linii w trzech plikach. To ten sam rodzaj pomylki co przy pierwszym
oszacowaniu calosci na ~700 linii: liczenie po pliku forka zamiast po tym,
czego brakuje w upstreamie.

### Czego patch 0004 celowo NIE robi

Tablice producenta dla tych samych punktow kalibracji zawieraja obok wpisow do
bloku PMA takze wpisy warstw `PHY_PCS_*` i `UNIPRO_*`, ktore ida przez DME i
przez okno UniPro, a nie przez okno PMA. Nalezą do sterownika hosta i tam
trafia. Trzy rzeczy, o ktorych host bedzie musial pamietac, bo bez nich sam PHY
nie wystarczy:

1. Blok po-linkowy PMA producent otacza para zapisow atrybutu UniPro `0xA006`
   (`0x80000000` przed, `0x0` po, `ufs-cal-9820.c:396` i `:447`), wiec wolanie
   `generic_phy_configure(UFS_PHY_POST_LINK)` musi wypasc miedzy nimi.
2. Wpisy `PHY_PCS_*_PRD` i `*_LR_PRD` maja w tablicy wartosc `0x00` jako
   ATRAPE: dyspozytor producenta podstawia w to miejsce okresy wyliczone
   z `mclk_rate` (`ufs-cal-9820.c:1039-1090`). Przepisane doslownie daja zera
   i psuja wykrywanie line-reset. Nasz CMU musi wiec umiec podac czestotliwosc
   zegara UniPro przez `clk_get_rate`, nie tylko go wlaczyc.
3. Liczbe pasow do kalibracji host musi znac PRZED startem linku, a rdzen
   U-Boota czyta `PA_CONNECTEDRXDATALANES` dopiero po nim. Zrodlem ma byc DT
   (`ufs,pmd-attr-lane = [02]`) albo wlasny `dme_get`.

Hibernacja jest pominieta swiadomie: producent ma tablice wejscia i wyjscia
z niej, ale bootloader czyta pamiec i oddaje sterowanie, wiec nigdy nie prosi
lacza o hibernacje.

### Pulapka DT, ktora czeka przy nastepnym kroku

Drzewo producenta ma `ufs-phy` jako dziecko wezla UFS **bez `compatible`, bez
`#phy-cells` i bez `phys`**, wiec w U-Boocie taki wezel nie zbinduje sie do
niczego. Nasz DTS musi mu nadac `compatible = "samsung,exynos9820-ufs-phy"`,
`#phy-cells`, `samsung,pmu-syscon` i powiazanie `phys`/`phy-names` po stronie
hosta. Do tego okno PMA producenta ma `0x800`, a tablice siegaja `0xbbc` na
drugim pasie; u producenta uchodzi to na sucho tylko dlatego, ze system
operacyjny mapuje cale strony. Nasz wezel dostanie `0x1000`, a sterownik i tak
odmawia startu przy oknie krotszym niz zasieg tablic.

Wezel PMU musi dostac `compatible = "samsung,exynos9820-pmu"` (patch 0004
dopisuje go do sterownika) i musi byc sprobowany PRZED PHY, bo to przez jego
syscon idzie sterowanie izolacja.

### Co ten patch ustalil o zrodlach producenta

Dwa miejsca, w ktorych oczywisty odczyt daje sterownik piszacy pod zly adres
i milczacy o tym:

* Odstep miedzy bankami rejestrow pasow to `0x400` bajtow, wedlug kopii
  `PHY_PMA_TRSV_ADDR` z pliku 9820 (`ufs-cal-9820.c:66`). Kopia o tej samej
  nazwie w `ufs-exynos.h:388` mowi `0x140` i jest martwa, nikt jej w tym
  drzewie nie wola.
* Czekanie na zatrzask odbiornika odpytuje rejestr co **40 us**, nie 400:
  `ufs30_cal_wait_cdr_lock` (`ufs-cal-9820.c:915-940`) ma `delay2_us = 40`
  miedzy odczytami i `delay_us = 1` przed restartem bloku CDR. Fork ma w obu
  miejscach 400 us.

Pilnuje tego bramka `scripts/check-ufs-phy-cal.py`, wpieta w `scripts/verify.sh`.
Sprawdza w obie strony: kazdy wpis sterownika wobec cytowanej linii producenta
ORAZ kazda linie producenta dotyczaca naszej plyty wobec sterownika. Ta druga
polowa jest wazniejsza, bo fork mial wszystkie przepisane wartosci poprawne,
a gubil cale tablice i czekania.

## Korekta zakresu przy patchu 0005 (host UFS)

Tabela dawala hostowi ~1900 linii, znowu z pomiaru forka, a wyszlo **785**.
Tym razem szacunek byl ZAWYZONY, i to z tego samego powodu, dla ktorego PHY
bylo zanizone: liczono cudzy plik zamiast tego, czego brakuje. Plik producenta
ma 1327 linii, ale wiekszosc z nich obsluguje rzeczy, ktorych bootloader nie
robi: zarzadzanie energia, hibernacje, obsluge bledow w locie, szyfrowanie
sprzetowe (FMP), jednostke ochrony (SMU), log CPORT i sysfs. Dla porownania
wszystkie sterowniki UFS producentow w upstreamie mieszcza sie w 232 do 692
liniach, a z tablic kalibracyjnych po stronie hosta zostaje 38 wpisow.

**Wniosek metodyczny, ten sam co przy PHY:** szacuj po tym, czego brakuje
w upstreamie i co jest realnie potrzebne do bootu, nie po objetosci cudzego
pliku. Raz dalo to blad czterokrotnie w dol, raz dwuipolkrotnie w gore.

### Czego patch 0005 celowo NIE robi

Hibernacja, zarzadzanie energia, szyfrowanie FMP, jednostka SMU (cale czwarte
okno `0x13d70000`), log CPORT i obsluga bledow dzialajacego systemu.
Bootloader czyta pamiec i oddaje sterowanie.

### Ustalenia, ktore zmienily plan

1. **Rdzen U-Boota nie potrzebuje zmiany.** Brakuje w nim haka po zmianie
   trybu mocy, ale punkt PRZED zmiana lapie sie w `get_max_pwr_mode` (to
   ostatnia instrukcja `ufshcd_get_max_pwr_mode`), a punkt PO zmianie w naszym
   `probe`, zaraz po powrocie z `ufshcd_probe`. Zapowiadany osobny patch do
   rdzenia okazal sie niepotrzebny.
2. **Cicha degradacja do PWM-G1.** Gdy rdzen nie umie wyliczyc najlepszego
   trybu, loguje to, POMIJA zmiane trybu i mimo to zwraca sukces. Bez wlasnej
   bramki pamiec chodzilaby kilkadziesiat razy wolniej, a w logu nie byloby
   ani slowa. Sterownik sprawdza `pwr_info`, zanim wykona ostatni punkt
   kalibracji.
3. **Tablica przed-linkowa jest pisana WIELE RAZY.** Rdzen wola
   `link_startup_notify(PRE_CHANGE)` z wnetrza petli ponowien, wiec wszystko
   w niej musi zniesc powtorzenie. Liczba pasow jest czytana raz i pamietana,
   bo przy drugim obiegu lacze bywa juz czesciowo podniesione.
4. **Bramkowanie zegara PHY rozwiazane jak w mainline, nie jak u producenta.**
   Producent trzyma bit `MPHY_APBCLK_STOP` poza swoja zbiorcza maska i kasuje
   go przy KAZDYM dostepie do bloku PMA, co wymagaloby, zeby sterownik PHY
   siegal do okna hosta. Mainline wklada ten bit do maski zbiorczej i kasuje
   raz na caly czas podnoszenia lacza. Wzielismy wersje mainline i dzieki temu
   patch 0004 nie wymagal zadnej zmiany.

### Bramki

`scripts/check-ufs-phy-cal.py` (warstwa PMA) i `scripts/check-ufs-host-cal.py`
(warstwy DME i UniPro), obie wpiete w `scripts/verify.sh`, obie czytaja
sterownik Z PATCHA, bo to patch jest tym, co sie wysyla. Wspolny parser tablic
producenta lezy w `scripts/ufs_cal.py`, zeby dziura w nim nie powstala dwa
razy: wzorzec wymagajacy przedrostka `0x` w polu wartosci nie widzial wpisow
zapisanych dziesietnie, przez co polowa "kompletnosc" nie miala jak ich
zazadac. Dzis parser krzyczy na kazdy wiersz tablicy, ktorego nie umie
rozebrac.

Bramka hosta sprawdza dodatkowo **kolejnosc**: przekazanie sterowania do PHY ma
stac dokladnie tam, gdzie u producenta lezy blok PMA. To ona pilnuje, zeby para
zapisow atrybutu `0xA006` zostala klamra wokol tego bloku, a nie wyladowala
przed nim. Obie bramki maja przetestowane negatywnie po trzy sposoby zepsucia.

**Czego bramki NIE pilnuja:** seria bootloadera nie ma odpowiednika
`docs/HW-BLOCKED.md` ani liczenia adnotacji `UNVERIFIED` (bramka w
`scripts/verify.sh` liczy wylacznie `patches/*.patch`, czyli serie jadra).
Patch 0005 wnosi jedna taka adnotacje, o kolejnosci resetu urzadzenia wzgledem
programowania hosta, i trzeba ja trzymac w glowie do uruchomienia na sprzecie.

## Ostatni krok: drzewo urzadzen, plyta i konfiguracja (patche 0006 do 0008)

### Dwa bledy w JUZ ZATWIERDZONYCH patchach, ktore wyszly dopiero teraz

Dopoki port budowal sie defconfigiem 7870, oba byly niewidzialne. Oba siedzialy
w patchu 0001 i oba sa w nim naprawione.

1. **`PINCTRL_EXYNOS9820` nie mial `select PINCTRL_EXYNOS`**, jako jedyny
   z czterech wariantow w tym Kconfigu. Wspolny rdzen pinctrl budowany jest
   tylko pod tym symbolem, wiec konfiguracja z samym naszym sterownikiem
   NIE LINKOWALA SIE. Nie bolalo, bo defconfig 7870 wlacza swoj wariant, ktory
   ten symbol wybiera.

2. **Kolejnosc tablic bankow nie odpowiadala aliasom.** `pinctrl-exynos.c:177`
   wybiera tablice przez `dev_seq(dev)`, a dla wezla z aliasem jest to numer
   aliasu. Nasze drzewo numeruje je alfabetycznie (alive, aud, cmgp, fsys0,
   fsys1, peric0, peric1, vts), a sterownik mial kolejnosc po adresach (peric0,
   peric1, fsys0, fsys1, vts, alive, cmgp, aud). KAZDY kontroler dostalby cudza
   tablice bankow: kompilacja przechodzi, drzewo sie waliduje, a piny sa
   ustawiane w zlych blokach. To byla pozycja oznaczona `UNVERIFIED` w patchu
   0001; teraz jest rozstrzygnieta w druga strone niz zakladal komentarz, bo
   komentarz mowil o drzewie BEZ aliasow, a nasze je ma. Pilnuje tego bramka.

### Dwie blokady startu w kodzie plyty

Plyta `exynos-mobile` zakladala eMMC. `misc_init_r` wolalo `blk_get_dev("mmc", 0)`
i zwracalo `-ENODEV`, a rdzen zamienia blad initcalla na `hang()`, wiec telefon
z UFS stawal PRZED dotknieciem pamieci. Drugi raz to samo robil setup fastboota.
Patch 0006 szuka urzadzenia po kolei w `mmc`, potem `scsi` (tam blokowa warstwa
wystawia UFS), a fastbootowi bez eMMC odbiera tylko flashowanie. Przy okazji
caly ten setup daje sie wykompilowac, czego wczesniej nie dalo sie zrobic: kod
nazywal opcje fastboota bezwarunkowo.

Drugie: `CONFIG_NR_DRAM_BANKS=3`, a ta plyta ma szesc bankow pamieci, wiec trzy
z nich byly dla U-Boota niewidzialne. Nasz defconfig ma szesc.

### Dlaczego kopia, a nie drugi generator

Zwiad rekomendowal drugi generator DTS obok `gen-dts-exynos9820.py`. Odrzucone:
`dts/upstream` jest z zalozenia LUSTREM drzewa jadra (widac to na 7870, gdzie
plik jest bajt w bajt kopia z naglowkiem i prawami autorskimi jadra), a dodatki
wylacznie u-bootowe maja w tym drzewie swoje miejsce, `arch/arm/dts/<plyta>-u-boot.dtsi`,
doklejany automatycznie (`scripts/Makefile.lib:226`). Wiec trzy pliki sa wierna
kopia, a wezly, ktorych jadro jeszcze nie ma (UFS, PHY, CMU_FSYS1), leza
w nakladce. Drugi generator duplikowalby okolo 1400 linii tekstu wezlow i wnosil
dokladnie to ryzyko rozjazdu, ktoremu mial zapobiegac.

### Bramka

`scripts/check-uboot-dts.py`, wpieta w `scripts/verify.sh`, sprawdza trzy rzeczy
roznego rodzaju: kopie w `dts/upstream` musza byc BAJT W BAJT plikami z galezi
`series` drzewa jadra; kolejnosc aliasow `pinctrl` musi odpowiadac kolejnosci
tablic bankow w sterowniku; adresy wezlow UFS musza zgadzac sie z drzewem
producenta, lacznie z oknem PMA, ktore musi pokryc drugi pas. Wszystkie trzy
przetestowane negatywnie.

### Czego ten krok NIE robi

Wyswietlacz, USB, fastboot, eMMC i uklad zarzadzania zasilaniem sa poza
defconfigiem: zaden z nich nie lezy na drodze od resetu do odczytu pamieci
i oddania sterowania przez EFI, i zaden nie byl probowany na tym telefonie.
Wczesna konsola jest osobnym fragmentem do recznego scalenia, bo jej adres
znamy z drzewa, a czestotliwosci taktowania NIE ZMIERZYLISMY.

### Co jest nadal nieudowodnione

Nic z tego portu nie bylo uruchomione na sprzecie. Trzy rzeczy do sprawdzenia
przy pierwszym starcie, w tej kolejnosci: czy wczesna konsola cokolwiek mowi
(jesli nie, pierwszym podejrzanym jest czestotliwosc z fragmentu), jaka
czestotliwosc zegara UniPro wypisuje sterownik UFS, i czy lacze doszlo do biegu
wysokiego. Dowodem koncowym jest ODCZYT SEKTORA, a nie `ufs init` bez bledu:
sama komenda `ufs init` nie skanuje SCSI.

## Domkniecie serii: opieka i dokumentacja plyty

Dwie rzeczy, ktore zostawaly po stronie "gotowe, ale nie do wyslania".

**Wpis w MAINTAINERS.** Checkpatch pytal o niego przy kazdym patchu wnoszacym
pliki. Sekcja `ARM SAMSUNG EXYNOS9820 SOC` stoi zaraz za `EXYNOS850` (jest
bezposredni precedens o tym samym ksztalcie) i obejmuje sterowniki, defconfig,
nakladke, naglowek bindingu zegarow i fragment konsoli. Po niej
`scripts/get_maintainer.pl` kieruje nasze pliki pod ten wpis, a patch 0008 ma
**0 bledow, 0 ostrzezen, 0 uwag**. Pozostale patche wciaz maja to jedno
ostrzezenie i tak ma byc: wpis wchodzi raz, w ostatnim patchu serii.

**Strona `doc/board/samsung/exynos-mobile/exynos9820.rst`.** Rodzina ma stron
per SoC (jest `exynos7870.rst`), naszej brakowalo, a procedura dla 9820 ROZNI
SIE od tamtej i bez opisu nikt by tego nie odgadl.

### Czym rozni sie obraz rozruchowy tego telefonu

Zmierzone na zbudowanym obrazie, nie przepisane z 7870:

* `u-boot.bin` to **dokladnie** `u-boot-nodtb.bin` plus `u-boot.dtb`
  (537 128 + 26 176 = 563 304 B, a suma kontrolna ogona zgadza sie z `u-boot.dtb`
  co do bajtu). **Drzewo urzadzen jedzie w srodku obrazu**, wiec nie ma czego
  pakowac osobno; 7870 wymaga stuba w formacie QCDT przekazanego przez `--dt`,
  my nie.
* Obraz nie jest FIT-em (pierwsze bajty to instrukcja skoku, nie `d00dfeed`),
  a na offsecie 56 siedzi `41 52 4d 64`, czyli magic obrazu jadra arm64.
  S-BOOT widzi wiec jadro i tak je laduje.
* Format kontenera bierze sie z pakietu urzadzenia postmarketOS:
  `header_version=1`, strona 2048, offsety jadra `0x8000`, ramdysku `0x1000000`,
  second `0xf0000000`, tagow `0x100`, metoda `heimdall-bootimg`, partycja
  `BOOT`. Pakiet nie podaje bazy, wiec zostaje domyslna narzedzia.
* `deviceinfo_bootimg_append_seandroidenforce="true"`, czyli do obrazu trzeba
  **dopisac na koncu `SEANDROIDENFORCE`**, inaczej S-BOOT go odrzuca. Latwo to
  przeoczyc, a objawem jest telefon, ktory po prostu nie startuje.

### Co z tego zostalo WYKONANE

**Dokumentacja zbudowana.** Sphinx 8.1.3 z zaleznosciami z `doc/sphinx/requirements.txt`
w osobnym srodowisku `~/.uboot-docs` (systemowy Python nietkniety; doszedl tylko
pakiet `fontconfig`, bo `doc/conf.py` U-Boota wola `fc-list` i bez niego build
pada na etapie konfiguracji, co NIE MA zwiazku z nasza strona). Wynik: kod
wyjscia 0, **zero ostrzezen dotyczacych naszych stron**, strona
`board/samsung/exynos-mobile/exynos9820.html` powstala i jest podlinkowana ze
spisu tresci rodziny, a dyrektywy `prompt` wyrenderowaly komendy.

**Obraz rozruchowy zbudowany i zweryfikowany**, `D:/S10Plus-pmos/boot-uboot-nasz.img`
(602 128 B po dolozeniu ekranu; 567 312 B w pierwszej wersji, bez niego). Dowody
odczytane z samego obrazu, nie z komendy, ktora go zrobila: magic `ANDROID!`;
jadro 598 168 B pod `0x10008000` (baza domyslna `0x10000000` plus offset
`0x8000`); brak ramdysku; tagi pod `0x10000100`; strona 2048; `header_version` 1;
**sha256 jadra w obrazie zgadza sie z `u-boot.bin` co do bajtu**
(`83e71db70a15e3ba...`); na koncu pliku literalne `SEANDROIDENFORCE`.

Pakowanie przestalo byc czynnoscia reczna: robi je `scripts/pack-uboot-odin.sh`,
bo kazda zmiana w bootloaderze wymaga przejscia tej samej sciezki, a kazdy jej
etap ma wlasna pulapke (naglowek v1 i strona 2048, ogon `SEANDROIDENFORCE`
doklejany PO `mkbootimg`, `tar --format=ustar` zamiast domyslnego gnu, plik
w srodku nazwany `boot.img`, suma md5 DOPISANA do tara a nie obok niego).

Pakowanie ujawnilo blad w pierwszej wersji tej strony: pakiet urzadzenia ustawia
takze `--os_version` i `--os_patch_level`, a procedura ich nie wymieniala.
Poprawione, dokumentacja przebudowana, nadal bez ostrzezen.

### Czego NADAL nie wykonano

**Wgrania na telefon.** W chwili pisania nie byl podlaczony (`adb devices`
i `fastboot devices` puste), a poza tym zapis partycji `BOOT` nieprzetestowanym
bootloaderem to decyzja wlasciciela urzadzenia, nie skryptu. Komenda jest
w dokumentacji plyty; powrot idzie przez Odina z firmware z kopii
(`D:/S10Plus-backup/2026-09-17`).

## Analiza statyczna serii bootloadera

Seria jadra ma swoj analizator od dawna, seria bootloadera nie miala ZADNEGO.
To byla najwieksza dziura w pokryciu, bo ten kod **nigdy sie nie wykonal**:
dopoki telefon nie wystartuje, analiza statyczna jest jedynym narzedziem, ktore
w ogole moze znalezc w nim blad. Kompilacja `W=1` tego nie zastepuje, bo patrzy
na skladnie, a nie na sciezki wykonania ani na adnotacje typow.

Bramka `scripts/check-uboot-analyzer.sh` wola dwa narzedzia, bo lapia
ROZLACZNE klasy: `clang --analyze` sciezki (niezainicjowana wartosc, wyluskanie
NULL-a, martwa galaz), a `sparse` typy (przestrzenie adresowe `__iomem`, endian,
typy bitowe, czyli to, co sie psuje w sterowniku dotykajacym MMIO).

### Wynik: zero znalezisk w naszym kodzie

Sprawdzone szesc plikow (piec naszych plus plyta, ktora zmieniamy). clang: **0
znalezisk**. sparse poza znanym tlem: **0**.

Zeby to cokolwiek znaczylo, harness zostal najpierw udowodniony jako zywy:
wstrzykniete w miejscu wyluskanie NULL-a zostalo zgloszone jako
`core.NullDereference`, a plik wrocil do stanu z commitu.

### Dlaczego progi, a nie zero

Trzy klasy maja w U-Boocie tlo, ktorego nie da sie usunac z poziomu naszych
plikow, wiec kazda ma osobny licznik i osobny pulap. Tlo jest ZMIERZONE, nie
zalozone:

| klasa | nasze | tlo upstreamu |
|---|---|---|
| przestrzen adresowa (`__iomem`) | 32 | `phy-exynos-usbdrd.c` ma **55**, sam rdzen `ufs-uclass.c` ma **38** |
| zasieg symbolu (`Should it be static`) | 6 | ma je kazdy sterownik, z makra `U_BOOT_DRIVER` |
| ograniczenie parsera sparse'a | 3 | literaly UTF-16 `u"..."` w `exynos-mobile.c:31`, kod plyty ktorego NIE pisalismy |

Upstream nie anotuje `__iomem` konsekwentnie, wiec wymaganie zera od naszych
plikow byloby wymaganiem czegos, czego nie robi kod obok. Wszystko POZA tymi
trzema klasami ma byc zerem i to jest wlasciwa tresc tej bramki.

### Co analiza realnie poprawila

Jedno znalezisko przeszlo w poprawke: `exynos9820_pin_ctrl` byla deklarowana
bez `static`, mimo ze jest uzywana wylacznie we wlasnym pliku, jako dane
sterownika. Najnowszy wariant upstreamu, `pinctrl-exynos850.c`, deklaruje swoja
jako `static`; starsze 7420 i 78x0 nie. Poszlismy za nowszym. Zmiana nie
kosztowala ani bajta obrazu.

### Trzy testy negatywne

| co wstrzykniete | ktory licznik ma paść |
|---|---|
| wyluskanie NULL-a | clang, znalezisk sciezkowych: 2 |
| przypisanie wskaznika `__iomem` do golego | przestrzen adresowa: 33, pulap 32 |
| `void *p = 0;` | uwagi poza znanymi klasami: 1 |

Po kazdym przywroceniu bramka wraca na zielono, a plik jest czysty wobec commitu.

### Pulapka srodowiskowa, ktora przy tym wyszla

Bramka musi siegnac do drzewa U-Boota w WSL, a `verify.sh` chodzi pod Git
Bashem. Git Bash **przerabia argumenty wygladajace na sciezki uniksowe** i
doklada do nich swoj katalog glowny, przez co `wsl.exe` dostawal
`C:/Program Files/Git/mnt/c/...`. Obejscie to podwojny ukosnik na poczatku
sciezki, opisane w samym skrypcie.

## Znak zycia na ekranie (19.09.2026)

Pytanie, ktore wymusilo te zmiane, brzmialo: **po wgraniu U-Boota skad bede
wiedziec, ze on zyje?** Bez odpowiedzi wgranie nie jest testem, tylko zamiana
dzialajacego telefonu na czarny ekran bez informacji.

### Dlaczego samo `CONFIG_VIDEO` nie wystarcza

Telefon nie ma portu szeregowego, a to, czy wstanie konsola, zalezy od zegarow,
sterownikow i drzewa urzadzen, czyli od wszystkiego, co ten port dopiero wnosi.
Gdy ekran zostaje z obrazkiem, z ktorym wstal, **dwie rozne awarie wygladaja
identycznie**: U-Boot w ogole nie wystartowal, albo wystartowal i zawisl zanim
cokolwiek napisal. Bez ich rozroznienia pierwsza probe na sprzecie da sie
podsumowac wylacznie slowem "nic".

### Co dolozone

1. **Wezel `simple-framebuffer`** w `chosen` overlaya plyty, pod `0xca000000`.
   Adres nie jest zgadniety: S-Boot tego egzemplarza podaje jadru
   `s3cfb.bootloaderfb=0xca000000` i tak zostal odczytany z urzadzenia.
   Geometria to 1440 x 3040 x 4 B, czyli `reg` o dlugosci `0x10b3000`.
2. **`CONFIG_VIDEO` i `CONFIG_VIDEO_SIMPLE`** w defconfigu, czyli konsola
   na panelu.
3. **Pasek koloru malowany najwczesniej, jak sie da**, w `board_early_init_f`.
   Kolor: nieprzezroczysta magenta `0xffff00ff` w `a8r8g8b8`. Dolne 128 wierszy,
   bo konsola pisze od gory i obie rzeczy daja sie czytac razem.
4. **Wyzwalacz DECON-a przeniesiony** z `board_init` do tego samego miejsca,
   bo panel jest command-mode: pokazuje obraz dopiero po wyzwoleniu, a w chwili
   startu bootloadera nikt go juz nie wyzwala, wiec bez tego zapisu wszystko
   malowane w framebufferze pozostaje niewidoczne.

### Dlaczego akurat `board_early_init_f`

To pozycja 947 w liscie inicjalizacji: **po** `fdtdec_setup` (926), wiec drzewo
urzadzen jest juz dostepne, i **przed** `dram_init` (986), sterownikami,
relokacja i konsola. MMU jest jeszcze wylaczone, wiec zapisy ida wprost pod
adresy fizyczne.

### Jak czytac wynik

| co widac na ekranie | co to znaczy |
| --- | --- |
| pasek, a nad nim tekst | dziala wszystko az po konsole |
| sam pasek, bez tekstu | U-Boot wystartowal, adres framebuffera i wyzwalacz dobre, zawiesilo sie cos dalej |
| obrazek, z ktorym telefon wstal | U-Boot nie wystartowal, albo ekran nie jest tam, gdzie mowi drzewo |

Tylko trzeci wiersz nie mowi nic o samym bootloaderze i od niego trzeba zaczac
diagnostyke: jesli telefon poza tym zyje, pierwszym podejrzanym jest wyzwalacz,
bo cala reszta ekranu jest czytana z drzewa, a ten jeden zapis jest stala.

### Dowod, ze kod jest w binarce

Deasemblacja `board_early_init_f`: `mov w1, #0x1281` plus
`str w1, [x0, #112]` (czyli `0x70`, `DECON_HW_SW_TRIG_CONTROL`), dalej
`mov w1, #0xffff00ff`, a przed petla komplet bramek zakresu
(`tst x0, #0x3` na podzielnosc `stride`, `umull` i `cmp` na to, czy
`stride * height` miesci sie w `reg`, `csel` na `min(height, 128)`). Te same
bajty odnalezione w spakowanym `boot-uboot-nasz.img` pod offsetami 14264
i 14476. Weryfikacja byla potrzebna, bo obraz urosl tylko o 96 B, co przy
szescdziesieciu liniach kodu wyglada jak wyciecie; wyjasnienie: stary wyzwalacz
z `board_init` zniknal na rzecz nowego.

Drzewo sprawdzone niezaleznie: `display-controller@19030000` z compatible
`samsung,exynos9820-decon` JEST w zbudowanym `u-boot.dtb`, a `reg` framebuffera
ma dlugosc dokladnie `stride * height`, wiec bramka zakresu przechodzi na styk,
a nie przez zapas.

### Czego to nadal NIE dowodzi

Ze pasek sie pokaze. Zadna czesc tej sciezki nie zostala uruchomiona na
sprzecie; kod nosi `UNVERIFIED` i tak samo opisuje to strona plyty. To jest
narzedzie do odczytania wyniku pierwszej proby, a nie wynik.

### Pulapka, ktora przy tym wyszla

Pliki drzewa U-Boota edytowane **z Windowsa przez `//wsl.localhost/...`** staja
sie wlasnoscia `root`, przez co skrypt lecacy jako `pm` pada pozniej na
`PermissionError` przy zwyklym zapisie. Objaw nie wskazuje na przyczyne, bo
blad wyglada na problem samego skryptu. Fix: `sudo chown pm:pm <plik>`, a lepiej
edytowac drzewo z poziomu WSL.

Druga, drobniejsza: `~/.uboot-docs` to katalog UKRYTY, wiec `ls ~/*venv*` go nie
znajduje i latwo postawic drugie, zbedne srodowisko Sphinksa obok istniejacego.

### Pulap ostrzezen podniesiony do 21 (22.09.2026)

Latka 0029 liczy sufit pamieci w `board_get_usable_ram_top()`, czyli w chwili,
gdy nie istnieje jeszcze zadne urzadzenie modelu sterownikow. Czyta wiec plaskie
drzewo (`fdt_path_offset`, `fdtdec_get_addr_size_auto_parent`), a checkpatch
prosi w tym miejscu o `dev_read_...`. To jest falszywe trafienie, bo ten
interfejs wymaga `udevice`, ktorego tam z definicji nie ma. Poprzednia wartosc
lezy obok, w `scripts/golden/checkpatch-uboot-warnings.max.przed-rdzeniami`.

### Pulap ostrzezen podniesiony do 22 (22.09.2026)

Latka 0031 wnosi polecenie `spinner`, a checkpatch na kazde nowe polecenie
mowi "make sure you add a test". Testow polecen U-Boot uruchamia pod sandboxem
i tylko dla polecen wbudowanych w ten obraz; `spinner` jest poleceniem PLYTY,
kompilowanym wylacznie dla `exynos-mobile`, i robi jedna rzecz: maluje po
framebufferze opisanym w drzewie tego telefonu. Sandbox ani tego polecenia nie
ma, ani nie ma czego nim sprawdzic. Poprzednia wartosc lezy obok, w
`scripts/golden/checkpatch-uboot-warnings.max.przed-obrecza`.

Pozostale piec ostrzezen z tej rundy ZNIKNELO zamiast trafic pod pulap: odczyty
drzewa w `exynos_fb_get()` i `exynos_decon_trigger()` przepisane sa na `ofnode`
(to samo dziala przed modelem sterownikow, bo `CONFIG_OF_LIVE` jest wylaczone),
a warunek kompilacji paskow rozruchu z latki 0032 to `if (IS_ENABLED(...))`
w srodku funkcji, nie `#if` wokol niej. Dowod, ze to naprawde wypada z obrazu:
`nm u-boot | grep exynos_mark_colour` nie znajduje nic, a obraz jest o 288 B
mniejszy.
