"""Run the ready-made areas of the scenario notebook on the SR service and pack their pictures.

    export SR_API_KEY=srk_... SR_API_URL=https://...
    python tools/hackathon/make_areas.py                      # estimates only (free)
    python tools/hackathon/make_areas.py --run OUT_DIR        # run, then write the package
    python tools/hackathon/make_areas.py --run OUT_DIR --only tondo hanoi

Every area in areas.py is run at the three stage-2 levels (tau 100, 250, 500; stage 1 and the
Sentinel-2 input come with each). The result is OUT_DIR/scenario_areas.zip: for each area the
five pictures (one contrast stretch for all, so the levels compare fairly) and meta.json with
the scenes found, the tile count, the cost and the warnings. Upload the zip next to the other
data packages; the notebook then shows these areas at once and without a key.
OUT_DIR/contact_sheet.png shows every area: check that each one is the place its name says.

A finished area is skipped on the next run (delete its folder in OUT_DIR to redo it). Needs an
instructor key (the areas are 3 km; about USD 0.50 each) and sr-client[geo], pillow, matplotlib.

Side effect: the service has then computed every area, so a team that sends one of them from
the notebook gets it back without GPU work (and at once within 24 hours of this run).
"""
import argparse
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from areas import AREAS, LEVELS, stretch_u8  # noqa: E402

TAUS = {k: t for k, _, t in LEVELS if t}
LAYERS = [k for k, _, _ in LEVELS]
NAME = "scenario_areas"


def estimates(sr, box, date):
    """What a fresh run would cost at each level, and the scenes it would use."""
    usd = {"stage1": sr.estimate(box, date, stages=["1"], cache=False).get("estimated_usd", 0)}
    est = {}
    for k, tau in TAUS.items():
        est = sr.estimate(box, date, tau=tau, cache=False)
        usd[k] = est.get("estimated_usd", 0)
    return usd, est


def submit(sr, box, date, tau):
    from sr_client import SRError
    while True:
        try:
            return sr.submit(box, date, tau=tau)
        except SRError as exc:
            if getattr(exc, "status", None) != 429:      # 429: the key's queue is full
                raise
            time.sleep(20)


def rgb(job, name):
    da = job.open(name)
    return np.moveaxis(da.isel(band=[0, 1, 2]).values.astype("float32"), 0, -1)


def run_area(sr, slug, a, out):
    from PIL import Image
    from sr_client import area_around
    box = area_around(a["lat"], a["lon"], km=a["km"])
    usd, est = estimates(sr, box, a["date"])
    jobs = {k: submit(sr, box, a["date"], tau) for k, tau in TAUS.items()}
    for k, job in jobs.items():
        job.wait(quiet=True)
        print(f"  {k}: {job.status}, warnings {[w['code'] for w in job.warnings]}")
    first = next(iter(jobs.values()))
    raw = {"s2": rgb(first, "lr_reference.tif"), "stage1": rgb(first, "stage1_sr.tif")}
    raw.update({k: rgb(job, "stage2_sr.tif") for k, job in jobs.items()})
    folder = out / NAME / slug
    folder.mkdir(parents=True, exist_ok=True)
    for k, img in stretch_u8(raw).items():
        if k == "s2":
            Image.fromarray(img).save(folder / "s2.png")
        else:
            Image.fromarray(img).save(folder / f"{k}.jpg", quality=95, subsampling=0)
    facts = {"tiles": est.get("tiles"), "usd": usd,
             "scenes": [{"date": s["date"], "cloud_cover": s.get("cloud_cover")}
                        for s in est.get("scenes", [])],
             "warnings": sorted({w["code"] for j in jobs.values() for w in j.warnings}),
             "jobs": {k: j.id for k, j in jobs.items()},
             "actual_usd": {k: (j.info.get("cost") or {}).get("actual_usd")
                            for k, j in jobs.items()}}
    (folder / "facts.json").write_text(json.dumps(facts, indent=1))
    return facts


def pack(out):
    """meta.json, the zip and the contact sheet, from every finished area in OUT_DIR."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    root = out / NAME
    done = [s for s in AREAS if (root / s / "facts.json").exists()
            and all(any((root / s / f"{k}.{e}").exists() for e in ("jpg", "png"))
                    for k in LAYERS)]
    meta = {"areas": {s: json.loads((root / s / "facts.json").read_text()) for s in done}}
    (root / "meta.json").write_text(json.dumps(meta))
    with zipfile.ZipFile(out / f"{NAME}.zip", "w", zipfile.ZIP_STORED) as z:
        z.write(root / "meta.json", f"{NAME}/meta.json")
        for s in done:
            for p in sorted((root / s).glob("*.[jp][pn]g")):
                z.write(p, f"{NAME}/{s}/{p.name}")
    if done:
        fig, axes = plt.subplots(len(done), 3, figsize=(9, 3.1 * len(done)), squeeze=False)
        for row, s in zip(axes, done):
            for ax, k in zip(row, ("s2", "stage1", "t250")):
                p = next(root.joinpath(s).glob(f"{k}.*"))
                ax.imshow(Image.open(p), interpolation="nearest")
                ax.set_xticks([]), ax.set_yticks([])
                ax.set_title(f"{AREAS[s]['name']}\n{k}" if k == "s2" else k, fontsize=8)
        fig.tight_layout()
        fig.savefig(out / "contact_sheet.png", dpi=110)
    size = (out / f"{NAME}.zip").stat().st_size / 1e6
    print(f"packed {len(done)} of {len(AREAS)} areas: {out / (NAME + '.zip')} ({size:.0f} MB)")
    missing = [s for s in AREAS if s not in done]
    if missing:
        print("not in the package (the notebook sends these to the service):", ", ".join(missing))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", metavar="OUT_DIR", help="run the areas and write the package here")
    ap.add_argument("--only", nargs="*", help="slugs of the areas to run (default: all)")
    ap.add_argument("--pack-only", action="store_true", help="pack what OUT_DIR holds; run nothing")
    args = ap.parse_args()
    wanted = {s: a for s, a in AREAS.items() if not args.only or s in args.only}
    out = Path(args.run).resolve() if args.run else None
    if args.pack_only:
        return pack(out)
    from sr_client import SRClient, area_around
    sr = SRClient()  # SR_API_KEY / SR_API_URL from the environment
    total = 0.0
    for slug, a in wanted.items():
        box = area_around(a["lat"], a["lon"], km=a["km"])
        usd, est = estimates(sr, box, a["date"])
        days = sorted({s["date"] for s in est.get("scenes", [])})
        total += sum(v for k, v in usd.items() if k != "stage1")
        flags = ", ".join(w.get("code", "?") for w in est.get("warnings_likely", []))
        flags += "".join(f" PROBLEM: {x}" for x in est.get("problems", []))
        print(f"{slug}: {est.get('tiles')} tiles, {len(days)} clear days"
              f"{' (' + days[0] + ' to ' + days[-1] + ')' if days else ''}, "
              f"~${sum(v for k, v in usd.items() if k != 'stage1'):.2f} {('[' + flags + ']') if flags else ''}")
    print(f"total ~${total:.2f} (before caching)")
    if not out:
        return
    for slug, a in wanted.items():
        if (out / NAME / slug / "facts.json").exists():
            print(f"{slug}: already done")
            continue
        print(f"{slug}: {a['name']}")
        try:
            run_area(sr, slug, a, out)
        except Exception as exc:  # one bad area must not stop the rest
            print(f"  FAILED: {exc}")
    pack(out)


if __name__ == "__main__":
    main()
