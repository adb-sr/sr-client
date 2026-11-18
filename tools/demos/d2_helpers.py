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

plt.rcParams.update({"figure.dpi": 100, "axes.titlesize": 11})
INPUTS = ["Sentinel-2", "Stage 1", "Stage 2"]
KEYS = {"Sentinel-2": "s2", "Stage 1": "stage1", "Stage 2": "stage2"}
COLOURS = {"Sentinel-2": "#a6a6a6", "Stage 1": "#7fbfdf", "Stage 2": "#007DB7"}
TASK_CLASS = {"buildings": 7, "roads": 3}
PIXEL_M = 2.5
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


def window(arr, size_m=2000, east_m=0, north_m=0):
    """A square of size_m metres cut from an image or map (last two axes are y, x); its
    centre is moved east_m and north_m from the middle of the area."""
    h, w = arr.shape[-2:]
    half = int(round(size_m / PIXEL_M / 2))
    cy = int(np.clip(h // 2 - north_m / PIXEL_M, half, h - half)) if 2 * half < h else h // 2
    cx = int(np.clip(w // 2 + east_m / PIXEL_M, half, w - half)) if 2 * half < w else w // 2
    return arr[..., max(cy - half, 0):cy + half, max(cx - half, 0):cx + half]


def rgb(img, ceiling=0.3):
    """Natural colour for display from a (4, y, x) reflectance image."""
    return np.clip(np.moveaxis(img[:3], 0, -1) / ceiling, 0, 1)


def _off(axes):
    for ax in np.ravel(axes):
        ax.set_xticks([])
        ax.set_yticks([])


# ---- looking -----------------------------------------------------------------------------

def show_inputs(place, size_m=1000, east_m=0, north_m=0):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    for ax, inp in zip(axes, INPUTS):
        ax.imshow(rgb(window(place.images[inp], size_m, east_m, north_m)),
                  interpolation="nearest")
        ax.set_title(inp + (" (10 m, enlarged)" if inp == "Sentinel-2" else " (2.5 m)"))
    _off(axes)
    fig.suptitle(f"{place.name}: {size_m} m across")
    fig.tight_layout()
    plt.show()


def show_reference(place, size_m=1000, east_m=0, north_m=0):
    """The public maps on top of the Stage 2 image: buildings red, roads yellow."""
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.imshow(rgb(window(place.images["Stage 2"], size_m, east_m, north_m)),
              interpolation="nearest")
    roads = window(place.refs["roads"], size_m, east_m, north_m)
    buildings = window(place.refs["buildings"], size_m, east_m, north_m)
    over = np.zeros(roads.shape + (4,))
    over[roads] = (1, 0.85, 0, 0.8)
    over[buildings] = (1, 0.2, 0.2, 0.6)
    ax.imshow(over, interpolation="nearest")
    ax.set_title(f"{place.name}: public maps (buildings red, roads yellow)")
    _off(ax)
    plt.show()


def show_landcover(place, size_m=1000, east_m=0, north_m=0):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.9))
    cmap = ListedColormap(place.class_colours)
    for ax, inp in zip(axes, INPUTS):
        ax.imshow(window(place.maps[inp], size_m, east_m, north_m), cmap=cmap, vmin=0,
                  vmax=len(place.classes) - 1, interpolation="nearest")
        ax.set_title(f"map from {inp}")
    _off(axes)
    fig.legend([Patch(facecolor=c, edgecolor="grey") for c in place.class_colours],
               place.classes, loc="lower center", ncol=8, fontsize=9, frameon=False)
    fig.suptitle(f"{place.name}: {size_m} m across")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    plt.show()


# ---- scoring -----------------------------------------------------------------------------

def scores(pred, ref, valid):
    p, r = pred[valid], ref[valid]
    tp, fp, fn = np.sum(p & r), np.sum(p & ~r), np.sum(~p & r)
    return {"F1": 2 * tp / max(2 * tp + fp + fn, 1), "found": tp / max(tp + fn, 1),
            "correct": tp / max(tp + fp, 1)}


def score_table(place):
    """F1 of each input for buildings and roads, plus the share of the reference that was
    found (recall) and the share of the model's pixels that are correct (precision)."""
    rows = []
    for task in TASK_CLASS:
        for inp in INPUTS:
            s = scores(place.prediction(task, inp), place.refs[task], place.valid)
            rows.append({"task": task, "input": inp, **{k: round(float(v), 2)
                                                        for k, v in s.items()}})
    return pd.DataFrame(rows).set_index(["task", "input"])


def show_scores(table, title):
    f1 = table["F1"].unstack("input")[INPUTS]
    ax = f1.plot.bar(color=[COLOURS[i] for i in INPUTS], figsize=(7, 3.6), rot=0, width=0.75)
    for c in ax.containers:
        ax.bar_label(c, fmt="%.2f", fontsize=8)
    ax.set_ylabel("F1 (1 = perfect)")
    ax.set_xlabel("")
    ax.set_title(title)
    ax.set_ylim(0, max(0.1, f1.values.max() * 1.25))
    ax.legend(frameon=False, ncol=3, loc="upper left")
    plt.show()


def best_input(table, task, margin=0.02):
    f1 = table["F1"][task]
    best = f1.idxmax()
    if f1[best] - f1["Sentinel-2"] < margin:
        return "no real difference"
    return best


def check_guess(table, guesses):
    for task, guess in guesses.items():
        result = best_input(table, task)
        mark = "as you guessed" if guess == result else f"you guessed: {guess}"
        f1 = table["F1"][task]
        print(f"{task:<10} best: {result:<18} ({mark});  F1 " +
              ", ".join(f"{i} {f1[i]:.2f}" for i in INPUTS))


def _error_image(pred, ref, valid):
    img = np.full(pred.shape + (3,), 0.12)
    img[pred & ref] = OK_COLOUR
    img[pred & ~ref] = FALSE_COLOUR
    img[~pred & ref] = MISS_COLOUR
    img[~valid] = 0
    return img


def show_errors(place, task, size_m=500, east_m=0, north_m=0):
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
        axes[1, j].imshow(_error_image(pred, ref, valid), interpolation="nearest")
        axes[1, j].set_title(f"{task} from {inp}: F1 here {scores(pred, ref, valid)['F1']:.2f}")
    _off(axes)
    fig.legend([Patch(color=c) for c in (OK_COLOUR, FALSE_COLOUR, MISS_COLOUR)],
               ["correct", "false alarm (only the model)", "missed (only the public map)"],
               loc="lower center", ncol=3, frameon=False)
    fig.suptitle(f"{place.name}, {task}: {size_m} m across", y=0.995)
    fig.tight_layout(rect=(0, 0.04, 1, 0.98), h_pad=1.5)
    plt.show()


# ---- from a map to a decision -----------------------------------------------------------

def per_square(mask, valid, square_m=250):
    """Share of 'yes' pixels in each square of square_m metres (NaN where data is missing)."""
    n = int(square_m / PIXEL_M)
    h, w = (s // n * n for s in mask.shape)
    m = mask[:h, :w].reshape(h // n, n, w // n, n).mean((1, 3))
    v = valid[:h, :w].reshape(h // n, n, w // n, n).mean((1, 3))
    return np.where(v > 0.9, m, np.nan)


def _top(values, k):
    order = np.argsort(-np.nan_to_num(values.ravel(), nan=-1))
    return set(order[:k].tolist())


def decision(place, task, budget=10, square_m=250, show=True):
    """You can visit ``budget`` squares. With each input, pick the squares where the model's
    map shows the most buildings (or roads). A pick is a hit if the square is truly among the
    ``budget`` densest according to the public map. Returns hits per input."""
    truth = per_square(place.refs[task], place.valid, square_m)
    n = int(np.isfinite(truth).sum())
    budget = min(budget, n)
    true_top = _top(truth, budget)
    hits, picks, corr = {}, {}, {}
    for inp in INPUTS:
        est = per_square(place.prediction(task, inp), place.valid, square_m)
        picks[inp] = _top(est, budget)
        hits[inp] = len(picks[inp] & true_top)
        ok = np.isfinite(est) & np.isfinite(truth)
        corr[inp] = float(np.corrcoef(est[ok], truth[ok])[0, 1])
    if show:
        fig, axes = plt.subplots(1, 4, figsize=(16, 4.6))
        vmax = np.nanmax(truth)
        axes[0].imshow(truth, cmap="Reds", vmin=0, vmax=vmax)
        axes[0].set_title(f"public map: share of {task}\n(black frames: the {budget} densest)")
        for idx in true_top:
            r, c = divmod(idx, truth.shape[1])
            axes[0].add_patch(Rectangle((c - .5, r - .5), 1, 1, fill=False, ec="k", lw=1.5))
        for ax, inp in zip(axes[1:], INPUTS):
            est = per_square(place.prediction(task, inp), place.valid, square_m)
            ax.imshow(est, cmap="Reds", vmin=0, vmax=max(vmax, np.nanmax(est)))
            for idx in picks[inp]:
                r, c = divmod(idx, truth.shape[1])
                ax.add_patch(Rectangle((c - .5, r - .5), 1, 1, fill=False, lw=2,
                                       ec="#1a9641" if idx in true_top else "#d7191c"))
            ax.set_title(f"{inp}: {hits[inp]} of {budget} picks are hits\n"
                         f"(pattern agreement r = {corr[inp]:.2f})")
        _off(axes)
        fig.suptitle(f"{place.name}: {square_m} m squares; green frame = hit, red = wasted visit")
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        plt.show()
        print(f"{n} squares of {square_m} m; you can visit {budget}. "
              f"Picking at random would give about {budget * budget / n:.1f} hits.")
        for inp in INPUTS:
            print(f"  {inp:<11} {hits[inp]:>2} hits of {budget}")
    return hits


# ---- all places --------------------------------------------------------------------------

def all_places(summary, value="F1"):
    """One table for all places: rows = place and task, columns = inputs."""
    rows = []
    for name, s in summary.items():
        for task in TASK_CLASS:
            rows.append({"place": name, "task": task,
                         **{inp: s["scores"][task][inp].get(value) for inp in INPUTS}})
    return pd.DataFrame(rows).set_index(["task", "place"]).sort_index()


def show_all_places(summary, value="F1", label="F1 (1 = perfect)"):
    table = all_places(summary, value)
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.2), sharey=True)
    for ax, task in zip(axes, TASK_CLASS):
        t = table.loc[task]
        t.index = [n.split(",")[0].replace(" office", "").replace(" headquarters", " HQ")
                   for n in t.index]
        t[INPUTS].plot.bar(ax=ax, color=[COLOURS[i] for i in INPUTS], rot=0, width=0.78,
                           legend=task == "buildings")
        for c in ax.containers:
            ax.bar_label(c, fmt="%.2f", fontsize=7)
        ax.set_title(task.capitalize())
        ax.set_xlabel("")
        ax.set_ylabel(label)
        ax.tick_params(axis="x", labelsize=8)
    axes[0].legend(frameon=False, ncol=3, loc="upper left")
    fig.tight_layout()
    plt.show()
    return table


def result_card(g):
    """Everything for the debrief, from the notebook's variables (pass globals())."""
    def get(name, default="(not answered)"):
        v = g.get(name, default)
        return default if v in ("", None) else v

    lines = ["=" * 68, f"PLACE     {get('PLACE')}"]
    if "table" in g:
        for task in TASK_CLASS:
            f1 = g["table"]["F1"][task]
            lines.append(f"F1        {task:<10} " + ", ".join(f"{i} {f1[i]:.2f}" for i in INPUTS))
    if "hits" in g:
        lines.append(f"DECISION  {get('TASK')}, {get('BUDGET')} squares: hits " +
                     ", ".join(f"{i} {g['hits'][i]}" for i in INPUTS))
    lines += ["-" * 68,
              f"my guess, buildings:     {get('GUESS_BUILDINGS')}",
              f"my guess, roads:         {get('GUESS_ROADS')}",
              f"rescued by SR:           {get('RESCUE')}",
              f"failure:                 {get('FAILURE')}",
              f"VERDICT for {get('VERDICT_FOR')}: {get('VERDICT')}",
              f"what would change it:    {get('WOULD_CHANGE_MY_MIND')}",
              "=" * 68]
    print("\n".join(lines))
