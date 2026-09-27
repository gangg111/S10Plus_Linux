### HW-BLOCKED: kolejka rzeczy, ktorych zadna recenzja nie rozstrzygnie

Ten plik jest kolejka pozycji, ktore da sie zamknac **wylacznie pomiarem na sprzecie**
(UART, oscyloskop, odczyt rejestru przez devmem, obserwacja panelu). Zadna recenzja kodu,
zadne porownanie ze zrodlem downstreamu i zaden zielony `scripts/verify.sh` ich nie rozstrzygnie.

Zasady, ktore obowiazuja bez wyjatku:

1. Stala oznaczona tutaj jako niepewna ma w kodzie komentarz `/* UNVERIFIED: ... */`,
   ktory mowi, co jest niesprawdzone i jak to sprawdzic. Numeru pozycji w kodzie NIE MA:
   ten plik nie idzie do jadra, wiec dla czytelnika upstream nic by nie znaczyl, a dwie
   z tych adnotacji siedza we wspolnym `samsung-dsim.c`. Zwiazek adnotacja-pozycja trzyma
   `scripts/golden/unverified-sites.txt`, pilnowany przez bramke [6] `scripts/verify.sh`.
2. Pozycji stad **nie wolno obchodzic modelem ani ekstrapolacja**. Model wolno zbudowac,
   ale jego wynik pozostaje niepewny do czasu pomiaru.
3. Pozycja wypada z tej listy dopiero po potwierdzeniu na sprzecie i **wchodzi wtedy do
   `scripts/verify.sh` jako golden file**, zeby nikt jej pozniej nie cofnal.
4. Werdykt NIEWERYFIKOWALNE od audytora cytowan trafia tutaj, nie do kosza.
5. Ten plik mowi, **co** zmierzyc. Kolejnosc i konkretne polecenia sa
   w `docs/UART-BRINGUP.md`. HW-31, HW-19, HW-34, HW-40 zdjeto na stockowym Androidzie,
   a HW-11 z logu S-Boota z /proc/last_kmsg (sekcja "Zamkniete pomiarem" na koncu tego
   pliku); ten sam log potwierdzil pomiarem wartosci HW-01, HW-02 i HW-03. HW-20 czeka
   na sonde, a cztery dalsze pozycje (HW-23, HW-07, HW-08, HW-09) na istniejacym
   porcie pmOS, zanim w ogole ruszy nasza seria.

Kolumna "waga" mowi, co pozycja psuje, jesli zgadnieta wartosc jest bledna:

* **boot**: zawis albo brak startu (zle SFR, martwy zegar, zla domena zasilania)
* **obraz**: brak obrazu albo obraz uszkodzony, mimo poprawnego bootu
* **jakosc**: obraz jest, ale parametr jest niedokladny (fotometria, DPI, zaklocenia)
* **diagnoza**: bledna wartosc sama nie szkodzi, ale sprowadzi debug na zla sciezke

#### Tabela zbiorcza

| # | pozycja | waga | co zmierzyc |
|---|---|---|---|
| HW-01 | jednostka licznikow D-PHY | obraz | oscyloskop na liniach HS, metoda prob z UART |
| HW-02 | zegar lacza HS: 898 kontra 897,0 kontra 897,6 Mbps | obraz | pomiar bitrate na linii zegarowej D-PHY |
| HW-03 | zegar escape DSI: 18 kontra 20 MHz | obraz | pomiar na wyjsciu dzielnika escape |
| HW-04 | liczba linii w pakiecie TE (0xBE1 = 3041) | obraz | sonda na gpd0-0, test 3041 kontra 3042 kontra 3053 |
| HW-05 | model FFC (stala C = 79153,7) dla zegarow innych niz stockowy | jakosc | porownanie zaklocen dla slowa firmowego i modelowego |
| HW-06 | tablice MTP panelu (odczyt 0xC8) | jakosc | odczyt MTP przez DSI read na zywym panelu |
| HW-07 | maska domeny zasilania DPU (`local_pwr_cfg = 0x1`) | boot | zrzut 0x15861e00 i 0x15861e04 przed i po wlaczeniu |
| HW-08 | `need_smc = 0x191b0204` dla domeny DPU | boot | proba wlaczenia domeny bez SMC i odczyt STATUS |
| HW-09 | wersja i wariant SYSMMU, rozmiar okna 0x9000 | boot | odczyt REG_MMU_VERSION i CAPA0/CAPA1 dla trzech instancji |
| HW-10 | mapowanie grup DPP na SYSMMU D0/D1/D2 | obraz | wymuszony page fault z okna DPP0 |
| HW-11 | rewizja krzemu EVT0 (PLL_CON8 = 0xA28, MC_ANA_CON2 = 0x2) | boot | odczyt chipid i porownanie z progiem EVT0 |
| HW-12 | `initial_dec_delay`: 436 w DECON kontra 616 w PPS panelu | obraz | wzorzec testowy przy obu wartosciach |
| HW-13 | kompletnosc konfiguracji DSC (splitter DSCC, PPS36-55, PPS60-75) | obraz | zrzut okien enkoderow i porownanie ze stockiem |
| HW-14 | czwarte przerwanie DECON (SPI 407) i role pozostalych trzech | diagnoza | liczniki na wszystkich czterech przy ciaglym scan-oucie |
| HW-15 | numery SPI: I2C_CMGP2 (81), SYSMMU (212, 214, 216) | boot | /proc/interrupts kontra wymuszona aktywnosc bloku |
| HW-16 | RCO CMGP i APM: tablica producenta mowi 49,152 MHz, pomiaru brak | diagnoza | odczyt muxa CLK_CON_MUX_MUX_CLK_I2C_CMGP2 i pomiar SCL |
| HW-17 | bity i offsety bramek CMU_DPU i CMU_CMGP (bit 21) | boot | wylaczanie bramki po jednej i test dostepu do SFR |
| HW-18 | brak zegarow krytycznych w CMU_DPU, bo blok jest w domenie zasilania | boot | clk_summary kontra devmem, proba wylaczenia pd_dpu |
| HW-20 | odstepy czasowe miedzy narastaniem szyn panelu (role i kolejnosc juz ustalone) | obraz | pomiar napiec na pinach zlacza w stockowym Androidzie |
| HW-21 | potwierdzenie czasow sekwencji panelu (10 ms i 5 ms ze sterownika producenta) | obraz | sonda na gpa3-4 i szynach vci/vdd3/vddr w stocku |
| HW-22 | wysokosc fizyczna matrycy: 148 kontra 147 kontra 121 mm | jakosc | pomiar suwmiarka aktywnego obszaru |
| HW-23 | oryginalnosc panelu dotykowego w naszym egzemplarzu | diagnoza | odczyt ID firmware na hsi2c10 adres 0x48, evtest |
| HW-24 | domena zasilania G3D (mozliwe SMC do EL3) | boot | proba wlaczenia i log |
| HW-25 | wlasciciel bloku bias D-PHY (czy dzieli go drugi kontroler) | obraz | odczyt BIAS_CON przy pracujacym DSI i CSIS |
| HW-26 | czy bit 0 w LINK_STATUS3 raportuje lock PLL-a spoza lacza | obraz | odczyt 0x14 przed i po zaprogramowaniu D-PHY |
| HW-27 | bit izolacji PMU bloku top D-PHY (0x70c) | obraz | odczyt PMU przed dostepem do 0x19160000 |
| HW-28 | szyna ELVSS panelu, nieobslugiwana przez sterownik S2DOS05 w mainline | obraz | odczyt rejestru wlaczania i napiecia na C12029 w stocku kontra nasze jadro |
| HW-29 | ktore z 533 zegarow nie moga byc wygaszone przez clk_disable_unused | boot | clk_summary przed i po late_initcall, z clk_ignore_unused i bez |
| HW-30 | dzielnik 16 w oknach TE i czy wynik daje obraz bez rozrywania | obraz | wzorzec testowy przy wyliczonych i przy dwukrotnie wiekszych oknach |
| HW-32 | czy bootloader zostawia reset D-PHY zdjety i czy nasza sekwencja jest potrzebna | obraz | odczyt 0x19011008 przed startem jadra i po nim |
| HW-33 | ktore wejscie wybiera mux MUX_CLK_PERIS_GIC, ktorego tablice nie opisuja | diagnoza | odczyt 0x10021000 i porownanie czestotliwosci GIC |
| HW-35 | czy SYSMMU bloku wyswietlania dziala na arm64 i czy z nim obraz nadal jest | obraz | boot z EXYNOS_IOMMU=y, probe trzech sysmmu w logu, ramka na ekranie |
| HW-36 | czy sterownik DECON przejmuje ekran po simple-framebufferze, czy powstaja dwa urzadzenia DRM | diagnoza | boot z DRM_SIMPLEDRM=y, policzenie /dev/dri/card* i sprawdzenie, ktore rysuje |
| HW-37 | czy zapis stanu filtrow przerwan przy uspieniu siega poza opisana przestrzen rejestrow | diagnoza | dmesg po wybudzeniu, odczyt 0x13C40810 i 0x10830840 przed i po |
| HW-38 | czy staly odmaskowany wyzwalacz TE powoduje rwanie obrazu przy commitach | obraz | wzorzec testowy w ruchu, obserwacja rwania, zliczanie ostrzezen sterownika |
| HW-39 | typ wyzwalania przerwan: deklarujemy poziom, egzemplarz pracuje na zboczu | diagnoza | wymuszone zgloszenie na kazdym bloku i licznik w /proc/interrupts |

#### HW-01 Jednostka licznikow D-PHY

**Niepewne.** Wiersz tablicy dla 900 Mbps jest przepisany poprawnie
(`sources/ds/dsim_reg.c:259` daje `{900, 35, 14, 3, 56, 36, 5, 50, 26, 5}`), ale jednostka,
w ktorej wyrazone sa liczniki, nie jest nigdzie udokumentowana. Kontrola na nanosekundy sie
nie domyka: `clk_zero` wychodzi okolo 15,6 ns przy minimum 262 ns wymaganym przez MIPI D-PHY.
Producent sam oznacza te tablice komentarzem, ze wymaga zmiany, zeby spelniala specyfikacje
(`sources/ds/dsim_reg.c:94`). To jest przepisanie, nie zrozumienie, wiec **nie da
sie tego przeliczyc na inny zegar lacza**.

**Zmierzyc.** Oscyloskop albo analizator MIPI na liniach D-PHY: realne T-CLK-PREPARE,
T-CLK-ZERO, T-HS-PREPARE i T-HS-ZERO przy zaprogramowanym wierszu 900. Stosunek pomiaru do
zapisanego licznika porownac z okresem `word_clk` (56 MHz) i z okresem oscylatora 26 MHz.
Metoda zapasowa bez oscyloskopu: zmieniac po jednym liczniku o znana delte i obserwowac,
przy jakiej wartosci panel przestaje odpowiadac, co daje granice w jednostkach licznika.

**Zweryfikowane pomiarem S-Boota (17.09.2026), wartosci potwierdzone bit w bit.** Log
S-Boota tego egzemplarza pokazuje, ze bootloader programuje dokladnie te dziesiec licznikow
(`clk_prepare 35, clk_zero 14, clk_post 3, clk_trail 56, hs_prepare 36, hs_zero 5, hs_trail 50,
lpx 26, hs_exit 5, b_dphyctl 0x1c2`) przy `bps(898)`, po czym panel realnie zaswieca
(`dsim pll is stable`, `PHY ready done`, logo narysowane). Nasza seria pisze te same surowe
wartosci, wiec sa poprawne dla portu niezaleznie od nieznanej jednostki: nie przeliczamy ich
na inny zegar. Formalnie otwarta zostaje sama jednostka fizyczna, ktora ma sens tylko dla
przeliczenia na inny punkt pracy, a takiego nie mamy. Pomiar i porownanie pole po polu:
`measurements/2026-09-17-etap0/dsim-dphy-silicon.md`. Pilnuje `scripts/check-dphy-timing.py`.

**Miejsce w serii:** `drivers/phy/samsung/phy-exynos9820-dsim.c`

