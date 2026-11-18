"""Run every job the workshop demos send, before the workshop, so that participants get
them back from the cache quickly and at no cost.

    export SR_API_KEY=srk_... SR_API_URL=https://...
    python tools/demos/prestage.py                  # free estimates for the five places
    python tools/demos/prestage.py --run            # main job of each place
    python tools/demos/prestage.py --run --all      # + the worksheet experiments and the
                                                    #   walkthrough's dial and check jobs
    python tools/demos/prestage.py --run --download DIR   # also save the main jobs' files

Jobs are sent one after another and the script waits whenever the key's queue is full.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from places import (AREA_KM, EXPERIMENTS, PLACES, PRESENTER_CHECKS,  # noqa: E402
                    PRESENTER_DIALS, PRESENTER_PLACE)
from sr_client import SRClient, SRError, area_around  # noqa: E402


def satellogic_scene(scene):
    from rasterio.warp import transform
    d, _, _, zone, e, n = scene.split("_")
    epsg = (32600 if zone.endswith("N") else 32700) + int(zone[:-1])
    lon, lat = transform(f"EPSG:{epsg}", "EPSG:4326", [int(e) + 192], [int(n) - 192])
    return f"{d[:4]}-{d[4:6]}-{d[6:]}", lat[0], lon[0]


def job_list(everything):
    jobs = {}
    for name, p in PLACES.items():
        area = area_around(p["lat"], p["lon"], km=AREA_KM)
        jobs[f"{name} | main"] = (area, p["date"], {})
        if everything:
            for label, params in EXPERIMENTS.items():
                jobs[f"{name} | {label}"] = (area, p["date"], params)
    if everything:
        p = PLACES[PRESENTER_PLACE]
        small = area_around(p["lat"], p["lon"], km=1)
        for label, params in PRESENTER_DIALS.items():
            jobs[f"walkthrough | {label}"] = (small, p["date"], params)
        for place, scene in PRESENTER_CHECKS.items():
            day, lat, lon = satellogic_scene(scene)
            jobs[f"walkthrough | {place}"] = (area_around(lat, lon, km=1), day, {})
    return jobs


def submit(sr, area, day, params):
    while True:
        try:
            return sr.submit(area, day, **params)
        except SRError as exc:
            if exc.status != 429:
                raise
            time.sleep(15)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="send the jobs (uses the key's budget)")
    ap.add_argument("--all", action="store_true", help="also experiments and walkthrough jobs")
    ap.add_argument("--download", help="save the files of each place's main job under DIR")
    args = ap.parse_args()
    sr = SRClient()
    jobs = job_list(args.all)
    total = 0.0
    for name, (area, day, params) in jobs.items():
        est = sr.estimate(area, day, **params)
        total += est["estimated_usd"]
        notes = [w["code"] for w in est["warnings_likely"]] + [f"PROBLEM {p}" for p in est["problems"]]
        print(f"{name}: {day}, {est['tiles']} tiles, ~${est['estimated_usd']:.2f}, "
              f"{len(est['scenes'])} images {notes or ''}")
    print(f"{len(jobs)} jobs, ~${total:.2f} if nothing is cached")
    if not args.run:
        return
    sent = {name: submit(sr, *spec) for name, spec in jobs.items()}
    record = {}
    for name, job in sent.items():
        t0 = time.monotonic()
        job.wait(quiet=True)
        cost = job.info.get("cost", {}).get("actual_usd")
        record[name] = {"job_id": job.id, "status": job.status, "cost_usd": cost,
                        "warnings": [w["code"] for w in job.warnings]}
        print(f"{name}: {job.status} {job.id} ${cost or 0:.3f} {record[name]['warnings']} "
              f"(waited {time.monotonic() - t0:.0f} s)", flush=True)
        if args.download and name.endswith("| main"):
            job.download(args.download)
    if args.download:
        Path(args.download, "prestage.json").write_text(json.dumps(record, indent=1))


if __name__ == "__main__":
    main()
