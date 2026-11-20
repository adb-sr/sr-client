import json
import os
import re
import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch, Rectangle
from scipy import ndimage as ndi

plt.rcParams.update({"figure.dpi": 100, "axes.titlesize": 11})
INPUTS = ["Sentinel-2", "Stage 1", "Stage 2"]
KEYS = {"Sentinel-2": "s2", "Stage 1": "stage1", "Stage 2": "stage2"}
COLOURS = {"Sentinel-2": "#a6a6a6", "Stage 1": "#7fbfdf", "Stage 2": "#007DB7"}
TASK_CLASS = {"buildings": 7, "roads": 3}
PIXEL_M = 2.5
TOLERANCES = [0, 2.5, 5]   # metres: a pixel counts if the other map has one this close
TOLERANCE_M = 2.5          # the default
METRICS = ["F1", "IoU"]
OK_COLOUR, FALSE_COLOUR, MISS_COLOUR = (0.10, 0.70, 0.30), (0.20, 0.45, 0.95), (0.90, 0.20, 0.20)


# ---- the data package ---------------------------------------------------------------------

def _fetch(name, url, folder="demo2_data"):
    """A file of the data package: from a local folder, or downloaded once."""
    if Path(url).is_dir():
        return Path(url) / name
    path = Path(folder) / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading {name} ...")
        urllib.request.urlretrieve(f"{url.rstrip('/')}/{name}", path)
    return path


def get_summary(url):
    """Scores of every place (computed before the workshop)."""
    return json.loads(_fetch("summary.json", url).read_text())


class Place:
    """Everything about one place: the three images, the model's map of each, the public
    reference maps and the scores."""

    def __init__(self, name, url):
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        z = np.load(_fetch(f"{slug}.npz", url))
        self.name = name
        self.meta = json.loads(str(z["meta"]))
        self.images = {i: z[KEYS[i]].astype("float32") / 10000 for i in INPUTS}   # 4 bands, 0-1
        self.maps = {i: z[f"lc_{KEYS[i]}"] for i in INPUTS}                       # classes 0-7
        self.refs = {"buildings": z["ref_buildings"].astype(bool),
                     "roads": z["ref_roads"].astype(bool)}
        self.valid = z["valid"].astype(bool)
        self.classes = self.meta["classes"]
        self.class_colours = self.meta["class_colours"]
        self.size_m = self.valid.shape[0] * PIXEL_M

    def __repr__(self):
        m = self.meta
        return (f"{self.name}, {m['date']}: {self.size_m / 1000:.0f} km square, "
                f"{m['n_buildings']:,} buildings and {m['n_road_segments']:,} road segments "
                f"in the public maps" +
                (f"; warnings: {', '.join(m['warnings'])}" if m["warnings"] else ""))

    def prediction(self, task, inp):
        """True where the model's map from this input says 'building' (or 'road')."""
        return self.maps[inp] == TASK_CLASS[task]


