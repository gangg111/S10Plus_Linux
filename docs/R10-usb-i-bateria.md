# R10 - USB i bateria

Stan na 20.09.2026. Obie rzeczy weszly do serii jako siedem commitow
(patche 0055 do 0061). Zadna nie jest jeszcze potwierdzona na sprzecie.

## USB: po co, skoro telefon ma dzialac bez kabla

Nie chodzi o ladowanie ani o przesylanie plikow. Chodzi o to, ze **dzis ten
telefon nie ma jak o sobie nic powiedziec**. Initramfs postmarketOS zbiera
komplet diagnostyki (`blkid.txt`, `partitions.txt`, `dmesg.txt`), probuje
wystawic ja jako dysk przez USB i konczy na jednym zdaniu:

    /sys/kernel/config/usb_gadget does not exist, can't set up storage gadget

Siec nie wstaje, powloka awaryjna nie ma klawiatury, a ekran mieści 45 kolumn
i przewija sie bezpowrotnie. Kazda diagnoza kosztuje wiec pelny cykl wgrania.
USB w trybie urzadzenia to zamienia na odczyt pliku z komputera.

### Co bylo potrzebne, a czego nie

Najwazniejsze ustalenie rozpoznania: **tryb urzadzenia nie wymaga ani ukladu
USB-C, ani protokolu PD, ani max77705, ani extcon.** Sciezka peripheral
w kontrolerze DWC3 nie dotyka zadnej z tych rzeczy. To scina zakres z calego
stosu USB-C do jednego wariantu PHY i trzech wezlow.

| ogniwo | stan | co zrobiono |
|---|---|---|
| kontroler zegarow CMU_FSYS0A | sterownik i identyfikatory byly od dawna | dopisany sam wezel |
| PHY USB 2.0 | mainline nie znal tego ukladu | nowy wariant, kalka z nastepnego ukladu rodziny |
| kontroler DWC3 | mainline nie znal tego ukladu | compatible z odwolaniem do wariantu 850, zero zmian w sterowniku |
| wiazania | brak wpisow | dopisane do obu plikow |
| konfiguracja | ZERO opcji USB w serii | dopisany blok |

### Trzy rzeczy, ktore kosztowalyby iteracje, gdyby ich nie zmierzyc

1. **`CONFIG_PHY_EXYNOS5_USBDRD` nie chcialo byc `=y`.** Ten symbol ma
   `depends on TYPEC || !TYPEC`, czyli klasyczna pulapke trojstanowa: przy
   `TYPEC=m`, ktore daje domyslny defconfig arm64, symbol NIE MOZE byc `=y`
   i kconfig po cichu przycina go z powrotem do `=m`. Zmierzone: merge_config
   melduje podmiane na `=y`, a po `olddefconfig` w `.config` stoi `=m`.
   Modulow ta seria nie buduje, wiec `=m` znaczy tyle co brak. Fix:
   `CONFIG_TYPEC=y`, chociaz zadnego ukladu USB-C nie obslugujemy.

2. **Brak zasilaczy NIE jest bledem sondy.** Rozpoznanie twierdzilo, ze
   `devm_regulator_get` bez `vdd10-supply` i `vdd33-supply` konczy sonde
   porazka. Sprawdzone w zrodle rdzenia regulatorow: `have_full_constraints()`
   zwraca prawde na kazdym systemie z zapelnionym drzewem urzadzen, a zwykle
   pobranie brakujacego zasilacza oddaje wtedy **atrape**. Dlatego nie
   dorabiamy sztucznych szyn dla rail, ktorych i tak nie kontrolujemy.

3. **Przesuniecie rejestru PMU zgadza sie co do bitu.** Producent podaje
   `pmu_offset = <0x72c>`, a mainline ma dokladnie te sama wartosc dla
   nastepnego ukladu rodziny. To jest powod, dla ktorego wariant jest kalka,
   a nie zgadywaniem.

### Sufit predkosci: USB 2.0, swiadomie

Producent deklaruje `super-speed-plus`. My opisujemy **jedno z trzech okien
rejestrow PHY**, to od USB 2.0. Pozostale dwa niosa pasy SuperSpeed i strone
DisplayPort tego samego bloku kombinowanego, a ich obsluga wymaga tablic
kalibracyjnych PMA i PCS, ktorych nie ma w zadnym ze zrodel, z jakich ta seria
powstaje. Port, ktory sie zglasza w High Speed, jest wart wiecej niz okno,
do ktorego nikt nie pisze.

