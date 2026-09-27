# R12: Bluetooth

Runda dwunasta. Cel: doprowadzić do działania układ Bluetooth telefonu, żeby
połączenie z komputerem nie musiało iść wyłącznie przez kabel.

## Co to za układ i gdzie siedzi

Telefon ma **BCM4375** (Broadcom), układ łączony: Wi-Fi po PCIe i Bluetooth po
porcie szeregowym. Te dwie strony są niezależne, więc Bluetooth można uruchomić
bez kontrolera PCIe, którego mainline dla tego SoC nie ma (`pci-exynos`
obsługuje wyłącznie `samsung,exynos5433-pcie`).

Droga do układu, warstwa po warstwie, wszystko odczytane z drzewa producenta
`sources/ds/exynos9820.dts` i z tablic zegarów `sources/ds/cmucal-sfr.c`:

| warstwa | adres albo numer | skąd wzięte |
| --- | --- | --- |
| kontroler zegarów CMU_PERIC1 | `0x10800000`, okno `0x8000` | `SFR_BLOCK(CMU_PERIC1, ...)` |
| mux portu szeregowego | `0x01c0`, bit 4 | `PLL_CON0_MUX_CLKCMU_PERIC1_UART_BT_USER` |
| dzielnik portu | `0x1814`, bity 0 do 3 | `CLK_CON_DIV_DIV_CLK_PERIC1_UART_BT` |
| bramka wewnętrzna | `0x2020`, bit 21 | `..._RSTNSYNC_CLK_PERIC1_UART_BT_IPCLKPORT_CLK` |
| bramka IPCLK | `0x2098`, bit 21 | `..._UID_UART_BT_IPCLKPORT_IPCLK` |
| bramka PCLK | `0x209c`, bit 21 | `..._UID_UART_BT_IPCLKPORT_PCLK` |
| rejestry systemowe PERIC1 | `0x10820000` | wzorzec PERIC0 (`0x10420000`) |
| rejestr trybu bloku USI | offset `0x1000` | alias `usi_uart_bt = "/usi@10821000"` |
| port szeregowy | `0x10840000`, przerwanie 408 | węzeł `uart@10840000`, `interrupts = <0 0x198 0>` |
| wyprowadzenia portu | `gpq0-0` do `gpq0-3`, funkcja 2 | grupa `uart1-bus` |
| linia włączająca układ | `gpm8-0` | grupa `bt-en` w `pinctrl@15C30000` |
| linia budzenia układu | `gpg2-0` | grupa `bt-btwake` w `pinctrl@10430000` |
| linia budzenia komputera | `gpa2-3` | grupa `bt-hostwake` w `pinctrl@15850000` |

Bank `gpq0` należy do kontrolera wyprowadzeń `alive`, nie do `peric1`, mimo że
sam port szeregowy stoi w PERIC1. To nie pomyłka: tak ma to podzielone tablica
banków producenta.

## Co ta runda wnosi

Siedem łatek, od 0074 do 0080. Przed nimi seria zyskała jeszcze dwie, których
jej brakowało: 0065 opisuje wiązania skrzynki i firmware APM, a 0073 wnosi ich
węzły do drzewa.

1. **0074** identyfikatory zegarów CMU_PERIC1 w wiązaniu (103 zegary).
2. **0075** kontroler zegarów w sterowniku: 16 muxów użytkownika, 15 dzielników,
   72 bramki, wszystko przepisane z tablic producenta przez generator.
3. **0076** rejestry systemowe PERIC1 i CMGP w wiązaniu.
4. **0077** rozpoznanie `brcm,bcm4375-bt` w wiązaniu układów Broadcoma.
5. **0078** to samo w sterowniku `hci_bcm`, bez żadnych odstępstw: dwa, które
   ten sterownik zna, dodano po pomiarze konkretnego układu, a tego nikt
   jeszcze nie mierzył.
6. **0079** opis sprzętu w drzewie SoC: kontroler zegarów, rejestry systemowe,
   blok USI w trybie portu szeregowego i sam port, razem z wyprowadzeniami.
7. **0080** włączenie portu na płycie i opis układu pod nim.

Konfiguracja jądra dostaje stos Bluetooth, magistralę urządzeń na porcie
szeregowym, protokół H4 z rozszerzeniami Broadcoma i profil urządzeń wejścia
(bo pierwszym sensownym użyciem będzie klawiatura).

## Czego świadomie nie ma

**Prędkości portu.** Sterownik bez `max-speed` zostaje na 115200 baud. Stock
Samsunga jedzie szybciej, ale liczby nie mam z pomiaru, tylko z cudzych portów,
więc wpiszę ją dopiero, gdy zobaczę, że układ w ogóle odpowiada.

**Odstępstw sterownika.** `no_early_set_baudrate`, `drive_rts_on_open`
i pozostałe są w `hci_bcm` dla konkretnych układów, po pomiarach. Wpis BCM4375
jest pusty, dopóki nie zmierzę, że czegoś potrzebuje.

