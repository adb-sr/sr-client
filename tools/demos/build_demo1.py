"""Builds notebooks/demo1_super_resolution.ipynb: the one notebook of Practical demonstration 1.

    python tools/demos/build_demo1.py

The session zig-zags. Each part has a one-line cell that everyone runs (pictures and controls),
a collapsed "Under the hood" cell with the plain sr-client code behind it (the presenter opens
it on the screen; optional for everyone else), and a few minutes in which participants explore
their own place and answer a question. "Going deeper" at the end is for later.

The helper code (d1_helpers.py), the controls (widgets_common.py, d1_widgets.py) and the list
of places (places.py) are pasted into a hidden form cell, so the notebook runs on its own in
Colab.
"""
from pathlib import Path

import nbformat as nbf

from places import AREA_KM, EXPERIMENTS, PLACES, PRESENTER_CHECKS, PRESENTER_DIALS, as_code

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "notebooks" / "demo1_super_resolution.ipynb"
PIP = '%pip install -q "sr-client[geo,viz] @ git+https://github.com/adb-sr/sr-client@v0.1.0"'
cells = []


def md(s):
    cells.append(nbf.v4.new_markdown_cell(s.strip("\n")))


def code(s, hidden=False):
    c = nbf.v4.new_code_cell(s.strip("\n"))
    if hidden:
        c.metadata["cellView"] = "form"
    cells.append(c)


def hood(title, s):
    """A collapsed cell: Colab shows only its title and the run button until it is opened."""
    code(f'# @title Under the hood: {title} {{ display-mode: "form" }}\n' + s.strip("\n"),
         hidden=True)


place_rows = "\n".join(f"| **{name}** | {p['note']} |" for name, p in PLACES.items())

md(r"""
# Practical demonstration 1: the super-resolution service

*SSTA workshop, 26 November 2026. Goes with Session 2, "ADB's approach to super-resolution".*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo1_super_resolution.ipynb)

You make a super-resolved image of **a place you know** and judge it yourself, one part at a
time. We go through the parts together. Each part has the same three beats:

| | What | Who |
|---|---|---|
| **▶ Look** | Run a one-line cell. Images and controls appear under it. | everyone |
| **⚙ Under the hood** | A collapsed cell with the code behind what you just saw: the calls to the service, and how it works inside. The presenter opens it on the screen. To open it yourself, double-click its title (or click *Show code*), then run it. | optional |
| **✎ Your turn** | Explore your own place with the sliders and buttons, and answer one question. | everyone, in pairs |

| Part | You look at | Under the hood | Question |
|---|---|---|---|
| 1 | Pick a place and send it to the service | the request in code | |
| 2 | The 8 Sentinel-2 images the model uses | how the service found and chose them | **Q1** How many are really clear? |
| 3 | Stage 1 next to Sentinel-2 | from 320 m tiles to one image | **Q2** What can you see now that you could not see before? |
| 4 | Stage 2, the full result | what comes with every result | **Q3** One detail it got right, one it got wrong |
| 5 | One dial turned, next to the default | the experiment in code, and the two numbers | **Q4** Which version would you use, and for what? |
| 6 | Your result card | | |

**You do not need to write code.** Run each grey cell once, from top to bottom, with
**Shift + Enter** (or the ▶ button). The menus, buttons and sliders under a cell act at once,
and your answers are saved as you type. You can skip every *Under the hood* cell: nothing
later depends on them.

**Stuck?** Raise your hand, or carry on with *Cebu City and Mandaue*: every part works with
it. Sections 7 to 10 are for later.
""")

