"""Builds notebooks/demo1_your_turn.ipynb: the participants' worksheet for Practical
demonstration 1 (about 20 minutes, self-led, in pairs).

    python tools/demos/build_demo1_worksheet.py

The helper code (d1_helpers.py) and the list of places (places.py) are pasted into a hidden
form cell, so the notebook runs on its own in Colab.
"""
import json
from pathlib import Path

import nbformat as nbf

from places import AREA_KM, EXPERIMENTS, OWN_PLACE, PLACES, as_code

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "notebooks" / "demo1_your_turn.ipynb"
PIP = '%pip install -q "sr-client[geo,viz] @ git+https://github.com/adb-sr/sr-client@v0.1.0"'
cells = []


def md(s):
    cells.append(nbf.v4.new_markdown_cell(s.strip("\n")))


def code(s, hidden=False):
    c = nbf.v4.new_code_cell(s.strip("\n"))
    if hidden:
        c.metadata["cellView"] = "form"
    cells.append(c)


def options(values):
    return json.dumps(list(values), ensure_ascii=False)


place_rows = "\n".join(f"| **{name}** | {p['note']} |" for name, p in PLACES.items())
experiment_default = "much more noise (tau 999)"
assert experiment_default in EXPERIMENTS
place_default = "Cebu City and Mandaue"
assert place_default in PLACES

md(rf"""
# Practical demonstration 1: your turn

*SSTA workshop, 26 November 2026. Goes with Session 2, "ADB's approach to super-resolution".*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo1_your_turn.ipynb)

You have just seen the service at work on one example. Now you make a super-resolved image
of **a place you know** and judge it yourself. Work in pairs: one person runs the cells, the
other looks closely and notes the answers.

**About 20 minutes, five steps, four questions.** You do not need to write code: run each
cell with **Shift + Enter** (or the ▶ button) and change values in the small forms on the
right.

| Step | What you do | Question |
|---|---|---|
| 1 | Pick a place and send it to the service | |
| 2 | Look at the 8 Sentinel-2 images the model uses | **Q1** How many are really clear? |
| 3 | Compare Stage 1 with Sentinel-2 | **Q2** What can you see now that you could not see before? |
| 4 | Look at Stage 2, the full result | **Q3** One detail it got right, one it got wrong |
| 5 | Turn one dial and compare | **Q4** Which version would you use, and for what? |

At the end, the notebook prints a **result card** with your answers. We compare the cards in
the room.

**Stuck?** Raise your hand, or carry on with *Cebu City and Mandaue*: every step works with
it.
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
print(f"Key {me['prefix']} ({me['owner']}): ${me['budget']['remaining_usd']:.2f} of budget left")
""")
code('# @title Helper functions (run this cell; you do not need to read it) { display-mode: "form" }\n'
     + (HERE / "d1_helpers.py").read_text() + "\n\n"
     + as_code("PLACES", {k: {f: v[f] for f in ("lat", "lon", "date", "note")}
                          for k, v in PLACES.items()})
     + as_code("EXPERIMENTS", EXPERIMENTS), hidden=True)

md(rf"""
## 1. Pick a place *(2 minutes)*

Choose the place you know best. All five were run before the workshop, so they come back
quickly and cost nothing.

| Place | What is there |
|---|---|
{place_rows}

Each area is a {AREA_KM} km square. The cell first asks for an **estimate**, which is free:
how many Sentinel-2 images exist around the date, and what the job would cost.

*Your own place* also works (choose the last entry in the list and fill in a point and a
date), but it takes a few minutes longer and uses your budget. Do the five steps with a
listed place first if you are short of time.
""")
code(rf"""
PLACE = "{place_default}"  # @param {options([*PLACES, OWN_PLACE])}
# only used for "My own place": a point (from Google Maps: right-click, copy) and a date
MY_LAT = 14.6760  # @param {{type:"number"}}
MY_LON = 121.0437  # @param {{type:"number"}}
MY_DATE = "2026-04-15"  # @param {{type:"date"}}

LAT, LON, DATE = choose_place(PLACE, MY_LAT, MY_LON, MY_DATE)
area = area_around(LAT, LON, km={AREA_KM})

est = sr.estimate(area, DATE)      # free
can_send = print_estimate(est)
""")
md("Now send the job. Both stages run; Stage 1 is ready first, after about a minute.")
code(r"""
job = sr.submit(area, DATE)        # Stage 1 + Stage 2, with the default dials
print("job", job.id, job.status)
""")

