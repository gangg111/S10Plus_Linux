# R13: pozostałe rdzenie

Runda trzynasta. Telefon startuje na jednym rdzeniu z ośmiu, bo wiersz
rozruchowy niesie `maxcpus=1`. Ten parametr nie jest ostrożnością: bez niego
telefon resetował się w trakcie rozruchu, a próba włączenia rdzenia przez
`/sys/devices/system/cpu/cpu1/online` na wystartowanym systemie kończyła się
tak samo, natychmiastowym restartem.

## Co się okazało

Wywołanie PSCI `CPU_ON` nie wystarcza na tym układzie. Firmware oczekuje, że
host najpierw **zdejmie blokadę przerwania tego rdzenia** w osobnym bloku obok
jednostki zarządzania zasilaniem, a dopiero potem poprosi o start.

Widać to wprost w sekwencjach producenta. Plik
`flexpmu_cal_cpu_exynos9820.h` opisuje włączenie każdego z ośmiu rdzeni trzema
krokami, w tej kolejności:

| krok | rejestr | adres | co robi |
| --- | --- | --- | --- |
| 1 | `GRP2_INTR_BID_ENABLE` | `0x15870000 + 0x200` | zeruje bit tego rdzenia |
| 2 | `GRP2_INTR_BID_CLEAR` | `0x15870000 + 0x20c` | kasuje zawieszony bit, po odczycie `0x208` |
| 3 | `CLUSTER<k>_CPU<m>_INT_EN` | `0x15860000 + …` | zdejmuje maskę przerwania rdzenia |

Drugi plik, `flexpmu_cal_powermode_exynos9820.h`, wymienia rejestry podpowiedzi
`CPU_INFORM`: `0x15860000 + 0x860`, po jednym słowie na rdzeń, od `0x860` do
`0x87c`.

**Te same rejestry, pod tymi samymi offsetami, ma Tensor gs101**, dla którego
mainline niesie już cały mechanizm w `drivers/soc/samsung/exynos-pmu.c`.
Komentarz w tym pliku mówi wprost, po co on jest: „CPU_INFORM register hint
values are required to be programmed in addition to the standard PSCI calls to
have functional CPU hotplug and CPU idle states. This is required to workaround
limitations in the el3mon/ACPM firmware". Nasz układ ma to samo firmware ACPM,
co widać po tym, że cała droga do głównego układu zasilania prowadzi przez nie
(runda R11).

Porównanie offsetów, żeby nie było wątpliwości:

| rejestr | gs101 w mainline | Exynos 9820 u producenta |
| --- | --- | --- |
| `CPU_INFORM(cpu)` | `0x0860 + cpu * 4` | `0x0860` do `0x087c`, po rdzeniu |
| `GRP1_INTR_BID_UPEND` | `0x0108` | `0x0108` |
| `GRP1_INTR_BID_CLEAR` | `0x010c` | `0x010c` |
| `GRP2_INTR_BID_ENABLE` | `0x0200` | `0x0200` |
| `GRP2_INTR_BID_UPEND` | `0x0208` | `0x0208` |
| `GRP2_INTR_BID_CLEAR` | `0x020c` | `0x020c` |

## Co wnosi runda

Trzy łatki, 0081 do 0083:

1. **0081** opis wiązania: nowy blok `samsung,exynos9820-pmu-intr-gen` oraz
   właściwość wskazująca na niego z węzła jednostki zasilania. Nazwa
   właściwości przestaje być związana z jednym producentem
   (`samsung,pmu-intr-gen-syscon`), a stara zostaje, bo drzewa Tensora już ją
   noszą.
2. **0082** wpis układu w sterowniku jednostki zasilania: te same procedury co
   dla Tensora, bo rejestry są te same. Bez ścieżki przez firmware, bo rejestry
   tego układu są zapisywalne wprost z jądra.
3. **0083** opis sprzętu: blok pod `0x15870000` i wskazanie go z węzła
   jednostki zasilania.

Konfiguracja nic nie potrzebuje: `CONFIG_EXYNOS_PMU`, `CONFIG_HOTPLUG_CPU`
i `CONFIG_ARM_PSCI_CPUIDLE` są już włączone.

## Czego to jeszcze nie dowodzi

**Nic z tego nie było uruchomione na telefonie.** To jest hipoteza z mocnym
uzasadnieniem, nie pomiar: rejestry się zgadzają co do offsetu, mechanizm jest
opisany w mainline dla układu z tym samym firmware, a sekwencje producenta
robią dokładnie to, co ten kod. Ale objawem u nas jest **reset**, a nie
„rdzeń nie wstaje", i dopóki tego nie zobaczę, nie wiem, czy to ta sama
przyczyna.

