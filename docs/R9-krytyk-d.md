### R9: runda kompletnosci, czyli co widac dopiero, gdy przestac patrzec na kod

Trzy poprzednie rundy patrzyly na to samo: na patche, na stale rejestrowe i na cytaty.
Ta runda zaczela sie od pytania, ktorego nikt wczesniej nie zadal: **czego nikt nie
obejrzal**. Krytyk kompletnosci policzyl pokrycie szesciu poprzednich soczewek i wyszlo
mu, ze caly wysilek skupil sie na waskim pasie czterech patchy, a `sources/ub`,
`sources/uniLoader` i `sources/pmaports` byly nietkniete przez wszystkich. Wskazal
trzynascie obszarow.

Wniosek, ktory z tego wyszedl, jest niewygodny i wart zapisania osobno: **najwieksze
ryzyko dla pytania "czy telefon wstanie" nie lezalo juz w stalych rejestrowych**, ktore
trzy rundy przekopaly linia po linii, tylko o poziom nizej, w warstwie konfiguracji,
w mapie pamieci i w lancuchu bootloadera. Zadna bramka tej warstwy nie dotykala,
bo zadna bramka o niej nie wiedziala.

#### Cztery rzeczy, ktore mogly skonczyc sie brakiem obrazu przy zielonych bramkach

**1. Jadro bez ani jednego sterownika tej serii.** Seria nie dodaje wpisu
w `arch/arm64/configs`, wiec wszystkie trzy nowe symbole (`DRM_EXYNOS9820_DECON`,
`DRM_PANEL_SAMSUNG_S6E3HA9`, `PHY_EXYNOS9820_DSIM`) sa domyslnie `n`. Defconfig arm64
nie ma tez `REGULATOR_S2DOS05`, `PINCTRL_EXYNOS` ani `EXYNOS_PM_DOMAINS`. Jadro
zbudowane z samego defconfiga kompiluje sie bez jednej uwagi, przechodzi wszystkie
bramki i **nie ma w sobie ani DECON-a, ani panelu, ani D-PHY, ani regulatorow, ktore
ten panel zasilaja**. Panel wisialby na `EPROBE_DEFER` w nieskonczonosc.

Bramka kompilacji tego z konstrukcji nie widzi: podaje pliki kompilatorowi wprost
i nigdy nie pyta Kconfiga, czy te pliki w ogole trafilyby do obrazu.

Zamkniete: `scripts/exynos9820.config` (fragment do scalenia) plus bramka
`scripts/check-kconfig.sh`. Bramka scala fragment z defconfigiem w katalogu tymczasowym
i sprawdza dwie rzeczy: czy kazdy zamowiony symbol po `olddefconfig` ma zadana wartosc
i czy zaden symbol swiadomie wylaczony nie wszedl bokiem przez `select`. Zmierzone:
14 zamowionych, 2 swiadomie wylaczone, 0 rozjazdow, a przy okazji wchodza same
`DRM_SAMSUNG_DSIM`, `DRM_DISPLAY_DSC_HELPER`, `GENERIC_PHY_MIPI_DPHY`, `I2C_EXYNOS5`
i `PINCTRL_EXYNOS_ARM64`.

Trzy testy negatywne, wykonane, nie opisane: symbol zmienia nazwe u gory (EXIT=1),
zaleznosc niespelniona przez zbicie `ARCH_EXYNOS` (siedem symboli naraz, EXIT=1),
symbol swiadomie wylaczony wchodzi bokiem (EXIT=1).

**2. Dziesiec brakujacych obszarow reserved-memory.** Plyta wylaczala z zarzadu jadra
jeden obszar, bufor obrazu. Port dla tej samej plyty lezacy w tym repozytorium wylacza
jedenascie. W chwili, gdy HW-31 zostanie zdjete i powstanie wezel `memory@`, jadro bez
tych wylaczen zaczyna alokowac strony w pamieci hipernadzorcy, modemu i firmware'u
bezpiecznego: zawis albo abort **bez linii na UART**, zanim ktokolwiek zobaczy obraz.