### Dowod dzialania, do wykonania na telefonie

```sh
dmesg | grep -iE 'dwc3|usbdrd|phy-exynos'
ls /sys/class/udc/            # spodziewane: 10c00000.usb
ls -d /sys/kernel/config/usb_gadget
```

Nazwa w `/sys/class/udc` jest wyprowadzona z kodu rdzenia UDC, nie odczytana
z urzadzenia. Jesli initramfs zglosi "No UDC found", to wlasnie ta nazwa
jest pierwsza rzecza do porownania.

## Bateria: sam odczyt poziomu, bez ladowania

Zakres jest zawezony celowo. Licznik ladunku odpowiada na pytanie ile zostalo
i nie wymaga niczego poza wezlem, bo sterownik jest w mainline od dawna.
Ladowarka wymagalaby opisu ogniwa i dzialajacego sposobu przerwania ladowania,
a pomylka w tym kosztuje wiecej niz brak funkcji.

| ogniwo | co to jest |
|---|---|
| uklad | MAX77705, towarzysz glownego PMIC-a, adres 0x66 |
| magistrala | USI_CMGP3 w trybie I2C, pod 0x15d60000, przerwanie SPI 82 |
| piny magistrali | gpm12-0 i gpm13-0, funkcja 2 |
| przerwanie ukladu | gpa1-6 jako EINT, poziom niski |
| licznik ladunku | osobny wezel I2C, obsluguje go max17042_battery.c |
| sterowniki | wszystkie juz w mainline, zero nowego kodu |

Liczby ogniwa odczytane wprost ze zrodel producenta i przeliczone: 4000 mAh,
ladowanie do 2850 mA, napiecie koncowe 4350 mV, puste przy 3200 mV. Do samego
licznika ladunku nie sa potrzebne, ale beda, gdy przyjdzie ladowarka.

### Dwa zalozenia, obydwa oznaczone

**HW-42, tryb bloku USI.** Ta magistrala nie jest dedykowanym kontrolerem
I2C, tylko blokiem USI, a o protokole decyduje rejestr trybu lezacy POZA nim.
Naszego wezla dla tego rejestru nie ma: bierzemy tryb, ktory zostawia firmware
rozruchowe, na tej podstawie, ze ono odczytuje te bateria, zanim odda maszyne.
Bazy bloku rejestrow systemowych CMGP rowniez nie mamy skad wziac, wychodzi
z analogii do innej domeny. Dlatego wezla pod ten adres NIE dopisujemy
na probe: na tym ukladzie zapis pod zly adres konczy sie zewnetrznym
przerwaniem magistrali.

**HW-43, adres licznika ladunku.** 0x36 pochodzi z jedynej innej plyty
w mainline noszacej ten uklad. Zrodla producenta dla tego telefonu w ogole
nie umieszczaja licznika na magistrali: wieszaja go w korzeniu drzewa bez adresu
i wiaza z bateria po nazwie. Koszt bledu jest maly, bo zly adres to nieudana
sonda i nic wiecej, ale wynik ma byc odczytany, nie zalozony.

Swiadomie pominieto tez `maxim,rsns-microohm`. Producent podaje rezystor jako
indeks, nie jako wartosc w omach, a bez tej wlasciwosci sterownik liczy ladunek
z napiecia i nadal odpowiada na pytanie. Liczba wymyslona tutaj odpowiadalaby
blednie.

### Dowod dzialania, do wykonania na telefonie

```sh
dmesg | grep -iE 'max77705|max17042|hsi2c|i2c'
ls /sys/class/power_supply/
cat /sys/class/power_supply/*/capacity
```

## Fastboot w bootloaderze: z martwego przycisku w dzialajacy

Pozycja **Enter Fastboot Mode** w menu BIOS-u nie mogla zadzialac: w konfiguracji
bootloadera nie bylo ani jednej opcji USB, a w binarce nie bylo nawet polecenia
`fastboot`. Naprawione.

### Co sie okazalo po drodze

