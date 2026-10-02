### Obraz boot Droidiana bez debugu bring-upu

Jadro Droidiana (galaz `droidian` w `~/droidian/kernel/samsung/beyond2lte`, WSL) bez sondy
`s10probe`, znacznikow na obrazie S-Boota i logu na partycje cache (commit fc5c3b7ab) oraz
initramfs bez skryptu `zz-early-debug` (3 wibracje, szum na fb0, telnet roota bez hasla;
commit 7179e925d).

1. `jadro-buduj.sh` (WSL): przyrostowo na kopii `~/droidian/pidfd2`, czyli wyjsciu budowy jadra
   z partycji boot, w kontenerze build-essential z clangiem Androida 17.0-r487747c.
   Nazwa wydania podana wprost (`KERNELRELEASE=4.14.356-samsung-beyond2lte`), bez niej
   wychodzi `openela-rc1`.
2. `bez-early-debug.py <obraz> <wyjscie>`: initramfs obrazu bez skryptu, jadro bit w bit.
3. `podmien-jadro.py <obraz> <Image> <wyjscie>`: nowe jadro w obrazie, ramdysk i naglowek bez zmian.

Oba skrypty Pythona przeliczaja id naglowka v1 tak jak mkbootimg (SHA1 z jadra, ramdysku,
second, recovery_dtbo i dtb, kazdy z dlugoscia) i sprawdzaja wzor na obrazie wejsciowym.

Dowod: `System.map` nowego jadra ma o 11 symboli mniej, wszystkie `s10*`; obraz
`D:\S10Plus-droidian\boot-bez-debugu-2026-10-01.img` (sha256 `2d9f9f8c...`). Po wgraniu
`grep -c s10probe_hit /proc/kallsyms` daje 0.