Dopisane wszystkie jedenascie, kazdy z cytatem. Siedem potwierdza drzewo producenta:
`sec_debug_magic`, `mm_debug` i `seclog_mem` z drzewa SoC
(`ds/exynos9820.dts:2885-2892`, `:2980-2983`), `modem_if`, `cp_ram_logging`,
`modem_spare` i `secure_camera` z drzewa plyty
(`ds/exynos9820-beyond2lte_eur_open_26.dts:4490-4503`, `:6727-6734`). Trzy ostatnie,
ziarno KASLR i dwa obszary EL2, ma tylko obcy port
(`ub/exynos9820-common.dtsi:60-72`, `:109-112`) i dostaly wlasny wpis **HW-34** razem
z adnotacja `UNVERIFIED` w drzewie.

Kuszace bylo powiazanie `el2_code@87000000` z baza kodu bootloadera, bo taka wartosc
`CONFIG_TEXT_BASE` ma kilkanascie plyt uniLoadera. Sprawdzone i **odrzucone**: ta rodzina
ma `CONFIG_TEXT_BASE=0x89000000` (`uniLoader/configs/beyond1lte_defconfig:5`). Zostalo
zapisane jako to, czym jest, czyli jako niewiadoma.

**3. Dwa zapisy producenta, ktorych D-PHY nie robil.** Sterownik PHY wypisywal blok
stalych producenta i uznawal robote za skonczona. Producent po tym bloku **nadpisuje
w nim dwa pola**: licznik przesuniecia bufora zegara slowa na 3 (`ds/dsim_reg.c:1893`)
i licznik zatrzasku PLL na 500 razy dzielnik wstepny (`:1903`, przy marginesie zbitym
do zera w `:42`). Blok stalych zostawia w tych polach 0 i 5200, a dla tego lacza wlasciwe
sa 3 i 1000. Dopisane w kolejnosci producenta, razem z uzasadnieniem, czemu nie wystarczy
sam blok stalych.

**4. Bramka bisectowalnosci obiecywala wiecej, niz robila.** `check-bisect.sh` mial
zamknieta liste plikow i brakowalo w niej czterech, ktore seria dotyka:
`pinctrl-samsung.c`, `pinctrl-exynos-arm64.c`, `exynos_drm_drv.c` i `exynos_drm_dsi.c`,
czyli patchy 0007, 0035 i 0037. Osobno: petla kompilowala wylacznie pliki `.c`, wiec
**zadna posrednia wersja drzewa urzadzen nie byla budowana**, a to wlasnie tam zyje
ryzyko kolejnosci: 0039 odwoluje sie do makr z naglowka, ktory wnosi 0011, i do etykiety
`&pd_dpu` z 0038. Lista uzupelniona, doszedl krok budowania DTB dla kazdego commita
dotykajacego `arch/arm64/boot/dts/exynos/`.

#### Cztery zarzuty, ktore po sprawdzeniu upadly

Sceptycyzm dziala w obie strony i te cztery sa tego dowodem.

**Obcinanie adresu bufora obrazu do 32 bitow.** Zarzut: DECON zapisuje baze bufora przez
`lower_32_bits()`, a przy wylaczonym `EXYNOS_IOMMU` nikt nie ogranicza adresu, wiec bufor
przydzielony powyzej 4 GiB dalby po obcieciu adres losowego obszaru. Sprawdzone:
`exynos_drm_gem.c:58` alokuje przez `dma_alloc_attrs(drm_dev_dma_dev(dev), ...)`, czyli
na urzadzeniu DECON-a, a **kazde urzadzenie platformowe utworzone z drzewa urzadzen
dostaje `coherent_dma_mask = DMA_BIT_MASK(32)`** (`of/platform.c:169-171`). Alokator nie
moze wiec zwrocic adresu powyzej 4 GiB i obciecie jest bezpieczne. Zarzut **obalony**,
ale wart komentarza w kodzie, zeby nie wracal.

