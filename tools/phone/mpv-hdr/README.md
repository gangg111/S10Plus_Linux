# HDR10, HDR10+ i HLG na panelu S6E3HA9

Panel Galaxy S10+ nie dekoduje PQ ani BT.2020. Android pokazuje HDR tak, ze
odtwarzacz mapuje tony do mozliwosci panelu (dla HDR10+ wedlug metadanych
dynamicznych ST 2094-40), a system podbija jasnosc panelu do trybu HBM. Tutaj
ta sama droga idzie przez mpv i KWin:

1. mpv (`vo=gpu-next`, libplacebo) mapuje tony klatka po klatce wedlug metadanych
   HDR10+ (`tone-mapping=st2094-40`) do szczytu 800 nitow i renderuje wynik w PQ,
   BT.2020, 10 bitow na kanal.
2. mpv podaje KWin opis obrazu (wp_color_management: BT.2020, PQ, 800 nitow).
3. KWin 6.7.5 z polityka EDR podnosi jasnosc panelu z poziomu SDR (420 nitow) do
   800 nitow, a tresc SDR na ekranie przyciemnia o ten sam wspolczynnik.
4. Modul `s6e3ha9_jas` (tools/phone/s6e3ha9-jasnosc, `hbm=1`) realizuje 800 nitow
   (od 27.09.2026 z pakietami IRC i POC producenta; bez nich HBM gasil ekran)
   krzywa HBM z MTP panelu.

Pomiary i dowody: measurements/2026-09-25-hdr.

## Co tu lezy

| plik | na telefonie | co to |
|---|---|---|
| `buduj-mpv.sh` | `~/narz/mpv-hdr/` | buduje mpv 0.41.0 z latka i instaluje za opakowaniem |
| `mpv-opakowanie.sh` | `/usr/local/bin/mpv` | ustawia `PAN_MESA_DEBUG=linear` i uruchamia mpv |
| `mpv.conf` | `~/.config/mpv/mpv.conf` | SDR: `vo=gpu` + `profile=fast`; profil `[hdr]` |
| `hdr-auto.lua` | `~/.config/mpv/scripts/` | wlacza `[hdr]` dla PQ i HLG przed otwarciem pliku |

## Latka mpv

mpv 0.41 wiaze powierzchnie koloru Wayland tylko dla `vo=dmabuf-wayland`. Na
OpenGL (Mali-G76 nie ma uzywalnego Vulkana: panvk na v7 to Vulkan 1.0 za flaga
`PAN_I_WANT_A_BROKEN_VULKAN_DRIVER`, a libplacebo wymaga wiecej) nikt inny opisu
obrazu nie ustawia, wiec KWin traktuje wyjscie mpv jako sRGB i EDR sie nie wlacza.
Latka w `buduj-mpv.sh` dopisuje `gpu-next` do warunku w `video/out/wayland_common.c`.

## Profil HDR

`target-colorspace-hint-strict=no` jest konieczne: w trybie scislym mpv bierze
cel z lancucha wymiany OpenGL, ktory zna tylko BT.709, i podaje KWin prymarne
BT.709 mimo `target-prim=bt.2020`.

Profil wlacza skrypt Lua, a nie `profile-cond`: zmiana `vo` w locie zeruje
`video-params`, warunek staje sie falszywy i mpv przelacza wyjscie w petli
(gpu, gpu-next, gpu...) bez ani jednej klatki. Skrypt czyta krzywa przejscia
z naglowka strumienia (`ffprobe`) w haku `on_load`, zanim powstanie wyjscie.

## Tekstury liniowe

Dekodowanie jest programowe (MFC nie ma sterownika w mainline). Przy 4K watek
`vo` zjada 85% duzego rdzenia: 62% to `memcpy` do pamieci GPU, reszta to
kafelkowanie tekstur w panfroscie i bledy stron. `PAN_MESA_DEBUG=linear` usuwa
kafelkowanie; opakowanie ustawia je tylko dla mpv, reszta pulpitu go nie widzi.

| plik (10 s, 24 kl/s) | kafelki | liniowe |
|---|---|---|
| 2160p HDR10+ | 51 zgubionych | 2 |
| 1440p HDR10+ | 11 | 0 |
| 1080p HDR10+ | 1 | 1 |
| 1080p60 SDR (vo=gpu) | 4 | 4 |

Zrzut tej samej klatki z kafelkami i bez: sredni rozjazd 0,1 na 65535.

## Ustawienia KWin

`~/.config/kwinoutputconfig.json`, wyjscie DSI: `colorProfileSource: "EDID"`,
`edrPolicy: "always"`, `highDynamicRange: false`. EDID z modulu decon9820 niesie
prymarne Display P3 i blok metadanych HDR z luminancjami panelu (800/420 nitow),
ale bez PQ, bo panel go nie dekoduje; dlatego KWin wlacza EDR, a nie tryb HDR.
EDR wymaga urzadzenia jasnosci z PowerDevil (`/sys/class/backlight/s6e3ha9`).

## Ograniczenia

- 4K HDR10+ trzyma 24 kl/s z 1-5 zgubionymi klatkami na 10 s. Material 4K60
  wymaga sprzetowego dekodera (MFC), ktorego sterownika nie ma.
- Aplikacje inne niz mpv (przegladarka, odtwarzacze na GStreamerze) nie podaja
  opisu obrazu HDR, wiec pokaza HDR jako SDR.
