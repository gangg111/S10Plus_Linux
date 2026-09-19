## R8: trzecia runda, na powierzchni zmienionej po recenzji (Krytyk C)

Po zamknieciu recenzji glownej ruszylem okolo 25 commitow. Ta runda patrzy
wylacznie na to, co wtedy powstalo, bo poprawka cudzego bledu jest tak samo
dobrym miejscem na wlasny.

Cztery soczewki, do kazdej wlasny sceptyk, ktory dostawal WYLACZNIE liste
zarzutow i mial je obalac. Agenci mieli zakaz otwierania `docs/R6-krytyk-a.md`
i `docs/R7-krytyk-b.md`, zeby nie zobaczyli obrony autora, oraz sufit
45 wywolan narzedzi. Osiem agentow, 1,58 mln tokenow, 309 wywolan, 22 minuty.

Wynik: **33 znaleziska, w tym 3 blokujace. Sceptycy podtrzymali 6.**
Kazde podtrzymane sprawdzilem jeszcze raz sam, na plikach zrodlowych.

### Trzy blokujace

| # | zarzut | werdykt |
| --- | --- | --- |
| 1 | patch D-PHY twierdzi, ze 898 Mbps to jedyny punkt pracy panelu, a producent daje osiem i domyslnie 1157 | **obalone** |
| 2 | wezel DECON zabiera caly wspoldzielony blok DPU_DMA, ktory nie nalezy do DECON0 | **obalone**, poza jednym zdaniem opisu |
| 3 | przy kompresji host DSIM dostaje nieskompresowana szerokosc linii | **podtrzymane, poprawione** |

**1. Zla tabela panelu.** Audytor czytal wezel `s6e3fa7_davinci`
(`sources/ds/exynos9820-beyond2lte_eur_open_26.dts:495`), czyli inny panel
z innego telefonu. Nasz panel to `s6e3ha9_beyond2` (`:690`), a on ma
`timing,dsi-hs-clk = <0x382>`, czyli 898, i `timing,pmsk = <0x2 0x8a 0x2 ...>`,
czyli P=2, M=138, S=2, dokladnie to, co stoi w sterowniku. Osiem wezlow
`mipi_freq` to pula czestotliwosci adaptacyjnych, po ktora siegaja tylko wezly
z `adaptive_freq_info`; `s6e3ha9_beyond2` takiego wpisu nie ma. Sprawdzone
osobno, po sceptyku.

**2. Okno DPU_DMA.** Producent tez uzywa calego bloku, tylko rozbitego na
wlasne urzadzenia `dpp` po 0x1000 na kanal (`exynos9820.dts:6559`, `:6588`,
`:6603`, `:6618`, `:6633`), a w naszym drzewie nie ma z czym kolidowac, bo nie
ma ani DECON1/2, ani wezlow dpp. Zostalo jedno realne zdanie: opis schematu
mowil, ze blok "istnieje tylko po to, zeby karmic ten kontroler", podczas gdy
mapa blokow producenta wymienia trzy DECON-y przy jednym DPU_DMA
(`regs-decon.h:36-38`). Zdanie poprawione.

**3. Szerokosc linii przy kompresji.** To byl realny blad, ktory zjadlby caly
obraz. Producent w rejestrze rozdzielczosci zapisuje szerokosc PO kompresji:

```
dsim_reg.c:1030-1032
    if (lcd->dsc_enabled)
            width = lcd->dsc_enc_sw * lcd->dsc_slice_num;
    else
            width = hresol;
```

a `dsc_enc_sw` liczy `dsim_calc_slice_width()` (`dsim_drv.c:1646-1690`) tym
samym wzorem, ktorego uzywa nasz DECON do kolejek wyjsciowych. Dla tego panelu
wychodzi 240 na plaster i **480** razem, a seria zapisywala **1440**. DECON
wystawia 240 na enkoder, wiec host czekalby na trzy razy wiecej danych, niz
przychodzi: czarny ekran i ani jednej linii w logu.

Poprawione w `samsung_dsim_hresol()`, pod warunkiem na `dsi->dsc`, ktory dla
kazdego innego wariantu w tym sterowniku jest pusty. Wzor producenta ma 1/3
zaszyte na sztywno; nasz liczy z `bits_per_pixel` konfiguracji DSC i przy
8.0 bpp daje te same liczby.

