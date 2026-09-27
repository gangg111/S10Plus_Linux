# R14: Wi-Fi

Runda czternasta. Cel: uruchomić drugą połowę układu łączności, tę na
magistrali PCIe. Bluetooth (runda R12) wisi na porcie szeregowym i jest
niezależny; Wi-Fi wymaga kontrolera PCIe, którego mainline nie ma dla żadnego
Exynosa nowszego niż 5433, ani dla Tensora gs101.

**Stan na 23.09.2026: działa na telefonie.** Łącze PCIe wstaje przy
pierwszej próbie, `brcmfmac` uruchamia na BCM4375B1 obraz producenta,
`wlan0` powstaje sam przy każdym rozruchu, a skan widzi sieci na 2,4 i 5 GHz.
Do tego potrzebne były cztery łatki więcej (0101–0104, niżej) i firmware
w initramfs. Łączy się z WPA2 samo przy starcie: 5 GHz, 270 Mbit/s,
około 90 Mbit/s pobierania z internetu. Pomiar: `measurements/2026-09-23-wifi/`. 6 GHz ten telefon nie
ma: kalibracja modułu nie zawiera ani jednego parametru dla tego pasma.

## Gdzie to siedzi

| warstwa | adres albo numer | skąd wzięte |
| --- | --- | --- |
| kontroler (ELBI) | `0x13ed0000`, okno `0x1000` | węzeł `pcie0@13ED0000` producenta |
| rejestry DesignWare (DBI) | `0x13f00000`, `0x1000` | to samo |
| przestrzeń konfiguracji | `0x14ffe000`, `0x2000` | to samo |
| warstwa fizyczna, część cyfrowa (PCS) | `0x13ee0000` | to samo |
| warstwa fizyczna, część analogowa (PMA) | `0x13ef0000` | to samo |
| przerwanie | 253 | `interrupts = <0 0xfd 0>` |
| rejestry systemowe | `0x13c11044`, dwa słowa | okno `sysreg` węzła |
| izolacja w jednostce zasilania | `0x71c`, bit 0 | `PCIE_PHY_CONTROL` w sterowniku producenta |
| linia zegara żądania | `gpf2-0`, funkcja 2 | grupa `pcie0_clkreq` |
| linia resetu układu | `gpf2-2`, wyjście | grupa `pcie0_perst` |
| identyfikator urządzenia PCI | `0x4475` | `BCM4375_D11AX_ID` w `bcmdevs.h` |
| identyfikator układu | `0x4375` | `BCM4375_CHIP_ID` tamże |
| baza pamięci układu | `0x170000` | `CR4_4369_RAM_BASE`, którą 4375 bierze w `dhd_pcie.c` |

Drugi kontroler (`pcie1` pod `0x13120000`) zostaje poza serią: na tej płycie
drzewo producenta trzyma go wyłączonym, bo nic do niego nie podłączono.

## Trzy rzeczy, które skróciły drogę

1. **Rejestry sterujące zgadzają się z mainline.** Nagłówek producenta ma
   `PCIE_IRQ_PULSE 0x000`, `PCIE_SW_WAKE 0x018`, `PCIE_APP_LTSSM_ENABLE 0x02c`
   i `PCIE_ELBI_RDLH_LINKUP 0x074` pod tymi samymi offsetami, których używa
   sterownik Exynosa 5433. Ta część przeniosła się bez zmian.
2. **Zegary już były.** Cały blok `CMU_FSYS1` powstał przy pamięci masowej,
   a w nim siedzi komplet zegarów PCIe Gen2. Rejestry systemowe pod
   `0x13c11044` to dwa słowa wewnątrz opisanego już `sysreg_fsys1`.
3. **Kontroler nie jest w przełączalnej domenie zasilania**, więc odpada cała
   warstwa, która przy wyświetlaczu kosztowała osobną rundę.

## Czego z mainline wziąć się NIE dało

**Ścieżka resetu jest inna.** Sterownik 5433 zna cztery rejestry resetu:
`0x01c`, `0x020`, `0x024` i `0x028`. Na tym układzie żadnego z nich nie ma,
a pod `0x020` leży rejestr odczytu poziomu przerwań. Reset rdzenia to tutaj
jedno słowo pod `0x1d0`. Przeniesienie tamtej funkcji dosłownie zapisywałoby
zera do rejestru przerwań.

