"""Builds notebooks/demo2_use_cases.ipynb (Practical demonstration 2)."""
import sys

import nbformat as nbf

OUT = sys.argv[1]
cells = []


def md(s):
    cells.append(nbf.v4.new_markdown_cell(s.strip("\n")))


def code(s):
    cells.append(nbf.v4.new_code_cell(s.strip("\n")))


md(r"""
# Practical demonstration 2: from super-resolved images to maps

*SSTA workshop, 26 November 2026. Goes with Session 3, "Sample use cases".*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo2_use_cases.ipynb)

Session 3 showed that super-resolution helps some tasks and not others, and that you should
**test it on a small labelled sample before you rely on it**. In this notebook we run that
test ourselves, in two places:

* **Cebu City and Mandaue**: a dense city, for **structures and streets**;
* **Nueva Ecija**: rice farms with villages and **farm-to-market roads**.

For each place we compare three inputs, as in Session 3: **Sentinel-2** (10 m, enlarged to
2.5 m), **Stage 1** (8 images combined) and **Stage 2** (the full model). We follow the four
steps from Session 3:

| Step | Here |
|---|---|
| 1. Label | public maps: Open Buildings (structures) and OpenStreetMap (roads) |
| 2. Train | a land-cover model already trained on real high-resolution images |
| 3. Apply | run it on each of the three inputs |
| 4. Score | compare each map with the public maps |

Then two more uses: **numbers for planning** (how much of each district is built up), and a
**test with a model you train yourself**, which is also the starting point for tomorrow's
hackathon.

**You need** the API key and service URL from the workshop. **Runtime:** the land-cover model
runs on Colab's CPU in a few minutes; with a GPU (*Runtime → Change runtime type → T4 GPU*)
it takes seconds.
""")

md("## 0. Setup")
code(r"""
%pip install -q "sr-client[geo,viz] @ git+https://github.com/adb-sr/sr-client@v0.1.0" satlaspretrain_models duckdb
""")
code(r"""
import getpass
import os

from sr_client import SRClient, SRError, area_around


def secret(name, prompt):
    if os.environ.get(name):
        return os.environ[name]
    try:
        from google.colab import userdata
        return userdata.get(name)
    except Exception:
        return getpass.getpass(prompt) if "KEY" in name else input(prompt)


os.environ["SR_API_KEY"] = secret("SR_API_KEY", "API key (srk_...): ")
os.environ["SR_API_URL"] = secret("SR_API_URL", "Service URL: ")

sr = SRClient()
print(f"${sr.me()['budget']['remaining_usd']:.2f} of budget left")
""")

