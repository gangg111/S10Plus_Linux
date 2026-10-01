# R15: modem s5000ap, czyli co naprawde znaczy "karta SIM"

## Punkt wyjscia: SIM nie jest po stronie procesora aplikacyjnego

Karta SIM tego telefonu jest elektrycznie przylaczona do **modemu**, nie do
procesora, na ktorym dziala nasze jadro. Nie istnieje wiec zaden pomiar
obecnosci karty, ktory dalby sie wykonac przed uruchomieniem modemu, i nie da
sie zbudowac taniego celu posredniego dotykajacego SIM wczesniej niz na samym
koncu drogi. "Wdrozenie karty SIM" znaczy w praktyce "uruchomienie procesora
komunikacyjnego", i tak trzeba to zadanie czytac.

Modem to `s5000ap` (Exynos Modem 5100). Rozmawia z procesorem aplikacyjnym
przez **pamiec dzielona i skrzynke pocztowa**, nie przez PCIe; drugi kontroler
PCIe tego SoC jest w drzewie producenta wylaczony wlasnie dlatego.

## Werdykt

**Dzialajaca karta SIM i LTE sa poza zasiegiem tego portu.** Brakuje nie
jednego elementu, tylko calego pietra, i to z dwoch niezaleznych powodow.

**Powod pierwszy: nie ma sterownika.** Mainline nie zna zadnego modemu
Samsunga na Exynosie. Stos producenta to okolo czterdziestu plikow, z ktorych
sam `link_device_shmem.c` ma 106 036 bajtow, a zasada 2 tego projektu zabrania
przepisywania cudzego kodu. Trzeba by napisac od zera transport, kolejki,
protokol i sterowanie rozruchem.

**Powod drugi, wazniejszy: nie ma z czym rozmawiac.** Wsrod dwudziestu dwoch
kanalow modemu **nie ma kanalu AT**. Sterowanie idzie kanalami `umts_ipc0`
i `umts_ipc1` protokolem Samsung IPC w wersji `0x32`, ktorego zaden wolny stos
nie mowi: `ModemManager` i `oFono` nie maja do niego wtyczki, `libsamsung-ipc`
obsluguje modemy sprzed dekady, a Replicant, ekipa z najwieksza wiedza o tych
ukladach, oficjalnie nie ma 4G i przeniosla sie na inny sprzet. We wszystkich
portach postmarketOS na Exynosie, takze tych dojrzalych od lat, modem jest
oznaczony jako zepsuty. To nie jest luka do zalatania, tylko teren, na ktorym
nikt nie byl.

**Realistyczny sufit ambicji** to dowod, ze procesor komunikacyjny startuje
i wykonuje oryginalne firmware z naszej wlasnej kopii partycji radio. Odczyt
stanu karty lezy dwa etapy dalej i ma skale nieznana.

## Liczby sprzetowe, odczytane z plikow lezacych lokalnie

Wszystkie ponizsze pochodza ze zrodel producenta dodanych do `sources/ds`
przy tej rundzie, wiec kazda daje sie zacytowac w serii.

### Skrzynka pocztowa AP <-> CP

Blok `MCU_IPC` pod **0x15920000**, dlugosc **0x180**, jedno przerwanie
**SPI 41**, region `mcu,id = 0` (MCU_CP).

| rejestr | offset | rola |
|---|---|---|
| MCUCTLR | 0x0 | bit 0 to reset programowy |
| INTGR0 | 0x8 | wyzwalanie, strona CP |
| INTCR0 | 0xc | kasowanie zgloszen od CP |
| INTMR0 | 0x10 | maska zgloszen od CP |
| INTSR0 | 0x14 | stan zgloszen od CP, bity 16..31 |
| INTMSR0 | 0x18 | stan po masce |
| INTGR1 | 0x1c | wyzwalanie w strone CP |
| INTCR1 | 0x20 | kasowanie |
| INTMR1 | 0x24 | maska |
| INTSR1 | 0x28 | stan |
| INTMSR1 | 0x2c | stan po masce |
| ISSR0.. | 0x80 co 4 B | rejestry wiadomosci |

Kierunek AP do CP: zapis `1 << numer` do `INTGR1`. Kierunek CP do AP: odczyt
`INTSR0` maskowany `0xFFFF0000`, kasowanie tej samej wartosci w `INTCR0`.