**Adres bufora obrazu przeniesiony z innej plyty.** Wpis HW-19 mowil, ze 0xca000000 jest
udokumentowane dla beyond1lte i przeniesione bez weryfikacji. To bylo **nieprawda i wpis
zostal sprostowany**: `ub/exynos9820-beyond2lte.dts:17-23` podaje ten adres wprost dla
beyond2lte, z ta sama geometria i tym samym formatem, a `ub/exynos9820-common.dtsi:87-90`
przybija ten obszar jako `no-map`. Trzecie zrodlo, dla plyty siostrzanej, jest po stronie
bootloadera (`uniLoader/configs/beyond1lte_defconfig:8`,
`uniLoader/board/samsung/board-beyond1lte.c:29`). Pozycja zostaje otwarta, bo zadne
z trzech zrodel nie jest odczytem z pracujacego S-Boota, ale jej **uzasadnienie bylo
falszywe**.

**Magistrala PMIC panelu wywnioskowana.** Zarzut: nie wiadomo, czy `hsi2c2` to wlasciwa
magistrala i czy 0x60 to wlasciwy adres, bo producent trzyma ten uklad w nakladce, ktorej
cel jest nierozwiazany. Sprawdzone i **rozstrzygniete z pliku**: tablica `__fixups__`
nakladki wiaze fragment z etykieta, `hsi2c_44 = "/fragment@85:target:0"`
(`ds/exynos9820-beyond2lte_eur_open_26.dts:8271`), a `hsi2c_44 = "/hsi2c@15D50000"`
(`ds/exynos9820.dts:11537`). To dokladnie nasz wezel. Cytat dopisany do DT, zeby nikt
nie musial tego odtwarzac drugi raz.

**Regresja wspoldzielonego `samsung-dsim` u obcych platform.** Zarzut: patch 0033 zamienia
rozroznienie po typie sprzetu na flage w danych sterownika, wiec jesli ktorykolwiek
wariant exynos zostal pominiety, jego panel przestanie sie inicjalizowac. Policzone:
stary predykat obejmowal typy od `DSIM_TYPE_EXYNOS3250` do `DSIM_TYPE_EXYNOS5433`, czyli
piec wariantow, i **dokladnie piec** struktur ma dzis `init_on_first_transfer = 1`
(exynos3, exynos4, exynos5, exynos5422, exynos5433). Warianty 7870, imx8mm, imx8mp
i 9820 flagi nie maja i nie mialy jej wczesniej. Zarzut **obalony**.

#### Bramka DTB: rozjazd wyjasniony pomiarem, nie deklaracja

Wzorzec `scripts/golden/dtb.sha256` przestal sie zgadzac. Zamiast go nadpisac, rozjazd
zostal wyjasniony: stan drzewa sprzed wzorca (`1010f25eafd` z reflogu) zbudowany tym
samym potokiem daje **dokladnie** `ff24dd680cf1...`, czyli hash wzorcowy, a jedyna
roznica wobec stanu biezacego to jedenascie linii w `exynos9820.dtsi`: adres i rozmiar
okna `sysreg_dpu`, poprawione w poprzedniej rundzie z 0x19010000/0x1000 na
0x19011000/0x10. Nic wiecej sie nie zmienilo, wiec nadpisanie wzorca jest uzasadnione,
a nie wygodne. Stary hash zostaje w `scripts/golden/dtb.sha256.przed-sysreg`.

#### Procedura bring-upu przestala byc wykonalna i zostala naprawiona

Soczewka "telefon w reku" znalazla piec rzeczy, przez ktore procedura nie dalaby sie
wykonac. Wszystkie potwierdzone przez otwarcie plikow:

1. **Caly etap 2 byl niewykonalny.** Port pmOS, na ktorym mial sie odbyc, jest zbudowany
   z `# CONFIG_DEVMEM is not set`
   (`pmaports/device/testing/linux-postmarketos-exynos9820/config-postmarketos-exynos9820.aarch64:2727`),
   wiec `/dev/mem` w nim nie powstaje i zadne `devmem` nie zadziala. Dopisane dwa wyjscia,
   oba do przygotowania **przed** sesja: przebudowa pakietu jadra z `CONFIG_DEVMEM=y`
   albo wlasny modul (`CONFIG_MODULES=y`, `:820`).
2. **HW-09 czytal zly rejestr.** Procedura kazala czytac wersje SYSMMU spod poczatku okna,
   gdzie stoi `MMU_CTRL`. `REG_MMU_VERSION` jest pod 0x034 (`iommu/exynos-iommu.c:151`).
   Odczyt spod 0x000 dawalby liczbe, ktora wyglada jak wersja i nia nie jest.
