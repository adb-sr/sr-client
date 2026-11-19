"""Builds notebooks/demo1_super_resolution.ipynb: the presenter's walkthrough for Practical
demonstration 1 (Part A, about 15 minutes) plus the deeper material (Part B).

    python tools/demos/build_demo1.py
"""
from pathlib import Path

import nbformat as nbf

from places import EXPERIMENTS, PLACES, PRESENTER_CHECKS, PRESENTER_DIALS, as_code

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "notebooks" / "demo1_super_resolution.ipynb"
cells = []


def md(s):
    cells.append(nbf.v4.new_markdown_cell(s.strip("\n")))


def code(s, hidden=False):
    c = nbf.v4.new_code_cell(s.strip("\n"))
    if hidden:
        c.metadata["cellView"] = "form"
    cells.append(c)


md(r"""
# Practical demonstration 1: the super-resolution service

*SSTA workshop, 26 November 2026. Goes with Session 2, "ADB's approach to super-resolution".*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo1_super_resolution.ipynb)

**This is the walkthrough the presenter shows** (about 15 minutes). You do not need to run
it now: watch, and then make an image of a place you know with the short worksheet,
[`demo1_your_turn.ipynb`](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo1_your_turn.ipynb).
This notebook stays online if you want to go through it later.

**Part A: how to use the service** (shown in the session)

1. **Search**: which Sentinel-2 images exist for an area and a date? (free)
2. **Send a job**, and the options you can set.
3. **The inputs and Stage 1**: 8 images combined into one 2.5 m image.
4. **Stage 2**: the diffusion step adds detail.
5. **What comes with every result**: files, quality flags, sources and cost.

**Part B: going deeper** (for later)

6. **The two dials**: how much noise (Dial 1) and how many steps (Dial 2).
7. **Sharp or truthful?** Measuring what the model adds.
8. **Near-infrared**: the fourth band, and a vegetation index.
9. **Checking against real high-resolution images**: colour, near-infrared and NDVI.

**You need** an API key (`srk_...`) and the service URL, both handed out at the workshop.
Run the cells from top to bottom with **Shift + Enter**. The super-resolution runs on the
service's GPUs, so Colab needs no GPU. The example area was run before the workshop, so its
jobs cost nothing; the whole notebook takes about 15 minutes to run.
""")

md("# Part A: how to use the service\n\n## 0. Setup")
code(r"""
%pip install -q "sr-client[geo,viz] @ git+https://github.com/adb-sr/sr-client@v0.1.0"
""")

md(r"""
Your API key starts with `srk_`. In Colab you can store it under **Secrets** (the key icon
on the left) as `SR_API_KEY`, and the URL as `SR_API_URL`; otherwise the cell asks for them.
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
me = sr.me()
print(f"Key {me['prefix']} ({me['owner']}): up to {me['limits']['max_area_km']} km per side, "
      f"${me['budget']['remaining_usd']:.2f} of budget left")
""")

md(r"""
The service runs one model, `sen4x-v2`. It has the two stages from the slides, and the
diffusion step has the two dials: `tau` (τ, how much noise is added, Dial 1) and `nfe`
(the number of steps, Dial 2).
""")
code(r"""
model = sr.models()[0]
print(model["name"])
for stage, what in model["stages"].items():
    print(f"  stage {stage}: {what}")
print("dials:", {k: v for k, v in model["params"].items() if k in ("tau", "nfe")})
""")

code('# @title Helper functions (run this cell; you do not need to read it) { display-mode: "form" }\n'
     + (HERE / "d1_helpers.py").read_text() + "\n\n"
     + as_code("PLACES", {k: {f: v[f] for f in ("lat", "lon", "date", "note")}
                          for k, v in PLACES.items()})
     + as_code("EXPERIMENTS", EXPERIMENTS), hidden=True)

