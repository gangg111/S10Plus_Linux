#!/usr/bin/env python3
"""hubd: wlasny demon huba czujnikow i GNSS BCM47752 (Galaxy S10+) w miejsce lhd.

Robi to, co zamkniety lhd Samsunga robi dla czujnikow:
  1. zeruje uklad linia nStdby (GPS_PWR_EN), wiec startuje on z ROM,
  2. autobaud i synchronizacja numerow warstwy transportowej (TL),
  3. GetVersion i kontrola zgodnosci patcha (CheckPatch z lhd),
  4. wgranie patcha z /dev/bbd_patch jako RPC MemoryWrite w pakietach RELIABLE,
  5. StartScratchApp, druga synchronizacja, tym razem z aplikacja, GetVersion,
  6. ESW:READY do /dev/bbd_control, potem most /dev/bbd_sensor -> RPC 0x20.
Pakiety huba z danymi czujnikow (RPC 0x21) zjada jadro (bbd_rpc_lh.c) i nie
dochodza tutaj; dochodzi reszta oraz powtorki pakietow RELIABLE, ktore jadro
przepuszcza i ktore trzeba potwierdzic.

Protokol odtworzony z lhd i z otwartego kodu jadra opisuje README.md obok.
Kazda liczba ponizej ma tam zrodlo.
"""
import argparse
import collections
import os
import re
import select
import signal
import struct
import sys
import time

# ---------------------------------------------------------------- warstwa TL

ESC, SOP, EOP = 0xB0, 0x00, 0x01
XON, XOFF = 0x11, 0x13
ZAMIANY = {ESC: 0x03, XON: 0x04, XOFF: 0x05}
ODWROTNE = {v: k for k, v in ZAMIANY.items()}

F_ACK = 0x001
F_RELIABLE = 0x002
F_RELIABLE_ACK = 0x004
F_RELIABLE_NACK = 0x008
F_MSG_LOST = 0x010
F_MSG_GARBAGE = 0x020
F_SIZE_EXT = 0x040
F_EXT = 0x080
F_INTERNAL = 0x100
F_IGNORE_SEQID = 0x200
ZNANE_FLAGI = 0x3FF

MAKS_LADUNEK = 0x400            # lhd: ladunek pakietu i transakcja RPC
MAKS_RAMKA = 2048 + 14          # bbd_rpc_lh.c: MAX_INCOMING_PACKET_SIZE + naglowek


def _tabela_crc(wielomian=0x4D):
    t = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = ((c << 1) ^ wielomian) & 0xFF if c & 0x80 else (c << 1) & 0xFF
        t.append(c)
    return bytes(t)


TABELA_CRC = _tabela_crc()
# pierwszy wiersz crc_table[] z bbd_rpc_lh.c, ta sama tablica siedzi w lhd
assert TABELA_CRC[:16] == bytes.fromhex('004d9ad77934e3aef2bf68258bc6115c')


def crc_tl(dane):
    """CRC-8 ramki: od bajtu rozmiaru do konca ladunku, polowki zamienione."""
    s = 0
    for b in dane:
        s = TABELA_CRC[s ^ b]
    return ((s & 0x0F) << 4) | (s >> 4)


class Ramka:
    __slots__ = ('seq', 'flagi', 'detale', 'ladunek', 'crc')

    def __init__(self, seq, flagi, detale, ladunek, crc):
        self.seq, self.flagi, self.detale = seq, flagi, detale
        self.ladunek, self.crc = ladunek, crc

    def __repr__(self):
        return 'Ramka(seq=%d flagi=0x%03x detale=%s ladunek=%s)' % (
            self.seq, self.flagi, {hex(k): v for k, v in self.detale.items()},
            self.ladunek[:24].hex())


def zbuduj_ramke(seq, flagi, ladunek=b'', detale=None):
    """Ramka TL gotowa do wyslania: B0 00, pola z ucieczkami, B0 01.

    Kolejnosc jak w TransportLayer::BuildAndSendPacket lhd: SeqId, mlodszy
    bajt rozmiaru, mlodszy bajt flag, po bajcie detalu na kazda ustawiona
    flage od bitu 0 w gore, ladunek, CRC.  SIZE_EXT i EXT licza sie same."""
    detale = detale or {}
    n = len(ladunek)
    if n > MAKS_LADUNEK:
        raise ValueError('ladunek %d B ponad %d' % (n, MAKS_LADUNEK))
    flagi &= ~(F_SIZE_EXT | F_EXT)
    if n > 0xFF:
        flagi |= F_SIZE_EXT
    if flagi > 0xFF:
        flagi |= F_EXT
    tresc = bytearray((n & 0xFF, flagi & 0xFF))
    for bit in range(16):
        maska = 1 << bit
        if not flagi & maska:
            continue
        if maska == F_SIZE_EXT:
            tresc.append(n >> 8)
        elif maska == F_EXT:
            tresc.append(flagi >> 8)
        else:
            tresc.append(detale.get(maska, 0) & 0xFF)
    tresc += ladunek
    surowe = bytes((seq & 0xFF,)) + bytes(tresc) + bytes((crc_tl(tresc),))
    wyj = bytearray((ESC, SOP))
    for b in surowe:
        if b in ZAMIANY:
            wyj += bytes((ESC, ZAMIANY[b]))
        else:
            wyj.append(b)
    wyj += bytes((ESC, EOP))
    return bytes(wyj)


