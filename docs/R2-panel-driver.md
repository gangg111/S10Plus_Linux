# Szkic sterownika panelu S6E3HA9 do mainline

**Stan:** kompiluje się, przechodzi `dt_binding_check` i `checkpatch --strict`, **nie był
uruchomiony na sprzęcie** (nie ma jeszcze hosta DSI dla 9820 w mainline — patrz `docs/R2-display.md`).
Artefakty: `patches/0016`,
`patches/0017`.

## 1. Co jest w sterowniku

`drivers/gpu/drm/panel/panel-samsung-s6e3ha9-main.c` (371 linii), wzorowany na istniejącym w mainline
`panel-samsung-s6e3ha8.c` (ten sam producent DDI, ta sama klasa panelu, S9):

| element | źródło danych |
|---|---|
| tryb 1440×3040@60, porch 2/2/2 i 15/3/1, 70×148 mm | węzeł DT `s6e3ha9_beyond2`, `docs/R2-panel-timings.md` §2 |
| sekwencja `prepare`/`enable`/`disable` | `beyond2_a3_s0_*_cmdtbl`, §9 tamże |
| DSC 1.1, 8 bpp, 2 slice’y 720×40 | firmowy PPS, §3 tamże |
| FFC `C5 0D 10 B4 3E 01` | §8 tamże |
| TSP HSYNC / TE start `B9 01 B0 E1 09 …` | §10 tamże |
| `reset-gpios` | `disp-reset` = **gpa3-4, active low** (overlay płyty, alias `gpa3` w `…_26.dts:8132`) |
| zasilanie `vdd3`/`vci`/`vddr` | S2DOS05: ldo1 1,8 V / ldo4 3,0 V / buck1 1,5–1,6 V (`…_26.dts:6529-6552`) |

Nazewnictwo zasilań i podział ról wzięte z bindingu `samsung,s6e3ha8.yaml`, a napięcia
z downstreamu potwierdzają to przypisanie 1:1.

## 2. DSC: dlaczego nie ma w kodzie ręcznie wpisanych 30 pól

Sterownik ustawia tylko to, co jest specyficzne dla panelu (wymiary, slice, bpp, bpc,
`line_buf_depth`, `block_pred_enable`, `convert_rgb`), a resztę liczą helpery DRM:

```c
drm_dsc_set_const_params(dsc);
drm_dsc_set_rc_buf_thresh(dsc);
drm_dsc_setup_rc_params(dsc, DRM_DSC_1_1_PRE_SCR);
dsc->initial_scale_value = drm_dsc_initial_scale_value(dsc);
drm_dsc_compute_rc_parameters(dsc);
```

To nie jest założenie — **zweryfikowane**: `scripts/check-dsc-config.py` odtwarza algorytm
z `drm_dsc_helper.c` i porównuje wynik z bajtami firmowego PPS. Zgodność **30/30 pól**, w tym
te liczone (`initial_dec_delay` 616, `scale_increment_interval` 1132, `scale_decrement_interval` 10,
`nfl_bpg_offset` 631, `slice_bpg_offset` 489, `final_offset` 4336, `slice_chunk_size` 720) oraz
komplet `rc_buf_thresh[14]` i `rc_range_params[15]`. Log: `build-logs/23-dsc-config-check.log`.

Wniosek: firmowy PPS S6E3HA9 to czysty DSC 1.1 pre-SCR dla 8 bpp/8 bpc — żadnych odstępstw
producenta, więc kopiowanie tablic byłoby powielaniem tego, co jądro już ma.

## 3. Niezależne potwierdzenie FFC

Istniejący w mainline `panel-samsung-s6e3ha8.c:109-110` wysyła **identyczne** bajty FFC
(`0xc5, 0x0d, 0x10, 0xb4, 0x3e, 0x01`) z komentarzem „FFC Setting **897.6Mbps**". Dokładnie ten
zegar wychodzi z odwrócenia modelu FFC w `docs/R2-panel-timings.md` §8 (0x3E01 → 897,6 Mbps).
Dwa niezależne źródła, ta sama liczba.

## 4. Czego sterownik NIE robi (świadomie)

- ~~**Jasnosc**~~ zamkniete, patrz sekcje 7 i dalej: czesc AID (AOR, ELVSS, VINT) plus
  gamma per poziom liczona z MTP panelu. Poza zakresem zostaja HBM i kompensacja
  temperaturowa.
- **Tryby DSU** (1080×2280, 720×1520) — jest tylko tryb natywny.
- **AOD/LPM, MDNIE, COPR, HMD** — funkcje downstreamu bez odpowiednika w DRM.

## 5. Bramki