#### HW-02 Zegar lacza HS

**Niepewne.** W obiegu sa trzy wartosci dla jednej wielkosci: 898 Mbps (DT), 897,0 Mbps
(arytmetyka PLL: 26 * 138 / (2 * 2^2) * 2, `docs/R2-panel-timings.md:52`) i 897,6 Mbps
(odwrocenie modelu FFC). Wszystkie liczniki pochodne (`word_clk` 56, `esc_div` 3, wybor wiersza
D-PHY, liczniki TE 86 / 8867 / 10102, indeks `b_dphyctl` 11) sa liczone z zaokraglonej 898 z DT.

**Zmierzyc.** Czestosciomierz na linii zegarowej D-PHY przy zaprogramowanym P/M/S = 2/138/2.
Wynik ustala **jedna** wartosc wejsciowa, z ktorej trzeba przeliczyc wszystkie pochodne.

**Zweryfikowane pomiarem S-Boota (17.09.2026), punkt pracy potwierdzony, drut niezmierzony.**
Log S-Boota pokazuje, ze bootloader programuje `P/M/S = 2/138/2` i etykietuje to `bps(898)`,
dokladnie jak nasze DT, a wszystkie liczniki pochodne (`word_clk 56`, `b_dphyctl 0x1c2`, wybor
wiersza D-PHY) zgadzaja sie z bootloaderem co do wartosci. Wybor etykiety 898 jest wiec neutralny
dla rejestrow. Czego log NIE daje: pomiaru czestotliwosci na drucie, wiec spor 897,0 kontra
897,6 kontra 898 jako fizyczna wartosc pozostaje otwarty, ale zmalal z "trzy sprzeczne wartosci"
do "jeden punkt pracy z pod-Mbps etykieta, ktora nie zmienia zadnego zapisu". Pomiar:
`measurements/2026-09-17-etap0/dsim-dphy-silicon.md`. Pilnuje `scripts/check-dphy-timing.py`.

#### HW-03 Zegar escape DSI

**Niepewne.** Zrodla podaja 18 i 20 MHz. Po przejsciu na `samsung-dsim` wartosc zadana
stoi juz tylko w jednym miejscu, we wlasciwosci `samsung,esc-clock-frequency` wezla DSIM
(`patches/0040`), i wynosi 20 MHz. Sprzeczna stala w sterowniku znikla razem z naszym
hostem DSI, ale sam spor trwa: preskaler dzieli **zegar slowa** (lacze przez 16), wiec dla
898 Mbps wychodzi dzielnik 3 i okolo 18,7 MHz, a nie zadane 20.

**Zmierzyc.** Odczyt dzielnika escape na zywym sprzecie plus pomiar czestotliwosci na wyjsciu.
Po rozstrzygnieciu: **usunac sprzeczna stala**, zostawic jedno zrodlo prawdy.

**Zweryfikowane pomiarem S-Boota (17.09.2026), spor rozstrzygniety.** Log S-Boota daje pelny
lancuch odczytany z zywego sprzetu: `requested escape clock 20 MHz`, `escape clock divider is
0x3`, `escape clock is 18 MHz`, plus `b_dphyctl(450)`, czyli wpis tablicy producenta dla escape
18 MHz. To nie sa dwie prawdy, tylko wejscie i wyjscie dzielnika: 20 to wartosc zadana (rowna
temu, co zadaje bootloader i co ma nasza wlasciwosc `samsung,esc-clock-frequency`), 18 to wynik
po dzieleniu przez 3. Nasze DT ma juz jedno zrodlo prawdy (20) i jest ono poprawne. Nasze pole
`ulps_exit = 0x1c2` to niezaleznie ten sam wpis dla 18 MHz. Zostaje otwarta tylko forma zapisu
komentarza UNVERIFIED w serii (do sprzatniecia przy nastepnej rewizji patchy), sama wielkosc jest
rozstrzygnieta. Pomiar: `measurements/2026-09-17-etap0/dsim-dphy-silicon.md`. Pilnuje
`scripts/check-dphy-timing.py`.

**Miejsce w serii:** `arch/arm64/boot/dts/exynos/exynos9820.dtsi`

#### HW-04 Liczba linii w pakiecie TE

**Niepewne.** Wartosc 0xBE1 = 3041 jest przepisana z tablicy panelu
(`sources/ds/s6e3ha9_beyond2_a3_s0_panel.h:809-812`, pakiet `0xB9 0x01 0xB0 0xE1 ...`),
nie wyprowadzona. Arytmetyka z komentarza producenta dla naszych porch daje 3053
(3040 + vbp 15 - 2), a wariant z odjeciem 11 linii daje 3042. Zadna regula nie daje 3041
(`docs/R2-panel-timings.md:384-387`). Dodatkowo pakiet jest dostrojony pod PLL_SLEEP,
a PLL sleep **nie jest** zaimplementowany po stronie DECON i DSIM.

**Zmierzyc.** Sonda na pinie TE (gpd0-0, funkcja 0xf wg `sources/ds/exynos9820.dts:2037-2049`):
odstep zbocza TE od poczatku transferu ramki przy 3041, 3042 i 3053, plus obserwacja tearingu.

**Miejsce w serii:** `drivers/gpu/drm/panel/panel-samsung-s6e3ha9-main.c`

#### HW-05 Model FFC dla zegarow innych niz stockowy

**Niepewne.** Stala C = 79153,7 jest dopasowana empirycznie do 4 punktow wariantu davinci2
(Note10+), nie odczytana z dokumentacji DDI (`scripts/ffc-calc.py:34`). Na jedynym punkcie
kontrolnym beyond2 model myli sie o 7 LSB (przewiduje 0x3DFA, panel ma 0x3E01), wiec blad przy
innych zegarach jest nieznany. Zalozenie, ze bajt [2] jest liniowa skala (0x64 kontra 0xB4),
tez pozostaje hipoteza.

**Nie dotyczy zegara stockowego.** Dla 898 Mbps pakiet `0xC5 0x0D 0x10 0xB4 0x3E 0x01`
przenosi sie 1:1 z panelu i nie wymaga modelu.

**Zmierzyc.** Zaprogramowac panel slowem firmowym 0x3E01 i modelowym 0x3DFA przy 898 Mbps,
porownac zaklocenia. Nastepnie zmienic zegar na 950 Mbps, wyslac przewidziane 0x3A96
i sprawdzic stabilnosc obrazu.

#### HW-06 Tablice MTP panelu

**Niepewne.** Silnik dimmingu liczy gamme z danych MTP **odczytanych z panelu** komenda 0xC8.
Arytmetyka jest udowodniona wobec silnika producenta (74/74 poziomy bajt w bajt dla 7 zestawow
losowych MTP, `build-logs/42-dimming-engine-check.log`), ale **na realnych danych z naszego
egzemplarza nie byla uruchomiona ani razu**, bo wymaga zywego panelu.

**Zmierzyc.** Po pierwszym boocie odczytac 34 bajty MTP komenda 0xC8, zrzucic je przez UART
i przepuscic przez `scripts/dimming-harness` obok silnika producenta. Zrzut MTP zapisac w repo
jako golden file, zeby bramka przestala byc losowa.

#### HW-07 Maska domeny zasilania DPU

**Zawezone po audycie cytowan.** Sama maska **nie jest juz** wywnioskowana: deskryptor PMUCAL
producenta podaje ja wprost, `sources/ds/flexpmu_cal_local_exynos9820.h:287-288` zapisuje
`DPU_CONFIGURATION` pod 0x15860000 + 0x1e00 maska `(0x1 << 0)` i czeka na `DPU_STATUS`
pod + 0x1e04 z ta sama maska. Plik dociagnieto dopiero po audycie, wczesniej cytatu nie
dalo sie otworzyc.

**Niepewne zostaje co innego.** Mainlineowy `exynos_pd_power` zapisuje **cale slowo**
(`writel_relaxed(pwr, base)`,
`sources/linux/drivers/pmdomain/samsung/exynos-pm-domains.c:47`), wiec przy wlaczaniu do rejestru
trafia 0x00000001 i zerowane sa pozostale 31 bitow, o ktorych zadne zrodlo nic nie mowi.
Porownanie STATUS jest maskowane
(`:52`), wiec sam odczyt jest bezpieczny, ale zapis nie.

**Zmierzyc.** Przez UART zrzucic pelne 32 bity 0x15861e00 i 0x15861e04 przed i po wlaczeniu
domeny oraz cale okno 0x15861e00 do 0x15861e1f (rozmiar 0x20 wg `patches/0038`).

**Miejsce w serii:** `arch/arm64/boot/dts/exynos/exynos9820.dtsi`

#### HW-08 need_smc dla domeny DPU

**Niepewne.** Downstreamowy wezel ma `need_smc = <0x191b0204>`
(`sources/ds/exynos9820.dts:3952-3956`), a `docs/R1-cmu-dpu.md:99-101` twierdzi, ze wlaczenie
domeny nie wymaga zadnego SMC. Jesli SMC jest wymagane, `exynos_pd_power` zapisze rejestr,
domena nie wstanie, a polling STATUS skonczy sie timeoutem.

**Zmierzyc.** Proba wlaczenia domeny bez SMC i odczyt STATUS. Jesli nie wstaje, sprawdzic,
czy EL3 wystawia odpowiedni SMC i czy trzeba go dopisac do sterownika domeny.

**Miejsce w serii:** `arch/arm64/boot/dts/exynos/exynos9820.dtsi`

#### HW-09 Wersja i wariant SYSMMU

**Niepewne.** Teza "mainline juz obsluguje SysMMU v7, sterownika nie trzeba pisac" opiera sie na
porownaniu offsetow z downstreamowym naglowkiem. Rozmiar okna 0x9000 dobrano tak, by objac blok
VM pod offsetem 0x8000. Faktyczna wersja na krzemie nie zostala odczytana. Mainline przy
major >= 7 czyta CAPA1 i sam przelacza sie na wariant VM
(`sources/linux/drivers/iommu/exynos-iommu.c:153-155`, `:528-543`).

**Zmierzyc.** Po probe sterownika odczytac REG_MMU_VERSION (major w bitach 31:28, minor 27:21),
REG_V7_CAPA0 (0x870) i REG_V7_CAPA1 (0x874) dla instancji 0x190a0000, 0x190b0000 i 0x190c0000,
oraz sprawdzic w dmesg, ktory wariant wybral sterownik.

#### HW-10 Mapowanie grup DPP na numery SYSMMU

**Niepewne.** Przypisanie D0/D1/D2 wynika wylacznie z kolejnosci indeksow zegarow w downstreamie
(`sources/ds/exynos9820.dts:2992`, `:3009`, `:3026`), a downstream opisuje porty nazwami grup
(VGRFS GF0, VGF GF1, VGS VG WB). Zwiazek numeru SYSMMU z grupa okien DPP pozostaje nieudowodniony,
wiec `iommus` w `decon0` moze wskazywac zla instancje.

**Zmierzyc.** Wlaczyc jedna instancje naraz, uruchomic scan-out z okna DPP0 i sprawdzic, ktora
instancja zglasza page fault (REG_FAULT_ADDR 0x070, REG_FAULT_TRANS_INFO 0x078).

#### HW-12 initial_dec_delay

**Niepewne.** Enkodery DECON dostaja 436 (0x1b4) na sztywno, bo tak robi producent przy
niezdefiniowanym VESA_SCR_V4 (`patches/0037`, cytat `decon_reg.c:1073`), a PPS panelu niesie
616. Obie wartosci maja wlasna zielona bramke (`build-logs/23-dsc-config-check.log` dla 616,
`build-logs/33-decon-dsc-check.log` dla 436) i **zadna bramka ich nie wiaze**. Albo jeden
z enkoderow bedzie zle skonfigurowany, albo skopiowano blad producenta.

**Zmierzyc.** Wzorzec testowy przy 436 i przy 616: bledna wartosc objawia sie przesunieciem albo
poszarpaniem pierwszych linii slice. Rownolegle odczytac licznik underrun DSIM po kilku sekundach.