def rozbierz(m):
    """Tresc ramki bez ucieczek -> Ramka albo None.  Te same kontrole co
    TransportLayer_PacketReceived w bbd_rpc_lh.c: CRC, znane flagi, rozmiar."""
    if len(m) < 4 or crc_tl(m[1:-1]) != m[-1]:
        return None
    seq, rozmiar, zostalo = m[0], m[1], m[2]
    wszystkie = zostalo
    i, reszta = 3, len(m) - 4
    detale = {}
    bit = 0
    while bit < 16 and zostalo and reszta > 0:
        maska = 1 << bit
        bit += 1
        if not zostalo & maska:
            continue
        zostalo &= ~maska
        d = m[i]
        i += 1
        reszta -= 1
        if maska == F_SIZE_EXT:
            rozmiar |= d << 8
        elif maska == F_EXT:
            zostalo |= d << 8
            wszystkie |= d << 8
        elif maska & ZNANE_FLAGI:
            detale[maska] = d
        else:
            return None
    if zostalo or rozmiar != reszta:
        return None
    return Ramka(seq, wszystkie & ~(F_SIZE_EXT | F_EXT), detale,
                 bytes(m[i:i + reszta]), m[-1])


class Dekoder:
    """Strumien bajtow -> ramki; maszyna stanow bbd_parse_asic_data."""

    def __init__(self):
        self.stan = 0
        self.bufor = bytearray()
        self.smieci = 0
        self.zle = 0

    def karm(self, dane):
        wynik = []
        for b in dane:
            if b == XON or b == XOFF:
                continue
            if self.stan == 0:                  # czeka na ESC
                if b == ESC:
                    self.stan = 1
                else:
                    self.smieci += 1
            elif self.stan == 1:                # czeka na SOP
                if b == SOP:
                    self.stan = 2
                    self.bufor = bytearray()
                elif b != ESC:
                    self.stan = 0
            elif self.stan == 2:                # tresc
                if b == ESC:
                    self.stan = 3
                elif len(self.bufor) < MAKS_RAMKA:
                    self.bufor.append(b)
                else:
                    self.stan = 0
            else:                               # po ESC w tresci
                if b == EOP:
                    r = rozbierz(bytes(self.bufor))
                    if r is None:
                        self.zle += 1
                    else:
                        wynik.append(r)
                    self.stan = 0
                elif b in ODWROTNE:
                    self.bufor.append(ODWROTNE[b])
                    self.stan = 2
                elif b == SOP:
                    self.bufor = bytearray()
                    self.stan = 2
                elif b == ESC:
                    self.stan = 1
                else:
                    self.stan = 0
        return wynik


# ----------------------------------------------------------------------- RPC

RPC_GET_VERSION = 0x00
RPC_VERSION_RESPONSE = 0x03
RPC_MEMORY_WRITE = 0x05
RPC_MEMORY_MASKED_WRITE = 0x06
RPC_RESET = 0x1A
RPC_SENSOR_REQUEST = 0x20
RPC_SENSOR_RESPONSE = 0x21
RPC_START_SCRATCH_APP = 0x2E
RPC_MEMORY_CRC8 = 0x31
RPC_SERVICE_START = 0x37


def _liczba_rpc(v):
    if v < 0x80:
        return bytes((v,))
    if v >= 0x8000:
        raise ValueError(v)
    return bytes((0x80 | (v >> 8), v & 0xFF))


def koduj_rpc(lista):
    wyj = bytearray()
    for ident, dane in lista:
        wyj += _liczba_rpc(ident) + _liczba_rpc(len(dane)) + dane
    return bytes(wyj)


def dekoduj_rpc(dane):
    """Ladunek pakietu -> [(id, dane)] albo None, gdy dlugosci sie nie domykaja
    (BbdBridge_CheckPacketSanity)."""
    lista, i, n = [], 0, len(dane)
    while i < n:
        ident = dane[i]
        i += 1
        if ident & 0x80:
            if i >= n:
                return None
            ident = ((ident & 0x7F) << 8) | dane[i]
            i += 1
        if i >= n:
            return None
        dl = dane[i]
        i += 1
        if dl & 0x80:
            if i >= n:
                return None
            dl = ((dl & 0x7F) << 8) | dane[i]
            i += 1
        if i + dl > n:
            return None
        lista.append((ident, bytes(dane[i:i + dl])))
        i += dl
    return lista


