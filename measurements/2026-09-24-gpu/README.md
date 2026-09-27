# GPU Mali-G76 przez panfrost (24.09.2026)

Jadro #60, DTB z etapow 16 (wezel GPU) i 17 (DVFS GPU), panfrost jako modul,
Mesa 26.2.3 z pmOS edge, Plasma Mobile 6.7.5.

## Identyfikacja (czytaj32.c, /dev/mem, tylko odczyt)

Domena G3D w PMU po bootloaderze: CONFIGURATION 0x15862100 = 1, STATUS = 1.

| rejestr | wartosc | znaczenie |
|---------|---------|-----------|
| GPU_ID | 0x72110000 | Mali-G76 r0p0 (0x7211 & 0xf00f = 0x7001, model g76 w panfroscie) |
| SHADER_PRESENT | 0x00770077 | 12 rdzeni |
| L2_PRESENT / MEM_FEATURES | 1 / 0x301 | jedna grupa, 4 plasterki L2 |
| MMU_FEATURES | 0x2830 | VA 48 bitow, PA 40 bitow |
| AS_PRESENT / JS_PRESENT | 0xff / 7 | 8 przestrzeni adresowych, 3 sloty |
| COHERENCY_FEATURES | 0 | brak koherencji |
| JM_CONFIG / SHADER_CONFIG / L2_MMU_CONFIG | 0x000f0000 / 0x00020000 / 0 | to samo, co ustawia kbase r32p1 producenta |

## Start panfrosta

```
panfrost 18500000.gpu: mali-g76 id 0x7211 major 0x0 minor 0x0 status 0x0
panfrost 18500000.gpu: shader_present=0x770077 l2_present=0x1
[drm] Initialized panfrost 1.6.0 for 18500000.gpu on minor 1
```

Mesa: `OpenGL ES profile renderer: Mali-G76 MC12 (Panfrost)`, `OpenGL ES 3.1 Mesa 26.2.3`.

## Poprawnosc (porownaj.c)

Ta sama scena (1440x3040, tekstura z mipmapami, mieszanie alfa, shader
z trygonometria) na panfroscie i na llvmpipe: 13 132 800 kanalow, 85,4%
identycznych, 14,5% rozni sie o 1, 0,13% o 2, 120 o 3-8, zadnego wiecej niz 8
(max 4). Obraz: porownanie.png (lewo GPU, prawo llvmpipe). Walidacja glmark2
(`--validate`) pada tak samo na llvmpipe, wiec nie nadaje sie na dowod.

## Wydajnosc (glmark2-es2-wayland --off-screen, 1440x3040)

| scena | GPU 156 MHz | llvmpipe |
|-------|-------------|----------|
| texture | 402 kl/s | 49 kl/s |
| shading phong | 294 | 20 |
| effect2d | 163 | 19 |
| desktop blur, 4 okna | 58 | 6 |
| wynik | 228 | 22 |

## Zegar GPU przez APM (g3d_takt.c, clk_set_rate przez clk-acpm)

glmark2 texture: 156 MHz 404 kl/s, 325 MHz 767 kl/s (1,90x przy 2,08x
zegara), z powrotem 156 MHz 403 kl/s. Obie wiadomosci potwierdzone
(`clk_set_rate = 0`). Poziomy fvmap G3D: 702, 676, 650, 598, 572, 433, 377,
325, 260, 200, 156 (start), 100 MHz.

## Plasma na GPU (~/narz/ab.sh, 5 x szuflada w 17,1 s)

| | llvmpipe rano | llvmpipe z cpufreq | GPU 156 MHz | GPU z devfreq |
|---|---|---|---|---|
| render klatki KWin, mediana | 103-115 ms | 108-112 ms | 7,4 ms | 6,4-7,4 ms |
| CPU plasmashell / 17 s | 83-86 s | 51-57 s | 2,5-2,7 s | 0,9-1,2 s |
| system zajety | 73-75% | 52-58% | 6% | 4-5% |
| odstep klatek w animacji, mediana | 162 ms | 131-146 ms | 43-48 ms | 47-51 ms |

Z devfreq GPU spedzilo 11,4 s na 156 MHz i 1,7 s na 702 MHz: GPU nie jest
waskim gardlem. Od konca renderu do przelaczenia klatki mija ok. 50 ms:
klatka idzie do simpledrm, ktory kopiuje procesorem 17,5 MB z konwersja
XRGB8888 -> ARGB8888 (framebuffer bootloadera ma format a8r8g8b8, simpledrm
wystawia tylko XR24). Sama kopia z bufora wlasnego simpledrm (kopia-drm.c):
9,2 ms na M4, 13,8 ms na A75, 16,9 ms na A55; KWin oddaje bufor z pamieci GPU.
Do 60 kl/s potrzebny jest wlasny sterownik DECON (skan bez kopii, vblank).

