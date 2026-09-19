## R7: recenzja glowna calej serii (Krytyk B)

Szesc soczewek na 39 patchy: bindingi, seria jako calosc, D-PHY i spoiwo,
drzewa urzadzen, podsystemy Samsunga, DRM. Werdykt: **8 BLOKUJACYCH,
37 DO_POPRAWY, 34 DROBIAZGI**.

Kazde znalezisko sprawdzilem osobno na plikach zrodlowych, zanim cokolwiek
ruszylem. Ponizej co sie potwierdzilo, co nie, i co z tego wyszlo. Znaleziska
obalone sa tu razem z dowodem, zeby nikt nie wracal do nich po raz drugi.

### Blokujace: 8 zgloszonych, 6 potwierdzonych, 2 obalone

| # | zarzut | werdykt | co zrobione |
| --- | --- | --- | --- |
| 1 | predykat `samsung_dsim_hw_is_exynos()` odpowiada po pozycji w wyliczeniu, nie po wlasciwosci | potwierdzone | flaga `init_on_first_transfer` w `driver_data`, nadana dokladnie tym pieciu wariantom, ktore makro obejmowalo; osobny patch przed wpisem 9820 |
| 2 | odwolania `HW-nn` w kodzie idacym na liste | potwierdzone | numery usuniete z 10 miejsc i z opisu jednego commita; sledzenie przejela mapa `scripts/golden/unverified-sites.txt` i trzy bramki, ktore pilnuja jej w obie strony |
| 3 | brak wpisu `MAINTAINERS` dla zegarow, bindingu i drzew | potwierdzone | sekcja `SAMSUNG EXYNOS9820 SoC SUPPORT` w commicie z drzewem SoC |
| 4 | wezel DECON siega po rejestry spoza swojego okna, a binding usprawiedliwia to stanem sterownika | potwierdzone | drugie okno to teraz caly blok `DPU_DMA` (0x19070000, 0x10000), nazwa `dma` zamiast falszywej `dpp`; sterownik siega do kanalu przez offset |
| 5 | cicha sciezka bledu przy liczeniu parametrow DSC | potwierdzone | parametry liczone przed wyborem sciezki danych, blad odrzuca tryb juz w `mode_valid()` |
| 6 | kolizja przestrzeni nazw szesciu `CLK_*_CMU_*` z `cmu_apm` | **obalone** | zaden symbol nie jest zdublowany, a `CMU_TOP` nie definiuje ani jednego zegara CMGP czy VTS. Ten sam ksztalt ma mainline: `exynos850.h:119` trzyma `CLK_GOUT_CLKCMU_CMGP_BUS` w sekcji CMU_APM, obok `CLK_GOUT_CLKCMU_APM_BUS` w sekcji CMU_TOP (`:60`) |
| 7 | brak wezla `memory@` w pliku plyty | potwierdzone | nowa pozycja HW-31, adnotacja `UNVERIFIED` w miejscu, gdzie wezel ma stanac, krok 0a w `docs/UART-BRINGUP.md` i akapit w liscie przewodnim czesci D. Mapy **nie zmyslamy**: drzewo producenta podaje 6 GiB w trzech plaskich bankach, a telefon ma 8 albo 12 GiB, wiec to wartosc sprzed lataniny S-Boota |
| 8 | list czesci D mowi "brak zaleznosci", a `dtbs_check` zglosi piec wezlow bez schematu | potwierdzone co do zasady, **liczba obalona** | zmierzone: `dt-validate -m` po usunieciu bindingow czesci A, B i C zglasza **trzy** wezly (DECON, D-PHY, panel), nie piec. Host DSI i blok top D-PHY lapia sie na schematy ogolne. List mowi teraz "trzy" i wymienia je |

Przy okazji zamykania 4 wyszla **dziura, ktorej nie zglosil nikt**: dwukropek
w opisie bindingu DECON-a. Plain scalar w YAML nie moze zawierac `": "`, wiec
`dt-doc-validate` przerywal parsowanie, a `dt-validate` cicho pomijal caly plik
("ignoring, error parsing file"). Binding DECON-a nie byl przez to sprawdzany
w ogole. Poprawione, obie bramki znow go widza.

### Zmiany funkcjonalne z listy DO_POPRAWY