# -------------------------------------------------------- sesja transportowa

class Transport:
    """Numeracja, potwierdzenia, powtorki RELIABLE i synchronizacja numerow.

    Czasy jak TransportLayer::Tick w lhd: powtorka RELIABLE po 500 ms, po 10
    probach blad lacza; SeqIdRequest co 100 ms, po 6 probach porazka.  Okno
    RELIABLE: lhd wstrzymuje wgrywanie, gdy wolne miejsce spada ponizej
    0x800 z 0x2800 bajtow."""

    POWTORKA = 0.5
    MAKS_PROB = 10
    SYNC_CO = 0.1
    SYNC_PROB = 6
    OKNO = 0x2800 - 0x800
    MAKS_W_LOCIE = 150

    def __init__(self, pisz, zegar, log):
        self.pisz, self.zegar, self.log = pisz, zegar, log
        self.na_blad = None
        self.licznik_sync = 0
        self.stat = collections.Counter()
        self.wyzeruj()

    def wyzeruj(self):
        self.tx_seq = 0
        self.tx_rel = 0
        self.w_locie = collections.OrderedDict()    # numer -> [ladunek, czas, proby]
        self.rx_seq = None
        self.rx_rel = None
        self.rx_rel_klucz = None
        self.winny_ack = False
        self.sync = None

    # -- nadawanie

    def _nadaj(self, flagi, ladunek=b'', detale=None, bez_ack=False):
        detale = dict(detale or {})
        if not bez_ack and self.winny_ack and self.rx_seq is not None:
            flagi |= F_ACK
            detale[F_ACK] = self.rx_seq
        if flagi & F_ACK:
            self.winny_ack = False
        ramka = zbuduj_ramke(self.tx_seq, flagi, ladunek, detale)
        self.tx_seq = (self.tx_seq + 1) & 0xFF
        self.stat['nadane'] += 1
        self.pisz(ramka)

    def _nadaj_rel(self, nr, ladunek):
        # Powtorka musi byc bajt w bajt ta sama poza SeqId: odbiorca rozpoznaje
        # duplikat po numerze RELIABLE, CRC i dlugosci, a CRC obejmuje flagi
        # i detale.  Dlatego zadnego doklejania ACK do pakietow RELIABLE.
        ramka = zbuduj_ramke(self.tx_seq, F_RELIABLE, ladunek, {F_RELIABLE: nr})
        self.tx_seq = (self.tx_seq + 1) & 0xFF
        self.stat['nadane'] += 1
        self.pisz(ramka)

    def wyslij(self, ladunek, niezawodnie=False):
        if not niezawodnie:
            self._nadaj(0, ladunek)
            return None
        nr = self.tx_rel
        self.tx_rel = (nr + 1) & 0xFF
        self.w_locie[nr] = [ladunek, self.zegar(), 0]
        self.stat['reliable'] += 1
        self._nadaj_rel(nr, ladunek)
        return nr

    def bajty_w_locie(self):
        return sum(len(w[0]) for w in self.w_locie.values())

    def zmiesci(self, n):
        return (len(self.w_locie) < self.MAKS_W_LOCIE and
                self.bajty_w_locie() + n <= self.OKNO)

    # -- odbior

    def _potwierdzone(self, nr):
        """RELIABLE_ACK jest skumulowane: zwalnia wszystko do nr wlacznie."""
        if nr not in self.w_locie:
            return
        while self.w_locie:
            k, _ = self.w_locie.popitem(last=False)
            self.stat['potwierdzone'] += 1
            if k == nr:
                break

    def odbierz(self, r):
        """Zwraca ladunek RPC do przetworzenia albo None."""
        self.stat['odebrane'] += 1
        if not r.flagi & F_IGNORE_SEQID and self.rx_seq is not None:
            if r.seq != (self.rx_seq + 1) & 0xFF:
                # jadro zjada pakiety z RPC 0x21, wiec przeskoki sa normalne
                self.stat['przeskok_seq'] += 1
        self.rx_seq = r.seq
        if r.flagi & F_RELIABLE_ACK:
            self._potwierdzone(r.detale[F_RELIABLE_ACK])
        if r.flagi & F_RELIABLE_NACK:
            # detal to ostatni numer przyjety u odbiorcy; reszte wyslac od razu
            self.stat['nack'] += 1
            self._potwierdzone(r.detale[F_RELIABLE_NACK])
            for w in self.w_locie.values():
                w[1] = -1e9
        nowy = len(r.ladunek) > 0
        if r.flagi & F_RELIABLE:
            nr = r.detale[F_RELIABLE]
            klucz = (nr, r.crc, len(r.ladunek))
            if klucz == self.rx_rel_klucz:
                nowy = False
                self.stat['duplikat'] += 1
            else:
                # Bez sprawdzania ciaglosci numerow: pierwszy egzemplarz
                # pakietu z danymi czujnikow zjada jadro, do nas trafia
                # dopiero powtorka.  NACK za luke zablokowalby hub.
                self.rx_rel_klucz = klucz
                self.rx_rel = nr
            self._nadaj(F_ACK | F_RELIABLE_ACK, b'',
                        {F_ACK: r.seq, F_RELIABLE_ACK: nr}, bez_ack=True)
        elif nowy:
            self.winny_ack = True
        if r.flagi & F_INTERNAL:
            if nowy:
                self._wewnetrzny(r.seq, r.ladunek)
            return None
        return r.ladunek if nowy else None

    def _wewnetrzny(self, seq, d):
        if d[0] == 0 and len(d) == 2:
            # SeqIdRequest z drugiej strony; odpowiedz jak lhd 0x3a144
            seq_odp = self.tx_seq
            ost_rel = 0xFF if self.rx_rel is None else self.rx_rel
            odp = bytes((1, d[1], seq, 0, ost_rel, seq_odp, self.tx_rel,
                         (self.tx_rel - 1) & 0xFF))
            self._nadaj(F_INTERNAL, odp, bez_ack=True)
            self.stat['sync_od_ukladu'] += 1
        elif d[0] == 1 and len(d) == 8:
            if self.sync is None or d[1] != self.licznik_sync:
                self.stat['sync_obca'] += 1
                return
            self.tx_seq = (d[2] + 1) & 0xFF
            self.tx_rel = (d[4] + 1) & 0xFF
            self.rx_seq = d[5]
            self.rx_rel = (d[6] - 1) & 0xFF
            self.rx_rel_klucz = None
            koniec = self.sync['koniec']
            self.sync = None
            koniec(True)
        else:
            self.stat['wewnetrzny_%d' % d[0]] += 1

    # -- synchronizacja i czas

    def synchronizuj(self, koniec):
        self.w_locie.clear()
        self.licznik_sync = (self.licznik_sync + 1) & 0xFF
        self.sync = {'proby': 0, 'termin': 0.0, 'koniec': koniec}
        self._zadanie_sync()

    def _zadanie_sync(self):
        self.sync['proby'] += 1
        self.sync['termin'] = self.zegar() + self.SYNC_CO
        # dokladnie jak StartRemoteSync: INTERNAL|IGNORE_SEQID, ladunek [0, licznik]
        self._nadaj(F_INTERNAL | F_IGNORE_SEQID, bytes((0, self.licznik_sync)),
                    bez_ack=True)

    def tick(self, teraz):
        if self.sync is not None and teraz >= self.sync['termin']:
            if self.sync['proby'] >= self.SYNC_PROB:
                koniec = self.sync['koniec']
                self.sync = None
                koniec(False)
            else:
                self._zadanie_sync()
        for nr, w in list(self.w_locie.items()):
            if teraz - w[1] < self.POWTORKA:
                continue
            if w[2] >= self.MAKS_PROB:
                self.log('TL: %d powtorek pakietu RELIABLE %d bez potwierdzenia'
                         % (w[2], nr))
                self.w_locie.clear()
                if self.na_blad:
                    self.na_blad()
                return
            w[1], w[2] = teraz, w[2] + 1
            self.stat['powtorki'] += 1
            self._nadaj_rel(nr, w[0])

    def termin(self):
        t = [w[1] + self.POWTORKA for w in self.w_locie.values()]
        if self.sync is not None:
            t.append(self.sync['termin'])
        return min(t) if t else None


