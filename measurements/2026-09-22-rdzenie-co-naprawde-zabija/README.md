# Rdzenie: co naprawde kladzie ten telefon (22.09.2026)

Dzien zaczal sie od zalozenia, ze rdzenia nie da sie obudzic, bo cos jest nie
tak z PSCI albo z zasilaniem. Konczy sie z **rdzeniem 1 realnie wystartowanym**
i z przyczyna zawezona do jednej rzeczy.

## Narzedzie

Zadnego zwyklego kanalu nie ma: `pstore` nie przezywa resetu, `/dev/mem`
odmawia, zrzut okna PMU przez debugfs wywala czytajacy proces. Wszystkie
ponizsze pomiary zrobione wlasnymi, jednorazowymi modulami jadra, opisanymi
w `tools/sondy/`.

## Tablica eliminacji

| podejrzany | jak sprawdzony | werdykt |
| --- | --- | --- |
| numery funkcji PSCI | porownanie z drzewem producenta | **odpada**, identyczne |
| sterownik PSCI producenta | pobrany `drivers/firmware/psci.c` | **odpada**, niezmieniony |
| trzeci krok sekwencji producenta | zaimplementowany, jadro #41 | **odpada**, bez roznicy |
| poziom uprzywilejowania | `CPU(s) started at EL1` | **odpada**, taki sam |
| `SMC` jako takie | modul `jedensmc.c` | **odpada**, wraca |
| monitor bezpieczenstwa | modul `kto.c` | dziala, SMCCC 1.1, PSCI 0.1 |
| brak sterownika ACPM | odczyt z `/sys/bus/platform/drivers` | **odpada**, sterownik JEST |
| nasza procedura przed `CPU_ON` | modul `przygot.c` | **odpada**, przechodzi |
| `CPU_ON` samo w sobie | modul `cpuon0.c` | **odpada**, `SUCCESS` |
| co rdzen wykonuje po starcie | modul `wfi.c` | **zostaje** |

## Trzy pomiary, ktore rozstrzygnely

### 1. Kto odpowiada na SMC

```
SMCCC_VERSION          -> 0x00010001    (SMCCC 1.1)
SMCCC_ARCH_FEATURES    -> 0x00000000    (sukces)
PSCI_VERSION           -> NOT_SUPPORTED
PSCI_FEATURES CPU_ON   -> NOT_SUPPORTED
MIGRATE_INFO_TYPE      -> NOT_SUPPORTED
SiP 0x82000000         -> 0x82000000
```

Monitor jest prawdziwy i zgodny z SMCCC 1.1, a brak funkcji PSCI 0.2+ jest
poprawny dla implementacji 0.1, ktora wlasnie deklaruje drzewo. Komentarz
w drzewie portu odniesienia, ze "PSCI advertises 0.2+", jest **bledny**.

### 2. Rdzen DA SIE wystartowac

`CPU_ON(rdzen=1, adres startu=0)` zwraca **`SUCCESS`** i telefon **zyje**.
Odczyt jednostki zasilania zaraz potem:

```
CPU0_STATUS 0x1004 = 0x1   CPU0_STATES 0x1008 = 0x10
CPU1_STATUS 0x1084 = 0x1   CPU1_STATES 0x1088 = 0x10
CPU2_STATUS 0x1104 = 0x0   CPU3_STATUS 0x1184 = 0x0
```

Rdzen 1 jest zasilony i pracuje, w tym samym stanie co rdzen 0, i kreci sie
na smieciach. Ukladowi to nie przeszkadza.

### 3. Rdzen uspiony kladzie uklad

Start rdzenia 1 na wlasnym, dwuinstrukcyjnym kodzie (`wfi`, potem `b .-4`)
**polozyl telefon natychmiast**.

To sie zgadza z komentarzem mainline w `drivers/soc/samsung/exynos-pmu.c`:
podpowiedzi `CPU_INFORM` sa wymagane OBOK wywolan PSCI, zeby hotplug i stany
bezczynnosci dzialaly, jako obejscie ograniczen firmware `el3mon`/ACPM.
Swiezo obudzony rdzen nie ma nic do roboty i wchodzi w WFI natychmiast, wiec
pelne `echo 1 > cpu1/online` trafia na to samo w ulamku sekundy.

**ZASTRZEZENIE:** nie ma jeszcze dowodu, ze rdzen wykonal wlasnie TEN kod,
bo dane mogly nie zejsc z pamieci podrecznej do pamieci. Rozstrzyga to test
A/B ta sama droga, ale z petla BEZ `wfi`.

## Trop do sprawdzenia przy naprawie

