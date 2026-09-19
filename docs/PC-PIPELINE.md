### Bramki na PC bez Linuksa: jak i dlaczego tak

Faza rekonesansu powstala w Termuxie na samym telefonie. Przeniesienie jej na PC
z Windows postawilo pytanie, ktore decyduje o wiarygodnosci calego projektu: **czym
udowodnic, ze kod sie kompiluje i ze DTB jest ten sam**, skoro nie ma tu Linuksa.

Ten dokument opisuje, co zadzialalo, co nie, i jakim dowodem to potwierdzono. Jest
potrzebny, bo bez niego kazdy kolejny przebieg bramek zaczyna sie od tych samych
kilku godzin dochodzenia.

#### Co odpadlo i dlaczego

**WSL**: nie zainstalowany, instalacja wymaga uprawnien administratora. Nie ruszane.

**Kernel build pod MSYS2**: odpada u podstaw. Tamtejszy `gcc` (`/mingw64/bin/gcc`,
target `x86_64-w64-mingw32`) zapisuje pliki zaleznosci z **CRLF** i z **natywnymi
sciezkami** (`C:/msys64/tmp/pm2.o: ...`). Dowod pomiarowy: `fixdep` czyta wlasny
`.fixdep.d` i pada z `read: No error`, bo `st_size` = 59, a `read()` zwraca 58, czyli
o dokladnie jeden bajt CR mniej. Kbuild opiera sie na tych plikach na kazdym kroku,
wiec nie ma sensu tego obchodzic: dowod z takiego toolchainu bylby niewiarygodny.

**Telefon**: przy tej sesji niepodlaczony (`adb devices` pusty), wiec bramek nie dalo
sie odtworzyc tam, gdzie powstaly.

#### Trzy pulapki, ktore blokuja samo rozpakowanie drzewa jadra

**1. Wielkosc liter.** Drzewo jadra zawiera pliki roznjace sie wylacznie wielkoscia
liter, np. `include/uapi/linux/netfilter/xt_CONNMARK.h` obok `xt_connmark.h`. Na NTFS
domyslnie jeden z pary nadpisuje drugi i `git status` pokazuje brakujace pliki.

Rozwiazanie: **flaga case-sensitive na katalogu**, dziedziczona przez podkatalogi
tworzone pozniej, ustawiana bez uprawnien administratora:

```
fsutil file setCaseSensitiveInfo <pusty-katalog> enable
```

Katalog musi byc **pusty** w chwili ustawiania flagi. Kolejnosc, ktora dziala:
sklonuj `.git` gdzie indziej, utworz pusty `sources/linux`, ustaw flage, przenies
`.git` do srodka, dopiero potem `git checkout`. Dowod: po checkoucie `xt_CONNMARK.h`
i `xt_connmark.h` leza obok siebie, `git status` czysty, 94887 plikow.

**2. Dowiazania symboliczne.** Drzewo ma 99 dowiazan (m.in.
`scripts/dtc/include-prefixes/dt-bindings` i `include/dt-bindings/input/linux-event-codes.h`).
Przy `core.symlinks=false` git zapisuje je jako **pliki tekstowe ze sciezka w srodku**,
przez co `cpp` wkleja tekst `../../uapi/linux/input-event-codes.h` do zrodla DTS,
a `dtc` konczy `syntax error`.

Rozwiazanie: `git config core.symlinks true` i ponowny checkout tych 99 plikow.
Na Windows dziala bez administratora, jesli wlaczony jest tryb dewelopera
(`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock\AllowDevelopmentWithoutDevLicense = 1`).

**3. Konce linii.** `core.autocrlf` musi byc `false` **przed** checkoutem, inaczej cale
drzewo dostaje CRLF i zaden patch serii sie nie nakłada. Jesli juz sie stalo:
`git config core.autocrlf false && git rm --cached -r . && git reset --hard`.

#### Czym zastapiono make

`scripts/pc-prepare.sh` odtwarza to, co kbuild robi w fazie `archprepare`, bez make:

