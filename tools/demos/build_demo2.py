"""Builds notebooks/demo2_use_cases.ipynb: Practical demonstration 2 (self-led, in pairs).

    python tools/demos/build_demo2.py

Everything the notebook shows was computed before the workshop by build_demo2_package.py;
the notebook only downloads it. It needs no API key, no GPU and no installation.
"""
import json
from pathlib import Path

import nbformat as nbf

from places import PLACES

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "notebooks" / "demo2_use_cases.ipynb"
DATA_URL = "https://huggingface.co/datasets/adbsr-internal/ssta-hackathon/resolve/main/demo2"
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


place_default = "Cebu City and Mandaue"
assert place_default in PLACES
place_rows = "\n".join(f"| **{name}** | {p['note']} |" for name, p in PLACES.items())
VIEW = """EAST_M = 0  # @param {type:"slider", min:-750, max:750, step:50}
NORTH_M = 0  # @param {type:"slider", min:-750, max:750, step:50}
SIZE_M = %d  # @param [250, 500, 1000, 2000] {type:"raw"}"""
BEST = options(["Sentinel-2", "Stage 1", "Stage 2", "no real difference"])

md(r"""
# Practical demonstration 2: from super-resolved images to maps

*SSTA workshop, 26 November 2026. Goes with Session 3, "Sample use cases".*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo2_use_cases.ipynb)

Session 3 ended with a rule: **before you use super-resolution for a task, test it on a small
labelled sample.** In this notebook you run that test for the place you worked on this
morning, and you end with a verdict: would you **deploy** it, **pilot** it, or **not use**
it?

Work in pairs again. **About 25 minutes, six steps.** You do not need to write code: run each
cell with **Shift + Enter** and change values in the small forms on the right. Nothing needs
a key or a GPU: the images and the maps were made before the workshop, and the notebook only
downloads them.

| Step | What you do | Time |
|---|---|---|
| 1 | Pick your place and look at the three images | 3 min |
| 2 | **Guess first**: which image will give the best map? | 1 min |
| 3 | See the maps a land-cover model draws from each image | 3 min |
| 4 | Score them against public maps, and check your guess | 4 min |
| 5 | Hunt: find one place where super-resolution rescued the map and one where it failed | 6 min |
| 6 | Use the map for a decision, and give your **verdict** | 8 min |

The four steps of Session 3 are all here:

| Session 3 | In this notebook |
|---|---|
| 1. Label | public maps: Open Buildings (structures) and OpenStreetMap (roads) |
| 2. Train | a land-cover model that was already trained on real high-resolution images |
| 3. Use | we ran it on Sentinel-2, on Stage 1 and on Stage 2 (before the workshop) |
| 4. Score | you compare each map with the public maps |
""")

md("## 0. Setup\n\nRun the next cell. It holds the helper code; you do not need to read it.")
code('# @title Helper functions (run this cell; you do not need to read it) { display-mode: "form" }\n'
     + (HERE / "d2_helpers.py").read_text()
     + f'\n\nDATA_URL = os.environ.get("DEMO2_DATA_URL", "{DATA_URL}")\n', hidden=True)

md(rf"""
## 1. Pick your place *(3 minutes)*

Take the place you used this morning, so you already know what its images look like. (If you
used your own place this morning, take the listed place you know best.)

| Place | What is there |
|---|---|
{place_rows}

For each place there are three images of the same 2 km square:

* **Sentinel-2**: the free 10 m image, enlarged to 2.5 m pixels. This is the "do nothing"
  option.
* **Stage 1**: 8 Sentinel-2 images combined. Nothing invented.
* **Stage 2**: the full model, with added detail.
""")
code(rf"""
PLACE = "{place_default}"  # @param {options(PLACES)}

place = Place(PLACE, DATA_URL)
print(place)
show_inputs(place, size_m=1000)
""")

md(r"""
## 2. Guess first *(1 minute)*

A land-cover model will draw a map from each of the three images. It was trained on **real
high-resolution images** and has never seen a super-resolved one. We then check its
**buildings** and its **roads** against public maps.

Which image will give the best map? Agree on a guess before you go on.
""")
code(rf"""
# @title Your guess: which image gives the best map?
GUESS_BUILDINGS = "Stage 2"  # @param {BEST}
GUESS_ROADS = "Stage 2"  # @param {BEST}
""")

