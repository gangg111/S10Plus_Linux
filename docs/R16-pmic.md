# R16: glowny uklad zasilania S2MPS19, czyli skad dotyk bierze prad

## Punkt wyjscia: dotyk mial sterownik, wezel i magistrale, a nie mial zasilania

Panel dotykowy byl opisany w drzewie od rundy R3, sterownik `s6sy761` jest
w mainline, magistrala `104b0000.i2c` ruszyla po naprawie kolejnosci resetu
kontrolera (`patches/0068`). Mimo to kazdy transfer konczyl sie tym samym:

```
exynos5-hsi2c 104b0000.i2c: DIAG trans: brak potwierdzenia, ts=000a0006
exynos5-hsi2c 104b0000.i2c: DIAG ret=-6 ... sla=00000000
```

W `/proc/bus/input/devices` bylo jedno urzadzenie, `gpio-keys`. Uklad na adresie
0x48 nie odpowiadal, bo nie mial z czego odpowiadac: obie jego szyny, `tsp_io`
i `tsp_avdd`, pochodza z LDO glownego PMIC-a, a ten nie byl przez jadro
w ogole obslugiwany. Drzewo opisywalo je jako `regulator-fixed`, czyli atrapy
z komentarzem, ze prawda jest gdzie indziej.

## Werdykt

Uklad `S2MPS19` odpowiada teraz przez ACPM, wszystkie 40 jego szyn jest
zarejestrowanych, a panel dotykowy zglasza zdarzenia. Cala warstwa transportu
byla juz w mainline i nie wymagala ani jednej zmiany.

## Dlaczego nie trzeba bylo pisac warstwy transportu

To jest najwazniejsze ustalenie tej rundy i zaoszczedzilo ono osobnego
sterownika. Mainline ma `exynos-acpm-pmic.c`, napisany dla PMIC-ow Tensora.
Producent ma `acpm_mfd.c`. Sprawdzenie polegalo na porownaniu ukladu bitow
w poleceniu, nie na podobienstwie nazw:

| pole | producent (`acpm_mfd.h:19-32`) | mainline `exynos-acpm-pmic.c` |
|---|---|---|
| kanal SPEEDY | przesuniecie 12, maska 0xF | `GENMASK(15, 12)` |
| bank rejestrow | przesuniecie 8, maska 0xF | `GENMASK(11, 8)` |
| rejestr | przesuniecie 0, maska 0xFF | `GENMASK(7, 0)` |
| kod funkcji | przesuniecie 0 w drugim slowie | `GENMASK(7, 0)` |
| wartosc odczytu | przesuniecie 8 | `GENMASK(15, 8)` |
| kod powrotu | przesuniecie 24 | `GENMASK(31, 24)` |

Kolejnosc kodow funkcji tez jest ta sama: odczyt, zapis, modyfikacja, odczyt
hurtowy, zapis hurtowy (`acpm_mfd.h:51:56`). Zlozenie polecenia po stronie
producenta widac w `acpm_mfd.c:19-30`. Wniosek: do zrobienia zostawala mapa
rejestrow, uklad przerwan i dwie liczby.

## Liczby sprzetowe, odczytane z plikow lezacych lokalnie

### Kanaly

Oba numery pochodza z drzewa producenta tej plyty, z wezla
`s2mps19mfd@00` (`exynos9820-beyond2lte_eur_open_26.dts:5356-5361`):
`acpm-ipc-channel = <2>`, `acpm-speedy-channel = <0>`. Przypadkiem sa to te
same numery, ktorych uzywa glowny PMIC Tensora.

### Banki rejestrow

`s2mps19_core.c:40-43` daje adresy bankow, ktore ida w polu typu polecenia:
wspolny 0x00, PMIC 0x01, zegar czasu rzeczywistego 0x02, diagnostyka 0x0F.
Bank pomiarowy, ktory maja PMIC-i Tensora, w tym ukladzie nie istnieje:
jego przetwornik siedzi w banku PMIC od 0xbf. Dlatego w `sec-acpm.c` bank
pomiarowy stal sie opcjonalny, tak jak wczesniej bank zegara.

### Przerwania

Siedem rejestrow zgloszen zamiast szesciu. Maski wziete wprost z tablicy
producenta (`s2mps19_irq.c:59-62` i dalej), a nie odtworzone z kolejnosci nazw
w wyliczeniu, i to nie jest ostroznosc na wyrost: rejestr INT3 **pomija bit 4**,
wiec odtworzenie z nazw przesunelo by siedem ostatnich zgloszen tego rejestru
o jedna pozycje.

### Szyny