| element | jak |
|---|---|
| `dtc` | kompilowany ze zrodel jadra (`scripts/dtc/`), flex i bison z MSYS2 |
| `.config` | kconfigowy `conf` zbudowany ze zrodel, `--defconfig` plus `--syncconfig` |
| wrappery `asm/*.h` | z `generic-y` i `mandatory-y` (`scripts/pc-gen-headers.py`) |
| `cpucap-defs.h`, `sysreg-defs.h`, `kernel-hwcap.h` | `awk` na `arch/arm64/tools/` |
| naglowki syscalli | `scripts/syscallhdr.sh` i `syscalltbl.sh` |
| `bounds.h`, `asm-offsets.h`, `rq-offsets.h` | kompilacja do `.s` plus `scripts/pc-mkoffsets.py` (port `filechk_offsets`) |
| `timeconst.h` | `bc` na `kernel/time/timeconst.bc` |

`conf` **musi** byc zbudowany kompilatorem z pelnym POSIX-em (`/usr/bin/gcc` z MSYS2),
bo `confdata.c` wlacza `sys/mman.h`, ktorego mingw nie ma.

#### Kompilacja pojedynczego pliku dla arm64

`scripts/cc-kernel.sh` odtwarza flagi kbuilda dla arm64 z `LLVM=1`. Trzy rzeczy w tym
zestawie nie sa oczywiste i kazda kosztowala osobna iteracje:

1. **`-fms-extensions`**: kernel wlacza je przez `CC_FLAGS_DIALECT` (`Makefile:815`,
   `CONFIG_CC_MS_EXTENSIONS`). Bez tego clang **milczaco porzuca** anonimowe pole
   z tagiem (`struct ns_tree;` w `struct ns_common`), po czym sypie sie `fs.h`
   asercja `sizeof(struct filename) % 64 == 0` i braki pol `ns_id`.
2. **`-O2`**: bez optymalizacji `BUILD_BUG_ON(1)` nie znika i `kvm_host.h` wywala
   `-Werror=return-type`.
3. **nazwa modulu bez myslnikow**: kbuild robi `name-fix-token`
   (`scripts/Makefile.lib:19`); bez tego `kmod_exynos-pm-domains` trafia do wbudowanego
   asemblera jako niepoprawny identyfikator i pada `unexpected token in argument list`.

#### Bramki schematow DT bez kbuilda

`dtschema` ma wlasne narzedzia i nie potrzebuje make:

- `dt-validate -s <bindings> <dtb>` odpowiada `CHECK_DTBS`. Pelny przebieg wobec
  wszystkich schematow jadra: 40 sekund, **0 naruszen**.
- `dt-doc-validate -u <bindings> <plik.yaml>` odpowiada `dt_binding_check`.

Artefakt srodowiska: na Windows `dt-doc-validate` zglasza dla **kazdego** pliku, takze
nietknietego pliku mainline, `Cannot determine base path from $id`. Porownuje sciezke
z `$id` ze sciezka systemowa, a ta ma odwrotne ukosniki. Sprawdzone na dwoch plikach
mainline (`samsung,exynos5433-decon.yaml`, `samsung,exynos850-clock.yaml`): ten sam
komunikat. `verify.sh` odsiewa dokladnie ten komunikat i dwie linie po nim, reszta
komunikatow nadal jest bledem.

#### Dowod, ze ta droga daje ten sam wynik co Linux

DTB zbudowane na PC (`cpp` z mingw plus `dtc` zbudowany lokalnie) ma sha256

```
b78e31abbf5d862254f9d9160c1e2b466daacc614222673c21994dccfaa4face
```

czyli **bajt w bajt to samo**, co build z Termuxa (clang 21.1.8, kbuild), zapisany
w `build-logs/43-verify-24-patches.log`. To jest kontrola krzyzowa dwoch niezaleznych
toolchainow na dwoch systemach.