# --------------------------------------------------------------------- patch

class BladPatcha(Exception):
    pass


def _liczba(s):
    return int(s, 16) if s.lower().startswith('0x') else int(s)


class Patch:
    """Plik tekstowy patcha (<Klucz=wartosc>, Blob w hex) z /dev/bbd_patch.

    Blob to strumien rekordow [kod][u16 dlugosc][ladunek] (PatchEngine lhd),
    kody 0xF0..0xF5, dlugosc ponizej 0x3B7."""

    def __init__(self, tekst):
        pola = {k.decode(): v.decode('ascii', 'replace')
                for k, v in re.findall(rb'<(\w+)=([^>]*)>', tekst)}
        if 'Blob' not in pola:
            raise BladPatcha('brak pola Blob')
        self.blob = bytes.fromhex(re.sub(r'\s', '', pola.pop('Blob')))
        self.pola = pola
        try:
            self.asic = int(pola['AsicVersion'], 16)
            self.poziom = _liczba(pola['PatchLevel'])
            self.adres = int(pola['PatchAddress'], 16)
            self.typ = pola['Type'][0]
            self.crc_naglowka = _liczba(pola['Crc'])
            dl = _liczba(pola['BlobLength'])
        except (KeyError, ValueError, IndexError) as e:
            raise BladPatcha('naglowek: %s' % e)
        if dl != len(self.blob):
            raise BladPatcha('BlobLength %d, a blob ma %d B' % (dl, len(self.blob)))
        if self.crc() != self.crc_naglowka:
            raise BladPatcha('Crc naglowka %d, wyliczone %d'
                             % (self.crc_naglowka, self.crc()))
        self.rekordy = list(self._rekordy())

    def crc(self):
        """PatchReader::GetBlob: 7 slow u32, CustomerVersion i Name po 32 B, blob."""
        p = self.pola
        slowa = (len(self.blob), self.asic, _liczba(p['ChangeList']) & 0xFFFFFFFF,
                 self.poziom, _liczba(p['PostPatchLevel']), ord(self.typ), self.adres)
        d = b''.join(struct.pack('<I', w) for w in slowa)
        if 'CustomerVersion' in p:
            d += p['CustomerVersion'].encode()[:32].ljust(32, b'\0')
        d += p['Name'].encode()[:32].ljust(32, b'\0')
        s = 0
        for b in d + self.blob:
            s = TABELA_CRC[s ^ b]
        return s

    def _rekordy(self):
        b, i = self.blob, 0
        while i < len(b):
            if i + 3 > len(b):
                raise BladPatcha('uciety rekord na %d' % i)
            kod = b[i]
            n = struct.unpack_from('<H', b, i + 1)[0]
            if not 0xF0 <= kod <= 0xF5 or n >= 0x3B7 or i + 3 + n > len(b):
                raise BladPatcha('zly rekord 0x%02x/%d na %d' % (kod, n, i))
            yield kod, b[i + 3:i + 3 + n]
            i += 3 + n

    def rpc_wgrywania(self):
        """Rekordy -> RPC, jak IPatchEngineCb lhd.  Bez F3 (suma 32-bit):
        jej parametry RPC sa tylko domniemane, a nasze patche jej nie maja."""
        for kod, d in self.rekordy:
            if kod == 0xF1:
                adres = struct.unpack_from('<I', d)[0]
                yield RPC_MEMORY_WRITE, struct.pack('<IH', adres, len(d) - 4) + d[4:]
            elif kod == 0xF0:
                yield RPC_MEMORY_MASKED_WRITE, d[:12]
            elif kod == 0xF2:
                yield RPC_MEMORY_CRC8, d[:8]          # bajt CRC lhd pomija
            elif kod == 0xF4:
                yield RPC_SERVICE_START, d.ljust(20, b'\0')
            elif kod == 0xF5:
                continue                              # MaskedVerify: lhd nic nie wysyla
            else:
                raise BladPatcha('rekord 0x%02x nieobslugiwany' % kod)

    def obraz(self):
        """Obszary pamieci po wgraniu: {adres: bajty} (tylko F1)."""
        obszary = {}
        for kod, d in self.rekordy:
            if kod == 0xF1:
                obszary[struct.unpack_from('<I', d)[0]] = d[4:]
        return obszary