**Miejsce w serii:** `drivers/gpu/drm/exynos/exynos9820_drm_decon.c`

#### HW-13 Kompletnosc konfiguracji DSC po stronie DECON

**Niepewne.** Patch 0016 implementuje enkodery, ale nie konfiguruje splittera DSCC (w calym
patchu nie ma ani jednego rejestru DSCC, jest tylko selektor sciezki
`DECON_DPATH_DSCC_ENC01_OUTFIFO01_DSIMIF0 = 0x0b1`, `patches/0037`), nie zapisuje slow
PPS36-55 i PPS60-75 (zaklada wartosci resetowe) i nie uzywa zdefiniowanego `DSC_SW_RESET`.

**Zmierzyc.** Po pierwszym modeset zrzucic przez devmem cale okna enkoderow (0x4000 i 0x5000
wzgledem bazy DECON) i porownac slowo po slowie z tym, co programuje stockowy kernel.

#### HW-14 Przerwania DECON

**Niepewne.** Role przypisane numerom 183 (frame-start), 184 (frame-done) i 189 (extra) pochodza
z kolejnosci pobierania w downstreamowym `decon_dsi.c`. Czwarte przerwanie (SPI 407) nie zostalo
zidentyfikowane i nie jest opisane w bindingu, ktory wymaga dokladnie trzech
(`patches/0036`), wiec pozniejsze dolozenie go bedzie zmiana ABI.

**Zmierzyc.** Zarejestrowac wszystkie cztery jako handler zliczajacy, uruchomic ciagly scan-out
i porownac czestotliwosci; zrzucic DECON_INTERRUPT_STATUS przy kazdym.

#### HW-15 Numery przerwan SPI

**Niepewne.** Numery pochodza z chiffathefox/u-boot i z downstreamowego DT, objete jednym
zbiorczym zdaniem w opisie commita (`patches/0014`). `CHECK_DTBS` weryfikuje ksztalt, nie
wartosci. GIC_SPI 81 dla I2C_CMGP2 nie ma cytatu ani w patchu, ani w docs. Dla SYSMMU zalozenie,
ze pierwszy z pary jest przerwaniem nie-bezpiecznym, jest wnioskiem z kodu sterownika, a dla
wezla Abox kolejnosc pary jest odwrotna (`sources/ds/exynos9820.dts:3040`).

**Zmierzyc.** Porownac /proc/interrupts z wymuszona aktywnoscia kazdego bloku (transakcja I2C do
PMIC, ramka DECON, wymuszony page fault). Przerwanie, ktore nigdy nie zlicza, ma zly numer albo
zly typ wyzwalania (port wpisuje IRQ_TYPE_LEVEL_HIGH, downstream deklaruje typ 0).

#### HW-16 Oscylator RCO bloku CMGP

**Czesciowo rozstrzygniete.** Czestotliwosc jest jednak w zrodlach producenta:
`ds/cmucal-node.c:2799` podaje `FIXEDRATE(OSCCLK_RCO_CMGP, 49152000, ...)`, a dla bloku APM
linie 2787-2790 podaja `OSCCLK_RCO_APM`, `CLK_RCO_APM` i `OSCCLK_APM` po 49 152 000 Hz oraz
`CLK_DLL_DCO` 360 000 000 Hz. Sterownik zegarow rejestruje je jako zegary o stalej
czestotliwosci, zamiast podstawiac pod nie 26 MHz oscylator SoC, jak robil to poprzedni port.

Zostaje sam pomiar: tablica producenta to deklaracja, nie odczyt z krzemu, a bootloader moze
zostawic mux na innym wejsciu, niz zaklada model. Wtedy warstwa zegarow zaraportuje falszywa
czestotliwosc magistrali I2C PMIC panelu, a sterownik i tak zglosi sukces.

**Zmierzyc.** Odczytac CLK_CON_MUX_MUX_CLK_I2C_CMGP2 (offset 0x100c) i PLL_CON0 (0x0100),
ustalic rodzica. Jesli RCO, zmierzyc SCL przy znanym dzielniku i wyliczyc RCO wstecz;
oczekiwane 49,152 MHz.

#### HW-17 Bity i offsety bramek CMU_DPU i CMU_CMGP

**Rozstrzygniete ze zrodel, zostaje potwierdzenie funkcjonalne.** To NIE jest juz
ekstrapolacja z jednego przykladu. Po dociagnieciu `sources/ds/cmucal-sfr.c` kazda z 28
bramek ma wlasny wpis `SFR_ACCESS(..._CG_VAL, 21, 1, ...)`, a kazdy offset wlasny wpis
`SFR(...)`; pilnuje tego `scripts/check-cmu.py`, ktory porownuje 437 z 437 offsetow calego
sterownika zegarow, 28 bitow bramek i wszystkie pola muxow i dzielnikow, z zerem niezgodnosci.

**Zmierzyc.** Zostaje jedno: czy bramka pod danym offsetem gasi ten blok, o ktorym mysimy.
Wylaczyc ja i sprawdzic, czy dostep do odpowiadajacego okna SFR zawisa (bramka poprawna),
czy nic nie zmienia (bramka opisuje inny blok). Najwazniejsze 0x2048 (APB DSIM0, od niego
zalezy dostep do rejestrow DSIM) i 0x20e4 do 0x20ec (SYSMMU).

#### HW-18 Flagi bramek CMU_DPU

**Niepewne.** Rodzice przestali byc zgadywani: ida z tablic CAL razem z offsetami i bitami,
a `scripts/check-cmu.py` porownuje kazdy z nich z plikiem producenta. Zostaje polityka flag.
CMU_DPU siedzi w przelaczalnej domenie zasilania, wiec sterownik nie daje mu ANI JEDNEJ bramki
`CLK_IS_CRITICAL` (poprzedni port dawal osiem, w tym PCLK samego CMU i porty AXI, co trzymaloby
zegary domeny wlaczone), a bramki SYSMMU dostaja `CLK_IGNORE_UNUSED`. Za malo zegarow
trzymanych daje zawis magistrali przy `clk_disable_unused`, za duzo blokuje wylaczanie domeny.

**Zmierzyc.** clk_summary po probe kontra odczyt dzielnikow przez devmem; proba wylaczenia
pd_dpu i sprawdzenie w pm_genpd_summary, czy domena przechodzi w off.

#### HW-20 Szyny PMIC S2DOS05

**Niepewne.** Downstream nazywa regulatory vdd1, vdd2 i vdd5
(`sources/ds/exynos9820-beyond2lte_eur_open_26.dts:6529-6552`), wiec przypisanie
buck1 = vddr, ldo1 = vdd3, ldo4 = vci jest **wywnioskowane** z napiec (1,5-1,6 V, 1,8 V, 3,0 V)
i z nazewnictwa bindingu innego panelu (S6E3HA8). Zla kolejnosc wlaczania szyn to typowa
przyczyna braku obrazu, a przy panelach OLED bywa przyczyna uszkodzenia. Osobno: szyna `elvss`
z downstreamu (`:6553-6556`) nie jest opisana ani w bindingu, ani w `patches/0040`.

**Zmierzyc.** Zmierzyc napiecia na pinach zlacza panelu w dzialajacym stockowym Androidzie
i skorelowac z wyjsciami PMIC. Zmierzyc kolejnosc czasowa narastania szyn przy starcie.

**Czesc zamknieta bez sprzetu.** Instrukcja serwisowa (sekcja Level 3 Repair, punkt
8-4-16 Display) podaje szyny panelu z napieciami i punktami pomiarowymi:
VDD_DDI_3P0 = 3,0 V (C12027), VDD_DDI_1P8 = 1,8 V (C12028), VDD_DDR_1P6 = 1,6 V (C12037).
To potwierdza przypisanie rol: vci = 3,0 V, vdd3 = 1,8 V, vddr = 1,6 V, i zaweza szyne
vddr do jednej wartosci. Uwaga: drzewo producenta dopuszcza dla niej ZAKRES 1,5-1,6 V
(`s2dos05-buck1`, `:6529-6535`), czyli uklad potrafi mniej; 1,6 V to wartosc, przy
ktorej ta plyta pracuje wedlug procedury serwisowej. Obok stoja ELVDD 4,6 V (C12039),
ELVSS od -5,4 do -1,4 V (C12029) i ELAVDD 7,6 V (C12036). Wczesniej bylo tu napisane,
ze wytwarza je przetwornica samego panelu i nie sterujemy nimi. To bylo bledne:
drzewo producenta pokazuje na tym samym ukladzie CZWARTY regulator, `s2dos05-elvss`
(`sources/ds/exynos9820-beyond2lte_eur_open_26.dts:6553-6557`), bez ograniczen
napieciowych. Patrz HW-28.

**Kolejnosc zamknieta ze zrodel producenta.** Urzadzenie buduje sie z
`CONFIG_EXYNOS_COMMON_PANEL=y` (`sources/ds/exynos9820-beyond2lte_defconfig:3560`), wiec
zasilaniem panelu steruje `sources/ds/panel_drv.c`, a nie starszy `dsim_set_panel_power()`
z `dsim_drv.c:652`. To rozroznienie jest istotne: obie funkcje maja te sama nazwe i stoja
w tym samym pliku pod `#if`, a ta nieuzywana podaje INNE czasy (5 ms, 5 ms, 10 ms).

`panel_regulator_enable()` (`sources/ds/panel_drv.c:217-240`) podnosi szyny idac po swojej
tablicy od indeksu 0, a tablica jest zadeklarowana jako `PANEL_REGULATOR_DDI_3P0 = 0`,
`PANEL_REGULATOR_DDI_1P8`, `PANEL_REGULATOR_DDR_1P6`, `PANEL_REGULATOR_SSD`
(`sources/ds/panel_drv.h:96-102`). Nazwy wiaza sie z wyjsciami PMIC w drzewie plyty:

| rola | nazwa u producenta | wyjscie S2DOS05 | napiecie |
| --- | --- | --- | --- |
| vci | `ddi-3p0` | `s2dos05-ldo4` | 3,0 V |
| vdd3 | `ddi-1p8` | `s2dos05-ldo1` | 1,8 V |
| vddr | `ddr-1p6` | `s2dos05-buck1` | 1,6 V, w trybie oszczednym 1,5 V |
| (ELVSS) | `short-detect` | `s2dos05-elvss` | prad 2 mA, w trybie oszczednym 8 mA |

Zrodla: `sources/ds/exynos9820-beyond2lte_eur_open_26.dts:6650-6674` (przypisanie rol do
phandle) i `:6528-6558` (te same phandle przy `s2dos05-buck1`, `-ldo1`, `-ldo4`, `-elvss`).
To potwierdza przypisanie, ktore wczesniej bylo wywnioskowane z samych napiec, i ustala
kolejnosc: **vci, potem vdd3, potem vddr**. Wylaczanie idzie w odwrotna strone
(`panel_regulator_disable()` liczy od `PANEL_REGULATOR_MAX - 1` w dol).

**Zostaje do zmierzenia:** same odstepy CZASOWE miedzy narastaniem kolejnych szyn.
Producent nie wstawia miedzy nie zadnego opoznienia, wiec wynikaja z czasu wlaczenia
regulatorow, a nie z kodu.

#### HW-21 Czasy resetu i zasilania panelu

**Rozstrzygniete ze zrodel producenta.** Do tej pory sekwencja byla jedyna rzecza w serii
przepisana ze sterownika INNEGO panelu (`panel-samsung-s6e3ha8.c:56-61`, `:192`), z czasami,
ktore nawet tam sa inne. Sterownik producenta dla tego urzadzenia podaje ja wprost,
`__set_panel_power()` w `sources/ds/panel_drv.c:350-389`:

```
panel_regulator_enable(panel);      /* vci, vdd3, vddr, w tej kolejnosci */
usleep_range(10000, 10000 + 10);    /* 10 ms */
gpio_direction_output(RESET, 1);    /* pin wysoki, czyli reset ZWOLNIONY */
usleep_range(5000, 5000 + 10);      /* 5 ms przed pierwsza komenda DCS */
```