Przy okazji wyszlo, ze wpis `4fcba6b6...` w `build-logs/00-tree-hash.txt` pochodzi ze
**starszego, zepsutego przebiegu**: `verify.sh` w wersji sprzed przepisania mial
`git apply --check ... && git apply ...`, a gdy sprawdzenie padalo (bo drzewo bylo juz
zapatchowane z poprzedniego uruchomienia), seria nie byla nakladana i build szedl dalej
na starym stanie drzewa. Widac to w pierwszych 20 liniach
`build-logs/43-verify-24-patches.log`: dziesiec komunikatow `patch does not apply`,
po ktorych przebieg spokojnie leci dalej. Nowy `verify.sh` sprawdza nakladanie serii
na osobnym indeksie i nie moze tego przeoczyc.


#### Bramki dodane po audycie cytowan

Audyt wykazal, ze potok mial slepa plame: bramki sprawdzaly, czy kod sie **buduje** i czy
**wyliczone tablice** zgadzaja sie ze zrodlem, ale nic nie sprawdzalo pojedynczych stalych
rejestrowych ani tego, czy cytowany plik w ogole istnieje w paczce zrodel. Piec blednych
offsetow i bitow przeszlo przez checkpatch, W=1, dt-validate i identyczny co do bajtu DTB.

Trzy nowe bramki zamykaja te dziure. Kazda ma test negatywny, czyli sprawdzono, ze
przywrocenie naprawionego bledu ja zapala, bo bramka, ktorej nikt nie widzial jak pada,
nie jest bramka.

| skrypt | co porownuje | pokrycie |
|---|---|---|
| `check-citations.py` | kazda sciezka downstreamu i kazdy cytat z numerem linii w patchach i dokumentach | 29 sciezek, 199 cytatow |
| `check-regs.py` | stale w `exynos9820_regs.h` wobec naglowkow producenta, po nazwie | 235 z 258 stalych, 23 nierozwiazane przypiete wzorcem |
| `check-cmu.py` | offsety, bity bramek i pola muxow i dzielnikow wobec `cmucal-sfr.c` | 528 z 528 offsetow, 515 pol |

Trzy pulapki, ktore te bramki same na siebie zastawily przy pisaniu, wszystkie wykryte
testem negatywnym, nie przegladem:

1. **Cytat poprzedzony ukosnikiem byl niewidoczny.** Negatywne spojrzenie wstecz
   `(?<![\w/])` miało odsiewac sciezki, a odsiewalo wlasnie te cytaty, ktore sa zapisane
   pelna sciezka. Po poprawce liczba widzianych cytatow skoczyla z 77 na 124.
2. **Cytat sierocy.** Zapis `dsim_reg.c:45-90 for the values and :1847-1893 for the order`
   ma druga pozycje bez nazwy pliku. Pierwsza wersja bramki ja pomijala, czyli nie sprawdzala
   dokladnie tego cytatu, ktory audyt zakwestionowal. Teraz sieroty sa wiazane z ostatnio
   nazwanym plikiem.
3. **Literal szesnastkowy zawiera litere.** Test "czy wyrazenie ma identyfikator" odrzucal
   `(0x1 << 1)` jako sparametryzowane, przez co dwanascie zgodnych stalych zglaszalo sie
   jako niezgodne. Fałszywy alarm bramki jest tak samo szkodliwy jak przeoczenie, bo uczy
   ignorowania jej wyniku.

#### Bramka, ktora zostala usunieta

`compare-dsim.py` porownywala nasza mape rejestrow DSIM z `samsung-dsim` i
raportowala, ze 14 z 15 offsetow jest roznych, 9 rejestrow nie ma odpowiednika,
a obslugi DSC nie ma wcale. Sluzyla za dowod, ze osobny host DSI jest konieczny.

Recenzja pod katem mainline ten argument obalila: `samsung-dsim` ma tablice
`reg_ofs` i jedenascie pol pozycji bitow w `driver_data` **wlasnie dlatego**, ze
offsety roznia sie miedzy generacjami, wiec ta sama liczba wyszlaby dla kazdego
juz obslugiwanego wariantu. Bramka mierzyla cos prawdziwego i wyciagala z tego
zly wniosek. Zostala usunieta razem z plikiem wzorcowym, bo trzymanie jej
oznaczaloby dalsze twierdzenie czegos, czego seria juz nie twierdzi.

#### Analiza statyczna: co z listy dokumentu sterujacego dziala, a co nie