| # | co bylo zle | dowod | poprawka |
| --- | --- | --- | --- |
| 23 | literowka producenta `USE13` w nazwie zegara i w makrze ABI | `cmucal-node.c:1209` mowi `USE13`, ale dzielnik, obie bramki i sam rejestr mowia `USI13` (`:1369`, `:2590`, `:2596`) | `POPRAWKI_NAZW` w generatorze; makro to teraz `CLK_MOUT_PERIC0_USI13_USI_USER` |
| 25 | `exynos_arm64_register_cmu_pm(pdev, false)` pomijal `exynos_arm64_init_clocks()` dla szesciu CMU | kazdy nowszy sterownik Exynosa idzie przez `exynos_arm64_register_cmu()`, ktora wola ja bezwarunkowo (`clk-exynos-arm64.c:260`) | `true`; sprawdzone, ze wszystkie offsety naszych `clk_regs` w zakresie bramek 0x2000-0x2fff to wylacznie `CLK_CON_GAT_*` |
| 28 | `decon_dsc_compressed_width()` rozjezdzala sie ze wzorem producenta | producent inkrementuje PRZED sprawdzeniem warunku (`decon_reg.c:1016-1021`), wiec dla parzystej liczby pikseli dodaje dwa; nasze `while` nie dodawalo nic | `round_up(pixels, 2)` po dodaniu jedynki przy niezerowej reszcie; bramka `check-decon-dsc.py` odtwarza teraz oba wzory i porownuje je na 8192 szerokosciach |
| 29 | `exynos9820_reg_values[]` bez rozmiaru, wbrew uzasadnieniu wlasnego patcha | ta sama dziura, ktora patch "explicit size" zamykal dla `reg_ofs` | enum dostal `NUM_REG_VALUES`, wszystkie szesc tablic dostalo rozmiar; patch nazywa sie teraz "Give the register tables an explicit size" |
| 14 | `power_off` nie zerowal `phy->timing`, wiec bramka "powered on before being configured" lapala tylko pierwsze wlaczenie | mostek zawsze wola `phy_configure()` tuz przed `phy_power_on()` dla wariantu z zewnetrznym PHY (`samsung-dsim.c:1033-1039`), wiec zerowanie niczego nie psuje | `phy->timing = NULL`, `phy->lanes = 0` |
| 12 | kolejnosc zapisow do linii danych inna niz u producenta | producent pisze `MD_GNR` dla wszystkich linii, dopiero potem `MD_ANA` (`dsim_reg.c:583-591`) | dwie osobne petle, kolejnosc zrownana |
| 16 | wezel chipid deklarowal sie jako uklad 9810 | kazdy inny SoC ma wlasny lancuch (`exynos990.dtsi:179`), a binding wylicza je po jednym | nowy patch bindingu `samsung,exynos9820-chipid` plus zmiana w drzewie |
| 19 | `syscon-reboot` z `mask`, bez `value` | sterownik traktuje to jako stary binding i zamienia pola: zapisuje 0x2 na CALE slowo (`syscon-reboot.c:106-109`); `exynos990.dtsi:379-385` podaje oba | dopisane `value = <0x2>` |
| 31 | `s6e3ha9_on()` ustawial `MIPI_DSI_MODE_LPM` drugi raz | wbrew komentarzowi w tej samej funkcji sondujacej, ze host cachuje flagi przy podlaczeniu | linia usunieta |
| 32 | `devm_backlight_device_register()` dostawal `NULL` zamiast wlasciwosci | `props.type` zostawal zerem, a `enum backlight_type` zaczyna sie od `BACKLIGHT_RAW = 1` (`include/linux/backlight.h:45`) | struktura `props` z typem i zakresem jasnosci |
| 37 | wariant deklarowal `min_freq` i `max_freq`, ktorych nikt nie czyta | czyta je tylko `samsung_dsim_pll_find_pms()` (`:880-881`), a nasz wariant idzie przez `set_external_pll()` (`:1086-1089`) | pola usuniete |
| 1 | binding mowil, ze zegar `bus` wszystkich czterech CMU idzie z CMU_TOP | wlasne drzewo karmi CMU_CMGP z CMU_APM (`exynos9820.dtsi:435-436`) | osobna galaz `allOf` dla CMU_CMGP |

### Zmiany redakcyjne i strukturalne