Reset nie jest na tej drodze impulsowany: sciezka wylaczania zostawia go zwartym
(`gpio_direction_output(RESET, 0)` przed wylaczeniem szyn), wiec przy starcie wystarczy go
zwolnic. Nasz sterownik robil trzy rzeczy inaczej: podnosil szyny w zlej kolejnosci, czekal
120 ms zamiast 10 ms i pulsowal resetem 5/10 ms. Poprawione w `patches/0017`.

Osobno wyszlo, ze `regulator_bulk_enable()` NIE nadaje sie do tej rampy: kazda szyne oddaje
do `async_schedule_domain()` i dopiero potem czeka (`drivers/regulator/core.c`), wiec nie ma
zadnej kolejnosci. Rampa w dol kolejnosc ma, odwrotna do tablicy, wiec `regulator_bulk_disable()`
zostaje.

**Zmierzyc (juz nie zeby POZNAC sekwencje, tylko zeby ja POTWIERDZIC).** Sonda na linii reset
(gpa3-4) i na szynach vci, vdd3, vddr w stockowym Androidzie: sprawdzic, czy realne odstepy
zgadzaja sie z tym, co deklaruje kod, bo miedzy `regulator_enable()` a napieciem na szynie
stoi jeszcze czas wlaczenia samego regulatora. Rownolegle skracac czasy, az panel przestanie
startowac, zeby poznac margines.

#### HW-22 Wysokosc fizyczna matrycy  (ROZSTRZYGNIETE)

**Bylo niepewne:** trzy rozne liczby, 148 mm z downstreamowego DT, 147 mm z DT U-Boota
i 121 mm ze starego dpu20. Sterownik przyjmowal 148.

**Rozstrzygniete bez sprzetu.** Instrukcja serwisowa producenta podaje w specyfikacji
produktu przekatna i rozdzielczosc: 6,4 cala, WQHD+, 1440x3040. Przy tej proporcji
przekatna 162,56 mm daje aktywny obszar 69,6 x 146,9 mm, czyli 70 x 147 mm po
zaokragleniu. To samo mowi niezaleznie DT U-Boota. Sterownik poprawiony na 147.

Pomiar suwmiarka jest nadal mile widziany jako kontrola, ale nie jest juz warunkiem:
148 pochodzilo z zaokraglenia w gore w cudzym DT, a nie z pomiaru.

#### HW-23 Oryginalnosc panelu dotykowego

**Niepewne.** Na panelach aftermarket sterownik `s6sy761` probuje sie poprawnie, ale nie generuje
zdarzen dotyku (`docs/R3-touch.md:66-69`, `:76-77`). Nie sprawdzono, czy nasz egzemplarz ma
oryginalny panel, wiec ewentualny brak dotyku zostanie mylnie zdiagnozowany jako blad DT.

**Zmierzyc.** Sprawdzic, czy urzadzenie na hsi2c10 adres 0x48 odpowiada na odczyt ID firmware,
i porownac z wartoscia oryginalnego kontrolera; `evtest` na /dev/input/eventN.

#### HW-24 Domena zasilania G3D

**Czesciowo rozstrzygniete (24.09.2026).** Bootloader zostawia domene wlaczona (PMU 0x15862100
CONFIGURATION = 1, STATUS = 1), a zegar i napiecie GPU prowadzi firmware APM (domena DVFS 10),
wiec CMU_G3D nie jest potrzebne do pracy GPU: panfrost wstaje na tym stanie, GPU_ID 0x72110000
(measurements/2026-09-24-gpu). Wezel GPU w drzewie celowo nie ma `power-domains`.

Otwarte zostaje wylaczanie domeny. Producent wola wokol kazdego cyklu zasilania SMC
0x82000410 z adresem 0x18410204 (need_smc z drzewa producenta) i grupa 2: tryb 0 przed
wylaczeniem (zapis konfiguracji TrustZone bloku), tryb 1 po wlaczeniu (odtworzenie); kod
w exynos-el3_mon.c i cal-if/pmucal_local.c drzewa LineageOS z SOURCES.md. Sterownik domen
w mainline tego nie robi.

**Zmierzyc.** Z dopisanym SMC w sterowniku domen: wylaczenie i wlaczenie domeny G3D, potem
odczyt GPU_ID i test renderu. Bez SMC nie wlaczac `power-domains` w wezle GPU.

#### HW-25 Wlasciciel bloku bias D-PHY

**Niepewne.** Blok M4S4 pod `0x19160000` (0x100) niesie `DSIM_PHY_BIAS_CON`
(`sources/ds/regs-dsim.h:430`) i u producenta jest osobnym wezlem
`samsung,mipi-phy-m4s4-top` obok wezla lacza `samsung,mipi-phy-m4s0`
(`sources/ds/exynos9820.dts:6727` i `:6736`). Poszlaka za wspoldzieleniem jest jedna i slaba: w drzewie producenta stoi DRUGI wezel
o tym samym compatible `samsung,mipi-phy-m4s4-top` i tym samym offsecie izolacji 0x70c
(`sources/ds/exynos9820.dts:4483-4488`, owner = 1, strona CSIS, wobec `:6728-6730`,
owner = 0, strona DPU). Poza tym wezly sie roznia: ten po stronie CSIS ma wlasne
`reg` (0x19160b00), `reset` i `samsung,reset-sysreg`, ktorych wezel DPU nie ma wcale. Wspolna izolacja nie dowodzi jednak
wspolnych rejestrow bias. Nie wiadomo, czy jakikolwiek
DRUGI kontroler realnie siega po ten zakres: SoC dopuszcza dwa kontrolery DSI
(`sources/ds/dsim.h:55`, `MAX_DSIM_CNT 2`), ale w drzewie producenta jest tylko jeden
wezel `dsim@0x19080000` i tylko on zapisuje ten zakres. Wezly D-PHY dla CSIS uzywaja
innych okien (`sources/ds/exynos9820.dts:4487`, `0x19160b00`), wiec nie koliduja.

Opis w DT nie zaklada odpowiedzi: blok jest wezlem `syscon`, na ktory lacze wskazuje
phandlem, co jest poprawne w obu przypadkach. Zalozeniem pozostaje tylko to, ze zapis
stalych bias przy kazdym wlaczeniu lacza jest nieszkodliwy, gdyby blok byl wspolny.

**Zmierzyc.** Po uruchomieniu: odczytac `BIAS_CON0..4` przed i po wlaczeniu lacza
i sprawdzic, czy jakikolwiek inny blok (CSIS) zmienia te rejestry, gdy DSI pracuje.
Jesli tak, programowanie bias musi przeniesc sie tam, gdzie nie powtarza sie per lacze.

**Miejsce w serii:** `drivers/phy/samsung/phy-exynos9820-dsim.c`

#### HW-26 Bit stabilnosci PLL dla PLL-a spoza lacza

**Niepewne.** Host czeka na zaskoczenie PLL-a czytajac `DSIM_LINK_STATUS3` bit 0
(`sources/ds/regs-dsim.h:35-36`). Bit istnieje w naglowku producenta i jego offset nie
zalezy od rewizji krzemu, ale **producent go nigdzie nie czyta**: jedyne realne czekanie
na lock idzie przez `DSIM_PHY_PLL_STAT0` w zakresie PHY (`sources/ds/dsim_reg.c:779`,
wolane z `:798`). Czy ten bit w rejestrze lacza raportuje stan PLL-a, ktory na tym SoC
lezy w osobnym D-PHY, nie zostalo wykazane.

Powod wyboru rejestru lacza: offset `DSIM_PHY_PLL_STAT0` **zmienia sie miedzy rewizjami**
(0x0120 na EVT0, 0x0140 dalej, `sources/ds/regs-dsim.h:442-446`), a ktora rewizje ma ten
egzemplarz, tez nie jest ustalone. Obie drogi maja wiec niezweryfikowany skladnik;
wybrano te, ktorej offset jest staly.

**Zmierzyc.** Po uruchomieniu: odczytac 0x14 przed i po zaprogramowaniu D-PHY i sprawdzic,
czy bit 0 przechodzi z 0 na 1 razem z lockiem. Jesli nie, przeniesc czekanie do sterownika
PHY na `DSIM_PHY_PLL_STAT0`, a rewizje krzemu ustalic wczesniej (patrz pozycja o VPORCH).

**Miejsce w serii:** `drivers/gpu/drm/bridge/samsung-dsim.c`

#### HW-27 Izolacja PMU bloku top D-PHY

**Niepewne.** Producent daje blokowi M4S4 top WLASNY bit izolacji w PMU pod offsetem
0x70c, rozny od bitu bloku lacza M4S0 pod 0x710 (`sources/ds/exynos9820.dts:6729`
i `:6738`). Nic w tej serii tej izolacji nie zwalnia: sterownik PHY siega po blok top
przez regmap, zakladajac, ze jest dostepny, gdy domena DPU jest zasilona.
Zalozeniem jest wiec stan po resecie albo praca bootloadera.

**Zmierzyc.** Odczytac rejestr PMU 0x70c przed pierwszym dostepem do 0x19160000
i sprawdzic, czy izolacja jest zdjeta. Jesli nie, zapisy bias nie dochodza do bloku
i trzeba ja zwolnic, zanim PHY zostanie zaprogramowane.

**Miejsce w serii:** `drivers/phy/samsung/phy-exynos9820-dsim.c`

#### HW-28 Szyna ELVSS panelu, nieobslugiwana przez mainline

**Niepewne.** Uklad zasilania wyswietlacza ma na tej plycie CZTERY wyjscia: drzewo
producenta wylicza `s2dos05-buck1` (vdd1), `s2dos05-ldo1` (vdd2), `s2dos05-ldo4` (vdd5)
oraz `s2dos05-elvss` (`sources/ds/exynos9820-beyond2lte_eur_open_26.dts:6529-6557`).
Sterownik w mainline (`drivers/regulator/s2dos05-regulator.c:93-110`) wystawia tylko
`ldo1`..`ldo4` i `buck`, a naglowek (`include/linux/regulator/s2dos05.h:57-61`) definiuje
bity wlaczania wylacznie dla nich. ELVSS nie jest wiec ani modelowany, ani sterowalny
z mainline, a jest to katoda matrycy OLED: bez niej panel nie swieci.

Nie wiadomo, czy ta szyna wstaje sama (stan po resecie ukladu albo praca bootloadera),
czy wymaga zapisu przez I2C. Jesli wymaga, to sterownik panelu bedzie sie poprawnie
inicjalizowal i zostawial czarny ekran, bez zadnego bledu.

**Zmierzyc.** Odczytac rejestr wlaczania S2DOS05 przez I2C w stockowym Androidzie
i po starcie naszego jadra, i porownac. Rownolegle zmierzyc napiecie na C12029
(ELVSS, oczekiwane od -5,4 do -1,4 V) w obu przypadkach. Jesli w naszym jadrze szyny
nie ma, trzeba dopisac ELVSS do sterownika regulatora w mainline.

#### HW-29 Polityka CLK_IS_CRITICAL i CLK_IGNORE_UNUSED w sterowniku zegarow

**Niepewne.** Tablice CAL nie mowia, ktorego zegara nie wolno wygasic, wiec podzial 533 zegarow
jest decyzja, nie transkrypcja. `CLK_IS_CRITICAL` dostaje tylko szkielet bloku: PCLK samego CMU,
porty magistrali LHM i LHS oraz kontroler przerwan. `CLK_IGNORE_UNUSED` dostaje wszystko
w CMU_TOP i w always-onowym CMU_APM oraz bramki SYSMMU, GPIO, TMU i licznikow magistrali,
bo mainline nie ma jeszcze sterownikow ich odbiorcow. Reszta idzie z flagami zerowymi.

Liczby wychodza inne niz gdziekolwiek indziej i trzeba to powiedziec wprost. Nasz sterownik
ma 24 zegary krytyczne i 156 ignorowanych. Poprzedni port mial 135 krytycznych i ani jednego
ignorowanego. Sterowniki w drzewie: clk-exynos990.c 7 i 20, clk-exynos850.c 19 i 24,
clk-gs101.c 18 i 18.

