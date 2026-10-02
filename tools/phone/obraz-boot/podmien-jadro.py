# Obraz boot (naglowek Androida v1) z podmienionym jadrem: ramdysk, wiersz polecen
# i reszta naglowka bez zmian, id przeliczony jak w mkbootimg, rozmiar partycji zachowany.
# Uzycie: python podmien-jadro.py <obraz.img> <Image> <wyjscie.img>
import hashlib
import struct
import sys

src, image, dst = sys.argv[1:4]
img = open(src, "rb").read()
assert img[:8] == b"ANDROID!"
ks, ka, rs, ra, ss, sa, ta, page, ver = struct.unpack_from("<9I", img, 8)
assert ver == 1 and ss == 0
ID_OFF = 8 + 36 + 4 + 16 + 512


def pages(n):
    return (n + page - 1) // page * page


old_kernel = img[page:page + ks]
ramdisk = img[page + pages(ks):page + pages(ks) + rs]
assert not any(img[page + pages(ks) + pages(rs):]), "dane za ramdyskiem"


def ident(kernel):
    sha = hashlib.sha1()
    for blob in (kernel, ramdisk, b"", b"", b""):
        sha.update(blob)
        sha.update(struct.pack("<I", len(blob)))
    return sha.digest()


assert img[ID_OFF:ID_OFF + 20] == ident(old_kernel), "inny wzor id"
kernel = open(image, "rb").read()
hdr = bytearray(img[:page])
struct.pack_into("<I", hdr, 8, len(kernel))
hdr[ID_OFF:ID_OFF + 32] = ident(kernel) + b"\0" * 12
new = bytes(hdr) + kernel + b"\0" * (pages(len(kernel)) - len(kernel)) + ramdisk
assert len(new) <= len(img), ("nie miesci sie w partycji", len(new), len(img))
new += b"\0" * (len(img) - len(new))
open(dst, "wb").write(new)
print("jadro %d -> %d B, ramdysk %d B, zajete %d z %d B" %
      (ks, len(kernel), rs, page + pages(len(kernel)) + rs, len(img)))
