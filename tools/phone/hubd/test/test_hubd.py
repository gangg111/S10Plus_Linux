"""Testy hubd bez telefonu: python -m unittest discover tools/phone/hubd/test

Prawdziwy patch (909 kB) podaje sie przez HUBD_PATCH=<plik .txt>; bez niego
testy rozruchu jada na malym patchu zbudowanym tutaj, z CRC liczonym od zera.
"""
import os
import random
import struct
import sys
import unittest

TU = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(TU, '..'))
sys.path.insert(0, TU)
import hubd as H  # noqa: E402
import emulator as E  # noqa: E402


def crc8(dane, s=0):
    """CRC-8 liczone bitowo, niezaleznie od tablicy w hubd."""
    for b in dane:
        s ^= b
        for _ in range(8):
            s = ((s << 1) ^ 0x4D) & 0xFF if s & 0x80 else (s << 1) & 0xFF
    return s


def maly_patch(obszarow=40, ziarno=7):
    los = random.Random(ziarno)
    blob = bytearray()
    adres = 0x00800000
    for _ in range(obszarow):
        dane = bytes(los.randrange(256) for _ in range(912))
        blob += bytes((0xF1,)) + struct.pack('<HI', 4 + len(dane), adres) + dane
        adres += len(dane)
    nazwa, klient = b'test_hubd', b'None'
    slowa = struct.pack('<7I', len(blob), 0x004775B0, 0xFFFFFFFF, 0, 1, ord('A'), 0x00800161)
    crc = crc8(bytes(blob), crc8(slowa + klient.ljust(32, b'\0') + nazwa.ljust(32, b'\0')))
    tekst = ('<FormatVersion=0x00010003>\n<Crc=%d>\n<BlobLength=%d>\n<AsicVersion=0x004775B0>\n'
             '<ChangeList=4294967295>\n<PatchLevel=0>\n<PostPatchLevel=1>\n'
             '<CustomerVersion=None>\n<Name=test_hubd>\n<Type=Application>\n'
             '<PatchAddress=0x00800161>\n<Blob=%s>\n' % (crc, len(blob), blob.hex().upper()))
    return H.Patch(tekst.encode() + b'\0')


def patch_do_testow():
    p = os.environ.get('HUBD_PATCH')
    if p:
        with open(p, 'rb') as f:
            return H.Patch(f.read())
    return maly_patch()