Roznica wobec drzewa bierze sie z tego, ILE tego SoC prowadzi mainline. gs101 zostawia
wiekszosc bramek CMU_TOP z flagami zerowymi, bo jego bloki maja sterowniki, ktore same
zajmuja swoje zegary. Tutaj mainline nie prowadzi prawie zadnego odbiorcy CMU_TOP, w tym
kontrolera pamieci: bramka `gout_cmu_mif_busp` nie ma kto zajac, a jej wygaszenie zabiera
DRAM. Poprzedni port rozwiazywal to samo przez `CLK_IS_CRITICAL` na komplecie bramek TOP,
czyli twardziej niz my.

Jesli mimo to regula pominie zegar, ktory musi chodzic, `clk_disable_unused` wygasi go
przy late_initcall i system stanie bez zadnego komunikatu.

**Zmierzyc.** Wystartowac dwa razy, raz z parametrem `clk_ignore_unused` i raz bez, i porownac
`/sys/kernel/debug/clk/clk_summary`. Kazdy zegar, ktory znika tylko w drugim przebiegu, a blok
po tym przestaje odpowiadac na dostep do SFR, dopisac do listy trzymanych.

#### HW-30 Okna czasowe TE liczone z predkosci lacza

**Niepewne.** W trybie komend host pilnuje dwoch okien: `TIME_TE_PROTECT_ON`
i `TIME_TE_TOUT`. Wyliczamy je z predkosci lacza, przepisujac wzor producenta.

Dwa z trzech skladnikow tego wzoru sa udokumentowane. Producent podaje przy nich
znaczenie w milisekundach: `#define TE_PROTECT_ON_TIME 158 /* 15.8ms*/` i
`#define TE_TIMEOUT_TIME 180 /* 18ms */` (`sources/ds/dsim_reg.c:38-39`), a wlasne
notatki serii rozpisuja calosc razem z przykladem (`docs/R2-panel-timings.md:403-410`).

Nieudokumentowany jest trzeci skladnik: **dzielenie przez 16**, ktore zamienia te
milisekundy na jednostki rejestru. Zadne dostepne zrodlo nie mowi, skad ta liczba,
a wynik nigdy nie byl sprawdzony na pracujacym panelu. Za male okno daje rozrywanie
obrazu przy szybkich zmianach, za duze potrafi zablokowac wyzwalanie ramki.

Wczesniej komentarz w kodzie powolywal sie tutaj na HW-04, ale HW-04 dotyczy liczby
linii w pakiecie TE panelu, a nie okien czasowych hosta. Audyt cytowan to wychwycil.

**Zmierzyc.** Wzorzec testowy z ruchoma krawedzia przy wyliczonych oknach, potem
przy dwukrotnie wiekszych i dwukrotnie mniejszych. Rozrywanie albo zatrzymanie
obrazu wskaze, ktora strona wzoru jest zla.

**Miejsce w serii:** `drivers/gpu/drm/bridge/samsung-dsim.c`

#### HW-32 Reset D-PHY w rejestrach systemowych bloku wyswietlania

**Niepewne.** Producent przy kazdym wlaczeniu lacza zaklada reset bloku M4S4,
programuje PLL i linie, po czym reset zdejmuje, a przy wylaczeniu zaklada go
z powrotem (`sources/ds/dsim_reg.c:2197`, `:2211`, `:2272`). Robi to przez jeden
rejestr rejestrow systemowych bloku wyswietlania, `DISP_DPU_MIPI_PHY_CON` pod
offsetem 0x8 od okna, ktore mapuje, czyli od 0x19011000
(`sources/ds/exynos9820.dts:6714-6716` wobec `dpu20/helper.c:568-585`, gdzie
`dpu_get_sysreg_addr()` bierze ten wezel po compatible i robi `of_iomap`).
Uzywa bitu `M_RESETN_M4S4_MODULE` dla DSIM0 i czysci bit wyboru zrodla resetu,
ktory dla lacza 0 jest bitem 5, bo wywolanie odwraca indeks
(`sources/ds/regs-decon.h:19` wobec `sources/ds/dsim_reg.c:2132`).

Seria robi teraz to samo, w tej samej kolejnosci
(`drivers/phy/samsung/phy-exynos9820-dsim.c`, `exynos9820_dsim_phy_reset()`).
Wartosci sa przepisane, wiec nie sa zgadniete. Niepewne jest co innego:

* czy bootloader zostawia ten reset zdjety, czy zalozony. Jesli zdjety,
  nasza sekwencja jest niepotrzebna, ale nieszkodliwa; jesli zalozony, to bez
  niej PHY w ogole nie odpowiada i nie ma po tym zadnego sladu w logu;
* czy zakladanie resetu przy wylaczaniu nie gasi obrazu, ktory zostawil S-Boot,
  wczesniej niz zajmie sie nim nasz potok.

**Zmierzyc.** Przez UART albo `devmem` na dzialajacym porcie pmOS odczytac
0x19011008 przed uruchomieniem naszego sterownika i po nim. Bit 1 ustawiony
znaczy reset zdjety. Porownac ze stanem po starcie samego S-Boota.

**Miejsce w serii:** `drivers/phy/samsung/phy-exynos9820-dsim.c`

#### HW-33 Mux zegara GIC bez pola wyboru w tablicach

**Niepewne.** `MUX_CLK_PERIS_GIC` ma rejestr, `CLK_CON_MUX_MUX_CLK_PERIS_GIC`
pod offsetem 0x1000 w CMU_PERIS (`sources/ds/cmucal-sfr.c:348`), ale tablice
opisuja przy nim wylacznie pola BUSY i automatycznego bramkowania
(`:3372-3373`). Pola wyboru nie ma. Sterownik nie ma wiec czego czytac ani
pisac i tego muxa nie rejestruje.

Jego wejscia to `MUX_CLKCMU_PERIS_BUS_USER` i `OSCCLK_PERIS`
(`sources/ds/cmucal-node.c:976-979`), a odbiorcami sa dwa zegary, ktore
producent podpina wlasnie pod ten mux (`:2692` i `:2694`): zegar kontrolera
przerwan i jeden z portow magistrali. Nasz sterownik podpina je pod pierwsze
wejscie, czyli pod zegar magistrali.

**Czym to grozi.** Nie bramkowaniem, bo bramki sa osobne i zgadzaja sie
z tablicami. Grozi bledna CZESTOTLIWOSCIA raportowana dla zegara GIC: jesli
sprzet wybiera oscylator, to 26 MHz zamiast zegara magistrali. Kod, ktory
liczy z tej czestotliwosci opoznienia, dostanie zla liczbe.

**Zmierzyc.** Odczytac 0x10021000 na dzialajacym porcie pmOS i porownac
z `clk_summary` dla `gout_peris_gic_clk`. Bity wyboru sa nieudokumentowane,
wiec dowodem bedzie zgodnosc czestotliwosci zmierzonej z jednym z dwoch wejsc,
a nie sama zawartosc rejestru.

**Ten sam przypadek w CMU_AUD.** `MUX_HCHGEN_CLK_AUD_CPU` ma rejestr pod
0x101c (`sources/ds/cmucal-sfr.c:347`) i tylko pola BUSY i automatycznego
bramkowania (`sources/ds/cmucal-sfr.c:3370`). Wejscia: `MUX_CLK_AUD_CPU`
i `OSCCLK_AUD` (`sources/ds/cmucal-node.c:972`), odbiorcy: trzy dzielniki
zegarow rdzenia audio i bramka CA32 (`sources/ds/cmucal-node.c:1244`,
`sources/ds/cmucal-node.c:1480`). Sterownik podpina je pod `mout_aud_cpu`.
Zmierzyc tak samo: odczyt 0x18c0101c przy wlaczonej domenie AUD i porownanie
z `clk_summary`. Czestotliwosc tych zegarow nic nie znaczy, dopoki rdzen DSP
audio nie jest uruchamiany.

**Miejsce w serii:** `drivers/clk/samsung/clk-exynos9820.c`

#### HW-35 SYSMMU bloku wyswietlania na arm64

**Niepewne.** DT deklaruje trzy jednostki SYSMMU dla DECON-a
(`sysmmu_dpud0`, `sysmmu_dpud1`, `sysmmu_dpud2` w `patches/0039`, podpiete
przez `iommus` w `patches/0040`), ale fragment konfiguracji
`scripts/exynos9820.config` zostawia `CONFIG_EXYNOS_IOMMU` wylaczone i to jest
decyzja, nie przeoczenie.

Powod jest w Kconfigu: `config EXYNOS_IOMMU` robi `select ARM_DMA_USE_IOMMU`
(`sources/linux/drivers/iommu/Kconfig:259-264`), czyli wciaga symbol swiata
ARM32, podczas gdy na arm64 sterownik DRM idzie druga galezia, przez `IOMMU_DMA`
(`sources/linux/drivers/gpu/drm/exynos/exynos_drm_dma.c:110-114` rozgalezia sie
dokladnie na tych dwoch symbolach). Tej kombinacji dla tego SoC nikt nie
uruchomil, a wlaczenie jej zmienia caly model adresowania bufora obrazu: bez
IOMMU DECON dostaje adres fizyczny, z IOMMU adres wirtualny magistrali.

Jest tu zaleznosc kolejnosci, ktora tez trzeba sprawdzic pomiarem: domena
`pd_dpu` musi byc wlaczona, zanim SYSMMU zrobi probe, bo inaczej sterownik
czyta rejestry martwego bloku.

**Czym to grozi.** Klasa "dziala i przestaje dzialac po zmianie opcji": obraz
moze byc bez IOMMU i zniknac po jego wlaczeniu albo odwrotnie. Zadna bramka
tego nie zobaczy, bo obie konfiguracje kompiluja sie tak samo.

**Zmierzyc.** Zbudowac i uruchomic obie konfiguracje. Krok pierwszy, najtanszy:
z `CONFIG_EXYNOS_IOMMU=y` sprawdzic w logu, czy trzy sysmmu w ogole robia probe
i czy `exynos_drm_register_dma` zwraca zero. Krok drugi: ramka na ekranie w obu
konfiguracjach.

#### HW-36 Przejecie ekranu po simple-framebufferze

**Niepewne.** DT plyty deklaruje `/chosen/framebuffer0` i przybija ten obszar
jako `no-map`, zeby bootloader zostawil obraz do czasu, az wystartuje nasz
sterownik. Nie ma jednak kodu, ktory ten obraz przejmuje: w calym
`sources/linux/drivers/gpu/drm/exynos/` nie ma ani jednego wywolania
`aperture_remove_conflicting_devices` ani `drm_aperture_remove_framebuffers`.

Z wlaczonym `CONFIG_DRM_SIMPLEDRM` powstana wiec dwa urzadzenia DRM na ten sam
ekran. Userland moze otworzyc to zamrozone i uznac, ze ekran dziala, albo
odwrotnie. Dlatego fragment konfiguracji zostawia SIMPLEDRM wylaczone, co jest
decyzja tymczasowa: kosztem jest brak obrazu miedzy bootloaderem a startem
DECON-a.

**Czym to grozi.** Nie brakiem obrazu, tylko blednym rozpoznaniem: pierwsza
sesja bring-upu moze zobaczyc obraz S-Boota i wziac go za obraz z naszego
sterownika. To najgorszy rodzaj bledu diagnostycznego, bo zamyka dochodzenie
falszywym sukcesem.

**Zmierzyc.** Uruchomic z `CONFIG_DRM_SIMPLEDRM=y` i policzyc `/dev/dri/card*`.
Jesli powstaja dwa, sprawdzic, ktore rysuje, wypisujac wzorzec przez oba.
Rozstrzygniecie decyduje, czy do serii dochodzi wywolanie usuwajace
konkurencyjny framebuffer, czy SIMPLEDRM zostaje wylaczony na stale.

#### HW-37 Offset filtru przerwan bankow pinow