code(r'''
# @title Helper functions (run this cell; you do not need to read it) { display-mode: "form" }
import re
import time
import warnings
from pathlib import Path

import duckdb
import geopandas as gpd
import httpx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.warp import transform_bounds
from scipy import ndimage as ndi

warnings.filterwarnings("ignore", category=UserWarning)
plt.rcParams.update({"figure.dpi": 100, "axes.titlesize": 11})
INPUTS = ["Sentinel-2", "Stage 1", "Stage 2"]
COLOURS = {"Sentinel-2": "#a6a6a6", "Stage 1": "#7fbfdf", "Stage 2": "#007DB7"}


# ── images ──────────────────────────────────────────────────────────────────

def load_inputs(job):
    """The three inputs on the same 2.5 m grid, in reflectance (0-1)."""
    s2 = job.open("stage2_sr.tif").astype("float32").load()
    s1 = job.open("stage1_sr.tif").astype("float32").load()
    lr = job.open("lr_reference.tif").astype("float32").load().rio.write_nodata(np.nan)
    lr = lr.rio.reproject_match(s2, resampling=Resampling.cubic)   # 10 m enlarged to 2.5 m
    valid = job.open("validity.tif", reflectance=False).load().values[0] > 0
    return {"Sentinel-2": lr, "Stage 1": s1, "Stage 2": s2}, valid


def rgb(da, ceiling=0.3):
    return np.clip(np.nan_to_num(np.moveaxis(da.sel(band=[1, 2, 3]).values, 0, -1)) / ceiling,
                   0, 1)


def window(arr, frac=0.4):
    """The middle part of an image (frac of each side), to zoom in."""
    h, w = arr.shape[:2]
    dy, dx = int(h * frac / 2), int(w * frac / 2)
    return arr[h // 2 - dy:h // 2 + dy, w // 2 - dx:w // 2 + dx]


# ── public reference maps ───────────────────────────────────────────────────

OPEN_BUILDINGS = ("https://data.source.coop/vida/google-microsoft-osm-open-buildings/"
                  "geoparquet/by_country/country_iso={iso}/{iso}.parquet")
ROAD_WIDTH_M = {"motorway": 12, "trunk": 10, "primary": 8, "secondary": 7, "tertiary": 6,
                "residential": 5, "unclassified": 5, "living_street": 4, "service": 4,
                "track": 3}


def _duckdb():
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial; "
                "SET s3_region = 'us-west-2';")
    return con


def _bbox_filter(bbox):
    w, s, e, n = bbox
    return f"bbox.xmin < {e} AND bbox.xmax > {w} AND bbox.ymin < {n} AND bbox.ymax > {s}"


def open_buildings(bbox, iso="PHL"):
    """Building footprints (Google, Microsoft and OpenStreetMap, combined by VIDA)."""
    df = _duckdb().execute(
        f"SELECT ST_AsWKB(geometry) AS wkb, bf_source AS source "
        f"FROM read_parquet('{OPEN_BUILDINGS.format(iso=iso)}') WHERE {_bbox_filter(bbox)}").df()
    return gpd.GeoDataFrame(df[["source"]], crs=4326,
                            geometry=gpd.GeoSeries.from_wkb(df["wkb"].apply(bytes)))


def overture_release():
    listing = httpx.get("https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/"
                        "?list-type=2&prefix=release/&delimiter=/", timeout=60).text
    return sorted(re.findall(r"<Prefix>release/([^<]+)/</Prefix>", listing))[-1]


def osm_roads(bbox):
    """Road centre lines from OpenStreetMap, via the Overture Maps transportation layer."""
    path = (f"s3://overturemaps-us-west-2/release/{overture_release()}/"
            f"theme=transportation/type=segment/*")
    df = _duckdb().execute(
        f"SELECT ST_AsWKB(geometry) AS wkb, class FROM read_parquet('{path}', "
        f"hive_partitioning = 1) WHERE subtype = 'road' AND {_bbox_filter(bbox)}").df()
    return gpd.GeoDataFrame(df[["class"]], crs=4326,
                            geometry=gpd.GeoSeries.from_wkb(df["wkb"].apply(bytes)))


def rasterize_like(gdf, like, buffer_m=None):
    """Burn shapes into a True/False map on the image grid. Lines are widened by buffer_m,
    which may be one number or a column name (half of it on each side)."""
    g = gdf.to_crs(like.rio.crs)
    if isinstance(buffer_m, str):
        geoms = [geom.buffer(w / 2) for geom, w in zip(g.geometry, g[buffer_m])]
    elif buffer_m:
        geoms = g.geometry.buffer(buffer_m / 2)
    else:
        geoms = g.geometry
    shape = (like.sizes["y"], like.sizes["x"])
    if len(geoms) == 0:
        return np.zeros(shape, bool)
    return rasterize(((geom, 1) for geom in geoms), out_shape=shape,
                     transform=like.rio.transform()).astype(bool)


def reference_maps(like):
    """Open Buildings and OpenStreetMap roads for the area of an image, on its grid."""
    bbox = transform_bounds(like.rio.crs, "EPSG:4326", *like.rio.bounds())
    buildings = open_buildings(bbox)
    roads = osm_roads(bbox)
    roads = roads[roads["class"].isin(ROAD_WIDTH_M)].copy()
    roads["width"] = roads["class"].map(ROAD_WIDTH_M)
    return {"buildings": rasterize_like(buildings, like),
            "roads": rasterize_like(roads, like, "width")}, buildings, roads


# ── the land-cover model ────────────────────────────────────────────────────

LC_CLASSES = ["bare land", "rangeland", "developed space", "road", "tree", "water",
              "agriculture", "building"]
LC_COLOURS = ["#800000", "#00FF24", "#949494", "#FFFFFF", "#226126", "#0045FF", "#4BB549",
              "#DE1F07"]   # the OpenEarthMap colours
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_landcover_model(url):
    from satlaspretrain_models.model import Model
    from satlaspretrain_models.utils import Backbone, Head

    path = Path(url) if Path(url).exists() else Path("landcover_model.pth")
    if not path.exists():
        print("downloading the model ...")
        torch.hub.download_url_to_file(url, str(path))
    state = torch.load(path, map_location="cpu")["model_state_dict"]
    model = Model(num_channels=3, multi_image=False, backbone=Backbone.SWINB, fpn=True,
                  head=Head.SEGMENT, num_categories=len(LC_CLASSES), weights=None)
    model.load_state_dict({k: v.float() for k, v in state.items()})
    return model.eval().to(DEVICE)


@torch.no_grad()
def landcover(model, da, patch=384, overlap=64, batch=4):
    """Class map (0-7, LC_CLASSES) of a 2.5 m image. The model reads red, green and blue
    reflectance; the image is cut into overlapping 960 m squares."""
    x = np.nan_to_num(da.sel(band=[1, 2, 3]).values).astype("float32")
    _, h, w = x.shape
    ys = sorted({*range(0, max(h - patch, 0), patch - overlap), max(h - patch, 0)})
    xs = sorted({*range(0, max(w - patch, 0), patch - overlap), max(w - patch, 0)})
    probs = np.zeros((len(LC_CLASSES), h, w), "float32")
    count = np.zeros((h, w), "float32")
    spots = [(y, x0) for y in ys for x0 in xs]
    for i in range(0, len(spots), batch):
        part = spots[i:i + batch]
        inp = torch.from_numpy(np.stack([x[:, y:y + patch, x0:x0 + patch] for y, x0 in part]))
        out = model(inp.to(DEVICE))[0].softmax(1).cpu().numpy()
        for (y, x0), p in zip(part, out):
            probs[:, y:y + patch, x0:x0 + patch] += p
            count[y:y + patch, x0:x0 + patch] += 1
    return (probs / count).argmax(0)


def show_landcover(maps, titles, size=4.6):
    fig, axes = plt.subplots(1, len(maps), figsize=(size * len(maps), size + 0.6),
                             squeeze=False)
    for ax, m, t in zip(axes[0], maps, titles):
        ax.imshow(m, cmap=ListedColormap(LC_COLOURS), vmin=0, vmax=len(LC_CLASSES) - 1,
                  interpolation="nearest")
        ax.set_title(t)
        ax.axis("off")
    fig.legend([Patch(facecolor=c, edgecolor="grey") for c in LC_COLOURS], LC_CLASSES,
               loc="lower center", ncol=8, fontsize=9, frameon=False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    plt.show()


# ── scoring ─────────────────────────────────────────────────────────────────

def scores(pred, ref, valid):
    p, r = pred[valid], ref[valid]
    tp, fp, fn = np.sum(p & r), np.sum(p & ~r), np.sum(~p & r)
    return {"F1": 2 * tp / max(2 * tp + fp + fn, 1), "IoU": tp / max(tp + fp + fn, 1),
            "precision": tp / max(tp + fp, 1), "recall": tp / max(tp + fn, 1)}


def show_errors(pred, ref, valid, title, ax):
    """Green: both say yes. Blue: false alarm (only the model). Red: missed (only the map)."""
    img = np.full(pred.shape + (3,), 0.12)
    img[pred & ref] = (0.10, 0.70, 0.30)
    img[pred & ~ref] = (0.20, 0.45, 0.95)
    img[~pred & ref] = (0.90, 0.20, 0.20)
    img[~valid] = 0
    ax.imshow(img, interpolation="nearest")
    ax.set_title(title)
    ax.axis("off")


def bar_chart(table, title):
    """table: rows = places, columns = inputs."""
    ax = table[INPUTS].plot.bar(color=[COLOURS[i] for i in INPUTS], figsize=(7, 3.6), rot=0,
                                width=0.75)
    for c in ax.containers:
        ax.bar_label(c, fmt="%.2f", fontsize=8)
    ax.set_ylabel("F1 (1 = perfect)")
    ax.set_title(title)
    ax.set_ylim(0, max(0.1, table[INPUTS].values.max() * 1.25))
    ax.legend(frameon=False, ncol=3, loc="upper left")
    plt.show()


# ── a model you train yourself ──────────────────────────────────────────────

def pixel_features(da):
    """Per-pixel features: the 4 bands, NDVI, edges and local averages/variation."""
    img = np.nan_to_num(da.values).astype("float32")
    red, nir = img[0], img[3]
    ndvi = (nir - red) / (nir + red + 1e-6)
    bright = img[:3].mean(0)
    feats = [*img, ndvi, ndi.gaussian_gradient_magnitude(bright, 1.5),
             ndi.gaussian_gradient_magnitude(bright, 4)]
    for size in (5, 11, 21):
        mean = ndi.uniform_filter(bright, size)
        sq = ndi.uniform_filter(bright ** 2, size)
        feats += [mean, np.sqrt(np.maximum(sq - mean ** 2, 0)), ndi.uniform_filter(ndvi, size)]
    return np.stack(feats, -1).reshape(-1, len(feats))


def train_and_test(da, ref, valid, n_train=60_000, seed=0):
    """Train on the west half, test on the east half (a 50 m gap between them).
    Returns the F1 on the east half and the predicted map."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import precision_recall_curve

    h, w = ref.shape
    cols = np.broadcast_to(np.arange(w), (h, w))
    train = (valid & (cols < w // 2 - 10)).ravel()
    test = (valid & (cols >= w // 2 + 10)).ravel()
    X, y = pixel_features(da), ref.ravel()
    rng = np.random.default_rng(seed)
    idx = rng.choice(np.flatnonzero(train), min(n_train, train.sum()), replace=False)
    clf = HistGradientBoostingClassifier(max_iter=150, random_state=seed).fit(X[idx], y[idx])
    # threshold that gives the best F1 on the training half
    pr, rc, th = precision_recall_curve(y[idx], clf.predict_proba(X[idx])[:, 1])
    f1 = 2 * pr * rc / np.maximum(pr + rc, 1e-9)
    thr = th[np.argmax(f1[:-1])]
    pred = (clf.predict_proba(X)[:, 1] >= thr).reshape(h, w)
    return scores(pred, ref, test.reshape(h, w))["F1"], pred


def decide(row, margin=0.02):
    best = max(INPUTS, key=lambda k: row[k])
    if best == "Sentinel-2" or row[best] - row["Sentinel-2"] < margin:
        return "Sentinel-2 is enough"
    if best == "Stage 1" or row["Stage 2"] - row["Stage 1"] < margin:
        return "use Stage 1"
    return "use Stage 2 (full model)"
''')