def _centre(shape, size_m, east_m, north_m):
    """Centre (row, col) and half-width (pixels) of the view, kept inside the area."""
    h, w = shape[-2:]
    half = int(round(size_m / PIXEL_M / 2))
    cy = int(np.clip(h // 2 - north_m / PIXEL_M, half, h - half)) if 2 * half < h else h // 2
    cx = int(np.clip(w // 2 + east_m / PIXEL_M, half, w - half)) if 2 * half < w else w // 2
    return cy, cx, half


def window(arr, size_m=2000, east_m=0, north_m=0):
    """A square of size_m metres cut from an image or map (last two axes are y, x); its
    centre is moved east_m and north_m from the middle of the area."""
    cy, cx, half = _centre(arr.shape, size_m, east_m, north_m)
    return arr[..., max(cy - half, 0):cy + half, max(cx - half, 0):cx + half]


def rgb(img, ceiling=0.3):
    """Natural colour for display from a (4, y, x) reflectance image."""
    return np.clip(np.moveaxis(img[:3], 0, -1) / ceiling, 0, 1)


def _off(axes):
    for ax in np.ravel(axes):
        ax.set_xticks([])
        ax.set_yticks([])


# ---- figures (each returns a matplotlib figure) ------------------------------------------

def fig_locator(place, size_m, east_m, north_m):
    """The whole area, small, with a yellow frame around the current view."""
    cy, cx, half = _centre(place.valid.shape, size_m, east_m, north_m)
    fig, ax = plt.subplots(figsize=(2.4, 2.4))
    ax.imshow(rgb(place.images["Stage 2"][:, ::4, ::4]), interpolation="nearest",
              extent=(0, place.valid.shape[1], place.valid.shape[0], 0))
    ax.add_patch(Rectangle((cx - half, cy - half), 2 * half, 2 * half, fill=False,
                           ec="#ffd400", lw=2))
    ax.set_title("where you are", fontsize=9)
    _off(ax)
    fig.tight_layout()
    return fig


def fig_inputs(place, size_m=1000, east_m=0, north_m=0):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    for ax, inp in zip(axes, INPUTS):
        ax.imshow(rgb(window(place.images[inp], size_m, east_m, north_m)),
                  interpolation="nearest")
        ax.set_title(inp + (" (10 m, enlarged)" if inp == "Sentinel-2" else " (2.5 m)"))
    _off(axes)
    fig.suptitle(f"{place.name}: {size_m} m across")
    fig.tight_layout()
    return fig


def fig_landcover(place, size_m=1000, east_m=0, north_m=0):
    """Top: the three images. Bottom: the land-cover map the model drew from each."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 10.8))
    cmap = ListedColormap(place.class_colours)
    for j, inp in enumerate(INPUTS):
        axes[0, j].imshow(rgb(window(place.images[inp], size_m, east_m, north_m)),
                          interpolation="nearest")
        axes[0, j].set_title(inp)
        axes[1, j].imshow(window(place.maps[inp], size_m, east_m, north_m), cmap=cmap, vmin=0,
                          vmax=len(place.classes) - 1, interpolation="nearest")
        axes[1, j].set_title(f"map from {inp}")
    _off(axes)
    fig.legend([Patch(facecolor=c, edgecolor="grey") for c in place.class_colours],
               place.classes, loc="lower center", ncol=8, fontsize=10, frameon=False)
    fig.suptitle(f"{place.name}: {size_m} m across", y=0.995)
    fig.tight_layout(rect=(0, 0.04, 1, 0.98), h_pad=3.0)
    return fig


def fig_reference(place, size_m=2000, east_m=0, north_m=0):
    """The public maps on top of the Stage 2 image: buildings red, roads yellow."""
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(rgb(window(place.images["Stage 2"], size_m, east_m, north_m)),
              interpolation="nearest")
    roads = window(place.refs["roads"], size_m, east_m, north_m)
    buildings = window(place.refs["buildings"], size_m, east_m, north_m)
    over = np.zeros(roads.shape + (4,))
    over[roads] = (1, 0.85, 0, 0.8)
    over[buildings] = (1, 0.2, 0.2, 0.6)
    ax.imshow(over, interpolation="nearest")
    ax.set_title("the public maps: buildings red, roads yellow")
    _off(ax)
    fig.tight_layout()
    return fig


# ---- scoring -----------------------------------------------------------------------------

def tol_text(metres):
    return "pixel-exact" if metres == 0 else f"within {metres:g} m"


def tol_key(metres):
    return f"{metres:g}"


def near(mask, metres=TOLERANCE_M, pixel_m=PIXEL_M):
    """True wherever ``mask`` has a pixel within ``metres``."""
    r = int(round(metres / pixel_m))
    if r == 0:
        return mask
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return ndi.binary_dilation(mask, structure=x * x + y * y <= r * r)


def from_shares(found, correct):
    """F1 and IoU from the two shares. IoU = F1 / (2 - F1): always lower than F1, same order."""
    f1 = 2 * found * correct / max(found + correct, 1e-9)
    return {"F1": f1, "IoU": f1 / (2 - f1)}


def scores(pred, ref, valid, metres=TOLERANCE_M):
    """found: share of the reference's pixels with a model pixel within ``metres``;
    correct: share of the model's pixels with a reference pixel within ``metres``;
    F1 and IoU combine the two (0 = nothing right, 1 = perfect)."""
    found = np.sum(ref & near(pred, metres) & valid) / max(np.sum(ref & valid), 1)
    correct = np.sum(pred & near(ref, metres) & valid) / max(np.sum(pred & valid), 1)
    return {**from_shares(found, correct), "found": found, "correct": correct}


def everywhere(place, task, metres=TOLERANCE_M):
    """Scores of a useless map that says 'building' (or 'road') everywhere: the line a real
    map has to beat. In a dense city it is high, because most places are near a building."""
    s = scores(np.ones_like(place.valid), place.refs[task], place.valid, metres)
    return {m: float(s[m]) for m in METRICS}


def score_table(place, metres=TOLERANCE_M):
    """F1 and IoU of each input for buildings and roads, plus the share of the reference that
    was found (recall) and the share of the model's pixels that are correct (precision)."""
    rows = []
    for task in TASK_CLASS:
        for inp in INPUTS:
            s = scores(place.prediction(task, inp), place.refs[task], place.valid, metres)
            rows.append({"task": task, "input": inp, **{k: round(float(v), 2)
                                                        for k, v in s.items()}})
    table = pd.DataFrame(rows).set_index(["task", "input"])
    table.attrs["everywhere"] = {t: everywhere(place, t, metres) for t in TASK_CLASS}
    table.attrs["metres"] = metres
    return table


def _bars(ax, values, inputs, base=None, metric="F1", metres=TOLERANCE_M, legend=True):
    """Grouped bars: rows of ``values`` = groups on the x axis, columns = inputs."""
    values[inputs].plot.bar(ax=ax, color=[COLOURS[i] for i in inputs], rot=0, width=0.78,
                            legend=False)
    for c in ax.containers:
        ax.bar_label(c, fmt="%.2f", fontsize=7.5)
    if base is not None:
        for k, b in enumerate(base):
            if b is not None:
                ax.hlines(b, k - 0.42, k + 0.42, colors="k", linestyles="--", lw=1.2,
                          label="a map that says yes everywhere" if k == 0 else None)
    ax.set_ylabel(f"{metric} (1 = perfect)\n{tol_text(metres)}")
    ax.set_xlabel("")
    ax.set_ylim(0, 1.12)
    if legend:
        ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=8)


def fig_scores(table, title, metric="F1"):
    vals = table[metric].unstack("input")[INPUTS].loc[list(TASK_CLASS)]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    base = [table.attrs["everywhere"][t][metric] for t in vals.index]
    _bars(ax, vals, INPUTS, base, metric, table.attrs["metres"])
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    return fig


def best_input(table, task, metric="F1", margin=0.02):
    v = table[metric][task]
    best = v.idxmax()
    if v[best] - v["Sentinel-2"] < margin:
        return "no real difference"
    return best


def guess_lines(table, guesses, metric="F1"):
    """Was the guess right? One line per task."""
    lines = []
    for task, guess in guesses.items():
        result = best_input(table, task, metric)
        if guess in (None, ""):
            mark = "you did not guess"
        else:
            mark = "as you guessed ✓" if guess == result else f"you guessed: {guess}"
        v = table[metric][task]
        base = table.attrs["everywhere"][task][metric]
        lines.append(f"{task:<10} best: {result:<18} ({mark})   {metric} " +
                     ", ".join(f"{i} {v[i]:.2f}" for i in INPUTS) +
                     f";  saying yes everywhere: {base:.2f}")
    return lines


def _error_image(pred, ref, valid, metres=TOLERANCE_M):
    """Green: right (within ``metres`` of the other map). Blue: false alarm (only the
    model). Red: missed (only the public map)."""
    near_pred, near_ref = near(pred, metres), near(ref, metres)
    img = np.full(pred.shape + (3,), 0.12)
    img[ref & ~near_pred] = MISS_COLOUR
    img[pred & ~near_ref] = FALSE_COLOUR
    img[(pred & near_ref) | (ref & near_pred)] = OK_COLOUR
    img[~valid] = 0
    return img


def fig_errors(place, size_m=500, east_m=0, north_m=0, task="buildings", metres=TOLERANCE_M,
               metric="F1"):
    """Top: the three images. Bottom: the model's map of each against the public map.
    Green: correct. Blue: false alarm (only the model). Red: missed (only the public map)."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 10.6))
    valid = window(place.valid, size_m, east_m, north_m)
    ref = window(place.refs[task], size_m, east_m, north_m)
    for j, inp in enumerate(INPUTS):
        axes[0, j].imshow(rgb(window(place.images[inp], size_m, east_m, north_m)),
                          interpolation="nearest")
        axes[0, j].set_title(inp)
        pred = window(place.prediction(task, inp), size_m, east_m, north_m)
        axes[1, j].imshow(_error_image(pred, ref, valid, metres), interpolation="nearest")
        here = scores(pred, ref, valid, metres)[metric]
        axes[1, j].set_title(f"{task} from {inp}: {metric} here {here:.2f}")
    _off(axes)
    fig.legend([Patch(color=c) for c in (OK_COLOUR, FALSE_COLOUR, MISS_COLOUR)],
               [f"right ({tol_text(metres)})", "false alarm (only the model)",
                "missed (only the public map)"],
               loc="lower center", ncol=3, frameon=False)
    fig.suptitle(f"{place.name}, {task}: {size_m} m across", y=0.995)
    fig.tight_layout(rect=(0, 0.04, 1, 0.98), h_pad=3.0)
    return fig


# ---- the model at home: OpenEarthMap -------------------------------------------------------

OEM_INPUTS = ["aerial", *INPUTS]
COLOURS["aerial"] = "#3a3a3a"


def get_oem(url):
    """The land-cover model on 79 hand-labelled OpenEarthMap tiles (scores and 3 examples)."""
    oem = json.loads(_fetch("oem_reference.json", url).read_text())
    oem["ex"] = dict(np.load(_fetch("oem_examples.npz", url)))
    return oem


def oem_table(oem, metres=TOLERANCE_M):
    s = oem["scores"][tol_key(metres)]
    rows = [{"task": t, "input": i, **{k: round(v, 2) for k, v in s[t][i].items()}}
            for t in TASK_CLASS for i in OEM_INPUTS]
    table = pd.DataFrame(rows).set_index(["task", "input"])
    table.attrs["everywhere"] = {t: s[t]["everywhere"] for t in TASK_CLASS}
    table.attrs["metres"] = metres
    return table


def fig_oem_scores(oem, metric="F1", metres=TOLERANCE_M):
    table = oem_table(oem, metres)
    vals = table[metric].unstack("input")[OEM_INPUTS].loc[list(TASK_CLASS)]
    fig, ax = plt.subplots(figsize=(8.5, 3.9))
    base = [table.attrs["everywhere"][t][metric] for t in vals.index]
    _bars(ax, vals, OEM_INPUTS, base, metric, metres)
    ax.set_title(f"At home: {oem['n_tiles']} hand-labelled OpenEarthMap tiles in "
                 f"{len(oem['cities'])} cities", fontsize=10)
    fig.tight_layout()
    return fig


def fig_oem_example(oem, i=0):
    """One OpenEarthMap tile: hand-drawn labels, the four images, and the map from each."""
    ex, colours = oem["ex"], oem["class_colours"]
    cmap = ListedColormap(["#000000", *colours])
    fig, axes = plt.subplots(2, 5, figsize=(17, 7.4))
    axes[0, 0].imshow(ex[f"{i}_label"], cmap=cmap, vmin=0, vmax=8, interpolation="nearest")
    axes[0, 0].set_title("drawn by hand (the truth)")
    for j, inp in enumerate(OEM_INPUTS, start=1):
        axes[0, j].imshow(ex[f"{i}_{inp}"], interpolation="nearest")
        axes[0, j].set_title(inp + (" image (0.5 m)" if inp == "aerial" else ""))
        axes[1, j].imshow(ex[f"{i}_map_{inp}"], cmap=cmap, vmin=0, vmax=8,
                          interpolation="nearest")
        axes[1, j].set_title(f"map from {inp}")
    axes[1, 0].axis("off")
    axes[1, 0].legend([Patch(facecolor=c, edgecolor="grey") for c in colours],
                      oem["classes"][1:], loc="center", fontsize=10, frameon=False)
    _off(axes)
    name = str(ex["names"][i])
    fig.suptitle(f"OpenEarthMap tile {name.rsplit('_', 1)[0].replace('_', ' ').title()}, "
                 "500 m across", y=0.995)
    fig.tight_layout(h_pad=2.5)
    return fig


# ---- all places --------------------------------------------------------------------------

def all_places(summary, value="F1", metres=TOLERANCE_M):
    """One table for all places: rows = place and task, columns = inputs."""
    rows = []
    for name, s in summary.items():
        sc = s["scores"][tol_key(metres)]
        for task in TASK_CLASS:
            rows.append({"place": name, "task": task,
                         **{inp: sc[task][inp].get(value) for inp in INPUTS}})
    return pd.DataFrame(rows).set_index(["task", "place"]).sort_index()


def _short(name):
    return name.split(",")[0].replace(" office", "").replace(" headquarters", " HQ")


def fig_all_places(summary, metric="F1", metres=TOLERANCE_M, own_model=False):
    """Bars for every place; dashed: a map that says yes everywhere."""
    value = f"own_model_{metric}" if own_model else metric
    table = all_places(summary, value, metres)
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.2), sharey=True)
    for ax, task in zip(axes, TASK_CLASS):
        t = table.loc[task]
        base = None if own_model else [
            summary[n]["scores"][tol_key(metres)][task]["everywhere"][metric] for n in t.index]
        t.index = [_short(n) for n in t.index]
        _bars(ax, t, INPUTS, base, metric, metres, legend=task == "buildings")
        ax.set_title(task.capitalize() + (" (a model trained on each input)" if own_model else ""))
        ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    return fig


def show_all_places(summary, metric="F1", metres=TOLERANCE_M):
    plt.show(fig_all_places(summary, metric, metres))
    return all_places(summary, metric, metres)
