#!/usr/bin/env python3
# Lists the arm64 packages of the Droidian archive (snapshot 102 + production, as in
# env.sh) whose newest version depends on a qt6-base-private-abi the archive no longer
# provides.  Those are the ones archive-rebuild/build.sh has to rebuild; run this when
# an image build stops on "qt6-base-private-abi (= X) ... none of the choices are
# installable".  Needs python3 and dpkg (for version comparison).
import gzip, lzma, re, subprocess, urllib.request
from collections import defaultdict

REPOS = {
    "snapshot 102": "http://releases.droidian.org/snapshots/102/dists/rolling/main/binary-arm64/Packages",
    "production": "https://production.repo.droidian.org/dists/trixie/main/binary-arm64/Packages",
}
ABI = re.compile(r"qt6-base-private-abi \(= ([^)]+)\)")


def fetch(url):
    for ext, dec in ((".xz", lzma.decompress), (".gz", gzip.decompress), ("", bytes)):
        try:
            with urllib.request.urlopen(url + ext, timeout=60) as r:
                return dec(r.read()).decode("utf-8", "replace")
        except Exception:
            continue
    raise SystemExit("cannot fetch " + url)


def newer(a, b):
    return subprocess.run(["dpkg", "--compare-versions", a, "gt", b]).returncode == 0


versions = defaultdict(list)
for repo, url in REPOS.items():
    for stanza in fetch(url).split("\n\n"):
        f = dict(re.findall(r"^([A-Za-z-]+): (.*)$", stanza, re.M))
        if "Package" in f:
            versions[f["Package"]].append((f.get("Version", ""), repo, f.get("Depends", ""), f.get("Provides", "")))

provided = {m for vs in versions.values() for v in vs for m in ABI.findall(v[3])}
print("qt6-base-private-abi provided:", ", ".join(sorted(provided)))
stale = []
for name, vs in sorted(versions.items()):
    best = vs[0]
    for v in vs[1:]:
        if newer(v[0], best[0]):
            best = v
    for want in ABI.findall(best[2]):
        if want not in provided:
            stale.append((name, best[0], want))
print("packages to rebuild: %d" % len(stale))
for name, version, want in stale:
    print("  %-34s %s (wants Qt %s)" % (name, version, want))