md(r"""
## 1. Super-resolved images for both places

Two 2 km squares. Both were run before the workshop, so they come back quickly and cost
nothing. The two jobs run one after the other.
""")
code(r"""
PLACES = {
    "Cebu City": dict(area=area_around(10.3300, 123.9200, km=2), date="2026-03-20"),
    "Nueva Ecija": dict(area=area_around(15.5784, 120.9726, km=2), date="2026-03-15"),
}
jobs = {}
for name, p in PLACES.items():
    jobs[name] = sr.submit(p["area"], p["date"])
    print(name, jobs[name].id)
for name, job in jobs.items():
    print(name)
    job.wait()
""")
code(r"""
images, valid = {}, {}
for name, job in jobs.items():
    images[name], valid[name] = load_inputs(job)
    for w in job.warnings:
        print(f"{name}: warning [{w['code']}] {w['message']}")

for name in PLACES:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    for ax, inp in zip(axes, INPUTS):
        ax.imshow(window(rgb(images[name][inp])), interpolation="nearest")
        ax.set_title(f"{name}: {inp}")
        ax.axis("off")
    fig.tight_layout()
    plt.show()
""")

md(r"""
## 2. Step 1, label: public reference maps

Session 3 used expert labels drawn by hand. Here we use two public maps that anyone can
download for any place in the Philippines:

* **Open Buildings**: building footprints from Google, Microsoft and OpenStreetMap, combined by
  VIDA (source.coop). They were themselves made by a model from 50 cm images, so they are good
  but not perfect.
* **OpenStreetMap roads**, through the Overture Maps transportation layer. Roads are lines, so
  we widen each one by a typical width for its class (12 m for a motorway down to 3 m for a
  farm track). Missing or misplaced roads in OpenStreetMap will count as errors of the model.
""")
code(r"""
refs, vectors = {}, {}
for name in PLACES:
    like = images[name]["Stage 2"]
    refs[name], b, r = reference_maps(like)
    vectors[name] = (b, r)
    print(f"{name}: {len(b):,} buildings ({refs[name]['buildings'].mean():.0%} of the area), "
          f"{len(r):,} road segments ({refs[name]['roads'].mean():.0%} of the area)")

fig, axes = plt.subplots(1, 2, figsize=(13, 6.5))
for ax, name in zip(axes, PLACES):
    ax.imshow(window(rgb(images[name]["Stage 2"])), interpolation="nearest")
    over = np.zeros(window(refs[name]["roads"]).shape + (4,))
    over[window(refs[name]["roads"])] = (1, 0.85, 0, 0.8)
    over[window(refs[name]["buildings"])] = (1, 0.2, 0.2, 0.6)
    ax.imshow(over, interpolation="nearest")
    ax.set_title(f"{name}: buildings (red) and roads (yellow)")
    ax.axis("off")
plt.tight_layout()
plt.show()
""")