Pola `mbx_*` z drzewa plyty to **numery rejestrow ISSR**, adres wynosi
`0x80 + 4 * numer`. Dla naszej plyty: `ap2cp_msg` 0 (0x80), `cp2ap_msg` 1
(0x84), `ap2cp_united_status` 2 (0x88), `cp2ap_united_status` 3 (0x8c).
Pola `sbi_*` to maska i pozycja bitowa **wewnatrz** tego rejestru.

Zrodlo: `regs-mcu_ipc.h`, `mcu_ipc.c`, wezel `mailbox_cp` i pola `mbx_*`
w drzewie plyty producenta.

### Domena modemu w jednostce zasilania

Baza **0x15860000**. Sekwencja wlaczania to dokladnie cztery kroki:

1. zapis bitu 3 do `CP_CTRL_S` **0x3014**,
2. zapis bitu 0 do `CP_CONFIGURATION` **0x3000**,
3. czekanie, az `CP_STATUS` **0x3004** bit 0 bedzie 1,
4. czekanie, az `CP_IN` **0x3024** bit 4 bedzie 1.

Zatrzymanie to zapis 0 na bit 0 w 0x3000 i czekanie na 0 w 0x3004. Zwolnienie
resetu to zapis 1 i te same dwa oczekiwania co w krokach 3 i 4.

**Uwaga rozstrzygajaca, dopisana po krytyce planu:** przez swiat bezpieczny
idzie **wylacznie** `CP_CTRL_S` (0x3014). Rejestry 0x3000, 0x3004 i 0x3024 sa
zwyklymi rejestrami jednostki zasilania. Bity potwierdzenia reaguja na zapis
do 0x3000, a nie do 0x3014, wiec **komplet oczekiwanych bitow moze sie ustawic
mimo ze zapis do 0x3014 zostal po cichu polkniety**. Kazdy eksperyment
rozstrzygajacy "czy domena jest nasza" musi porownywac zapis wprost do 0x3014
z odczytem tego samego rejestru przez wywolanie do firmware, a nie patrzec na
bity potwierdzenia.

Zrodlo: `pmucal_cp_exynos9820.h`.

### Wyzwalacz startu na tej konkretnej plycie

Nie `cal_cp_init`, tylko **zapis wartosci 1 pod 0x15020000** (`ap2cp_cfg_addr`
z drzewa plyty), z natychmiastowym odczytem weryfikujacym. Sciezka przez
`cal_cp_init` dotyczy plyt bez tego rejestru.

### Rozruch przez firmware bezpieczenstwa

`SMC 0x82000700` z trzema parametrami, opakowane w `SMC 0x82001011`
wlaczajace i wylaczajace blok kryptograficzny, ktory sprawdza podpis. Gdy
firmware zwroci **0x100** (sprawdzanie niezakonczone), sterownik odpytuje
w petli trybem **0x8**, najwyzej **0x1000** razy.

Tryby: 0 zwykly rozruch (parametry to rozmiary bootloadera CP i obrazu
glownego), 1 zrzut, 2 ponowna inicjalizacja, 7 tryb reczny.

### Uklad pamieci dzielonej

Baza `modem_if` to **0xf0000000** (185 MB). Podzial z wezla `shmem`
producenta: obszar CP 0x7800000, potem 0x800000, potem 0x3200000, obszar IPC
pod offsetem **0xb200000** o rozmiarze 5 MB, czyli **0xfb200000**, i koniec
calosci dokladnie tam, gdzie zaczyna sie `cp_ram_logging` (0xfb900000).

**To jest jedyna czesc modemu, ktora w naszym drzewie jest juz zrobiona
i zweryfikowana:** trzy rezerwacje pamieci zgadzaja sie co do bajtu
z tablica zaszyta w naszej wlasnej kopii partycji radio, a pilnuje ich
`scripts/check-memory-map.py`.

### Protokol

`mif,link_attrs = 0x7c9` znaczy: ruch IPC przez kolejki pierscieniowe (SBD),
a rozruch i zrzut przez stary interfejs pamieciowy z walidacja wartosci
rozpoznawczej. Pierwsze 64 kB obszaru IPC to komendy i deskryptory, bufory
zaczynaja sie dalej.