**Niepewne.** Producent trzyma dla kazdego banku pinow DWA offsety przerwan: sterowania
(`ECON`) i filtru (`FLTCON`), i podaje oba wprost w tablicy
(`sources/ds/pinctrl-exynos-arm64.c:664`, szosty argument makra). Makro, ktorego uzywa
nasza tablica, `EXYNOS850_PIN_BANK_EINTG`, przyjmuje tylko pierwszy z nich
(`sources/linux/drivers/pinctrl/samsung/pinctrl-exynos.h:163-171`), a wspolna sciezka
mainline wylicza drugi jako podwojony pierwszy
(`sources/linux/drivers/pinctrl/samsung/pinctrl-exynos.c:886-891`).

To wyliczenie lamie sie za kazdym bankiem, ktorego rejestr filtru obsluguje cztery piny
zamiast osmiu, bo taki bank zjada cztery bajty, a nie osiem. Dla tego SoC rozjezdza sie
siedem z 25 bankow GPIO: gpf3 (0x10 wobec 0x0C u producenta), gpc0 (0x18 wobec 0x14),
gpc1 (0x20 wobec 0x1C), gpd0 (0x28 wobec 0x24), gpg3 (0x30 wobec 0x28), gph0 (0x38 wobec
0x30) i gph1 (0x40 wobec 0x38).

**Czym to NIE grozi i to jest tu najwazniejsze.** To nie jest blad wniesiony przez ta
serie, tylko ograniczenie makra przyjete w calym mainline: ten sam wzor lamie sie
identycznie dla exynos850, exynos8895, exynos2200, exynos7885, exynosautov9, fsd
i artpec8, i wlasnie dlatego GS101 dostal osobne pole `eint_fltcon_offset`
(`sources/linux/drivers/pinctrl/samsung/pinctrl-exynos.h:217-224`). Sciezka jest uzywana wylacznie przy uspieniu i wybudzeniu,
dla bankow typu GPIO, wiec nie dotyka ani bootu, ani zwyklej pracy. Poniewaz zapis
i odtworzenie licza ten sam zly adres, kazdy rejestr wraca ta sama wartoscia, a wyliczone
okna sa ciagle i pokrywaja komplet realnych rejestrow kontrolera. Efekt netto na
zawartosc rejestrow jest wiec tozsamosciowy.

**Czym grozi naprawde.** Dwoma rzeczami. Pierwsza: gdyby kiedys doszedl kod ustawiajacy
filtr przerwania per bank (`exynos_eint_set_filter`), dla tych siedmiu bankow trafialby
w cudzy rejestr. Druga: dla ostatniego banku w dwoch kontrolerach wyliczony adres wychodzi
poza obszar, ktoremu producent przypisuje jakikolwiek bank, czyli FSYS1 +0x10..0x17
i PERIC1 +0x40..0x47. Adresy nadal mieszcza sie w stronie filtrow, wiec nie moga nadpisac
maski przerwan, ale sa to zapisy do przestrzeni rejestrowej nieopisanej po stronie
producenta.

**Zmierzyc.** Po wybudzeniu z uspienia do RAM sprawdzic `dmesg` pod katem bledu magistrali
podczas wznawiania oraz odczytac 0x13C40810 i 0x10830840 przed uspieniem i po nim. Odczyt
zwracajacy zero i brak bledu zamyka pozycje jako nieszkodliwa; blad magistrali oznacza,
ze te siedem bankow trzeba przeniesc na wzorzec GS101, czyli zmienic wspoldzielony
sterownik pinctrl, co wykracza poza te serie.

#### HW-38 Protokol maskowania wyzwalacza na klatke

**Niepewne.** Producent odmaskowuje wyzwalacz TE tylko na czas jednej aktualizacji
rejestrow cienia i maskuje go zaraz po jej zakonczeniu: `decon_reg_update_req_and_unmask`
wystawia zadanie i odmaskowuje (`sources/ds/decon_reg.c:1963-1969`), a
`decon_reg_wait_update_done_and_mask` czeka, az rejestr zadania wroci do zera, i maskuje
z powrotem (`:1987-1998`).

Nasz sterownik uzbraja wyzwalacz raz, przy pierwszym wypchnieciu klatki, i trzyma go
odmaskowanym na stale. Sygnal TE z panelu moze wiec trafic w srodek aktualizacji
rejestrow okna i pokazac klatke zlozona po polowie ze starych i nowych parametrow.

**Czego brakuje do rozstrzygniecia.** Paczka zrodel nie zawiera `decon_core.c`, wiec nie
widac, ktorego z dwoch pomocnikow producent wola na kazda klatke, a ktorego tylko przy
zmianie trybu. Bez tego pelne odtworzenie protokolu byloby zgadywaniem, a ono wymaga
zmiany wspolpracy ze sciezka przerwania zakonczenia ramki.

**Co zrobiono zamiast.** Krok posredni, ktory nie zmienia protokolu, a zamienia cicha
awarie w linie w logu: przed wystawieniem nowego zadania sterownik sprawdza, czy
poprzednie zostalo skonsumowane, i ostrzega, jesli nie. W zdrowym potoku ten odczyt
zwraca zero za pierwszym razem.

**Zmierzyc.** Wzorzec testowy w ruchu przy stalym strumieniu klatek, obserwacja rwania,
i rownolegle zliczanie ostrzezen z tej sciezki. Zero ostrzezen i brak rwania zamyka
pozycje; ostrzezenia albo rwanie oznaczaja, ze trzeba odtworzyc pelny protokol z
maskowaniem na kazda klatke.

#### HW-39 Typ wyzwalania przerwan

**Niepewne.** Nasz plik SoC opisuje **kazde** przerwanie jako wyzwalane poziomem: 35 wpisow
`IRQ_TYPE_LEVEL_HIGH` i 4 `IRQ_TYPE_LEVEL_LOW` w
`arch/arm64/boot/dts/exynos/exynos9820.dtsi`. Egzemplarz pracuje inaczej. W drzewie, ktore
bootloader podaje jadru producenta, typ jest **nieokreslony** prawie wszedzie: na 458 trojek
we wlasciwosciach `interrupts` az 441 ma trzecia komorke `0x00`, czyli `IRQ_TYPE_NONE`
(`measurements/2026-09-11-etap0a/stock-fdt.dts`; osiem ma `0x04`, reszta to pojedyncze
przypadki i maski rdzeni dla PPI). Skutek widac w pracujacym systemie: 256 linii jest
zarejestrowanych jako `Edge`, a tylko 33 jako `Level`
(`measurements/2026-09-11-etap0a/interrupts.txt`).

**To nie jest powod, zeby przepisac zero od producenta.** Poziom wysoki to konwencja calego
mainline dla tej rodziny: tak opisuja swoje przerwania exynos5433 (108 wpisow), exynos8895
(92), exynos850 (54), exynos990 (28) i kazdy inny plik SoC Exynos w drzewie. `IRQ_TYPE_NONE`
u producenta nie znaczy "zbocze", tylko "nie ustawiam"; to, ze jego jadro konczy z `Edge`,
mowi o domyslnej konfiguracji kontrolera, nie o tym, jak peryferium zglasza sygnal.

Pozycja jest tu dlatego, ze nasz port **twierdzi** cos, czego na tym sprzecie nikt nie
sprawdzil, a rozjazd z jedynym dzialajacym systemem na tej plycie jest faktem. Zly typ daje
albo burze przerwan (linia poziomowa obsluzona jak zboczowa zostaje aktywna), albo zgloszenie,
ktore nigdy nie dochodzi. Na liniach, ktore realnie pracuja, czyli i2c panelu i wyzwalaczu TE,
oba warianty koncza sie brakiem obrazu albo zawieszeniem.

**To nie jest pytanie o linie, ktore i tak milcza.** Odczyt z telefonu pokazuje, ze chodzi
o linie z realnym ruchem: start i koniec ramki DECON-a licza po 6045 zdarzen, a przerwanie DSIM
41618, i wszystkie trzy sa tam zarejestrowane jako `Edge`
(`measurements/2026-09-11-etap0a/interrupts.txt`). Zla decyzja o typie uderzy wiec w sciezke,
ktora chodzi przy kazdej klatce, a nie w rzadki przypadek bledu.

**Numery przerwan sa juz potwierdzone** i to nie jest czescia tej pozycji: `hsi2c` pod
0x15d50000 ma w drzewie z telefonu `interrupts = <0x00 0x51 0x00>`, czyli SPI 81 (ta sama
wartosc jest w zrodlach producenta, `sources/ds/exynos9820.dts:8235`), i zywy licznik
`GIC-0 113` z tysiacami zdarzen; trzy SYSMMU bloku wyswietlania maja pary `<0xd4 0xd3>`,
`<0xd6 0xd5>` i `<0xd8 0xd7>`, czyli SPI 212, 214 i 216 na linii nie-bezpiecznej, dokladnie
tak jak w naszym drzewie (przelicznik `hwirq = SPI + 32` zgadza sie na trzech blokach
niezaleznie).

**Zmierzyc.** Wymusic zgloszenie na kazdym bloku po kolei: transakcja na i2c panelu, wymuszony
blad strony na SYSMMU, klatka na wyzwalaczu TE. Po kazdym sprawdzic `/proc/interrupts`: licznik
ma urosnac o tyle, ile bylo zdarzen. Licznik stojacy w miejscu albo rosnacy lawinowo rozstrzyga
typ tej linii.

**Miejsce w serii:** `arch/arm64/boot/dts/exynos/exynos9820.dtsi`

### Zamkniete pomiarem

Pozycje, ktore wypadly z kolejki, bo maja odczyt z urzadzenia. Zostaja tutaj z data i zrodlem,
zeby bylo widac, czym dokladnie zostaly zamkniete i ktora bramka tego pilnuje. Material lezy
w `measurements/2026-09-11-etap0a/` (stockowy Android) i `measurements/2026-09-17-etap0/`
(log S-Boota z /proc/last_kmsg), metryki pochodzenia w tamtejszych `README.md`.

#### HW-11 Rewizja krzemu: EVT1, nie EVT0

**Zamkniete 17 wrzesnia 2026, z logu S-Boota tego egzemplarza.** Pozycja pytala, czy krzem
naszej sztuki to EVT0, bo zapisy `PLL_CON8 = 0xA28` i `MC_ANA_CON2 = 0x2` sa u producenta objete
`#if !defined(CONFIG_SOC_EXYNOS9820_EVT0)` (`sources/ds/dsim_reg.c:60-64`, `:75-77`), a nasza
seria zapisuje je bezwarunkowo. Na krzemie EVT0 bylby to zapis do rejestru, ktorego producent
celowo nie dotyka.

Firmware telefonu odpowiada wprost i dwukrotnie: baner bootloadera to
`EXYNOS9820 EVT 1.1 (Base on ARM CortexA55)`, a sterownik DSIM w tym samym logu wybiera sciezke
`dsim_is_pll_stable:EVT1`. To jest **EVT1**, nie EVT0, wiec nasze bezwarunkowe zapisy sa poprawne.
Odczyt rejestru chipid, ktory zakladala procedura, okazal sie zbedny: baner bootloadera to
oswiadczenie firmware'u o wlasnej rewizji krzemu, a jego zadaniem jest te rewizje znac.

**Czego to nie dowodzi.** Ze dwa te zapisy sa na EVT1 konieczne, tylko ze sa niegroźne
i wlasciwe. Dowodzi rzeczy, o ktora chodzilo: nie piszemy do rejestru zablokowanego na naszej
rewizji krzemu.

**Pilnuje:** `scripts/check-dphy-timing.py` czyta rewizje z logu S-Boota i zapala bramke, gdyby
pomiar wskazal EVT0. Test negatywny wykonany: podmiana baneru na `EVT 0.1` zapala bramke.

#### HW-40 Rewizja panelu w tym egzemplarzu: tablice sa wlasciwe

**Zamkniete 11 wrzesnia 2026, bez sprzetu, bo wystarczyl pomiar z etapu 0a i jeden plik
producenta.** Pozycja powstala tego samego dnia z niepokojacego rozjazdu: bootloader podaje
`lcdtype=10555411`, czyli **0xA11013**, a naglowek, z ktorego przepisano sekwencje
inicjalizacyjna i tablice dimmingu, zna dla tej plyty tylko 0x900100, 0xA01010 i 0xA01011.
Rozniil sie ostatni bajt, ten od rewizji sterownika wyswietlacza.

