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


def reference_maps(like, iso="PHL"):
    """Open Buildings and OpenStreetMap roads for the area of an image, on its grid."""
    bbox = transform_bounds(like.rio.crs, "EPSG:4326", *like.rio.bounds())
    buildings = open_buildings(bbox, iso)
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