md(r"""
## 3. Steps 2 and 3, train and apply: a land-cover model

We reuse a model that was **trained on real high-resolution images** and has never seen a
super-resolved image (the "reuse" path in Session 3). It starts from SatlasPretrain (Allen
Institute for AI) and was fine-tuned on OpenEarthMap, hand-labelled aerial and satellite
images from 44 countries. It labels each pixel as one of 8 classes, including **building** and
**road**. It is the model behind the road result in Session 3.
 The model file (180 MB) is downloaded from Hugging Face.
""")
code(r"""
LANDCOVER_URL = os.environ.get(
    "LANDCOVER_URL", "https://huggingface.co/adbsr-internal/satlas-downstream/"
                     "resolve/main/landcover_oem_satlas_swinb_fp16.pth")
model = load_landcover_model(LANDCOVER_URL)
print("running on", DEVICE)

maps = {}
for name in PLACES:
    t0 = time.time()
    maps[name] = {inp: landcover(model, images[name][inp]) for inp in INPUTS}
    print(f"{name}: 3 maps in {time.time() - t0:.0f} s")
""")
code(r"""
for name in PLACES:
    show_landcover([window(maps[name][inp]) for inp in INPUTS],
                   [f"{name}: map from {inp}" for inp in INPUTS])
""")