**Rozjazd okazal sie pozorny, bo producent nie dopasowuje wariantu po tym polu.** Wybor idzie
przez tablice `panel-lut` z drzewa urzadzen, wpis po wpisie, kazdy z wlasna maska:
`(lut[i].id & lut[i].mask) == (id & lut[i].mask)`, pierwsze trafienie wygrywa
(`sources/ds/panel.c:187-207`). Format wpisu to `{id, mask, index, ddi_index}`
(`sources/ds/panel.h:866-871`), a nazwe wariantu daje dopiero `index` w liscie `panel-name`.
Pole `.id` w strukturze wariantu jest opisowe i nie bierze udzialu w wyborze.

Tablica **z tego telefonu** (`measurements/2026-09-11-etap0a/stock-fdt.dts`, wezel
`panel-lookup`) ma cztery wpisy, a lista nazw trzy pozycje w kolejnosci `_default`, `_utype`,
`_preliminary`:

| wpis | id | maska | wskazuje | co to znaczy |
|---|---|---|---|---|
| 0 | 0x000000 | 0x300000 | `_preliminary` | bity 20-21 rowne 0 |
| 1 | 0x100000 | 0x300000 | `_preliminary` | bity 20-21 rowne 1 |
| 2 | 0x000000 | 0x0f0000 | `_utype` | polbajt koloru obudowy rowny 0 |
| 3 | 0x000000 | 0x000000 | `_default` | maska zero, lapie wszystko |

Dla 0xA11013 bity 20-21 daja 2, a polbajt koloru obudowy 1, wiec trzy pierwsze wpisy nie lapia
i wybor spada na czwarty: **`s6e3ha9_beyond2_a3_s0_default`**, czyli dokladnie ten wariant,
z ktorego przepisano tablice do serii. Ostatni bajt identyfikatora nie ma znaczenia dla wyboru.

**Czego to nie dowodzi.** Ze rewizja 0x13 zachowuje sie identycznie jak 0x11 w czyms, czego
tablice nie opisuja. Dowodzi natomiast rzeczy, o ktora chodzilo: producent steruje TYM
egzemplarzem dokladnie tymi tablicami, ktore ma nasza seria, i jego ekran dziala.

**Pilnuje:** `scripts/check-panel-variant.py` odtwarza ten rachunek na zapisanym pomiarze
i sprawdza tez, czy naglowek producenta nadal opisuje `_default` jako 0xA01011. Testy negatywne
wykonane: 0xA01013 wybiera `_utype`, 0x123456 wybiera `_preliminary`, oba zapalaja bramke;
0xA11113, czyli zmiana bitu spoza masek, nadal wybiera `_default` i bramka slusznie przechodzi.

#### HW-19 Adres framebuffera S-Boota: 0xca000000

**Zamkniete 11 wrzesnia 2026.** Bootloader tego egzemplarza podaje adres wprost w linii
polecen, ktora dostaje jadro producenta: `s3cfb.bootloaderfb=0xca000000`
(`measurements/2026-09-11-etap0a/cmdline.txt`). To wlasnie tego brakowalo: nie kolejnego
drzewa z ta sama liczba, tylko odczytu z pracujacego S-Boota. Trzy wczesniejsze zrodla
(niezalezny port dla beyond2lte oraz defconfig i plik plyty uniLoadera dla beyond1lte)
podawaly te sama wartosc i wszystkie okazaly sie trafne.

**Pilnuje:** `scripts/check-memory-map.py` porownuje adres z naszego DTB z zapisanym cmdline.
Test negatywny wykonany: podmiana adresu na 0xcb000000 zapala bramke.

#### HW-31 Mapa pamieci RAM plyty: szesc bankow, 8082 MiB

**Zamkniete 11 wrzesnia 2026.** Mapa wyszla nie z `/proc/iomem`, jak zakladala procedura,
tylko ze zrodla pewniejszego: `/sys/firmware/fdt`, czyli blobu drzewa urzadzen, ktory
bootloader tej plyty podaje jadru producenta. Blob jest w `stock-fdt.dtb` (371894 B,
`sha256 877a949f886622c3359ee60e85f098b061943a5ffc5ff7cbac9ee87800cd6910`), a jego model to
"Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820", czyli ta plyta.

| bank | adres | rozmiar |
|---|---|---|
| 1 | 0x0_80000000 | 0x3ab00000 (939 MiB) |
| 2 | 0x0_c0000000 | 0x20000000 (512 MiB) |
| 3 | 0x0_e1900000 | 0x1e700000 (487 MiB) |
| 4 | 0x8_80000000 | 0x80000000 (2048 MiB) |
| 5 | 0x9_00000000 | 0x80000000 (2048 MiB) |
| 6 | 0x9_80000000 | 0x80000000 (2048 MiB) |

Razem 8474591232 bajtow, czyli 8082 MiB. Kontrola: `/proc/iomem` pokazuje te same granice
(trzy gorne banki widnieja tam jako jeden ciagly zakres 880000000-9ffffffff, bo sie stykaja),
a `MemTotal` to 7599168 kB, czyli 8082 MiB minus rezerwacje i narzut jadra.

Dwie dziury ponizej 4 GiB sa prawdziwe i celowo zostaly w drzewie: 0xbab00000-0xbfffffff
(87040 KiB) i 0xe0000000-0xe18fffff (25600 KiB). Trzyma je oprogramowanie zabezpieczajace.
Przewidywania z poprzedniej wersji tej pozycji potwierdzily sie: trzy banki ponizej 4 GiB
rozdzielone dziurami, osobne banki pod 0x0_80000000 i 0x8_80000000. Wartosc producenta
z `sources/ds/exynos9820.dts:5288-5301` (trzy plaskie banki po 2 GiB, razem 6 GiB) byla,
zgodnie z przypuszczeniem, wartoscia sprzed lataniny S-Boota i **nie** opisuje tego egzemplarza.

**Pilnuje:** `scripts/check-memory-map.py` porownuje banki z naszego DTB z blobem z telefonu,
bank po banku. Test negatywny wykonany: zmiana rozmiaru pierwszego banku o 0x100000 zapala
bramke. Dodatkowo suma kontrolna `scripts/golden/dtb.sha256`; poprzednia wersja lezy obok
jako `dtb.sha256.przed-mapa-ram`, a roznica miedzy nimi to dokladnie te szesc wezlow
(sprawdzone przez dekompilacje obu DTB).

#### HW-34 Trzy obszary reserved-memory tylko z obcego portu

**Zamkniete 11 wrzesnia 2026.** Wszystkie trzy sa w drzewie, ktore bootloader podaje jadru
producenta, pod dokladnie tymi adresami i rozmiarami, ktore mielismy z obcego portu:

| obszar | adres | rozmiar | compatible u producenta |
|---|---|---|---|
| kaslr | 0x80001000 | 0x1000 | `kernel-kaslr` |
| el2_code | 0x87000000 | 0x200000 | `el2,uh` |
| el2_earlymem | 0x9_fd800000 | 0x2800000 | `el2,uh` |

Przy okazji potwierdzily sie pozostale osiem rezerwacji przepisanych ze zrodel producenta
(sec_debug_magic, mm_debug, secure_camera, seclog_mem, modem_spare, modem_if, cp_ram_logging),
czyli **kazda** rezerwacja w pliku plyty ma teraz pokrycie w odczycie z urzadzenia.

Drzewo producenta ma tez obszary, ktorych nie deklarujemy: rodzine `debug_snapshot`,
sterty ION kamery i `sec_rdx_bootdev`. Nie sa pomylka po naszej stronie: stockowe jadro
oddaje te pamiec jako zwykla (widac je w `/proc/iomem` wewnatrz zakresow `System RAM`),
a ich obsluga nalezy do sterownikow, ktorych ten port nie ma.

**Pilnuje:** `scripts/check-memory-map.py` wymaga, zeby kazda zadeklarowana rezerwacja
istniala w blobie z telefonu pod tym samym adresem i rozmiarem. Test negatywny wykonany:
przesuniecie `el2_code` o 0x100000 zapala bramke.

#### HW-41 Zegar odniesienia PHY pamieci masowej

Wezel PHY w `arch/arm64/boot/dts/exynos/exynos9820.dtsi` podaje jako `ref_clk` oscylator
plyty. **To jest wniosek, nie odczyt.** Drzewo producenta nie opisuje osobnego PHY dla UFS
w ogole: jego sterownik siega do bloku PMA z wnetrza sterownika hosta i zadnego zegara przy
tym nie pobiera. Nasz wlasny sterownik w bootloaderze tez zadnego nie pobiera, a lacze mimo
to staje na HS Gear 3 po dwoch pasach, co znaczy tylko tyle, ze zegar plynie, nie skad plynie.

Binding `samsung,ufs-phy.yaml` wymaga dokladnie jednego `ref_clk`, wiec pole musi byc
wypelnione. Wybrano oscylator, bo to jego pin sasiad wyprowadza do kosci jako
`ufs_refclk_out`.

**Jak zamknac:** odczytac bit zatrzasku PLL w bloku PMA przy odcietym oscylatorze albo
zmierzyc czestotliwosc na pinie `gpf3-0`. Jesli zatrzask znika razem z oscylatorem, wpis jest
potwierdzony i wchodzi do `scripts/verify.sh` jako golden.

**Czego NIE robic:** nie zastepowac tego modelem ani analogia do gs101. Tamten uklad ma
wlasny wpis w swoim drzewie, nasz go nie ma.

#### HW-42 Tryb bloku USI, na ktorym siedzi glowny PMIC

`arch/arm64/boot/dts/exynos/exynos9820.dtsi` opisuje magistrale
`i2c@15d60000` jako I2C, ale ten blok jest **USI**, nie dedykowanym kontrolerem:
o tym, czy mowi I2C, SPI czy UART, decyduje rejestr trybu LEZACY POZA NIM,
w bloku rejestrow systemowych domeny CMGP. Naszego wezla dla tego rejestru NIE MA.

Bierzemy tryb, ktory zostawia firmware rozruchowe, na tej podstawie, ze ono
odczytuje te bateria zanim odda maszyne, wiec musialo ten tryb ustawic. To jest
wniosek, nie odczyt. Bazy samego bloku rejestrow systemowych CMGP rowniez nie
mamy skad wziac: w zrzutach producenta nie ma ani wezla pod tym adresem, ani
etykiety, a wartosc 0x15c20000 wychodzi z analogii do domeny PERIC0.

**Jak zamknac:** odczytac rejestr trybu pod 0x15c22030 na wystartowanym
systemie i porownac z wartoscia oznaczajaca I2C. Jesli magistrala nie odpowiada,
to jest pierwsza rzecz do sprawdzenia, nie adres ukladu.

**Czego NIE robic:** nie dopisywac wezla `sysreg` pod wyliczonym adresem
"na probe". Na tym ukladzie zapis pod zly adres konczy sie zewnetrznym
przerwaniem magistrali, co juz nas raz kosztowalo cala sesje przy PLL.

**ZAMKNIETE: wezel jest, tryb ustawiany jawnie, a bez niego blok stoi.**
Drzewo ma `sysreg_cmgp` i kazda magistrala tej domeny dostaje jawne
`samsung,sysreg` z offsetem swojego rejestru trybu (`0x30` dla tej), a plyta
wybiera tryb wpisem `samsung,mode`. Adres nie jest juz analogia: wezly
producenta `usi_00_cmgp` do `usi_03_cmgp_i2c` wymieniaja te rejestry po
jednym, od `0x15c22000` w gore. Zmierzone na telefonie: bez wezla USI blok
stoi w resecie, zapisy sterownika nie docieraja i magistrala nie zglasza
zadnego przerwania; z wezlem transfery dochodza do skutku.

Osobno, i wazniejsze dla tej pozycji: **glowny uklad zasilania nie odpowiada
na tej magistrali w ogole**, bo siedzi za firmware APM, a nie na szynie
procesora. Opisuje to runda R11 i wezel `firmware/power-management`.

