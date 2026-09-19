# 00 — podsumowanie fazy rekonesansu (R1–R5)

Data: 2026-08-18. Baza mainline: `linux@1200d84f4c0a929a0780180d25063d93773be79c` (v7.2.0).
Wszystkie stałe i werdykty mają cytat `repo@commit:ścieżka:linia` w raportach szczegółowych.


> **Co zmienila recenzja pod katem mainline.** Ponizsza tabela zapisuje faze
> rekonesansu i jej werdykty merytoryczne, ktore zostaly w mocy. Architektura
> **zmienila sie** po recenzji: osobny host DSI zostal skasowany na rzecz
> wariantu `samsung-dsim`, D-PHY wydzielono do wlasnego sterownika w
> `drivers/phy/samsung/`, DECON stal sie komponentem `exynos_drm` zamiast
> trzymac wlasne `drm_device`, a katalog `drivers/gpu/drm/exynos9820/` nie
> istnieje. Wiersze, ktorych to dotyczy, sa poprawione; reszta opisuje stan
> rekonesansu.

## Tabela werdyktow

| # | pytanie | werdykt | pewność | co blokuje / co dalej |
|---|---|---|---|---|
| **R1** | zegary GPU (CMU_G3D) | **NIE ma nic w mainline** (0 trafień na „9820"). Out-of-tree driver istnieje (2516 linii, 6 bloków CMU), ale **bez CMU_G3D** — są tylko `PLL_G3D` i `CLKCMU_G3D_SWITCH` w CMU_TOP | wysoka (git grep na czystej bazie + kod drivera) | offsety rejestrów CMU_G3D nieznane; domena zasilania G3D (EL3/SMC) niezweryfikowana |
| **R2a** | DECON w `drm/exynos` dla 9820 | **NIE** — mainline ma tylko `exynos5433-decon`, `exynos5433-decon-tv`, `exynos7-decon`, `exynos7870-decon`; 9820 to `samsung,exynos9-decon`, inna mapa rejestrów (trigger `0x70` vs `0x2040`) | wysoka (porównanie rejestr po rejestrze) | nowy wariant sterownika, 448 `#define` w downstreamowym nagłówku |
| **R2b** | `samsung-dsim` dla 9820 | **NIE bez przepisania** — offsety kompletnie inne (`SWRST` 0x04 vs 0x0C, `RESOL` 0x3c vs `MDRESOL` 0x20), plus rejestry nieznane sterownikowi; **zero obsługi DSC** w mainline | wysoka | DSC (panel używa PPS 128 B), PLL/DPHY do napisania |
| **R2c** | panel w G975F | **S6E3HA9**, moduł **AMB644WQ01** (SDC), id `0xA01011`; sekwencje zlokalizowane i zacytowane (init `:1366`, display-on `:1505`, exit `:1517`, klucze `:689-694`) | wysoka | — |
| **R2c+** | timingi i DSC | **wyciągnięte** (`docs/R2-panel-timings.md`): command mode 1440×3040@60, 4 linie, HS 898 Mbps (PMS 2/138/2, kontrola: 26·138/(2·4)·2 = 897), esc 20 MHz, hbp/hfp/hsa 2/2/2, vbp/vfp/vsa 15/3/1; DSC 1.1, 8 bpp (3:1), 8 bpc, 2 slice’y 720×40, 2 enkodery; komplet pól PPS zdekodowany | wysoka (te same bajty PPS w 3 miejscach downstreamu, identyczne co do bajtu) | — |
| **R2c++** | D-PHY | wiersz tablicy dla 898 Mbps + mapa rejestrów PHY (`docs/R2-panel-timings.md` §7): clk_prepare 35, clk_zero 14, clk_post 3, clk_trail 56, hs_prepare 36, hs_zero 5, hs_trail 50, lpx 26, hs_exit 5, ULPS-exit 0x1C2; **esc clk faktycznie 18 MHz, nie 20** | średnia — liczby pewne, ale **jednostka liczników nieudokumentowana** (kontrola w UI nie wychodzi, Samsung sam oznacza tablicę jako niezgodną ze spec) | jednostka liczników D-PHY |
| **R2-bl** | jasność panelu (AID) | **dopisana** (`patches/0019`): backlight programujący AOR + ELVSS + VINT z firmowych tablic, 74 poziomy UI (2-420 nitów). Weryfikacja: tablice generowane skryptem i porównane z nagłówkami producenta — **74/74 wiersze** | wysoka co do danych; gamma per poziom **liczona** z MTP (`patches/0019`, `patches/0019`); bez HBM i kompensacji temperatury | silnik dimmingu, pierwszy boot |
| **R2-dim** | silnik dimmingu z MTP | **dopisany** (`patches/0019`): odtworzenie napiec punktow strojenia z MTP, interpolacja 256-stopniowej skali szarosci, wyliczenie 74x34 bajtow gammy. Weryfikacja: silnik producenta i port skompilowane jako programy userspace i nakarmione tym samym MTP — **74/74 poziomy bajt w bajt zgodne dla 7 zestawow MTP** | wysoka co do arytmetyki; **podpiety** (`patches/0019`): odczyt MTP 0xC8 w `s6e3ha9_on()`, wysylka 0xCA w kazdej zmianie jasnosci | wpiecie do sterownika panelu, HBM, kompensacja temperatury, pierwszy boot |
| **R2-rd** | odczyty DSI | **nie trzeba ich pisac**: po przejsciu na `samsung-dsim` (`patches/0034`) odczyty robi wspoldzielony sterownik, ktory ma je od lat. Nasza wlasna implementacja BTA i drenazu `RXFIFO` zostala skasowana razem z osobnym hostem | wysoka; **nietestowane na sprzecie** | pierwszy boot |
| **R2-pmic** | PMIC s2dos05 | **sterownika nie trzeba** — mainline ma MFD + regulator + binding. Brakowało magistrali: dopisany **CMU_CMGP**, kontroler I2C_CMGP2 (`15d50000`, gpm10/11) i węzeł PMIC-a; panel dostał prawdziwe regulatory zamiast atrap. `CHECK_DTBS` EXIT=0, 21 patchy na czystej bazie OK | wysoka; **nietestowane na sprzęcie** | odczyty DSI, pierwszy boot |
| **R2-phy** | bloki analogowe D-PHY | **dopisane** (`patches/0025`-`0021`): BIAS/PLL/MC/MD GNR+ANA, dithering, blok bias (M4S4) przez `syscon`. **Przy okazji naprawiony błąd**: PLL_CON jest pod 0x100, nie 0x300 — szkic pisał PMS do MC_GNR_CON. Kompilacja EXIT=0, `CHECK_DTBS` EXIT=0, 19 patchy na czystej bazie OK | wysoka co do adresów; **znaczenia pól nie znam — to przepisanie, nie zrozumienie** | odczyty DSI, PMIC s2dos05 |
| **R2-dsc** | DSC w DECON | **dopisane** (`patches/0037`): własny PPS na enkoder (720 px zamiast 1440), OUTFIFO 240 px/enkoder, parametry brane od panelu przez hosta DSI. Weryfikacja: parametry liczone helperami rdzenia `drm_dsc_*` na polowce obrazu i porownane ze wzorem producenta — **14/14 pol modelu** plus 4 pola sprzetowe sprawdzane w zrodle | wysoka co do arytmetyki; **nie testowane na sprzęcie** | bloki analogowe D-PHY, odczyty DSI, PMIC s2dos05 |
| **R2-dt** | bindingi + węzły DECON/DSIM | **dopisane**: binding DECON-a wlasny, a host DSI dopisany do istniejacego `samsung,mipi-dsim.yaml` (recenzja odrzucila argument o osobnej generacji IP), węzły `decon0`+`dsim0` z zegarami CMU_DPU, `pd_dpu`, `iommus`, grafem do panelu i panelem S6E3HA9 na beyond2lte. `dt_binding_check` EXIT=0, `CHECK_DTBS` EXIT=0, 15 patchy na czystej bazie OK | wysoka co do opisu; **obraz nadal nie ruszy** | DSC w DECON, bloki analogowe PHY, PMIC s2dos05 |
| **R1-mmu** | SYSMMU | **sterownika nie trzeba pisać** — 9820 ma SysMMU v7, a mainline `exynos-iommu.c` obsługuje v7 (10/10 offsetów rejestrów zgodnych z downstreamem, ten sam `compatible`). Dopisane brakujące węzły DT: trzy SYSMMU + CMU_DPU. `CHECK_DTBS` EXIT=0, `dt_binding_check` EXIT=0, checkpatch czysty | wysoka co do mapy rejestrów; **wersja z krzemu do potwierdzenia przy pierwszym boocie** | bindingi/węzły DECON i DSIM |
| **R1-pd** | pd-dpu | **dopisana**: `samsung,exynos9820-pd` (maska 0x1) + węzeł `pd_dpu@15861e00`; 9820 używa tego samego bloku co starsze Exynosy, więc wystarczył nowy compatible. Kompilacja EXIT=0, `CHECK_DTBS` EXIT=0, seria 10 patchy stosuje się na czystą bazę | wysoka co do danych; **niesprawdzone na sprzęcie** | SYSMMU, bindingi DECON/DSIM |
| **R1-dpu** | CMU_DPU | **dopisany**: baza 0x19000000, mux user + dzielnik BUSP + 22 bramki (ACLK_DECON/DPP/DMA, APB DSIM0, SYSMMU, infra). Offsety, szerokości i rodzice każdej bramki z tablic `cal-if` downstreamu. Kompilacja EXIT=0, `dt_binding_check` EXIT=0 | wysoka co do danych; **nieuruchomione na sprzęcie** | domena zasilania pd-dpu, SYSMMU; typy PLL **dopisane do mainline** (`patches/0012`), shim zniknal |
| **R2-drv2** | sterownik DECON/DSIM | **przebudowany po recenzji**: osobny host DSI skasowany, jego role przejal wariant `DSIM_TYPE_EXYNOS9820` w `samsung-dsim` (`patches/0034`); D-PHY to teraz osobny sterownik (`patches/0025`), a DECON jest komponentem `exynos_drm` z jawnym CRTC i plane (`patches/0037`). Seria jest przez to **krotsza o 68 linii** niz przed przebudowa | wysoka co do kodu; **nie zapala ekranu** | pierwszy boot |
| **R2-drv** | szkic sterownika panelu | `panel-samsung-s6e3ha9-main.c` (371 linii) + binding, `patches/0017`, `patches/0017`; DSC liczone helperami DRM — **zgodność 30/30 pól z firmowym PPS**; kompilacja EXIT=0 (0 ostrzeżeń z pliku), `dt_binding_check` OK, `checkpatch --strict` bez błędów | wysoka co do kodu; **zero testów na sprzęcie** (brak hosta DSI dla 9820) | zamkniete: AID dimming z MTP (`patches/0019`), bramki na PC, wpis w MAINTAINERS |
| **R2c++++** | init + TE | sekwencja init przepisana do postaci bajtów (`docs/R2-panel-timings.md` §9: DSC-COMP → PPS → sleep-out → scaler/CASET/PASET → TE on → err-fg → FFC → TSP-HSYNC → ISC/STM/gamma-mode → set-BL) + TE po obu stronach (§10: panel `35 00` i `B9 01 B0 E1 …` = 3041 linii, wariant PLL_SLEEP; SoC: pin gpd0-0, `psr_mode=2`, `trig_mode=0`, liczniki DSIM 86 / 8867 / 10102) | wysoka — bajty rozwinięte skryptem z tablic źródłowych, nie przepisane ręcznie | skąd dokładnie 3041 linii |
| **R2c+++** | FFC (0xC5) | dla 898 Mbps **nie trzeba nic przeliczać** — nasz zegar = stockowy, pakiet `0xC5 0x0D 0x10 0xB4 0x3E 0x01` przenosi się 1:1. Reguła na zmianę zegara wyprowadzona z tablicy dynamicznej tego samego DDI (Note10+): `word = round(79 153,7 × skala / f)` | wysoka dla samego pakietu; model odtwarza 4/4 punkty davinci2 co do bitu, na beyond* zostaje 7 LSB (0,044 %) | drugi punkt pomiarowy dla wariantu 5-bajtowego |
| **R2d** | jasność = DCS 0x51 + ELVSS? | **OBALONE w części 0x51** (zero wystąpień `0x51` w `s6e3ha9.c`); jest **AID dimming**: gamma `0xCA`, AOR `0xB1`, TSET/MPS/ELVSS `0xB5`, VGH/VINT `0xF4`, update `0xF7`, pod kluczem `0xF0 5A 5A`. **ELVSS potwierdzone** (tablice 3D po jasności i temperaturze) | wysoka | driver panelu musi wozić tablice per-poziom, nie jeden zapis |
| **R3** | dotyk | **JEST w mainline**: `s6sy761.c`, 544 linie, I2C, `samsung,s6sy761`. Downstream: `sec_ts/y771`, 12 552 linie, I2C. Port pmOS używa mainline’owego drivera i dotyk **działa** (na oryginalnym panelu) | wysoka (kod + DT + raport autora portu) | aftermarket panel = probe OK, brak zdarzeń; sprawdzić nasz egzemplarz |
| **R4** | istniejące porty | Brief §3 **nieaktualny**: od 2026-07-31 w pmaports jest **generyczny port mainline exynos9820** (kernel 7.2.0, boot przez fork U-Boota po EFI, DT w repo U-Boota), porty downstream **zarchiwizowane**. Ekran = `P` (simple-framebuffer), dotyk = `P`, 3D/audio/Wi-Fi/bateria = `N` | wysoka | brak wersji firmware’u G975F (Samsung OSS = HTTP 403) |
| **R5** | szablon portu | Odtworzony i **zweryfikowany budową**: 3 patche (bindingi, zegary-binding+IDs, DT), `dtbs` + `CHECK_DTBS` + `dt_binding_check` + `checkpatch --strict` przechodzą | wysoka (logi w `build-logs/`) | — |

## Co się zmienia w planie projektu (bramki z §4 briefu)

| bramka | stan po rekonesansie |
|---|---|
| **B0** — zegary GPU | zamknięta: **nie ma**; GPU wymaga dopisania bloku CMU_G3D do istniejącego drivera + power domain |
| **B1** — UART | bez zmian; DT z tej fazy ma już `serial0` jako `stdout-path` (`samsung,exynos9820-uart`) |
| **B2** — boot do shella | **w dużej mierze zrobione przez innych**: pmOS bootuje, SSH/UFS/USB-gadget działają; ścieżka to U-Boot (EFI) + TWRP, nie kexec |
| **B3** — DRM/KMS | **najdroższa pozycja i realny rdzeń projektu**: nowy DECON + nowy DSI host + panel z AID dimming + DSC. Nikt tego nie ma. To jedyna droga do wymagania §2.1 (jasność, wygaszanie) |
| **B4** — dotyk | **zamknięta pozytywnie**: driver w mainline, DT w tej fazie, potwierdzone działanie |
| **B5** — GPU | bez zmian: hazard; dodatkowo brak CMU_G3D w warstwie zegarów |
| **B6** — energy model/cpuidle/thermal | otwarta i **pilniejsza niż w briefie**: bez cpufreq/cpuidle port dostaje twardy cutoff termiczny przy 8 rdzeniach (`maxcpus=6` w porcie pmOS) |

## Rekomendacja kolejności (nie było pytane — jedna linijka uzasadnienia)

B1 (UART) → potwierdzić na sprzęcie framebuffer i dotyk na *naszym* egzemplarzu → B3 w kolejności
DECON → DSI → panel, bo dopiero panel daje jasność i wygaszanie wymagane w §2.

## Mapa dokumentów

- `docs/R1-clocks.md` — zegary i CMU_G3D
- `docs/R1-cmu-dpu.md` — dopisany blok CMU_DPU (odblokowuje DT dla DECON/DSIM)
- `docs/R1-sysmmu.md` — SYSMMU: mainline już obsługuje v7, dopisane węzły DT
- `docs/R2-display.md` — DECON, DSIM, panel, jasność
- `docs/R2-panel-timings.md` — timingi panelu i parametry DSC (+ `scripts/decode-pps.py`)
- `docs/R2-panel-driver.md` — szkic sterownika panelu do mainline (+ `scripts/check-dsc-config.py`)
- `docs/R2-decon-dsim-driver.md` - szkic sterownika DECON/DSIM (+ `scripts/check-decon-dsc.py`)
- `docs/R2-decon-dsim-dt.md` - bindingi i wezly DT dla DECON i DSIM
- `docs/R2-s2dos05.md` - PMIC panelu i magistrala CMGP
- `docs/R3-touch.md` - dotyk
- `docs/R4-existing-ports.md` - istniejace porty
- `docs/R5-template.md` - szablon portu
- `docs/R6-krytyk-a.md` - audyt cytowan, werdykt FAIL i co z niego wyszlo
- `docs/R7-krytyk-b.md` - recenzja glowna serii
- `docs/R8-krytyk-c.md` - runda na zmienionej powierzchni
- `docs/R9-krytyk-d.md` - runda kompletnosci: konfiguracja jadra, pamiec, lancuch startowy
- `docs/HW-BLOCKED.md` - 35 pozycji do rozstrzygniecia na sprzecie, plus piec zamknietych
  (HW-19, HW-31, HW-34, HW-40 na stockowym Androidzie, HW-11 z logu S-Boota; HW-01/02/03
  potwierdzone pomiarem, formalnie otwarte)
  odczytem z telefonu 11 wrzesnia 2026 (osobna sekcja na koncu pliku)
- `docs/COVER-LETTERS.md` - listy przewodnie czterech czesci serii
- `docs/PC-PIPELINE.md` - jak bramki jada na PC bez Linuksa i czym to udowodniono
- `docs/UART-BRINGUP.md` - uporzadkowana procedura sesji przy telefonie
- `docs/S1-sesja-sprzetowa.md` - pierwsza sesja przy telefonie: co zmierzono i co z tego wyszlo
- `docs/S2-sesja-uart.md` - druga sesja przy telefonie: jig UART zbudowany, wynik negatywny i czym jest poparty

## Faza druga: audyt i domkniecie serii (praca na PC)

Rekonesans zamknal sie seria 24 patchy, ktora **jako calosc nie mogla dzialac**. Audyt
wykazal piec defektow blokujacych; wszystkie sa naprawione, kazdy z dowodem.

| defekt | dowod, ze byl realny | jak naprawiony |
|---|---|---|
| Brak sterownika zegarow. Zaden z 24 patchy nie dotykal `drivers/clk`, wiec `decon0`, `dsim0`, trzy SYSMMU i `i2c@15d50000` nie mialy dostawcy zegarow i nie przeszlyby probe | `grep -l drivers/clk patches/*.patch` bez trafien | `patches/0013` wnosi sterownik do mainline, `patches/0022` dokłada bloki CMU_DPU i CMU_CMGP |
| Seria stala na shimie. Blok CMU_DPU kompilowal sie tylko po lokalnej podmianie dwoch typow PLL, jawnie oznaczonej jako "nie jest czescia zadnego patcha" | `build-logs/26-cmu-dpu-verify.log:10-16` | `patches/0012` dopisuje `pll_0817x` i `pll_1018x` do `clk-pll`, z cytatem `cal-if/pll_spec.c:293-301`; shim zniknal |
| Odwrocona polaryzacja resetu panelu. Sekwencja konczyla sie wartoscia 1 przy `GPIO_ACTIVE_LOW`, czyli **z resetem wcisnietym**, po czym leciala cala sekwencja DCS; zwalniana byla dopiero w `unprepare` | downstream `disp-reset` to `gpa3 4` z flaga `0x1` (ACTIVE_LOW), `exynos9820-beyond2lte_eur_open_26.dts:6626-6628` | poprawka w `patches/0017`: reset zwalniany przed komendami, wciskany przy wylaczaniu |
| **Wszystkie dziewiec PLL-i czytalo zly rejestr.** Sterownik przekazywal do `PLL()` offset `PLL_CON0_*`, a `samsung_pll0822x_recalc_rate` czyta spod `con_offset` wspolczynniki M, P i S, ktore leza w **CON3**. Kazda czestotliwosc odczytana z drzewa CMU_TOP byla wiec liczona z zawartosci rejestru sterujacego. Blad nie przeszkadza w starcie, bo zegary ustawia bootloader i bledny jest tylko odczyt, dlatego przezyl caly audyt | mapa producenta dla tego SoC pokazuje oba wpisy: `PLL_CON0_PLL_AUD0` pod 0x120 i `PLL_CON3_PLL_AUD0` pod 0x12c (`sources/ds/cmucal-sfr.c:46-47`), czyli CON3 = CON0 + 0xc; upstreamowy `clk-exynos850.c`, ta sama rodzina sterownika i te same typy PLL, przekazuje `PLL_CON3_*`. Po poprawce `cmucal` **niezaleznie potwierdza** nasz `PLL_CON3_PLL_MMC` = 0x01ac, bo symbol wchodzi do porownania z producentem | `patches/0013`: dziewiec definicji `PLL_CON3_*` i dziewiec wywolan `PLL()` przestawionych na nie. Pilnuje `scripts/check-pll-con3.py` (kazde `PLL()` musi dostac CON3, a kazdy CON3 rowna sie CON0 + 0xc), trzy testy negatywne wykonane. **Znalezione dopiero przy pisaniu wlasnego U-Boota**, bo ta sama wiedza o PLL-ach musiala pojsc drugi raz do bootloadera |
| DECON bral tylko jeden z trzech zegarow. Binding wymaga `aclk`, `aclk-dma` i `aclk-dpp`, DT podaje wszystkie trzy, sterownik pobieral sam `aclk`, a pisal do rejestrow IDMA bramkowanych przez pozostale dwa | `patches/0037` (binding) wobec sterownika w `patches/0037` | poprawka w `patches/0037`: `devm_clk_bulk_get` na trzy zegary |
| Silnik dimmingu byl martwym kodem. 1300 linii arytmetyki linkowanych do modulu, ale nikt ich nie wolal; rownoczesnie `patches/0019` usunal statyczna gamme z sekwencji init, wiec po calej serii gamma nie byla programowana w ogole | brak wywolan `s6e3ha9_dimming_*` w sterowniku panelu | `patches/0019`: odczyt MTP 0xC8, przeliczenie, wysylka 0xCA przy kazdej zmianie jasnosci |

Dodatkowo: wpis do MAINTAINERS dla nowego katalogu sterownika jedzie razem z patchem,
ktory ten katalog tworzy (`patches/0037`), zgodnie z konwencja jadra, a z historii serii
usunieto dwa pliki `.orig`, ktore zostawilo GNU patch.

### Druga runda audytu: co jeszcze wyszlo

Serie przepuszczono przez niezalezny audyt (cytaty, recenzja pod katem mainline,
weryfikacja twierdzen w dokumentach, proba zlamania bramek). Znalezione i naprawione:

| defekt | dlaczego to bylo grozne | poprawka |
|---|---|---|
| Pliki wzorcowe bramek zawieraly absolutna sciezke tej maszyny | `verify.sh` konczyl sie kodem 1 po kazdym sklonowaniu repo gdzie indziej, co przeczy pierwszemu zdaniu README | `dump-init-seq.py` drukuje sama nazwe pliku, wzorce odswiezone |
| Odsylacze `patches/NNNN` w dokumentach wskazywaly patche sprzed przenumerowania serii | czytelnik trafial pod zupelnie inny patch, np. "jasnosc panelu" prowadzila do bloku zegarow | 40 odsylaczy poprawionych, doszla bramka `scripts/check-doc-refs.py` z migawka |
| Cztery commity II fazy nie mialy `Signed-off-by` | `git am` odrzuca taki patch, DCO niespelnione | dopisane |
| Patch ze sterownikiem zegarow mial w `From:` nas, a wnosil 2516 linii cudzego kodu | brak lancucha atrybucji, maintainer nie moze tego wziac | autorstwo przeniesione na autora oryginalu, w opisie jawna nota, ze jego `Signed-off-by` trzeba jeszcze zebrac |
| Licznik runtime PM schodzil pod zero po nieudanym wlaczeniu (DECON i DSIM) | `pm_runtime_resume_and_get()` sam oddaje referencje przy bledzie, a sciezka wylaczania oddawala ja drugi raz i pisala do rejestrow bez zegarow | flaga stanu `enabled`, sciezka wylaczania wychodzi bez dotykania sprzetu |
| Przerwanie DECON rejestrowane przed `pm_runtime_enable` i przed inicjalizacja KMS | przerwanie zostawione przez bootloader dawalo dostep do rejestrow przy zgaszonym bloku i wyluskanie NULL na CRTC | rejestracja przeniesiona za KMS, handler wychodzi, gdy blok nie jest wlaczony |
| Zegary wlaczane wylacznie z callbackow runtime PM, a `Kconfig` nie wymagal `PM` | przy `CONFIG_PM=n` `pm_ptr()` daje NULL, `pm_runtime_resume_and_get()` zwraca 1 i sterownik pisze do rejestrow z zabranymi zegarami | `depends on PM` |
| CMU_DPU rejestrowany sciezka bez wsparcia PM, mimo ze lezy w przelaczalnej domenie | po cyklu domeny rejestry zegarow nie sa odtwarzane | `exynos_arm64_register_cmu_pm()` plus `dev_pm_ops`, jak w `clk-exynos5433.c` |
| Opisy commitow odsylaly do `docs/HW-BLOCKED.md` i `scripts/*.sh`, ktorych w drzewie jadra nie ma | po wyslaniu na liste odwolania sa martwe | przeformulowane na opis bez sciezek |
| Wpis MAINTAINERS byl osobnym, ostatnim patchem | konwencja jadra: hunk MAINTAINERS jedzie z patchem tworzacym katalog | wpisany do patcha ze sterownikiem, osobny commit usuniety |
| Komentarz w sterowniku panelu twierdzil, ze gammy z MTP nie ma | zdanie bylo prawdziwe w patchu 0026 i przestalo byc w 0028, a nikt go nie poprawil | 0028 aktualizuje komentarz |

Osobno, juz po audycie, wyszedl defekt w `patches-oot/0001`: patch ruszal sam sterownik,
a nie wnosil identyfikatorow zegarow do naglowka bindingu w drzewie chiffathefoxa, wiec
u odbiorcy **nie zbudowalby sie**. Zaden ze skryptow tego nie sprawdzal, bo `patches-oot/`
nie bylo objete zadna bramka: dokladnie ten sam wzorzec, ktory audyt znalazl przy serii
glownej (artefakt wysylany, ktorego nikt nie testuje). Patch uzupelniony o 36 identyfikatorow,
zgodnosc kodu z naglowkiem potwierdzona kompilacja, i doszly dwie bramki na `patches-oot/`.

Trzy twierdzenia w dokumentach okazaly sie za mocne i zostaly oslabione do stanu
faktycznego: zasieg komentarzy `UNVERIFIED` (czesc z 28 pozycji, nie wszystkie), liczba
pozycji HW-BLOCKED mogacych zablokowac boot (dziewiec, nie trzy) oraz "sciezek
absolutnych brak" (jest jedna, domyslny cel `sync-to-downloads.sh`).

### Co sie zmienilo w bramkach

Stary `verify.sh` byl bramka pozorna. Nakladanie serii i build byly polaczone przez `&&`
w jednej linii, wiec gdy `git apply --check` padal, przebieg leciał dalej na starym stanie
drzewa (widac to w `build-logs/43-verify-24-patches.log:1-20`), `checkpatch` mial `|| true`,
a hash DTB byl tylko dopisywany do logu, nie porownywany. Zaden ze skryptow `check-*` nie
byl w niej wolany, wiec trzy jedyne realne dowody liczbowe nie byly ratchetem.

Nowy `scripts/verify.sh` mial wtedy 40 bramek, kazda z jawnym kodem wyjscia, i konczyl
sie kodem 2, gdy czegos **nie dalo sie** uruchomic. Liczby w tej sekcji sa z tamtej chwili
i celowo nie sa aktualizowane, bo opisuja, co konkretnie ta runda zmienila; stan biezacy
jest w README i w `docs/PC-PIPELINE.md`. Doszly bramki, ktorych wczesniej nie bylo:

- nakladanie serii na osobnym indeksie gita, bez dotykania drzewa roboczego,
- porownanie sha256 DTB z plikiem wzorcowym (`scripts/golden/dtb.sha256`),
- kompilacja siedmiu plikow `.c` serii dla arm64, w dwoch wariantach
  (zwyklym i `W=1`), wymagane **zero** uwag,
- `dt-validate` i `dt-doc-validate` z `dtschema`, bez `make`,
- kontrola, ze kazde `UNVERIFIED: HW-nn` w serii ma pozycje w `docs/HW-BLOCKED.md`,
- kontrola, ze w `patches/` nie ma plikow `.orig` ani `.rej`.

Wynik: `build-logs/44-pc-verify.log`, 40 bramek, 0 porazek, EXIT=0.

### Co pozostaje otwarte

- **Signed-off-by autora sterownika zegarow.** `patches/0013` wnosi 2516 linii kodu
  chiffathefoxa wziete z publicznego drzewa GPL-2.0, nie z posta na liscie, wiec jego
  podpisu DCO nie ma. Trzeba go zebrac, zanim seria pojdzie na liste; do tego czasu
  patch jest kompletny technicznie, ale nie do przyjecia formalnie.
- **Sprzet.** Nic z tej serii nie bylo uruchomione na telefonie. Pozycji w
  `docs/HW-BLOCKED.md` jest 38 i wszystkie czekaja na pomiar, w tym dwanascie z waga
  "boot", czyli takich, ktore moga skonczyc sie zawisem albo brakiem startu (HW-07,
  HW-08, HW-09, HW-15, HW-17, HW-18, HW-24, HW-29). HW-11, HW-19, HW-31 i HW-34 z tej
  wagi zostaly juz zamkniete pomiarem.
  Kolejnosc pomiarow i konkretne polecenia sa w `docs/UART-BRINGUP.md`; dwie pozycje
  zdejmuje sie na stockowym Androidzie, szesc na istniejacym porcie pmOS, reszta
  wymaga naszej serii albo oscyloskopu.
- **HBM i kompensacja temperaturowa.** Producent ma 90 wierszy jasnosci (74 UI plus
  16 HBM do 800 nitow) i przelacza tablice ELVSS/VINT wg temperatury; port ma 74 wiersze
  i wycinek OVER_ZERO. HBM wymaga **osobnego** odczytu krzywej gammy z panelu
  (rejestr 0xB3, offset 2, 34 bajty, `sources/ds/s6e3ha9.h:51-53`), a nie doklejenia
  16 wierszy do tablicy AID; szczegoly w `docs/R2-panel-driver.md`.
- **CMU_G3D.** Nie istnieje w zadnej warstwie zegarow, ani w mainline, ani w drzewie
  chiffathefox. GPU pozostaje zablokowane podwojnie: brak zegarow i nieznana sciezka
  wlaczania domeny zasilania.
- **Splitter DSC (DSCC) i pelny zakres PPS po stronie DECON.** Enkodery sa
  zaprogramowane, splitter nie; slowa PPS36-55 i PPS60-75 zostaja na wartosciach
  resetowych (HW-13).
- **Rozszerzenie `samsung-dsim` zamiast nowego hosta DSI.** Uzasadnienie, dlaczego nie da
  sie rozszerzyc istniejacego sterownika, jest rozproszone po `docs/R2-display.md`;
  przed wyslaniem na liste trzeba je zebrac w jedna tabele rozjazdu rejestr po rejestrze.
