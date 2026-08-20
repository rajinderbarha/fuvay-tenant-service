"""Triage by prefix survival: if the feature's own route prefix still has served
routes, the dead call is a rename inside a LIVE feature (real bug, fixable).
If the whole prefix is gone, the feature was removed."""
import json, re, sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
def norm(p):
    p=p.split("?")[0].rstrip("/"); p=re.sub(r"\$\{[^}]*\}","{p}",p); return re.sub(r"\{[^}]*\}","{p}",p)
served=sorted({norm(p) for p in d["served"]})
live, gone = [], []
for app, paths in d["dead"].items():
    for p in paths:
        segs=p.strip("/").split("/")
        # longest prefix (>=3 segments) that still has ANY served route under it
        best=None
        for n in range(len(segs)-1, 2, -1):
            pref="/"+"/".join(segs[:n])
            sib=[s for s in served if s.startswith(pref+"/") or s==pref]
            if sib:
                best=(pref, sib); break
        (live if best else gone).append((app,p,best))
print(f"IN A LIVE FEATURE AREA ({len(live)}) — real bugs, the area works but this route is wrong")
for app,p,(pref,sib) in sorted(live):
    print(f"  [{app}] {p}\n        area {pref}/ still serves {len(sib)} route(s), e.g. {sib[0]}")
print(f"\nWHOLE FEATURE AREA GONE ({len(gone)}) — removed feature, needs disclosure not a fix")
for app,p,_ in sorted(gone):
    print(f"  [{app}] {p}")
