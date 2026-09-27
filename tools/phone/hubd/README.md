# hubd: własny demon huba czujników BCM47752

Zastępuje zamknięty `lhd` Samsunga w części potrzebnej czujnikom (żyroskop,
akcelerometr, magnetometr, ciśnienie, światło, zbliżeniowy). Wszystkie te
czujniki siedzą za mikrokontrolerem w układzie GNSS BCM47752 na SPI17.
Jądro (port `brcm_sensorhub`) daje transport i protokół SSP; demon musi
obudzić układ, wgrać mu firmware (patch) i przepychać pakiety SSP do huba.

## Co robi

1. `ESW:NOTREADY` do `/dev/bbd_control`, linia nStdby (`GPS_PWR_EN`) 0, potem 1.
2. 36 bajtów `0x80` (autobaud), synchronizacja numerów TL (SeqIdRequest).
3. GetVersion, kontrola zgodności patcha jak `CheckPatch` w lhd.
4. Patch z `/dev/bbd_patch`: 486 rekordów `F1` jako RPC `MemoryWrite` w
   pakietach RELIABLE, okno 8 KiB, powtórka po 500 ms.
5. `StartScratchApp(0x00800161)`, drugi autobaud i synchronizacja z aplikacją.
6. `ESW:READY`: SSP w jądrze startuje, rekordy z `/dev/bbd_sensor` idą do
   huba jako RPC `0x20`. Odpowiedzi `0x21` zjada jądro i oddaje SSP.

`BBD:RESET_REQ` z jądra powtarza całość. Po 3 porażkach z rzędu demon kończy
z kodem 1 i zostawia układ w czuwaniu.

## Źródła protokołu

| co | skąd |
|---|---|
| ramka TL, flagi, CRC, ucieczki | `bbd_rpc_lh.c` (jądro Samsunga) i RE lhd, `SPEC.md` rozdz. 2 |
| numery RPC | enum w `bbd_rpc_lh.c` i RE lhd, rozdz. 3 |
| kontener patcha, pole `Crc` | RE lhd, rozdz. 4 i 5 |
| maszyna stanów wgrywania | RE lhd, rozdz. 7 (`FD_*`) |
| rekord `/dev/bbd_sensor` | `bbd_send_packet` w `bbd.c`: `u16 długość` + pakiet |

Wektory z jądra, które koder i dekoder odtwarzają bajt w bajt (testy):
zapytanie `B0 00 00 02 80 03 00 00 00 01 B1 B0 01` i odpowiedź z CRC `0x43`
z `bcm_gps_regs.c`. `Crc` obu patchy z jądra wychodzi zgodny (236 i 151).

## Testy (bez telefonu)

    python -m unittest discover -s tools/phone/hubd/test
    HUBD_PATCH=<bbd_patch_beyond_r_os.txt> python -m unittest discover -s tools/phone/hubd/test

`test/emulator.py` to układ (ROM, pamięć, aplikacja z echem RPC 0x20) i
przepisany filtr jądra z `bbd_rpc_lh.c`. Z prawdziwym patchem: 441 692 B
obrazu w pamięci emulatora, rozruch także przy 5% zgubionych ramek.

## Czego nie wiadomo bez sprzętu

Czy ROM odpowiada na GetVersion od razu po autobaud, jaką wersję ROM zgłasza,
czy hub wysyła dane czujników w pakietach RELIABLE (wtedy pierwszy z nich
jądro odda demonowi, a nie SSP; licznik `rpc_0x21` to pokaże), czy
`RPC 0x20` ma iść jako RELIABLE (`--czujniki-zwykle` przełącza).
Na telefonie: `sudo python3 hubd.py --sprawdz-patch` najpierw, potem
`sudo python3 hubd.py --statystyki 10`.