Drugi punkt niepewności: sekwencja producenta ma **trzeci krok**
(`CLUSTER<k>_CPU<m>_INT_EN`), którego ścieżka Tensora nie wykonuje. Offsety są
odczytane i wypisane niżej, ale kod ich na razie nie rusza. Jeśli dwa pierwsze
kroki nie wystarczą, to jest następna rzecz do dołożenia, a nie powód, żeby
zaczynać od nowa.

| rdzeń | klaster | rejestr | offset |
| --- | --- | --- | --- |
| 0 | 0 (A55) | `CLUSTER0_CPU0_INT_EN` | `0x1044` |
| 1 | 0 | `CLUSTER0_CPU1_INT_EN` | `0x10c4` |
| 2 | 0 | `CLUSTER0_CPU2_INT_EN` | `0x1144` |
| 3 | 0 | `CLUSTER0_CPU3_INT_EN` | `0x11c4` |
| 4 | 1 (A75) | `CLUSTER1_CPU0_INT_EN` | `0x1344` |
| 5 | 1 | `CLUSTER1_CPU1_INT_EN` | `0x13c4` |
| 6 | 2 (Mongoose) | `CLUSTER2_CPU0_INT_EN` | `0x1544` |
| 7 | 2 | `CLUSTER2_CPU1_INT_EN` | `0x15c4` |

We wszystkich ośmiu chodzi o bit 3, zerowany przy starcie rdzenia i ustawiany
przy jego zatrzymaniu.

## Jak to sprawdzić na telefonie

To wgranie ma badać **jedną** rzecz, więc idzie osobno od Bluetootha, a wiersz
rozruchowy zostaje z `maxcpus=1`. Po starcie:

```
dmesg | grep -iE "pmu|psci|cpu"
ls /sys/devices/system/cpu/
echo 1 > /sys/devices/system/cpu/cpu1/online
cat /sys/devices/system/cpu/online
```

Trzy możliwe wyniki, każdy coś mówi:

1. **Rdzeń wstaje**, `online` pokazuje `0-1`: hipoteza potwierdzona, zostaje
   podnieść `maxcpus` i włączyć resztę.
2. **Telefon resetuje się jak dotąd**: dwa pierwsze kroki nie wystarczyły,
   wchodzi trzeci (`CLUSTER…_INT_EN`) z tablicy powyżej.
3. **Polecenie wraca błędem, bez resetu**: to już postęp, bo znaczy, że coś
   zatrzymało start przed wejściem do firmware; wtedy patrzeć w `dmesg`.

Gdyby w logu pojawiło się `pmu-intr-gen syscon unavailable`, to znaczy, że
drzewo nie ma węzła albo właściwości i sterownik poszedł dalej bez nich.

## Co pokazał telefon (22.09.2026)

Runda zakładała, że brakującym ogniwem jest trzeci krok sekwencji producenta.
Zmierzone: **nie jest**.

Sterownik dostał pełną sekwencję, czyli obok dwóch kroków z kodu Tensora także
zerowanie bitu 3 w `CLUSTER<k>_CPU<m>_INT_EN` przy wybudzaniu rdzenia i
ustawianie go przy wyłączaniu. Jądro **#41** wgrane po sieci, sumy zgodne po
obu stronach. Wynik bez zmiany: `echo 1 > cpu1/online` resetuje telefon
natychmiast, `online: 0`, `nproc 1`, uptime 68 s po próbie. Poprawka została
**wycofana z drzewa**, żeby nie zaciemniała obrazu przy następnej hipotezie;
jej treść leży w `measurements/2026-09-22-rdzenie-trzeci-krok`.

Przy okazji runda zmieniła też swoją własną diagnozę objawu. Opis wyżej mówi
o zawieszeniu; telefon **resetuje się**, i to na tyle wcześnie, że jądro nie
zdąży wypisać ani jednego bajtu.

### Wykluczone: niezgodność wywołania PSCI

Drzewo producenta (`sources/ds/exynos9820.dts:5669`) deklaruje ten sam węzeł co
nasze, z tymi samymi identyfikatorami funkcji, a są to standardowe numery
PSCI 0.2:

```
	psci {
		compatible = "arm,psci";
		method = "smc";
		cpu_suspend = <0xc4000001>;
		cpu_off = <0x84000002>;
		cpu_on = <0xc4000003>;
	};
```

Wołamy więc dokładnie to, co woła producent. Hipoteza o złym wywołaniu SMC
odpada bez wgrywania czegokolwiek.

### Czego nie da się dziś zobaczyć