3. **Etap 3 sam sobie przeczyl.** Kazal nie ruszac DECON-a i w tym samym etapie wymuszal
   ramke DECON-a dla HW-15. Przerwania DECON-a przeniesione do etapu 4.
4. **Trzy rozne liczby pozycji zdejmowanych na porcie pmOS.** Dokument mowil siedem,
   HW-BLOCKED osiem, a z naglowkow etapow wychodzilo szesc. Ujednolicone na szesc,
   z wyliczeniem, ktore to sa, zeby liczba byla suma naglowkow, a nie osobnym
   twierdzeniem.
5. **HW-20 stalo w zlym etapie i powtarzalo nieaktualna teze.** Role szyn sa juz ustalone
   instrukcja serwisowa, otwarte zostaly wylacznie odstepy czasowe, a te mierzy sie na
   stockowym Androidzie. Pozycja przeniesiona do etapu 0a, obok HW-31.

Doszedl tez etap wczesniejszy niz wszystkie, bo okazalo sie, ze nie ma czego uruchamiac:
konfiguracja jadra z punktu 1 wyzej oraz **droga drzewa urzadzen do jadra**. uniLoader
trzyma DTB wkompilowany we wlasny obraz (`uniLoader/arch/aarch64/linker.lds.S:41-42`,
`arch/aarch64/start.S:46-47`), a plyty beyond2lte **w ogole nie zna**: w `configs` jest
tylko `beyond1lte_defconfig`, w `board/samsung/` tylko `board-beyond1lte.c`. To warunek
konieczny pierwszego bootu i dzis nie jest spelniony.

#### Dwie decyzje konfiguracyjne, ktore sa decyzjami, a nie przeoczeniem

Fragment konfiguracji zostawia wylaczone `EXYNOS_IOMMU` i `DRM_SIMPLEDRM`, i oba maja
teraz wlasne pozycje, bo oba sa nierozstrzygalne bez sprzetu.

**HW-35, SYSMMU na arm64.** `EXYNOS_IOMMU` robi `select ARM_DMA_USE_IOMMU`
(`iommu/Kconfig:259-264`), czyli wciaga symbol swiata ARM32, podczas gdy na arm64
sterownik DRM idzie druga galezia, przez `IOMMU_DMA`
(`gpu/drm/exynos/exynos_drm_dma.c:109-113`). Tej kombinacji dla tego SoC nikt nie
uruchomil, a wlaczenie jej zmienia caly model adresowania bufora obrazu. Klasa ryzyka:
dziala i przestaje dzialac po zmianie opcji, przy identycznej kompilacji.

**HW-36, przejecie ekranu po simple-framebufferze.** DT deklaruje `/chosen/framebuffer0`,
zeby bootloader zostawil obraz, ale w calym `gpu/drm/exynos/` nie ma ani jednego
wywolania usuwajacego konkurencyjny framebuffer. Z wlaczonym `DRM_SIMPLEDRM` powstalyby
dwa urzadzenia DRM na ten sam ekran i pierwsza sesja bring-upu mogla by wziac zamrozony
obraz S-Boota za obraz z naszego sterownika. To najgorszy rodzaj bledu diagnostycznego,
bo zamyka dochodzenie falszywym sukcesem.

#### Rozjazdy liczbowe w dokumentach

Krytyk zgodnosci znalazl kilkanascie miejsc, w ktorych dokumenty podawaly liczby sprzed
kilku rund. Wszystkie sprawdzone przez uruchomienie odpowiedniej bramki i poprawione:
cytatow 199 zamiast 126, offsetow CMU 528 zamiast 437, stalych rejestrowych 258 zamiast
257, wezlow DT 60 zamiast 59, kompilowanych plikow 10 zamiast siedmiu, pozycji
HW-BLOCKED 36 zamiast 29, wezlow SoC 31 zamiast 30. Osobno: inwentarz skryptow w README
wymienial 21 z 34 plikow, a `SOURCES.md` nie opisywalo siedmiu plikow lezacych
w `sources/ds`.

