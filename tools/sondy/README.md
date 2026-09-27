# Sondy: jednorazowe moduly jadra do pytania sprzetu

Na tym telefonie nie ma zadnego zwyklego kanalu diagnostycznego: `pstore` nie
przezywa resetu, `/dev/mem` odmawia odczytu rejestrow peryferiow, a zrzut okna
jednostki zasilania przez debugfs wywala czytajacy proces. Zostaje wlasny
modul jadra i to on jest tu narzedziem.

## Jak sie ich uzywa

```sh
# budowanie krzyzowe, w WSL, przy drzewie z nasza seria
make -C /home/pm/linux ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
     M=<katalog z modulem> modules

# na telefon idzie kluczem ratunkowym, bo klucz roboczy ma filtr tok
scp -i <klucz ratunkowy> <modul>.ko user@172.16.42.1:/tmp/
ssh  -i <klucz roboczy>  user@172.16.42.1 "sudo insmod /tmp/<modul>.ko; sudo dmesg | tail"
```

Kazdy z nich zwraca w `init` blad `-EAGAIN`, zeby **nie zostawac w pamieci**;
`insmod` melduje wtedy "Resource temporarily unavailable" i to jest wynik
poprawny, nie usterka. Komunikaty ida przez `pr_emerg`, wiec trafiaja takze
**na panel telefonu** i przezywaja jego smierc, co przy tych probach bywa
jedynym sposobem odczytania wyniku.

## Co ktory robi

| plik | pytanie |
| --- | --- |
| `nic.c` | test kontrolny: czy ladowanie modulow w ogole jest zdrowe |
| `pmuczyt.c` | odczyt wybranych rejestrow jednostki zasilania przez regmape |
| `kto.c` | kto odpowiada na `SMC`: wersja SMCCC, funkcje PSCI, wywolanie SiP |
| `jedensmc.c` | jedno jedyne `SMC`, `PSCI_VERSION`, z komunikatem przed i po |
| `aff.c` | `AFFINITY_INFO` dla rdzenia 1 |
| `cpuon0.c` | `CPU_ON` na rdzen 1 z adresem startu 0 |
| `przygot.c` | odtworzenie czterech krokow naszego sterownika sprzed `CPU_ON` |
| `wfi.c` | start rdzenia 1 na wlasnej petli `wfi` |

## Pulapki, ktore te sondy odslonily

- Odczyt `0x0818`, `0x081c` i `0x3b48` w oknie jednostki zasilania **wywala
  oops jadra**. Po oopsie jadro jest `Tainted: M D` i **kolejny `insmod` pada
  juz w `finit_module`**, wiec dalsze pomiary wymagaja restartu telefonu.
- W mapie gs101 `INFORM4` to `0x0840`, a NIE `0x0810`. Latwo czytac co innego,
  niz sie mysli.
- Modul zbudowany przy drzewie, ktore sie zmienilo, nie wejdzie; buduj przy tym
  samym drzewie, z ktorego jest jadro na telefonie.

Wyniki i wnioski: `measurements/2026-09-22-rdzenie-co-naprawde-zabija`.
