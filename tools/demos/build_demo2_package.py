"""Build the data package for Practical demonstration 2: for each place of the workshop,
the three inputs (Sentinel-2 enlarged, Stage 1, Stage 2), the land-cover model's map of each,
the public reference maps and the scores.

Participants only download and look; nothing here runs in the workshop.

    export SR_API_KEY=srk_... SR_API_URL=https://...
    python tools/demos/build_demo2_package.py OUT_DIR [--weights FILE_OR_URL] [--only NAME]

Needs: sr-client[geo], torch, satlaspretrain_models, duckdb, geopandas, scikit-learn, scipy.
Writes OUT_DIR/<slug>.npz per place and OUT_DIR/summary.json. Upload the folder's content to
the address in build_demo2.py (DATA_URL).
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
exec((Path(__file__).parent / "old_d2_helpers.py").read_text())  # the verified Nov 2 code

from places import AREA_KM, PLACES  # noqa: E402
from sr_client import SRClient, area_around  # noqa: E402

WEIGHTS = ("https://huggingface.co/adbsr-internal/satlas-downstream/resolve/main/"
           "landcover_oem_satlas_swinb_fp16.pth")
TASKS = {"buildings": 7, "roads": 3}   # class index in LC_CLASSES
CELL = 100                             # 250 m squares of 2.5 m pixels


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def per_cell(mask, valid_mask):
    h, w = (s // CELL * CELL for s in mask.shape)
    m = mask[:h, :w].reshape(h // CELL, CELL, w // CELL, CELL).mean((1, 3))
    v = valid_mask[:h, :w].reshape(h // CELL, CELL, w // CELL, CELL).mean((1, 3))
    return np.where(v > 0.9, m, np.nan)


def to_uint16(da):
    return np.clip(np.nan_to_num(da.values) * 10000, 0, 65535).round().astype("uint16")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--weights", default=WEIGHTS)
    ap.add_argument("--only", help="build one place only (name contains this)")
    ap.add_argument("--no-own-model", action="store_true",
                    help="skip the quick per-input model (the 'train your own' numbers)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summary_file = out / "summary.json"
    summary = json.loads(summary_file.read_text()) if summary_file.exists() else {}

    sr = SRClient()
    model = load_landcover_model(args.weights)
    for name, p in PLACES.items():
        if args.only and args.only.lower() not in name.lower():
            continue
        t0 = time.time()
        job = sr.submit(area_around(p["lat"], p["lon"], km=AREA_KM), p["date"])
        job.wait(quiet=True)
        images, valid = load_inputs(job)
        like = images["Stage 2"]
        refs, buildings, roads = reference_maps(like)
        maps = {inp: landcover(model, images[inp]).astype("uint8") for inp in INPUTS}

        rows = {}
        for task, cls in TASKS.items():
            rows[task] = {"reference_share": float(refs[task][valid].mean())}
            truth = per_cell(refs[task], valid)
            for inp in INPUTS:
                s = scores(maps[inp] == cls, refs[task], valid)
                est = per_cell(maps[inp] == cls, valid)
                ok = np.isfinite(est) & np.isfinite(truth)
                s["density_r"] = float(np.corrcoef(est[ok], truth[ok])[0, 1])
                if not args.no_own_model:
                    s["own_model_F1"] = float(train_and_test(images[inp], refs[task], valid)[0])
                rows[task][inp] = {k: round(float(v), 4) for k, v in s.items()}
        meta = {"name": name, "lat": p["lat"], "lon": p["lon"], "date": p["date"],
                "note": p["note"], "job_id": job.id, "pixel_m": 2.5,
                "crs": str(like.rio.crs), "transform": list(like.rio.transform())[:6],
                "warnings": [w["code"] for w in job.warnings],
                "n_buildings": int(len(buildings)), "n_road_segments": int(len(roads)),
                "classes": LC_CLASSES, "class_colours": LC_COLOURS, "scores": rows}
        np.savez_compressed(
            out / f"{slug(name)}.npz",
            s2=to_uint16(images["Sentinel-2"]), stage1=to_uint16(images["Stage 1"]),
            stage2=to_uint16(images["Stage 2"]),
            lc_s2=maps["Sentinel-2"], lc_stage1=maps["Stage 1"], lc_stage2=maps["Stage 2"],
            ref_buildings=refs["buildings"], ref_roads=refs["roads"], valid=valid,
            meta=json.dumps(meta))
        summary[name] = {"file": f"{slug(name)}.npz", **{k: meta[k] for k in (
            "lat", "lon", "date", "note", "warnings", "n_buildings", "n_road_segments",
            "scores")}}
        summary_file.write_text(json.dumps(summary, indent=1))
        size = (out / f"{slug(name)}.npz").stat().st_size / 1e6
        f1 = {t: [rows[t][i]["F1"] for i in INPUTS] for t in TASKS}
        print(f"{name}: {size:.1f} MB, {time.time() - t0:.0f} s, warnings {meta['warnings']}, "
              f"F1 (S2, Stage 1, Stage 2) {f1}", flush=True)


if __name__ == "__main__":
    main()