md(r"""
## 2. What did the satellite see? *(4 minutes)*

For every 320 m square, the model gets the **8 clearest Sentinel-2 images** closest to your
date. Below are the 8 for the middle of your area, read from the public Sentinel-2 archive.

* Pixels outlined in **red** are masked: ESA's classification marks them as cloud, cirrus or
  shadow. The model fills them from the other images.
* Image 1 is the **reference**: the result follows its layout and colours.
* The classification is not perfect. It misses thin cloud and haze, and sometimes masks
  bright roofs.

**Q1. How many of the 8 images are really clear over your place? Is there a cloud, haze or
shadow that the red outline missed?**
""")
code(r"""
wait_for_stage(job, "1")
tile = show_inputs(job, LAT, LON, DATE)
""")
code(r"""
# @title Q1: your answer (set the values, then run the cell)
Q1_CLEAR_IMAGES = 8  # @param {type:"slider", min:0, max:8, step:1}
Q1_MISSED_CLOUD = "not sure"  # @param ["no", "yes", "not sure"]
""")

md(r"""
## 3. Stage 1: eight images become one *(4 minutes)*

Stage 1 combines the 8 images into one image with 2.5 m pixels. It adds nothing that the
satellite did not measure, so it is sharper than Sentinel-2 but still soft.

Move the view to a spot you know: a street you walk, your office, a market, a field.
`EAST_M` and `NORTH_M` move the view from the centre of the area (in metres), `SIZE_M` zooms.
The cell runs again each time you change a value.

**Q2. Name one thing you can make out in Stage 1 that you could not make out in the
Sentinel-2 image.**
""")
code(r"""
lr = load(job, "lr_reference.tif")     # the Sentinel-2 input, 10 m
s1 = load(job, "stage1_sr.tif")        # Stage 1, 2.5 m
print(f"agreement of Stage 1 with Sentinel-2 at 10 m: {agreement(s1, lr):.2f}  (1 = same pattern)")
""")
code(r"""
# @title Move the view { run: "auto" }
EAST_M = 0  # @param {type:"slider", min:-750, max:750, step:50}
NORTH_M = 0  # @param {type:"slider", min:-750, max:750, step:50}
SIZE_M = 500  # @param [250, 500, 1000, 2000] {type:"raw"}

show([view(lr, LAT, LON, SIZE_M, EAST_M, NORTH_M), view(s1, LAT, LON, SIZE_M, EAST_M, NORTH_M)],
     ["Sentinel-2, 10 m", "Stage 1, 2.5 m"], size=6.5,
     suptitle=f"{PLACE}: {SIZE_M} m across")
""")
code(r"""
# @title Q2: your answer
Q2_NEW_IN_STAGE_1 = ""  # @param {type:"string"}
""")

md(r"""
## 4. Stage 2: the model adds detail *(5 minutes)*

Stage 2 adds noise to the Stage 1 image and removes it step by step. While it removes the
noise, it draws small details the way it learned them from 1.8 million real high-resolution
images. The result looks sharp. Some of that detail is real, and some is only *plausible*.

You know this place, so you can tell the difference. Move the view again and look for:

* something Stage 2 shows **correctly** (a road that is really there, the shape of a building
  you know);
* something that is **wrong or invented** (a roof pattern that does not exist, a road that
  ends nowhere, a building that became trees).

**Q3. One detail Stage 2 got right, and one it got wrong.**
""")
code(r"""
job.wait()
s2 = load(job, "stage2_sr.tif")        # Stage 2, 2.5 m
print_warnings(job)
print(f"agreement with Sentinel-2 at 10 m: Stage 1 {agreement(s1, lr):.2f}, "
      f"Stage 2 {agreement(s2, lr):.2f}")
""")
code(r"""
# @title Move the view { run: "auto" }
EAST_M = 0  # @param {type:"slider", min:-750, max:750, step:50}
NORTH_M = 0  # @param {type:"slider", min:-750, max:750, step:50}
SIZE_M = 500  # @param [250, 500, 1000, 2000] {type:"raw"}

show([view(da, LAT, LON, SIZE_M, EAST_M, NORTH_M) for da in (lr, s1, s2)],
     ["Sentinel-2, 10 m", "Stage 1", "Stage 2"], size=5.6,
     suptitle=f"{PLACE}: {SIZE_M} m across")
""")
code(r"""
# @title Q3: your answers
Q3_RIGHT = ""  # @param {type:"string"}
Q3_WRONG = ""  # @param {type:"string"}
""")