class Ramki(unittest.TestCase):
    def test_wektor_zapytania_z_jadra(self):
        # bcm_gps_regs.c, transaction_2nd bez bajtu komendy SSI
        r = H.zbuduj_ramke(0, H.F_INTERNAL | H.F_IGNORE_SEQID, bytes((0, 1)))
        self.assertEqual(r, bytes.fromhex('B0 00 00 02 80 03 00 00 00 01 B1 B0 01'))

    def test_wektor_odpowiedzi_z_jadra(self):
        # bcm_gps_regs.c, zakomentowana transaction_3rd: CRC 0x43 musi przejsc
        f = H.Dekoder().karm(bytes.fromhex('B0 00 00 08 80 01 00 01 01 00 00 FF 00 00 FF 43 B0 01'))
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].flagi, H.F_INTERNAL)
        self.assertEqual(f[0].ladunek, bytes.fromhex('01 01 00 00 FF 00 00 FF'))

    def test_tablica_crc_rowna_bitowemu(self):
        for b in range(256):
            self.assertEqual(H.TABELA_CRC[b], crc8(bytes((b,))))

    def test_losowe_ramki_w_obie_strony(self):
        los = random.Random(3)
        wybor = [0, H.F_ACK, H.F_RELIABLE, H.F_RELIABLE_ACK, H.F_INTERNAL,
                 H.F_RELIABLE | H.F_ACK, H.F_INTERNAL | H.F_IGNORE_SEQID]
        strumien, oczek = bytearray(b'\x13\x80\xb0'), []
        for i in range(400):
            n = los.choice([0, 1, 5, 255, 256, 900, 1024])
            lad = bytes(los.choice([0xB0, 0x11, 0x13, 0x00, 0x01, los.randrange(256)])
                        for _ in range(n))
            fl = los.choice(wybor)
            det = {m: los.randrange(256) for m in (1, 2, 4, 8, 16, 32, 0x100, 0x200) if fl & m}
            strumien += H.zbuduj_ramke(i, fl, lad, det)
            if i % 7 == 0:
                strumien += bytes(los.randrange(256) for _ in range(5))   # smieci
            oczek.append((i & 0xFF, fl, lad))
        dek = H.Dekoder()
        wynik = []
        for k in range(0, len(strumien), 333):
            wynik += dek.karm(strumien[k:k + 333])
        # smieci moga zjesc najwyzej ramke tuz za soba, reszta ma przejsc
        dostalem = {(r.seq, r.flagi, r.ladunek) for r in wynik}
        brak = [o for o in oczek if o not in dostalem]
        self.assertLessEqual(len(brak), len(oczek) // 7 + 1)
        self.assertGreater(len(wynik), 340)

    def test_uszkodzona_ramka_odrzucona(self):
        r = bytearray(H.zbuduj_ramke(5, 0, b'abcdef'))
        r[6] ^= 0x01
        self.assertEqual(H.Dekoder().karm(bytes(r)), [])


class Rpc(unittest.TestCase):
    def test_w_obie_strony(self):
        lista = [(0x00, b''), (0x05, bytes(200)), (0x401, b'xyz'), (0x7FFF, bytes(0x80))]
        self.assertEqual(H.dekoduj_rpc(H.koduj_rpc(lista)), lista)

    def test_ucieta_dlugosc(self):
        self.assertIsNone(H.dekoduj_rpc(bytes((0x05, 0x10, 1, 2))))


class Patche(unittest.TestCase):
    def test_maly_patch(self):
        p = maly_patch()
        self.assertEqual(len(p.rekordy), 40)
        self.assertEqual(sum(len(v) for v in p.obraz().values()), 40 * 912)

    def test_zle_crc(self):
        p = maly_patch()
        tekst = ('<Crc=%d>' % ((p.crc_naglowka + 1) & 0xFF)).encode()
        with self.assertRaises(H.BladPatcha):
            H.Patch(tekst + b'<BlobLength=%d><AsicVersion=0x004775B0><ChangeList=1>'
                    b'<PatchLevel=0><PostPatchLevel=1><Name=x><Type=A><PatchAddress=0x0>'
                    % len(p.blob) + b'<Blob=' + p.blob.hex().encode() + b'>')

    @unittest.skipUnless(os.environ.get('HUBD_PATCH'), 'HUBD_PATCH nie podany')
    def test_prawdziwy_patch(self):
        p = patch_do_testow()
        self.assertEqual(p.asic, 0x004775B0)
        self.assertEqual(p.adres, 0x00800161)
        self.assertTrue(all(k == 0xF1 for k, _ in p.rekordy))


class Rozruch(unittest.TestCase):
    patch = None

    @classmethod
    def setUpClass(cls):
        cls.patch = patch_do_testow()

    def gotowy(self, s):
        self.assertTrue(s.az(lambda: s.hub.stan in ('GOTOWY', 'UPADEK')),
                        'stan %s, logi %s' % (s.hub.stan, s.logi[-5:]))
        self.assertEqual(s.hub.stan, 'GOTOWY', s.logi[-8:])
        self.assertEqual(s.uklad.tryb, 'APP')
        self.assertEqual(s.uklad.pamiec, self.patch.obraz())
        self.assertEqual(s.sterowanie[-1], 'ESW:READY')

    def test_bez_strat(self):
        s = E.Symulacja(self.patch)
        self.gotowy(s)
        self.assertEqual(s.uklad.nack, 0)
        self.assertEqual(s.hub.tl.stat['powtorki'], 0)
        self.assertEqual(s.sterowanie[:2], ['ESW:NOTREADY', 'BBD:PassThru=1'])

    def test_ze_stratami(self):
        for ziarno in range(4):
            s = E.Symulacja(self.patch, strata=0.05, ziarno=ziarno)
            self.gotowy(s)
            self.assertGreater(s.hub.tl.stat['powtorki'], 0)

    def test_most_czujnikow(self):
        for rel in (False, True):
            s = E.Symulacja(self.patch, rel_czujniki=rel)
            self.gotowy(s)
            pakiety = [bytes((i, 0x55, 0xAA)) * (i + 1) for i in range(30)]
            s.hub.z_czujnikow(b''.join(struct.pack('<H', len(p)) + p for p in pakiety))
            s.az(lambda: len(s.jadro.do_ssp) >= 29, limit=5)
            # przy odpowiedziach RELIABLE jadro oddaje demonowi pierwsza z nich
            # (jego licznik numerow startuje od 0, uklad nadaje 0), SSP jej nie dostaje
            oczek = pakiety[1:] if rel else pakiety
            self.assertEqual(s.jadro.do_ssp, oczek)
            self.assertEqual(s.uklad.uruchomienia, 30)

    def test_rekord_czujnika_w_kawalkach(self):
        s = E.Symulacja(self.patch)
        self.gotowy(s)
        rek = struct.pack('<H', 5) + b'hello'
        s.hub.z_czujnikow(rek[:3])
        s.hub.z_czujnikow(rek[3:])
        s.az(lambda: s.jadro.do_ssp, limit=5)
        self.assertEqual(s.jadro.do_ssp, [b'hello'])

    def test_reset_na_zadanie_jadra(self):
        s = E.Symulacja(self.patch)
        self.gotowy(s)
        s.hub.ze_sterowania(b'BBD:RESET_REQ\0')
        self.assertNotEqual(s.hub.stan, 'GOTOWY')
        self.gotowy(s)
        self.assertEqual(s.uklad.wgrania, 2)

    def test_martwy_uklad(self):
        s = E.Symulacja(self.patch, martwy=True)
        s.az(lambda: s.hub.stan == 'UPADEK', limit=120)
        self.assertEqual(s.hub.stan, 'UPADEK')
        self.assertIn('SYNC failure', s.hub.powod)
        self.assertEqual(s.sterowanie[-1], 'ESW:NOTREADY')
        self.assertFalse(s.uklad.zasilany)


if __name__ == '__main__':
    unittest.main()