**Nazwy układu w tablicy `btbcm`.** Sterownik buduje nazwę pliku firmware
z nazwy odczytanej z samego układu. Tablica `bcm_uart_subver_table` nie zna
BCM4375, więc nazwa wyjdzie zapasowa (`brcm/BCM.hcd`). Wpis dopiszę po
odczytaniu prawdziwego numeru wersji z telefonu, a nie zgadując go.

**Wi-Fi.** Wymaga napisania od zera kontrolera PCIe dla tego SoC plus obsługi
BCM4375 w `brcmfmac` (który zna 43752, 4377 i 4378, ale nie 4375). To osobna,
znacznie większa robota.

## Firmware

Układ po włączeniu zasilania umie tylko odpowiedzieć na pierwsze polecenia;
reszta, razem z własnym adresem, przychodzi z pliku łat, który host wgrywa przy
każdym starcie. Plik należy do telefonu i leży na jego partycji producenta.

Kopia zapasowa z 17 września tej partycji **nie obejmuje**: ma 20 obrazów
(rozruch, efs, klucze, radio, odzyskiwanie), a `vendor` to `/dev/block/sda26`,
1 153 433 600 B, i nie był zgrywany. Przeszukanie wszystkich skopiowanych
obrazów po ciągach `BCM4375`, `bcm4375` i `.hcd` dało zero trafień, więc na
komputerze tego pliku nie ma.

Dlatego w obrazie systemu siedzi `usr/local/bin/bt-firmware.sh`, uruchamiany
przy starcie przez usługę `bt-firmware.service`. Montuje partycję producenta
tylko do odczytu, kopiuje znaleziony plik `.hcd` do `/lib/firmware/brcm/` pod
własną nazwą i pod zapasową `BCM.hcd`, po czym ponawia próbę powiązania
sterownika z portem. Raport zapisuje do `/var/log/bluetooth-firmware.txt`.

## Co sprawdzić po wgraniu

```
cat /var/log/bluetooth-firmware.txt
dmesg | grep -iE "bluetooth|hci_uart|bcm"
ls /sys/class/bluetooth/
hciconfig -a
```

Kolejność objawów, od najniższego poziomu:

1. `ls /sys/bus/serial/devices/` pokazuje urządzenie: port szeregowy powstał,
   czyli kontroler zegarów i blok USI działają.
2. W logu jest linia `Bluetooth: hci0: BCM: chip id ...`: układ odpowiedział,
   czyli linia włączająca i wyprowadzenia są dobrze opisane.
3. W logu jest `BCM (...) build ...`: znamy numer wersji układu i można dopisać
   go do tablicy `bcm_uart_subver_table`.
4. `hciconfig -a` pokazuje adres inny niż `00:00:00:00:00:00`: firmware się
   wgrało.

Gdy port nie powstanie, pierwsze pytanie brzmi: czy zegary PERIC1 w ogóle
wstały. Odpowiada na nie `grep -i peric1 /sys/kernel/debug/clk/clk_summary`,
a nie odczyt rejestrów przez `/dev/mem`, który przy zamkniętej bramce zegarowej
albo zwraca zera, albo wiesza telefon.

## Długi zamknięte przy okazji

Roboty wokół Bluetootha nie dało się zrobić bez ruszenia generatorów, a te
wyciągnęły trzy rozjazdy, które leżały w serii:

1. **Trzy grupy wyprowadzeń** (dwie dla pamięci masowej, jedna dla magistrali
   głównego układu zasilania) były dopisane wprost do pliku, z pominięciem
   generatora. Pierwsza regeneracja je skasowała i drzewo przestało się składać.
   Wróciły do generatora razem z pełnymi komentarzami z serii.
2. **Poprawka „PLL czyta współczynniki z CON3, nie z CON0"** żyła tylko
   w pliku wynikowym, więc regeneracja ją cofnęła. Generator umie to teraz sam:
   trzy PLL-e mają offset CON3 wprost w tablicach producenta, a pozostałe sześć
   liczy się z reguły `CON3 = CON0 + 0xc`, którą te trzy potwierdzają.
3. **Pięć łatek (0063 do 0067, dziś 0063 do 0068) było zepsutych**: puste linie kontekstu bez
   wiodącej spacji i cztery błędne liczby w nagłówkach fragmentów. `git am`
   mówił na to tylko „corrupt patch at line 53". Do tego serii brakowało łatki,
   która wnosi do drzewa skrzynkę APM i firmware ACPM, chociaż generator zna ten
   etap od dawna.

Zamykają to trzy nowe bramki: `check-latki.py` (arytmetyka łatek),
`check-generatory.py` (stan końcowy każdego generowanego pliku) oraz
`odswiez-latki.py`, który tę samą różnicę umie też zapisać. Po naprawie cała
seria, 80 łatek, nakłada się na bazę czysto i daje plik w plik to, co stoi
w drzewie roboczym, a `check-gen-dts` przechodzi wszystkie 16 etapów.