## Bledy zadan GPU (otwarte)

Okolo 25-50 bledow na 165 s po starcie, 90% z plasmashell, reszta KWin
(pierwszy zawsze ok. 18 s, jc=0xb2e8140): DATA_INVALID_FAULT, JOB_BUS_FAULT,
INSTR_INVALID_ENC, IMPRECISE_FAULT, TILE_RANGE_FAULT. Proste programy
jednokontekstowe bez bledow.

Wykluczone pomiarem, kazde osobnym rozruchem, liczba bledow bez zmian:
runtime PM GPU (power/control=on), THP panfrosta, flush reduction, mapowania
WB (wymuszone WC), jedno zadanie na slot (credit_limit=1), pelne FLUSH_MEM
(L2 + TLB) przed kazdym zadaniem, Mesa 26.2.3 z MR !41072, Mesa main
5338eb32, PAN_MESA_DEBUG=sync (plasmashell nadal trafia na blad i sie
przerywa).

Sprawdzone narzedziami: strony mmap procesow zgodne ze stronami buforow
(strony_bo.c: 14898/14898 i 45/45), tablice stron MMU GPU zgodne ze
stronami buforow, bez wpisow w dziurach (gpu_strony.c: 141878 i 63363
stron). W chwili bledu (panfrost-diag.py --cache) linia pod adresem
zadania czytana przez cache i przez WC jest identyczna: tylko status
i adres bledu wpisane przez GPU, reszta zera. Czyli w pamieci, ktora obie
strony widza jednakowo, nie ma deskryptora, ktory Mesa wskazala.

Ten sam objaw zgloszony w Mesie: issue 16359 (Mali-G57, panfrost 1.6.0,
jadro 7.3-rc3, Mesa 26.1.7-26.2.3), bez odpowiedzi.

## Mesa 24.3.4: bledy te same (regresja Mesy 25/26 wykluczona)

Mesa 24.3.4 (tylko panfrost i softpipe, bez LLVM) zbudowana na telefonie do
/opt/mesa-243. Budowanie wymagalo jednej poprawki: przy wayland-client 1.26
(HAVE_WL_DISPATCH_QUEUE_TIMEOUT) src/loader/loader_wayland_helper.c nie
dolacza util/timespec.h, a uzywa timespec_sub_saturate bezwarunkowo.

Sesja z tym samym jadrem #60 i DTB etapu 18, srodowisko przez
~/.config/plasma-workspace/env: KWin, plasmashell i Xwayland zaladowaly
libgallium-24.3.4.so, KWin zglosil "OpenGL ES 3.1 Mesa 24.3.4". Do 95 s po
starcie (dmesg-mesa243.txt na telefonie): 24 DATA_INVALID_FAULT,
10 INSTR_INVALID_ENC, 2 IMPRECISE_FAULT, pierwszy blad po 19,6 s. Te same
klasy i to samo tempo co na Mesie 26.2.3 (25-50 na 165 s), wiec to nie jest
regresja Mesy 25/26. Zostaja: jadro 7.x (panfrost 1.6), platforma (DT,
zegary, pamiec) i errata G76 r0p0, ktorych nie obsluguje zadna Mesa.

Uboczne: pod Mesa 24.3.4 obraz w Plasmie byl przeswietlony i nieczytelny
(ocena uzytkownika). Przyczyny nie badalem; sesja wrocila do Mesy 26.2.3.

## ROZWIAZANE: tablice stron AARCH64_4K (latka 0116)

Przyczyna: panfrost uruchamial G76 w trybie legacy (LPAE): kazdy bufor
dostawal atrybut 0x8D z SH_OS, a spacer tablic zadnych atrybutow. Jadro
producenta (kbase bv_r32p1, wybrane przez defconfig beyond2lte) uruchamia ten
GPU wylacznie z tablicami AArch64 4K (TRANSCFG 0x42000006). Te sama rodzine
bledow na MT8188 (G57) usunal w mainline commit 21fc936cae3
(GPU_QUIRK_FORCE_AARCH64_PGTABLE). Wczesniejsze pomiary "tablice MMU =
strony buforow" sprawdzaly adresy, nie atrybuty.

Latka 0116 dopasowuje "samsung,exynos9820-mali" i wymusza AARCH64_4K. Pomiar
(licz-gpu.sh, bledy js fault w pierwszych 165 s po starcie, DECON M1b):
baza 202 (170 IMPRECISE, 30 DATA_INVALID, 2 JOB_BUS, 1 INSTR_INVALID_ENC),
po zmianie 0, a przez 325 s z szuflada, CPU w 100% i wideo 1080p60 nadal 0.
Uzytkownik: glicz brak. KWin renderuje na "Mali-G76 MC12 (Panfrost)",
devfreq GPU pracuje (74 przejscia w pierwszej minucie).
