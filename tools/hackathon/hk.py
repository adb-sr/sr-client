# Helpers for the SSTA mini-hackathon notebooks.
# This file is pasted into a hidden cell of each notebook by build.py, so every notebook
# is self-contained. Edit it here, then re-run build.py.

import json
import os
import shutil
import sys
import time
import urllib.request
import zipfile
from functools import lru_cache
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch, Rectangle
from PIL import Image

# --------------------------------------------------------------------------- look

COLOURS = {"s2": "#9e9e9e", "stage1": "#8fd3b6", "stage2": "#1f8a70", "hr": "#007db7",
           "random": "#d9d9d9", "best": "#4d4d4d", "perfect": "#4d4d4d"}
SHORT = {"s2": "Sentinel-2", "stage1": "SR stage 1", "stage2": "SR stage 2",
         "hr": "Real high-res", "s2_10m": "Sentinel-2 as delivered (10 m)"}
HIT_C, MISS_C = "#1a9850", "#d73027"
plt.rcParams.update({"figure.dpi": 100, "font.size": 10, "axes.titlesize": 10,
                     "axes.spines.top": False, "axes.spines.right": False})

# --------------------------------------------------------------------------- data

DATA_ROOT = Path("/content/hackathon_data") if Path("/content").exists() else Path("hackathon_data")