Warstwa ramkowania **nie jest tajemnica**: naglowek ma 4, 5 albo 6 bajtow
zaleznie od pol sterujacych, pierwszy bajt to konfiguracja, drugi numer
kanalu. Opisuje to `sipc5.h`, ktory teraz lezy lokalnie. Tajemnica jest
warstwa **znaczenia komend** w wersji 0x32, nie sposob pakowania ramek.

Komendy skrzynki: start inicjalizacji 0x1, telefon wystartowal 0x8, awaria
0x7 i 0x9. Wartosci rozpoznawcze pamieci: rozruch `0x424F4F54`, zrzut
`0x44554D50`, **awaria `0xDEADDEAD`**.

### Czego modem od nas NIE potrzebuje

W calym sterowniku producenta dla tego wariantu nie ma ani jednego wywolania
zegara, regulatora ani zarzadzania energia, a w tablicach kalibracyjnych SoC
nie ma bloku `CMU_CP`. Modem nie wymaga wiec od naszego jadra ani jednego
zegara.

## Trzy rzeczy, ktore krytyka planu odwrocila

**1. Nasz bootloader nie ma kanalu zwrotnego do PC.** Konsola naszego U-Boota
to **panel telefonu**, a fastboot oddaje hostowi status powodzenia, nie tresc
wypisana przez polecenie. Pomysl "wlaczmy polecenia pamieci i czytajmy
rejestry z PC bez wgrywania" jest fikcja: wynik zobaczy tylko czlowiek
patrzacy na ekran. Zeby to naprawic, trzeba napisac **wlasna obsluge polecenia
fastboot**, ktora wklada odczytana wartosc do komunikatu odpowiedzi. To jest
osobny etap z wlasnymi wgraniami, a nie kilka linii w konfiguracji.

**2. Skreslenie bloku DIT jest hipoteza, nie ustaleniem.** Zalezność w plikach
konfiguracyjnych sugeruje, ze do kanalow prowadzacych do karty DIT nie jest
potrzebny, ale konfiguracja plyty producenta ma go **wlaczonego**, czyli
jedyny znany dzialajacy rozruch tego modemu odbywa sie z DIT. Zanim uznamy to
za skreslone, trzeba sprawdzic, czy wszystkie odwolania do jego rejestru
systemowego sa pod ta opcja.

**3. Kolejnosc rozruchu ma wiecej krokow, niz wygladalo.** Pierwszym krokiem
jest wyzerowanie rejestrow wiadomosci i ustawienie pol startowych, w tym pola
**`ds_detect`, ktorym procesor aplikacyjny mowi modemowi, ile jest slotow
karty**. Pominiecie go uderza dokladnie w cel calego zadania. Zapis pod
0x15020000 nastepuje u producenta **przed** przeslaniem obrazu, nie po.

## Czego ta runda nie obiecuje

- Dzialajacej karty SIM, polaczen, SMS ani transmisji danych.
- Ze firmware bezpieczenstwa przyjmie wywolanie rozruchowe z lancucha
  zaczynajacego sie od naszego U-Boota. To jedyny warunek rozstrzygajacy
  i nie da sie go sprawdzic inaczej niz na sprzecie.
- Ze modem po uruchomieniu zobaczy jakakolwiek siec: dane kalibracyjne
  i tozsamosc pochodza z obszaru, ktorego w ogole nie ma na partycji radio.
- Wspolpracy z gotowymi narzedziami telefonii. Modem nie wystawia kanalu
  tekstowego ani zadnego standardowego protokolu.
- Skrotu przez zamknieta warstwe producenta: istniejacy port innego systemu
  dla tego telefonu jedzie na jadrze producenta i calym userspace Androida,
  wiec jest rozlaczny z naszym portem.
- Jakiejkolwiek modyfikacji firmware modemu. Podpis sprawdza swiat bezpieczny,
  a bezpiecznik przeciwcofkowy jest przepalony.

## Runda 28.09.2026: HW-46 rozstrzygniete, rejestry domeny CP niedostepne wprost