md(r"""
## 1. Search: which Sentinel-2 images are there?

`area_around(lat, lon, km)` makes a square around a point. The example is a 2 km square
over Cebu City and Mandaue. March is in the dry season, so there are few clouds.

The estimate is free. It shows how many tiles the area needs (squares of 320 m, the size the
model works on), what it would cost, and
every Sentinel-2 image the service found. It searches **45 days before and after** the date
and keeps images with **less than 40 % cloud** over the whole Sentinel-2 tile. (For the
training data we searched ±180 days, Session 2; a shorter window makes the result describe a
shorter period. You can change it with `time_window`.)
""")
code(r"""
LAT, LON = 10.3300, 123.9200     # Cebu City and Mandaue
DATE = "2026-03-20"              # dry season
area = area_around(LAT, LON, km=2)

est = sr.estimate(area, DATE)
print(f"{est['tiles']} tiles, about ${est['estimated_usd']:.2f}; "
      f"{len(est['scenes'])} Sentinel-2 images between {est['search_window'][0]} and "
      f"{est['search_window'][1]}")
for w in est["warnings_likely"]:
    print("warning:", w["message"])
for p in est["problems"]:
    print("cannot submit:", p)
""")

md(r"""
## 2. Send a job, and the options

`sr.submit(area, date)` sends the job. Both stages run by default; stage 1 is published
first, after about a minute. Everything else is optional:

| Option | Default | What it does |
|---|---|---|
| `stages` | `["1", "2"]` | `["1"]` is fast and cheap; add Stage 2 later with `job.upgrade()` |
| `time_window` | 45 days before and after | how far from the date the search may go |
| `max_cloud` | 40 | skip images with more cloud than this (%, whole Sentinel-2 tile) |
| `tau` | 250 | Dial 1: how much noise Stage 2 adds (10 to 999) |
| `nfe` | same as `tau` | Dial 2: in how many steps the noise is removed |
| `seed` | 0 | the random noise; same inputs and same seed give the same image |

Example: `sr.submit(area, DATE, tau=500, seed=1)`.

We send the job now and look at the inputs while it runs. We also start the experiments for
Part B (the dials) in the background: seven small jobs over a 1 km square in the middle of
the area. They wait in the queue behind the main job.
""")
code(r"""
job = sr.submit(area, DATE)     # stage 1 + stage 2 with the default dials (tau = nfe = 250)
print("job", job.id, job.status)

SMALL = area_around(LAT, LON, km=1)
DIALS = {
    "tau 100":            dict(tau=100),
    "tau 250":            dict(tau=250),
    "tau 500":            dict(tau=500),
    "tau 999":            dict(tau=999),
    "tau 250, 10 steps":  dict(tau=250, nfe=10),
    "tau 250, 50 steps":  dict(tau=250, nfe=50),
    "tau 250, seed 1":    dict(tau=250, seed=1),
}
sweep = Sweep({name: (SMALL, DATE, p) for name, p in DIALS.items()})
""")

md(r"""
## 3. The inputs, and Stage 1

As soon as stage 1 is ready, the job's manifest lists which Sentinel-2 images were used for
each tile. Below, each dot is one image that the search found. The height of a dot is **how
much of our area is under cloud or cloud shadow in that image**, according to ESA's scene
classification. The filled dots were used; the grey ones were too cloudy over this area or
not needed.

The search in section 1 can only filter on the cloud cover of the whole Sentinel-2 tile
(110 km across), which says little about a 2 km area. So the service then looks at each
image over each 320 m tile and keeps the clearest ones closest to the date. That is why an
image that is mostly cloudy over the area can still be used: for the tiles where it is clear.

(Cebu lies where two Sentinel-2 tiles overlap, so most satellite passes were found twice.
Their dots lie on top of each other, and the service uses one copy.)
""")
code(r"""
wait_for_stage(job, "1")
m = manifest(job)

target = date.fromisoformat(DATE)
used = set(m["scenes"])
cloudy = cloud_over_area([s["id"] for s in est["scenes"]], area)   # read from the archive

fig, ax = plt.subplots(figsize=(10, 3.2))
for s in est["scenes"]:
    d = (date.fromisoformat(s["date"][:10]) - target).days
    ax.scatter(d, 100 * cloudy[s["id"]], s=60,
               color="#007DB7" if s["id"] in used else "none",
               edgecolors="#007DB7" if s["id"] in used else "grey")
ax.axvline(0, color="k", ls=":")
ax.set_ylim(-5, 105)
ax.set_xlabel(f"days from {DATE}")
ax.set_ylabel("cloud and shadow\nover our area (%)")
ax.set_title(f"{len(est['scenes'])} images found, {len(used)} used (filled)")
plt.show()
""")