def sprawdz_zgodnosc(patch, asic, rom, poziom):
    """CheckPatch lhd: lista niespelnionych warunkow (pusta = zgodny)."""
    bledy = []
    rodzina = (asic & 0xFFFFFF) == 0x4775B0
    if not (asic == patch.asic or (rodzina and patch.asic == 0x4775B0)):
        bledy.append('asic 0x%08x, patch dla 0x%08x' % (asic, patch.asic))
    if rodzina and (asic >> 24) not in (0, 3, 4, 5, 7):
        bledy.append('nieznana rewizja ROM 0x%02x' % (asic >> 24))
    if poziom != patch.poziom:
        bledy.append('uklad ma patch poziomu %d, a ten wymaga %d' % (poziom, patch.poziom))
    if not patch.blob:
        bledy.append('pusty blob')
    return bledy


# ------------------------------------------------------------------------ hub

class Hub:
    """Maszyna stanow wgrywania (FD_* z lhd) i most czujnikow.

    io musi miec: pisz_tty(bytes), steruj(str), nstdby(int)."""

    AUTOBAUD = bytes((0x80,)) * 36      # lhd, .rodata 0x8114
    RESET_NISKO = 0.05
    PO_WLACZENIU = 0.05
    PO_AUTOBAUD = 0.01                  # LheAutoBaudDelayMS=10
    PO_STARCIE_APLIKACJI = 0.02
    WERSJA_CO = 0.25
    WERSJA_PROB = 5
    AUTOBAUD_PROB = 5
    MAKS_RESETOW = 3                    # LheMaxMcuResetTries=3

    def __init__(self, io, patch, zegar=time.monotonic, log=None,
                 czujniki_niezawodnie=True):
        self.io, self.patch, self.zegar = io, patch, zegar
        self.log = log or (lambda s: None)
        self.czujniki_niezawodnie = czujniki_niezawodnie
        self.tl = Transport(self._pisz, zegar, self.log)
        self.tl.na_blad = lambda: self._porazka('blad lacza')
        self.dek = Dekoder()
        self.stan = 'STOP'
        self.powod = None
        self.budzik = None
        self.resety = 0
        self.wersja = None
        self.bufor_czujnikow = bytearray()
        self.stat = collections.Counter()
        self.t0 = None

    def _pisz(self, dane):
        self.io.pisz_tty(dane)

    def _za(self, sek, fn):
        self.budzik = (self.zegar() + sek, fn)

    # -- przebieg

    def start(self):
        self.resety += 1
        self.t0 = self.zegar()
        self.io.steruj('ESW:NOTREADY')
        self.tl.wyzeruj()
        self.dek = Dekoder()
        self.bufor_czujnikow = bytearray()
        self.proby_autobaud = 0
        self.proby_resetu_rom = 0
        self.stan = 'RESET'
        self.log('start %d: uklad w stan czuwania' % self.resety)
        self.io.nstdby(0)
        self._za(self.RESET_NISKO, self._wlacz)

    def _wlacz(self):
        self.io.nstdby(1)
        self._za(self.PO_WLACZENIU, lambda: self._autobaud('ROM'))

    def _autobaud(self, cel):
        self.cel = cel
        self.stan = 'AUTOBAUD_' + cel
        self.io.pisz_tty(self.AUTOBAUD)
        self._za(self.PO_AUTOBAUD, self._sync)

    def _sync(self):
        self.stan = 'SYNC_' + self.cel
        self.tl.synchronizuj(self._po_sync)

    def _po_sync(self, ok):
        if not ok:
            self.proby_autobaud += 1
            if self.proby_autobaud >= self.AUTOBAUD_PROB:
                return self._porazka('%s SYNC failure' % self.cel)
            return self._autobaud(self.cel)
        self.log('synchronizacja z %s po %.0f ms'
                 % (self.cel, 1000 * (self.zegar() - self.t0)))
        self.proby_autobaud = 0
        self.proby_wersji = 0
        self._pytaj_o_wersje()

    def _pytaj_o_wersje(self):
        self.stan = 'WERSJA_' + self.cel
        self.proby_wersji += 1
        self.tl.wyslij(koduj_rpc([(RPC_GET_VERSION, b'')]), niezawodnie=True)
        self._za(self.WERSJA_CO, self._brak_wersji)

    def _brak_wersji(self):
        if self.proby_wersji >= self.WERSJA_PROB:
            return self._porazka('brak VersionResponse od %s' % self.cel)
        self._pytaj_o_wersje()

    def _wersja(self, d):
        if not self.stan.startswith('WERSJA_') or len(d) < 12:
            self.stat['wersja_poza_kolejka'] += 1
            return
        asic, rom, poziom = struct.unpack_from('<III', d)
        self.budzik = None
        self.wersja = (asic, rom, poziom)
        self.log('%s: asic 0x%08x rom 0x%08x patch %d'
                 % (self.cel, asic, rom, poziom))
        if self.cel == 'APP':
            if (asic & 0xFFFFFF) != (self.patch.asic & 0xFFFFFF):
                return self._porazka('aplikacja zglasza asic 0x%08x' % asic)
            return self._gotowy()
        bledy = sprawdz_zgodnosc(self.patch, asic, rom, poziom)
        if bledy and poziom != self.patch.poziom and not self.proby_resetu_rom:
            # uklad nie jest w ROM (np. aplikacja zostala po poprzednim
            # demonie): jeszcze jeden reset linia nStdby
            self.proby_resetu_rom += 1
            self.log('uklad nie w ROM (%s), reset' % '; '.join(bledy))
            self.tl.wyzeruj()
            self.io.nstdby(0)
            self._za(self.RESET_NISKO, self._wlacz)
            return
        if bledy:
            return self._porazka('patch niezgodny: ' + '; '.join(bledy))
        self._wgrywaj()

    def _wgrywaj(self):
        self.stan = 'WGRYWANIE'
        self.io.steruj('BBD:PassThru=1')
        self.do_wgrania = [koduj_rpc([r]) for r in self.patch.rpc_wgrywania()]
        self.nr_rekordu = 0
        self.t_wgrywania = self.zegar()
        self._pompuj()

    def _pompuj(self):
        while self.nr_rekordu < len(self.do_wgrania):
            rpc = self.do_wgrania[self.nr_rekordu]
            if not self.tl.zmiesci(len(rpc)):
                return
            self.tl.wyslij(rpc, niezawodnie=True)
            self.nr_rekordu += 1
        if not self.tl.w_locie:
            self._uruchom_aplikacje()

    def _uruchom_aplikacje(self):
        dt = self.zegar() - self.t_wgrywania
        self.log('patch wgrany: %d RPC, %d B bloba w %.1f s'
                 % (len(self.do_wgrania), len(self.patch.blob), dt))
        self.io.steruj('BBD:PassThru=0')
        if self.patch.typ == 'A':
            rpc = (RPC_START_SCRATCH_APP, struct.pack('<I', self.patch.adres))
        else:
            rpc = (RPC_SERVICE_START, struct.pack('<5I', self.patch.adres, 0, 0, 0, 0))
        self.tl.wyslij(koduj_rpc([rpc]))
        self.stan = 'START_APLIKACJI'
        self._za(self.PO_STARCIE_APLIKACJI, lambda: self._autobaud('APP'))

    def _gotowy(self):
        self.stan = 'GOTOWY'
        self.resety = 0
        self.log('hub gotowy po %.1f s od startu' % (self.zegar() - self.t0))
        self.io.steruj('ESW:READY')

    def _porazka(self, powod):
        self.log('porazka: %s' % powod)
        self.budzik = None
        self.tl.wyzeruj()
        if self.resety >= self.MAKS_RESETOW:
            self.stan = 'UPADEK'
            self.powod = powod
            self.io.steruj('ESW:NOTREADY')
            self.io.nstdby(0)
            return
        self.start()

    # -- wejscia

    def tick(self, teraz=None):
        teraz = self.zegar() if teraz is None else teraz
        self.tl.tick(teraz)
        if self.budzik is not None and teraz >= self.budzik[0]:
            fn = self.budzik[1]
            self.budzik = None
            fn()
        if self.stan == 'WGRYWANIE':
            self._pompuj()

    def termin(self):
        t = [x for x in (self.tl.termin(),
                         self.budzik[0] if self.budzik else None) if x is not None]
        return min(t) if t else None

    def z_tty(self, dane):
        for r in self.dek.karm(dane):
            ladunek = self.tl.odbierz(r)
            if ladunek is None:
                continue
            rpcs = dekoduj_rpc(ladunek)
            if rpcs is None:
                self.stat['zly_ladunek'] += 1
                continue
            for ident, d in rpcs:
                self._rpc(ident, d)
        if self.stan == 'WGRYWANIE':
            self._pompuj()

    def _rpc(self, ident, d):
        self.stat['rpc_0x%02x' % ident] += 1
        if ident == RPC_VERSION_RESPONSE:
            self._wersja(d)
        elif ident == RPC_SENSOR_RESPONSE:
            pass            # powtorka, pierwszy egzemplarz dostalo juz SSP w jadrze
        elif self.stat['rpc_0x%02x' % ident] == 1:
            self.log('RPC 0x%02x od ukladu (%d B), pierwszy raz: %s'
                     % (ident, len(d), d[:16].hex()))

    def z_czujnikow(self, dane):
        """/dev/bbd_sensor: rekordy [u16 dlugosc][pakiet SSP], jak bbd_send_packet.
        Kazdy rekord idzie w calosci jako ladunek RPC 0x20, lustro RPC 0x21."""
        self.bufor_czujnikow += dane
        rekordy = []
        b = self.bufor_czujnikow
        while len(b) >= 2:
            n = struct.unpack_from('<H', b)[0]
            if len(b) < 2 + n:
                break
            rekordy.append(bytes(b[:2 + n]))
            del b[:2 + n]
        if self.stan != 'GOTOWY':
            self.stat['czujniki_przed_gotowoscia'] += len(rekordy)
            return
        porcja = []
        for rek in rekordy:
            rpc = koduj_rpc([(RPC_SENSOR_REQUEST, rek)])
            if len(rpc) > MAKS_LADUNEK:
                self.stat['czujniki_za_duze'] += 1
                self.log('pakiet SSP %d B nie miesci sie w RPC' % len(rek))
                continue
            if porcja and sum(map(len, porcja)) + len(rpc) > MAKS_LADUNEK:
                self.tl.wyslij(b''.join(porcja), self.czujniki_niezawodnie)
                porcja = []
            porcja.append(rpc)
            self.stat['czujniki_do_huba'] += 1
        if porcja:
            self.tl.wyslij(b''.join(porcja), self.czujniki_niezawodnie)

    def ze_sterowania(self, dane):
        for tekst in dane.split(b'\0'):
            tekst = tekst.decode('ascii', 'replace').strip()
            if not tekst:
                continue
            self.log('bbd_control: %s' % tekst)
            if 'BBD:RESET_REQ' in tekst:
                self.resety = 0
                self._porazka('reset na zadanie jadra')


