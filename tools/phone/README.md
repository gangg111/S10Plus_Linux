# Filtr tok po stronie telefonu

Praca nad tym portem polega dzis w duzej czesci na czytaniu telefonu: `dmesg`,
`clk_summary`, `/proc/interrupts`, drzewo urzadzen, listy plikow. Kazde takie
wyjscie w calosci wchodzi do kontekstu modelu, a wiekszosc z niego to
powtorzenia i szum. Na PC rozwiazuje to hook, ktory przepisuje polecenia na
`tok <polecenie>`, zanim powloka je zobaczy. Po drugiej stronie kabla takiego
hooka nie ma.

Dlatego filtr siedzi **na telefonie**, w wymuszonym poleceniu klucza SSH.
Dziala bez wiedzy strony wolajacej: ktokolwiek wpisze `ssh telefon dmesg`,
dostanie wyjscie przefiltrowane, nie musi o niczym pamietac ani niczego
dopisywac.

## Co gdzie lezy

| na telefonie | co to |
|---|---|
| `~/.local/bin/tok` | statyczna binarka aarch64, musl, 817 kB, bez zaleznosci |
| `~/.local/bin/tok-ssh` | opakowanie polecen przychodzacych po SSH |
| `~/.ssh/authorized_keys` | klucz roboczy z `command=`, ponizej klucz ratunkowy |

| w repozytorium | co to |
|---|---|
| `tools/phone/tok-ssh` | zrodlo opakowania |
| `tools/phone/wszyj-tok-w-obraz.sh` | wklada komplet do obrazu pmOS |

## Jak zbudowac binarke

Zrodlo toka to jeden plik `tok.rs` budowany golym `rustc`, wiec cala budowa dla
telefonu to jedno polecenie ze strony Windows. Cel `*-musl` linkuje sie sam
(wlasna kopia libc, `rust-lld`), wiec obcy linker nie jest potrzebny.

```bash
rustup target add aarch64-unknown-linux-musl
rustc -O --target aarch64-unknown-linux-musl -C target-feature=+crt-static \
      -C linker=rust-lld -C linker-flavor=ld.lld -C strip=symbols \
      tok.rs -o tok-aarch64
```

Bez `-C linker=rust-lld` budowa pada, bo `cc` na tej maszynie wskazuje na gcc
dla x86_64 i nie umie zlinkowac aarch64 (`unrecognized option '--eh-frame-hdr'`).

**Dlaczego musl, a nie glibc.** Nie chodzi o wydajnosc, tylko o to, ze wynik ma
byc jednym plikiem, ktory dziala wszedzie: telefon ma postmarketOS na musl, a
statyczny glibc jest w tej roli krucha droga (NSS, lokalizacja). Statyczna
binarka musl uruchomi sie takze na systemie z glibc, wiec ewentualna zmiana
dystrybucji jej nie unieważni.

## Trzy drogi ominiecia filtra

1. **Sesja interaktywna** (`ssh telefon` bez polecenia) dostaje zwykla powloke.
2. **Przedrostek `TOK_RAW=1`** daje wyjscie surowe co do bajtu:
   `ssh telefon 'TOK_RAW=1 dmesg'`. Uzywac tam, gdzie liczy sie dokladnosc:
   sumy kontrolne, zrzuty rejestrow, porownania bajt w bajt.
3. **Klucz ratunkowy** (`s10-ratunek`) nie ma wymuszonego polecenia. Sluzy do
   przesylania plikow i za wyjscie awaryjne.

Gdyby toka zabraklo albo nie dalo sie go uruchomic, opakowanie puszcza
polecenie surowo. Filtr, ktory potrafi ZABLOKOWAC dostep do maszyny, bylby
lekarstwem gorszym od choroby.

## Przesylanie plikow

Ten telefon **nie ma binarki `scp`**: sshd obsluguje przesylanie wbudowanym
`internal-sftp`, a wymuszone polecenie przechwytuje takze zadania podsystemu
i nie ma jak oddac sterowania z powrotem do wnetrza sshd. Sa dwie drogi, obie
sprawdzone:

```bash
ssh -i s10 telefon 'cat > /sciezka/docelowa' < plik.lokalny   # przez filtr
scp -i s10-ratunek plik.lokalny telefon:/sciezka              # kluczem ratunkowym
```

Strumien binarny przez filtr przechodzi **bez zmiany ani jednego bajtu**:
200 000 losowych bajtow, ta sama suma sha256 po obu stronach.

## Co zostalo zmierzone 21.09.2026

| proba | wynik |
|---|---|
| `dmesg` przez filtr | 481 wierszy surowych -> ogon z zwinieciem powtorzen |
| to samo drugi raz | jeden wiersz, `unchanged since last run` |
| `TOK_RAW=1 dmesg` | pelne 481 wierszy |
| potok i cudzyslowy | przechodza, wynik poprawny |
| kod wyjscia | `exit 7` wraca jako 7 |
| brak binarki toka | polecenie leci surowo, dostep zachowany |
| strumien binarny 200 kB | suma sha256 identyczna |
| lacznie po 12 poleceniach | 19 185 -> 2 747 tokenow, **85,7 % mniej** |

## Uwaga diagnostyczna

Dedup sesji sprawia, ze powtorzone polecenie o niezmienionym wyjsciu wraca jako
`unchanged since last run`. To jest zamierzone i to wlasnie oszczedza najwiecej,
ale przy diagnostyce trzeba pamietac, ze **brak wyjscia znaczy brak zmiany**,
a nie brak danych. Pelne wyjscie ostatniego przebiegu zawsze da sie odzyskac:
`ssh telefon 'TOK_RAW=1 ~/.local/bin/tok full'`.
