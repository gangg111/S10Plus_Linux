# Pasek stanu: napis technologii sieci (LTE / 5G / ...)

Górny pasek Plasma Mobile pokazuje sam trójkąt siły sygnału, bez tekstu
generacji sieci jak w One UI. Te dwa pliki QML dodają napis (5G / LTE / H+ /
3G / E / 2G) obok trójkąta.

## Pliki

- `SignalStrengthInfo.qml` (singleton): dodaje właściwość `technology`, czytaną
  co 5 s skryptem `/usr/lib/s10plus/modem-rat.sh` przez `P5Support.DataSource`
  (silnik `executable`). `SignalIndicator` z ModemManagera NIE wystawia RAT,
  stąd skrypt.
- `SignalStrengthIndicator.qml`: etykieta w pasku pokazuje `technology` zamiast
  nazwy operatora (ta jest pusta na tym modemie); drugi wiersz paska dalej
  używa `SignalStrengthInfo.label` z nazwą operatora, więc go nie ruszamy.

Skrypt `modem-rat.sh` jest w pakiecie adaptacji
(`usr/lib/s10plus/modem-rat.sh`, instaluje się przez `usr/lib/s10plus/*`),
więc jedyne, co wymaga buildu, to te dwa pliki QML.

## Dlaczego nie da się tego wgrać na dysk

QML powłoki jest wkompilowany w `libmobileshellplugin.so` (ścieżki `qrc:`),
podmiana `/usr/lib/.../mobileshell/*.qml` i restart `plasmashell` nie zmienia
nic na ekranie (potwierdzone 04.10.2026 logiem `qrc:` i brakiem efektu).
Zmiana musi wejść jako łatka do źródła **plasma-mobile-wf** (Droidian) i pakiet
trzeba przebudować. W źródle pliki leżą w
`components/mobileshell/qml/statusbar/` (patrz `tools/phone/pasek-stanu` nota
o `StatusBar.qml`).

## Stan weryfikacji (04.10.2026)

- Ścieżka danych sprawdzona: `modem-rat.sh` zwraca `LTE` dla użytkownika sesji
  (uid 32011), `plasma_engine_executable.so` jest, mobileshell już importuje
  `plasma5support`.
- Render napisu NIE sprawdzony na ekranie, bo wymaga przebudowy pakietu
  (qrc). Po zbudowaniu zweryfikować zrzutem paska: ma pokazać `LTE` obok
  trójkąta.