Dokument sterujacy wymienia cztery bramki analityczne dostepne na PC, a
niedostepne w Termuxie. Stan faktyczny na tej maszynie:

| bramka z dokumentu | stan | dlaczego |
|---|---|---|
| `make W=1` | **jest**, jako `W=1 scripts/cc-kernel.sh` na kazdym pliku serii | flagi odtworzone z `scripts/Makefile.warn:113-121` |
| `make C=2` (sparse) | **nie ma** | `sparse` nie jest zbudowany dla Windows i nie ma go w repozytoriach MSYS2 (`pacman -Ssq "^sparse$"` bez trafien) |
| smatch | **nie ma** | to samo, plus wymaga zbudowanego drzewa z kbuildem |
| coccicheck | **nie ma** | `spatch` nie jest pakietowany dla MSYS2 |
| modpost i pelne linkowanie modulu | **nie ma** | wymaga przejscia kbuilda, ktorego ten pipeline swiadomie nie uruchamia |

Zamiast sparse i smatch stoi **analizator sciezkowy clanga**
(`scripts/check-analyzer.sh`), ktory lapie te sama klase bledow: odczyt
niezainicjowanej wartosci, wyluskanie NULL-a, wyciek zasobu. Kompilacja W=1
tego nie widzi, bo to analiza sciezek wykonania, a nie ostrzezenia skladniowe.
Dowod, ze bramka dziala: wstawienie do sterownika DECON wyluskania wskaznika,
ktory na jednej sciezce jest NULL-em, daje
`core.NullDereference` i kod wyjscia 1.

Checker `deadcode.DeadStores` jest wylaczony i to nie jest wygoda. Makra
debugowe jadra znikaja przy wylaczonym `CONFIG_DYNAMIC_DEBUG`, wiec kazda
zmienna uzywana tylko w `dev_dbg()` wyglada dla analizatora na martwy zapis.
Dowod, ze to szum: przy wlaczonym checkerze zglasza sie tak samo `byte_clk`
w `samsung-dsim.c:1093`, ktory stoi w mainline od 2023 roku (`e7447128ca4a`).

Dwa znaleziska, ktore zostaja we wzorcu (`scripts/golden/analyzer.txt`), sa
w `pinctrl-samsung.c` i pochodza z kodu mainline sprzed tej serii: analizator
nie potrafi udowodnic, ze petla wypelniajaca `virt_base[]` sie wykona. Nasze
dziesiec plikow daje zero.

Dwie z tych pozycji zmienily stan po ostatniej rundzie i tabela wyzej mowi
o nich za malo, wiec osobno:

**modpost i pelne linkowanie nadal nie ma i to jest realna dziura.** Bramka
kompilacji tluczie plik po pliku przez `scripts/cc-kernel.sh` z naglowkiem
`autoconf.h` wygenerowanym ze zwyklego arm64 defconfiga. Nie widzi wiec czterech
klas bledu: niespelnionej zaleznosci Kconfiga, cyklu `select`, brakujacego
symbolu przy linkowaniu modulu i konfliktu bool w tristate. Pierwsza z tych
czterech zamyka nowa bramka `scripts/check-kconfig.sh`, opisana nizej. Trzy
pozostale zostaja otwarte i zamkna sie dopiero przy pierwszym prawdziwym
`make` na maszynie z Linuksem.

**Warstwa konfiguracji byla slepa plama i nie widzial jej nikt.** Seria dokladala
trzy nowe symbole, wszystkie domyslnie `n`, a defconfig arm64 nie ma tez
`REGULATOR_S2DOS05`, `PINCTRL_EXYNOS` ani `EXYNOS_PM_DOMAINS`. Jadro zbudowane
z samego defconfiga kompiluje sie bez jednej uwagi, przechodzi wszystkie bramki
i nie zapala ekranu, bo nie ma w nim ani DECON-a, ani panelu, ani D-PHY, ani
regulatorow, ktore ten panel zasilaja. Zadna bramka tego nie widziala, bo
bramka kompilacji podaje pliki kompilatorowi wprost i nie pyta Kconfiga, czy
te pliki w ogole trafilyby do obrazu.

