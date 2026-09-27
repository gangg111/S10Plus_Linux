# cpufreq przez firmware APM i dlawienie klastrow (24.09.2026)

Jadro #59 z latkami 0109-0111 (identyfikatory domen ACPM, wariant Exynos9820
w `clk-acpm`, etap 15 drzewa: OPP, zegary rdzeni, progi pasywne 85 C).

## Pierwszy rozruch: cpufreq-dt nie wstal

```
cpufreq: cpufreq_policy_online: ->get() failed      (x8)
cpufreq-dt cpufreq-dt: failed register driver: -19
```

Firmware nie podaje biezacej czestotliwosci (FREQ_GET zwraca 0 na kanalach
0 i 1), zegar raportowal 0, a rdzen cpufreq odrzuca polityke z zerem.
Pierwsza naprawa przez `assigned-clocks` w wezle `acpm_ipc` dzialala, ale
odrzucil ja dt-validate (binding ACPM ma additionalProperties: false,
a metaschemat wymaga `clocks` obok `assigned-clocks`). Ostatecznie (jadro #60)
sterownik `clk-acpm` raportuje dla 9820 poziom startowy domeny z tablic fvmap
(1053 / 1222 / 1378 MHz dla klastrow), dopoki cpufreq nie ustawi innego.

## Po naprawie

```
policy0 cpus=0 1 2 3 gov=schedutil min=442000 max=1950000
policy4 cpus=4 5     gov=schedutil min=507000 max=2210000
policy6 cpus=6 7     gov=schedutil min=520000 max=2080000
cooling_device0 cpufreq-cpu0 max=12, cooling_device1 cpufreq-cpu4 max=15,
cooling_device2 cpufreq-cpu6 max=14
```

Spoczynek: policy6 520000, policy4 845000 (wczesniej na sztywno 1378/1222 MHz).
Pod petla ADD (`takt.c` z 2026-09-24-termika): kazdy rdzen zmierzony na maksimum
polityki, 1950 / 2210 / 2080 MHz, czyli schedutil podnosi zegar, a firmware
go ustawia.

## Dlawienie: 150 s pelnego obciazenia 8 rdzeni (`chlodzenie-150s.txt`)

Temperatura klastra big zatrzymala sie na 84-86 C (prog pasywny 85 C), M4
schodzi do 1664-1820 MHz, A55 pozniej do 1742 MHz, A75 zostaje na 2210.
5 s po zdjeciu obciazenia: 55 C, chlodzenie 0. Noca, przed tymi latkami, ten
sam scenariusz (zegary max, brak chlodzenia) dal 99 C w minute i wylaczenie
przez prog krytyczny.

## Plasma Mobile z cpufreq: ten sam test co rano (`~/narz/ab.sh`)

Czysty restart telefonu (jadro #60), dziennik klatek KWin
(`KWIN_LOG_PERFORMANCE_DATA=1`), syntetyczny palec: 5 x otworz/zamknij
szuflade w 17,1 s. Rano ten sam test na zegarach z bootloadera
(1053 / 1222 / 1378 MHz, bez cpufreq).

| przebieg | plasmashell CPU | kwin CPU | system zajety | klatek | render mediana / p90 |
|----------|-----------------|----------|---------------|--------|----------------------|
| rano 1-3 | 83,0-85,8 s     | 16,4-18,6 s | 73-75%     | 36-47  | 103-115 / 166-172 ms |
| dvfs-1   | 51,4 s          | 20,1 s   | 52%           | 49     | 107,7 / 145,8 ms     |
| dvfs-2   | 55,1 s          | 23,8 s   | 58%           | 50     | 112,0 / 150,1 ms     |
| dvfs-3   | 57,3 s          | 21,5 s   | 57%           | 49     | 108,8 / 148,6 ms     |

W trakcie przebiegu kazdy klaster spedzil ok. 11 z 17 s na maksymalnym
poziomie (`time_in_state`: 1950 MHz 11,6 s, 2210 MHz 11,1 s, 2080 MHz
11,3 s), a big doszedl do 66 C, daleko od progu 85 C.

Wniosek z pomiaru: cpufreq zdjal ok. jednej trzeciej czasu procesora
powloki, ale czas skladania klatki w KWin (llvmpipe, 1440x3040) zostal
przy ok. 110 ms, czyli ok. 9 kl/s w animacji, przy 16,7 ms potrzebnych do
60 kl/s. Zegar procesora nie jest tu waskim gardlem, jest nim programowe
renderowanie. Nastepny krok: GPU (Mali-G76, panfrost).