md("## 0. Setup\n\nRun the next three cells. The first takes about a minute.")
code(PIP)
md(r"""
Your API key starts with `srk_`. The cell asks for the key and the service URL (both are on
your card). In Colab you can also store them under **Secrets** (the key icon on the left) as
`SR_API_KEY` and `SR_API_URL`.
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
code('# @title Helper functions (run this cell; you do not need to read it) { display-mode: "form" }\n'
     + (HERE / "d1_helpers.py").read_text() + "\n\n"
     + as_code("PLACES", {k: {f: v[f] for f in ("lat", "lon", "date", "note")}
                          for k, v in PLACES.items()})
     + as_code("EXPERIMENTS", EXPERIMENTS) + "\n\n"
     + (HERE / "widgets_common.py").read_text() + "\n\n"
     + (HERE / "d1_widgets.py").read_text(), hidden=True)

# ---- part 1 ---------------------------------------------------------------------------------
md(rf"""
## 1. Pick a place *(3 minutes)*

**▶ Look.** Run the cell, choose the place you know best, and press **Send to the service**.
The service first makes a free **estimate** (which Sentinel-2 images exist around the date,
and what the job would cost) and then starts the job. All five places were run before the
workshop, so they come back quickly and cost nothing.

| Place | What is there |
|---|---|
{place_rows}

Each area is a {AREA_KM} km square. *My own place* is the last entry in the menu: fill in a
point and a date. It takes a few minutes longer and uses your budget, so start with a listed
place if you are short of time. If you change the place later, run the cells of parts 2 to 5
again.
""")
code("pick_place(sr)")
hood("the same request in code", r"""
LAT, LON, DATE, area, job = picked()          # the place you sent with the button

# what the service offers: one model, two stages, and the dials of Stage 2
model = sr.models()[0]
print(model["name"])
for stage, what in model["stages"].items():
    print(f"  stage {stage}: {what}")
print("  dials:", {k: v for k, v in model["params"].items() if k in ("tau", "nfe", "seed")})

# the area is a square around a point: [west, south, east, north]
print("area:", area_around(LAT, LON, km=2))

# the estimate is free: it searches the Sentinel-2 archive and runs nothing
est = sr.estimate(area, DATE)
print(f"{est['tiles']} tiles, about ${est['estimated_usd']:.2f}; {len(est['scenes'])} Sentinel-2 "
      f"images between {est['search_window'][0]} and {est['search_window'][1]}")
for s in est["scenes"][:5]:
    print("  ", s["date"][:10], s["id"])
print("   ...")

# the button then ran:   job = sr.submit(area, DATE)
print("job", job.id, job.refresh().status)

explain("request")
""")

# ---- part 2 ---------------------------------------------------------------------------------
md(r"""
## 2. The inputs: what did the satellite see? *(7 minutes)*

**▶ Look.** For every 320 m square, the model gets the **8 clearest Sentinel-2 images**
closest to your date. The cell shows the 8 for the middle of your area, read from the public
Sentinel-2 archive (this takes about half a minute).

* Pixels outlined in **red** are masked: ESA's classification marks them as cloud, cirrus or
  shadow. The model fills them from the other images.
* Image 1 is the **reference**: the result follows its layout and colours.
* The classification is not perfect. It misses thin cloud and haze, and sometimes masks
  bright roofs.
""")
code("step2_inputs()")
hood("how the service found and chose these images", r"""
LAT, LON, DATE, area, job = picked()

# every result comes with a manifest: what was used for each 320 m tile
m = manifest(job)
tile = middle_tile(m)                        # the tile shown above
print(f"{len(m['tiles'])} tiles; the one in the middle:")
print("  corner (row, col in 10 m pixels):", tile["row"], tile["col"])
for d, sid in zip(tile["dates"], tile["scene_ids"]):
    print("  ", d, sid)

# all images the search found, and how cloudy each is over this area
est = sr.estimate(area, DATE)
cloudy = cloud_over_area([s["id"] for s in est["scenes"]], area)   # read from the archive
plot_search(est, m, cloudy, DATE)

explain("search")
""")
md(r"""
**✎ Your turn.** Look at your 8 images above and answer **Q1** in the blue box under them.
""")

# ---- part 3 ---------------------------------------------------------------------------------
md(r"""
## 3. Stage 1: eight images become one *(7 minutes)*

**▶ Look.** Stage 1 combines the 8 images into one image with 2.5 m pixels. It is sharper
than Sentinel-2 but still soft.
""")
code("step3_stage1()")
hood("from 320 m tiles to one image", r"""
LAT, LON, DATE, area, job = picked()

# the results are GeoTIFFs; job.open() reads one as an xarray image
s1 = load(job, "stage1_sr.tif")              # = job.open("stage1_sr.tif"), in reflectance
lr = load(job, "lr_reference.tif")
print(f"Sentinel-2 input: {lr.sizes['x']} x {lr.sizes['y']} pixels of {abs(lr.rio.resolution()[0]):g} m")
print(f"Stage 1:          {s1.sizes['x']} x {s1.sizes['y']} pixels of {abs(s1.rio.resolution()[0]):g} m, "
      f"{s1.sizes['band']} bands, {s1.rio.crs}")

# the tiles the model worked on, drawn on the Stage 1 image
show_tiles(manifest(job), s1)

explain("tiles")
""")
md(r"""
**✎ Your turn.** Use the **sliders** above to move to a spot you know: a street you walk,
your office, a market, a field. The small picture on the left shows where you are in the
area; the **Zoom** buttons change how much you see. Then answer **Q2**.
""")

# ---- part 4 ---------------------------------------------------------------------------------
md(r"""
## 4. Stage 2: the model adds detail *(8 minutes)*

**▶ Look.** Stage 2 adds noise to the Stage 1 image and removes it step by step. While it
removes the noise, it draws small details the way it learned them from 1.8 million real
high-resolution images. The result looks sharp. Some of that detail is real, and some is only
*plausible*.
""")
code("step4_stage2()")
hood("what comes with every result", r"""
LAT, LON, DATE, area, job = picked()
job.wait(quiet=True)                         # until both stages are done

# the quality map: where the result has no data or rests on few different images
validity = job.open("validity.tif", reflectance=False).load()
show_validity(validity)

m = manifest(job)
print("warnings:", [w["code"] for w in job.warnings] or "none")
print("model:   ", m["model"])
print("cost:    ", m["cost"])
print(m["attribution"])

# the files, to open in QGIS or ArcGIS
paths = job.download("sr_results")
for name, path in paths.items():
    print(f"  {path}  ({path.stat().st_size / 1e6:.1f} MB)")

explain("result")
""")
md(r"""
**✎ Your turn.** You know this place, so you can tell real detail from invented detail. Move
the view above and look for:

* something Stage 2 shows **correctly** (a road that is really there, the shape of a building
  you know);
* something that is **wrong or invented** (a roof pattern that does not exist, a road that
  ends nowhere, a building that became trees).

Then answer **Q3**.
""")

# ---- part 5 ---------------------------------------------------------------------------------
md(r"""
## 5. One experiment: turn a dial *(10 minutes)*

**▶ Look.** Stage 2 has the two dials from Session 2:

* **Dial 1, `tau`**: how much noise is added, from 0 (Stage 1 only) to 999 (almost only
  noise). More noise lets the model draw more of its own detail. The default is 250. (The
  noise experiments keep the default 250 steps, so only one dial changes.)
* **Dial 2, `nfe`**: in how many steps the noise is removed. Fewer steps are faster and
  cheaper, and less sharp.
* The noise is random. The **seed** fixes it: another seed gives another version of the
  invented detail, while everything that was measured stays the same.

Choose **one** experiment in the menu; other pairs will choose others, and we compare at the
end. Click what you expect, then press **Run my experiment**. A setting that was run before
comes back at once; a new one takes about 4 minutes.

The result shows the default image, yours, and **where the two differ** (bright = large
difference). If your experiment was the other seed, that third picture is a map of where the
model invented detail. Under the pictures are two numbers for each version: *agreement with
Sentinel-2* (1 = same pattern as the satellite measured) and *fine detail* (higher =
sharper).
""")
code("step5_experiment()")
hood("the experiment in code, and the two numbers", r"""
LAT, LON, DATE, area, job = picked()
name, trial = my_experiment()                # the experiment you ran with the button

# an experiment is the same request with other options
print(f"{name}:  sr.submit(area, DATE, **{EXPERIMENTS[name]})")
for label, j in (("default", job), (name, trial)):
    p, cost = j.refresh().info["params"], j.info["cost"]["actual_usd"] or 0
    print(f"  {label:<30} tau {p.get('tau', 250)}, steps {p.get('nfe') or p.get('tau', 250)}, "
          f"seed {p.get('seed', 0)}, cost ${cost:.3f} ($0 if it was computed before)")

# the two numbers under the pictures
lr = load(job, "lr_reference.tif")
for label, j in (("default", job), (name, trial)):
    s2 = load(j, "stage2_sr.tif")            # agreement() first averages it back to 10 m
    print(f"  {label:<30} agreement with Sentinel-2 {agreement(s2, lr):.2f}   "
          f"fine detail {detail(s2):.4f}")

explain("dials")
""")
md(r"""
**✎ Your turn.** Move the view above to compare the two versions at a spot you know. Then
run the next cell and answer **Q4**.
""")
code("step5_question()")

# ---- part 6 ---------------------------------------------------------------------------------
md(r"""
## 6. Your result card *(5 minutes)*

Run the cell. If you change an answer afterwards, press **Update the card**. Enter your
answers in the poll (the link is on the slide), and be ready to say in one sentence what you
found at your place.
""")
code("result_card()")

md(r"""
---
# For later

## 7. If you have time

**Near-infrared and vegetation.** The model also sharpens the near-infrared band, which our
eyes cannot see. Plants reflect a lot of it. The false-colour image shows near-infrared as
red; NDVI turns it into a vegetation index (green = dense vegetation).
""")
code(r"""
LAT, LON, DATE, area, job = picked()
lr, s2 = load(job, "lr_reference.tif"), load(job, "stage2_sr.tif")
show([view(lr, LAT, LON, 1000), view(s2, LAT, LON, 1000)],
     ["Sentinel-2, false colour", "Stage 2, false colour"], bands=(4, 1, 2), ceiling=0.45,
     size=5.5)
fig, axes = plt.subplots(1, 2, figsize=(11, 5))
for ax, (title, da) in zip(axes, [("Sentinel-2, 10 m", lr), ("Stage 2, 2.5 m", s2)]):
    im = ax.imshow(view(ndvi(da), LAT, LON, 1000).values, cmap="RdYlGn", vmin=-0.2, vmax=0.8,
                   interpolation="nearest")
    ax.set_title(f"NDVI, {title}")
    ax.axis("off")
fig.colorbar(im, ax=axes, shrink=0.8)
plt.show()
""")
md(r"""
**Another place, another dial.** In part 1, choose another place (or *My own place*) and
press the button again, then run the cells of parts 2 to 5 again. Or choose another
experiment in part 5 and press its button. Tips for your own place:

* pick a dry-season date (in Luzon, December to May) so there are enough clear images;
* near the coast you will get the `water` warning: the sea and reefs are not reliable;
* the area is a 2 km square around your point.

**Take the images home.** The *Under the hood* cell of part 4 downloads the files of your
job. They open in QGIS or ArcGIS.

---
# Going deeper

Sections 8 to 10 take one example further: all dial settings side by side, the trade-off
between sharp and truthful as a chart, and a check against real 1 m images. They use Cebu
City and Mandaue, whose jobs were run before the workshop, and take about 15 minutes to run.
They are written as plain code, without buttons.

The next cell starts seven small jobs in the background: a 1 km square in the middle of the
Cebu area, each with another setting of the dials.
""")
code(r"""
B_LAT, B_LON, B_DATE = (PLACES["Cebu City and Mandaue"][k] for k in ("lat", "lon", "date"))
SMALL = area_around(B_LAT, B_LON, km=1)
DIALS = {
    "tau 100":            dict(tau=100),
    "tau 250":            dict(tau=250),
    "tau 500":            dict(tau=500),
    "tau 999":            dict(tau=999),
    "tau 250, 10 steps":  dict(tau=250, nfe=10),
    "tau 250, 50 steps":  dict(tau=250, nfe=50),
    "tau 250, seed 1":    dict(tau=250, seed=1),
}
sweep = Sweep({name: (SMALL, B_DATE, p) for name, p in DIALS.items()})
""")

md(r"""
## 8. The two dials, side by side

The cell waits for the seven jobs started above. When they are done, it starts three more for
section 10 in the background.
""")
code(r"""
sweep.status()
dial_jobs = sweep.wait()

# section 10: one job per real high-resolution image, on the day it was taken (1 km each)
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
show([clip(small[k], B_LAT, B_LON, 0.25) for k in order],
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
show([clip(small[k], B_LAT, B_LON, 0.25) for k in order],
     ["Stage 1", "10 steps", "50 steps", "250 steps"], size=3.6,
     suptitle="Dial 2 at τ = 250: 250 m in the middle")

print("cost of each 1 km job (USD; $0 when the result was already computed before):")
for name, j in dial_jobs.items():
    print(f"  {name:<22} {j.refresh().info['cost']['actual_usd'] or 0:.3f}")
""")

md(r"""
## 9. Sharp or truthful?

Session 2 showed the trade-off: more detail, but the detail is less certain. We can measure
both sides on our own images:

* **agreement with Sentinel-2**: average each 4 × 4 block of the 2.5 m image back to one
  10 m pixel. Does it still match what the satellite measured? (A correlation: 1 = the same
  pattern of light and dark.)
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
show([clip(a, B_LAT, B_LON, 0.25), clip(b, B_LAT, B_LON, 0.25)], ["seed 0", "seed 1"], size=4.6)

fig, ax = plt.subplots(figsize=(4.6, 4.6))
ax.imshow(clip(diff, B_LAT, B_LON, 0.25).values, cmap="magma",
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

""")

md(r"""
## 10. Checking against real high-resolution images

So far we compared the results with Sentinel-2, which cannot show anything smaller than
10 m. To check the 2.5 m detail itself we need a real high-resolution image of the same place
on the same day.

[Satellogic EarthView](https://registry.opendata.aws/satellogic-earthview/) is a free archive
of 1 m images (red, green, blue and NIR, CC BY 4.0). Its images are the kind the model learned
from, but **these three were held out of training**: the model has never seen them or
anything within their 384 m squares. Section 8 started one 1 km job around each, for the day
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
  section 9 again: the diffusion step draws detail that is *plausible*, not detail that was
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
