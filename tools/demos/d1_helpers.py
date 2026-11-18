import threading
import time
from datetime import date

import httpx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import rioxarray
import xarray as xr
from rasterio.enums import Resampling
from rasterio.warp import transform, transform_bounds
from rasterio.windows import from_bounds
from scipy.ndimage import binary_erosion

plt.rcParams.update({"figure.dpi": 100, "axes.titlesize": 11})
EARTH_SEARCH = "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/"


def manifest(job):
    """The job's manifest.json: scenes used per tile, parameters, cost, warnings."""
    return httpx.get(job.results()["files"]["manifest.json"], timeout=60).json()


def wait_for_stage(job, stage, poll_s=10):
    """Wait until a stage's result is published (stage 1 is published before stage 2)."""
    t0 = time.monotonic()
    while True:
        job.refresh()
        if job.status in ("failed", "cancelled"):
            raise RuntimeError(f"job {job.id} {job.status}: {job.info.get('error')}")
        try:
            if stage in job.results()["stages_done"]:
                print(f"\rstage {stage} ready after {(time.monotonic() - t0) / 60:.1f} min".ljust(60))
                return job
        except SRError as exc:
            if exc.status != 409:  # 409 = no result yet
                raise
        print(f"\r{job.status}, {(time.monotonic() - t0) / 60:.1f} min ...", end="", flush=True)
        time.sleep(poll_s)


def load(job, name):
    """A result file as an xarray DataArray in reflectance (0-1), read into memory."""
    return job.open(name).astype("float32").load()


def clip(da, lat, lon, km):
    """The km x km square around a point (works for 2.5 m and 10 m images alike)."""
    x0, y0, x1, y1 = transform_bounds("EPSG:4326", da.rio.crs, *area_around(lat, lon, km))
    return da.rio.clip_box(x0, y0, x1, y1)


def rgb(da, bands=(1, 2, 3), ceiling=0.3):
    """Natural colour (or any 3 bands) scaled for display: reflectance / ceiling."""
    a = np.moveaxis(da.sel(band=list(bands)).values, 0, -1)
    return np.clip(np.nan_to_num(a) / ceiling, 0, 1)


def show(images, titles, size=4.2, bands=(1, 2, 3), ceiling=0.3, suptitle=None):
    fig, axes = plt.subplots(1, len(images), figsize=(size * len(images), size + 0.4),
                             squeeze=False)
    for ax, img, title in zip(axes[0], images, titles):
        ax.imshow(rgb(img, bands, ceiling) if hasattr(img, "rio") else img,
                  interpolation="nearest")
        ax.set_title(title)
        ax.axis("off")
    if suptitle:
        fig.suptitle(suptitle, y=1.0)
    fig.tight_layout()
    plt.show()


def to_10m(da):
    """Average 4 x 4 pixels of a 2.5 m image: what Sentinel-2 would have seen."""
    return da.coarsen(x=4, y=4, boundary="trim").mean()


def enlarge(lr_da, like):
    """A 10 m image enlarged (bicubic) to the 2.5 m grid of ``like``."""
    return lr_da.rio.write_nodata(np.nan).rio.reproject_match(like, resampling=Resampling.cubic)


def agreement(sr_da, lr_da):
    """Correlation (0-1) between a 2.5 m image averaged to 10 m and the Sentinel-2 input,
    averaged over the 4 bands. 1 = the same pattern of light and dark."""
    a = to_10m(sr_da).values
    b = lr_da.values[:, :a.shape[1], :a.shape[2]]
    ok = np.isfinite(a).all(0) & np.isfinite(b).all(0)
    return float(np.mean([np.corrcoef(a[i][ok], b[i][ok])[0, 1] for i in range(4)]))


def detail(da):
    """How much fine detail an image has: the average brightness change from one pixel to
    the next (natural-colour bands)."""
    v = np.nan_to_num(da.sel(band=[1, 2, 3]).values.mean(0))
    return float(np.mean(np.abs(np.diff(v, axis=0))) + np.mean(np.abs(np.diff(v, axis=1))))