**Nie ma bocznego kanału do rejestrów konfiguracyjnych.** Sterownik 5433
owija każdy dostęp do nich ustawianiem bitu 21 w `0x11c` i `0x120`. W całym
nagłówku producenta nie ma ani jednego z tych symboli, a kontroler dostaje
osobne okno. Haki `read_dbi` i `write_dbi` w naszym sterowniku po prostu nie
istnieją.

## Dlaczego warstwa fizyczna jest w tym samym sterowniku

Mainline zwykle wydziela ją do `drivers/phy`. Tutaj się nie da bez oddawania
komuś okna, które już ma właściciela: **trzy resety, których ta warstwa
potrzebuje, to rejestry kontrolera** (`0x288`, `0x28c`, `0x290`), pulsowane
w środku zapisywania jej tablic, a leżą w oknie, które zajmuje rdzeń
DesignWare. Sekwencja wygląda tak i nie da się jej rozciąć:

1. dwa słowa rejestrów systemowych (tryb PCS i włączenie linii),
2. puls resetu `0x288`,
3. 48 bajtów tablicy wspólnej i 80 bajtów tablicy nadajnika i odbiornika,
4. osiem pojedynczych zapisów do części cyfrowej,
5. puls resetu `0x290`, puls resetu `0x28c`, odczekanie 100 mikrosekund,
6. przestawienie układu odzysku zegara.

Obie tablice to wersja producenta dla kanału zerowego przy zegarze
odniesienia 26 MHz. Nie zależą od rewizji krzemu: w całym pliku kalibracji nie
ma ani jednego odwołania do wersji układu.

**Jedno okno zamiast dwóch.** Wiązanie DesignWare wymienia wszystkie
dopuszczalne nazwy okien i zna dokładnie jedną nazwę dla warstwy fizycznej.
Oba bloki leżą obok siebie, więc drzewo podaje jedno okno od `0x13ee0000`
o długości `0x11000`: część cyfrowa na jego początku, analogowa 64 kilobajty
dalej.

## Co wnosi runda

Cztery łatki, 0084 do 0087:

1. **0084** opis wiązania kontrolera.
2. **0085** sterownik, razem z warstwą fizyczną i podglądem historii łącza.
3. **0086** opis sprzętu: kontroler, pięć zegarów, dwa wyprowadzenia.
4. **0087** rozpoznanie BCM4375 w `brcmfmac`: sześć linii wpisów, trzy liczby
   ze źródeł producenta.

Po pierwszym uruchomieniu doszły trzy, bo bez nich nic by nie ruszyło:

5. **0101** wiązanie dopuszcza `vpcie3v3-supply`.
6. **0102** sterownik włącza to zasilanie w probe, przy wciśniętym PERST#
   (linia WL_REG_ON, `gpg0-5`: bez niej połowa Wi-Fi układu nie ma
   zasilania i łącze stoi w Detect); zwalnia PERST# przed konfiguracją PHY,
   w kolejności `exynos_pcie_establish_link()` producenta; odmawia MSI
   (pusta `msi_init` plus `bridge->msi_domain`), bo płyta nie ma
   podpiętego przerwania MSI, a producent jedzie na INTx.
7. **0103** drzewo płyty: regulator stały na `gpg0-5` ze 100 ms na start
   (tyle czeka producent), podany kontrolerowi, i włączony `pcie0`.
8. **0104** `brcmfmac` zapisuje słowo możliwości hosta (`host_cap`,
   pamięć współdzielona +84, tu `0x1407`), jak robi to `bcmdhd`. Bez niego
   firmware odpowiadał na polecenia, skanował i się kojarzył, ale nie brał
   ani jednego bufora odbiorczego (`msgbuf_stats`: `h2d_rx_submit rp 0,
   wp 511`), więc żadna ramka danych, nawet EAPOL, nie dochodziła, a punkt
   dostępu zrywał handshake z `reason=15`. To wygląda jak złe hasło, a nim
   nie jest.

Konfiguracja dostaje magistralę PCI, host DesignWare, nasz sterownik oraz
`brcmfmac` ze ścieżką PCIe, której dotąd nie było (był tylko SDIO).

## Podgląd, gdy łącze nie wstanie

Kontroler zapisuje trzydzieści dwa ostatnie stany maszyny treningu łącza
w rejestrach od `0x138`. To jedyne miejsce, z którego widać, jak daleko doszedł
trening. Producent wypisuje to do logu przy każdej porażce; sterownik wystawia
to przez `debugfs`, plikiem `link_history` w katalogu urządzenia. Obok stanu
łącza jest stan zasilania i stan podtrybu L1, bo łącze stojące w fazie
sondowania wygląda tak samo jak takie, które wytrenowało i spadło, a rozróżnia
je dopiero ta druga kolumna.