Zamyka to `scripts/exynos9820.config` razem z bramka `scripts/check-kconfig.sh`.
Bramka scala fragment z arm64 defconfigiem w katalogu tymczasowym i sprawdza
dwie rzeczy naraz: ze kazdy zamowiony symbol po `olddefconfig` ma zadana
wartosc, oraz ze zaden symbol swiadomie wylaczony nie wszedl bokiem przez
`select`. Zmierzone: 14 symboli zamowionych, 2 swiadomie wylaczone, 0 rozjazdow,
a przy okazji wchodza same `DRM_SAMSUNG_DSIM`, `DRM_DISPLAY_DSC_HELPER`,
`GENERIC_PHY_MIPI_DPHY`, `I2C_EXYNOS5` i `PINCTRL_EXYNOS_ARM64`.

Trzy testy negatywne, wszystkie wykonane, nie opisane:

1. Symbol znika albo zmienia nazwe u gory (`REGULATOR_S2DOS05` na
   `REGULATOR_S2DOS05_RENAMED`): bramka zglasza go jako nieustawiony, EXIT=1.
2. Zaleznosc niespelniona (`ARCH_EXYNOS` zbity do `n`): siedem symboli naraz
   przestaje sie ustawiac, EXIT=1. To wlasnie ta klasa, ktorej bramka
   kompilacji nie widzi.
3. Symbol swiadomie wylaczony wchodzi bokiem (`DRM_SIMPLEDRM` dopisany jako
   `y`): bramka zglasza, ze decyzja przestala obowiazywac, EXIT=1.

Konfiguracja liczona jest w katalogu tymczasowym, bo `KCONFIG_CONFIG` i oba
`KCONFIG_AUTO*` wskazuja poza drzewo. Bez tego bramka nadpisywalaby `.config`
i `include/generated/autoconf.h`, czyli psulaby wejscie bramki kompilacji,
ktora stoi po niej.

#### Dwie bramki dolozone przy okazji, obie o tej samej klasie bledu

Runda kompletnosci pokazala, ze bramki potrafia byc zielone o czyms innym, niz
mysli czytelnik. Dwa przypadki z tej rundy i co z nich wyszlo.

**Suma kontrolna zrodel nie mowi, skad one sa.** `scripts/golden/sources-ds.sha256`
przypina TRESC czterdziestu plikow producenta, ale siedem z nich weszlo do
`sources/ds` bez wiersza w `SOURCES.md`. Czytelnik odtwarzajacy prace dostawal
plik bez sciezki w drzewie producenta, wiec nie mogl sprawdzic ani cytatu, ani
commita, z ktorego plik pochodzi. To dokladnie ta klasa bledu, ktora zamknal
audyt cytowan po stronie patchy, tylko przesunieta o poziom wyzej, do samej
paczki zrodel. Zamyka to `scripts/check-sources-doc.py`: kazdy plik z `sources/ds`
musi byc opisany w `SOURCES.md`, a dwa trzymane lokalnie pod skrocona nazwa maja
jawna tablice aliasow, zeby alias nie stal sie furtka na wszystko. Test
negatywny wykonany: usuniecie jednego opisu zapala bramke.

**Bramka cytowan rozwiazywala nazwy plikow, nie sciezki.** Indeks byl budowany
po nazwie pliku i wylacznie z drzew producenta, wiec cytat do pliku mainline
o tej samej nazwie co plik producenta byl sprawdzany wzgledem **tego drugiego**.
Nazwa `pinctrl-exynos.h` istnieje po obu stronach: cytat do wiersza 217 w wersji
mainline zglaszal sie jako blad, bo wersja producenta ma 206 wierszy, a cytat do
wiersza 163 przechodzil, choc byl sprawdzany na zlym pliku. Bramka rozroznia
teraz oba przypadki: cytat pisany pelna sciezka jest sprawdzany dokladnie
wzgledem tego pliku, takze w `sources/linux`. Test negatywny wykonany: cytat do
wiersza 99999 w pliku mainline zapala bramke, czego poprzednia wersja nie
potrafila.

#### Trzy bramki z pierwszej sesji przy telefonie