md(r"""
## 4. Step 4, score: how close is each map to the reference?

We compare the model's **building** and **road** classes with the reference maps, pixel by
pixel, as in Session 3: green where both say yes, blue for a false alarm (only the model),
red for a miss (only the reference). **F1** combines them: 0 = no overlap, 1 = perfect.
""")
code(r"""
rows = []
for name in PLACES:
    for task, cls in (("buildings", 7), ("roads", 3)):
        for inp in INPUTS:
            s = scores(maps[name][inp] == cls, refs[name][task], valid[name])
            rows.append({"place": name, "task": task, "input": inp, **s})
results = pd.DataFrame(rows)

for task in ("buildings", "roads"):
    table = results[results.task == task].pivot(index="place", columns="input", values="F1")
    bar_chart(table, f"{task.capitalize()}: land-cover model vs. the public map")
""")
code(r"""
for name, task, cls in (("Cebu City", "buildings", 7), ("Nueva Ecija", "roads", 3)):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    for ax, inp in zip(axes, INPUTS):
        f1 = results.query("place == @name and task == @task and input == @inp").F1.item()
        show_errors(window(maps[name][inp] == cls), window(refs[name][task]),
                    window(valid[name]), f"{name}, {task}: {inp} (F1 {f1:.2f})", ax)
    fig.legend([Patch(color=c) for c in ((0.1, 0.7, 0.3), (0.2, 0.45, 0.95), (0.9, 0.2, 0.2))],
               ["correct", "false alarm", "missed"], loc="lower center", ncol=3,
               frameon=False)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    plt.show()
""")