## Czego to jeszcze nie dowodzi

*Ten rozdział opisuje stan sprzed 23.09.2026; oba ryzyka poniżej są już
rozstrzygnięte pomiarem (`measurements/2026-09-23-wifi/`): łącze wstaje,
a obraz `bcmdhd_sta.bin_b1` działa pod `brcmfmac` jako `brcmfmac4375-pcie.bin`,
z NVRAM od rewizji B1 (`nvram.txt_CS01_semco_b1`). Ponieważ `brcmfmac` jest
wbudowany i prosi o firmware przed zamontowaniem korzenia, pliki muszą leżeć
w initramfs: `tools/phone/wszyj-firmware-wifi-w-initramfs.sh`.*

**Nic z tego nie chodziło na telefonie.** Jądro się buduje, drzewo waliduje się
wobec schematów bez zarzutu, ale żadna z tych liczb nie była sprawdzona na
sprzęcie.

**Firmware jest niepewne i to jest największe ryzyko tej rundy.** `brcmfmac`
szuka pliku `brcm/brcmfmac4375-pcie.bin`, a takiego pliku nie ma ani
w `linux-firmware`, ani w żadnym publicznym zbiorze: wszyscy, łącznie z portem
postmarketOS dla tego telefonu, używają sterownika producenta `bcmdhd`
i jego pliku `bcmdhd_sta.bin`. Oba sterowniki wywodzą się z tego samego kodu
Broadcoma i na magistrali PCIe używają tego samego protokołu pierścieniowego,
więc jest realna szansa, że obraz z telefonu zadziała po przemianowaniu, ale
**to jest hipoteza do sprawdzenia, nie fakt**. Plik leży na partycji producenta
obok firmware Bluetootha, więc wyjmie go ten sam skrypt.

**Prędkość łącza.** Drzewo podaje Gen1, tak jak producent, mimo że tablice
warstwy fizycznej są opisane jako Gen2. Podniesienie tego jest osobną zmianą,
po tym jak łącze wstanie.

## Jak to sprawdzić po wgraniu

```
dmesg | grep -iE "pcie|exynos9820|brcmf"
cat /debug/exynos9820-pcie*/link_history      # albo /sys/kernel/debug/...
lspci -vv
ls /sys/bus/pci/devices/
```

Kolejność objawów:

1. W logu jest `exynos9820-pcie ... host bridge`: sterownik wystartował,
   zegary i rejestry systemowe są dobrze opisane.
2. `lspci` pokazuje most główny: kontroler odpowiada na swojej konfiguracji.
3. `lspci` pokazuje urządzenie `14e4:4475`: łącze wstało i układ odpowiada.
4. W logu jest `brcmfmac: ... chip 4375`: sterownik rozpoznał układ.
5. Pojawia się `wlan0`: firmware się wgrało.

Gdy zatrzyma się na drugim punkcie, pierwsze pytanie to `link_history`: stan
`0x11` i wyżej znaczy, że łącze wytrenowało, niższy pokazuje, gdzie stanęło.

## Co dalej, według tego, co się przyda

**Modem nie idzie przez PCIe.** Sprawdzone w drzewie płyty: modem tego
telefonu to `s5000ap`, czyli układ wbudowany, rozmawiający przez pamięć
współdzieloną i skrzynkę; wyprowadzenia `s5100_*` w drzewie są dla
zewnętrznego modemu 5G, którego ta płyta nie ma, i właśnie dlatego drugi
kontroler PCIe jest u producenta wyłączony. Pominięcie obsługi modemu
w sterowniku PCIe niczego więc nie traci; telefonia to osobna, duża robota po
stronie skrzynki.

**Oszczędzanie energii wchodzi po uruchomieniu łącza.** Sterownik producenta
ma pełną obsługę stanów L1.1 i L1.2 oraz zgłoszeń do zarządcy częstotliwości.
Na telefonie to realnie znaczy zużycie baterii przy włączonym Wi-Fi, więc
runda po tej powinna to dołożyć. Najpierw jednak łącze musi wstawać
powtarzalnie: stany uśpienia przy niedziałającym łączu tylko zaciemniają obraz.

**Podgląd jest od razu**, bo bez niego pierwsze uruchomienie byłoby zgadywaniem.