md(r"""
### The 8 images behind one place

For each 320 m tile the model gets 8 images, the clearest and closest in time. Here are the 8
for the tile in the middle of the area (500 m around it), read straight from the public
Sentinel-2 archive.

* Pixels outlined in red are **masked**: ESA's scene classification marks them as cloud,
  cirrus or shadow. They are filled from the other images. The classification misses some
  thin clouds and haze; look for them.
* Image 1 is the **reference**: the output follows its geometry and colours.
* If there are fewer than 8 different clear images, some are used twice (marked "repeat").
""")
code(r"""
# the tile nearest the middle of the area (row/col: its corner, in 10 m pixels; 32 px wide)
mid_r, mid_c = m["grid"]["height"] / 2, m["grid"]["width"] / 2
tile = min(m["tiles"], key=lambda t: (t["row"] + 16 - mid_r) ** 2 + (t["col"] + 16 - mid_c) ** 2)
scenes = scene_images(tile["scene_ids"], LAT, LON, km=0.5)

fig, axes = plt.subplots(1, len(scenes), figsize=(2.3 * len(scenes), 2.8))
for i, (ax, (sid, img, masked), d) in enumerate(zip(axes, scenes, tile["dates"]), 1):
    ax.imshow(img)
    if masked.any():
        ax.contour(masked, levels=[0.5], colors="red", linewidths=0.8)
    days = (date.fromisoformat(d) - target).days
    note = " (reference)" if i == 1 else " (repeat)" if sid in tile["scene_ids"][:i - 1] else ""
    ax.set_title(f"{i}{note}\n{days:+d} days", fontsize=9)
    ax.axis("off")
plt.tight_layout()
plt.show()
""")

md(r"""
### Stage 1: 8 images combined into one

Stage 1 combines the 8 images into one image with 2.5 m pixels. It is sharper than one
Sentinel-2 image, but still blurry. `lr_reference.tif` is the Sentinel-2 input on the same
area: the per-pixel average of the images the model saw, at 10 m.
""")
code(r"""
lr = load(job, "lr_reference.tif")
s1 = load(job, "stage1_sr.tif")

show([clip(lr, LAT, LON, 0.6), clip(s1, LAT, LON, 0.6)],
     ["Sentinel-2, 10 m", "Stage 1, 2.5 m"], size=5.5)
""")

md(r"""
**Stage 1 adds nothing that is not in the images.** One way to check: average each 4 × 4
block of Stage 1 back to one 10 m pixel. If Stage 1 only rearranges what the satellite
measured, this should look like the Sentinel-2 input again.

The agreement number is a correlation: 1 means the same pattern of light and dark at 10 m.
Expect a high but not perfect value: on our test areas it was 0.83 to 0.93 over cities and
0.74 to 0.77 over farmland. The Sentinel-2 input here is the average of 8 dates, and
Stage 1 makes one sharp image from them; fields that change between the dates probably
explain most of the gap over farmland.
""")
code(r"""
show([clip(lr, LAT, LON, 0.6), clip(to_10m(s1), LAT, LON, 0.6)],
     ["Sentinel-2, 10 m", "Stage 1, averaged back to 10 m"], size=5.5)
print(f"agreement with Sentinel-2: {agreement(s1, lr):.2f}")
""")

md(r"""
## 4. Stage 2: the diffusion step adds detail

Stage 2 adds noise to the Stage 1 image and then removes it step by step. While removing the
noise, the model draws the small details it learned from 1.8 million high-resolution images
(Session 2).
""")
code(r"""
job.wait()
s2 = load(job, "stage2_sr.tif")
job.show()     # the whole 2 km area, both stages
""")
code(r"""
show([clip(lr, LAT, LON, 0.5), clip(s1, LAT, LON, 0.5), clip(s2, LAT, LON, 0.5)],
     ["Sentinel-2, 10 m", "Stage 1", "Stage 2"], size=4.6, suptitle="500 m in the middle")
print(f"agreement with Sentinel-2: Stage 1 {agreement(s1, lr):.2f}, "
      f"Stage 2 {agreement(s2, lr):.2f}")
print(f"fine detail:               Stage 1 {detail(s1):.4f}, Stage 2 {detail(s2):.4f}")
""")

