# R17: fastboot na żądanie, bez dotykania telefonu

Runda siedemnasta. Do tej pory wejście w fastboot wymagało palca na klawiszu
głośności: menu BEYOND BOOT pojawia się tylko po naciśnięciu Volume Down, bo
`bootdelay` wynosi zero. Telefon leżący przy komputerze był więc zdalnie
dostępny wyłącznie wtedy, gdy wstał do systemu. To zamykało drogę do jedynej
rzeczy, której z działającego systemu zrobić się nie da: wymiany całego obrazu
korzenia.

## Czego oczekiwaliśmy

Że wystarczy przeczytać słowo, które Linux i tak zapisuje. Jądro ma do tego
sterownik `syscon-reboot-mode`, drzewo opisuje rejestr, a polecenie
`reboot bootloader` zapisuje tam wartość i prosi o reset. Brakowało tylko
odczytu po stronie bootloadera.

## Co wnosi runda

Cztery łatki, 0025 do 0028:

1. **0025** sterownik trybu rozruchu trzymanego w kontrolerze systemowym.
   Wiązanie to dokładnie to, które Linux nazywa `syscon-reboot-mode`: węzeł
   siedzi w kontrolerze, `offset` wskazuje rejestr, a każda właściwość
   `mode-<nazwa>` podaje wartość. Klasa U-Boota robi resztę sama: dopasowuje,
   nazywa tryb w środowisku i zeruje rejestr.
2. **0026** płyta czyta ten tryb w `board_late_init` i przy `bootloader`
   przestawia `bootcmd` na fastboota.
3. **0027** brakująca funkcja `bcb_clear()`: polecenie `bcb clear` potrafi
   wyczyścić jedno pole bloku sterującego, a kod nie miał czym.
4. **0028** płyta czyta też blok sterujący z partycji `misc`, i to jest droga,
   która na tym telefonie działa.

## Dlaczego droga przez rejestr nie działa

Bo nie jesteśmy pierwsi w kolejce. Rejestr pod `0x1586080c` nazywa się u
producenta `SEC_DEBUG_PANIC_INFORM` (`sources/ub/exynos9820.dtsi:580`), a
wartości, które do niego trafiają, są poleceniami S-Boota, nie naszymi.

Zmierzone, nie założone. Po `systemctl reboot --reboot-argument=bootloader`
jądro zapisało `0x1234567d`, telefon się zresetował i pojawił się na kablu jako
`04E8:685D`, czyli **tryb Download Samsunga**. Do naszego bootloadera to słowo
nie dotarło ani razu.

To przesądza o całej piątce nazw z drzewa: `download`, `upload`, `charging`,
`recovery` i `bootloader` należą do pierwszego stopnia rozruchu. Nie ma wśród
nich takiej, którą dałoby się pożyczyć.

Sterownik z łatki 0025 zostaje mimo to: jest ogólny, drzewo ten rejestr opisuje,
a układ, którego pierwszy stopień nie zjada słowa, byłby przez niego obsłużony.

## Droga, która działa

Blok sterujący, który Android trzyma na partycji `misc`. Na tym telefonie ta
partycja ma megabajt **samych zer**, czyli nikt jej nie używa, więc i nikt nie
wejdzie nam w drogę.

Przebieg potwierdzony na sprzęcie:

1. Z systemu: `printf 'bootonce-bootloader' | dd of=/dev/sda19 conv=notrunc`.
2. Reset.
3. Na panelu widać linię naszej płyty: `The misc partition asks for:
   bootonce-bootloader`, a pod nią `Fastboot Mode`.
4. Z komputera `fastboot devices` odpowiada `R58M24H6LW`.
5. `fastboot reboot` prowadzi z powrotem do systemu w 90 sekundach, a pole
   polecenia w bloku ma 32 bajty zer. Polecenie działa raz, dokładnie jak mówi
   jego nazwa.

Pomiar w całości: `measurements/2026-09-22-tryb-rozruchu`.

## Trzy rzeczy, które wyszły przy okazji

### Bootloader wgrywa się zdalnie, bez fastboota i bez Odina

Partycja `boot` to zwykłe `sda14` (`/dev/disk/by-partlabel/boot`), więc nowy
U-Boot wchodzi przez `dd` z działającego systemu. Kontrola sumy po zapisie
musi iść z pominięciem pamięci podręcznej (`echo 3 > /proc/sys/vm/drop_caches`),
inaczej porównuje się z tym, co się przed chwilą zapisało. Kopia poprzedniej
zawartości leży w `D:\S10Plus-pmos\kopie\`.

### Wyłączanie systemu potrafi zawisnąć w pamięci masowej

`systemctl reboot` stanął na `sd 0:0:0:0: [sda] Synchronizing SCSI cache` i nie
ruszył przez 25 minut: jądro żyło, userspace był już zabity, resetu nie było.
Zdarzyło się po serii zapisów przez `dd`; restart bez takich zapisów przeszedł.
Obejście: `sysctl -w kernel.sysrq=1`, `sync`, a potem `echo s` i `echo b` do
`/proc/sysrq-trigger`, co omija `device_shutdown()` razem z tym poleceniem. Po
takim resecie ext4 wstał bez odtwarzania dziennika. Pozycja do zbadania osobno.

### Ciepły reset nie odświeża magistrali USB

Po resecie bez odłączenia kabla telefon **jest** w fastboocie, ale komputer go
nie widzi, bo host nie zauważył ponownego podłączenia. Wystarczy wypiąć i wpiąć
kabel. Przy resecie przyciskami to nie występuje.