# ---------------------------------------------------------------- urzadzenia

class Urzadzenia:
    def __init__(self, a, log):
        self.log = log
        self.nstdby_sciezka = a.nstdby
        self.tty = os.open(a.tty, os.O_RDWR | os.O_NONBLOCK)
        self.czuj = os.open(a.czujniki, os.O_RDWR | os.O_NONBLOCK)
        self.ster = os.open(a.sterowanie, os.O_RDWR | os.O_NONBLOCK)
        self.kolejka = bytearray()

    def pisz_tty(self, dane):
        self.kolejka += dane
        self.wypchnij()

    def wypchnij(self):
        # zapis do /dev/ttyBCM zwraca mniej, gdy bufor nadawczy jadra jest pelny
        while self.kolejka:
            try:
                n = os.write(self.tty, self.kolejka)
            except BlockingIOError:
                return
            if n <= 0:
                return
            del self.kolejka[:n]

    def steruj(self, tekst):
        # bbd_control szuka napisu strstr-em w buforze, ktorego nie zeruje
        os.write(self.ster, tekst.encode() + b'\0')

    def nstdby(self, v):
        with open(self.nstdby_sciezka, 'w') as f:
            f.write('1' if v else '0')


def petla(a):
    def log(s):
        print('hubd: %s' % s, file=sys.stderr, flush=True)

    with open(a.patch, 'rb') as f:
        patch = Patch(f.read())
    log('patch %s: %d rekordow, asic 0x%08x, adres startu 0x%08x, Crc %d zgodne'
        % (patch.pola.get('Name'), len(patch.rekordy), patch.asic, patch.adres,
           patch.crc_naglowka))
    if a.sprawdz_patch:
        return 0
    io = Urzadzenia(a, log)
    hub = Hub(io, patch, log=log, czujniki_niezawodnie=not a.czujniki_zwykle)
    koniec = []
    signal.signal(signal.SIGTERM, lambda *_: koniec.append(1))
    signal.signal(signal.SIGINT, lambda *_: koniec.append(1))
    poll = select.poll()
    poll.register(io.czuj, select.POLLIN)
    poll.register(io.ster, select.POLLIN)
    hub.start()
    ostatnie_stat = time.monotonic()
    while not koniec and hub.stan != 'UPADEK':
        poll.register(io.tty, select.POLLIN | (select.POLLOUT if io.kolejka else 0))
        t = hub.termin()
        czekaj = 50 if t is None else max(0, min(50, int((t - time.monotonic()) * 1000) + 1))
        for fd, ev in poll.poll(czekaj):
            if fd == io.tty:
                if ev & select.POLLOUT:
                    io.wypchnij()
                if ev & select.POLLIN:
                    hub.z_tty(os.read(io.tty, 32768))
            elif fd == io.czuj and ev & select.POLLIN:
                hub.z_czujnikow(os.read(io.czuj, 8192))
            elif fd == io.ster and ev & select.POLLIN:
                hub.ze_sterowania(os.read(io.ster, 4096))
        hub.tick()
        if a.statystyki and time.monotonic() - ostatnie_stat > a.statystyki:
            ostatnie_stat = time.monotonic()
            log('stan %s, TL %s, hub %s' % (hub.stan, dict(hub.tl.stat), dict(hub.stat)))
    log('koniec: stan %s%s' % (hub.stan, ', ' + hub.powod if hub.powod else ''))
    try:
        io.steruj('ESW:NOTREADY')
        io.nstdby(0)
    except OSError:
        pass
    return 1 if hub.stan == 'UPADEK' else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--tty', default='/dev/ttyBCM')
    p.add_argument('--czujniki', default='/dev/bbd_sensor')
    p.add_argument('--sterowanie', default='/dev/bbd_control')
    p.add_argument('--patch', default='/dev/bbd_patch')
    p.add_argument('--nstdby', default='/sys/class/sec/gps/GPS_PWR_EN/value')
    p.add_argument('--czujniki-zwykle', action='store_true',
                   help='RPC 0x20 w zwyklych pakietach zamiast RELIABLE')
    p.add_argument('--sprawdz-patch', action='store_true',
                   help='tylko wczytaj i sprawdz patch, ukladu nie ruszaj')
    p.add_argument('--statystyki', type=float, default=0,
                   help='co ile sekund logowac liczniki (0 = nie)')
    a = p.parse_args(argv)
    try:
        return petla(a)
    except BladPatcha as e:
        print('hubd: patch odrzucony: %s' % e, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