**HW-46 MA ODPOWIEDZ: domena modemu jest WYLACZONA.** Sonda `modem_sonda`
(ioremap bloku PMU, odczyt `CP_STATUS` 0x15860000+0x3004) zwrocila `0x00000000`,
czyli bit 0 = 0. Pierwszy stopien rozruchu **nie** zostawia modemu zasilanego,
wiec sekwencja producenta (wykonywana tylko w stanie zero) nie jest pomijana:
trzeba wykonac pelne wlaczenie przez `CP_CONFIGURATION` bit 0, potem czekac na
`CP_STATUS` bit 0 i `CP_IN` bit 4, i dopiero potem zwalniac reset przez
`CP_CTRL_S` bit 3.

Kod sondy: `tools/phone/modem-sonda/modem_sonda.c`, zrzut rejestrow przez
`/sys/kernel/debug/modem_sonda/rejestry`, zapis przez `.../zapisz`
(tylko znane offsety domeny CP).

### Sprostowanie: wezel PMU JEST w naszym drzewie i sterownik sie zwiazal

Pierwsza wersja tego wpisu twierdzila, ze w `exynos9820.dtsi` brakuje wezla
kontrolera PMU. **To bylo nieprawda** i wynikalo z mojego pobieznego
przegladniecia pliku. Wezel stoi w linii 909:

```
pmu_system_controller: system-controller@15860000 {
	compatible = "samsung,exynos9820-pmu", "samsung,exynos7-pmu", "syscon";
	reg = <0x15860000 0x10000>;
	poweroff: syscon-poweroff { offset = <0x030c>; }   /* PS_HOLD_CONTROL */
	reboot:   syscon-reboot   { offset = <0x3a00>; }   /* SWRESET */
}
```

Dowod zwiazania sterownika (odczyt z zywego telefonu):

```
/sys/bus/platform/devices/15860000.system-controller
/sys/bus/platform/devices/15860000.system-controller:reboot-mode
/sys/bus/platform/devices/15860000.system-controller:syscon-poweroff
/sys/bus/platform/devices/15860000.system-controller:syscon-reboot
/sys/class/reboot-mode/syscon-reboot-mode
```

Czyli regmap PMU dziala, a `syscon-reboot` i `reboot-mode` na nim stoja i sa
uzywane przy kazdym restarcie tego telefonu. **Blok PMU nie jest zamkniety.**
Poprzednia wersja tego wpisu sie mylila takze w tym punkcie.

### Co jest prawdziwa przeszkoda: rejestry domeny CP (0x3000..0x3028) nie odpowiadaja

Dwa niezalezne przebiegi, dwa rozne wejscia, ten sam objaw:

| Przebieg | Wejscie | Wynik |
|---|---|---|
| 1 (starszy rozruch, `teegris.ko` zaladowany) | `readl(0x15860000+0x3004)` | zwrocilo `0x00000000`, bez bledu |
| 2 (czysty rozruch) | `readl(0x15860000+0x3004)` w `init` | `synchronous external abort`, ESR `0x96000010` |
| 2 | `readl` petli po 0x3000..0x3028 w `rejestry_show` | ten sam wyjatek, tym razem w `cat` |

Wyjatek jest **zewnetrzny** (typ 0x10 = External abort, not on translation
table walk), czyli to nie blad adresu, tylko odpowiedz szyny: urzadzenie pod tym
adresem nie odpowiada na dostep przez `ioremap`+`readl`.

Do tego `clk_summary` pokazuje, ze wszystkie zegary `gout_apm_*` maja
`enable count = 0` i nie maja konsumenta.

**Wniosek:** PMU jako calosc jest dostepny przez syscon, ale **rejestry domeny
modemu wymagaja czegos, czego nasz dostep nie ma** (otwartego zegara bloku APM,
wlaczonej domeny zasilania albo sciezki przez firmware). Nie jest to blad sondy
i nie da sie tego obejsc zapisem do `CP_CONFIGURATION`, bo nie mamy jak
odczytac potwierdzenia.

**Hipoteza sprawdzona 28.09.2026 i OBALONA.** Test: `insmod teegris.ko` (rc=0,
`/dev/tzdev` obecne, licznik `tzdev_iwi_event` rosnie, czyli swiat bezpieczny
zyje), zaraz potem sonda. Wynik: `insmod sonda rc=139` i ten sam
`synchronous external abort` w `readl`, tym razem z `teegris` na liscie modulow.
Czyli **zywy swiat bezpieczny nie odblokowuje rejestrow domeny modemu**.

