"""Emulator ukladu BCM47752 i filtra jadra do testow hubd bez telefonu.

FiltrJadra to przepisany bbd_parse_asic_data + TransportLayer_PacketReceived
z bbd_rpc_lh.c: decyduje, ktore surowe bajty trafia do /dev/ttyBCM, a ktore
RPC 0x21 do SSP.  Uklad trzyma sie tej samej scislej logiki RELIABLE, co kod
TL Broadcomu w jadrze (duplikat, nastepny numer, inaczej NACK).

Zalozenia, ktorych nie da sie sprawdzic bez sprzetu (SPEC.md, sekcja 8):
ROM przyjmuje ramki dopiero po autobaud, odpowiada na GetVersion zwyklym
pakietem, potwierdza kazdy pakiet RELIABLE, po StartScratchApp wymaga
ponownego autobaud i synchronizacji.
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import hubd as H  # noqa: E402

ROM = 0x0003F13A        # wartosc zmyslona: realnej nie znamy (SPEC 8)


class FiltrJadra:
    """bbd_rpc_lh.c: m_aucRxEscapedBuf idzie do demona, RPC 0x21 do SSP."""

    MAKS_ESC = (2048 + 14 + 2) * 2

    def __init__(self):
        self.stan = 0
        self.rx = bytearray()
        self.esc = bytearray()
        self.rel = (0, 0, 0)        # m_ucReliableSeqId, m_ucReliableCrc, m_usReliableLen
        self.do_ssp = []

    def karm(self, dane):
        do_demona = bytearray()
        for b in dane:
            if len(self.esc) < self.MAKS_ESC:
                self.esc.append(b)
            if b in (H.XON, H.XOFF):
                continue
            if self.stan == 0:
                if b == H.ESC:
                    self.stan = 1
            elif self.stan == 1:
                if b == H.SOP:
                    self.stan = 2
                    self.rx = bytearray()
                elif b != H.ESC:
                    self.stan = 0
            elif self.stan == 2:
                if b == H.ESC:
                    self.stan = 3
                else:
                    self.rx.append(b)
            else:
                if b == H.EOP:
                    if self._pakiet():
                        do_demona += self.esc
                    self.esc = bytearray()
                    self.stan = 0
                elif b in H.ODWROTNE:
                    self.rx.append(H.ODWROTNE[b])
                    self.stan = 2
                elif b == H.SOP:
                    self.stan = 2
                    self.rx = bytearray()
                    self.esc = bytearray()
                elif b == H.ESC:
                    self.stan = 1
                else:
                    self.stan = 0
        return bytes(do_demona)

    def _pakiet(self):
        """True, gdy jadro przekazuje surowe bajty do /dev/ttyBCM."""
        r = H.rozbierz(bytes(self.rx))
        if r is None:
            return False
        n = len(r.ladunek)
        przetworz = bool(r.flagi & H.F_RELIABLE) or n > 0
        if r.flagi & H.F_RELIABLE:
            nr = r.detale[H.F_RELIABLE]
            if (nr, r.crc, n) == self.rel:
                przetworz = False
            elif nr == (self.rel[0] + 1) & 0xFF:
                self.rel = (nr, r.crc, n)
            else:
                przetworz = False
        if not przetworz:
            return True
        if r.flagi & H.F_INTERNAL:
            return True
        return not self._czujniki(r.ladunek)

    def _czujniki(self, ladunek):
        rpcs = H.dekoduj_rpc(ladunek)
        if rpcs is None:
            return False
        ile = 0
        for ident, d in rpcs:
            if ident == H.RPC_SENSOR_RESPONSE:
                n = struct.unpack_from('<H', d)[0]
                self.do_ssp.append(d[2:2 + n])
                ile += 1
        return ile > 0


class Uklad:
    def __init__(self, patch, los=None, strata=0.0, rel_czujniki=False, martwy=False):
        self.patch = patch
        self.los = los or random.Random(1)
        self.strata = strata
        self.rel_czujniki = rel_czujniki
        self.martwy = martwy
        self.wyjscie = bytearray()
        self.zasilany = False
        self.tryb = None
        self.pamiec = {}
        self.wgrania = 0
        self.uruchomienia = 0
        self.nack = 0
        self.czas = 0.0
        self.w_locie = {}

    # -- linia nStdby

    def nstdby(self, v):
        if not v:
            self.zasilany = False
            self.tryb = None
        elif not self.zasilany:
            self.zasilany = True
            self.pamiec = {}
            self._restart('ROM')

    def _restart(self, tryb):
        self.tryb = tryb
        self.po_autobaud = False
        self.licznik80 = 0
        self.dek = H.Dekoder()
        self.tx_seq = 0
        self.tx_rel = 0
        self.w_locie = {}
        self.rel_nr = 0xFF
        self.rel_klucz = None

    # -- odbior od AP

    def z_ap(self, dane):
        if not self.zasilany or self.martwy:
            return
        i = 0
        while not self.po_autobaud and i < len(dane):
            self.licznik80 = self.licznik80 + 1 if dane[i] == 0x80 else 0
            i += 1
            if self.licznik80 >= 16:
                self.po_autobaud = True
        for r in self.dek.karm(dane[i:]):
            if self.los.random() < self.strata:
                continue
            self._ramka(r)

    def _nadaj(self, flagi, ladunek=b'', detale=None):
        ramka = H.zbuduj_ramke(self.tx_seq, flagi, ladunek, detale)
        self.tx_seq = (self.tx_seq + 1) & 0xFF
        if self.los.random() >= self.strata:
            self.wyjscie += ramka

    def _nadaj_rel(self, ladunek):
        nr = self.tx_rel
        self.tx_rel = (nr + 1) & 0xFF
        self.w_locie[nr] = [ladunek, self.czas]
        self._nadaj(H.F_RELIABLE, ladunek, {H.F_RELIABLE: nr})

    def tick(self, teraz):
        self.czas = teraz
        for nr, w in list(self.w_locie.items()):
            if teraz - w[1] >= 0.5:
                w[1] = teraz
                self._nadaj(H.F_RELIABLE, w[0], {H.F_RELIABLE: nr})

    def _ramka(self, r):
        if r.flagi & H.F_RELIABLE_ACK:
            nr = r.detale[H.F_RELIABLE_ACK]
            for k in list(self.w_locie):
                del self.w_locie[k]
                if k == nr:
                    break
        if r.flagi & H.F_INTERNAL:
            d = r.ladunek
            if d[:1] == b'\0' and len(d) == 2:
                odp = bytes((1, d[1], r.seq, 0, self.rel_nr, self.tx_seq, self.tx_rel,
                             (self.tx_rel - 1) & 0xFF))
                self._nadaj(H.F_INTERNAL, odp)
            return
        przetworz = len(r.ladunek) > 0
        if r.flagi & H.F_RELIABLE:
            nr = r.detale[H.F_RELIABLE]
            klucz = (nr, r.crc, len(r.ladunek))
            if klucz == self.rel_klucz:
                przetworz = False
                self._nadaj(H.F_ACK | H.F_RELIABLE_ACK, b'', {H.F_ACK: r.seq, H.F_RELIABLE_ACK: nr})
            elif nr == (self.rel_nr + 1) & 0xFF:
                self.rel_nr, self.rel_klucz = nr, klucz
                self._nadaj(H.F_ACK | H.F_RELIABLE_ACK, b'', {H.F_ACK: r.seq, H.F_RELIABLE_ACK: nr})
            else:
                przetworz = False
                self.nack += 1
                self._nadaj(H.F_ACK | H.F_RELIABLE_NACK, b'',
                            {H.F_ACK: r.seq, H.F_RELIABLE_NACK: self.rel_nr})
        if not przetworz:
            return
        for ident, d in H.dekoduj_rpc(r.ladunek):
            self._rpc(ident, d)

    def _rpc(self, ident, d):
        if ident == H.RPC_GET_VERSION:
            poziom = 0 if self.tryb == 'ROM' else 1
            self._nadaj(0, H.koduj_rpc([(H.RPC_VERSION_RESPONSE,
                                         struct.pack('<III', self.patch.asic, ROM, poziom))]))
        elif ident == H.RPC_MEMORY_WRITE and self.tryb == 'ROM':
            adres, n = struct.unpack_from('<IH', d)
            assert n == len(d) - 6
            self.pamiec[adres] = d[6:]
        elif ident == H.RPC_START_SCRATCH_APP and self.tryb == 'ROM':
            adres = struct.unpack_from('<I', d)[0]
            if adres == self.patch.adres and self.pamiec == self.patch.obraz():
                self.wgrania += 1
                self._restart('APP')
        elif ident == H.RPC_SENSOR_REQUEST and self.tryb == 'APP':
            self.uruchomienia += 1
            odp = H.koduj_rpc([(H.RPC_SENSOR_RESPONSE, d)])
            if self.rel_czujniki:
                self._nadaj_rel(odp)
            else:
                self._nadaj(0, odp)


class Symulacja:
    """Hub + filtr jadra + uklad na wspolnym zegarze; io dla Hub to self."""

    def __init__(self, patch, strata=0.0, ziarno=1, rel_czujniki=False, martwy=False,
                 czujniki_niezawodnie=True):
        self.czas = 0.0
        self.uklad = Uklad(patch, random.Random(ziarno), strata, rel_czujniki, martwy)
        self.jadro = FiltrJadra()
        self.sterowanie = []
        self.logi = []
        self.do_ukladu = bytearray()
        self.hub = H.Hub(self, patch, zegar=lambda: self.czas, log=self.logi.append,
                         czujniki_niezawodnie=czujniki_niezawodnie)
        self.hub.start()

    def pisz_tty(self, dane):
        self.do_ukladu += dane

    def steruj(self, tekst):
        self.sterowanie.append(tekst)

    def nstdby(self, v):
        self.uklad.nstdby(v)

    def krok(self, dt=0.002):
        self.czas += dt
        if self.do_ukladu:
            d = bytes(self.do_ukladu)
            self.do_ukladu.clear()
            self.uklad.z_ap(d)
        self.uklad.tick(self.czas)
        if self.uklad.wyjscie:
            d = bytes(self.uklad.wyjscie)
            self.uklad.wyjscie.clear()
            f = self.jadro.karm(d)
            if f:
                self.hub.z_tty(f)
        self.hub.tick(self.czas)

    def az(self, warunek, limit=120.0):
        koniec = self.czas + limit
        while not warunek() and self.czas < koniec:
            self.krok()
        return warunek()