Ta druga dziura dostala wlasna bramke, `scripts/check-sources-doc.py`, bo suma kontrolna
`sources-ds.sha256` przypina **tresc** plikow producenta, a nie mowi nic o tym, skad one
sa. Czytelnik odtwarzajacy prace dostawal plik bez sciezki w drzewie producenta, wiec nie
mogl sprawdzic ani cytatu, ani commita. Bramka wymaga, zeby kazdy plik z `sources/ds` byl
opisany w `SOURCES.md`, z jawna tablica dwoch aliasow dla plikow trzymanych lokalnie pod
skrocona nazwa. Test negatywny wykonany: usuniecie jednego opisu zapala bramke.

Liczb historycznych w `docs/00-summary.md` **nie ruszono**, bo opisuja, co zmienila
konkretna runda; dopisana jest za to nota, ze sa z tamtej chwili i ze stan biezacy jest
w README i w `docs/PC-PIPELINE.md`.

#### Piata soczewka: piec patchy, ktorych nikt nie przeczytal do konca

Krytyk kompletnosci policzyl, ze poza recenzja zostalo okolo 280 KB serii: 0007
(tablice bankow pinow), 0011 (binding i naglowek zegarow), 0013 (sterownik zegarow),
0019 (silnik gamma z MTP) i 0037 (DECON). Kazdy z tej piatki dostal wlasnego audytora
z jednym zadaniem i limitem wywolan narzedzi, a kazdy raport przeszedl przez sceptyka,
ktorego zadaniem bylo zarzuty **obalic**, nie potwierdzic. Wyszly 34 zarzuty, sceptycy
obalili jeden, jeden uznali za nierozstrzygalny bez sprzetu, reszte potwierdzili
otwarciem wskazanej linii.

Najwiecej, szesnascie, przyniosl DECON, i to on zmienil obraz sytuacji. Dotad
rozumowanie brzmialo: rejestry sa przepisane ze zrodla i porownane bramka, wiec
sterownik jest wierny. Ta soczewka postawila pytanie odwrotne, ktorego zadna bramka
nie zadaje: **czego producent nie robi warunkowo, a my nie robimy wcale**. Brak zapisu
nie zostawia sladu w logu, nie psuje kompilacji i nie ma czego porownac z tablica.

Osiem zapisow, ktore producent wykonuje bezwarunkowo, a nasz sterownik pomijal:

| rejestr | co ustawia | co grozilo |
|---|---|---|
| `CLOCK_CONTROL_0` | bramkowanie zegara blokow wewnetrznych i bity QACTIVE | zapisy do bloku bez zegara przepadaja |
| `SCALED_SIZE_CONTROL_0` | rozmiar obrazu wychodzacego z blendera | zly rozmiar albo brak obrazu |
| `OUTFIFO_TH_CONTROL_0` | prog transferu do DSIM | niedomiar albo przepelnienie FIFO |
| `OUTFIFO_DATA_ORDER_CONTROL` | kolejnosc kanalow | zamienione R i B na sciezce bez kompresji |
| `DSIM_CONNECTION_CONTROL` | ktory interfejs jedzie do ktorego lacza | brak obrazu przy poprawnej reszcie |
| `IDMA_OUT_CON` | alfa ramki dla formatu bez kanalu alfa | czarny obraz przy XRGB8888 |
| `DPU_DMA_QOS_LUT07_00/15_08` | parametry ruchu kanalu na magistrali | niedomiar FIFO pod obciazeniem |
| `IDMA_DYNAMIC_GATING_EN` | dynamiczne bramkowanie kanalu | to samo |

Do tego piec rozbieznosci w tym, co pisalismy:

1. **Sciezka wylaczania nie zadala aktualizacji rejestrow cienia.** `DECON_EN_F` jest
   polem cieniowanym, wiec skasowanie go bez zadania aktualizacji nie robi nic, a
   odpytywanie stanu bezczynnosci moglo tylko wyczerpac swoj limit czasu. Wynik nie byl
   ani sprawdzany, ani logowany, po czym `pm_runtime_put` odcinal zasilanie **pod
   pracujacym blokiem**. Dopisane: zadanie aktualizacji, reakcja na przekroczenie czasu
   i drugi stopien, czyli natychmiastowe zatrzymanie, tak jak u producenta.
