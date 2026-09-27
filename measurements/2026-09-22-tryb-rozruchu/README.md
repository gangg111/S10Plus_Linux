# Tryb rozruchu: S-Boot zjada slowo, zanim dojdzie do nas (22.09.2026)

## Co bylo do sprawdzenia

Czy `reboot bootloader` z Linuksa moze wprowadzic telefon w fastboot naszego
U-Boota, czyli czy slowo zapisane w jednostce zasilania przezyje pierwszy
stopien rozruchu.

## Jak zmierzone

1. W U-Boocie: sterownik `syscon-reboot-mode` (latka 0025) i odczyt trybu
   w `board_late_init` (latka 0026). Wgrane przez fastboot na partycje boot,
   telefon wstal, Linux doszedl do ekranu logowania, siec po USB odpowiada.
2. Po stronie jadra sprawdzone bezposrednio na urzadzeniu:
   - wezel `reboot-mode` jest w drzewie pod `system-controller@15860000`,
   - sterownik `syscon-reboot-mode` JEST ZWIAZANY z tym wezlem
     (`/sys/bus/platform/drivers/syscon-reboot-mode/15860000.system-controller:reboot-mode`).
3. Proba: `sudo systemctl reboot --reboot-argument=bootloader`.
   (Samo `systemctl reboot bootloader` nie dziala, systemd 262 odpowiada
   "Too many arguments"; argument podaje sie przez `--reboot-argument`.)

## Wynik

Telefon pojawil sie na USB jako:

```
SAMSUNG Mobile USB CDC Composite Device   USB\VID_04E8&PID_685D
SAMSUNG Mobile USB Modem
```

`04E8:685D` to **tryb Download Samsunga**, nie nasz fastboot. Fastboota nie
bylo ani przez 400 sekund nasluchu, ani pozniej.

## Wniosek

S-Boot czyta rejestr `INFORM3` (`0x1586080c`) i dziala na nim **zanim** odda
sterowanie obrazowi z partycji boot. Slowo `0x1234567d` (`bootloader`) jest
dla niego wlasnym poleceniem i prowadzi do trybu Download.

To przesadza tez o pozostalych nazwach z drzewa: `download`, `upload`,
`charging` i `recovery` to rowniez tryby S-Boota. Zaden z pieciu nie moze byc
kanalem do naszego bootloadera, bo kazdy zostanie skonsumowany wczesniej.

Sterownik i odczyt po stronie U-Boota **nie sa bledne** i zostaja: zle jest
miejsce, z ktorego czytaja. Nastepny krok to znalezienie rejestru, ktorego
S-Boot nie rusza (kandydaci: `INFORM4` pod `0x15860810`, `INFORM5` pod
`0x15860814`), co da sie sprawdzic bez zadnego wgrywania: zapisac znacznik
przez `devmem`, zrestartowac zwyczajnie i odczytac go z powrotem.

## Przy okazji: log proby rdzeni

`/home/user/rdzenie.log` przezyl zawieszenie dokladnie tak, jak zapowiadal
zapis z `sync` po kazdym kroku: konczy sie na linii `== PROBA: echo 1 >
cpu1/online` i nie mowi nic o tym, co telefon zabilo. Co z niego wynika:

- etapy hotplugu jednostki zasilania SA zarejestrowane
  (`31: 62: soc/exynos-pmu:prepare`, `74:196: soc/exynos-pmu:online`),
- `pstore` wtedy nie istnial, wiec nie bylo drugiego kanalu,
- wpis "brak" przy `samsung,pmu-intr-gen-syscon` byl **bledem mojej sondy**,
  a nie brakiem wlasciwosci: szukala do glebokosci 3, a wlasciwosc lezy na 4.
  Sprawdzona teraz wprost: jest.

## Rozwiazanie, zmierzone (ten sam dzien)

Kanalem zostal **blok sterujacy Androida na partycji `misc`** (`/dev/sda19`,
1 MB, na tym telefonie **caly wyzerowany**, czyli nikt go nie uzywa).

Przebieg, ktory przeszedl:

1. Z Linuksa: `printf 'bootonce-bootloader' | dd of=/dev/sda19 conv=notrunc`.
2. Reset.
3. Na panelu widac wprost linie z naszej plyty:
   `The misc partition asks for: bootonce-bootloader`, a pod nia `Fastboot Mode`.
4. Z komputera: `fastboot devices` -> `R58M24H6LW  fastboot`,
   `version-bootloader: U-Boot 2026.10-rc4-ga231ca01a0d6-dirty`.
5. `fastboot reboot` -> telefon wstaje do Linuksa w 90 s, **nie** wraca do
   fastboota, a pole polecenia w bloku ma 32 bajty zer.

Czyli dziala w obie strony: polecenie dziala raz i znika.

## Dwie rzeczy, ktore przy okazji wyszly i sa wazne osobno

### Partycje mozna pisac z Linuksa, wiec bootloader wgrywa sie zdalnie

`/dev/disk/by-partlabel/boot -> sda14`. Nowy U-Boot wchodzi przez zwykle
`dd` z dzialajacego systemu, z kontrola sumy z pominieciem pamieci podrecznej
(`echo 3 > /proc/sys/vm/drop_caches`). Fastboot ani Odin nie sa do tego
potrzebne. Kopia poprzedniej zawartosci: `D:\S10Plus-pmos\kopie\`.

### Wylaczanie systemu potrafi zawisnac w sterowniku pamieci masowej

`systemctl reboot` stanal na:

```
[785.982143] systemd-shutdown[1]: Rebooting.
[786.016679] sd 0:0:0:0: [sda] Synchronizing SCSI cache
```

i nie ruszyl przez 25 minut: jadro zyje (gadzet USB dalej zgloszony), userspace
juz zabity (brak sieci), resetu nie ma. Zdarzylo sie po serii zapisow przez
`dd`; wczesniejszy restart bez takich zapisow przeszedl. Obejscie, ktore dziala:
`sysctl -w kernel.sysrq=1`, `sync`, `echo s > /proc/sysrq-trigger`,
`echo b > /proc/sysrq-trigger` - to omija `device_shutdown()`, wiec i to
polecenie do pamieci masowej. Po takim resecie ext4 wstal bez odtwarzania
dziennika. Do zbadania osobno.

### Cieply reset nie odswieza magistrali USB

Po resecie przez sysrq telefon **jest** w fastboocie (widac na panelu), ale
Windows dalej nie widzi nowego urzadzenia, bo kabel nie zostal fizycznie
odlaczony i host nie zauwazyl ponownego podlaczenia. Wystarczy wypiac i wpiac
kabel. Przy resecie przyciskami problem nie wystepuje.
