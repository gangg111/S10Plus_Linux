# DECON M1b: sterownik KMS na potoku S-Boota, 60 kl/s (24.09.2026)

Jadro #60, DTB etapu 18, Mesa 26.2.3, KWin 6.7 (Plasma Mobile). Poprzedni
krok: measurements/2026-09-24-decon-m0-m1a (odczyt potoku i jednorazowa
podmiana bufora).

## Co to jest

decon9820.c: modul out-of-tree, ktory przejmuje potok zostawiony przez
S-Boot bez modesetu (okno 5, IDMA GF0, tryb polecen DSI z TE, DSC, SYSMMU
w bypassie). Flip to zapis adresu do IDMA_IN_BASE_ADDR_Y i zadanie
aktualizacji cienia WIN(5); aktualizacja plaszczyzny czeka na zatrzask
(ramka TE), a zdarzenie flipa wysyla DRM zaraz potem (brak drm_vblank_init,
wiec no_vblank i drm_atomic_helper_fake_vblank). Tempo klatek idzie za TE.

Wersja v1 (decon9820-v1-przed-recenzja.c) przeszla recenzje trzech soczewek
i sedziego (recenzja.md): 9 potwierdzonych usterek, wszystkie poprawione
w v2 (decon9820.c), m.in. brak plane atomic_disable (skan zwolnionego
bufora), brak gaszenia panelu (latka 0100 rozpoznaje tylko wezel
simple-framebuffer; v2 wola lcd_notify_blank_all z urzadzeniem posrednim
o tym wezle), import obcego dmabuf przez SWIOTLB, modul nierozladowywalny.

## Warunek: CMA 256 MB ponizej 4 GB

Domyslne CMA to 32 MB (CONFIG_CMA_SIZE_MBYTES), a jeden bufor ekranu to
17,5 MB. Wpis 00-s10.conf dostal `cma=256M@0-4G` (kopia .przed-cma):
`cma: Reserved 256 MiB at 0x00000000aaa00000`, w wolnym oknie miedzy
secure_camera (0x96000000) a seclog_mem (0xc0000000). Rozruch czysty.
Sterownik przed przejeciem ekranu probnie alokuje 4 bufory i bez tego
odmawia.

## Uruchomienie (bez restartu)

1. `systemctl stop plasma-mobile`, `modprobe decon9820`:
   `[drm] Initialized decon9820 0.2.0 for decon9820 on minor 2`,
   `fb0: decon9820drmfb`, konsola 90x95, simpledrm usuniety, bez bledow.
2. Wzor z decon-wzor.py zapisany do /dev/fb0: uzytkownik widzi pasy
   z siatka na calym panelu. DECON skanuje bufor fbdev sterownika.
3. `systemctl start plasma-mobile`: KWin "Using Atomic Mode Setting on gpu
   /dev/dri/card2", "Skipping KMS incapable drm device node at card1",
   render na renderD128. W plaszczyznie 3 bufory AR24 1440x3040 po
   17 657 856 B (z sumami CRC panfrosta, czyli tworzone przez Mesa kmsro
   i renderonly na card2), KWin nie mapuje ich w CPU (0 mmap card2): GPU
   pisze wprost do buforow, ktore DECON skanuje. CMA: 259 832 - 191 000 =
   68 832 kB = fbcon 17 100 + 3 x 17 244 kB.

## Wynik (ab.sh: 5 x otworz/zamknij szuflade, dziennik klatek KWin)

| | simpledrm + GPU (2026-09-24-gpu) | DECON M1b |
|---|---|---|
| odstep klatek w animacji, mediana | 43-48 ms | 16,71 ms |
| odstep klatek, p90 | | 16,86-16,92 ms |
| render, mediana | | 4,6-4,7 ms |
| CPU KWin / 17 s | | 1,04-1,06 s |
| system zajety | 4-6% | 3% |

Caly dziennik sesji (klatki-decon.csv, lacznie ze startem Plasmy): 933
odstepy ponizej 200 ms, 902 (96,7%) to jedna ramka, 29 dwie, 2 dluzej.
Uzytkownik: animacja plynna, bez glicz. Przycisk zasilania gasi i zapala
panel (DPMS KWin -> crtc atomic_disable/enable -> 0x28/0x29 z latki 0100).

Bledy zadan GPU trwaja (248 do 1937 s po starcie), otwarte osobno
(measurements/2026-09-24-gpu).

## Ladowanie przy starcie

decon9820.service (w /etc/systemd/system, WantedBy=graphical.target,
Before=plasma-mobile.service) robi `modprobe decon9820`. Rozruch 28,4 s
(systemd-analyze), jednostka status=0/SUCCESS, konsola przechodzi
z simpledrm na DECON w 11,6 s (`switching to colour dummy device`, potem
`Initialized decon9820 ... on minor 2`, `fb0: decon9820drmfb`), KWin od
razu na card2 z 3 buforami. ab.sh: odstep klatek mediana 16,71 ms, p90
17,05 ms, render 4,7 ms, KWin 1,03 s CPU / 17 s. Odwrot:
`systemctl disable decon9820` i restart.

## Pulapki

- `systemctl restart plasma-mobile` NIE restartuje KWin: to usluga
  uzytkownika, przezywa, traci mastera DRM ("Atomic modeset test failed!
  Permission denied") i na ekran wraca fbcon; zabity KWin wstaje od razu
  bez nowego srodowiska. Czysto: sesja-od-nowa.sh (stop plasma-mobile,
  stop user@10000, start plasma-mobile) uruchomione przez systemd-run.
- Pobieranie pliku z telefonu przez `ssh cat` bez `TOK_RAW=1` daje
  wyjscie przefiltrowane przez tok (tu 235 B zamiast 83 457 B).

## Dalej

Wlaczenie do serii: wezel
DT i wiazanie, zegary z DT, controls_device w 0100 po wezle DECON, vblank
z przerwania DECON zamiast odpytywania zatrzasku (M2-M4 z plan-M0-M4.md).
