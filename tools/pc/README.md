# Trzy drogi wniesienia zmian na telefon, od najtanszej

Najwazniejsza rzecz na tej stronie: **wgranie obrazu kasuje system plikow
telefonu w calosci**. Wszystko, co na nim powstalo po ostatnim wgraniu (wlasne
pliki, logi, pomiary, cokolwiek w katalogu domowym) przepada. Do wiekszosci
zmian nie jest do niczego potrzebne.

| co zmieniam | czym | co ginie | ile trwa |
|---|---|---|---|
| klawiature (program, czcionka, usluga) | `wgraj-klawiature-po-sieci.sh` | nic | kilka sekund |
| jadro i drzewo urzadzen | `wgraj-jadro-po-sieci.sh` | nic, poprzednie jadro zostaje obok jako `vmlinuz-s10.poprzednie` | okolo minuty |
| caly system plikow (nowa baza pmOS, korzen do odtworzenia) | `fastboot flash userdata` obrazem z `tools/phone/wszyj-wszystko-w-obraz.sh` | CALY korzen telefonu | okolo 100 s plus rozruch |

Obie drogi sieciowe wymagaja tylko tego, zeby telefon odpowiadal pod
`172.16.42.1`, czyli zeby byl podlaczony kablem i wstal do systemu.

## Dlaczego obraz mimo wszystko utrzymujemy

Bo jest jedyna droga po czyms, co system plikow zniszczy, i jedyna, ktora
przenosi wszystko naraz: filtr `tok`, klucze, klawiature, firmware lacznosci,
regule sudo. Ma wlasny audyt, ktory przerywa na pierwszym braku, oraz kopie
klawiatury w initramfs, ktora odtwarza ja na KAZDYM korzeniu, takze cudzym.
Jest wiec siatka bezpieczenstwa, a nie codzienna droga.

## Kolejnosc, gdy telefon wraca po dluzszej przerwie

1. Zdjac to, czego nie da sie odtworzyc: pomiary i logi z telefonu na komputer.
   Robi to sam `wgraj-klawiature-po-sieci.sh` w pierwszym kroku (kopia katalogu
   domowego) i przerywa, gdy kopia wyjdzie pusta.
2. Dopiero potem cokolwiek podmieniac.
3. Obraz wgrywac wylacznie wtedy, gdy zmienil sie korzen, a nie gdy zmienil sie
   jeden program.

## Klucze

Klucz roboczy ma wymuszone polecenie (filtr `tok`), wiec **pliki nim nie
przejda**. Do przesylania plikow sluzy klucz ratunkowy. Stad w skryptach dwie
osobne zmienne: `KLUCZ` i `KLUCZ_PLIKI`.