md(r"""
**What to look for.** On plain Sentinel-2 the model finds few buildings and almost no roads:
it was trained on sharp images, and a 10 m image does not look like what it learned. On the
super-resolved images it finds many more. This is the main result of Session 3 on our own
examples: super-resolution lets a model trained on real high-resolution images work on free
Sentinel-2.

The scores are lower than in Session 3 because the references here are public maps, not
expert labels, and because a pixel-by-pixel score punishes small shifts of a few metres.

## 5. Numbers for planning

Planners often need numbers for areas rather than single objects: how much of each district
is built up, green, or water (Session 3: "good uses"). Here are the class shares that each
map gives for the two places.
""")
code(r"""
shares = []
for name in PLACES:
    for inp in INPUTS:
        m = maps[name][inp][valid[name]]
        counts = np.bincount(m, minlength=len(LC_CLASSES)) / m.size
        shares.append({"place": name, "input": inp,
                       **{c: round(100 * v, 1) for c, v in zip(LC_CLASSES, counts)}})
shares = pd.DataFrame(shares).set_index(["place", "input"])
print("share of the area (%)")
shares
""")

md(r"""
For a screening map, we count the share of building pixels in 250 m squares and compare
with Open Buildings. A good screening map puts the dense and the empty squares in the right
places, even if single buildings are missed.
""")
code(r"""
CELL = 100   # pixels of 2.5 m: 250 m squares


def per_cell(mask, valid_mask):
    h, w = (s // CELL * CELL for s in mask.shape)
    m = mask[:h, :w].reshape(h // CELL, CELL, w // CELL, CELL).mean((1, 3))
    v = valid_mask[:h, :w].reshape(h // CELL, CELL, w // CELL, CELL).mean((1, 3))
    return np.where(v > 0.9, m, np.nan)


fig, axes = plt.subplots(2, 4, figsize=(15, 8.8))
for row, name in zip(axes, PLACES):
    truth = per_cell(refs[name]["buildings"], valid[name])
    vmax = np.nanmax(truth)
    row[0].imshow(truth, cmap="Reds", vmin=0, vmax=vmax)
    row[0].set_title(f"{name}: Open Buildings")
    for ax, inp in zip(row[1:], INPUTS):
        est = per_cell(maps[name][inp] == 7, valid[name])
        ok = np.isfinite(est) & np.isfinite(truth)
        r = np.corrcoef(est[ok], truth[ok])[0, 1]
        ax.imshow(est, cmap="Reds", vmin=0, vmax=vmax)
        ax.set_title(f"{inp}: r = {r:.2f}")
    for ax in row:
        ax.axis("off")
fig.suptitle("Share of building pixels per 250 m square (r: correlation with Open Buildings)")
fig.tight_layout(h_pad=2.5)
plt.show()
""")