md(r"""
## 5. What comes with every result

Every job returns the images and the information you need to judge them:

| File | What it holds |
|---|---|
| `stage1_sr.tif`, `stage2_sr.tif` | the 2.5 m images: red, green, blue, NIR; reflectance × 10,000 |
| `lr_reference.tif` | the Sentinel-2 input, 10 m |
| `validity.tif` | 0 no data · 1 valid · 2 low diversity (fewer than 4 different clear images) |
| `manifest.json` | the images used for every tile, the settings, model versions, cost |

**Warnings** never stop a job, but read them: `water` (super-resolution erases detail in
shallow water and reefs; use the Sentinel-2 input there), `low_diversity`, `nodata` and
`haze`.
""")
code(r"""
validity = job.open("validity.tif", reflectance=False).load()
fig, ax = plt.subplots(figsize=(5, 5))
ax.imshow(validity.values[0], cmap=plt.matplotlib.colors.ListedColormap(
    ["black", "#cfe8f3", "orange"]), vmin=0, vmax=2, interpolation="nearest")
ax.set_title("validity: black no data, blue valid, orange low diversity")
ax.axis("off")
plt.show()

print("warnings:", [w["code"] for w in job.warnings] or "none")
print("model:", m["model"])
print("cost:", m["cost"])
print(m["attribution"])
""")

md(r"""
Download the files to open them in QGIS or ArcGIS. In Colab they appear in the file browser
on the left, under `sr_results/<job id>/`. Links last 7 days; the files are kept for 30
days.
""")
code(r"""
paths = job.download("sr_results")
for name, path in paths.items():
    print(f"  {path}  ({path.stat().st_size / 1e6:.1f} MB)")
print(f"budget left: ${sr.me()['budget']['remaining_usd']:.2f}")
""")

md(r"""
## Your turn

That is the whole service: an area and a date in, images and their quality information out.
Now open the worksheet and make an image of a place you know:
[`demo1_your_turn.ipynb`](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo1_your_turn.ipynb).

---
# Part B: going deeper

The rest of this notebook is for later. It uses the jobs that were started in the background
in section 2.
""")

md(r"""
## 6. The two dials

The seven background jobs from section 2 should be done or nearly done. When they are, the
cell starts three more for section 9 in the background.
""")
code(r"""
sweep.status()
dial_jobs = sweep.wait()

# section 9: one job per real high-resolution image, on the day it was taken (1 km each)
CHECKS = {
    "Ningbo, China: houses, gardens and greenhouses": "20220808_022419_SN18_51N_361530_3312762",
    "near Yangon, Myanmar: factories":                "20221106_044416_SN27_47N_204846_1870691",
    "near Faisalabad, Pakistan: farmland":            "20221206_095550_SN22_43N_329899_3480761",
}
checks = Sweep({place: (area_around(lat, lon, km=1), day, {})
                for place, (day, lat, lon) in
                ((p, satellogic_scene(s)) for p, s in CHECKS.items())})
""")

md(r"""
### Dial 1: how much noise (τ)

τ sets how much noise Stage 2 adds before removing it, from 0 (Stage 1 only) to 999 (almost
only noise). Little noise keeps the image close to what the satellite measured; much noise
lets the model draw more of its own detail. By default the number of steps equals τ.
""")
code(r"""
small = {name: load(j, "stage2_sr.tif") for name, j in dial_jobs.items()}
small["Stage 1"] = load(dial_jobs["tau 250"], "stage1_sr.tif")
lr_small = load(dial_jobs["tau 250"], "lr_reference.tif")

order = ["Stage 1", "tau 100", "tau 250", "tau 500", "tau 999"]
show([clip(small[k], LAT, LON, 0.25) for k in order],
     ["τ = 0 (Stage 1 only)", "τ = 100", "τ = 250", "τ = 500", "τ = 999"], size=3.2,
     suptitle="Dial 1: 250 m in the middle")
""")

md(r"""
### Dial 2: how many steps

The details appear step by step, so the number of steps (`nfe`) also controls how sharp the
result is. Fewer steps are faster and cheaper: the cost of Stage 2 grows with the number of
steps.
""")
code(r"""
order = ["Stage 1", "tau 250, 10 steps", "tau 250, 50 steps", "tau 250"]
show([clip(small[k], LAT, LON, 0.25) for k in order],
     ["Stage 1", "10 steps", "50 steps", "250 steps"], size=3.6,
     suptitle="Dial 2 at τ = 250: 250 m in the middle")

print("cost of each 1 km job (USD; $0 when the result was already computed before):")
for name, j in dial_jobs.items():
    print(f"  {name:<22} {j.refresh().info['cost']['actual_usd'] or 0:.3f}")
""")