md(r"""
## 3. The maps *(3 minutes)*

The model starts from SatlasPretrain (Allen Institute for AI) and was fine-tuned on
OpenEarthMap: aerial and satellite images from 44 countries, labelled by hand. It gives
every 2.5 m pixel one of 8 classes. It is the model behind the road result in Session 3.

This is the **"reuse"** path from Session 3: nobody labelled anything on super-resolved
images. We only fed the model three different images of your place.
""")
code('# @title Move the view { run: "auto" }\n' + (VIEW % 1000) + r"""

show_landcover(place, SIZE_M, EAST_M, NORTH_M)
show_inputs(place, SIZE_M, EAST_M, NORTH_M)
""")

md(r"""
## 4. Score against public maps *(4 minutes)*

The reference is two public maps that anyone can download for any place in the Philippines:

* **Open Buildings**: building footprints from Google, Microsoft and OpenStreetMap, combined
  by VIDA. They were made by a model from 50 cm images, so they are good but not perfect.
* **OpenStreetMap roads** (through Overture Maps). Roads are lines, so each one is widened to
  a typical width for its class (12 m for a motorway, 3 m for a farm track).

**F1** measures the overlap between the model's map and the public map, pixel by pixel:
0 = no overlap, 1 = perfect. *found* is the share of the public map's buildings (or roads)
that the model found; *correct* is the share of the model's buildings that are in the public
map.
""")
code(r"""
show_reference(place, size_m=1000)
table = score_table(place)
show_scores(table, f"{PLACE}: land-cover model against the public maps")
check_guess(table, {"buildings": GUESS_BUILDINGS, "roads": GUESS_ROADS})
table
""")
md(r"""
The scores look low compared with Session 3. Two reasons: the references are public maps and
not expert labels, and a pixel-by-pixel score punishes every shift of a few metres. Compare
the three inputs with each other, not with 1.
""")

md(r"""
## 5. Hunt: one rescue, one failure *(6 minutes)*

A score hides where the map is right and where it is wrong. Look for yourself. In the bottom
row, **green** is correct, **blue** is a false alarm (only the model says "building") and
**red** is missed (only the public map says so).

Move the view and find:

* a **rescue**: something the map from Sentinel-2 missed and the map from Stage 1 or Stage 2
  found;
* a **failure**: something the super-resolved map gets wrong. Is it a miss, a false alarm, or
  a building in the wrong shape? Could the public map be the one that is wrong?

You know this place: use that.
""")
code('# @title Move the view { run: "auto" }\n'
     'TASK = "buildings"  # @param ["buildings", "roads"]\n' + (VIEW % 500) + r"""

show_errors(place, TASK, SIZE_M, EAST_M, NORTH_M)
""")
code(r"""
# @title Your finds (a few words each)
RESCUE = ""  # @param {type:"string"}
FAILURE = ""  # @param {type:"string"}
""")

md(r"""
## 6. From a map to a decision *(8 minutes)*

Maps are used to decide something. Here is one such decision, the same kind you will work on
in tomorrow's hackathon:

> Your team can visit only a few 250 m squares of this area (to survey housing, or to check
> road condition). You send the team to the squares where the map shows the **most**
> buildings (or roads). How many of those visits go to the right squares?

A pick counts as a **hit** if the square is truly among the densest according to the public
map. Change `BUDGET` (how many squares you can visit) and `TASK`, and watch whether
super-resolution changes the number of hits. A better F1 does not always change the decision.
With so few squares, one hit more or less can be chance: try several budgets before you
conclude.
""")
code('# @title Your decision { run: "auto" }\n' + r"""
TASK = "buildings"  # @param ["buildings", "roads"]
BUDGET = 10  # @param {type:"slider", min:3, max:30, step:1}

hits = decision(place, TASK, BUDGET)
""")
md(r"""
**Your verdict.** For the use you have in mind at your place, would you:

* **deploy**: use maps from super-resolved images as they are;
* **pilot**: try it on a larger area with proper labels and field checks first;
* **not use** it: plain Sentinel-2 is as good, or the errors are too costly.

"Super-resolution does not help here" is a perfectly good result.
""")
code(r"""
# @title Your verdict
VERDICT_FOR = "a screening map of built-up areas"  # @param {type:"string"}
VERDICT = "pilot"  # @param ["deploy", "pilot", "do not use"]
WOULD_CHANGE_MY_MIND = ""  # @param {type:"string"}

result_card(globals())
""")
md(r"""
Enter your verdict in the poll (the link is on the slide), and be ready to say in one
sentence why.
""")