md(r"""
## 5. One experiment: turn a dial *(5 minutes)*

Stage 2 has the two dials from Session 2:

* **Dial 1, `tau`**: how much noise is added, from 0 (Stage 1 only) to 999 (almost only
  noise). More noise lets the model draw more of its own detail. The default is 250. (The
  noise experiments below keep the default 250 steps, so only one dial changes.)
* **Dial 2, `nfe`**: in how many steps the noise is removed. Fewer steps are faster and
  cheaper, and less sharp.
* The noise is random. The **seed** fixes it: another seed gives another version of the
  invented detail, while everything that was measured stays the same.

Choose **one** experiment. Other pairs will choose others, and we compare at the end. Before
you run it, write down what you expect.
""")
code(rf"""
EXPERIMENT = "{experiment_default}"  # @param {options(EXPERIMENTS)}
MY_GUESS = "sharper, and I would still trust it"  # @param ["sharper, and I would still trust it", "sharper, but I would not trust the detail", "less sharp", "hardly any difference"]

trial = sr.submit(area, DATE, **EXPERIMENTS[EXPERIMENT])
trial.wait()
s2_trial = load(trial, "stage2_sr.tif")
""")
md(r"""
The third image shows **where the two versions differ** (bright = large difference). If
your experiment was the other seed, this is a map of where the model invented detail.
""")
code(r"""
# @title Compare { run: "auto" }
EAST_M = 0  # @param {type:"slider", min:-750, max:750, step:50}
NORTH_M = 0  # @param {type:"slider", min:-750, max:750, step:50}
SIZE_M = 250  # @param [250, 500, 1000, 2000] {type:"raw"}

diff = seed_difference(s2, s2_trial)
show([view(s2, LAT, LON, SIZE_M, EAST_M, NORTH_M), view(s2_trial, LAT, LON, SIZE_M, EAST_M, NORTH_M),
      plt.cm.magma(np.clip(view(diff, LAT, LON, SIZE_M, EAST_M, NORTH_M).values / 0.05, 0, 1))],
     ["default (tau 250, 250 steps, seed 0)", EXPERIMENT, "where they differ"], size=5.6,
     suptitle=f"{PLACE}: {SIZE_M} m across")
print(f"{'':<34}{'agreement with':>16}{'fine':>10}")
print(f"{'':<34}{'Sentinel-2':>16}{'detail':>10}")
for label, da in (("Stage 1", s1), ("default", s2), (EXPERIMENT, s2_trial)):
    print(f"{label:<34}{agreement(da, lr):>16.2f}{detail(da):>10.4f}")
print(f"pixels that differ clearly between the two versions: {float((diff > 0.02).mean()):.0%}")
""")
md(r"""
*Agreement with Sentinel-2*: averaged back to 10 m, does the image still match what the
satellite measured (1 = same pattern)? *Fine detail*: how much the brightness changes from
one pixel to the next (higher = sharper).

**Q4. Which version would you use for a picture in a report? And which for counting
buildings or measuring roads?**
""")
code(r"""
# @title Q4: your answers
Q4_REPORT_PICTURE = "default Stage 2"  # @param ["Sentinel-2", "Stage 1", "default Stage 2", "my experiment"]
Q4_COUNTING = "default Stage 2"  # @param ["Sentinel-2", "Stage 1", "default Stage 2", "my experiment"]
""")

md(r"""
## 6. Your result card

Run the cell. Enter your answers in the poll (the link is on the slide), and be ready to say
in one sentence what you found at your place.
""")
code("result_card(globals())")

md(r"""
---
## If you have time

**Take the images home.** The files open in QGIS or ArcGIS. In Colab they appear in the file
browser on the left, under `sr_results/<job id>/`.

| File | What it holds |
|---|---|
| `stage1_sr.tif`, `stage2_sr.tif` | the 2.5 m images: red, green, blue, near-infrared; reflectance × 10,000 |
| `lr_reference.tif` | the Sentinel-2 input, 10 m |
| `validity.tif` | 0 no data · 1 valid · 2 low diversity (fewer than 4 different clear images) |
| `manifest.json` | the images used for every tile, the settings, model versions, cost |
""")
code(r"""
paths = job.download("sr_results")
for name, path in paths.items():
    print(f"  {path}  ({path.stat().st_size / 1e6:.1f} MB)")
""")
md(r"""
**Near-infrared and vegetation.** The model also sharpens the near-infrared band, which our
eyes cannot see. Plants reflect a lot of it. The false-colour image shows near-infrared as
red; NDVI turns it into a vegetation index (green = dense vegetation).
""")
code(r"""
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
**Another place, another dial.** Go back to step 1 and choose *My own place*, or back to
step 5 and try another experiment. Tips for your own place:

* pick a dry-season date (in Luzon, December to May) so there are enough clear images;
* near the coast you will get the `water` warning: the sea and reefs are not reliable;
* keep the area at 2 km while you explore.

**The full walkthrough.** The notebook the presenter used,
[`demo1_super_resolution.ipynb`](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo1_super_resolution.ipynb),
has more: all dial settings side by side, the trade-off between sharp and truthful as a
chart, and a check against real 1 m images.

---
Results contain modified Copernicus Sentinel data. Sentinel-2 scenes are read from the public
archive on AWS (Element 84 Earth Search).
""")

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python",
                                 "name": "python3"},
                  "language_info": {"name": "python"}, "colab": {"provenance": []}}
nbf.write(nb, OUT)
print("wrote", OUT, len(cells), "cells")
