# Dźwięk: sondy bloku audio, 25.09.2026

Jądro #62/#63, telefon po starcie z S-Boota i naszego U-Boota. Sondy to moduł
`aud_sonda.c` (tu ostatnia wersja, etap 4), który tylko czyta rejestry i kończy
`init` błędem, żeby nie zostać w pamięci. Każdy etap sprawdza najpierw stan
domeny AUD i przy wyłączonej nie czyta nic dalej. Opis całości:
docs/R19-dzwiek.md.

## Etap 1: domena zasilania AUD (PMU 0x15861900)

    AUD CONFIGURATION=00000001 STATUS=00000001
    DPU CONFIGURATION=00000001 STATUS=00000001 (dla porównania)

Domena jest włączona po starcie: zostawia ją tak bootloader.

## Etap 2: CMU_AUD (0x18c00000)

| rejestr | wartość | znaczenie |
| --- | --- | --- |
| PLL_CON0_PLL_AUD0 (+0x120) | a02d0110 | włączony, zablokowany, M 45, P 1, S 0 |
| PLL_CON3_PLL_AUD0 (+0x12c) | 00005eff | K 24319 |
| PLL_CON0_PLL_AUD1 (+0x140) | 00000000 | wyłączony |
| DIV_CLK_AUD_PLL (+0x1828) | 3 | /4 |
| DIV_CLK_AUD_MCLK (+0x1824) | 2 | /3 |
| DIV_CLK_AUD_UAIF0..3 | 5 | /6 |
| bramki ABOX ACLK, BCLK UAIF0/1, CCLK CA32, SMMU, SYSREG | 00200000 | otwarte (bit 21) |

PLL_AUD0 = 26 MHz · (45 + 24319/65536) = 1179,648 MHz = 24576 · 48 kHz.

## Etap 3: ABOX (0x18c50000)

| rejestr | wartość |
| --- | --- |
| VERSION (+0x4) | 02000100 (ABOX 2.0.1) |
| SYSPOWER_CTRL / STATUS | 0 / 0 |
| ROUTE_CTRL0..2, SPUS_CTRL0..1 | 0 |
| UAIF0_CTRL0, UAIF1_CTRL0 | 01000010 |
| RDMA0_CTRL0 | 00400000 (BURST_LEN 8, wyłączony) |
| RDMA0 BUF_STR/END/OFFSET/STATUS | 0 |
| WDMA0_CTRL | 00400000 |

## Etap 4: rejestry PLL_AUD0

    CON0 a02d0110  CON1 0000f300  CON2 10000001  CON3 00005eff  CON4 8000000f

Odczyt CON5 (+0x134) daje zewnętrzne przerwanie magistrali (oops w `insmod`,
jądro przeżyło, po restarcie czysto). Wniosek dla sterownika zegarów: mainline
`pll0831x` czyta K spod `con_reg + 8` (układ gs101: CON3 i CON5), a na 9820
K leży pod `con_reg + 0xc` (CON0 i CON3), więc CMU_AUD wymaga poprawki
w `clk-pll.c`, inaczej policzy 1170 MHz zamiast 1179,648 MHz.

## Wzmacniacze (hsi2c38)

Przed sterownikiem, z przestrzeni użytkownika (`gpioset` na gph1-1/gph1-2,
`i2ctransfer`):

    0x40 DEVID 00035a40  REVID 000000a0  OTPID 00000003
    0x41 DEVID 00035a40  REVID 000000a0  OTPID 00000003
    oba: 0x3808=0000004a 0x3810=00002424 0x3814=00007500 (po resecie)
    GPIO2_CTRL1=e1000001, PAD_CONTROL=0 (GPIO2 w HiZ)
    gpm24-0 z podciąganiem SoC w dół, w górę i bez: 1, 1, 1

Po łatce 0121 (regmap debugfs): `0x3808=42`, `0x3810=2424`, `0x3814=7500`,
`0x242c=02000000`, `0x1100c=01000001`; przerwanie 116 gpm24 wspólne dla obu,
zero wyzwoleń.

## Etap 5: SysMMU bloku audio (0x18e00000, `aud_sonda5.c`)

    MMU_CTRL=00000004  MMU_CFG=00020000  MMU_STATUS=00000000
    MMU_VERSION=70600000  CAPA0=20883800  CAPA1=00000021

Bit włączenia MMU_CTRL = 0: translacja wyłączona, DMA ABOX widzi adresy
fizyczne. Wersja 7, wariant z VM (CAPA1).

## Firmware Calliope: jak programuje RDMA

