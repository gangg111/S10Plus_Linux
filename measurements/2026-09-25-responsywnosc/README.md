# Responsywnosc: narzedzia wskazuja winnego (25.09.2026)

Jadro #61 (konfiguracja diagnostyczna: ftrace, kprobes, BTF, PSI, schedstats,
uclamp; sekcja "diagnostyka" w scripts/exynos9820.config), DECON M1b, panfrost
z tablicami AARCH64_4K, Mesa 26.2.3, KWin 6.7. Na telefonie: perf 7.1.5,
bpftrace 0.27, bcc-tools 0.37, trace-cmd 3.3.1 (apk).

## Metoda

slad-nagraj.sh nagrywa trace-cmd: sched_switch/wakeup/waking, cpu_frequency,
gpu_scheduler oraz sondy kprobe na calej drodze obrazu: evdev_events (dotyk),
drm_mode_atomic_ioctl (commit KWin), decon9820_pokaz (flip) i jego powrot
(zatrzask na TE), drm_crtc_send_vblank_event. Ruch robi syntetyczny palec
(uinput, 5 przesuniec szuflady). slad-analiza.py liczy czekanie w planiscie,
rdzen i takt startu kazdego watku, dlugosc biegow, czasy GPU i droge od dotyku
do zatrzasnietej klatki; slad-klatki.py rozbija klatke (commit -> flip ->
zatrzask), slad-podwojne.py pokazuje, gdzie wypadaja podwojne klatki.

## Co wskazaly narzedzia

1. perf (cpu-clock, 56 738 probek w animacji): system 97,7% bezczynny, KWin
   0,09% probek, plasmashell 1,59% (harfbuzz, QFontEngineFT, QML). Mocy nie
   brakuje.
2. Planista nie jest winny: od wybudzenia do startu mediana < 0,1 ms, p99 <= 3 ms.
3. Nasz sterownik wyswietlania nie jest winny: commit KWin -> flip 0,22 ms,
   flip -> zatrzask 1,1 ms (mediana), zatrzask -> zdarzenie do KWin 0,01 ms.
4. **Winny: takty i rdzenie.** Watki interfejsu chodza na malych i srednich
   rdzeniach przy minimalnym takcie (maly 442 MHz 93% czasu, sredni 507 MHz
   99%, duzy 520 MHz 99%, nieuzywany). schedutil widzi zrywy 1-5 ms na klatke
   i nie podnosi taktu; najdluzsze zrywy (plasmashell 31,8 ms, watek wejscia
   KWin 26 ms) zrywaja klatki.

| wariant | watki UI na | od dotyku do zatrzasku, mediana / p90 | odstep klatek p99 | podwojne klatki |
|---|---|---|---|---|
| bez podbicia | male/srednie, 442-507 MHz | 53,1 / 57,6 ms | 33,4 ms | 10 |
| uclamp.min 512 staly | srednie/duze, ~1040 MHz | 38,8 / 49,8 ms | 33,4 ms | |
| uclamp.min 1024 staly | duze, 2080 MHz | 37,3 / 47,1 ms | 16,93 ms | 0 |
| demon, samo podbicie 1024 w interakcji | duze w interakcji | 42,7 / 48,6 ms | 33,4 ms | 2 (70-120 ms od poczatku gestu) |
| **demon + prog 512 dla rysujacych** | duze w interakcji | 46,5 / 58,1 ms | **16,90 ms** | **0** |

Od dotyku do zatrzasku sklada sie z czekania plasmashell na swoja klatke
(~9-13 ms), renderu GPU (~1-2 ms), przytrzymania klatki przez watek commitow
KWin (DSI-1) do terminu przed vblankiem (~10-11 ms) i czekania na TE (~1 ms);
to typowa glebokosc potoku (2-3 ramki), jak w Androidzie.

## Zmiana: tools/phone/podbicie

Demon jak PowerHAL w Androidzie: na zdarzenie z dowolnego urzadzenia wejscia
(takze nowego, inotify) nadaje watkom sesji uzytkownika uclamp.min 1024, 1,5 s
po ostatnim zdarzeniu zdejmuje; KWin, plasmashell i plasma-keyboard maja staly
prog 512 (jak SurfaceFlinger i SystemUI). Jednostka podbicie.service w
/etc/systemd/system, binarka /usr/local/sbin/podbicie.

## Pulapki

- perf na tym SoC: domyslne cycles nie obejmuje wszystkich trzech PMU (A55,
  A75, Mongoose); uzywac -e cpu-clock.
- `perf record -- sh skrypt` uruchamia skrypt jako root, wiec ~ wskazuje /root;
  perf w tle na staly czas, skrypt jako uzytkownik.
- palec tworzy wlasne urzadzenie uinput, nie pisze do event0; demon i pomiar
  musza obejmowac nowe urzadzenia.
- evtest do pliku buforuje wyjscie i timeout je gubi; dotyk czytac surowo
  (dotyk-czytaj.py).

## Niezmierzone (wymaga czlowieka)

Czestotliwosc raportow prawdziwego dotyku (Android S10+: 120 Hz) i wrazenie
plynnosci przy prawdziwym palcu.
