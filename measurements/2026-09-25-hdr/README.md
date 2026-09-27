# HDR10+ na telefonie, 25.09.2026

Jadro #61, decon9820 v4 (EDID z blokiem HDR), s6e3ha9_jas `tryb=1 hbm=1`,
KWin 6.7.5 (EDR `always`, profil koloru z EDID), mpv 0.41.0 z latka
(tools/phone/mpv-hdr), Mesa 26.2.3 (panfrost). Opis calej drogi i ustawien:
tools/phone/mpv-hdr/README.md.

## Klip testowy

x265 w Alpine nie ma `--dhdr10-info`, wiec metadane HDR10+ wstrzykuje
`wstrzyknij_hdr10plus.py` jako prefiksowy SEI T.35 (B5 003C 0001 04, wersja 1,
skladnia ST 2094-40 jak `av_dynamic_hdr_plus_to_t35` w FFmpeg) przed pierwszym
plastrem kazdej klatki. `hdr10plus_json.py` robi dwie sceny: jasna (MaxSCL
1000/900/800 nitow) i ciemna (150/140/130). `zrob-klip.sh` sklada 10 s 1080p24
HEVC Main10 PQ/BT.2020 z HDR10 statycznym i HDR10+; ffprobe czyta metadane
dynamiczne obu scen.

## Wynik 1: EDR i opis obrazu (`test-hdr.sh`)

Jasnosc panelu (`actual_brightness`, nity) co 0,5 s od startu mpv:

    przed: panel 420 z 800
    420 420 473 585 698 796 800 800 800 800 800 800 800 800 800 800 800 800 800 800 800 800
    po: panel 420

mpv w obu scenach czyta inne metadane dynamiczne (scene-max 1000/900/800 i
150/140/130), cel renderowania i opis dla KWin to PQ, BT.2020, 800 nitow,
0 zgubionych klatek. Bez `target-colorspace-hint-strict=no` opis mial prymarne
BT.709 (cel z lancucha wymiany OpenGL).

## Wynik 2: metadane dynamiczne zmieniaja obraz (`dowod-dynamiki.sh`)

Ta sama nieruchoma tresc (smptehdbars) w obu scenach, rozne metadane HDR10+.
Zrzut okna mpv w scenie jasnej (2,5 s) i ciemnej (7,5 s), `porownaj_png.py`
liczy w obszarze obrazu:

| mapowanie tonow | sredni rozjazd scen |
|---|---|
| st2094-40 (dynamiczne) | 237,7 z 65535 (0,81%) |
| bt.2390 (statyczne, kontrola) | 26,9 (0,09%, szum kodeka) |

## Wynik 3: profil automatyczny (`test-profil.sh`)

Zwykle `mpv plik`: HDR10+ idzie przez gpu-next, PQ/BT.2020/800, panel 800;
SDR 1080p60 zostaje na `vo=gpu`, BT.1886/BT.709, panel 420. Pierwsza wersja
z `profile-cond` przelaczala vo w petli i stala na 0%.

## Wynik 4: 4K i tekstury liniowe (`macierz.sh`, `perf-vo.sh`)

Zgubione klatki na 10 s, dekoder 0 we wszystkich:

| plik | kafelki | `PAN_MESA_DEBUG=linear` |
|---|---|---|
| 2160p24 HDR10+ | 51 | 2 |
| 1440p24 HDR10+ | 11 | 0 |
| 1080p24 HDR10+ | 1 | 1 |
| 1080p60 SDR | 4 | 4 |

Przy 4K watek `vo` zuzywa 85% rdzenia (na M4, cpu6/7), GPU skacze 156-702 MHz,
czyli nie jest nasycone. perf watku vo: 62% `memcpy` (musl), ok. 20% kod
kafelkowania w libgallium, reszta bledy stron (`el0_da`, `clear_page`).
Przypiecie mpv do cpu4-7 pogarsza (94 zgubione), bo dekoder traci rdzenie.
`linear-poprawnosc.sh`: ta sama klatka z kafelkami i bez, sredni rozjazd 0,1.
Przez opakowanie `/usr/local/bin/mpv`: 2160p 1-5, 1440p i 1080p po 1.