| # | co | poprawka |
| --- | --- | --- |
| 8, 17 | jeden commit wnosil drzewo SoC, piny, plyte i wpis w `Makefile` | rozbite na dwa, jak `exynos990` i `exynos2200` w mainline: "Add initial support for the Exynos9820 SoC" i "Add initial support for the Samsung Galaxy S10+" |
| 6 | opis patcha tlumaczyl podzial zegarow nieistniejacym brakiem identyfikatorow | naglowek dwa patche wczesniej ma komplet dla osmiu blokow; opis mowi teraz o zakresie recenzji |
| 24 | brak wyjasnienia, czemu PCLK kontrolera CMU_DPU nie jest krytyczny, a CMU_CMGP jest | akapit w opisie: blok DPU siedzi w przelaczalnej domenie, zegar krytyczny nie pozwolilby jej zejsc |
| 5 | list czesci A twierdzil, ze gamma, AOR, ELVSS i VINT sa liczone z MTP | liczona jest tylko gamma; AOR, ELVSS i VINT to przepisane tablice producenta |
| 7 | sekcja `MAINTAINERS` nazwana "DRM DRIVERS" wymieniala pliki panelu i D-PHY | pliki panelu wypadly, bo pokrywa je juz `DRM PANEL DRIVERS` (`MAINTAINERS:9011`, `:9013`); nazwa zostaje, bo plik jest posortowany alfabetycznie, a wpisy DRM w mainline wymieniaja tez pliki spoza `drivers/gpu/drm` |
| 10 | tekst pomocy `Kconfig` obiecywal wiecej, niz robi `imply` | `select` nie wchodzi w gre, bo `DRM_EXYNOS_DSI` zalezy od symbolu, ktory mialby go wybierac; tekst mowi teraz, ze host jest wlaczany domyslnie i ma zostac wlaczony |
| 30 | adnotacja przy oknach TE tlumaczyla jedno z trzech wyrazen | komentarz obejmuje teraz takze liczbe transferow (galaz dla strumienia skompresowanego, `dsim_reg.c:1701-1703`) i okno stabilnego wygaszania (`:1262`) |
| 34 | patch z wariantem 9820 wnosil trzy zmiany we wspolnym kodzie, opis wymienial dwie | dopisana trzecia: bramka na pusty wpis w tablicy formatow, nieosiagalna dla wariantow na tablicy wspolnej |
| 3 | opis wlasciwosci w bindingu D-PHY mowil o zachowaniu sterownika | zdanie konczy sie na fakcie o bloku |
| 11 | komentarz opisywal galaz producenta, a nie to, co robi kod | mowi teraz, ze druga galaz (kalibracja skosu powyzej 1500 Mbps) jest nieosiagalna, bo tablica ma jeden wiersz |
| 35, 36 | `DRM_DEV_ERROR` obok `dev_*`, `dev_warn` przy kazdym wywolaniu `mode_valid()` | `dev_err` i `dev_warn_once` |

### Znaleziska obalone

| # | zarzut | dlaczego nie |
| --- | --- | --- |
| 18 | dwa wystapienia hsi2c maja rozne rozmiary okna (0x1000 i 0xc0) | to dwa rozne uklady wezlow: hsi2c10 siedzi pod wezlem USI, ktorego okno konfiguracji zaczyna sie pod +0xc0, hsi2c2 stoi samodzielnie i bierze caly blok, dokladnie jak u producenta (`exynos9820.dts:8234`). Ten sam wzorzec ma przyklad w `i2c-exynos5.yaml:120` i `:140` |
| 20 | grupa pinu TE nie ustawia `pin-pud` ani `pin-drv` | producent tez ich nie ustawia (`exynos9820.dts:2037-2042`); linia jest wejsciem aktywnie sterowanym przez panel, a wymyslenie podciagania byloby wartoscia z powietrza |
| 22 | `eint_gpio_init` przy instancjach bez bankow GPIO | zarzut co do faktow trafny: ani ALIVE, ani CMGP nie ma banku `EINT_TYPE_GPIO`. Nie jest to jednak nasz wymysl: `exynos2200_pin_ctrl[]` nadaje `eint_gpio_init` dokladnie tym samym dwom instancjom, ktorych banki0 to 5x EINTW + 3x EINTN, a banki1 same EINTW (`pinctrl-exynos-arm64.c:92-101`, `:104-111`, `:193-207`). Zostawione zgodnie z najnowszym sterownikiem w mainline |
| 26 | nowe typy PLL to czyste aliasy | tak samo alias jest `pll_0818x` wobec `pll_0822x`, ktore juz dziela `samsung_pll0822x_clk_ops`. Nazwanie rewizji IP po imieniu jest tu regula, a opis patcha cytuje specyfikacje producenta |
| 13 | `.validate` sprawdza wartosci, ktorych sterownik nie programuje | odrzucenie konfiguracji niezgodnej ze specyfikacja MIPI jest poprawne niezaleznie od tego, ktore pola trafiaja do rejestrow; komentarz obok juz mowi, co jest brane |
| 33 | panel deklaruje `MIPI_DSI_CLOCK_NON_CONTINUOUS`, a wariant nie ma `has_clklane_stop` | flaga opisuje, co potrafi panel, nie co robi host. Host bez tej zdolnosci zostawia zegar ciagly, co jest bezpieczne, a opis patcha mowi wprost, czemu bit nie jest ustawiany |
| 4, 21 | `simple-framebuffer` zostaje po dolozeniu prawdziwego potoku | tak samo robi **kazda** plyta Samsunga w mainline (2200-g0s, 7870, 8895-dreamlte, 9810-starlte, 990-x1s, gs101). Przekazanie z simplefb do DRM to sprawa `exynos_drm`, wspolna dla nich wszystkich, nie tej serii |
| 9 | plik panelu tworzony, a dwa patche pozniej przemianowany, "przerabia polowe tego, co dodal" | przemianowanie zostaje (jest skutkiem podzialu na dwa obiekty i `format-patch` pokazuje je jako rename), ale "polowa" to nieprawda: patch dodajacy silnik dimmingu **usuwa 5 linii** z tego pliku przy 176 dodanych dwa patche wczesniej |
| 2 | blok M4S4 jako generyczny `syscon` | blok nie ma wlasnego zegara ani domeny, a jego rejestry dzieli dwoch odbiorcow; wlasny sterownik dla piatki rejestrow biasu byloby wiecej kodu niz opisu. Zostawione swiadomie |

