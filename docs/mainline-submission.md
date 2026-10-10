### mainline Linux na Samsung Galaxy S10+ (SM-G975F, beyond2lte)

Repo jest przenosne: `git clone` plus `scripts/fetch-sources.sh` odtwarza cale srodowisko.
Skrypty i pliki wzorcowe nie zawieraja sciezek absolutnych; jedyny wyjatek to domyslny
cel `scripts/sync-to-downloads.sh` (`/sdcard/Download/s10-mainline`), ktory jest po to,
zeby kopiowac projekt na telefon, i przyjmuje sciezke argumentem.

Baza: `linux@1200d84f4c0a929a0780180d25063d93773be79c` (7.2.0).
Seria: **40 patchy** na mainline plus jeden patch na drzewo poza mainline.

#### Co to jest i czego NIE jest

To jest **material do wyslania na liste**, nie dzialajacy port. Kazda liczba w kodzie ma
cytat do zrodla albo wpis w `docs/HW-BLOCKED.md`. Zaden fragment nie zostal potwierdzony
na sprzecie: telefon nie byl bootowany z tej serii ani razu.

Zielony `scripts/verify.sh` znaczy dokladnie tyle: **nie pogorszylo sie i stale zgadzaja
sie ze zrodlem**. Nie znaczy "dziala".

#### Co znalazla trzecia runda recenzji

Jedno z odrzucen drugiej rundy bylo **moim bledem** i zostalo cofniete.
Twierdzilem, ze `DRM_EXYNOS9820_DECON select DRM_EXYNOS_DSI` byloby cyklem
w Kconfigu. Cyklu nie ma, ale moje uzasadnienie tez bylo bledne: `select`
NIE jest pomijany przy wykrywaniu rekurencji, bo `sym_check_sym_deps()`
sprawdza `sym->rev_dep` (`symbol.c:1227-1230`), a to jest budowane wlasnie
z wlasciwosci `P_SELECT` (`menu.c:379-382`). Osobna sprawa: sam
`select DRM_SAMSUNG_DSIM` budowal mostek, ale nie budowal kodu, ktory
dopasowuje wezel DT tego wariantu, wiec konfiguracja kompilowala sie
i nigdy nie dzialala. Rozwiazaniem nie jest jednak `select` na host DSI:
to symbol WIDOCZNY i z wlasnymi zaleznosciami, a takich dokumentacja
Kconfiga wymusza nie. Zostaje `select DRM_SAMSUNG_DSIM` (twarda zaleznosc
linkowania, bo DECON wola `samsung_dsim_get_dsc()`) plus `imply
DRM_EXYNOS_DSI`, czyli host wlaczony domyslnie, ale mozliwy do wylaczenia.

Najgrozniejsze znalezisko calego projektu wyszlo dopiero tutaj i **nie bylo
widoczne dla zadnej bramki**: sterownik DECON wolal
`drm_of_find_panel_or_bridge()` z `NULL` w argumencie `panel`, a ta funkcja
zaczyna sie od `if (WARN_ON(!panel)) return -EINVAL;` (`drm_of.c:248`). Probe
konczylby sie bledem przy kazdym starcie. Kompilacja, `checkpatch`, `dt-validate`
i bisekcja byly przy tym zielone, bo to poprawny kod C wolajacy istniejaca
funkcje z legalna wartoscia. Zamiast niej jest teraz
`of_drm_get_bridge_by_endpoint()`, do ktorej kieruje dokumentacja tej samej
funkcji. Mostek nie jest juz szukany w probe: to prowadzilo do zakleszczenia,
bo trafia on na globalna liste dopiero przy podpieciu panelu, a panel powstaje
z bindu mastera, ktory czeka na `component_add()` tego sterownika. Jest wiec
rozwiazywany przy pierwszym uzyciu, a referencja zwalniana akcja devm.

Druga rzecz tej samej klasy: `exynos_crtc_handle_event()` robi
`WARN_ON(drm_crtc_vblank_get())` i uzbraja zdarzenie na vblank, wiec wolanie go
na **wylaczonym** CRTC dawalo splat i zdarzenie, ktore nigdy nie przychodzi.
Teraz wylaczona sciezka oddaje zdarzenie wprost, pod `event_lock`.

Trzy uwagi zostaly **odrzucone z dowodem**, nie po cichu:

- „usunac galaz `else` z bindingu DSIM": sprawdzone eksperymentem: bez niej
  wezel `fsl,imx8mm-mipi-dsim` z jednym zegarem przechodzi walidacje, czyli
  rozluznilibysmy cudzy kontrakt. Z galezia jest odrzucany, tak jak przed
  cala seria.