Do tej listy doszły jeszcze dwie rzeczy z tej samej rodziny. Opisy wiązań
skrzynki i firmware APM siedziały w łatkach, które uczą te sterowniki naszego
układu, a `checkpatch` mówi wprost, że wiązania mają iść osobno; teraz idą
własną łatką (0065), ustawioną przed nimi. Dziewięć opisów łatek miało akapity
szersze niż 75 kolumn i zostało przezawiniętych, bez zmiany ani jednego słowa.
Po obu poprawkach serii zostaje 17 ostrzeżeń `checkpatch` przy zerze błędów:
dziesięć to „czy MAINTAINERS nie wymaga wpisu", siedem to odwołania do commitów
spoza płytkiego klonu.

## Audyt przed wgraniem

Całość przeszła audyt pięciu niezależnych kontroli (zegary, drzewo, wyprowadzenia,
sterownik, konfiguracja) plus jedna kontrola sceptyczna nad ich wynikami.
Siedemnaście znalezisk, z czego dwa blokujące. Co z tego weszło:

**Nakładające się okna rejestrów (blokujące).** Węzeł portu szeregowego brał
z drzewa producenta okno `0x100`, a okno bloku USI zaczyna się `0xc0` od tej
samej bazy. Oba sterowniki zamawiają pamięć na wyłączność, USI jako rodzic
pierwszy, więc port dostałby odmowę i nie powstałby wcale. Okno portu kończy się
teraz tam, gdzie zaczyna się okno USI, dokładnie jak w mainline dla tej rodziny
i jak w naszej własnej magistrali I2C piętro wyżej.

**Brak aliasów portów.** Sterownik bierze numer portu z aliasu, a bez niego
z licznika kolejności rozruchu. Przy jednym porcie to nie miało znaczenia, ale
ta runda dodaje drugi i numer konsoli zaczynałby zależeć od tego, który
sterownik wystartował pierwszy. Alias portu Bluetootha pojawia się dopiero
w etapie, który ten port wnosi, bo wcześniej nie ma na co wskazywać.

**Brak stanu wyprowadzeń trzech linii sterujących.** Same linie działają i bez
tego, bo sterownik wyprowadzeń ustawia funkcję pinu przy zamówieniu go jako
GPIO. Czego nie ustawia, to podciąganie i zachowanie przy uśpieniu domeny:
producent zapisuje przy każdej z tych trzech linii „zachowaj poprzedni stan"
i „bez podciągania". Teraz zapisujemy to samo.

**Brak obsługi urządzeń wejścia z przestrzeni użytkownika.** Profil `BT_HIDP`
zestawia połączenie, ale urządzenia wejścia z niego nie robi: to zadanie demona,
a ten potrzebuje węzła `/dev/uhid`. Bez tego klawiatura sparowałaby się i nie
pisała.

**Ponowienie próby po wgraniu firmware.** Skrypt ponawiał wiązanie sterownika
tylko wtedy, gdy kontrolera nie było w ogóle. Tymczasem typowy przypadek jest
inny: kontroler jest, tylko bez łat. Teraz ponawia zawsze, gdy plik właśnie
doszedł, a do raportu trafia lista nazw, których jądro naprawdę szukało.

Dwa znaleziska sceptyk odrzucił jako nierozstrzygnięte, jedno okazało się
nieaktualne (okno rejestrów było już poprawione, gdy audyt je zgłaszał), a jedno
obalił pomiar: `CONFIG_BT_HCIUART=y` miało być nieosiągalne przez trójstanową
zależność, a wychodzi `y`, bo `POWER_SEQUENCING` w tym jądrze jest `y`, nie `m`.
Odczyt z gotowej konfiguracji bije analizę zależności.

## Co zostało po tej rundzie do zrobienia

**Prędkość portu.** Po pierwszym uruchomieniu, gdy układ odpowie, trzeba dopisać
`max-speed`. Bez tego wszystko jedzie 115200 baud, czyli wgranie firmware trwa
ponad minutę przy każdym starcie, a profil dźwiękowy nie ma szans.

**Nazwa układu w tablicy `btbcm`.** Z logu wyjdzie numer wersji; po jego
odczytaniu dochodzi wiersz do `bcm_uart_subver_table` i wtedy trzeba zmienić
nazwę, pod którą skrypt kopiuje firmware (dziś zapasowa `BCM.hcd`).

**Bootloader nie ma zegarów PERIC1.** Kopia drzewa, którą nosi seria
bootloadera, jest teraz bajt w bajt tą samą co w jądrze, czyli opisuje też port
Bluetootha i jego kontroler zegarów. Sterownika CMU_PERIC1 po stronie
bootloadera nie ma, więc przy następnym budowaniu trzeba sprawdzić, czy jego
rozruch tego nie zauważa; poprzednim razem brak kontrolera zegara blokował
urządzenie po cichu, a objaw wychodził kilka warstw dalej.

**Bramka RSTNSYNC.** Bramka `gout_peric1_clk_peric1_uart_bt_clk` nie ma flagi
chroniącej przed wygaszeniem, a żaden węzeł drzewa jej nie zamawia. Dziś to nie
szkodzi, bo wiersz rozruchowy ma `clk_ignore_unused`, a tablice producenta
pokazują ją jako gałąź równoległą do tej, którą port faktycznie bierze. Do
sprawdzenia na telefonie jednym odczytem `clk_summary`, zanim ten parametr
kiedyś zniknie.