md(r"""
## 6. Test it yourself: a model you train on each input

So far we **reused** a model trained on real high-resolution images. The other path in
Session 3 is to **train a model on the images you will use**. If you have labels, you can do
that for each input and see which one gives the best map. This is the test from the end of
Session 3:

1. **Label** a sample: here the public maps again.
2. **Make the inputs**: Sentinel-2, Stage 1, Stage 2.
3. **Score each input**: train a quick model on the west half of the area and score it on the
   east half, which it has not seen.
4. **Decide**: use super-resolution only if it beats Sentinel-2.

The model is deliberately simple (a gradient-boosted classifier on per-pixel colours,
textures and edges); it trains in seconds on a laptop.
""")
code(r"""
rows = []
for name in PLACES:
    for task in ("buildings", "roads"):
        row = {"place": name, "task": task}
        for inp in INPUTS:
            row[inp], _ = train_and_test(images[name][inp], refs[name][task], valid[name])
        row["decision"] = decide(row)
        rows.append(row)
own = pd.DataFrame(rows).set_index(["place", "task"])
own.style.format({k: "{:.2f}" for k in INPUTS})
""")

md(r"""
**Compare with section 4.** When the model is trained on each input, the gap between
Sentinel-2 and super-resolution is much smaller than when we reuse a model trained on real
high-resolution images, and sometimes plain Sentinel-2 is best. Part of what super-resolution gives is that it makes Sentinel-2 *look
like* the images such models were trained on. So:

* if a good model trained on high-resolution images exists for your task, super-resolution
  lets you run it on free Sentinel-2;
* if you train your own model anyway, test whether super-resolution helps before you pay for
  it: sometimes Stage 1 or plain Sentinel-2 is just as good.

## 7. Before you use a map

* **Check the warnings and the validity map** of every job (Demonstration 1, section 8).
  Near water, use Sentinel-2.
* **Spot-check** a sample of the map against a real image or a field visit before acting on
  it.
* **Use maps for areas, not single objects**: screening, planning, trends. Not for decisions
  about one household or one building.
* **Each map shows a period** (the images span ±45 days), not a single day.

## 8. For the hackathon: your own place and your own labels

Everything above works for any place and any labels:

* change `PLACES` in section 1 (keep each area at 2 km or less while you explore);
* replace the reference maps with your own: any polygons in a GeoDataFrame, for example
  drawn in QGIS and read with `gpd.read_file("my_labels.gpkg")`, then
  `rasterize_like(my_labels, images[name]["Stage 2"])`;
* re-run sections 4 to 6.
""")
code(r"""
# Example: your own labels for one place (uncomment and adapt)
# my_labels = gpd.read_file("my_labels.gpkg")              # polygons of the thing you map
# my_ref = rasterize_like(my_labels, images["Cebu City"]["Stage 2"])
# for inp in INPUTS:
#     f1, _ = train_and_test(images["Cebu City"][inp], my_ref, valid["Cebu City"])
#     print(f"{inp:<11} F1 {f1:.2f}")
""")

md(r"""
---
Results contain modified Copernicus Sentinel data. Building footprints: Google–Microsoft–OSM
Open Buildings by VIDA (ODbL). Roads: © OpenStreetMap contributors (ODbL), via Overture Maps.
Land-cover model: SatlasPretrain (Ai2) fine-tuned on OpenEarthMap; CC BY-NC-SA 4.0,
non-commercial use.
""")

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python",
                                 "name": "python3"},
                  "language_info": {"name": "python"}, "colab": {"provenance": []}}
nbf.write(nb, OUT)
print("wrote", OUT, len(cells), "cells")
