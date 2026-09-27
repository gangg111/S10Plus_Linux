# Wzorzec: klawiatura Qt uzytkownika

Te pliki NIE sa budowane w tym projekcie.  Sa tu jako **zrodlo prawdy** dla
klawiatury w C: uklad, wymiary, kolory, czasy i zachowanie klawiszy maja byc
przeniesione z nich jeden do jednego.

Pochodzenie: projekt `pmos-kbd` uzytkownika, `D:\S10Plus-pmos\Keyboard`.

| plik | co z niego bierze klawiatura w C |
|---|---|
| `Layouts.qml` | cztery warstwy, rzedy, kolejnosc i szerokosci klawiszy, warianty pod przytrzymaniem, autopowtarzanie.  Z tego pliku GENEROWANY jest `../uklad.h` (`scripts/gen-uklad-klawiatury.py`), a bramka `scripts/check-uklad-klawiatury.py` pilnuje zgodnosci. |
| `Theme.qml` | paleta w zapisie szesnastkowym, wymiary w milimetrach, rozmiary pisma |
| `KeyButton.qml` | trzy stany tla klawisza, kropka wariantu, prog przytrzymania 0,35 s, autopowtarzanie 400 i 55 ms, zasada ReleaseWithinBounds |
| `Keyboard.qml` | wysokosci rzedow, podzial szerokosci wagami rzedu, trzy stany Shifta, wskazniki CAPS, CTRL i ALT |
| `AltPopup.qml` | dymek wariantow: rozmiar komorki, obwodka, wybor i zamykanie |

Jedna uwaga o wiernosci kopii: `Layouts.qml` jest **bajt w bajt** tym, co ma
uzytkownik.  `Keyboard.qml` w tej kopii ma dodatkowo wciecie na zakrzywione
krawedzie panelu (`Theme.safeMargin`), ktore dopisalem podczas pracy nad
klawiatura Qt; oryginal uzytkownika tego wciecia nie ma.  Reszta liczb
w obu wersjach jest taka sama.
