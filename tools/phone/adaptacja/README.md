### Pakiet adaptacji Droidiana dla Galaxy S10+ (beyond2lte)

Wszystko, czego port potrzebuje poza jadrem, zamiast plikow wgranych recznie.
Budowa natywnie na telefonie: `sh buduj.sh` (paczki w `~/src/`), instalacja
`sudo dpkg -i ../adaptation-samsung-beyond2lte*_2_*.deb`.

| Paczka | Zawartosc |
|---|---|
| `adaptation-samsung-beyond2lte` | zaleznosci: jadro, `-configs`, `-tools` |
| `adaptation-samsung-beyond2lte-configs` | reguly udev z `ueventd.rc` (bez nich nie ma ekranu Plasmy), regula wibratora, opcje `module-droid-card` dla HAL dzwieku Samsunga (bez nich pulseaudio pada), motyw plymouth `debian-s10`, automatyczna jasnosc, `dotyk-boost.service`, warunek Waylanda dla jednostki portalu KDE |
| `adaptation-samsung-beyond2lte-tools` (arm64) | `plasma_session` i `ksplashqml` z latkami Droidiana KDE_NO_KWIN (przekierowanie dpkg-divert paczki), wtyczka wayfire `podglad` |

Pochodzenie binarek w `tools/` (sumy sha256, 16 znakow):
- `plasma_session` `a2bd6cb80df9b2a8`, `ksplashqml` `2b0bfd933c4d92a6`: plasma-workspace 4:6.7.4-1
  z latkami droidian/plasma-workspace 6f6a983e d9eca8c6 638376b9 2d3627ad, budowane w
  `~/droidian/plasma-workspace` (WSL) 29.09.2026.
- `libpodglad.so` `e94aa52759acb92b`: `tools/phone/podglad/podglad.cpp`, budowa `podglad/buduj.sh`.

Migracja z recznego stanu (wersja 1 nie niosla tych plikow): preinst usuwa recznie
dodana jednostke `dotyk-boost` i autostart, a lokalne przekierowania `plasma_session`
i `ksplashqml` zamienia na przekierowania paczki bez ruszania plikow; postinst kasuje
z `/etc/udev/rules.d` i `/usr/local/lib` tylko kopie identyczne z paczka.