### Trzy bloki, trzy proby, jeden objaw (i to jest wynik tej rundy)

Po odkryciu, ze na tej plycie rozruch idzie sciezka `ap2cp_cfg_ioaddr`
(`modem_ctrl_s5000ap.c`, `s5000ap_on`), a nie przez sekwencje PMU, sprawdzilem
trzy rozne miejsca. Wszystkie koncza sie **`synchronous external abort`,
ESR `0x96000010`** (typ 0x10 = External abort, czyli szyna, nie blad adresu):

| Blok | Adres | Wynik |
|---|---|---|
| rejestry domeny CP w PMU | `0x15860000 + 0x3000..0x3028` | wyjatek, dwa razy (bez i ze swiatem bezpiecznym) |
| wyzwalacz rozruchu | `0x15020000` | wyjatek przy pierwszym `readl` |
| skrzynka MCU_IPC | `0x15920000` | wyjatek |

Do tego trzeci test, ktory mial wykluczyc bramki zegarowe: modul otworzyl przez
`clk_prepare_enable` szesnascie bramek APM z mainline'owego sterownika
(`gout_apm_lhs_axi_d_apm_i_clk`, `gout_apm_lhs_axi_p_apm_i_clk`,
`gout_apm_xiu_dp_apm_aclk`, `gout_apm_mailbox_ap_ap_pclk`,
`gout_apm_mailbox_ap_cp_pclk`, `gout_apm_sysreg_apm_pclk` i inne) i ponowil
odczyt. **Nadal wyjatek.** Czyli zamkniete bramki zegarowe nie sa przyczyna.

### Rozstrzygniecie: z U-Boota tez nie ma dostepu (pomiar uzytkownika, 28.09.2026)

Ostatnia droga byla przez bootloader, bo chodzi w innym kontekscie niz Linux:
bez zarzadzania energia i bez `ioremap`. Zbudowalem kanal zwrotny
(`fastboot oem peek`, commit 41) i uzytkownik wgral obraz na probe.

**Wynik: `oem board: peek: 0` (rejestr PMU) ZAWIESZA U-Boota.** Czyli bootloader
nie ma lepszego dostepu do tych blokow niz Linux. Kazda kolejna proba to kolejny
reset telefonu, wiec **badanie jest zamkniete i nie nalezy go powtarzac**.

To domyka pytanie z trzech poprzednich tabel: blokada nie jest wlasciwoscia
kontekstu, z ktorego czytamy (Linux z `ioremap`, Linux z otwartymi bramkami
zegarowymi, czy U-Boot przed kernelem). Jest wlasciwoscia sprzetu i firmware'u:
te bloki odpowiadaja dopiero po przygotowaniu przez lancuch rozruchowy
producenta, ktorego nie mamy.

**Decyzja uzytkownika:** czeka z instalacja czystego bootloadera (menu-panel,
bez `peek`) do zakonczenia badania modemu. Kodu `peek` **nie usuwamy z drzewa**,
zeby nie powtarzac pracy, gdyby kiedys byl potrzebny do czegos innego albo gdyby
trafil sie inny egzemplarz. **Obrazu `boot-uboot-peek.img` NIE wgrywamy.**

**Co jest ustalone o stanie bloku APM (z `clk_summary`):**

```
mout_cmu_apm_bus   1  1  400000000   (wlaczony)
gout_cmu_apm_bus   1  1  400000000
dout_cmu_apm_bus   2  2  400000000   konsument: 15800000.clock-controller
dout_apm_bus      10 10  400000000   (dziesieciu konsumentow)
gout_apm_apbif_pmu_alive_pclk  0  0  (bez konsumenta)
gout_apm_apbif_rtc_pclk        0  0  (bez konsumenta)
```

Blok APM **zyje** (RTC dziala, PMU dziala, `syscon-reboot` na nim stoi), ale
jego bloki peryferyjne zwiazane z modemem nie odpowiadaja na dostep z Linuksa.

**Wniosek tej rundy:** na tym telefonie **nie ma dostepu z Linuksa do blokow
modemu** - ani do rejestrow domeny, ani do wyzwalacza rozruchu, ani do skrzynki.
W Androidzie dziala to dlatego, ze firmware i pierwszy stopien rozruchu
przygotowuja te bloki przed kernelem. Nasza droga nie przechodzi tamtedy, wiec
kazdy dostep konczy sie wyjatkiem zewnetrzym, a nie bledem adresu.

