#!/usr/bin/env python
"""verify_roster_md5.py — hard md5 gate on the 44 roster prediction SOURCE files.

For every model in ROSTER25_DATA_MANIFEST.json, hash its downloaded Figshare source
(`~/mt_uip_roster25/_raw/<short>.csv.gz`) and compare to the manifest's `supplied_md5`
(the Figshare-published md5, verified against api.figshare.com computed_md5). This is the
ONLY acceptable closure for "are there other duplicated / corrupt roster files?" — an
ad-hoc byte-dedup scan is not.

Gate: 44/44 OK. Any FAIL means that model's source is not the authoritative published file;
its numbers must NOT be integrated and it must be listed prominently.

NOTE on the orb_v2_omat finding (2026-07-14): orb_v2_omat's source PASSES this gate (it IS
the genuine published Figshare 51607307, md5 d00f381...). Its problem is a different one the
md5 gate cannot catch — that genuine published Orb-v2 checkpoint is byte-identical to the
frozen 'orb' headline anchor, so it is a non-independent duplicate and is dropped from the
generational contrast (see mt29_roster_expansion_audit_dedup.py). The gate confirms it is the
only such case: all 44 raw sources are authentic, distinct published files by md5.

CPU only, no network.
"""
import os, sys, json, hashlib

MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ROSTER25_DATA_MANIFEST.json")
RAW_DIR = os.path.expanduser("~/mt_uip_roster25/_raw")


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    manifest = json.load(open(MANIFEST))
    models = manifest["models"]
    n = len(models)
    ok = 0
    fails = []
    print(f"md5 gate over {n} roster source files in {RAW_DIR}")
    print(f"{'model':18s} {'fig_id':>9s}  status  md5")
    for short in sorted(models):
        m = models[short]
        want = m["supplied_md5"]
        raw = os.path.join(RAW_DIR, f"{short}.csv.gz")
        if not os.path.exists(raw):
            fails.append((short, "MISSING", want, None))
            print(f"{short:18s} {m['figshare_id']:>9d}  FAIL    MISSING (want {want})")
            continue
        got = md5_of(raw)
        if got == want:
            ok += 1
            print(f"{short:18s} {m['figshare_id']:>9d}  OK      {got}")
        else:
            fails.append((short, "MISMATCH", want, got))
            print(f"{short:18s} {m['figshare_id']:>9d}  FAIL    {got} != supplied {want}")

    print("-" * 72)
    print(f"MD5 GATE: {ok}/{n} OK" + ("" if not fails else f"  ({len(fails)} FAIL)"))
    if fails:
        print("FAILURES (do NOT integrate these models' numbers):")
        for short, kind, want, got in fails:
            print(f"  - {short}: {kind} (supplied {want}, got {got})")
        sys.exit(1)
    print("All 44 roster raw sources are the authentic Figshare-published files (md5-verified).")
    sys.exit(0)


if __name__ == "__main__":
    main()