md(r"""
---
## For the discussion: all five places

The same scores for every place. Where does super-resolution help most? Where does it make
no difference? Is that what Session 3 would predict?
""")
code(r"""
summary = get_summary(DATA_URL)
show_all_places(summary).round(2)
""")
md(r"""
**What we found** (our run before the workshop):

* **Buildings**: the score rises with every step, in every place. F1 is 0.15 to 0.26 on
  Sentinel-2, 0.35 to 0.44 on Stage 1 and 0.53 to 0.60 on Stage 2.
* **Roads**: on Sentinel-2 the model finds almost no roads in four of the five places (F1
  0.01 to 0.07). Only around ADB headquarters, where the avenues are wide, does it reach
  0.20. On Stage 2 it reaches 0.20 to 0.44. The largest gain is for the farm roads of Nueva
  Ecija (0.01 to 0.44); the smallest is in Cebu, where the streets between small houses are
  narrower than a 2.5 m pixel can show.
* **The decision changes less than the score.** With 10 squares to visit for buildings, the
  hits were 4, 5 and 5 (Sentinel-2, Stage 1, Stage 2) at ADB headquarters, 4, 4 and 4 at
  DHSUD, 2, 3 and 1 in Cebu, but 3, 4 and 8 in Nueva Ecija. In a dense city almost every
  square is built up, so a sharper map hardly changes which squares come first. Where
  buildings are few and scattered, it does.

This is the pattern of Session 3: a model trained on real high-resolution images cannot read
a 10 m image, and super-resolution lets it work on free Sentinel-2. Whether that changes
what you would *do* depends on the decision.
""")

md(r"""
## If you have time

**Reuse a model, or train your own?** So far we *reused* a model trained on real
high-resolution images. The other path in Session 3 is to *train a model on the images you
will use*. Before the workshop we also trained a quick, simple model on each input (on the
west half of each area, scored on the east half). The table shows its F1.
""")
code(r"""
all_places(summary, "own_model_F1").round(2)
""")
md(r"""
**The gap disappears.** When a model is trained on each input, the three inputs score about
the same, and plain Sentinel-2 is often slightly ahead (buildings: 0.44 to 0.64 on Sentinel-2
against 0.40 to 0.59 on Stage 2). This quick model only looks at colours and textures around
each pixel, so it is a rough test, but it shows what part of the gain above is: super-resolution
makes Sentinel-2 *look like* the images that existing models were trained on. So:

* if a good model trained on high-resolution images exists for your task, super-resolution
  lets you run it on free Sentinel-2;
* if you train your own model anyway, test whether super-resolution helps before you rely on
  it. Sometimes plain Sentinel-2 is just as good.

**Before you use a map**

* **Check the warnings and the validity map** of every job (this morning's notebook). Near
  water, use Sentinel-2.
* **Spot-check** a sample of the map against a real image or a field visit before acting on
  it.
* **Use maps for areas, not single objects**: screening, planning, trends. Not for decisions
  about one household or one building.
* **Each map shows a period** (the images span 45 days before and after the date), not a
  single day.

**How the maps were made.** The images come from the super-resolution service (the same jobs
as this morning). The land-cover model is public:
[adbsr-internal/satlas-downstream](https://huggingface.co/adbsr-internal/satlas-downstream)
on Hugging Face. The script that made this data package is
[`tools/demos/build_demo2_package.py`](https://github.com/adb-sr/sr-client/blob/main/tools/demos/build_demo2_package.py).

---
Contains modified Copernicus Sentinel data. Building footprints: Google–Microsoft–OSM Open
Buildings by VIDA (ODbL). Roads: © OpenStreetMap contributors (ODbL), via Overture Maps.
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
