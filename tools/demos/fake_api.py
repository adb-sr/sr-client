"""Offline stand-in for the SR API, for testing the demo notebooks without a key.

Replaces ``SRClient._call`` so every client method (me, models, estimate, submit, refresh,
results, upgrade) answers from real dev job outputs on disk. Result links point at a local
HTTP server over those outputs, so ``Job.open``/``download``/``show`` and the notebooks'
manifest reads run their real code paths. A submit maps to the stored job whose area centre
is nearest (and, among equals, whose size is closest); EXCLUDE drops jobs we must not use.
"""
import glob
import json
import math
import os
import uuid

import sr_client
from sr_client import client as C

ROOT = os.environ["FAKE_JOBS_DIR"]
BASE = os.environ["FAKE_JOBS_URL"].rstrip("/")
EXCLUDE = {"7f21b1ad"}  # Cebu 2026-04-15: primary scene geolocated 20 m off

STORED = []
for f in glob.glob(f"{ROOT}/*/out/manifest.json"):
    jid = f.split("/")[-3]
    if jid[:8] in EXCLUDE or not os.path.exists(f"{ROOT}/{jid}/out/stage2_sr.tif"):
        continue
    m = json.load(open(f))
    a = m["params"]["area"]
    w, s, e, n = a["bbox"] if isinstance(a, dict) else a
    STORED.append((jid, m, ((s + n) / 2, (w + e) / 2), (e - w)))

JOBS = {}
MODELS = [{  # copied from sr_service.api
    "name": "sen4x-v2",
    "stages": {"1": "Sen4xProd: multi-image Swin2SR, 8 revisits at 10 m -> 2.5 m",
               "2": "DiT diffusion refiner, class-conditioned on GHS settlement type"},
    "params": {"tau": {"min": 10, "max": 1000, "default": 250},
               "nfe": {"min": 10, "max": "tau", "default": "tau"},
               "seed": {"min": 0, "max": 2 ** 31 - 1, "default": 0},
               "class_label": {"min": 0, "max": 3, "default": "GHS rule"}},
    "output": {"pixel_m": 2.5, "bands": ["red", "green", "blue", "nir"],
               "dtype": "uint16", "units": "reflectance x 10000", "nodata": 0},
}]


def _bbox(area):
    if isinstance(area, dict):
        area = area.get("bbox", area)
    return area


def _pick(area):
    w, s, e, n = _bbox(area)
    c, size = ((s + n) / 2, (w + e) / 2), e - w
    return min(STORED, key=lambda t: (round(math.dist(c, t[2]), 2), abs(size - t[3])))


def _call(self, method, path, **kw):
    body = kw.get("json") or {}
    if path == "/v1/me":
        return {"prefix": "srk_fake", "owner": "offline-test", "org": "test",
                "expires_at": None,
                "limits": {"max_area_km": 5, "max_tiles": 441, "max_running": 1,
                           "max_queued": 3},
                "budget": {"budget_usd": 3.0, "spent_usd": 0.0, "remaining_usd": 3.0}}
    if path == "/v1/models":
        return {"models": MODELS}
    if path == "/v1/estimate":
        jid, m, _, _ = _pick(body["area"])
        return {"tiles": len(m["tiles"]), "estimated_usd": 0.12,
                "search_window": m["acquisition"]["search_window"],
                "scenes": [{"id": k, "date": v["datetime"][:10],
                            "cloud_cover": v["cloud_cover"]} for k, v in m["scenes"].items()],
                "warnings_likely": [], "problems": [], "submittable": True}
    if path == "/v1/jobs" and method == "POST":
        jid, m, _, _ = _pick(body["area"])
        new = str(uuid.uuid4())
        JOBS[new] = (jid, m, body)
        return {"job_id": new, "status": "queued", "estimated_usd": 0.12}
    parts = path.strip("/").split("/")
    if parts[:2] == ["v1", "jobs"] and len(parts) >= 3:
        jid, m, body = JOBS[parts[2]]
        if len(parts) == 3 and method == "GET":
            return {"id": parts[2], "status": "done", "model": "sen4x-v2",
                    "params": {**m["params"], **body}, "error": None,
                    "progress": [{"step": "stage2", "state": "done", "done": 4, "total": 4}],
                    "warnings": m["warnings"], "results_ready": True,
                    "cost": {"estimated_usd": 0.12, "actual_usd": m["cost"]["usd"]}}
        if parts[3:] == ["results"]:
            return {"job_id": parts[2], "status": "done", "stages_done": ["1", "2"],
                    "expires_at": None,
                    "files": {f: f"{BASE}/{jid}/out/{f}" for f in m["files"]},
                    "warnings": m["warnings"], "attribution": m["attribution"]}
        if parts[3:] == ["upgrade"]:
            return {"job_id": parts[2], "status": "queued", "estimated_usd": 0.1}
    raise C.SRError(404, f"fake API: no route for {method} {path}")


C.SRClient._call = _call
sr_client.SRClient._call = _call
print(f"fake SR API: {len(STORED)} stored jobs, files at {BASE}")