md(r"""
## 7. Sharp or truthful?

Session 2 showed the trade-off: more detail, but the detail is less certain. We can measure
both sides on our own images:

* **agreement with Sentinel-2** (section 3): averaged back to 10 m, does the image still match
  what the satellite measured?
* **fine detail**: how much the brightness changes from one pixel to the next.

Look at how far each setting moves along the two axes compared with Stage 1. In our run of
this example, going from Stage 1 to τ = 999 almost doubled the fine detail (0.016 to 0.030)
while the agreement fell only from 0.88 to 0.82. Note what the agreement check *cannot* see: detail smaller than 10 m. Any detail the model draws below that
size is invisible to Sentinel-2, so it cannot be checked against it. The next experiment
shows where that detail is.
""")
code(r"""
rows = [("Stage 1", "Stage 1"), ("τ = 100", "tau 100"), ("τ = 250", "tau 250"),
        ("τ = 500", "tau 500"), ("τ = 999", "tau 999"),
        ("τ = 250, 10 steps", "tau 250, 10 steps"), ("τ = 250, 50 steps", "tau 250, 50 steps")]
pts = [(label, agreement(small[k], lr_small), detail(small[k])) for label, k in rows]
bicubic = enlarge(lr_small, small["Stage 1"])   # plain Sentinel-2, enlarged to 2.5 m
pts.append(("Sentinel-2, enlarged", agreement(bicubic, lr_small), detail(bicubic)))

fig, ax = plt.subplots(figsize=(8, 5))
for label, a, d in pts:
    ax.scatter(a, d, s=50, color="grey" if label.startswith("Sentinel") else "#007DB7")
    left = "steps" in label   # these sit close to τ = 100: label them on the left
    ax.annotate(label, (a, d), textcoords="offset points", xytext=(-8 if left else 8, 4),
                ha="right" if left else "left", fontsize=9)
ax.set_xlabel("agreement with Sentinel-2  (more truthful →)")
ax.set_ylabel("fine detail  (sharper →)")
plt.show()
for label, a, d in pts:
    print(f"  {label:<22} agreement {a:.3f}   detail {d:.4f}")
""")

md(r"""
### Same input, different seed

The noise that Stage 2 adds is random. The `seed` fixes it: the same seed always gives the
same result. With another seed, the parts that come from the satellite stay the same, and
the parts the model drew change. The difference map shows **where the model invented
detail**.
""")
code(r"""
a, b = small["tau 250"], small["tau 250, seed 1"]
diff = np.abs(a.sel(band=[1, 2, 3]) - b.sel(band=[1, 2, 3])).mean("band")
show([clip(a, LAT, LON, 0.25), clip(b, LAT, LON, 0.25)], ["seed 0", "seed 1"], size=4.6)

fig, ax = plt.subplots(figsize=(4.6, 4.6))
ax.imshow(clip(diff, LAT, LON, 0.25).values, cmap="magma",
          vmin=0, vmax=0.05)
ax.set_title("difference between the seeds")
ax.axis("off")
plt.show()
print(f"pixels that differ by more than 0.02 reflectance: {float((diff > 0.02).mean()):.0%}")
""")

md(r"""
**What this means for users.** Large shapes (blocks, wide roads, fields) are stable; small
things (single roofs, cars, textures) can change from seed to seed. In our run of this
example, about a third of the pixels changed by more than 0.02 reflectance, mostly on roofs
and between buildings. Use super-resolved images
for questions about areas, and do not trust a single small object without checking it
(Session 3).

## 8. Near-infrared: the fourth band

The model also sharpens the near-infrared band (NIR), which our eyes cannot see. Healthy
plants reflect a lot of NIR, so it is useful for vegetation. A false-colour image shows NIR as
red, and NDVI = (NIR − red) / (NIR + red) turns it into a vegetation index.
""")
code(r"""
show([clip(lr, LAT, LON, 1), clip(s2, LAT, LON, 1)],
     ["Sentinel-2, false colour", "Stage 2, false colour"], bands=(4, 1, 2), ceiling=0.45,
     size=5.5)

fig, axes = plt.subplots(1, 2, figsize=(11, 5))
for ax, (title, da) in zip(axes, [("Sentinel-2, 10 m", lr), ("Stage 2, 2.5 m", s2)]):
    im = ax.imshow(clip(ndvi(da), LAT, LON, 1).values,
                   cmap="RdYlGn", vmin=-0.2, vmax=0.8, interpolation="nearest")
    ax.set_title(f"NDVI, {title}")
    ax.axis("off")
fig.colorbar(im, ax=axes, shrink=0.8)
plt.show()
""")