### Brakujacy mechanizm, ktorego nie zglosil zaden wczesniejszy krytyk

Producent przy **kazdym** wlaczeniu lacza zaklada reset bloku M4S4, programuje
PLL i linie, po czym reset zdejmuje, a przy wylaczeniu zaklada z powrotem
(`dsim_reg.c:2197`, `:2211`, `:2272`). Rejestr i bity sa udokumentowane
(`regs-decon.h:17-21`): `DISP_DPU_MIPI_PHY_CON` pod 0x8 od okna, ktore
producent mapuje, bit `M_RESETN_M4S4_MODULE` dla DSIM0, plus bit wyboru zrodla
resetu. Adres tego okna wziety w tej rundzie z mapy blokow byl o 0x1000 obok;
poprawil to dopiero Krytyk D, patrz R9.

Seria nie dotykala tego bloku w ogole. Jesli bootloader zostawia reset
zalozony, PHY nie odpowiada i nie ma po tym sladu.

Dolozone: wezel `sysreg_dpu@19010000`, `samsung,exynos9820-dpu-sysreg`
w schemacie rejestrow systemowych, wlasciwosc `samsung,dpu-sysreg` w schemacie
D-PHY (wymagana) i `exynos9820_dsim_phy_reset()` w sterowniku, w kolejnosci
producenta. Otwarte pytanie, czego bootloader zostawia, to **HW-32**.

### Trzy bramki, ktore klamaly

| bramka | co bylo | co jest |
| --- | --- | --- |
| `check-decon-dsc.py` | `EXPECTED_HW` byl zadeklarowany i nieuzywany, a komunikat sukcesu drukowal jego DLUGOSC, wiec "4 pola sprzetowe sprawdzone" bylo nieprawda | cztery pola liczone z wyrazen sterownika dla tego panelu i porownane; wyrazenia przypiete wzorcem. Udowodnione, ze pada: po zmianie `dual_slice` bramka zglasza rozjazd |
| `check-binding-examples.sh` | dwa ciche `continue` omijaly licznik, wiec przy zerze zbudowanych przykladow bramka konczyla sie zielono, takze gdy seria w ogole nie byla nalozona | dolny prog: zero przykladow to blad. Udowodnione, ze pada |
| bramka [6] `verify.sh` | dwie niezalezne kontrole wiersza mapy, nic nie laczylo frazy z identyfikatorem, wiec wiersz przypisany do zlej pozycji przechodzil | kazda pozycja HW-BLOCKED niesie linie "Miejsce w serii", a bramka porownuje ja ze sciezka z mapy. Udowodnione, ze pada. Reszta luki (zamiana identyfikatorow miedzy dwoma pozycjami tego samego pliku) zapisana w naglowku mapy |

### Pozostale poprawki

* `DSIM_CMD_CONFIG_REG` byl jedynym wpisem wyliczenia rejestrow bez ani jednego
  odczytu i zapisu; usuniety z kodu wspoldzielonego.
* `drm/display/drm_dsc.h` dolaczony tam, gdzie siegamy po pola konfiguracji DSC.

### Czego ta runda nie objela

Audytor cytowan sam zapisal, czego nie zdazyl: 651 linii drzewa pinow wobec
tablic sterownika, pola bitowe muxow i dzielnikow wobec `SFR_ACCESS()`, oraz
rodzicow bramek wobec `cmucal-node.c`. Offsety rejestrow sprawdzil maszynowo
w komplecie: 416 z 416 w patchu sterownika zegarow i 121 ze 121 w patchu
CMU_DPU, zero rozbieznosci.

### Stan po rundzie

Seria: **40 patchy**, 50 plikow, +10463/-34. Bramek **58, wszystkie przechodza,
zero nieuruchomionych**, razem z bisectowalnoscia kazdego punktu serii
(`build-logs/50-verify-po-krytyku-c.log`). Lista rzeczy do zmierzenia na
sprzecie ma 32 pozycje.

Trzy razy w tej rundzie wstawilem `": "` w niecytowany skalar YAML. Za kazdym
razem skutek byl ten sam i niewidoczny golym okiem: `dt-validate` przestawal
sprawdzac CALY binding, a plik dalej wygladal poprawnie. Pierwszy raz wyszlo to
przypadkiem, drugi i trzeci zlapala bramka `dt-doc-validate`. Warto o tym
pamietac przy kazdej edycji opisu w schemacie.