#### HW-43 Adres licznika ladunku na magistrali PMIC-a

`arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dts` opisuje licznik ladunku
pod adresem 0x36. **Ten adres jest analogia, nie odczytem.** Pochodzi z jedynej
innej plyty w mainline noszacej ten sam uklad, Galaxy S9.

Zrodla producenta dla tego telefonu nie kłada licznika ladunku na magistrali
w ogole: wieszaja go w korzeniu drzewa bez adresu i wiaza z bateria po nazwie
(`battery,fuelgauge_name = "max77705-fuelgauge"`), wiec nie da sie stamtad
odczytac ani adresu, ani tego, czy jest taki sam jak w S9.

**ZAMKNIETE 20.09.2026: adres potwierdzony pomiarem.** Magistrala zostala
przeskanowana na wystartowanym telefonie, transferem wygenerowanym RECZNIE na jej
wlasnych nogach (sterowanie otwartym drenem przez /dev/gpiochipN, okolo 100 kHz),
z pominieciem kontrolera sprzetowego. Odpowiedzialy trzy uklady: **0x36** (licznik
ladunku, czyli wlasnie ta analogia), 0x66 (uklad towarzyszacy) oraz 0x69. Kontrola
spoczynku wypadla dobrze, obie linie czytaly sie jako wysokie.

Analogia z Galaxy S9 okazala sie trafna i wezel zostaje bez zmian.

#### HW-44 Wi-Fi wymaga kontrolera PCIe, ktorego mainline dla tego SoC nie ma

**Stan na 23.09.2026: ROZWIAZANE NA SPRZECIE.** Lacze wstaje przy pierwszej
probie, `brcmfmac` uruchamia obraz producenta na BCM4375B1, `wlan0` powstaje
sam przy kazdym rozruchu, skan widzi 2,4 i 5 GHz (6 GHz modul nie ma).
Brakowalo trzech rzeczy, ktorych bez telefonu nie bylo widac: zasilania
ukladu linia WL_REG_ON (`gpg0-5`), kolejnosci PERST# przed PHY i odmowy MSI;
wnosza je latki 0101-0103, a latka 0104 dopisuje slowo `host_cap`, bez
ktorego firmware nie oddawal zadnej ramki danych (skan i asocjacja szly,
WPA2 nie). Firmware musi lezec w initramfs, bo `brcmfmac`
jest wbudowany. Pomiar i szczegoly: `measurements/2026-09-23-wifi/` oraz
`docs/R14-wifi.md`.

**Stan na 21.09.2026: obie sciany opisane nizej sa juz zbudowane w kodzie,
niesprawdzone na sprzecie.** Latka 0084 wnosi opis wiazania, 0085 sterownik
kontrolera razem z warstwa fizyczna, 0086 wezel w drzewie urzadzen, a 0087
wpis ukladu 4375 do `brcmfmac`. Otwarte zostaje to, czego nie da sie
rozstrzygnac bez telefonu: czy lacze w ogole wstaje i czy obraz firmware
producenta (`bcmdhd`) jest do przyjecia przez `brcmfmac`. Opis ponizej
pokazuje, skad ta robota sie wziela.

Uklad lacznosci tego telefonu to **BCM4375**: Bluetooth wisi na porcie
szeregowym (runda R12 go uruchamia), ale Wi-Fi jest **na PCIe**, i tu droga
jest zamknieta z dwoch stron naraz.

**Strona pierwsza, kontroler.** `drivers/pci/controller/dwc/pci-exynos.c`
w mainline zna dokladnie jeden uklad: `samsung,exynos5433-pcie`. Dla Exynosa
9820 nie ma ani wpisu, ani opisu wiazania, ani sterownika warstwy fizycznej.
Napisanie tego to osobna robota rzedu tej, ktora poszla na pamiec masowa.

**Strona druga, sam uklad.** `brcmfmac` w sciezce PCIe zna 43752, 4377 i 4378,
ale **nie zna 4375**: nie ma dla niego ani wpisu identyfikatora, ani nazw
plikow firmware. Nawet z dzialajacym kontrolerem uklad nie dostalby sterownika.

**Czego NIE robic:** nie probowac obejscia przez USB ani przez tryb urzadzenia
na jakiejkolwiek innej magistrali. Ten uklad ma tylko jedno wyprowadzenie
danych Wi-Fi i jest nim PCIe.

**Co jest zamiast:** Bluetooth na porcie szeregowym, ktory daje siec osobista
i klawiature, oraz polaczenie po kablu. Dla samego SSH to wystarcza.

**Skala roboty, gdyby jednak.** Producent ma dwa kontrolery, `13ed0000.pcie0`
i `13120000.pcie1`, obsluzone czterema plikami downstreamu:
`pcie-exynos-host-v0.c`, `pcie-exynos-host-v1.c`, `pci-exynos9820_cal.c`
i `pci-host-v1-exynos9820_cal.c`. Sa wiec dane, z ktorych da sie napisac port
na `pcie-designware`, tak jak zrobilismy to dla pamieci masowej. To znaczy, ze
droga istnieje, ale jest rzedu calej rundy UFS, a nie poprawki: kontroler,
warstwa fizyczna, opis sprzetu, do tego wpis ukladu w `brcmfmac` razem
z nazwami plikow firmware, ktorych ten sterownik dla 4375 nie zna.

#### HW-45 Kolejnosc rejestracji dzielnikow CMU_PERIC0 w bootloaderze

**Co zmienione, 21.09.2026.** W `clk-exynos9820.c` bootloadera dwa dzielniki,
`dout_cmu_peric0_bus` i `dout_cmu_peric0_ip`, lezaly w tablicy rejestrowanej
PRZED tablica bramek, a ich rodzicami sa wlasnie bramki. `clk_register` wiaze
rodzica po nazwie i przy jego braku nie przerywa, tylko wpisuje NULL, wiec oba
dostawaly czestotliwosc policzona z `-ENODEV`. Wyszly do wlasnej tablicy
`top_div_peric0_clks` rejestrowanej za bramkami, czyli dokladnie tak, jak juz
stoja dzielniki APM, PERIS, DPU, UFS i USB w tym samym pliku. Bramka
`scripts/check-uboot-clk-order.py` zglasza po tej zmianie zero naruszen przy
259 zegarach w 9 CMU, a drzewo bootloadera buduje sie do `u-boot.bin`.

**Dlaczego to jest pozycja sprzetowa, a nie zamknieta.** Te dwa zegary zasilaja
CMU_PERIC0, z ktorego bierze takt konsola (`clk_uart_baud0`). Poprzednia proba
naprawienia kolejnosci skonczyla sie bootloopem i zostala wycofana: poprawna
czestotliwosc weszla do `serial_s5p.c`, ktory liczyl `uclk / baudrate`, a potem
`val / 16 - 1`, wiec kazda wartosc ponizej 1 843 200 dawala w rejestrze podzialu
0xFFFFFFFF. Port przestawal sie oprozniac, `putc` ponawial bez ogranicznika,
a czujnik zawieszenia konczyl to resetem. **Ten lancuch jest juz przerwany**:
`serial_s5p.c` ma dzis warunek `if (val < 16) return;`, czyli przy niedorzecznym
takcie zostawia podzial, ktory ustawil S-Boot, i port dalej dziala.

**Co ma pokazac wgranie.** Jedna zmienna, wylacznie bootloader:

* telefon wstaje i menu BEYOND BOOT wyglada jak dotad  -> kolejnosc naprawiona
  bez szkody, pozycja do zamkniecia;
* rozruch staje miedzy paskiem magenty a cyjanem       -> wina NIE lezy
  w wartosci taktu konsoli, bo ta jest teraz zabezpieczona, tylko w samej
  mechanice rejestracji, i trzeba szukac dalej.

Dowodem zamkniecia ma byc odczyt czestotliwosci obu zegarow z dzialajacego
bootloadera, a nie sam fakt, ze telefon wstal: zly rodzic nie daje zadnego
komunikatu, wiec rozruch moze przezyc obie wersje.

#### HW-46 Czy pierwszy stopien rozruchu zostawia modem zasilony

Sekwencja wlaczania domeny modemu u producenta jest zamknieta warunkiem
"stan rowny zeru", czyli wykonuje sie WYLACZNIE wtedy, gdy modem nie jest
jeszcze wlaczony. Nie wiemy, w ktorym stanie zostawia go S-Boot, a to
rozstrzyga, czy w ogole trzeba pisac sekwencje wlaczania, czy raczej sciezke
zatrzymania i zwolnienia resetu.

**Jak zmierzyc:** odczyt `CP_STATUS` (0x15860000 + 0x3004) bit 0 z dzialajacego
pmOS. To rejestr domeny zawsze zasilonej, bez bramki zegarowej, wiec odczyt
jest bezpieczny; skrzynki pod 0x15920000 przy tej okazji NIE dotykac, bo
odczyt peryferium za zamknieta bramka juz raz w tym projekcie zawiesil telefon.

**Czego NIE dowodzi:** stan 1 nie znaczy, ze modem wykonuje kod. Znaczy tylko,
ze domena jest zasilona.

#### HW-47 Czy CP_CTRL_S nalezy do swiata bezpiecznego

Warstwa kalibracyjna producenta kieruje do firmware **wylacznie** rejestr
`CP_CTRL_S` (0x15860000 + 0x3014); pozostale rejestry tej domeny sa zwykle.
Nie wiemy, czy zapis wprost do 0x3014 z naszego jadra cokolwiek robi.

**Jak zmierzyc:** zapisac bit 3 wprost, a nastepnie odczytac TEN SAM rejestr
droga przez firmware i porownac. Rozjazd miedzy zapisem a odczytem jest
dowodem, ze rejestr nalezy do EL3.

**Pulapka, ktora ta pozycja ma ominac:** bity potwierdzenia w 0x3004 i 0x3024
reaguja na zapis do 0x3000, a nie do 0x3014. Sekwencja moze wiec pokazac
komplet oczekiwanych bitow, mimo ze zapis do 0x3014 zostal po cichu polkniety.
Rozstrzygac wylacznie na 0x3014.

#### HW-48 Czy firmware bezpieczenstwa przyjmie wywolanie rozruchowe modemu
z lancucha zaczynajacego sie od NASZEGO bootloadera

Firmware modemu jest podpisane, a podpis sprawdza swiat bezpieczny przez
wywolanie `SMC 0x82000700`. Nie wiemy, czy EL3 tego egzemplarza przyjmie to
wywolanie, gdy rozruch nie przeszedl przez pelny lancuch Androida. To jest
**jedyny warunek rozstrzygajacy** o powodzeniu calej drogi i nie da sie go
sprawdzic inaczej niz proba.

**Jak zmierzyc:** wykonac wywolanie i odczytac kod powrotu. Kod 0x100 znaczy
"sprawdzanie niezakonczone" i wymaga odpytywania w petli; kazdy inny kod
bledu trzeba porownac z tablica bledow producenta.

**Ryzyko tego samego rodzaju co przy pamieci masowej:** deskryptory ochrony
UFS naleza do firmware i proba zapisu konczy sie bledem zewnetrznym oraz
panika. Tu moze byc tak samo.

#### HW-49 Typ wyzwalania przerwania skrzynki modemu

Drzewo producenta opisuje przerwanie skrzynki (SPI 41) wartoscia typu 0.
W tym projekcie juz raz okazalo sie, ze deklarowany typ wyzwalania nie zgadza
sie z tym, co robi egzemplarz (pozycja HW-39). Zly typ daje przerwanie, ktore
albo nie przychodzi, albo nie daje sie skasowac.

**Jak zmierzyc:** po zarejestrowaniu obslugi wyzwolic zgloszenie i policzyc
wpisy w liczniku przerwan. Licznik rosnie albo stoi, bez miejsca na
interpretacje. Najpierw jednak sprawdzic prostsza rzecz: czy rejestr
wiadomosci oddaje zapisana wartosc, bo to dowodzi okna i zegara, zanim w ogole
zacznie sie mowic o przerwaniach.
