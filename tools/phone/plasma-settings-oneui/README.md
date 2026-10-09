### Ustawienia w stylu One UI (plasma-settings 26.04.0)

Przerobiony wyglad `plasma-settings` (tag `v26.04.0`, ta sama wersja co pakiet Droidiana):
duzy tytul, ktory przy przewijaniu oddaje miejsce malemu paskowi, karta konta (otwiera
modul Uzytkownicy), jedna zaokraglona karta na kategorie, kolorowe kola z bialym symbolem
Breeze, separatory wciete od tekstu, plywajaca pigulka Szukaj. Strony podkategorii z duzym
tytulem i strzalka, moduly z czarnym naglowkiem. Kolory i wymiary zmierzone na zrzucie One UI 7
(1080 px, przeliczone na 480 punktow logicznych): tlo `#010101`, karta `#171719`, separator
`#3a3a3c`, promien 28, wiersz 65, kolo 32, tekst od 88.

- `0001-One-UI-look-for-the-phone-Galaxy-S10-port.patch`: zmiany w zrodle (QML, `main.cpp`,
  CMake, polskie napisy). Logika C++ modeli bez zmian.
- `OneUiDark.colors` (z `oneui-colors.py`, na bazie BreezeDark): schemat, ktory aplikacja
  laduje tylko dla siebie (`KDE_COLOR_SCHEME_PATH` + paleta), wiec strony modulow tez sa czarne.
- `kategorie-wagi.py`: wagi kategorii najwyzszego poziomu w kolejnosci One UI (Siec 5,
  Podlaczone urzadzenia 6, Wejscie i wyjscie 8, Aplikacje 9, Wyglad 12, Dostosowywanie 14).
- `ps-buduj.sh`: budowa krzyzowa w kontenerze `pmwf-krzyz` (pelna 8 s, przyrostowa 4-6 s);
  sysroot potrzebowal jeszcze `libkf6crash-dev` (rozpakowany z paczki arm64).

Wdrozenie: pakiet adaptacji 7 (`-tools`) przekierowuje `/usr/bin/plasma-settings`, polskie
`mobile.plasmasettings.mo` i 6 plikow kategorii (oryginaly jako `*.distrib`, ktorych loader
nie czyta), `-configs` dodaje `/usr/share/color-schemes/OneUiDark.colors`. Zaleznosc
`plasma-settings (= 26.04.0-1)`, bo binarka i kategorie musza pasowac do wersji z Debiana.

Nie zrobione: karty FormCard w samych modulach rysuja sie od krawedzi do krawedzi bez
zaokraglen (tak `kirigami-addons` robi na waskim ekranie); zmiana dotknelaby wszystkich aplikacji.