Firmware (`calliope_dram.bin`, kod ARM) buduje adresy ABOX parami MOVW/MOVT
pod fizycznym 0x18c5xxxx (188 razy). Ma zestaw generowanych funkcji
dostępowych, po jednym setterze i getterze na pole; maski w nich dają układ
pól, a `wywolania.py` (na deasemblacji `arm-none-eabi-objdump -D -b binary
-marm`) wypisuje, kto je woła i z jakimi argumentami. Nazwy pól zgadzają się
ze sterownikiem ABOX dla VxWorks (github.com/reddy49/gstreamer,
audio/drv/abox/src/vxbFdtAboxDma.h).

RDMA_CTRL0 (0x18c51000 + 0x100 · id):

| bity | pole | wartość przy starcie odtwarzania |
| --- | --- | --- |
| 0 | ENABLE | 1 na końcu |
| 4 | BUF_TYPE | z wiadomości PCM_SET_BUFFER |
| 5 | BUF_UPDATE | 1 |
| 8-12 | FORMAT | (szerokość << 3) \| (kanały - 1); szerokość 1 = 16, 2 = 24, 3 = 32 bity |
| 13 | EXPEND | 1 dla formatów 8, 16, 24 (mono), inaczej 0 |
| 15 | AUTO_FADE_IN | nieużywane przy starcie |
| 16-18 | FUNC | 0; 2 na czas zmiany głośności |
| 19-22 | BURST_LEN | 8 (RDMA2: 2, RDMA7: 4) |

BUF_STR (+0x08), BUF_END (+0x0c), STR_POINT (+0x14): bity 4-31, adres bajtowy
wyrównany do 16 B; BUF_OFFSET (+0x10): bity 4-15 (okres, najwyżej 64 KiB);
VOL_FACTOR (+0x18): bity 0-23, 0x800000 = wzmocnienie 1; SBANK_LIMIT (+0x20):
bity 4-13.

Kolejność w funkcji startu (0xf860c): VOL_FACTOR 0, VOL_CHANGE, FUNC 0,
BUF_STR, BUF_END = start + rozmiar, STR_POINT = start, BUF_OFFSET, BURST_LEN,
FORMAT, BUF_UPDATE 1, BUF_TYPE, EXPEND, ENABLE 1. Osobna funkcja (0xf8a74)
zdejmuje wyciszenie: FUNC 2, VOL_FACTOR 0x800000, FUNC 0. Przerwanie RDMA
firmware włącza w GIC wewnątrz ABOX (dystrybutor 0x18cf1000, numer id + 38);
AP ma do tego GIC własny interfejs CPU (węzeł producenta `abox-gic`, SPI 46).
AP producenta wysyła w PCM_SET_BUFFER adres IOVA bufora, rozmiar okresu
i liczbę okresów (`sources/ds/abox_rdma.c:1455`).

## Eksperyment E1: samo RDMA0 z AP (`abox_e1.c`, jądro #65)

Bufor 64 KiB spójny poniżej 4 GB (`0xaac50000`), żądanie DRAM przez
`SYSPOWER_CTRL`, SBANK RDMA0 128 B, RDMA0 wg sekwencji z firmware:

    przed:          CTRL0=00400000 STATUS=00000000 SYSPOWER=1/1
    zaprogramowane: CTRL0=00400920 STR=aac50000 END=aac60000 OFF=00001000
                    PT=aac50000 SBANK=00800000
    po 200 ms:      CTRL0=00400921 STATUS=00000000
    po sprzątaniu:  CTRL0=00400000, reszta 0, SYSPOWER=0/1

Żądanie DRAM działa od razu (STATUS 1), rejestry RDMA przyjmują zapisy, ale
samo włączone RDMA nie rusza: STATUS przez 200 ms zero. Potrzebna jest cała
ścieżka, czyli wejście SPUS, SIFS z licznikiem i taktowany UAIF, który pobiera
dane. Telefon bez skutków ubocznych.

## Eksperyment E2-0: SIFS drenowany licznikiem, bez UAIF (`abox_e2.c`)

Trasa po resecie (SPUS OUT0 = SIFS1, SIFS1 = SPUS OUT0) albo przez mikser do
SIFS0, licznik SIFS wg `sifsx_cnt_val()` z zegara CNT 98,304 MHz (`0xfff`).
Warianty `qch=0x1ff` (wszystkie Q-channel wyłączone), `buftype=1`,
`misc=1` (sysreg AUD `MISC_CON`, u producenta ustawiane przy włączaniu):
za każdym razem STATUS RDMA0 = 0 przez cały test. Licznik SIFS producent
ustawia tylko dla nagrywania, a przy odtwarzaniu go zeruje: próbki ciągnie
UAIF.

## Eksperyment E3: pełna ścieżka do UAIF1 (`abox_e3.c`)