2. **Reset kanalu wejsciowego stal w sciezce goracej.** `IDMA_SRESET` byl wydawany przy
   **kazdym** commicie plaszczyzny, a zaraz po nim szly zapisy konfiguracji, bez czekania
   na skasowanie bitu. Producent traktuje ten reset jako operacje deinicjalizacyjna
   i zawsze na nia czeka. Reset przeniesiony do nowej `decon_idma_init()`, wolanej raz
   na wlaczenie zasilania, z odpytaniem i limitem czasu.
3. **Maska zapisu sciezki danych nie obejmowala pola skalera.** Producent zeruje je przy
   kazdej zmianie sciezki. Ze bootloader realnie zostawia ten blok skonfigurowany, dowodzi
   sam producent, ktory sprawdza stan pracy i loguje "already called by BOOTLOADER".
4. **Przerwania kanalu byly ustawiane odwrotnie.** Pisalismy `IDMA_IRQ_FRAMEDONE_MASK`,
   czyli **maskowalismy** zakonczenie ramki, zostawiajac odmaskowanych osiem zrodel bledu,
   przy wlaczonym zezwoleniu i przy linii przerwania DMA, ktorej w ogole nie zadamy w DT.
   Producent odmaskowuje wszystko i kasuje zalegle zgloszenia. Poprawione na zapisy pod
   maska, bo bity zgloszen kasuje sie jedynka, a pelny zapis zostawialby to, co zastal
   bootloader.
5. **Wylaczenie wyzwalacza zostawialo bit zezwolenia zapalony.** Ta sama maska co
   u producenta, odwrotna wartosc jednego bitu.

Zapis calego rejestru `IDMA_IN_CON` zostal zamieniony na zapis pod maska formatu, bo
kasowal przy okazji `IN_IC_MAX`, czyli limit rownoleglych transakcji kanalu, ktorego
producent nie dotyka nigdy.

Osobno doszedl protokol, ktorego nadal **nie mamy w pelni**: producent trzyma wyzwalacz
TE odmaskowany tylko na czas jednej aktualizacji cienia i maskuje go zaraz po niej. My
trzymamy go odmaskowanym na stale. Pelne odtworzenie tego protokolu wymaga wspolpracy
ze sciezka przerwania zakonczenia ramki i nie da sie go sprawdzic bez sprzetu, wiec
zamiast zgadywac doszedl krok posredni: przed wystawieniem nowego zadania sterownik
sprawdza, czy poprzednie zostalo skonsumowane, i mowi o tym w logu, jesli nie. W zdrowym
potoku ten odczyt zwraca zero za pierwszym razem. Pozycja **HW-38**.

#### Zegary: jedna flaga, trzy potwierdzenia i rachunek producenta, ktory sie nie zgadza

Audyt sterownika zegarow potwierdzil to, co bramki juz mierzyly, i znalazl jedna rzecz,
ktorej zadna nie sprawdzala. **Kazdy blok CMU ma bramke wlasnego zegara APB** i wszystkie
mialy flage ochronna, poza jedna: `gout_dpu_dpu_cmu_dpu_pclk` nie mial zadnej. Ten zegar
nie ma konsumenta w drzewie urzadzen, bo jego konsumentem jest sam sterownik zegarow, wiec
`clk_disable_unused` wygasilby go w `late_initcall_sync`, a sciezka runtime PM siegalaby
potem do rejestrow CMU przez zgaszony PCLK przy kazdym wejsciu i wyjsciu domeny `pd_dpu`.

Poprawka nie jest recznym wpisem, tylko regula w generatorze: bramka o ksztalcie
`_<BLOK>_CMU_<BLOK>_IPCLKPORT_PCLK` dostaje `CLK_IGNORE_UNUSED`. Zmienil sie dokladnie
jeden zegar w calym pliku, bo pozostale siedem bylo juz krytyczne z innego powodu.
Wybrane `CLK_IGNORE_UNUSED`, a nie `CLK_IS_CRITICAL`, bo CMU_DPU siedzi w przelaczalnej
domenie zasilania i ma **zero** bramek krytycznych z zalozenia; ten sam wybor ma
mainline'owy `clk-exynos850.c` dla wlasnych PCLK-ow swoich CMU.