### Drobiazgi: 34 zgloszone, 16 poprawionych

Poprawione, bo kazdy z nich albo mowil nieprawde, albo zostawial czytelnikowi
pytanie:

| # | co | poprawka |
| --- | --- | --- |
| 32 | `devm_phy_optional_get()` przepuszcza brak wezla PHY, a rdzen PHY na `NULL` zwraca sukces z kazdej operacji | bramka za flaga wariantu: wariant z PLL-em w PHY odmawia sondowania bez niego, dla pozostalych osmiu nic sie nie zmienia |
| 31 | adres bufora zapisywany przez `lower_32_bits()` bez slowa o czesci wyzszej | komentarz: producent pisze ten sam jeden rejestr 32-bitowy (`dpp_reg.c:716`), bo bufor idzie przez SYSMMU |
| 29 | komentarz mowil "PPS79..87", a zapisy id, do PPS76..87 | poprawiony na PPS76..87 |
| 9 | `linux/bitfield.h` wlaczony i nieuzywany | usuniety, w pliku nie ma ani `FIELD_PREP`, ani `FIELD_GET`, ani `GENMASK` |
| 19 | banki EINTN deklarowaly `interrupt-controller` | usuniete z `gpq0` i `etc0`, dokladnie jak `exynos2200-pinctrl.dtsi`, gdzie jedyne trzy banki bez tych wlasciwosci to komplet EINTN tamtego SoC |
| 18 | `samsung,pin-function = <3>` gola liczba | `EXYNOS_PIN_FUNC_3` |
| 24 | opisy commitow obiecywaly powtarzalnosc "po ponownym uruchomieniu generatora", ktorego w drzewie jadra nie ma | zdania usuniete z trzech opisow; zostaje to, co sprawdzalne: kazda liczba pochodzi z tablic producenta |
| 23 | opis patcha "Add CMU_DPU and the DPU System MMUs" uzasadnial wylacznie SysMMU | akapit o oknie kontrolera zegarow, jego wejsciu i o tym, czemu stoi poza przelacznikiem domeny |
| 34 | kerneldoc `samsung_dsim_get_dsc()` nie mowil, kiedy wynik jest wazny | dopisane okno zycia: od podlaczenia peryferium do odlaczenia |
| 17 | komentarz podawal 18 MHz jako zegar escape, a drzewo mowi 20 MHz | komentarz tlumaczy teraz, ze 18,7 MHz wychodzi z podzialu w hoscie (`esc_ref_div = 16`), a PHY zegara escape w ogole nie dostaje |
| 4 | nazwa trzeciego przerwania wygladala na worek na wszystko | to nazwa z mapy rejestrow producenta (`EXTRA_INTERRUPT_ENABLE`, `decon_reg.c:2119`); binding to teraz mowi |
| 1 | galaz bindingu wymagala `phys`, a nie wymagala grafu ani domeny zasilania | dopisane `power-domains` i `ports` z `port@0` i `port@1`, jak w sasiednich galeziach |
| 2 | `minItems` rowne `maxItems` | usuniete, dtschema i tak przyjmuje `minItems` z `maxItems` |
| 7 | jedyny plik z copyrightem Samsunga cytowal go bez roku | oba zrodla maja teraz swoj wiersz: `dimming_gamma.h` bez roku i `s6e3ha9_beyond2_a3_s0_panel_dimming.h` z 2016 |
| 11 | ten sam adres pod dwiema nazwami | `DSIM_PHY_PLL_CON0` do `CON4` wyrazone przez `DSIM_PHY_PLL_CON(i)`, liczba stoi raz |
| 25 | `pll_1018x` wstawiony daleko od swojej rodziny | przeniesiony miedzy `pll_1017x` a `pll_1031x` |

