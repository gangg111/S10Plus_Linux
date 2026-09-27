# Plynnosc pod obciazeniem (24.09.2026)

Jadro #60, DTB etapu 18, cma=256M@0-4G, DECON M1b (decon9820 ladowany
przy starcie), Mesa 26.2.3, KWin 6.7 z KWIN_LOG_PERFORMANCE_DATA. Odstep
klatek liczony z dziennika klatek KWin (jak w ab.sh), wideo testowe
1080p60 H.264 8 Mb/s (ffmpeg testsrc2, 30 s), dekodowane programowo
(mainline nie ma dekodera sprzetowego MFC). Skrypty: pod-obciazeniem.sh,
mpv-diag.sh, mpv-dvfs.sh.

## Wyniki

| scenariusz | odstep klatek KWin, mediana / p90 | uwagi |
|---|---|---|
| szuflada, bez obciazenia (M1b) | 16,71 / 16,9 ms | |
| szuflada + 8 rdzeni w 100% | 16,70 / 16,84 ms | big 47 -> 91 C w 19 s, dlawienie do 1,46 GHz |
| mpv domyslny (vo=gpu-next) | 66,7 / 100 ms | ok. 43 klatki/s zgubione przez VO |
| mpv gpu-next, GPU przypiete 702 MHz | 33,7 / 100 ms | libplacebo za ciezki nawet na max takcie |
| mpv vo=gpu | 16,76 / 33,4 ms | 39 zgubionych, GPU glownie 702 MHz |
| mpv vo=gpu, profile=fast | 16,72 / 31,6 ms | 4 zgubione, GPU 14,7 s z 15 na 156 MHz |
| mpv z mpv.conf (vo=gpu, profile=fast), bez parametrow | 16,71 / 16,89 ms | 3 zgubione, 93,3% klatek w jednej ramce |
| mpv gpu-next + szuflada | 66,2 / 100 ms | |

Dekoder nadaza: przy vo=null 0 zgubionych klatek przy 143% jednego rdzenia
(z 8). Waskim gardlem byl renderer mpv, nie CPU, nie DECON i nie KWin
(render KWin 2,7-4,7 ms we wszystkich scenariuszach).

## Wniosek i zmiana

Interfejs trzyma 60 kl/s przy pelnym obciazeniu CPU. Wideo 1080p60 trzyma
60 kl/s po ustawieniu ~/.config/mpv/mpv.conf (vo=gpu, profile=fast);
domyslny gpu-next daje 15-30 kl/s na tym GPU. Inne odtwarzacze (np. Haruna
przez libmpv) trzeba bedzie sprawdzic osobno.

Governor simple_ondemand przy gpu-next skacze po calej tabeli 156-702 MHz,
ale przy przypietym 702 MHz wynik jest dalej ponizej 60 kl/s, wiec to nie
governor ogranicza.

Bledy zadan GPU w tych testach dalej wystepuja (88 -> 95 od startu w czasie
prob mpv), osobny watek: measurements/2026-09-24-gpu.