U-Boot ma **gotowy** sterownik `phy-exynos-usbdrd.c` i gotowy kontroler:
`dwc3-generic.c` zna juz `samsung,exynos850-dwusb3`, a nasz wezel wymienia go
jako wariant zapasowy, wiec kontroler nie wymagal ZADNEJ zmiany. Kod plyty ma
tez od dawna gotowe `exynos_fastboot_setup()`, ktore alokuje bufor przez
`lmb_alloc`, ustawia `fastboot_addr_r` i buduje aliasy partycji z tablicy GPT.
Ten kod nigdy sie nie kompilowal, bo `FASTBOOT` byl wylaczony.

### Jedyna realna roznica sprzetowa

Sterownik PHY w U-Boocie mial **na sztywno** `EXYNOS_USBDRD_PHY_CONTROL = 0x0704`.
Na naszym ukladzie to przesuniecie **strony DisplayPortu** tego samego bloku
kombinowanego, a przelacznik USB 2.0 siedzi pod `0x72c`. Producent nazywa oba
wprost: `pmu_offset = <0x72c>` i `pmu_offset_dp = <0x704>`. Samo dopisanie
compatible dalo by sterownik, ktory melduje sukces i zostawia PHY odizolowane.
Dlatego przesuniecie jest teraz polem wariantu, a nie stala.

Sekwencja startowa jest **odziedziczona** po sasiednim ukladzie, bo producent
podaje dla obu te sama wersje PHY, a jadro tak wlasnie steruje nastepnym
ukladem rodziny. To zalozenie, nie pomiar, i tak jest opisane w kodzie.

### Flashowanie celuje w UFS, nie w nieistniejacy eMMC

Kod plyty szukal dysku przez `blk_get_dev("mmc", ...)`, a ten telefon nie ma
karty. U-Boot ma backend blokowy, wiec fastboot celuje teraz w `scsi 0`, czyli
w ten sam dysk UFS, ktory bootloader juz czyta. Kod plyty wybiera backend
konfiguracja, zeby nie zepsuc plyt z eMMC, ktore dziela ten plik.

### Dowod, ze to jest w binarce

```
_u_boot_list_2_cmd_2_fastboot        w tablicy polecen U-Boota
samsung,exynos9820-usbdrd-phy        w binarce
samsung,exynos850-dwusb3             w binarce
dwc3: core.o gadget.o ep0.o dwc3-generic.o     wlinkowane
gadget: g_dnl.o f_fastboot.o                   wlinkowane
```

Bufor: `lmb_alloc` z rozmiaru `CONFIG_FASTBOOT_BUF_SIZE` (128 MB), adres
zapasowy `0xc0000000` lezy w drugim banku pamieci, 32 MB przed buforem ramki
pod `0xca000000`, i z dala od banku, w ktorym mieszka sam U-Boot.

### Czego to NIE naprawia

`patches-uboot/` nadal jest przestarzale: drzewo bootloadera ma commit WIP na
szczycie i kilkanascie niezatwierdzonych plikow, wiec bramka DT bootloadera
zostaje czerwona. To osobny, wczesniejszy dlug, nie skutek tej zmiany.

## Licznik paliwa po zmianie opisu plytki (24.09.2026)

Pierwsza wersja 0061 pomijala `maxim,rsns-microohm`, wiec sterownik ustawil
licznik w tryb tylko-napiecie: CGAIN 0, MiscCFG 0x0003 (alarm SOC na VFSOC),
LearnCFG 0x0007. Licznik jest zasilany z baterii i pamieta te rejestry. Po
dopisaniu rezystora sterownik liczyl progi alarmu z RepSOC, a uklad porownywal
je z VFSOC: przy pelnej baterii 108 przerwan/s i 10 154/s na I2C. Latka 0105
ustawia w probe SACFG na RepSOC, gdy opisany jest rezystor; sprawdzone na
jadrze #58 (MiscCFG 0x0003 przed restartem, 0x0000 po nim, przerwania zniknely).

CGAIN licznik w MAX77705 koduje jak rodzina ModelGauge m5: wzmocnienie 1,0 to
`0x0400`, nie `0x4000` jak w MAX17047. Na tym telefonie przywrocone recznie
(`i2cset -f -y 2 0x36 0x2e 0x0400 w`); od tej chwili `current_now` mierzy
realny prad (-799 mA przy 8 rdzeniach i limicie wejscia ladowarki 100 mA).
