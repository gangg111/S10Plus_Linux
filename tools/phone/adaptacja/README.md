### Pakiet adaptacji Droidiana dla Galaxy S10+ (beyond2lte)

Wszystko, czego port potrzebuje poza jadrem, zamiast plikow wgranych recznie.
Budowa natywnie na telefonie: `sh buduj.sh` (paczki w `~/src/`), instalacja
`sudo dpkg -i ../adaptation-samsung-beyond2lte*_2_*.deb`.

| Paczka | Zawartosc |
|---|---|
| `adaptation-samsung-beyond2lte` | zaleznosci: jadro, `-configs`, `-tools` |
| `adaptation-samsung-beyond2lte-configs` | reguly udev z `ueventd.rc` (bez nich nie ma ekranu Plasmy), regula wibratora, opcje `module-droid-card` dla HAL dzwieku Samsunga (bez nich pulseaudio pada), motyw plymouth `debian-s10`, automatyczna jasnosc, blokada wygaszania od aplikacji (`blokada-wygaszania.py`: `org.freedesktop.ScreenSaver` i blokady powerdevil do wayfire), `dotyk-boost.service`, warunek Waylanda dla jednostki portalu KDE |
| `adaptation-samsung-beyond2lte-tools` (arm64) | `plasma_session` i `ksplashqml` z latkami Droidiana KDE_NO_KWIN (przekierowanie dpkg-divert paczki), wtyczka wayfire `podglad`, `wayfire.ini` S10+ (przekierowanie domyslnego z plasma-mobile-wf), `plasma-settings` w stylu One UI z polskimi napisami i kategoriami (przekierowania, patrz tools/phone/plasma-settings-oneui) |

Pochodzenie binarek w `tools/` (sumy sha256, 16 znakow):
- `plasma_session` `a2bd6cb80df9b2a8`, `ksplashqml` `2b0bfd933c4d92a6`: plasma-workspace 4:6.7.4-1
  z latkami droidian/plasma-workspace 6f6a983e d9eca8c6 638376b9 2d3627ad, budowane w
  `~/droidian/plasma-workspace` (WSL) 29.09.2026.
- `libpodglad.so` `47c7bfc1acdc9de3`: `tools/phone/podglad/podglad.cpp`, budowa `podglad/buduj.sh`.
- `wayfire.ini` `3f162257c51d1c58`: konfiguracja sesji z telefonu (wtyczka podglad, gesty przelacznika, skala 3, `[grid] type = none`); `startplasmamobile-wf` kopiuje ja do `~/.config` tylko przy pierwszym starcie, wiec zmiana pliku nie dotyka istniejacych kont.
- `plasma-settings` `07204cbf6edee521`, `mobile.plasmasettings.mo` `6a8b77284bda3cbd`: `tools/phone/plasma-settings-oneui`, budowa `ps-buduj.sh`.
- FormCard (8 plikow, lista w `tools/phone/kirigami-addons-oneui`): `tools/phone/kirigami-addons-oneui`, zaokraglone karty One UI na telefonie.

Migracja z recznego stanu (wersja 1 nie niosla tych plikow): preinst usuwa recznie
dodana jednostke `dotyk-boost` i autostart, a lokalne przekierowania `plasma_session`
i `ksplashqml` zamienia na przekierowania paczki bez ruszania plikow; postinst kasuje
z `/etc/udev/rules.d` i `/usr/local/lib` tylko kopie identyczne z paczka.