def scene_images(scene_ids, lat, lon, km):
    """Natural colour and cloud mask of each Sentinel-2 scene around a point, read straight
    from the public archive (Element 84 Earth Search, AWS)."""
    out = []
    for sid in scene_ids:
        item = httpx.get(EARTH_SEARCH + sid, timeout=60).json()
        with rasterio.open(item["assets"]["visual"]["href"]) as r:
            win = from_bounds(*transform_bounds("EPSG:4326", r.crs, *area_around(lat, lon, km)),
                              r.transform)
            img = np.moveaxis(r.read(window=win), 0, -1)
        with rasterio.open(item["assets"]["scl"]["href"]) as r:  # scene classification, 20 m
            win = from_bounds(*transform_bounds("EPSG:4326", r.crs, *area_around(lat, lon, km)),
                              r.transform)
            scl = r.read(1, window=win, out_shape=img.shape[:2], resampling=Resampling.nearest)
        # masked like the service does: everything but vegetation, bare soil, water and
        # "unclassified" (ESA scene classes 4-7), i.e. clouds, cirrus, shadows, no data
        masked = ~np.isin(scl, (4, 5, 6, 7))
        out.append((sid, img, masked))
    return out


def ndvi(da):
    """Vegetation index: (NIR - red) / (NIR + red)."""
    red, nir = da.sel(band=1), da.sel(band=4)
    return (nir - red) / (nir + red)


# ---- section 9: checking against real high-resolution images ----------------------------
SATELLOGIC = "https://satellogic-earthview.s3.us-west-2.amazonaws.com/data/tif"


def satellogic_scene(scene):
    """Date and centre (lat, lon) of a Satellogic EarthView scene, from its name."""
    d, _, _, zone, e, n = scene.split("_")
    epsg = (32600 if zone.endswith("N") else 32700) + int(zone[:-1])
    lon, lat = transform(f"EPSG:{epsg}", "EPSG:4326", [int(e) + 192], [int(n) - 192])
    return f"{d[:4]}-{d[4:6]}-{d[6:]}", lat[0], lon[0]


def load_satellogic(scene):
    """A Satellogic EarthView scene: 384 m x 384 m at 1 m; red, green, blue, NIR;
    top-of-atmosphere reflectance (0-1). Read from the public archive on AWS."""
    d, _, _, zone, e, n = scene.split("_")
    url = (f"{SATELLOGIC}/zone={zone}/region={e}_{n}/date={d[:4]}-{d[4:6]}-{d[6:]}/"
           f"{scene}_TOA.tif")
    da = rioxarray.open_rasterio(url).astype("float32").load()
    return da.where(da > 0) / 10000


def sentinel2_image(scene_id, like):
    """One Sentinel-2 image (red, green, blue, NIR, reflectance 0-1) on the 10 m grid of
    ``like``; clouds, shadows and no data are NaN."""
    item = httpx.get(EARTH_SEARCH + scene_id, timeout=60).json()
    props = item["properties"]
    offset = 0 if props.get("earthsearch:boa_offset_applied", True) else (
        -1000 if props.get("s2:processing_baseline", "00") >= "04.00" else 0)
    bands = []
    for name in ("red", "green", "blue", "nir", "scl"):
        da = rioxarray.open_rasterio(item["assets"][name]["href"])
        x0, y0, x1, y1 = like.rio.transform_bounds(da.rio.crs)
        da = da.rio.clip_box(x0 - 50, y0 - 50, x1 + 50, y1 + 50)
        bands.append(da.rio.reproject_match(like, resampling=Resampling.nearest)[0]
                     .astype("float32"))
    clear = np.isin(bands[4], (4, 5, 6, 7)) & (bands[0] > 0)
    out = xr.concat([(b + offset) / 10000 for b in bands[:4]], dim="band")
    out = out.assign_coords(band=[1, 2, 3, 4]).where(clear)
    return out.rio.write_crs(like.rio.crs).rio.write_transform(like.rio.transform())