Zakresy napiec i rejestry sterujace pochodza z tablicy
`s2mps19_regulator.c:440-442` i dalej, wraz z przypisaniem kazdej szyny do
jednego z pieciu liniowych zakresow sprzetu (`s2mps19-regulator.h:203-213`).
Zakres czwarty nie jest uzywany przez zadna szyne tej plyty, wiec nie ma dla
niego stalej. LDO13M i LDO14M zostaly pominiete: krzem je ma, lista przerwan
nawet zglasza ich zwarcia, ale plyta ich nie wyprowadza, wiec producent nie
podaje dla nich zakresu, a zgadywanie bylo by gorsze niz brak opisu.

### Przerwanie samego PMIC-a

Drzewo producenta jest tu **niespojne** i trzeba to bylo rozstrzygnac, a nie
przepisac. Wezel ma `interrupts = <2 0 0>`, co przy odczycie dwukomorkowym
wskazywalo by pin 2. Ale ten wezel deklaruje trzy komorki przerwania, a dwa
niezalezne miejsca mowia co innego: wlasciwosc `s2mps19,irq-gpio` wskazuje
pin 1, a grupa pinow, na ktora wskazuje `pinctrl-0` tego wezla, nazywa sie
`m-pmic-irq` i ustawia `gpa0-1` z podciaganiem do gory. Sterownik producenta
zada `IRQF_TRIGGER_LOW`. Przyjete: `gpa0-1`, poziom niski. Potwierdzone
pozniej na telefonie, wpisem `118: gpa0 1 Level s2mps19` w `/proc/interrupts`.

## Czego NIE cachujemy i dlaczego

Oba banki maja `REGCACHE_NONE`. Firmware APM steruje szynami buck tego ukladu
samodzielnie w trakcie pracy jadra (to jest sens istnienia kanalu DVFS), wiec
zapamietane napiecie robilo by sie nieaktualne bez zadnego zapisu z naszej
strony. Rejestry zgloszen dodatkowo czyszcza sie odczytem i sa oznaczone jako
`precious`, zeby debugfs ich nie zjadl.

## Bezpiecznik, ktory musial byc na miejscu PRZED wlaczeniem tego ukladu

To jest glowny PMIC: na jego buckach stoi procesor, pamiec i modem. Gdyby
rdzen regulatorow uznal je za nieuzywane i wylaczyl, telefon zgasl by w trakcie
rozruchu. Przed wgraniem sprawdzone na zywym telefonie, a nie zalozone:

```
/proc/cmdline: ... clk_ignore_unused regulator_ignore_unused ...
```

Po rozruchu z nowym jadrem log potwierdza, ze bezpiecznik zadzialal:
`regulator: Not disabling unused regulators`. Drugi bezpiecznik jest w drzewie:
ograniczenia dostaly **tylko** dwie szyny dotyku. Reszta jest zarejestrowana
bez ograniczen, wiec nikt w jadrze nie moze poprosic o ich zmiane.

## Stan po tej rundzie, zmierzony

Jadro `#38 SMP PREEMPT Mon Sep 21 21:59:15 CEST 2026`, wgrane po kablu,
nie przez tryb pobierania. Pomiary w `measurements/2026-09-21-glowny-pmic/`.

Sterownik zwiazal sie z wezlem:

```
firmware:power-management:pmic-1 -> sec-pmic-acpm
s2mps19-regulator
```

Rejestr 0x00 banku wspolnego odczytany przez APM zwraca `0x12`, czyli realna
wartosc z ukladu, a nie zero z niepodlaczonej sciezki.

Zarejestrowanych szyn: 40. Napiecia odczytane z ukladu, nie zalozone, w tym
zywe wartosci DVFS: `BUCK1M 731250 uV`, `BUCK2M 693750 uV`, `BUCK6M 662500 uV`.
Szyny dotyku: `tsp_io enabled 1800000 uV`, `tsp_avdd enabled 3000000 uV`.

Dotyk:

```
input: s6sy761 as /devices/platform/soc@0/104b00c0.usi/104b0000.i2c/i2c-0/0-0048/input/input1
120:  375  gpa1  0 Level  s6sy761_irq
```

375 przerwan panelu i **zero** bledow transferu w calym logu, wobec bledu
`ret=-6` przy kazdej probie przed zmiana.

## Czego ta runda nie obiecuje

- Zegar czasu rzeczywistego tego ukladu nie jest obslugiwany. Bank 0x02
  istnieje, mapa nie zostala przepisana, bo nic jej jeszcze nie potrzebuje.
- Przetwornik i licznik mocy (rejestry od 0xbf) sa w mapie jako dostepne,
  ale nie ma dla nich sterownika.
- Sterowanie zewnetrzne szynami (pole `PWREN_SEL`) jest w mapie, ale zadna
  szyna z niego nie korzysta.
- LDO13M i LDO14M nie maja opisu, patrz wyzej.
- Kalibracja dotyku, gesty i tryb uspienia panelu to osobna robota; ta runda
  konczy sie na tym, ze panel ma prad i zglasza zdarzenia.