Przy okazji audyt wyjasnil, czemu sterownik nie ma **ani jednej** tablicy
`samsung_pll_rate_table`, co samo w sobie wyglada na brak. Powod jest w danych producenta:
wiersz `PLL_G3D` jest wewnetrznie sprzeczny (P/M/S daja 860 MHz, a etykieta mowi
245,76 MHz), a jedyny wiersz `PLL_MMC` ma P rowne zero, czyli dzielenie przez zero we
wzorze, ktory implementuje `clk-pll.c`. Mechaniczne przepisanie tych tablic wciagneloby
oba bledy. Konsekwencja jest realna i warto ja nazwac: bez tablicy PLL dostaje
`samsung_pll0822x_clk_min_ops`, ktore maja wylacznie `recalc_rate`, wiec zaden PLL w tym
sterowniku nie da sie przestroic, a `fout_pll_mmc` zostaje na tym, co ustawil bootloader.

Trzy rzeczy audyt przeliczyl i **nie znalazl nic**: kazda z 50 tablic rodzicow ma
dokladnie dwa do potegi szerokosci pola wpisow (58 par jednobitowych, 34 dwubitowe,
6 trzybitowych, zero tablic nieuzytych), probe obsluguje komplet osmiu blokow z bindingu,
a kolejnosc rejestracji muxow APM przed ich rodzicami typu fixed-rate jest bezpieczna,
bo rdzen CCF przechodzi liste sierot przy kazdej nowej rejestracji.

#### Piny: rozjazd, ktory jest ograniczeniem mainline, nie bledem serii

Audyt tablic bankow pinow porownal trzy liczby dla kazdego z 25 bankow GPIO i znalazl
rozjazd offsetu `FLTCON` dla siedmiu z nich. Zrodlo jest jednak po stronie makra, nie
naszej tablicy: makro `EXYNOS850_PIN_BANK_EINTG` nie ma pola na ten offset, a wspolna
sciezka mainline liczy go jako podwojony offset `ECON`, co lamie sie wszedzie, gdzie
rejestr `FLTCON` obsluguje cztery piny zamiast osmiu. Ten sam wzor lamie sie identycznie
dla exynos850, exynos8895, exynos2200, exynos7885, exynosautov9, fsd i artpec8, i wlasnie
dlatego GS101 dostal osobne pole `eint_fltcon_offset`.

Sceptyk sprawdzil skutek i on jest w tej chwili **zerowy**: sciezka dotyczy wylacznie
zapisu i odtworzenia stanu przy uspieniu, obie strony licza ten sam zly adres, wiec kazdy
rejestr jest odtwarzany ta sama wartoscia, a wyliczone okna pokrywaja komplet realnych
rejestrow kontrolera. Realny koszt to niemoznosc adresowania `FLTCON` per bank, gdyby
kiedys doszedl kod ustawiajacy filtr. Rozwiazaniem byloby przejscie na wzorzec GS101,
czyli zmiana we wspoldzielonym sterowniku pinctrl, wykraczajaca poza te serie. Zapisane
jako **HW-37**.

#### Bramka dimmingu mowila o silniku, a milczala o dekoderze

Najciekawsze znalezisko po stronie bramek. `check-dimming-engine.sh` porownywal 74 poziomy
dla siedmiu zestawow MTP i byl zielony, ale oba harnessy wpisywaly liczby **wprost do juz
zdekodowanej tablicy**, wiec `s6e3ha9_dimming_unpack_mtp` nie byla wolana ani razu.
Gorzej: losowanie dawalo wszystkim punktom wartosci od minus 7 do 7, podczas gdy realny
zakres to plus minus 511 dla V255, plus minus 127 dla punktow srodkowych i 0 do 15 **bez
znaku** dla VT oraz V0. Zaden przebieg nie dotykal wiec scian nasycenia, a punktom VT i V0
podawal wartosci ujemne, ktore w sprzecie nie moga wystapic.

