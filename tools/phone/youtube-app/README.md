# YouTube jako aplikacja webowa (Qt WebEngine)

Firefox NIE nadaje sie na tym urzadzeniu: ma TLS w pliku wykonywalnym, ktory
koliduje z Mali/bionikiem i powoduje SIGSEGV przy kazdym dotknieciu GL
(udokumentowane w pamieci `przegladarki-gpu-na-libhybris`). Dziala za to
**Qt WebEngine** (ten sam silnik, co okno DeepSeek Harness), uruchamiany przez
`qmlscene` z renderowaniem programowym.

## Pliki (instalowane do ~/.local usera)

- `youtube.qml` -> `~/.local/share/youtube-app/youtube.qml` - okno Qt WebEngine:
  mobilny user-agent (serwis m.youtube.com), trwaly profil (logowanie zostaje),
  pelny ekran na wideo.
- `youtube-app` -> `~/.local/bin/youtube-app` - wrapper. Kluczowe srodowisko:
  - `QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu --disable-gpu-compositing"` -
    kompozytor GPU Chromium nie dziala na libhybris (czarne okno), render CPU.
  - `QT_WAYLAND_FORCE_NONBLOCKING_SWAP_SUPPORT=1` - bez tego event loop Qt
    ZAMARZA na wayfire ("Non-blocking swap buffers not supported") i strona sie
    nie laduje (0 polaczen). Z nim m.youtube.com laduje sie (LOAD status=2).
  - app_id okna = `org.qt-project.qmlscene` (qmlscene go narzuca; dowiazanie
    o innej nazwie tego nie zmienia).
- `youtube.desktop` -> `~/.local/share/applications/youtube.desktop` - wpis w
  launcherze (ikona YouTube).
- `youtube.png` -> `~/.local/share/icons/hicolor/256x256/apps/youtube.png` - ikona.

## Instalacja na telefonie

    scp/ssh pliki do powyzszych sciezek, chmod +x youtube-app,
    update-desktop-database ~/.local/share/applications

## Ograniczenia (uczciwie)

- Wideo dekoduje CPU (--disable-gpu), wiec HD bywa ciezkie; nizsze
  rozdzielczosci chodza lepiej.
- Qt WebEngine (Debian) moze nie miec kodekow H.264 (proprietary); VP9/VP8/Opus
  dzialaja, a YouTube serwuje glownie VP9, wiec wiekszosc filmow gra.
- Zrzut ekranu narzedziem wayfire NIE pokazuje tresci WebEngine (renderuje sie
  do subpowierzchni Wayland), weryfikacja wzrokowo na panelu.