def _corr(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() > 50 else np.nan


def _moved(da, dx, dy):
    """The same image moved dx metres east and dy metres north."""
    out = da.assign_coords(x=da.x + dx, y=da.y + dy)
    return out.rio.write_transform(out.rio.transform(recalc=True))


def _averaged_onto(vhr, like):
    """The 1 m image averaged onto the grid of ``like`` (10 m or 2.5 m)."""
    return vhr.rio.write_nodata(np.nan).rio.reproject_match(like, resampling=Resampling.average)


def _align(vhr, s2):
    """Shift (metres east, north) that best lines the 1 m image up with Sentinel-2 at 10 m:
    a search in 3 m steps, then 1 m steps around the best."""
    def fit(dx, dy):
        a = _averaged_onto(_moved(vhr, dx, dy), s2).values
        return np.nanmean([_corr(a[i], s2.values[i]) for i in range(4)])

    best = max(((dx, dy) for dx in range(-24, 25, 3) for dy in range(-24, 25, 3)),
               key=lambda s: fit(*s))
    return max(((best[0] + i, best[1] + j) for i in range(-2, 3) for j in range(-2, 3)),
               key=lambda s: fit(*s))


def _match_brightness(vhr, s2):
    """Fit each band of the 1 m image to Sentinel-2 at 10 m (a straight line per band)."""
    a = _averaged_onto(vhr, s2).values
    out = vhr.copy()
    for i in range(4):
        ok = np.isfinite(a[i]) & np.isfinite(s2.values[i])
        gain, offset = np.polyfit(a[i][ok], s2.values[i][ok], 1)
        out[i] = vhr[i] * gain + offset
    return out


def _nudge(product, ref):
    """Move a product by up to one 2.5 m pixel to where it best matches the reference:
    two satellites never line up to the metre."""
    def fit(s):
        q = np.roll(product.values, s, axis=(-2, -1))
        return np.nanmean([_corr(q[b], ref.values[b]) for b in range(4)])

    s = max(((i, j) for i in (-1, 0, 1) for j in (-1, 0, 1)), key=fit)
    q = np.roll(product.values, s, axis=(-2, -1))
    if s[0]:
        q[..., 0 if s[0] > 0 else -1, :] = np.nan   # the row that wrapped around
    if s[1]:
        q[..., :, 0 if s[1] > 0 else -1] = np.nan
    return product.copy(data=q)


def fine_part(x):
    """A 2.5 m image minus its own 10 m average: the detail smaller than a Sentinel-2 pixel."""
    h, w = (x.shape[-2] // 4) * 4, (x.shape[-1] // 4) * 4
    x = x[..., :h, :w]
    m = np.nanmean(x.reshape(*x.shape[:-2], h // 4, 4, w // 4, 4), axis=(-3, -1))
    return x - np.repeat(np.repeat(m, 4, -2), 4, -1)


def compare_with_vhr(job, scene):
    """Sentinel-2, Stage 1 and Stage 2 next to a real 1 m image of the same place, all on the
    2.5 m grid of the job and cut to the 1 m image's footprint."""
    day = satellogic_scene(scene)[0]
    lr, s1, s2 = (load(job, f) for f in ("lr_reference.tif", "stage1_sr.tif", "stage2_sr.tif"))
    sid, info = min(manifest(job)["scenes"].items(), key=lambda kv: abs(
        (date.fromisoformat(kv[1]["datetime"][:10]) - date.fromisoformat(day)).days))
    s2_day = sentinel2_image(sid, lr)
    vhr = load_satellogic(scene)
    dx, dy = _align(vhr, s2_day)
    ref = _averaged_onto(_match_brightness(_moved(vhr, dx, dy), s2_day), s1)
    foot = binary_erosion(np.isfinite(ref.values).all(0), iterations=1)
    ys, xs = np.where(foot)
    # start on a 10 m pixel (4 x 4 output pixels), so fine_part's blocks are Sentinel-2's
    cut = dict(y=slice(ys.min() // 4 * 4, ys.max() + 1), x=slice(xs.min() // 4 * 4, xs.max() + 1))
    ref = ref.where(foot).isel(**cut)
    s2_date = info["datetime"][:10]
    gap = (date.fromisoformat(s2_date) - date.fromisoformat(day)).days
    images = {f"Sentinel-2 ({'same day' if gap == 0 else f'{gap:+d} days'}), enlarged":
              enlarge(s2_day, s1), "Stage 1": s1, "Stage 2": s2}
    images = {k: _nudge(v.where(foot).isel(**cut), ref) for k, v in images.items()}
    images["Satellogic, 1 m averaged to 2.5 m"] = ref
    print(f"Satellogic {day}; Sentinel-2 {s2_date}; Satellogic image moved {dx:+d} m east, "
          f"{dy:+d} m north to line up with Sentinel-2")
    return images


def show_vhr(images, title):
    fig, axes = plt.subplots(3, 4, figsize=(15, 12.5), layout="constrained")
    for j, (name, da) in enumerate(images.items()):
        axes[0, j].imshow(rgb(da), interpolation="nearest")
        axes[0, j].set_title(name, fontsize=10)
        axes[1, j].imshow(da.sel(band=4).values, cmap="gray", vmin=0, vmax=0.5,
                          interpolation="nearest")
        im = axes[2, j].imshow(ndvi(da).values, cmap="RdYlGn", vmin=-0.2, vmax=0.8,
                               interpolation="nearest")
    for ax, label in zip(axes[:, 0], ["natural colour", "near-infrared", "NDVI"]):
        ax.text(-0.04, 0.5, label, transform=ax.transAxes, rotation=90, ha="right",
                va="center", fontsize=11)
    for ax in axes.ravel():
        ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=axes[2, :], orientation="horizontal", shrink=0.4, label="NDVI")
    fig.suptitle(title)
    plt.show()


def vhr_scores(images):
    """Correlation with the real image: all detail, and the detail smaller than 10 m."""
    ref = images["Satellogic, 1 m averaged to 2.5 m"]
    rows = {}
    for name, da in images.items():
        if da is ref:
            continue
        row = {}
        for label, idx in (("colour", [0, 1, 2]), ("NIR", [3])):
            row[f"{label}: all"] = np.mean([_corr(da.values[i], ref.values[i]) for i in idx])
            row[f"{label}: < 10 m"] = np.mean([_corr(fine_part(da.values[i]),
                                                     fine_part(ref.values[i])) for i in idx])
        a, b = ndvi(da).values, ndvi(ref).values
        row["NDVI: all"], row["NDVI: < 10 m"] = _corr(a, b), _corr(fine_part(a), fine_part(b))
        rows[name.split(" (")[0]] = row
    return pd.DataFrame(rows).T


class Sweep:
    """Submits several jobs one after another in the background, waiting whenever the key's
    queue is full, so the rest of the notebook can go on meanwhile.
    ``settings``: {name: (area, date, {parameters})}."""

    def __init__(self, settings):
        self.settings, self.jobs, self.errors = settings, {}, {}
        client = SRClient()  # its own connection, used only by the background thread

        def run():
            for name, (area, target_date, params) in settings.items():
                while True:
                    try:
                        self.jobs[name] = client.submit(area, target_date, **params)
                        break
                    except SRError as exc:
                        if exc.status == 429:  # queue full: try again shortly
                            time.sleep(15)
                            continue
                        self.errors[name] = exc.message
                        break

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def status(self):
        for name in self.settings:
            job = self.jobs.get(name)
            state = (self.errors.get(name) or ("waiting to submit" if job is None
                                               else job.refresh().status))
            print(f"  {name:<22} {state}")

    def wait(self):
        while self.thread.is_alive() or any(
                j.refresh().status not in ("done", "partial", "failed", "cancelled")
                for j in self.jobs.values()):
            done = sum(j.status in ("done", "partial") for j in self.jobs.values())
            print(f"\r{done}/{len(self.settings)} done ...", end="", flush=True)
            time.sleep(10)
        print(f"\r{sum(j.status in ('done', 'partial') for j in self.jobs.values())}/"
              f"{len(self.settings)} done".ljust(40))
        for name, msg in self.errors.items():
            print(f"  {name}: not submitted: {msg}")
        return self.jobs


# ---- the worksheet ("your turn") ---------------------------------------------------------

def choose_place(place, my_lat=None, my_lon=None, my_date=None):
    """(lat, lon, date) of a place from the list, or of your own point and date."""
    if place in PLACES:
        p = PLACES[place]
        print(f"{place}: {p['note']}")
        return p["lat"], p["lon"], p["date"]
    print(f"Your own place: {my_lat:.4f}, {my_lon:.4f} on {my_date}")
    return float(my_lat), float(my_lon), str(my_date)


def print_estimate(est):
    """What the free estimate says, in plain words. Returns True if the job can be sent."""
    print(f"{est['tiles']} tiles of 320 m, about ${est['estimated_usd']:.2f} if nothing was "
          f"computed before")
    print(f"{len(est['scenes'])} Sentinel-2 images found between {est['search_window'][0]} "
          f"and {est['search_window'][1]}")
    for w in est["warnings_likely"]:
        print("warning:", w["message"])
    for p in est["problems"]:
        print("CANNOT SEND THIS JOB:", p)
    if est["problems"]:
        print("Pick another place or date and run the cell again.")
    return not est["problems"]


def view(da, lat, lon, size_m=500, east_m=0, north_m=0):
    """A square of size_m metres; its centre is moved east_m and north_m from (lat, lon)."""
    lat2 = lat + north_m / 111_320
    lon2 = lon + east_m / (111_320 * np.cos(np.radians(lat)))
    return clip(da, lat2, lon2, size_m / 1000)


def show_inputs(job, lat, lon, target_date, km=0.5):
    """The 8 Sentinel-2 images the model used for the tile in the middle of the area, with
    the masked pixels (cloud, cirrus, shadow, no data) outlined in red."""
    m = manifest(job)
    target = date.fromisoformat(str(target_date))
    mid_r, mid_c = m["grid"]["height"] / 2, m["grid"]["width"] / 2
    tile = min(m["tiles"],
               key=lambda t: (t["row"] + 16 - mid_r) ** 2 + (t["col"] + 16 - mid_c) ** 2)
    scenes = scene_images(tile["scene_ids"], lat, lon, km)
    fig, axes = plt.subplots(1, len(scenes), figsize=(2.3 * len(scenes), 2.9), squeeze=False)
    for i, (ax, (sid, img, masked), d) in enumerate(zip(axes[0], scenes, tile["dates"]), 1):
        ax.imshow(img)
        if masked.any() and not masked.all():
            ax.contour(masked, levels=[0.5], colors="red", linewidths=0.8)
        days = (date.fromisoformat(d) - target).days
        note = (" (reference)" if i == 1
                else " (repeat)" if sid in tile["scene_ids"][:i - 1] else "")
        ax.set_title(f"{i}{note}\n{d}, {days:+d} days\n{masked.mean():.0%} masked", fontsize=8)
        ax.axis("off")
    fig.suptitle(f"The 8 images behind the middle of your area ({int(km * 1000)} m across)",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    plt.show()
    distinct = len(set(tile["scene_ids"]))
    print(f"{len(m['scenes'])} different images used over the whole area; "
          f"this tile uses {distinct} different ones" +
          ("" if distinct == len(tile["scene_ids"]) else " (some twice)"))
    return tile


WARNING_MEANING = {
    "water": "detail in shallow water and on reefs is not reliable; use Sentinel-2 there",
    "low_diversity": "some tiles had fewer than 4 different clear images: less real detail",
    "nodata": "parts of the area have no clear image at all and are empty",
    "haze": "some input images are hazy: colours may be washed out",
    "missing_tiles": "some tiles could not be computed",
}


def print_warnings(job):
    """The job's warnings in plain words (job.wait() prints the service's own text)."""
    if not job.warnings:
        print("warnings: none")
    for code in dict.fromkeys(w["code"] for w in job.warnings):
        print(f"in plain words, {code}: {WARNING_MEANING.get(code, 'see the message above')}")


def seed_difference(a, b):
    """Mean absolute difference of two images over the natural-colour bands."""
    return np.abs(a.sel(band=[1, 2, 3]) - b.sel(band=[1, 2, 3])).mean("band")


def result_card(g):
    """Everything for the debrief, from the notebook's variables (pass globals())."""
    def get(name, default="(not answered)"):
        v = g.get(name, default)
        return default if v in ("", None) else v

    lines = ["=" * 64, f"PLACE       {get('PLACE')}  ({get('DATE')})"]
    if "s1" in g and "lr" in g:
        lines.append(f"AGREEMENT   with Sentinel-2 at 10 m: Stage 1 {agreement(g['s1'], g['lr']):.2f}"
                     + (f", Stage 2 {agreement(g['s2'], g['lr']):.2f}" if "s2" in g else ""))
    if "job" in g:
        codes = [w["code"] for w in g["job"].warnings]
        lines.append(f"WARNINGS    {', '.join(codes) if codes else 'none'}")
    lines += ["-" * 64,
              f"Q1  clear images out of 8:        {get('Q1_CLEAR_IMAGES')}",
              f"    a cloud the mask missed:      {get('Q1_MISSED_CLOUD')}",
              f"Q2  new in Stage 1:               {get('Q2_NEW_IN_STAGE_1')}",
              f"Q3  Stage 2 got right:            {get('Q3_RIGHT')}",
              f"    Stage 2 got wrong:            {get('Q3_WRONG')}",
              f"Q4  my experiment:                {get('EXPERIMENT')}",
              f"    for a picture in a report:    {get('Q4_REPORT_PICTURE')}",
              f"    for counting buildings:       {get('Q4_COUNTING')}",
              "=" * 64]
    print("\n".join(lines))