| bramka | wynik | log |
|---|---|---|
| kompilacja `panel-samsung-s6e3ha9.o` | **EXIT=0**, 0 ostrzeżeń z naszego pliku | `build-logs/21-panel-driver-build.log` |
| `dt_binding_check` bindingu panelu | **EXIT=0** | `build-logs/22-panel-binding-check.log` |
| zgodność DSC z firmowym PPS | **30/30 pól** | `build-logs/23-dsc-config-check.log` |
| `checkpatch --strict` (0004, 0005) | 0 błędów, 1 ostrzeżenie klasy „MAINTAINERS?" | `build-logs/05-checkpatch.log` |
| `git apply --check` całej serii (5 patchy) na czystej bazie | OK | — |

**Uczciwie o kompilacji:** pełny `kbuild` nie działa na Termuxie — host-toole (`sorttable`,
`asn1_compiler`, `scripts/mod/modpost`) nie kompilują się z bionikiem (brak `R_ARM_*`,
`ELF64_ST_TYPE`, kolizja `linux/types.h`). Dlatego nagłówki generowane normalnie przez
`make prepare` (`cpucap-defs.h`, `kernel-hwcap.h`, `sysreg-defs.h`, `bounds.h`, `timeconst.h`,
`rq-offsets.h`) zostały wytworzone tymi samymi skryptami co w Kbuildzie, a sam plik skompilowany
flagami jądra (`scripts/kcc-termux.sh` = `LINUXINCLUDE` + `CC_FLAGS_DIALECT`, w tym `-fms-extensions`).
**To dowodzi poprawności kodu i typów, nie dowodzi linkowania modułu ani `modpost` — do zrobienia
na PC przed wysłaniem serii.**

## 6. Zanim to pójdzie upstream

1. Wpis w `MAINTAINERS`.
2. Pełny build na PC (`make drivers/gpu/drm/panel/panel-samsung-s6e3ha9.o` + moduł).
3. Uruchomienie na sprzęcie — czyli najpierw host DSI/DECON dla 9820 (bramka B3).
4. Dopiero potem sensowny backlight (AID dimming z MTP).

## 7. Sterowanie jasnością (dopisane, `patches/0018`)

Panel nie przyjmuje `SET_DISPLAY_BRIGHTNESS` — poziom ustawia się **duty AOR** (`0xB1`) razem
z **ELVSS** (`0xB5`) i **VINT** (`0xF4`), zatrzaskiwanymi aktualizacją gammy (`0xF7 0x03`),
wszystko pod kluczem poziomu 2. Sterownik rejestruje `backlight_device` i programuje te trzy
rejestry przy każdej zmianie jasności.

### Tablice

74 poziomy UI (jasność platformy 0-255, 2-420 nitów), przepisane z firmowych tablic:

| kolumna | źródło |
|---|---|
| `brightness` (próg poziomu) | `…_panel_dimming.h`, `beyond2_a3_s0_brt_tbl` |
| `nits` (deklarowana luminancja) | tamże, `beyond2_a3_s0_lum_tbl` |
| `aor[2]` | `…_panel.h`, `beyond2_a3_s0_aor_table` |
| `elvss` | tamże, `beyond2_a3_s0_elvss_table`, wycinek **OVER_ZERO** (temperatura pokojowa) |
| `vint` | tamże, `beyond2_a3_s0_vint_table`, ten sam wycinek (stałe `0x23` w całym zakresie UI) |

**Weryfikacja:** `scripts/check-aid-tables.py` czyta wiersze z **kodu sterownika** i zestawia je
z nagłówkami producenta — **74/74 wiersze zgodne**, `build-logs/40-aid-tables-check.log`.
Nie przepisywałem ich ręcznie: zostały wygenerowane skryptem z tych samych nagłówków.

### Czego to nie robi (i dlaczego)

1. ~~**Nie liczy gammy per poziom.**~~ — **zrobione**, patrz sekcja „Silnik dimmingu z MTP" niżej.
   Oryginalny opis braku: To druga połowa tego, co producent nazywa AID dimming: krzywa
   gamma (`0xCA`, 34 bajty) jest u niego wyliczana z danych **MTP** panelu przez silnik dimmingu
   (`drivers/video/fbdev/exynos/panel/dimming.c` + tablice `_panel_dimming.h`, 59 KB danych
   wejściowych). Bez tego panel zostaje na gammie zaprogramowanej przy starcie, więc dany krok
   nie trafi dokładnie w swoją luminancję — jasność jest monotoniczna i sterowalna, ale nie
   skalibrowana fotometrycznie.
2. **Bez HBM** — 16 poziomów powyżej 255 (do 800 nitów) pominięte.
3. **Bez kompensacji temperaturowej** — używany jest wycinek OVER_ZERO; producent przełącza
   tablice ELVSS/VINT wg odczytu temperatury.

Odczyty DSI potrzebne do MTP już są (`patches/0034`), więc punkt 1 jest odblokowany technicznie —
brakuje samego silnika dimmingu.

### Bramki