md(r"""
## 9. Checking against real high-resolution images

So far we compared the results with Sentinel-2, which cannot show anything smaller than
10 m. To check the 2.5 m detail itself we need a real high-resolution image of the same place
on the same day.

[Satellogic EarthView](https://registry.opendata.aws/satellogic-earthview/) is a free archive
of 1 m images (red, green, blue and NIR, CC BY 4.0). Its images are the kind the model learned
from, but **these three were held out of training**: the model has never seen them or
anything within their 384 m squares. Section 6 started one 1 km job around each, for the day
the image was taken.

To compare fairly:

* the Satellogic image is averaged from 1 m to 2.5 m, the size of our pixels;
* it is lined up with the Sentinel-2 image of the same day (or the closest), at 10 m;
* its brightness is matched to that Sentinel-2 image, band by band, at 10 m. Satellogic
  measures at the top of the atmosphere, Sentinel-2 (as used here) at the ground, so their
  raw values differ. The matching uses only 10 m information, so it does not favour any of
  the images we test;
* the Sentinel-2 image we compare with is that same-day image, enlarged: what you would get
  without super-resolution.
""")
code(r"""
checks.status()
check_jobs = checks.wait()

place = "near Faisalabad, Pakistan: farmland"      # try the other two places as well
images = compare_with_vhr(check_jobs[place], CHECKS[place])
show_vhr(images, place)
""")

md(r"""
Look at the field edges and the tracks between the fields, the roofs, and the trees. Which
of the three looks most like the real image? And which one has the real detail **in the
right place**?

The numbers below are correlations with the real image (1 = the same pattern). "all" compares
everything; "< 10 m" compares only the detail smaller than a Sentinel-2 pixel, which is the
part that super-resolution adds. Each image may move by up to one 2.5 m pixel to line up,
since two satellites never line up to the metre.
""")
code(r"""
shown, tables = {place: images}, {}
for place, scene in CHECKS.items():
    if place not in shown:
        shown[place] = compare_with_vhr(check_jobs[place], scene)
    tables[place.split(":")[0]] = vhr_scores(shown[place])
table = pd.concat(tables)
table.round(2)
""")

md(r"""
**What we found in our run.** The pattern was the same in all three places:

* **Stage 1 has the most real detail.** Its detail smaller than 10 m matches the real image
  better than enlarged Sentinel-2 in every place, for colour, near-infrared and NDVI (NDVI:
  0.71, 0.75 and 0.83 in Ningbo, near Yangon and near Faisalabad, against 0.43, 0.57 and
  0.64 for Sentinel-2).
* **Stage 2 looks the most like the real image, but its detail is less often in the right
  place.** It scores below Stage 1, though still above Sentinel-2 in most cases. This is
  section 7 again: the diffusion step draws detail that is *plausible*, not detail that was
  *measured*.
* For maps where every pixel counts (measuring, change detection), Stage 1 is the safer
  choice; for looking and for models trained on real high-resolution images (Session 3),
  Stage 2 can work better.

**What this check cannot tell you.** Three small places, in the kind of images the model was
trained on, is a sanity check and not a full evaluation. Because the brightness is matched to
Sentinel-2, it tests patterns, not absolute values: it does not show whether an NDVI of 0.6
is really 0.6.
""")

md(r"""
---
Results contain modified Copernicus Sentinel data. Sentinel-2 scenes are read from the public
archive on AWS (Element 84 Earth Search).
""")

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python",
                                 "name": "python3"},
                  "language_info": {"name": "python"}, "colab": {"provenance": []}}
src = "\n".join(c.source for c in cells)
assert all(f'"{k}"' in src for k in [*PRESENTER_DIALS, *PRESENTER_CHECKS]), "places.py differs"
nbf.write(nb, OUT)
print("wrote", OUT, len(cells), "cells")
