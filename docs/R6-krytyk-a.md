## R6: audyt cytowan calej serii (Krytyk A)

Osiem grup patchy, w kazdej audytor i sceptyk. Audytor zbieral twierdzenia
powolujace sie na zrodlo i sprawdzal je otwierajac to zrodlo; sceptyk dostawal
wylacznie liste werdyktow PASS i mial je **obalac**, nie potwierdzac.

Wynik: **203 PASS, 13 FAIL, 16 NIEWERYFIKOWALNE**, do tego sceptycy obalili
24 cytaty i wskazali 74 twierdzenia, ktorych audyt w ogole nie objal.

Kazdy z 13 zarzutow zostal przed poprawka sprawdzony osobno, na plikach
zrodlowych. **Wszystkie 13 sie potwierdzilo.** Ponizej co bylo nie tak i czym
to zastapiono.

### Rzeczy funkcjonalne, nie redakcyjne

| # | gdzie | co bylo zle |
| --- | --- | --- |
| 1 | `samsung,exynos9820-decon.yaml`, przyklad | trzy makra zegarow, ktorych naglowek nie definiuje: `CLK_GOUT_DPU_ACLK_DECON/_DMA/_DPP` zamiast `CLK_GOUT_DPU_DPU_ACLK_*` |
| 2 | `samsung,exynos9820-mipi-dphy.yaml`, przyklad | to samo: `CLK_GOUT_DPU_DSIM0_PCLKS` zamiast `CLK_GOUT_DPU_AD_APB_MIPI_DSIM0_PCLKS` |
| 3 | plik plyty, `gpio-keys` | tylko klawisz zasilania oznaczony jako zrodlo wybudzenia, a producent oznacza DWA (`:1460` KEY_WINK i `:1482` KEY_POWER) |

Pierwsze dwa to skutek przenumerowania zegarow: drzewo urzadzen zaktualizowalem,
a przykladow w bindingach nie, bo **zadna bramka ich nie kompiluje**. `dt-validate`
sprawdza zbudowane DTB, a przyklady kompiluje dopiero `make dt_binding_check`
w pelnym drzewie jadra. Stad nowa bramka `scripts/check-clk-macros.py`, ktora
zbiera kazde `CLK_*` z naszych DTS i z naszych bindingow i sprawdza je
w naglowku. Sprawdzone, ze umie padac: po przywroceniu starej nazwy zglasza
brak i wychodzi z kodem 1.

Trzecie poprawilem idac za zrodlem: klawisz wink jest teraz `wakeup-source`,
tak jak u producenta.

### Twierdzenia nieprawdziwe

| # | gdzie | twierdzilo | jest |
| --- | --- | --- | --- |
| 4 | opis 0012 | `clk-gs101.c` ma 146 linii ponad 100 kolumn, `clk-exynos2200.c` 195, nasz 143 | 128, 164 i 124; moj pomiar rozwijal tabulatory po 8 znakow niezaleznie od pozycji w linii |
| 5 | opis 0012 | `CLK_IGNORE_UNUSED` obejmuje **wszystko** w CMU_APM | 28 z 37 bramek; pozostale 9 to szkielet bloku z `CLK_IS_CRITICAL` |
| 6 | opis 0020 | czestotliwosci RCO CMGP nie dokumentuje zadne zrodlo, wiec modelujemy ja jako 26 MHz | `cmucal-node.c:2799` podaje 49 152 000 Hz, a kod od kilku commitow rejestruje ja jako `FRATE` |
| 7 | opis 0006 | `struct samsung_pin_bank_data` nie ma pola na offset filtru | ma: `eint_fltcon_offset`, `pinctrl-samsung.h:164`; to makra `EXYNOS850_PIN_BANK_*` go nie ustawiaja |
| 8 | opis 0023 i komentarz w PHY | lock PLL lezy poza zakresem rejestrow tego PHY | lezy w srodku: `PLL_STAT0` pod 0x0140, przy zmapowanym oknie 0x800; prawdziwy powod to przesuwanie sie tego offsetu miedzy rewizjami krzemu |
| 9 | opis 0033 | DSIM dostaje wlasny binding | patch 0024 dopisuje go do istniejacego `samsung,mipi-dsim.yaml` |
| 10 | komentarz w DECON | zapisy PPS79-87 w `decon_reg.c:1100-1102` | `:1101-1103`; 1100 to komentarz |
| 11 | komentarz TODO w DECON | producent programuje tu dekompresor AFBC/SBWC i skaler | SBWC nie wystepuje w `dpp_reg.c` ani razu; jest za to sciezka HDR, ktorej lista nie wymieniala |
| 12 | komentarz w mostku | producent liczy okna TE czynnikami, ktorych nic nie dokumentuje | czynniki sa opisane wprost: 158 to 15,8 ms, 180 to 18 ms (`dsim_reg.c:38-39`); nieudokumentowane jest wylacznie dzielenie przez 16 |
| 13 | komentarz w mostku | ta niepewnosc to pozycja HW-04 | HW-04 dotyczy liczby linii w pakiecie TE, nie okien czasowych; okna dostaly wlasna pozycje HW-30 |

### Czego ta runda nie objela

Sceptycy wskazali **74 twierdzenia z cytatem**, ktorych audyt nie zdazyl sprawdzic
w limicie narzedzi. To nie sa znaleziska, tylko biala plama: nie wiadomo, czy sa
prawdziwe. Przy nastepnej rundzie warto zaczac od nich, zamiast przechodzic
jeszcze raz po tym, co juz ma werdykt.

16 pozycji NIEWERYFIKOWALNE to poprawny wynik, nie porazka: tam, gdzie zrodel
po prostu nie ma, audyt ma to powiedziec i powiedzial.

### Co z tego wynika dla nastepnych rund

Bledy rozkladaja sie nierowno. Trzy byly funkcjonalne i wszystkie trzy siedzialy
w miejscach, ktorych zadna bramka nie dotykala: dwa w przykladach bindingow,
jeden w zdaniu o zachowaniu producenta. Reszta to **zdania o zrodlach**, ktore
w chwili pisania byly prawdziwe albo prawdopodobne, a zdezaktualizowaly sie razem
z kodem: opis commita mowil o RCO modelowanym jako 26 MHz, gdy kod juz go
rejestrowal osobno. Nic w harnessie nie pilnowalo, zeby opis nadazal za trescia.