kompilacja EXIT=0 (0 uwag z pliku), `checkpatch --strict` 0 bledow, cala seria stosuje sie
na czysta baze. Bramki liczbowe: `scripts/check-dsc-config.py` (30/30 pol DSC),
`scripts/check-aid-tables.py` (74/74 wiersze AID), `scripts/check-dimming-engine.sh`
(74/74 poziomy dla 7 zestawow MTP). Wszystkie wpiete w `scripts/verify.sh`.

### Silnik dimmingu wpiety w sterownik (patches/0019)

Punkt 1 z listy brakow wyzej jest **zamkniety**. Sterownik czyta 34 bajty MTP komenda
DCS 0xC8 zaraz po wybudzeniu ukladu i przed pierwszym ustawieniem jasnosci, przepuszcza
je przez silnik i wysyla wyliczona krzywa gammy pakietem 0xCA razem z reszta warunku
jasnosci, przed istniejacym zatrzaskiem 0xF7.

Rejestr, offset i dlugosc sa te same, co u producenta: `S6E3HA9_MTP_REG` = 0xC8,
`S6E3HA9_MTP_OFS` = 0, `S6E3HA9_MTP_LEN` = 34 (`sources/ds/s6e3ha9.h:39-41`). Dane sa
jednorazowo programowane w panelu, wiec wystarczy jeden odczyt na wlaczenie zasilania;
sterownik trzyma flage `gamma_valid`.

Panel, ktory nie odpowie na odczyt, **nie jest traktowany jako blad**: jasnosc pozostaje
monotoniczna przez AOR, ELVSS i VINT, traci sie tylko kalibracje fotometryczna kroku.
Sterownik zglasza to `dev_warn` i jedzie dalej. Uzasadnienie: brak MTP degraduje jakosc,
nie funkcje, a wywalenie `prepare()` zabraloby obraz calkowicie.

**Czego to nadal nie robi**: HBM (16 poziomow powyzej 255, do 800 nitow) i kompensacji
temperaturowej ELVSS/VINT. Producent ma 90 wierszy jasnosci, port ma 74 i wycinek
OVER_ZERO.

Wazne, zeby nie zrobic tego zle: **HBM nie jest rozszerzeniem tablicy o 16 wierszy**.
Producent czyta dla HBM **osobna** 34-bajtowa krzywa gammy z panelu, rejestrem 0xB3 od
offsetu 2 (`S6E3HA9_HBM_GAMMA_REG`, `S6E3HA9_HBM_GAMMA_OFS`, `S6E3HA9_HBM_GAMMA_LEN`,
`sources/ds/s6e3ha9.h:51-53`; zasob `RES_HBM_GAMMA`, `sources/ds/s6e3ha9.c:590`, `:717`).
Dopisanie samych wierszy AOR, ELVSS i VINT dalo by monotoniczna jasnosc powyzej 255
z **bledna** luminancja, bo krzywa gammy pozostalaby ta z zakresu UI. Dlatego HBM czeka
na osobny patch, ktory dolozy drugi odczyt i druga sciezke gammy, a nie na doklejenie
16 wierszy do istniejacej tablicy.

**Czego to nie dowodzi**: ze wartosci gammy licza sie poprawnie dla NASZEGO panelu.
Arytmetyka jest zgodna z silnikiem producenta bajt w bajt dla 7 zestawow losowych MTP,
ale na realnym MTP z egzemplarza nie byla uruchomiona ani razu. To pozycja HW-06
w `docs/HW-BLOCKED.md`.

### Polaryzacja resetu (poprawka w patches/0017)

Pierwotna sekwencja resetu byla przepisana ze sterownika S6E3HA8 razem z jego
konwencja DT. Tamten binding opisuje `reset-gpios` jako `GPIO_ACTIVE_HIGH`
(przyklad w `samsung,s6e3ha8.yaml`), wiec ciag 1-0-1 konczy sie na stanie wysokim,
czyli z ukladem **wypuszczonym** z resetu.

Nasz binding i DT deklaruja `GPIO_ACTIVE_LOW`, bo tak opisuje ten pin downstream:
wezel `disp-reset` to `gpa3 4` z flaga `0x1`
(`sources/ds/exynos9820-beyond2lte_eur_open_26.dts:6626-6628`). Przy tej polaryzacji
wartosc logiczna 1 **wciska** reset, wiec skopiowany ciag konczyl sie z panelem
trzymanym w resecie, po czym leciala do niego cala sekwencja DCS, a zwolnienie
nastepowalo dopiero w `unprepare`. Obie polowki byly odwrocone.

Po poprawce: `s6e3ha9_reset()` wciska reset, czeka 5 ms, zwalnia i czeka 10 ms;
`unprepare()` i sciezka bledu w `prepare()` wciskaja reset przed zdjeciem zasilania.
Same czasy pozostaja niepewne i sa oznaczone `UNVERIFIED: HW-21`.