`__gs101_cpu_pmu_online()` pisze `GS101_CPU_INFORM(smp_processor_id())`, czyli
podpowiedz rdzenia BIEZACEGO. W sciezce hotplugu ta procedura jest
zarejestrowana na `CPUHP_BP_PREPARE_DYN` i biegnie na rdzeniu zerowym, wiec
czysci podpowiedz rdzenia 0, a nie tego, ktory wstaje. Przy cpuidle jest to
poprawne, przy hotplugu wyglada na blad. Zastrzezenie: zmierzone, ze wszystkie
`CPU_INFORM0..7` i tak sa zerowe.

## KOREKTA: to nie bylo WFI (ten sam dzien, godzine pozniej)

Test A/B obalil teze o `WFI`. Ta sama droga, ale petla **bez** `wfi`
(`nop`, potem `b .-4`), polozyla telefon **tak samo**. Roznica miedzy
proba bezpieczna a zabojcza nie byla wiec obecnosc `wfi`, tylko to, ze
rdzen dostawal adres startu wskazujacy na NASZA strone pamieci.

Przyczyna jest po stronie przyrzadu, nie sprzetu: rdzen wtorny startuje
z wylaczona pamiecia podreczna i wylaczonym MMU, wiec czyta wprost
z pamieci, a instrukcje zapisane przez rdzen zerowy mogly jeszcze siedziec
w jego pamieci podrecznej. `flush_icache_range()` czysci do punktu
jednolitosci, a nie do punktu spojnosci, wiec nie wystarcza. Rdzen
najpewniej wykonywal wiec smieci, a nie nasz kod, i to one kladly uklad.

Wniosek metodologiczny: kod dla rdzenia wtornego musi lezec w pamieci
SPOJNEJ (`dma_alloc_coherent`), bo tylko wtedy zapis trafia wprost do
pamieci. Poprawiona sonda: `tools/sondy/rdzen2.c`.

W mocy zostaje to, co bylo zmierzone niezaleznie od tego bledu:
`CPU_ON(rdzen=1, adres=0)` zwraca `SUCCESS`, rdzen jest zasilony
(`CPU1_STATUS = 0x1`, `CPU1_STATES = 0x10`) i telefonowi to nie szkodzi.

## ROZSTRZYGNIECIE: jadro lezalo powyzej 4 GB

Odczyt z telefonu, jeszcze przed naprawa:

```
9f5200000-9f737ffff : Kernel code
9f7700000-9f7cfffff : Kernel data
80002000-86ffffff   : System RAM
```

Pamiec zaczyna sie nisko, a obraz jadra lezal kilkadziesiat gigabajtow wyzej.
Linux podawal wiec do `CPU_ON` adres startu powyzej granicy czterech
gigabajtow, ktorego firmware nie obsluguje, i zamiast bledu kladlo caly uklad.

Zgadza sie to co do joty z pomiarem z tej samej sesji: `CPU_ON` z adresem
`0xe1900000`, czyli PONIZEJ granicy, zwrocilo `SUCCESS` i telefon zyl.

Powod, dla ktorego akurat u nas: alokator EFI naszego bootloadera bierze
pamiec ze szczytu najwyzszego banku, a `lmb_add_memory()` rezerwuje to, co
powyzej `ram_top`, wylacznie gdy wlaczone jest `LMB_LIMIT_DMA_BELOW_RAM_TOP`.
Port odniesienia robi to celowo odwrotnie, z komentarzem "Make sure kernel is
placed in the lowest memory bank", i podnosi szesc rdzeni. Stockowe jadro
Samsunga lezy pod `0x801f8000`.

## Naprawa i wynik

1. Latka bootloadera **0030**: `LMB_LIMIT_DMA_BELOW_RAM_TOP` w `Kconfigu`
   plyty. Obraz jadra ladunek pod `0xe3400000`, `MemTotal` bez zmian
   (7 666 604 kB).
2. Zdjecie `maxcpus=1` z wiersza rozruchowego; z nim jadro odrzucalo duze
   rdzenie przy konflikcie zdolnosci (`CPU5: will not boot`).

```
nproc = 8,  online = 0-7,  SMP: Total of 8 processors activated.
4x Cortex-A55 (0x41/0xd05), 2x Cortex-A75 (0x41/0xd0a), 2x Mongoose M4 (0x53/0x003)
```

Osiem petli obciazajacych przez 20 s: load 3.76, zaden rdzen nie odpadl, zero
paniki i zero oopsow. `systemd-analyze`: firmware 15,443 s, loader 5,013 s,
jadro 4,455 s, przestrzen uzytkownika 5,107 s, razem 30,019 s.

Trwalosc: wpis rozruchowy nalezy teraz do `tools/phone/wszyj-wszystko-w-obraz.sh`
razem z kontrola w audycie, a obraz na dysku ma juz poprawiony wpis, wpis
awaryjny z jednym rdzeniem oraz biezace jadro.
