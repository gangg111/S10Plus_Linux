# Obraz partycji up_param: kopia bazowego tara z podmienionymi plikami, ta sama kolejnosc
# i metadane wpisow (mode/uid/gid/uname/gname/mtime), USTAR, dopelnienie zerami do 8 MB.
# Uzycie: python pakuj.py <baza.tar> <wynik.tar> nazwa=plik [nazwa=plik ...]
import io
import sys
import tarfile

SIZE = 8388608
base, out = sys.argv[1], sys.argv[2]
repl = dict(a.split("=", 1) for a in sys.argv[3:])
src = tarfile.open(base)
buf = io.BytesIO()
dst = tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT)
done = set()
for m in src.getmembers():
    data = src.extractfile(m).read() if m.isfile() else None
    if m.name in repl:
        data = open(repl[m.name], "rb").read()
        done.add(m.name)
    info = tarfile.TarInfo(m.name)
    for k in ("mode", "uid", "gid", "uname", "gname", "mtime", "type"):
        setattr(info, k, getattr(m, k))
    info.size = len(data) if data is not None else 0
    dst.addfile(info, io.BytesIO(data) if data is not None else None)
dst.close()
assert done == set(repl), set(repl) - done
raw = buf.getvalue()
assert len(raw) <= SIZE, len(raw)
open(out, "wb").write(raw + b"\0" * (SIZE - len(raw)))
print("wpisow %d, tar %d B z %d" % (len(src.getmembers()), len(raw), SIZE))