def _fetch(url, dest, token=None):
    """Download url to dest with a simple progress line. url may also be a local path."""
    if not str(url).startswith(("http://", "https://")):
        shutil.copy(url, dest)
        return
    req = urllib.request.Request(url, headers={"User-Agent": "ssta-hackathon"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done, t0, last = 0, time.time(), 0.0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if time.time() - last > 2:
                last = time.time()
                pct = f"{done / total:.0%}" if total else ""
                print(f"\r  {done / 1e6:,.0f} MB {pct}   ", end="")
        print(f"\r  {done / 1e6:,.0f} MB in {time.time() - t0:.0f} s   ")


def get_task(task, base_url, extras=(), token=None):
    """Download and unzip <base_url>/<task>.zip (and optional extra zips) once; return a Task."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for name, required in [(task, True)] + [(e, False) for e in extras]:
        marker = DATA_ROOT / f".{name}.done"
        if marker.exists():
            continue
        url = f"{str(base_url).rstrip('/')}/{name}.zip"
        tmp = DATA_ROOT / f"{name}.zip"
        print(f"Downloading {name}.zip ...")
        try:
            _fetch(url, tmp, token)
            with zipfile.ZipFile(tmp) as z:
                z.extractall(DATA_ROOT)
            tmp.unlink()
            marker.touch()
        except Exception as e:  # extras are optional (e.g. restricted high-res images)
            if required:
                raise RuntimeError(f"Could not get {url}: {e}. Ask a facilitator.") from e
            print(f"  (skipped {name}: {e}; the notebook works without it)")
    return Task(DATA_ROOT / task)


class Task:
    def __init__(self, root):
        self.root = Path(root)
        self.meta = json.loads((self.root / "meta.json").read_text())
        self.inputs = [i["key"] for i in self.meta["inputs"]]
        self.labels = {i["key"]: i["label"] for i in self.meta["inputs"]}
        self.scenes = pd.DataFrame(self.meta["scenes"]).set_index("id")
        self.px = float(self.meta.get("pixel_m", 2.5))
        first = self.scenes.index[0]
        self.has_image = {k: (self.root / "img" / first / f"{k}.jpg").exists() for k in self.inputs}

    def __repr__(self):
        return f"<{self.meta['title']}: {len(self.scenes)} scenes, inputs {self.inputs}>"

    @lru_cache(maxsize=48)
    def _npz(self, sid):
        return np.load(self.root / "arr" / f"{sid}.npz")

    @lru_cache(maxsize=32)
    def arr(self, sid, key):
        """One array of a scene (decompressed once and kept; do not change it in place)."""
        return self._npz(sid)[key]

    def keys(self, sid):
        return self._npz(sid).files

    def img(self, sid, key, pre=False):
        """Display RGB (uint8) on the 2.5 m grid. key = an input or 's2_10m' (shown as 10 m blocks)."""
        suffix = "_pre" if pre else ""
        if key == "s2_10m":
            im = Image.open(self.root / "img" / sid / f"s2_10m{suffix}.png").convert("RGB")
            h, w = int(self.scenes.loc[sid, "h"]), int(self.scenes.loc[sid, "w"])
            return np.asarray(im.resize((w, h), Image.NEAREST))
        p = self.root / "img" / sid / f"{key}{suffix}.jpg"
        if not p.exists():
            return None
        return np.asarray(Image.open(p).convert("RGB"))

    @lru_cache(maxsize=24)
    def _view_u8(self, sid, key, stretch, pre):
        im = _view(self.img(sid, key, pre=pre), stretch)
        return None if im is None else (im * 255).round().astype(np.uint8)

    def view(self, sid, key, stretch="auto", pre=False):
        """The image as shown (contrast-stretched once per image and kept), floats 0-1."""
        im = self._view_u8(sid, key, stretch, pre)
        return None if im is None else im / 255.0


def autostretch(rgb, lo=2, hi=98):
    """Per-image contrast stretch for viewing only (the models saw the original values)."""
    if rgb is None:
        return None
    x = rgb.astype(np.float32)
    out = np.empty_like(x)
    for c in range(3):
        a, b = np.percentile(x[..., c], [lo, hi])
        out[..., c] = np.clip((x[..., c] - a) / max(b - a, 1), 0, 1)
    return out


def _view(rgb, stretch):
    return autostretch(rgb) if stretch == "auto" else (None if rgb is None else rgb / 255.0)


def _outline(mask):
    m = mask.astype(bool)
    edge = np.zeros_like(m)
    edge[1:, :] |= m[1:, :] != m[:-1, :]
    edge[:, 1:] |= m[:, 1:] != m[:, :-1]
    return edge & m


def _overlay(ax, mask, colour, alpha=1.0):
    rgba = np.zeros(mask.shape + (4,))
    rgba[mask] = list(plt.matplotlib.colors.to_rgb(colour)) + [alpha]
    ax.imshow(rgba, interpolation="nearest")


def _blank(ax, text="not available"):
    ax.text(0.5, 0.5, text, ha="center", va="center", color="#777", transform=ax.transAxes)
    ax.set_xticks([]), ax.set_yticks([])


# --------------------------------------------------------------------------- decisions

def expected_hits(score, hit, k):
    """Hits among the top-k by score. Ties at the cut-off are shared out at their hit rate,
    so a model that gives many places the same score is not lucky or unlucky by chance."""
    score = np.asarray(score, float)
    hit = np.asarray(hit, bool)
    k = min(int(k), len(score))
    if k == 0:
        return 0.0
    v = np.sort(score)[::-1][k - 1]
    above, tied = score > v, score == v
    return float(hit[above].sum() + (k - above.sum()) * hit[tied].mean())


def top_k(score, k, seed=0):
    """Indices of the top-k (ties broken at random, reproducibly)."""
    rng = np.random.default_rng(seed)
    jitter = rng.random(len(score)) * 1e-9
    return np.argsort(-(np.asarray(score, float) + jitter))[:k]


def decide(units, preds, hit, budget, cost_wasted=1.0, cost_missed=1.0, labels=None):
    """Score the decision 'visit the top <budget> places' for every input.

    units: DataFrame, one row per place.  preds: {input: array (n_models, n_places)}.
    hit: bool array, which places are worth visiting (from the reference labels).
    Returns a DataFrame with one row per input plus 'random' and 'perfect'."""
    hit = np.asarray(hit, bool)
    n_hit, n = int(hit.sum()), len(hit)
    k = min(int(budget), n)
    rows = []

    def row(name, hits_per_model):
        h = np.asarray(hits_per_model, float)
        m = h.mean()
        rows.append({
            "input": name,
            "hits": round(m, 1),
            "range over models": f"{h.min():.0f}–{h.max():.0f}" if len(h) > 1 else "",
            "hit rate": f"{m / k:.0%}" if k else "",
            "wasted visits": round(k - m, 1),
            "missed places": round(n_hit - m, 1),
            "cost": round((k - m) * cost_wasted + (n_hit - m) * cost_missed, 1),
        })

    for inp, p in preds.items():
        row(inp, [expected_hits(pm, hit, k) for pm in np.atleast_2d(p)])
    row("random", [k * n_hit / max(n, 1)])
    row("perfect", [min(k, n_hit)])
    out = pd.DataFrame(rows).set_index("input")
    if labels:
        out.index = [labels.get(i, i) for i in out.index]
    print(f"{n:,} places, {n_hit:,} of them are hits ({n_hit / max(n, 1):.0%}); budget {k}.")
    return out


def plot_decision(res, budget, title=""):
    names = list(res.index)
    keys = [next((k for k, v in SHORT.items() if v == nm or k == nm), nm) for nm in names]
    cols = [COLOURS.get(k, "#999") for k in keys]
    fig, ax = plt.subplots(figsize=(7, 0.45 * len(names) + 1))
    y = np.arange(len(names))[::-1]
    ax.barh(y, res["hits"], color=cols)
    for yi, v in zip(y, res["hits"]):
        ax.text(v + budget * 0.01, yi, f"{v:g}", va="center")
    ax.set_yticks(y, names)
    ax.set_xlim(0, budget * 1.12)
    ax.axvline(budget, color="#bbb", lw=1, ls="--")
    ax.set_xlabel(f"hits among the {budget} places you would visit")
    ax.set_title(title, loc="left")
    plt.tight_layout()
    return fig


def sweep(preds, hit, budgets=(5, 10, 20, 30, 50, 75, 100), labels=None, title=""):
    """Hit rate for a range of budgets: does the advantage of one input hold for small and large budgets?"""
    hit = np.asarray(hit, bool)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    budgets = [b for b in budgets if b <= len(hit)]
    for inp, p in preds.items():
        r = [np.mean([expected_hits(pm, hit, b) for pm in np.atleast_2d(p)]) / b for b in budgets]
        ax.plot(budgets, r, "o-", color=COLOURS.get(inp, "#999"), label=(labels or {}).get(inp, inp), lw=2)
    ax.plot(budgets, [hit.mean()] * len(budgets), "--", color="#999", label="random")
    ax.plot(budgets, [min(b, hit.sum()) / b for b in budgets], ":", color=COLOURS["best"], label="perfect")
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("budget (places visited)")
    ax.set_ylabel("share of visits that are hits")
    ax.set_title(title, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="center left", bbox_to_anchor=(1, 0.5))
    plt.tight_layout()
    plt.show()


def overlap_table(preds, k, labels=None, seed=0):
    """Share of the top-k places that two inputs have in common (first model of each)."""
    picks = {i: set(top_k(np.atleast_2d(p)[0], k, seed)) for i, p in preds.items()}
    names = list(picks)
    m = pd.DataFrame(index=names, columns=names, dtype=float)
    for a in names:
        for b in names:
            m.loc[a, b] = len(picks[a] & picks[b]) / max(k, 1)
    if labels:
        m.index = [labels.get(i, i) for i in names]
        m.columns = m.index
    try:
        return m.style.format("{:.0%}").background_gradient(cmap="Greens", vmin=0, vmax=1)
    except Exception:  # no jinja2: plain table
        return m.map(lambda v: f"{v:.0%}") if hasattr(m, "map") else m.applymap(lambda v: f"{v:.0%}")


def slide_numbers(res, scenario, budget, task_title, fname="my_slide_chart.png"):
    """Print the numbers for the team slide and save the bar chart as a PNG."""
    print(f"TASK: {task_title}")
    for k, v in scenario.items():
        print(f"{k.replace('_', ' ').upper()}: {v}")
    print()
    print(res[["hits", "range over models", "hit rate", "missed places", "cost"]].to_string())
    fig = plot_decision(res, budget, f"{scenario.get('decision', '')}")
    fig.savefig(fname, dpi=200, bbox_inches="tight")
    print(f"\nSaved {fname} (in Colab: Files panel on the left, right-click > Download).")


# --------------------------------------------------------------------------- informal settlements

def ifs_f1_table(task, thr=0.5):
    """Pixel F1 of the informal-settlement class per input, mean and spread over the task models."""
    acc = {}
    for sid in task.scenes.index:
        lab, val = task.arr(sid, "label"), task.arr(sid, "valid")
        v = val & (lab != 255)
        t = (lab == 1) & v
        for inp in task.inputs:
            p = task.arr(sid, f"prob_{inp}") >= thr * 255
            tp = (p & t).sum((1, 2))
            fp = (p & ~t & v).sum((1, 2))
            fn = (~p & t).sum((1, 2))
            a = acc.setdefault(inp, np.zeros((3, len(tp))))
            a += [tp, fp, fn]
    paper = {r["input"]: r.get("paper") for r in task.meta["metric_table"]}
    rows = []
    for inp, (tp, fp, fn) in acc.items():
        f1 = 2 * tp / np.maximum(2 * tp + fp + fn, 1) * 100
        rows.append({"input": task.labels[inp], "F1 % (mean)": round(f1.mean(), 1),
                     "lowest model": round(f1.min(), 1), "highest model": round(f1.max(), 1),
                     "paper": paper.get(inp)})
    return pd.DataFrame(rows).set_index("input")


def ifs_units(task, cell_m=100, thr=0.5, min_valid=0.8):
    """Cut every tile into square blocks of cell_m metres. For each block: the true informal share
    and, per input and task model, the share of the block the model flags as informal."""
    c = max(4, int(round(cell_m / task.px)))
    rows, preds = [], {inp: [] for inp in task.inputs}
    for sid in task.scenes.index:
        lab, val = task.arr(sid, "label"), task.arr(sid, "valid") & (task.arr(sid, "label") != 255)
        H, W = lab.shape
        ny, nx = H // c, W // c
        if ny == 0 or nx == 0:
            continue
        def blocks(a):
            return a[..., :ny * c, :nx * c].reshape(a.shape[:-2] + (ny, c, nx, c)).sum((-3, -1))
        nv = blocks(val.astype(np.float32))
        ninf = blocks(((lab == 1) & val).astype(np.float32))
        for inp in task.inputs:
            p = (task.arr(sid, f"prob_{inp}") >= thr * 255) & val
            preds[inp].append((blocks(p.astype(np.float32)) / np.maximum(nv, 1)).reshape(p.shape[0], -1))
        for iy in range(ny):
            for ix in range(nx):
                rows.append({"scene": sid, "group": task.scenes.loc[sid, "group"], "y0": iy * c,
                             "x0": ix * c, "size": c, "valid": nv[iy, ix] / c / c,
                             "truth": ninf[iy, ix] / max(nv[iy, ix], 1)})
    units = pd.DataFrame(rows)
    preds = {k: np.concatenate(v, axis=1) for k, v in preds.items()}
    keep = units["valid"].values >= min_valid
    units = units[keep].reset_index(drop=True)
    preds = {k: v[:, keep] for k, v in preds.items()}
    print(f"{len(units):,} blocks of {c * task.px:.0f} m x {c * task.px:.0f} m in {units.scene.nunique()} tiles")
    return units, preds


def ifs_show(task, sid, inputs=None, window=None, stretch="auto", model=None, thr=0.5,
             box=None, title=None):
    """Top row: the images. Bottom row: what the task model finds (orange) and the reference outline (black)."""
    inputs = inputs or ["s2_10m"] + task.inputs
    lab = task.arr(sid, "label")
    y0, x0, s = window or (0, 0, max(lab.shape))
    sl = (slice(y0, y0 + s), slice(x0, x0 + s))
    ref_edge = _outline(lab == 1)[sl]
    fig, axes = plt.subplots(2, len(inputs), figsize=(2.6 * len(inputs), 5.6), squeeze=False)
    for j, key in enumerate(inputs):
        ax, bx = axes[0, j], axes[1, j]
        im = task.view(sid, key, stretch)
        if im is None:
            _blank(ax, "image not\ndownloaded")
        else:
            ax.imshow(im[sl], interpolation="nearest")
        ax.set_title(SHORT.get(key, key))
        pkey = "s2" if key == "s2_10m" else key
        if key == "s2_10m":
            _blank(bx, "(the model sees the\nupsampled version)")
        else:
            prob = task.arr(sid, f"prob_{pkey}")
            p = (prob[model] if model is not None else prob.mean(0)) / 255.0
            bx.imshow(np.ones(p[sl].shape + (3,)))
            _overlay(bx, p[sl] >= thr, "#e6550d", 0.85)
            _overlay(bx, ref_edge, "black")
            if box:
                for b in (ax, bx):
                    b.add_patch(Rectangle((box[1] - x0 - .5, box[0] - y0 - .5), box[2], box[2],
                                          fill=False, ec="#d73027", lw=2))
        for b in (ax, bx):
            b.set_xticks([]), b.set_yticks([])
    axes[1, 0].set_ylabel("model output")
    fig.suptitle(title or f"{sid}  ({task.scenes.loc[sid, 'group']})", x=0.01, ha="left")
    fig.legend(handles=[Patch(color="#e6550d", label="flagged as informal (mean of models)"),
                        Patch(fc="white", ec="black", label="reference outline")],
               loc="lower center", ncol=2, frameon=False)
    plt.tight_layout(rect=(0, 0.04, 1, 1))
    plt.show()


def ifs_gallery(task, units, idx, key="stage2", stretch="auto", ctx=128, title="", hit=None):
    """Thumbnails of chosen blocks (with some context), framed green (hit) or red (not a hit)."""
    idx = list(idx)
    n = len(idx)
    cols = min(n, 8)
    rws = int(np.ceil(n / cols)) if n else 1
    fig, axes = plt.subplots(rws, cols, figsize=(1.9 * cols, 2.1 * rws), squeeze=False)
    for ax in axes.flat:
        ax.axis("off")
    for ax, i in zip(axes.flat, idx):
        u = units.iloc[i]
        im = task.view(u.scene, key, stretch)
        H, W = im.shape[:2]
        cy, cx = u.y0 + u["size"] // 2, u.x0 + u["size"] // 2
        y0 = int(np.clip(cy - ctx // 2, 0, max(H - ctx, 0)))
        x0 = int(np.clip(cx - ctx // 2, 0, max(W - ctx, 0)))
        ax.imshow(im[y0:y0 + ctx, x0:x0 + ctx])
        _overlay(ax, _outline(task.arr(u.scene, "label") == 1)[y0:y0 + ctx, x0:x0 + ctx], "black")
        good = bool(hit[i]) if hit is not None else None
        ax.add_patch(Rectangle((u.x0 - x0 - .5, u.y0 - y0 - .5), u["size"], u["size"], fill=False,
                               ec=HIT_C if good else MISS_C, lw=2.5))
        ax.set_title(f"true {u.truth:.0%}", fontsize=8)
    fig.suptitle(title, x=0.01, ha="left")
    plt.tight_layout()
    plt.show()


# --------------------------------------------------------------------------- building damage (xBD)

XBD_COLOURS = np.array([[0, 0, 0], [70, 130, 220], [240, 120, 20]], np.uint8) / 255.0


def xbd_metric_table(task):
    cm = {inp: np.zeros((3, 3), np.int64) for inp in task.inputs}
    for sid in task.scenes.index:
        lab, val = task.arr(sid, "label"), task.arr(sid, "valid")
        v = val & (lab != 255)
        t = lab[v].astype(np.int64)
        for inp in task.inputs:
            p = task.arr(sid, f"pred_{inp}")[v].astype(np.int64)
            cm[inp] += np.bincount(t * 3 + p, minlength=9).reshape(3, 3)
    paper = {(r["input"], r["metric"]): r.get("paper") for r in task.meta["metric_table"]}
    rows = []
    for inp, c in cm.items():
        iou = np.diag(c) / np.maximum(c.sum(0) + c.sum(1) - np.diag(c), 1)
        b_tp = c[1:, 1:].sum()
        b_f1 = 2 * b_tp / max(2 * b_tp + c[0, 1:].sum() + c[1:, 0].sum(), 1)
        d_f1 = 2 * c[2, 2] / max(2 * c[2, 2] + c[:, 2].sum() - c[2, 2] + c[2, :].sum() - c[2, 2], 1)
        rows.append({"input": task.labels[inp], "finds buildings (F1)": round(b_f1, 3),
                     "finds damaged buildings (F1)": round(d_f1, 3), "mIoU (3 classes)": round(iou.mean(), 3),
                     "paper building F1": paper.get((inp, "Building F1 (intact + damaged)"))})
    return pd.DataFrame(rows).set_index("input")


def xbd_units(task, event=None, target="damaged"):
    """One place = one xBD patch (~0.25 km2). truth = m2 of damaged (or all) buildings in the
    reference; prediction = m2 the model labels as damaged (or as any building)."""
    sc = task.scenes if event in (None, "all") else task.scenes[task.scenes.event == event]
    cls = (2,) if target == "damaged" else (1, 2)
    rows, preds = [], {inp: [] for inp in task.inputs}
    for sid, s in sc.iterrows():
        lab, val = task.arr(sid, "label"), task.arr(sid, "valid")
        v = val & (lab != 255)
        a = float(s.px_m_x) * float(s.px_m_y)
        rows.append({"scene": sid, "event": s.event, "valid": v.mean(),
                     "truth": np.isin(lab, cls)[v].sum() * a,
                     "buildings_m2": np.isin(lab, (1, 2))[v].sum() * a,
                     "damaged_m2": (lab == 2)[v].sum() * a})
        for inp in task.inputs:
            preds[inp].append(np.isin(task.arr(sid, f"pred_{inp}"), cls)[v].sum() * a)
    units = pd.DataFrame(rows)
    preds = {k: np.array(v)[None, :] for k, v in preds.items()}
    print(f"{len(units):,} patches" + (f" in {event}" if event not in (None, 'all') else ""))
    return units, preds


def xbd_show(task, sid, inputs=None, stretch="auto", title=None):
    """Rows: pre-event image, post-event image, model output (black background, blue intact,
    orange damaged). The last column of the bottom row is the reference."""
    inputs = inputs or task.inputs
    cols = inputs + ["reference"]
    fig, axes = plt.subplots(3, len(cols), figsize=(2.5 * len(cols), 7.8), squeeze=False)
    lab = task.arr(sid, "label")
    for j, key in enumerate(cols):
        if key == "reference":
            lab3 = np.where(lab == 255, 0, lab)
            rgb = XBD_COLOURS[lab3]
            rgb[lab == 255] = 0.35
            axes[2, j].imshow(rgb, interpolation="nearest")
            axes[2, j].set_title("reference")
            axes[0, j].axis("off"), axes[1, j].axis("off")
        else:
            for r, pre in ((0, True), (1, False)):
                im = task.view(sid, key, stretch, pre=pre)
                if im is None:
                    _blank(axes[r, j], "image not\ndownloaded")
                else:
                    axes[r, j].imshow(im)
            axes[0, j].set_title(SHORT.get(key, key))
            axes[2, j].imshow(XBD_COLOURS[task.arr(sid, f"pred_{key}")], interpolation="nearest")
        for r in range(3):
            axes[r, j].set_xticks([]), axes[r, j].set_yticks([])
    axes[0, 0].set_ylabel("before"), axes[1, 0].set_ylabel("after"), axes[2, 0].set_ylabel("model output")
    s = task.scenes.loc[sid]
    fig.suptitle(title or f"{sid}  (event start {s.event_start}; images after: S2 {s.s2_date}, "
                          f"high-res {s.hr_date})", x=0.01, ha="left")
    fig.legend(handles=[Patch(color=XBD_COLOURS[1], label="intact building"),
                        Patch(color=XBD_COLOURS[2], label="damaged building"),
                        Patch(color="#595959", label="not scored")], loc="lower center", ncol=3, frameon=False)
    plt.tight_layout(rect=(0, 0.03, 1, 1))
    plt.show()


def xbd_gallery(task, units, idx, key="stage2", stretch="auto", title="", hit=None):
    idx = list(idx)
    cols = min(len(idx), 8) or 1
    rws = int(np.ceil(len(idx) / cols)) or 1
    fig, axes = plt.subplots(rws, cols, figsize=(1.9 * cols, 2.1 * rws), squeeze=False)
    for ax in axes.flat:
        ax.axis("off")
    for ax, i in zip(axes.flat, idx):
        u = units.iloc[i]
        im = task.view(u.scene, key, stretch)
        if im is not None:
            ax.imshow(im)
        _overlay(ax, _outline(task.arr(u.scene, "label") == 2), "#f07814")
        good = bool(hit[i]) if hit is not None else None
        for s in ("left", "right", "top", "bottom"):
            ax.spines[s].set_visible(True)
        ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=False,
                               ec=HIT_C if good else MISS_C, lw=5))
        ax.set_title(f"{u.damaged_m2:,.0f} m2 damaged", fontsize=8)
    fig.suptitle(title, x=0.01, ha="left")
    plt.tight_layout()
    plt.show()


# --------------------------------------------------------------------------- field boundaries

def ai4_units(task, cell_m=500, small_m2=None, min_px=16, cache=True):
    """Cut every tile into square cells of cell_m metres and count, per cell, the fields whose
    centre lies in it: reference fields and the fields each model draws (one per seed).
    small_m2: count only fields smaller than this (None = all fields)."""
    c = max(8, int(round(cell_m / task.px)))
    key = f"units_{c}_{small_m2}_{min_px}.npz"
    cpath = task.root / key
    seeds = range(len(task.meta.get("models", [0, 1, 2])))
    if cache and cpath.exists():
        z = np.load(cpath, allow_pickle=True)
        units = pd.DataFrame(z["units"].tolist())
        return units, {k[5:]: z[k] for k in z.files if k.startswith("pred_")}
    a_px = task.px * task.px
    rows, preds = [], {inp: [] for inp in task.inputs}
    t0 = time.time()
    for sid in task.scenes.index:
        H, W = int(task.scenes.loc[sid, "h"]), int(task.scenes.loc[sid, "w"])
        ny, nx = H // c, W // c
        yy, xx = np.mgrid[0:H, 0:W]

        def counts(ids, min_px_):
            ids = ids.ravel().astype(np.int64)
            n = int(ids.max()) + 1
            cnt = np.bincount(ids, minlength=n)
            cy = np.bincount(ids, weights=yy.ravel(), minlength=n) / np.maximum(cnt, 1)
            cx = np.bincount(ids, weights=xx.ravel(), minlength=n) / np.maximum(cnt, 1)
            ok = (cnt >= min_px_) & (np.arange(n) > 0)
            if small_m2:
                ok &= cnt * a_px < small_m2
            iy, ix = (cy[ok] // c).astype(int), (cx[ok] // c).astype(int)
            inside = (iy < ny) & (ix < nx)
            return np.bincount(iy[inside] * nx + ix[inside], minlength=ny * nx)

        valid = task.arr(sid, "valid")
        vfrac = valid[:ny * c, :nx * c].reshape(ny, c, nx, c).mean((1, 3)).ravel()
        ref = counts(task.arr(sid, "fields_ref"), min_px)
        for inp in task.inputs:
            preds[inp].append(np.stack([counts(task.arr(sid, f"fields_{inp}_s{s}"), min_px) for s in seeds]))
        for i in range(ny * nx):
            rows.append({"scene": sid, "group": task.scenes.loc[sid, "group"], "y0": (i // nx) * c,
                         "x0": (i % nx) * c, "size": c, "valid": vfrac[i], "truth": int(ref[i])})
        print(f"\r  {sid} done ({time.time() - t0:.0f} s)   ", end="")
    print()
    units = pd.DataFrame(rows)
    preds = {k: np.concatenate(v, axis=1).astype(float) for k, v in preds.items()}
    if cache:
        np.savez(cpath, units=np.array(units.to_dict("records"), dtype=object),
                 **{f"pred_{k}": v for k, v in preds.items()})
    return units, preds


def ai4_tile_counts(task, small_m2=None, min_px=16):
    """Number of fields per tile: reference against each input (mean of the seeds)."""
    a_px = task.px * task.px
    seeds = range(len(task.meta.get("models", [0, 1, 2])))
    rows = []
    for sid in task.scenes.index:
        def n_fields(ids):
            cnt = np.bincount(ids.ravel().astype(np.int64))
            ok = (cnt >= min_px) & (np.arange(len(cnt)) > 0)
            if small_m2:
                ok &= cnt * a_px < small_m2
            return int(ok.sum())
        r = {"tile": sid, "reference": n_fields(task.arr(sid, "fields_ref"))}
        for inp in task.inputs:
            r[task.labels[inp]] = round(np.mean([n_fields(task.arr(sid, f"fields_{inp}_s{s}")) for s in seeds]))
        rows.append(r)
    df = pd.DataFrame(rows).set_index("tile")
    tot = df.sum()
    df.loc["ALL TILES"] = tot
    return df


def ai4_show(task, sid, y0=0, x0=0, size=400, inputs=None, stretch="auto", seed=0, title=None):
    """Top row: the images with the reference field outlines (red). Bottom row: the fields each
    model draws (seed 0), outlined, over its boundary probability."""
    inputs = inputs or ["s2_10m"] + task.inputs
    sl = (slice(y0, y0 + size), slice(x0, x0 + size))
    ref = task.arr(sid, "fields_ref")[sl]
    ref_edge = _boundaries(ref)
    fig, axes = plt.subplots(2, len(inputs), figsize=(3.1 * len(inputs), 6.4), squeeze=False)
    for j, key in enumerate(inputs):
        ax, bx = axes[0, j], axes[1, j]
        im = task.view(sid, key, stretch)
        ax.imshow(im[sl], interpolation="nearest")
        _overlay(ax, ref_edge, "#d73027", 0.9)
        ax.set_title(SHORT.get(key, key))
        if key == "s2_10m":
            _blank(bx, "(each input has its\nown trained model)")
        else:
            prob = task.arr(sid, f"prob_{key}_s0")[sl] / 255.0 if f"prob_{key}_s0" in task.keys(sid) else None
            if prob is not None:
                bx.imshow(prob, cmap="gray_r", vmin=0, vmax=2.5)  # light grey: boundary probability
            f = task.arr(sid, f"fields_{key}_s{seed}")[sl]
            _overlay(bx, _boundaries(f), "#1f8a70", 1)
            n = len(np.unique(f[f > 0]))
            bx.set_title(f"{n} fields drawn here", fontsize=9)
        for b in (ax, bx):
            b.set_xticks([]), b.set_yticks([])
    nref = len(np.unique(ref[ref > 0]))
    axes[1, 0].set_ylabel("model output")
    fig.suptitle(title or f"{sid}: {size * task.px / 1000:.1f} km window, {nref} reference fields",
                 x=0.01, ha="left")
    fig.legend(handles=[Patch(color="#d73027", label="reference field outlines"),
                        Patch(color="#1f8a70", label="fields the model draws")],
               loc="lower center", ncol=2, frameon=False)
    plt.tight_layout(rect=(0, 0.04, 1, 1))
    plt.show()


def _boundaries(ids):
    e = np.zeros(ids.shape, bool)
    e[1:, :] |= ids[1:, :] != ids[:-1, :]
    e[:, 1:] |= ids[:, 1:] != ids[:, :-1]
    return e


def ai4_gallery(task, units, idx, key="stage1", stretch="auto", title="", hit=None):
    idx = list(idx)
    cols = min(len(idx), 8) or 1
    rws = int(np.ceil(len(idx) / cols)) or 1
    fig, axes = plt.subplots(rws, cols, figsize=(1.9 * cols, 2.1 * rws), squeeze=False)
    for ax in axes.flat:
        ax.axis("off")
    for ax, i in zip(axes.flat, idx):
        u = units.iloc[i]
        sl = (slice(u.y0, u.y0 + u["size"]), slice(u.x0, u.x0 + u["size"]))
        ax.imshow(task.view(u.scene, key, stretch)[sl])
        _overlay(ax, _boundaries(task.arr(u.scene, "fields_ref")[sl]), "#d73027", 0.8)
        good = bool(hit[i]) if hit is not None else None
        ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=False,
                               ec=HIT_C if good else MISS_C, lw=5))
        ax.set_title(f"{u.truth} fields", fontsize=8)
    fig.suptitle(title, x=0.01, ha="left")
    plt.tight_layout()
    plt.show()