Sesja z 11 wrzesnia 2026 (`docs/S1-sesja-sprzetowa.md`) dolozyla dwie bramki, obie z tego
samego powodu: pojawil sie material, ktorego wczesniej nie bylo, czyli odczyt ze sprzetu,
i trzeba go bylo przypiac tak, zeby nie dalo sie go po cichu cofnac.

**Mapa pamieci wobec sprzetu** (`scripts/check-memory-map.py`). Regula 3 z `docs/HW-BLOCKED.md`
mowi, ze zamknieta pozycja wchodzi do `verify.sh` jako bramka. Sama suma kontrolna DTB tego
nie zalatwia: zmienia sie przy KAZDEJ zmianie drzewa, wiec przy nastepnej przebudowie kusi,
zeby ja po prostu nadpisac, a wtedy zla mapa RAM-u przeszlaby niezauwazona. Ta bramka czyta
oba bloby wlasnym parserem FDT i porownuje wartosci: szesc bankow `memory@` musi byc
identycznych z tymi z telefonu, a kazda nasza rezerwacja musi istniec w jego drzewie pod tym
samym adresem i rozmiarem (framebuffer osobno, bo producent trzyma go w linii polecen, nie
w `reserved-memory`). Testy negatywne wykonane: zmiana rozmiaru banku o 0x100000, przesuniecie
`el2_code` o 0x100000 i podmiana adresu framebuffera, kazda zapala bramke i wskazuje wiersz.

**Pliki DT zgodne z generatorami** (`scripts/check-gen-dts.py`). Ta bramka powstala, bo sesja
odslonila rozjazd, ktorego nikt nie pilnowal, a ktory istnial od rundy R9. Oba generatory pisza
o sobie, ze sa zrodlem prawdy dla swojego pliku, ale nikt ich nie uruchamial: generator pliku
plyty nie znal calego bloku `reserved-memory`, jedenastu rezerwacji dolozonych w R9. Jego wersja
byla o 79 wierszy krotsza i cofnelaby ta prace, gdyby ktos jej uzyl. Bramka wymaga, zeby plik
dotykalo dokladnie tyle commitow, ile generator ma etapow, i zeby tresc po kazdym z nich byla
co do znaku wyjsciem `--etap k`. Testy negatywne wykonane trzy: rozjazd na etapie 1, rozjazd
na etapie 2 i trzeci commit dotykajacy pliku, czyli etap, o ktorym generator nie wie.

Obie przy pierwszym podejsciu mialy **ten sam blad, ktory same tropia**: przy braku materialu
wracaly z kodem zero, czyli `verify.sh` policzylby je jako zielone, choc nic nie sprawdzily.
Zwracaja teraz kod 2, a `verify.sh` ma dla nich osobna galaz i liczy to jako bramke
nieuruchomiona. Sprawdzone na atrapie katalogu bez pomiarow i bez repozytorium gita.

**Wariant panelu** (`scripts/check-panel-variant.py`). Trzecia bramka z tej samej sesji, z innego
powodu: pomiar odslonil pozorny rozjazd, ktory latwo byloby "naprawic" w zla strone. Panel tego
egzemplarza zglasza 0xA11013, a tablice w serii pochodza z wariantu opisanego jako 0xA01011, wiec
ktos moglby kiedys podmienic tablice "dla zgodnosci". Bramka odtwarza regule producenta: identyfikator
przepuszczony przez tablice `panel-lut` z drzewa telefonu, wpis po wpisie, z maska, ma wybrac ten sam
wariant, z ktorego przepisano tablice. Testy negatywne wykonane trzy, w tym jeden pozytywny kontrolny:
identyfikatory wybierajace `_utype` i `_preliminary` zapalaja bramke, a zmiana bitu spoza wszystkich masek
jej nie zapala.

Klasa bledu jest ta sama, co przy poprzednich dwoch bramkach: **cos twierdzilo o sobie, ze jest
pilnowane, a nie bylo**. Roznica polega tylko na tym, ze tym razem twierdzil to generator o samym
sobie, w wlasnym komentarzu, i nikt tego nie sprawdzil przez cztery rundy recenzji.