Żaden kanał diagnostyczny nie działa na tej ścieżce: `pstore` nie przeżywa
resetu (skalibrowane celową paniką jądra, `/sys/fs/pstore` puste),
`/dev/mem` odmawia odczytu rejestrów peryferiów, a zrzut okna jednostki
zasilania przez debugfs wywala czytający proces, bo w tym oknie są adresy,
których odczyt kończy się błędem translacji.

### Co zostaje

Zasilanie klastra. Drzewo producenta obok PSCI niesie węzeł `cpupm`
(`sources/ds/exynos9820.dts:5677`) z własnym zarządzaniem zasilaniem klastrów,
czyli ich jądro **nie polega na samym PSCI**. To spina się z rundą R16: główny
układ zasilania jest osiągalny wyłącznie przez firmware ACPM, przez skrzynkę
pod `0x15900000`, a naszemu portowi tego sterownika brakuje.

## ROZWIĄZANE: osiem rdzeni na ośmiu (22.09.2026)

Cała ta runda celowała obok. Przyczyną nie była żadna sekwencja producenta,
żaden rejestr jednostki zasilania ani PSCI. **Jądro ładowało się powyżej
czterech gigabajtów.**

### Dowód

Odczyt z telefonu, gdy jeszcze nie działało:

```
9f5200000-9f737ffff : Kernel code
9f7700000-9f7cfffff : Kernel data
80002000-86ffffff   : System RAM
```

Pamięć zaczyna się nisko, a obraz jądra leżał kilkadziesiąt gigabajtów wyżej,
bo alokator EFI naszego bootloadera bierze pamięć ze szczytu najwyższego
banku. Linux podawał więc firmware'owi adres startu rdzenia powyżej granicy,
a ono zamiast błędu kładło cały układ.

Drugi dowód, niezależny, z własnej sondy: `CPU_ON(rdzeń 1, adres 0xe1900000)`,
czyli **poniżej** granicy, zwróciło `SUCCESS`, jednostka zasilania pokazała
rdzeń jako pracujący (`CPU1_STATUS = 0x1`, `CPU1_STATES = 0x10`), a telefon
działał dalej.

### Naprawa, dwie połowy

1. **Łatka bootloadera 0030**: `LMB_LIMIT_DMA_BELOW_RAM_TOP` włączone w
   `Kconfigu` płyty. Symbol jest bez promptu, więc w defconfigu by przepadł.
   Obraz jądra ląduje teraz pod `0xe3400000`, a pamięci nie ubywa ani
   kilobajta (`MemTotal` te same 7 666 604 kB).
2. **Zdjęcie `maxcpus=1`** z wiersza rozruchowego. Ten parametr przestał być
   potrzebny wraz z pierwszą połową, a zaczął szkodzić: z nim jądro ustala
   zdolności systemu na podstawie jednego małego rdzenia i odrzuca każdy
   później dobudzany duży, mówiąc wprost `CPU5: will not boot` przy konflikcie
   zdolności. Bez niego wszystkie osiem są obecne przy ustalaniu.

Wpis rozruchowy należy teraz do `tools/phone/wszyj-wszystko-w-obraz.sh`, razem
z kontrolą w audycie, więc nie zginie przy następnym wgraniu obrazu. Obok
zostaje wpis awaryjny `99-s10-jeden-rdzen.conf` z jednym rdzeniem.

### Wynik

```
nproc = 8,  online = 0-7,  SMP: Total of 8 processors activated.
4x Cortex-A55   (0x41/0xd05)
2x Cortex-A75   (0x41/0xd0a)
2x Mongoose M4  (0x53/0x003)
```

Osiem pętli obciążających przez dwadzieścia sekund: load 3.76, żaden rdzeń nie
odpadł, zero paniki i zero oopsów. Rozruch skrócił się widocznie: przestrzeń
użytkownika wstaje w 5,1 s, a `graphical.target` po 5,1 s.

### Co z tej rundy zostaje nieprawdą

Zdanie otwierające, że `maxcpus=1` „nie jest ostrożnością", było prawdziwe co
do objawu, ale diagnoza była błędna: telefon nie resetował się dlatego, że
brakowało kroków producenta, tylko dlatego, że dostawał adres startu, którego
firmware nie obsługuje. Trzeci krok sekwencji producenta został
zaimplementowany, zmierzony jako bez wpływu i wycofany
(`measurements/2026-09-22-rdzenie-trzeci-krok`).

Pełna ścieżka eliminacji i wszystkie sondy:
`measurements/2026-09-22-rdzenie-co-naprawde-zabija`, `tools/sondy/`.