RDMA0 -> SPUS -> SIFS1 (albo mikser SIFS0) -> UAIF1 jako master I2S 16/2,
BCLK 1,536 MHz z `DIV_CLK_AUD_UAIF1` = 383 (589,824 MHz / 384), UAIF1_CTRL1
`0x0984F000`, Q-channel BCLK_UAIF1 wyłączony na czas testu, piny UAIF1
nietknięte (sygnał nie wychodzi do wzmacniaczy).

    sciezka=1: t=3 ms RDMA=80000030 ... t=11 ms RDMA=80000098
               po 200 ms RDMA=80a00070 UAIF1=00000000
    sciezka=0: t=3 ms RDMA=80000038 ... po 200 ms RDMA=80a00088 UAIF1=00000000

**DMA ABOX działa bez firmware DSP.** Bit 31 (postęp) od razu, RBUF_OFFSET
(bity 12-27) i RBUF_CNT (bity 0-11) liczą w jednostkach 16 B: między 3 a 11 ms
przybywa 104 jednostek, czyli 1664 B w 8,6 ms = 193 B/ms, a 48 kHz · 2 · 2 B
= 192 B/ms. RBUF_OFFSET 0xa00 po 200 ms to dziesięć okresów po 4 KiB. UAIF1
bez błędu (STATUS 0), po teście wszystkie rejestry i dzielnik CMU wróciły do
wartości wyjściowych.

## Prototyp ALSA: odtwarzanie i nagrywanie (`tools/phone/abox9820`, jądro #65)

Karta `S10Plus`, łącze UAIF1 (I2S 48 kHz 2x16, BCLK 1,536 MHz) do obu CS35L40.
W trakcie `aplay` wskaźnik rośnie o ok. 24 600 ramek na 0,5 s, DAPM obu
wzmacniaczy `Main AMP: On`, `PWR_CTRL1` = 1, `PWR_CTRL2` = `0x21`, bity błędów
w `IRQ1_STATUS1..4` zerowe.

**Nagrywanie.** Pola WDMA z funkcji dostępowych firmware (0xfb6d8-0xfb920):
ENABLE b0, BUF_UPDATE b5, bit 13, FORMAT b8-12, FUNC b16-18, BURST_LEN
b19-22, BUF_STR/END/OFFSET/STR_POINT/VOL pod +0x08..+0x18, ten sam układ co
RDMA. Start w firmware (0xf8eb0): VOL, STR, END = STR + rozmiar, STR_POINT,
OFFSET, BURST 8, FORMAT, bit 13 tylko przy fladze, BUF_UPDATE. SBANK NSRC
firmware przydziela przy starcie z tablic (0xf7478-0xf74f4): NSRC0 od bajtu
0x400, 32 jednostki (512 B). Trasa: `ROUTE_CTRL1` NSRC0 = 9 (UAIF1),
`SPUM_CTRL0` NSRC0 bez ASRC, wyjście do DMA, `UAIF1_CTRL0` MIC_ENABLE w
triggerze.

Pierwsza próba z WDMA0: START przechodzi (bpftrace: `abox_pcm_trigger cmd=1
ret=0`), `UAIF1_CTRL0` = `01000017`, `WDMA0_CTRL` = `00400921`, a
`WDMA0_STATUS` przez całe 375 ms zero, więc `arecord` kończy EIO (timeout
bufora 16384 ramek). Przyczyna: SIFM0 zasila WDMA1, WDMA0 bierze RECP
(`route_base_wdma`). Z WDMA1 status `804003f8` i nagranie pełne.

**VMON i IMON** (`dwaton.py` gra 1 kHz w lewym kanale i 500 Hz w prawym,
-30 dBFS, `Analog PCM Volume` 17; `analiza.py` liczy amplitudę Goertzela po
pominięciu 100 ms; `vi.sh`):

    ASP TX2 Source = IMON (po resecie), TX1 = VMON:
      kanal 0: 1 kHz 763.5, 500 Hz 0.0, zer 0/91200
      kanal 1: min -1024 max 0, zer 68338/91200 (kolizja w slocie 1)
    rejestry przez I2C w trakcie: 0x4810 = 03020101 (0x40), 03020100 (0x41),
    0x4800 = 00010003 u obu, czyli ASPTX1 i ASPTX2 wlaczone, TX2 w slocie 1
    ASP TX2 Source = Zero:
      VMON kanal 0: 1 kHz 763.3, 500 Hz 0.0 | kanal 1: 500 Hz 790.7, 1 kHz 0.0
      IMON kanal 0: 1 kHz 710.5, 500 Hz 0.2 | kanal 1: 500 Hz 730.8, 1 kHz 1.2

Lewy slot to słuchawka (0x41), prawy dolny głośnik (0x40), zgodnie z mapą
kanałów RX. Prąd przez obie cewki ma częstotliwość swojego kanału.
