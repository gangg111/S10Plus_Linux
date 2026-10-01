---
name: ask-claude
description: "Zapytaj Claude (Claude Code na subskrypcji Artura, zainstalowany na tym telefonie, bez klucza API) i prowadz z nim rozmowe przez skrypt ask_claude.sh: druga opinia, recenzja planu lub kodu, red team, pomoc przy utknieciu, wiedza z pamieci Claude. Uzyj gdy user mowi: zapytaj Claude, skonsultuj z Claude, niech Claude to sprawdzi, pogadaj z Claude, co na to Claude, daj Claude do recenzji; albo gdy sam utknales po dwoch nieudanych probach, masz podjac duza decyzje (refactor, nowy modul, zmiana podejscia) albo chcesz niezaleznej recenzji wlasnego patcha przed oddaniem. NIE uzywaj do zlecania Claude zmian w plikach (ma tylko odczyt), do trywialnych pytan ani do researchu w sieci (od tego narzedzie web)."
---

# Rozmowa z Claude (telefon)

Claude to Claude Code na tym telefonie (`/usr/local/bin/claude`, sprawdzone na 2.1.285, zalogowany na subskrypcji usera). Skrypt odpala go w trybie `claude -p`, podaje pytanie przez stdin i zwraca odpowiedz. Claude dostaje TYLKO odczyt plikow (`Read`, `Grep`, `Glob`), bez powloki, bez zapisu i bez serwerow MCP: doradza i recenzuje, a zmiany wprowadzasz Ty.

## Kiedy NIE

- Chcesz, zeby Claude cos zmienil: nie moze. Popros o konkretny diff w odpowiedzi i wprowadz go sam narzedziem `edit`.
- Pytanie wymaga swiezych informacji z internetu: uzyj narzedzia `web`.
- Odpowiedz znasz albo zdobedziesz jednym `read`/`grep`: kazde pytanie zjada limit subskrypcji Claude usera.

## Procedura

1. **Zbuduj samowystarczalne pytanie.** Claude NIE widzi Twojej rozmowy z userem. Wpisz: cel, co juz sprawdziles i z jakim wynikiem, pelne sciezki plikow, pytanie zamkniete. Dluzsze pytanie zapisz do pliku narzedziem `write` i podaj `-f`. Zrobione, bo: ktos bez kontekstu rozmowy moglby na nie odpowiedziec.
2. **Wywolaj** w powloce:
   ```bash
   ~/.dsh/skills/ask-claude/ask_claude.sh -C "<katalog projektu>" -f "<plik z pytaniem>"
   ```
   Opcje: `-p "tekst"` zamiast pliku; `-C` katalog, ktory Claude moze czytac (domyslnie biezacy); `-t none` gdy pytanie nie wymaga czytania plikow (szybciej); `-s <id>` kontynuuje rozmowe; `-m` model; `-T` limit czasu w sekundach (domyslnie 600). Zrobione, bo: kod wyjscia 0 i pierwsza linia `SESSION: <uuid>`.
3. **Kontynuuj rozmowe** tym samym `-s <uuid>` i tym samym `-C`. Nowy temat = nowa sesja.
4. **Zweryfikuj, zanim uzyjesz.** Odpowiedz Claude to opinia, nie dowod. Twierdzenia o kodzie sprawdz odczytem pliku, zmiane testem. Gdy Claude i Twoja analiza sie roznia, podaj userowi obie wersje z dowodami.
5. **Pokaz userowi** krotko: o co zapytales, co Claude odpowiedzial, co przyjmujesz i dlaczego.

## Pulapki

- **Objaw:** odpowiedz ogolnikowa albo „nie wiem, o jaki plik chodzi”. **Przyczyna:** Claude nie widzi Twojej rozmowy. **Poprawka:** pelne sciezki, fragmenty logu, dokladne pytanie; `-C` na katalog projektu.
- **Objaw:** kod wyjscia 2. **Przyczyna:** duze zadanie z czytaniem wielu plikow; telefon jest wolniejszy niz PC. **Poprawka:** zawez pytanie albo podnies `-T`.
- **Objaw:** kod 1 i `BLAD (...)` o limicie lub logowaniu. **Przyczyna:** wyczerpany limit subskrypcji albo wylogowany CLI. **Poprawka:** nie ponawiaj w petli; powiedz userowi (logowanie: `claude` w terminalu telefonu).
- **Objaw:** kod 1 przy `-s`. **Przyczyna:** sesja o tym id nie istnieje w tym katalogu (inny `-C` niz przy pierwszym pytaniu). **Poprawka:** ten sam `-C` albo nowa sesja.

## Dowod ukonczenia

W odpowiedzi dla usera: identyfikator `SESSION`, cytat lub streszczenie odpowiedzi Claude oraz to, co zweryfikowales sam (plik, test, wynik komendy). Samo „Claude potwierdzil” nie jest dowodem.