Oba harnessy losuja teraz **surowy ladunek odczytu 0xC8**, ten sam ciag bajtow po obu
stronach, i kazdy rozpakowuje go swoim dekoderem: nasz `s6e3ha9_dimming_unpack_mtp`,
producenta przepisane co do znaku `gamma_ctoi` i `mtp_ctoi`. Porownanie obejmuje teraz
i dekoder, i silnik, a zakres pokrywa caly realny przedzial z definicji, bo dokladnie
z takich bajtow panel sklada odpowiedz. Siedem ziaren nadal daje 74 na 74 zgodnych
poziomow.

Test negatywny, ktorego stara bramka **nie moglaby** zdac: zwezenie maski V255 z dziewieciu
bitow do osmiu w naszym dekoderze. Stary harness nie podawal ani razu wartosci z ustawionym
bitem 8, wiec przeszedlby na zielono; nowy zglasza roznice i konczy sie kodem 1.

Dwie pozostale rozbieznosci w silniku dimmingu okazaly sie swiadome i dostaly komentarze
zamiast poprawek. `s6e3ha9_find_gray` obcina zakres, a producent zwraca blad, ktory
u niego wchodzi wprost jako indeks tablicy, czyli czyta sprzed jej poczatku; dla danych
tego panelu obie sciezki i tak sa nieosiagalne. Indeks szarosci nie ma dolnego
ograniczenia po dodaniu przesuniecia, dokladnie tak jak u producenta; ujemne wpisy siedza
przy punkcie, ktorego docelowa luminancja trzyma indeks w okolicach 200. Dopisanie
ograniczenia rozjechaloby nas z silnikiem, z ktorym sie porownujemy.

#### Dwa zarzuty, ktore po sprawdzeniu wskazaly nie na nas

Sceptyk potwierdzil, ze binding zegarow dla `cmu-fsys0a` wymaga czterech nazw wejsc,
a wezel w obcym porcie ma trzy i drugie z nich nazywa `usb31drd` zegar podpiety pod
wyjscie BUS. Sprawdzone po stronie zrodla: producent ma **trzy osobne wyjscia** CMU_TOP
dla tego bloku (`cmucal-node.c:1282`, `:1318`, `:2838`), wiec nasz binding z czterema
nazwami jest poprawny, a niespojnosc jest w tamtym drzewie.

Drugi: sterownik rejestruje osiem blokow, a nasze drzewo urzadzen tworzy szesc, wiec
CMU_FSYS0A i CMU_FSYS1 nigdy sie nie zarejestruja. To nie jest martwy kod, tylko normalny
podzial: sterownik SoC opisuje SoC, a plyta wlacza to, czego uzywa. Konsekwencja jest
jednak realna i warto ja zapisac: zadna weryfikacja na sprzecie nie dotknie tych dwoch
blokow, wiec ich flagi pozostana niesprawdzone dluzej niz reszta.

#### Co ta runda zostawia otwarte

Trzy rzeczy, ktorych na tej maszynie zamknac sie nie da, i one zostaja nazwane, a nie
zamiecione:

- **Nikt nie zlinkowal jadra.** Bramka kompilacji tluczie plik po pliku. Cykl `select`,
  brakujacy symbol przy linkowaniu modulu i konflikt bool w tristate zostaja niewidoczne
  do pierwszego prawdziwego `make` na maszynie z Linuksem. Jedna z czterech klas tej
  dziury, niespelniona zaleznosc Kconfiga, jest juz zamknieta bramka konfiguracji.
- **Plyta beyond2lte w uniLoaderze nie istnieje.** Trzeba ja dopisac, zanim cokolwiek
  wystartuje.
- **Protokol maskowania wyzwalacza na klatke jest odtworzony tylko czesciowo.** Paczka
  zrodel nie zawiera `decon_core.c`, wiec nie widac, ktorego pomocnika producent wola na
  kazda klatke. Zamiast zgadywac stoi tam krok posredni i pozycja **HW-38**.
- **Offset filtru przerwan bankow pinow rozjezdza sie dla siedmiu bankow**, ale zrodlem
  jest makro wspoldzielone z siedmioma innymi SoC, nie ta seria. Skutek jest dzis
  tozsamosciowy, bo obie strony licza ten sam zly adres. Pozycja **HW-37**.
- **Zaden z tych wyborow nie byl na sprzecie.** To zdanie wraca w kazdej rundzie i dalej
  jest prawdziwe.