- „wydzielic zmiane nazwy pliku panelu do osobnego patcha": `git format-patch`
  przedstawia ja jako `similarity index 87%` z siedmioma hunkami, wiec recenzent
  widzi te 69 zmienionych linii, a nie skasowanie i dodanie pliku.

Zamkniete w tej rundzie: tag `Fixes:` dla patcha 0001. Klon jest plytki, wiec
commit wskazano przez blame w API GitHuba na lustrze `torvalds/linux`, a nastepnie
potwierdzono odczytem pliku z tamtego commita: w `7eb8f069be8a` ("drm/exynos: add
DSIM driver", 2014-04-04) `exynos_dsi_init()` juz ignorowal kody powrotu
`exynos_dsi_enable_clock()` oraz `exynos_dsi_init_link()` i bezwarunkowo zwracal
zero (linie 396, 449, 946-955 tamtej wersji pliku). `Cc: stable` swiadomie nie
dodano: blad jest z 2014 roku i nie ma zgloszonego objawu u uzytkownikow, wiec
decyzja nalezy do maintainera.

#### Kolejnosc wysylki: seria idzie przez dwa drzewa

Nie da sie tego wyslac jako jednej serii do jednego maintainera. `MAINTAINERS:8374`
kieruje `drivers/gpu/drm/bridge/samsung-dsim.c` i jego naglowek do **drm-misc**,
a `MAINTAINERS:8675` kieruje `drivers/gpu/drm/exynos/` do **drm-exynos**
(`daeinki/drm-exynos.git`). Miedzy tymi czesciami jest zaleznosc budowania:
patch o wpisie w `exynos_drm_dsi.c` potrzebuje `DSIM_TYPE_EXYNOS9820` z naglowka
mostka, a sterownik DECON potrzebuje `samsung_dsim_get_dsc()`, ktore mostek
eksportuje.

Kolejnosc, ktora to rozwiazuje:

1. **drm-misc**: patche mostka (poprawka `samsung_dsim_init`, cztery
   przygotowawcze, przekazanie konfiguracji DSC, zasilanie zewnetrznego PHY,
   wpis wariantu) plus ich binding. To jest samodzielna calosc: nic z niej nie
   zalezy od reszty.
2. **phy** i **mfd**: sterownik D-PHY i wpis w `syscon.yaml` moga isc rownolegle.
3. **drm-exynos**: wpis w `exynos_drm_dsi.c` i sterownik DECON, dopiero gdy
   czesc pierwsza wyladuje w mainline, albo na galezi immutable udostepnionej
   przez drm-misc.
4. **soc/samsung**: zegary, domena zasilania, pinctrl i drzewa urzadzen.

W cover letterze kazdej czesci trzeba te zaleznosc napisac wprost, razem
z odsylaczem do pozostalych czesci. Gotowe teksty czterech listow leza
w `docs/COVER-LETTERS.md`, razem z przypisaniem kazdego z 40 patchy do czesci.

#### Czego brakuje, zeby to wyslac

Kod jest kompletny. Jedna rzecz jest poza zasiegiem klawiatury i ona blokuje wyslanie:

**Bootowanie na sprzecie.** Zaden fragment nie byl uruchomiony na telefonie. Plan pomiarow,
ktory zamyka pozycje z `docs/HW-BLOCKED.md`, jest w `docs/UART-BRINGUP.md`.

Lancuch DCO **przestal byc problemem**. Piec plikow nioslo wczesniej copyright chiffathefoxa:
binding zegarow, sterownik zegarow i trzy pliki drzewa urzadzen. Wszystkie sa teraz wypisywane
ze zrodel producenta przez skrypty w `scripts/`, a autorstwo commitow jest wlasne:

| plik | generator | co z niego bierze |
| --- | --- | --- |
| `samsung,exynos9820.h`, `clk-exynos9820.c` | `gen-clk-exynos9820.py` | 533 zegary z tablic CAL |
| `exynos9820-pinctrl.dtsi` | `gen-pinctrl-dts-exynos9820.py` | 64 banki, 37 list przerwan |
| `exynos9820.dtsi` | `gen-dts-exynos9820.py` | 31 wezlow SoC, cztery etapy serii |
| `exynos9820-beyond2lte.dts` | `gen-dts-beyond2lte.py` | piny klawiszy, szyny panelu, dwa etapy |

Ze zbudowanego drzewa urzadzen wynika, ze przepisanie niczego nie ruszylo. Zrzut DTB ma po
obu stronach 1039 linii, a jedyna roznica w wartosciach to jeden numer phandle, ktory
przesunal sie razem z wezlem: `soc@0` jest teraz uporzadkowane po adresie, a wczesniej blok
wyswietlacza stal przed wlasnym kontrolerem zegarow. Sprawdzone przez kanonizacje wszystkich
odwolan miedzywezlowych, nie przez porownanie hashy.

Zostaje jeden odsylacz do chiffathefoxa, w opisie patcha z typami PLL: to cytowanie
wczesniejszej realizacji tego samego pomyslu, a nie przejety kod.

#### Czego nie widzialy bramki: brakujacy sterownik pinctrl

Seria od poczatku deklarowala w drzewie osiem wezlow
`samsung,exynos9820-pinctrl` i dodawala dla nich binding, ale **nigdy nie
dodawala tablic bankow do sterownika**. Sterownik pinctrl Samsunga trzyma
geometrie bankow w statycznych tablicach w kodzie, nie w drzewie urzadzen
(`samsung_pinctrl_get_soc_data()` bierze `of_data->ctrl[id]` po aliasie
`pinctrlN`), wiec kompatybilne nie mialo z czym sie zestawic. Zaden z osmiu
kontrolerow by nie wystartowal, a razem z nimi zaden pin i zadne GPIO: UART,
obie magistrale I2C, reset panelu, klawisze. Kazdy inny compatible tego SoC ma
zapasowy (`"samsung,exynos9820-mct", "samsung,exynos4210-mct"`), ten jeden go
nie mial.

Zadna z 47 bramek tego nie widziala, bo brakujacy sterownik nie jest bledem
kompilacji ani bledem schematu: `dtbs_check` sprawdza ksztalt wezla, a nie to,
czy ktos go obsluzy. Dlatego doszla bramka `scripts/check-compatibles.py`,
ktora dla kazdego wezla naszego drzewa szuka jego `compatible` w tablicach
dopasowan calego jadra. Sprawdzone, ze umie padac: po usunieciu jednego wpisu
z `pinctrl-samsung.c` zglasza dokladnie te osiem wezlow.

Tablice bankow (8 kontrolerow, 64 banki, 234 piny) sa transkrypcja tablic
producenta, tak samo jak sterownik zegarow, i wypisuje je
`scripts/gen-pinctrl-exynos9820.py`. Typy bankow producenta okazaly sie
identyczne bajt w bajt z tym, co mainline ma juz pod nazwami
`exynos850_bank_type_off` i `exynos850_bank_type_alive`.

#### Sterownik zegarow jest generowany, nie przepisywany

Sterownik zegarow to z natury transkrypcja dwoch tablic producenta do slownika makr mainline,
wiec w tej serii **jest** transkrypcja robiona maszynowo. `scripts/cmucal-model.py` czyta
`ds/cmucal-sfr.c` i `ds/cmucal-node.c` (34 bloki, 2661 rejestrow, 8405 pol, 1795 wezlow),
a `scripts/gen-clk-exynos9820.py` wypisuje z nich `clk-exynos9820.c` i
`include/dt-bindings/clock/samsung,exynos9820.h`. Dwa przebiegi daja plik bajt w bajt taki sam.

Co z tego wyszlo w liczbach: 533 zegary zamiast 441 w poprzednim porcie, komplet 8 blokow CMU,
528 offsetow i 515 pol porownanych przez `scripts/check-cmu.py` wprost z plikiem producenta,
zero rozbieznosci. Pokrycie tej bramki wzroslo z 865 do 1043 sprawdzanych symboli.

Trzy rzeczy poprawily sie przy okazji, bo generator czyta tablice do konca:

- **Oscylatory RCO przestaly byc udawane.** Poprzedni port podstawial pod pierwsze wejscie
  muxow CMU_CMGP i CMU_APM 26 MHz oscylator SoC, z jawna nota, ze prawdziwej wartosci nie ma
  w zrodlach. Jest: `FIXEDRATE(OSCCLK_RCO_CMGP, 49152000)` i `CLK_DLL_DCO` 360 MHz
  (`ds/cmucal-node.c:2787-2799`). Sterownik rejestruje je jako zegary o stalej czestotliwosci.
- **Polityka flag przestala byc hurtowa.** Bylo 135 bramek `CLK_IS_CRITICAL` i zero
  `CLK_IGNORE_UNUSED`; jest 24 i 156, wedlug reguly opisanej w opisie commita. CMU_DPU, ktory
  siedzi w przelaczalnej domenie zasilania, nie ma juz ani jednej bramki krytycznej.
- **Sciezki USI, UART i I2C dostaly `nMUX()` i `DIV_F()`** z `CLK_SET_RATE_PARENT`, czyli to,
  czego opiekun podsystemu zazadal w commicie e11560b050ce dla exynos990. Flaga konczy sie na
  zegarze funkcyjnym: PCLK tego samego peryferium wisi na wspolnej magistrali bloku i nie moze
  przekazywac zadania czestotliwosci.

Zaden z tych wyborow nie byl sprawdzony na sprzecie. Polityka flag ma wlasna pozycje
`HW-29` w `docs/HW-BLOCKED.md`, razem z planem pomiaru.

#### Co zmienil audyt cytowan

Seria przeszla audyt, w ktorym kazda stala byla sprawdzana wobec otwartego zrodla. Werdykt:
**FAIL**, 19 niezgodnosci. Po weryfikacji kazdej z osobna 18 okazalo sie prawdziwych, jedna
byla falszywym alarmem, a przy naprawie wyszla dwudziesta, ktorej audyt nie mogl domknac.
Najgrozniejsze byly te, ktorych **zaden build ani zadna dotychczasowa bramka nie lapala**:
`pinctrl_fsys0/1` pod zmyslonymi adresami (`0x10c30000` zamiast `0x13030000`) z bledna
numeracja przerwan, `CMD_LPDT` zapisywany do zlego rejestru (i nigdy nie zerowany),
`ESCCLK_EN` na bicie 19 zamiast 16, format piksela `0x7` zamiast `0x3e`, oraz
`WIN_FUNC_COPY = 0x0`, czyli w rzeczywistosci `PD_FUNC_CLEAR`: okno bylo by czyszczone
zamiast pokazywac bufor.

Wazniejsza od pojedynczych stalych byla **dziura materialowa**: patche cytowaly
`decon_reg.c`, `regs-dpp.h`, `cmucal-sfr.c` i `flexpmu_cal_local_exynos9820.h`, ktorych
nie bylo w `sources/`. Cytaty byly poprawne, ale nikt odtwarzajacy prace nie mogl ich
otworzyc, wiec kilkadziesiat stalych bylo formalnie nieweryfikowalnych z winy paczki
zrodel, nie z natury sprzetu. Po dociagnieciu tych plikow caly sterownik zegarow daje sie
porownac z tablicami producenta maszynowo (528/528 offsetow), a bit bramkowania 21, ktory
byl opisany jako ekstrapolacja z jednego przykladu, ma wlasny wpis dla kazdej z 28 bramek.

Trzy nowe bramki pilnuja, zeby ta klasa bledow nie wrocila: `check-citations.py` (cytowany
plik musi istniec, cytowana linia musi istniec), `check-regs.py` (stale rejestrow wobec
naglowkow producenta) i `check-cmu.py` (sterownik zegarow wobec `cmucal-sfr.c`). Kazda ma
test negatywny: sprawdzono, ze przywrocenie kazdego z naprawionych bledow **zapala** ja.


#### Co zmienila recenzja pod katem mainline

Po audycie cytowan seria przeszla druga recenzje, tym razem tak, jakby czytal ja
maintainer, ktory ma ja przyjac albo odrzucic. Werdykt: **NEEDS-WORK**, dwanascie
uwag blokujacych. Trzy z nich przepisaly architekture:

**Osobny host DSI nie mial uzasadnienia.** Argument "mapa rejestrow jest inna"
jest prawdziwy dla **kazdego** wariantu, ktory `samsung-dsim` juz obsluguje, bo
ten sterownik ma tablice `reg_ofs` i jedenascie pol pozycji bitow wlasnie po to.
Nasz host zostal skasowany (736 linii), a na jego miejsce weszl
`DSIM_TYPE_EXYNOS9820`. Przy scalaniu wyszly trzy roznice, ktorych zadna
kompilacja nie lapie: preskaler zegara escape dzieli **zegar slowa**, nie bajtowy;
format piksela siedzi w innym polu i ma inne kodowanie; a `DSIM_FUNCRST` jest na
bicie 8, przez co istniejacy test "czy reset zrzuca linie" cicho przestalby
dzialac.

**D-PHY nie ma prawa mieszkac w hoscie.** Jego dwa zakresy MMIO staly w wezle
DSIM jako ABI. Teraz jest osobnym sterownikiem w `drivers/phy/samsung/`, a host
siega po niego przez `phys`/`phy-names`, tak jak `samsung-dsim` i tak juz umial.
Z tych dwoch zakresow tylko jeden nalezy do lacza: generator bias (M4S4) jest
blokiem obok, a SoC ma miejsce na drugi kontroler DSI, wiec drugi wezel PHY
dostalby `-EBUSY` na tym samym oknie. Blok bias jest wiec `syscon`, na ktory
wezly lacz wskazuja phandlem, zamiast wpisywac go sobie w `reg`.

**DECON nie moze byc druga karta.** Stawial wlasne `drm_device` na SoC, ktory ma
juz jedno, i uzywal `drm_simple_display_pipe`, co zamrazalo potok na jednej
plaszczyznie i wymuszalo zla kolejnosc: `atomic_enable` CRTC biegnie **przed**
lancuchem mostkow, wiec DECON byl uzbrajany na sygnal TE panelu, ktory siedzial
jeszcze w resecie. Teraz jest komponentem `exynos_drm` z jawnym CRTC i plane, a
start skanowania przeniesiono do pierwszego `atomic_flush`, ktory w
`drm_atomic_helper_commit_tail_rpm()` biegnie juz po podniesieniu lacza.

Piec parametryzacji, ktore trzeba bylo wprowadzic do wspoldzielonego
sterownika, poszlo osobnymi patchami przygotowawczymi przed wpisem nowego
wariantu, a nie razem z nim: kazdy z nich nie zmienia zachowania zadnego
istniejacego SoC i daje sie przeczytac osobno.

Efekt uboczny, ktory najlepiej pokazuje skale duplikacji: seria po tej
przebudowie jest **krotsza o 68 linii**, mimo ze zyskala pelnoprawny sterownik
PHY.

Reszta uwag: rozbicie patcha z kompatybilnymi SoC na siedem osobnych per
podsystem, scalenie dopiskow do bindingu zegarow z patchem, ktory go wprowadza,
mostek alokowany przez `devm_drm_bridge_alloc()`, przerwanie zadane z
`IRQF_NO_AUTOEN`, flaga `prepared` w panelu i liczenie DSC helperami rdzenia
zamiast druga kopia arytmetyki VESA.

#### Drugi audyt cytowan, na kodzie po przebudowie

Przebudowa architektury stworzyla nowy kod, ktorego bramka twarda nigdy nie
widziala, wiec audyt cytowan poszedl drugi raz, tym razem na sterownik PHY,
tablice `samsung-dsim`, przepisany DECON i DT wyswietlacza. Werdykt: **FAIL,
szesc znalezisk, zero falszywych alarmow.**

Najpowazniejsze nie dotyczylo zadnej stalej z osobna, tylko tego, co z nich
wynika. Po przejsciu na `samsung-dsim` host liczyl predkosc lacza z zegara
pikseli i **nieskompresowanych** 24 bitow na piksel, ignorujac DSC. Wychodzilo
**1592 Mbps**, a sterownik D-PHY ma wiersz timingow wylacznie dla **898 Mbps**,
wiec `.validate` odrzucalby kazde zadanie, PLL nigdy by sie nie zablokowal
i ekran nigdy by nie ruszyl. Kompilacja byla czysta, `checkpatch` zielony,
`dt-validate` bez zastrzezen, a DTB zgadzal sie z wzorcem co do bajtu.
Naprawa to jedna wlasciwosc w DT (`samsung,burst-clock-frequency`), a zeby ta
klasa bledu nie wrocila, doszla bramka `check-link-rate.py`, ktora odtwarza
sciezke wyboru predkosci i sprawdza, czy PHY ma dla niej wiersz.

Pozostale piec: zly indeks zegara w przykladzie bindingu PHY, bity linii escape
przepisane z wpisu innego SoC (linia zegarowa jest na bicie 12, nie 8),
`PLL_TIMER` bez konsumenta skopiowany z exynos5433, oraz komentarz twierdzacy,
ze wzor PLL daje 898 Mbps, podczas gdy daje 897 i producent opisuje ta sama
trojke PMS wezlem `freq_897`.

Przy naprawie **uszkodzilem po drodze cudzy wariant SoC**: nieograniczona
podmiana pierwszego wystapienia w pliku wspoldzielonym trafila w
`exynos7870_dsi_driver_data`. Wykryte porownaniem wszystkich usunietych linii
z baza i przywrocone; od tego momentu podmiany w `samsung-dsim` sa ograniczane
do bloku 9820.

#### Zawartosc

```
docs/            raporty R1-R5, zapisy trzech rund krytyki (R6-krytyk-a.md:
                 audyt cytowan, R7-krytyk-b.md: recenzja glowna,
                 R8-krytyk-c.md: runda na zmienionej powierzchni,
                 R9-krytyk-d.md: runda kompletnosci), podsumowanie
                 (00-summary.md), HW-BLOCKED.md, COVER-LETTERS.md,
                 PC-PIPELINE.md (bramki na PC), UART-BRINGUP.md (sesja przy telefonie)
patches/         40 patchy na mainline (bindingi per podsystem, zegary, DT, panel
                 z dimmingiem, D-PHY jako sterownik PHY, wariant Exynos9820
                 w samsung-dsim, DECON jako komponent exynos_drm, pd-dpu,
                 SYSMMU, PMIC, MAINTAINERS)
patches-oot/     patche na drzewa poza mainline (blok CMU_DPU/CMGP dla drzewa chiffathefox)
build-logs/      logi kazdej bramki i kazdego grepa uzytego jako dowod
measurements/    odczyty ze sprzetu, katalog na sesje (data + etap), z metryka pochodzenia
scripts/golden/  pliki wzorcowe bramek ratchet (zmiana wymaga uzasadnienia w commicie)
SOURCES.md       wszystkie zrodla z przypietymi commitami
scripts/         39 plikow, w czterech grupach.
                 srodowisko: fetch-sources.sh, pc-prepare.sh, cc-kernel.sh,
                 pc-gen-headers.py, pc-mkoffsets.py, sync-to-downloads.sh,
                 kcc-termux.sh, exynos9820.config (fragment konfiguracji jadra)
                 generatory: cmucal-model.py, gen-clk-exynos9820.py,
                 gen-dts-exynos9820.py, gen-dts-beyond2lte.py,
                 gen-pinctrl-exynos9820.py, gen-pinctrl-dts-exynos9820.py
                 bramki (wola je verify.sh): check-aid-tables.py,
                 check-analyzer.sh, check-binding-examples.sh, check-bisect.sh,
                 check-citations.py, check-clk-macros.py, check-clk-parents.py,
                 check-clk-vendor-parents.py, check-cmu.py,
                 check-compatibles.py, check-decon-dsc.py, check-gen-dts.py,
                 check-memory-map.py, check-panel-variant.py,
                 check-dimming-engine.sh, check-doc-refs.py,
                 check-dsc-config.py, check-kconfig.sh, check-link-rate.py,
                 check-regs.py, check-sources-doc.py, dimming-harness/
                 narzedzia pomocnicze: decode-pps.py, ffc-calc.py,
                 dump-init-seq.py
                 spinacz: verify.sh
```

#### Odtworzenie wynikow

```sh
./scripts/fetch-sources.sh     # zrodla wg SOURCES.md do sources/ (idempotentne)
./scripts/pc-prepare.sh        # dtc, .config i naglowki generowane, bez make
./scripts/verify.sh            # wszystkie bramki, ratchet
```

`verify.sh` konczy sie kodem **0** (wszystko przeszlo), **1** (regresja) albo **2**
(przeszlo, ale czesci bramek nie dalo sie uruchomic z braku narzedzi). Kod 2 **nie jest**
zaliczeniem: skrypt wypisuje wtedy, czego nie uruchomil.

Wymagania: `git python3 perl bison flex bc awk sed curl` oraz dwa kompilatory,
kompilator hosta z POSIX-em (`HOSTCC`) i `clang` potrafiacy `--target=aarch64-linux-gnu`.
Bramki schematow DT potrzebuja `dtschema` (`pip install dtschema`). `verify.sh` szuka
jego narzedzi w `.pc-tools/venv` albo w PATH; zalozenie tego venv jest krokiem recznym:
`python3 -m venv .pc-tools/venv && .pc-tools/venv/bin/pip install dtschema`.

Na Windows caly ciag jedzie z powloki MSYS2, bo kbuildowe skrypty potrzebuja POSIX-a:

```sh
/c/msys64/usr/bin/bash.exe -lc "cd <repo> && HOSTCC=/usr/bin/gcc CC=/mingw64/bin/clang sh scripts/pc-prepare.sh"
```

Uwaga na trzy pulapki, ktore kosztowaly realne godziny (opisane w `docs/PC-PIPELINE.md`):
drzewo jadra **nie da sie** wypakowac na katalogu bez rozroznienia wielkosci liter,
`git` musi tworzyc prawdziwe dowiazania symboliczne, a `core.autocrlf` musi byc `false`
**przed** checkoutem, bo inaczej zaden patch serii sie nie naklada.

#### Co jest udowodnione, a co nie

Bramki, ktore przechodza (`build-logs/58-verify-bisect-koniec.log`, **66 bramek, 0 padlo, 0 nieuruchomionych, EXIT=0**, w tym bisectowalnosc):

| bramka | co dowodzi |
|---|---|
| seria stosuje sie na przypieta baze | 40/40 patchy, sekwencyjnie, na czysty `1200d84f4c0a` |
| `checkpatch --strict` | 0 errors, 0 checks, warningi i dlugie linie osobno, kazde pod swoim limitem z `scripts/golden/` |
| cytaty do zrodel | kazdy cytowany plik producenta lezy w `sources/`, kazda cytowana linia istnieje (248 cytatow z numerem linii, 29 sciezek downstreamu); cytat pisany pelna sciezka jest sprawdzany wobec dokladnie tego pliku, takze w `sources/linux` |
| rejestry wobec producenta | 265 z 293 stalych sterownika rozwiazanych po nazwie do naglowkow producenta, 0 niezgodnych; 28 nierozwiazanych przypietych osobnym wzorcem, zeby nowa nierozwiazana stala zapalala bramke |
| predkosc lacza wobec tablicy D-PHY | predkosc, ktora wyliczy host, istnieje w tablicy timingow PHY, miesci sie pod `max_freq` i daje policzalny zegar escape |
| zegary wobec cmucal | 528/528 offsetow i 515 pol (bity bramek, muxy, dzielniki) wobec `cmucal-sfr.c`, 0 niezgodnych |
| drzewo zegarow bez sierot | kazdy z 594 rodzicow w sterowniku wskazuje zegar, ktory ten sterownik rejestruje, albo `oscclk` z DT; identyfikatory kazdego bloku tworza ciag 1..N zgodny z `CLKS_NR_<BLOK>` |
| kazdy wezel DT ma sterownik | 60 wezlow, 52 rozne ciagi `compatible`: kazdy wezel ma co najmniej jeden ciag, ktory wystepuje w tablicy dopasowan jakiegos sterownika w drzewie |
| dtb bajt w bajt | sha256 zgodny z wzorcem |
| `dt-validate` na dtb | odpowiednik `CHECK_DTBS`: 0 naruszen wobec wszystkich schematow jadra |
| `dt-doc-validate` | odpowiednik `dt_binding_check` dla bindingow serii |
| kompilacja arm64 | 10 plikow `.c` serii, clang na arm64, **0 uwag** |
| kompilacja `W=1` | te same pliki z grupa ostrzezen `W=1` kbuilda, **0 uwag** |
| PPS panelu | 128 bajtow zdekodowanych, zgodne w 3 miejscach downstreamu |
| DSC panelu | 30/30 pol sterownika zgodnych z firmowym PPS |
| DSC enkoderow DECON | 14/14 pol modelu helperow rdzenia zgodnych ze wzorem producenta, 4 pola sprzetowe sprawdzone w zrodle |
| tablice AID | 74/74 wiersze zgodne z naglowkami producenta |
| silnik dimmingu | 74/74 poziomy bajt w bajt, 7 zestawow MTP, wobec silnika producenta |
| model FFC, sekwencja init | wynik zgodny z plikiem wzorcowym |
| konfiguracja jadra | fragment `scripts/exynos9820.config` scalony z arm64 defconfigiem: 14 zamowionych symboli ma zadana wartosc, 2 swiadomie wylaczone nie wchodza bokiem przez `select` |
| opis zrodel producenta | kazdy plik w `sources/ds` jest opisany w `SOURCES.md`, z jawna tablica dwoch aliasow |
| spojnosc HW-BLOCKED | kazde `UNVERIFIED` w serii ma pozycje w dokumencie, a pozycja wskazuje ten sam plik |
| pliki DT zgodne z generatorami | oba pliki drzewa urzadzen sa co do znaku tym, co wypisuja `gen-dts-exynos9820.py` (cztery etapy) i `gen-dts-beyond2lte.py` (dwa); trzeci commit na pliku tez zapala bramke |
| mapa pamieci zgodna ze sprzetem | banki `memory@` i kazda rezerwacja porownane bank po banku z blobem `/sys/firmware/fdt` zdjetym z telefonu, adres framebuffera z jego linii polecen |
| wariant panelu tego egzemplarza | `lcdtype` z linii polecen przepuszczony przez tablice `panel-lut` z drzewa telefonu regula producenta: ma wychodzic wariant, z ktorego przepisano tablice do serii |
| odsylacze do patchy | migawka pilnuje, ze `patches/NNNN` w dokumentach wskazuje ten sam patch co wczesniej |
| patche out-of-tree | stosuja sie na przypiete drzewo chiffathefoxa i wnosza komplet identyfikatorow zegarow |
| bisectowalnosc (opcjonalna) | `VERIFY_BISECT=1`: kazdy z 25 punktow serii dotykajacych kodu albo drzewa urzadzen kompiluje sie u siebie, w czterech z nich budowane jest DTB |

Uwaga o wzorcu DTB. Do audytu cytowan wzorzec zgadzal sie **bajt w bajt z buildem
z Termuxa**, czyli z natywnym `make dtbs` na tej samej bazie, i to bylo niezalezne
potwierdzenie, ze potok na PC produkuje te same bajty co prawdziwy build. Audyt wymusil
poprawki w samym DT (adresy `pinctrl_fsys0/1`, okno GICC, `clock-frequency`), wiec hash
sie zmienil i tej rownowaznosci **nie da sie juz odtworzyc bez powtorzenia buildu
na telefonie**. Poprzedni hash lezy w `scripts/golden/dtb.sha256.przed-audytem`, zeby
tamten dowod dalo sie zaudytowac. Od teraz bramka DTB wykrywa regresje, ale nie dowodzi
juz rownowaznosci z natywnym buildem; wroci do tej roli po tym, jak seria zbuduje sie
natywnie na telefonie. Sesja z 11 wrzesnia 2026 tego nie zrobila: byla na stockowym
Androidzie, wiec dolozyla mape RAM-u (hash sprzed niej: `dtb.sha256.przed-mapa-ram`),
a nie build.

Czego bramki **nie** dowodza: ze cokolwiek dziala na krzemie. Lista rzeczy do zmierzenia
na sprzecie jest w `docs/HW-BLOCKED.md`: **36 otwartych**, a cztery zamkniete
11 wrzesnia 2026 odczytem z telefonu (HW-19 adres framebuffera, HW-31 mapa RAM-u,
HW-34 obszary EL2 i KASLR) leza tam w osobnej sekcji z dowodem. Doszla za to jedna nowa,
HW-39: ten sam odczyt pokazal, ze typ wyzwalania przerwan w naszym drzewie rozni sie od tego,
na czym pracuje egzemplarz. Piata, HW-40, powstala i zamknela sie tego samego dnia: panel
zglasza rewizje spoza naglowka, ale producent wybiera wariant tablica z maska, ktora ten bajt
ignoruje, wiec tablice w serii sa wlasciwe. Do czasu pomiaru zadna z otwartych nie jest rozstrzygnieta.

Komentarz `UNVERIFIED:` stoi w serii w **11 miejscach** i pokrywa **12 pozycji**
(jedno miejsce, maska domeny zasilania w DT, nalezy naraz do HW-07 i HW-08). Numeru
pozycji w samym kodzie NIE MA: `docs/HW-BLOCKED.md` nigdy nie trafi do jadra, wiec dla
czytelnika upstream `HW-26` nic by nie znaczylo, a dwa z tych komentarzy siedza we
wspoldzielonym `samsung-dsim.c`. Zwiazek trzyma `scripts/golden/unverified-sites.txt`,
a bramka [6] `verify.sh` pilnuje go w cztery strony: kazdy wiersz mapy musi wskazywac
istniejaca adnotacje, kazda pozycja z mapy musi miec naglowek w dokumencie, liczba
adnotacji w serii musi sie zgadzac z liczba wierszy mapy, a pozycja i wiersz musza
wskazywac ten sam plik. Pozostale 23 pozycje sa udokumentowane wylacznie
w `docs/HW-BLOCKED.md`, bo nie maja jednej stalej w kodzie, przy ktorej mozna by stanac.

#### Stan (skrot z docs/00-summary.md)

- Dotyk: **rozwiazany**, mainline ma `s6sy761`, DT w serii.
- Zegary: **dopisane**, sterownik `clk-exynos9820.c` w serii razem z brakujacymi typami PLL,
  wiec seria nie potrzebuje juz zadnego shimu, zeby sie zbudowac.
- Ekran: pelny lancuch w serii (DECON, DSIM, DSC, D-PHY, panel z AID dimmingiem liczonym
  z MTP). Nie zapalony na sprzecie ani razu.
- GPU: nadal brak bloku CMU_G3D w warstwie zegarow, domena zasilania niezweryfikowana.
- Istnieje dzialajacy generyczny port mainline pmOS (kernel 7.2.0, boot przez U-Boot/EFI),
  ekran tylko jako `simple-framebuffer`, dotyk dziala, 3D/audio/Wi-Fi/bateria nie.