To zamyka droge "modem startuje z naszego jadra" w obecnym ksztalcie. Dalsze
kroki wymagalyby albo sciezki przez firmware (SMC producenta, ktorego sygnatury
nie znamy dla tych blokow), albo przygotowania blokow przez bootloader - czyli
pracy w U-Bocie, gdzie mozna ustawic rejestry przed kernelem.

**Uwaga do komentarza w `exynos-pmu.c`** („PMU registers here are writable from
the kernel, so no secure path"): jest prawdziwy dla **rejestrow rdzeni** (cpuhp),
a dla **domeny modemu** trzy niezalezne pomiary go nie potwierdzaja.

**Sufit bez zmian:** to dalej „modem startuje", nie „karta dziala".

## Runda 28.09.2026 (c.d.): kanal zwrotny do U-Boota, `fastboot oem peek`

Wniosek z trzech blokow byl taki, ze dalsza droga prowadzi przez U-Boota, bo on
chodzi w innym kontekscie niz Linux: bez zarzadzania energia i bez `ioremap`.
Przeszkoda byla znana od 21.09: **U-Boot nie ma kanalu zwrotnego do PC** - jego
konsola to panel telefonu, a fastboot oddaje hostowi tylko OKAY/FAIL. Zeby to
obejsc, trzeba dopisac obsluge polecenia.

**Zrobione (commit 41 serii U-Boota, `484ea996`, latka
`patches-uboot/0041-...patch`):** w `board/samsung/exynos-mobile/exynos-mobile.c`
nadpisany slaby hook `fastboot_oem_board()`, ktory upstream zostawia wlasnie na
takie rzeczy, plus `CONFIG_FASTBOOT_OEM_BOARD=y` w defconfigu. Efekt:

```
fastboot oem peek
```

Odczytuje osiem rejestrow i podaje je jako linie `INFO` do PC, a nie na ekran:
bramke APM `+0x2018` (punkt odniesienia), `ap2cp_cfg`, `MCUCTLR` i `INTSR0`
skrzynki oraz `CP_CONFIGURATION`, `CP_STATUS`, `CP_CTRL_S`, `CP_IN` domeny.
**Tylko odczyt**, zaden zapis nie jest wykonywany.

Jak U-Boot nie ma jak czegos pokazac, to jest teraz jak. To nie jest tricks
na jeden raz: kazdy nastepny odczyt rejestru da sie dodac do tej samej tabeli.

**Stan zbudowania:** `u-boot.bin` 805 728 B, sha256
`6687e3dd0cf30f027eb8cad5e97bed959109bc2f656f0fdb670456485b452dcf`.
Obraz do wgrania `D:\S10Plus-pmos\boot-uboot-peek.img` (808 960 B, naglowek
`ANDROID!` przepisany z `boot-uboot-nasz.img` co do pola, `kernel_size`
zaktualizowany), paczka Odina `D:\S10Plus-pmos\uboot-peek.tar.md5` (819 232 B,
md5 doklejony na koncu, sprawdzony).

**Uwaga o poprzednim obrazie:** `u-boot.bin` lezacy w drzewie byl z 24.09 16:48,
a ostatni commit serii z 24.09 21:00. Nowy obraz zawiera oba, wiec przy okazji
nadgania tez drugi prog termiczny w DT.

**Czego ten krok nie rozstrzyga:** czy bloki modemu odpowiadaja z U-Boota.
To jest wlasnie pytanie, na ktore `oem peek` ma odpowiedziec, i nie da sie go
sprawdzic inaczej niz wgraniem obrazu.

## Stan po tej rundzie

Zrobione: rozpoznanie zamkniete, liczby sprzetowe odczytane i **przypiete
lokalnie** (jedenascie plikow producenta w `sources/ds`, opisane w
`SOURCES.md`, przypiete suma kontrolna), plan obalony przez krytyke
i poprawiony, cztery pytania sprzetowe otwarte jako HW-46 do HW-49.

Nie zrobione i swiadomie nietkniete: ani jedna linia sterownika. Nastepny
krok wymaga decyzji, czy w ogole wchodzic w droge, ktorej sufitem jest
"modem startuje", a nie "karta dziala".