Reszta to albo kwestie gustu, albo zarzuty, ktore nie wytrzymaly sprawdzenia:

| # | zarzut | dlaczego zostaje |
| --- | --- | --- |
| 12 | nowy symbol w `Kconfig`/`Makefile` phy nie na swoim miejscu alfabetycznie | ten plik nie jest posortowany alfabetycznie (`PHY_EXYNOS_PCIE` przed `PHY_SAMSUNG_UFS`, potem `PHY_EXYNOS4210_USB2`); nasz wpis stoi przy drugim PHY wideo, czyli w grupie funkcjonalnej |
| 13 | `suppress_bind_attrs` w sterowniku tristate bez `.remove` | tak samo robi **kazdy** sterownik PHY Samsunga w mainline: dp-video, mipi-video, pcie, usbdrd, sata, usb2 |
| 16 | wezel `syscon` bez `power-domains` | `syscon.yaml` dopuszcza wylacznie `compatible`, `reg` i `resets`, a ma `unevaluatedProperties: false`, wiec dopisanie domeny byloby odrzucone przez `dt-validate` |
| 22 | brak nagłowka `irq.h` przy uzyciu `IRQ_TYPE_LEVEL_LOW` | makro przychodzi przez `arm-gic.h`; tak samo robia `exynos990-pinctrl.dtsi`, `exynos850-pinctrl.dtsi` i `exynos2200-pinctrl.dtsi`, ktore uzywaja `IRQ_TYPE_*` i nie wlaczaja `irq.h` |
| 14 | plik nazywa sie `...dsim`, a compatible `...mipi-dphy` | obie nazwy sa prawdziwe: to PHY bloku DSIM. Zmiana dotknelaby `MAINTAINERS`, `Kconfig`, `Makefile` i nic by nie wyjasnila |
| 28 | szesc linii ponad 100 kolumn, trzy z nich to nie `#define` | opis patcha juz mowi o "register define and gate tables", czyli o obu; przelamanie zerwaloby odpowiednioscu jeden do jednego z nazwami rejestrow producenta |
| 21 | `arm,psci` (0.1) z jawnymi numerami funkcji z PSCI 0.2 | co naprawde wystawia S-Boot, wie tylko telefon; zmiana na `arm,psci-0.2` bez pomiaru byloby zgadywaniem, a bledny wybor to brak startu procesorow wtornych |
| 26 | jeden patch dodaje dwa niezwiazane bloki zegarow | CMU_DPU i CMU_CMGP wchodza razem, bo razem sa potrzebne potokowi wyswietlania i razem sie je recenzuje; opis mowi to teraz wprost |
| 3, 5, 6, 8, 10, 15, 20, 27, 30, 33, 35 | kolumna komentarza, nazewnictwo pary naglowek/yaml, drugi `select ... if`, surowe maski, brzmienie zdan | kosmetyka bez skutku dla czytelnika ani dla kodu, zostawiona swiadomie |

### Co z tego wyszlo w liczbach

Seria urosla z 38 do **40 patchy**: doszedl patch bindingu chipid, patch
z flaga `init_on_first_transfer` i podzial drzewa urzadzen na SoC i plyte.

Bramek jest **57, wszystkie przechodza, zero nieuruchomionych**, razem
z bisectowalnoscia (`build-logs/49-verify-po-krytyku-b.log`). Doszly:

* trzy sprawdzenia mapy `scripts/golden/unverified-sites.txt` w bramce [6],
  ktore pilnuja jej w obie strony, w tym zgodnosci LICZBY adnotacji;
* `scripts/check-binding-examples.sh`, czyli odpowiednik `make dt_binding_check`
  dla przykladow: wyciaga je, kompiluje i waliduje, 16 sztuk. Udowodniona, ze
  pada: po wpisaniu do przykladu `reg-names = "dpp"` zglasza
  `reg-names:1: 'dma' was expected` i wychodzi z kodem 1;
* `-m` w `dt-validate`, przez co wezel z compatible spoza wszystkich bindingow
  przestaje przechodzic po cichu.

Bramka DSC porownuje teraz wzor z producentem na 8192 szerokosciach plastra
zamiast szukac cyfry 3 w ciele funkcji, i tez jest udowodniona, ze pada.

Nic z tego nie zostalo uruchomione na telefonie. Lista rzeczy do zmierzenia
ma teraz 31 pozycji.
