### Zaokraglone karty FormCard (kirigami-addons 1.12.0)

Na waskim ekranie FormCard z `kirigami-addons` rysuje karty od krawedzi do krawedzi, bez
zaokraglen (`cardWidthRestricted` jest prawdziwe dopiero powyzej 30 jednostek siatki). Na telefonie
karta ma teraz margines 13 i promien 28 jak w One UI (lista glowna Ustawien), podswietlenie
wcisnietego wiersza zaokragla skrajne rogi tym samym promieniem, a naglowki sekcji (FormHeader) sa
wyrownane z tekstem karty, mniejsze i przygaszone. Na szerokim ekranie zachowanie bez zmian.

Od adaptacji 9 takze wiersze jak w One UI (zmierzone na zrzutach z calej aplikacji Ustawienia
One UI): poziomy margines 20, pionowy liczony z wysokosci pisma aplikacji (`FontMetrics` na
`Qt.application.font`, wspolczynnik 0,85), wiec przy 17 px tekstu wiersz ma 65 px jak w One UI,
a w aplikacjach z mniejszym pismem proporcjonalnie mniej; podtytul (opis) 0,8 rozmiaru tytulu
w `FormTextDelegate`, `FormSwitchDelegate`, `FormButtonDelegate`; podpisy sekcji 13 px, zwykla
grubosc, przygaszone, wciete do tekstu wiersza.

- `formcard-oneui.diff`: zmiany w `FormCard.qml`, `FormDelegateBackground.qml`, `FormHeader.qml`,
  `FormTextDelegate.qml`, `FormSwitchDelegate.qml`, `FormButtonDelegate.qml`,
  `private/FormCardUnits.qml` (potrzebuje `import QtQuick` dla `FontMetrics`, inaczej
  `FormCard.FormCard unavailable` w KAZDEJ aplikacji) oraz `qmldir` bez linii `prefer` (inaczej silnik QML bierze kopie wkompilowane we wtyczke
  i pliki na dysku sa ignorowane).
- Wdrozenie: pakiet adaptacji 8 i 9 (`-tools`) przekierowuje te 8 plikow w
  `/usr/lib/aarch64-linux-gnu/qt6/qml/org/kde/kirigamiaddons/formcard`, zaleznosc
  `qml6-module-org-kde-kirigamiaddons-formcard (= 1.12.0-1)`. Dotyczy wszystkich aplikacji.
- Test bez ruszania systemu: kopia modulu w `~/fc-test/org/kde/kirigamiaddons/formcard`
  i `QML_IMPORT_PATH=~/fc-test`.

Dowod: zrzuty Wi-Fi, Energii i Informacji systemowych; bledy `ProgressBar.qml` w module Energia
wystepuja tak samo z oryginalnym FormCard (52 i 48 w tym samym czasie), wiec nie pochodza z tej zmiany.
