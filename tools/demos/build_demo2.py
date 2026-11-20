"""Builds notebooks/demo2_use_cases.ipynb: Practical demonstration 2 (self-led, in pairs).

    python tools/demos/build_demo2.py

Everything the notebook shows was computed before the workshop by build_demo2_package.py;
the notebook only downloads it. It needs no API key, no GPU and no installation.
"""
import json
from pathlib import Path

import nbformat as nbf

from places import PLACES, as_code

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

OEM_TEXT = r"""
**What it shows** (within 2.5 m):

* From the **aerial** image the model is very good: F1 0.88 for buildings, 0.76 for roads.
  This is what it was built for.
* From **Sentinel-2** it is close to useless: 0.35 for buildings and 0.23 for roads, below
  the dashed line (0.40 and 0.25).
* **Stage 1** (0.55 and 0.46) and **Stage 2** (0.66 and 0.54) are in between. Stage 2 closes
  a little more than half of the gap between Sentinel-2 and the aerial image, for buildings
  and for roads (half pixel-exact, about two thirds within 5 m).
* **Precision and recall** show where the gain comes from. From Sentinel-2 the model marks
  few buildings, and most of those are right (precision 0.68), but it finds only 23 % of them
  (recall). Stage 2 keeps the precision (0.70) and finds 63 %.
* **The confusion matrix** tells the same story. From the aerial image, 78 % of the building
  pixels are called building. From Sentinel-2 only 18 % are: the rest become rangeland
  (29 %), developed space (27 %), tree (15 %) and even water (9 %). From Stage 2, 48 %.
* The three examples are a good, a typical and a poor tile for Stage 2, not the best ones.
  Look at what Stage 2 gets right (which blocks are built up, the main roads) and what it
  does not (the exact shape of each building, narrow paths).

So the model works on super-resolved images, but not as well as on a real aerial image. Keep
that in mind as you leave home: do not expect it to do better in the Philippines than here.
"""

RESULTS_TEXT = r"""
**What we found** (our run before the workshop; scores within 2.5 m unless said otherwise):

* **Buildings**: the score rises with every step, in every place: F1 0.21 to 0.32 on
  Sentinel-2, 0.48 to 0.56 on Stage 1, 0.65 to 0.75 on Stage 2 (pixel-exact 0.53 to 0.60;
  within 5 m 0.74 to 0.84). Stage 2 finds 64 to 78 % of the buildings (recall), and 67 to 79 %
  of what it marks is right (precision). Almost all the gain is recall: on Sentinel-2 the
  model already marks few buildings, and those are mostly right (precision 0.61 to 0.82), but
  it finds only 12 to 20 % of them. But in the four cities a map that says "building" everywhere already
  scores 0.54 to 0.72: Stage 2 is above that line by only 0.02 to 0.11. Where almost
  everything is built up, the map adds little to "it is all built up". In Nueva Ecija, with
  few buildings, the line is at 0.16 and Stage 2 (0.74) is far above it.
* **Roads**: on Sentinel-2 the model finds almost no roads in four of the five places (F1
  0.01 to 0.09); only around ADB headquarters, where the avenues are wide, does it reach
  0.25. Stage 2 reaches 0.29 to 0.61 and is clearly above the "roads everywhere" line (0.30
  to 0.36 in the cities, 0.09 in Nueva Ecija) in every place except Cebu (0.29 against 0.30),
  where the streets between small houses are too narrow. Stage 2 finds 25 to 54 % of the
  roads (recall), and 36 to 71 % of what it marks is right (precision): it misses roads more
  often than it invents them. The largest gain is for the farm roads of Nueva Ecija (0.01 to 0.61).
* **The tolerance changes the level, not the order.** Forgive more shift and every score
  rises, the dashed line too. The order of the three images never changes, and the lead of
  Stage 2 over the line moves by a few hundredths (Cebu roads go from just above the line,
  pixel-exact, to just below it). IoU gives lower numbers than F1 and the same order.
* **At home and away.** Here Stage 2 reaches F1 0.65 to 0.75 for buildings and 0.29 to 0.61
  for roads (within 2.5 m); at home it reached 0.66 and 0.54. About the same, in spite of the
  new country and the imperfect public maps, but the two are not strictly comparable (other
  labels, other places). And the dashed line is far higher in the dense cities here (0.54 to
  0.72 for buildings) than at home (0.40), so the same F1 is worth less here.

This is the pattern of Session 3: a model trained on real high-resolution images cannot read
a 10 m image, and super-resolution lets it work on free Sentinel-2. In a dense city, check
the map against the dashed line before you trust it.
"""

OWN_TEXT = r"""
With a model trained on each image (within 2.5 m): buildings 0.63 to 0.80 on Sentinel-2
against 0.62 to 0.78 on Stage 2; roads 0.25 to 0.37 against 0.24 to 0.38. This quick model
only looks at colours and textures around each pixel and is scored on the east half only, so
it is a rough test. Even so, trained on Sentinel-2 alone it reaches about the level the
land-cover model reached on Stage 2 for buildings.
"""


md(r"""
# Practical demonstration 2: from super-resolved images to maps

*SSTA workshop, 26 November 2026. Goes with Session 3, "Sample use cases".*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo2_use_cases.ipynb)

Session 3 ended with a rule: **before you use super-resolution for a task, test it on a small
labelled sample.** In this notebook you run that test for the place you worked on this
morning.

**The model.** Everything here uses one **land-cover model**. It starts from SatlasPretrain
(Allen Institute for AI) and was fine-tuned on OpenEarthMap: aerial and satellite images of
0.25 to 0.5 m from 44 countries, labelled by hand. It gives every pixel one of 8 classes
(bare land, rangeland, developed space, road, tree, water, agriculture, building). It was
trained on **real high-resolution images only**: it has never seen Sentinel-2 or a
super-resolved image, and it has never seen the Philippines. We use it as it is. It is the
model behind the road result in Session 3.

So first you see how good the model is **at home**, on images like the ones it learned from
(step 1). Then you take it to **your place** and feed it three versions of the same image
(steps 2 to 6).

Work in pairs again. **About 25 minutes, six steps.** You do not need to write code:

* **run each grey cell once**, from top to bottom, with **Shift + Enter** (or the ▶ button);
* then use the **menus, buttons and switches that appear under the cell**. They act at once,
  and your answers are saved as you type. You never need to run a cell twice.

Nothing needs a key or a GPU: the images and the maps were made before the workshop, and the
notebook only downloads them.

| Step | What you do | Time |
|---|---|---|
| 1 | The model at home: how good is it on hand-labelled tiles? | 4 min |
| 2 | Pick your place and look at the three images | 3 min |
| 3 | **Guess first**: which image will give the best map? | 1 min |
| 4 | See the maps the model draws from each image | 3 min |
| 5 | Score them against public maps, and check your guess | 5 min |
| 6 | Hunt: find one place where super-resolution rescued the map and one where it failed | 7 min |

The four steps of Session 3 are all here:

| Session 3 | In this notebook |
|---|---|
| 1. Label | public maps: Open Buildings (structures) and OpenStreetMap (roads) |
| 2. Train | the land-cover model, already trained on real high-resolution images |
| 3. Use | we ran it on Sentinel-2, on Stage 1 and on Stage 2 (before the workshop) |
| 4. Score | you compare each map with the public maps |
""")

md("## 0. Setup\n\nRun the next cell. It holds the helper code; you do not need to read it.")
code('# @title Helper functions (run this cell; you do not need to read it) { display-mode: "form" }\n'
     + (HERE / "d2_helpers.py").read_text() + "\n\n"
     + as_code("PLACES", {k: {f: v[f] for f in ("lat", "lon", "date", "note")}
                          for k, v in PLACES.items()})
     + f'PLACE_DEFAULT = "{place_default}"\n'
     + f'DATA_URL = os.environ.get("DEMO2_DATA_URL", "{DATA_URL}")\n\n\n'
     + (HERE / "widgets_common.py").read_text() + "\n\n"
     + (HERE / "d2_widgets.py").read_text(), hidden=True)

md(r"""
## 1. The model at home *(4 minutes)*

Before we take the model to the Philippines, look at how it does on home ground:
**79 OpenEarthMap tiles** of 500 m from 13 cities in Europe, Africa and Asia that
the model was **not trained on**, with every pixel labelled by hand on the aerial image.
Labels do not get cleaner than this, so this is the best case.

For each tile there are four images of the same place:

* **aerial**: the real 0.5 m image the labels were drawn on. This is what the model knows.
* **Sentinel-2** (the average of the 8 dates the super-resolution model used, enlarged),
  **Stage 1** and **Stage 2**: the same three versions you will see for your place. The
  Sentinel-2 images are from 2025 and the aerial images are older, so a few buildings may
  have changed; that counts a little against these three.

**How the scores work** (the same in the whole notebook):

* **Recall**: the share of the true buildings (or roads) that the model found.
  **Precision**: of what the model marks as building, the share that is right. Each alone
  can be gamed: a map that says "building" everywhere has a perfect recall, and a map that
  marks one sure building has a perfect precision.
* **F1** combines the two: 0 = nothing right, 1 = perfect. **IoU** (intersection over
  union) is the share both maps agree on, out of everything either map calls a building. It
  is always lower than F1 (IoU = F1 / (2 − F1)) and ranks the images in the same order; it is
  the number most papers report.
* **A pixel counts**: two maps never line up to the metre. *Pixel-exact* counts only the very
  same pixel; *within 2.5 m* forgives a shift of one pixel; *within 5 m* forgives two. The
  more you forgive, the higher every score.
* **Two useless maps to compare with** (tick them on or off):
  * a map that says **"building" everywhere** (dashed line). In a dense city it scores high,
    because almost every spot is near a building. A map is only worth something where it is
    clearly above this line.
  * a map that says **"no building" anywhere** (dotted line). It scores 0 on F1, IoU and
    recall, and has no precision at all: it marks nothing. Yet 83 % of its pixels are right
    here, and 95 % in Nueva Ecija, because most pixels are not buildings. That is why maps of
    rare things are not scored by the share of pixels right.

* **The confusion matrix** (under the examples) shows, for each class drawn by hand, which
  class the model gave those pixels. The diagonal is right; everything else is a confusion.
  It counts pixel-exact: a pixel has to land in one box, so the tolerance does not apply.

Run the cell and try the switches: they change every score in this notebook. Then click
through the three example tiles, and compare the confusion matrix of the aerial image with
that of Sentinel-2: where do the buildings go?
""")
code("model_at_home(DATA_URL)")
md(OEM_TEXT)

md(rf"""
## 2. Pick your place *(3 minutes)*

Now the model leaves home. Take the place you used this morning, so you already know what its
images look like. (If you used your own place this morning, take the listed place you know
best.)

| Place | What is there |
|---|---|
{place_rows}

For each place there are three images of the same 2 km square:

* **Sentinel-2**: the free 10 m image, enlarged to 2.5 m pixels. This is the "do nothing"
  option.
* **Stage 1**: 8 Sentinel-2 images combined. Nothing invented.
* **Stage 2**: the full model, with added detail.

Run the cell and choose your place in the menu (it loads in a few seconds). Move around with
the sliders; the small picture shows where you are. If you change the place later, every
step below follows: there is nothing to run again.
""")
code("pick_place(DATA_URL)")

md(r"""
## 3. Guess first *(1 minute)*

At home, the map from Stage 2 came much closer to the map from the aerial image than the map
from Sentinel-2 did. Will that hold here? The model has never seen the Philippines: the roofs,
the streets and the light are different, and instead of hand-drawn labels we check it against
public maps.

Which image will give the best map of **buildings**, and of **roads**? Agree on a guess and
click it before you go on.
""")
code("guess()")

md(r"""
## 4. The maps *(3 minutes)*

This is the **"reuse"** path from Session 3: nobody labelled anything on super-resolved
images. We only fed the land-cover model three different images of your place.

Top row: the three images. Bottom row: the map the model drew from each. Move around and
compare. Where do the maps differ most?
""")
code("show_maps()")

md(r"""
## 5. Score against public maps *(5 minutes)*

There are no hand-drawn labels for your place. The reference is two public maps that anyone
can download for any place in the Philippines:

* **Open Buildings**: building footprints from Google, Microsoft and OpenStreetMap, combined
  by VIDA. They were made by a model from 50 cm images, so they are good but not perfect.
* **OpenStreetMap roads** (through Overture Maps). Roads are lines, so each one is widened to
  a typical width for its class (12 m for a motorway, 3 m for a farm track).

The scores work as in step 1, and the switches are the same (changing one changes all).
Press **Show the scores** to see them, and whether your guess was right.
""")
code("show_scores()")
md(r"""
Compare the three images with each other and with the dashed line, not with 1, and not with
step 1: the public maps were not drawn on these images, so even a perfect model would not
reach 1. A missing road in OpenStreetMap counts against the model. Try the three tolerances:
which conclusions change, and which stay? Then look at precision and recall: does
super-resolution help the model *find* more, or make *fewer false alarms*? (For recall the
dashed line is at 1: saying yes everywhere finds everything.)
""")

md(r"""
## 6. Hunt: one rescue, one failure *(7 minutes)*

A score hides where the map is right and where it is wrong. Look for yourself. In the bottom
row, **green** is right (the two maps agree, within the tolerance you chose), **blue** is a
false alarm (only the model says "building") and **red** is missed (only the public map says
so).

Move the view and find:

* a **rescue**: something the map from Sentinel-2 missed and the map from Stage 1 or Stage 2
  found;
* a **failure**: something the super-resolved map gets wrong. Is it a miss, a false alarm, or
  a building in the wrong shape? Could the public map be the one that is wrong?

You know this place: use that. Switch between **buildings** and **roads**, try
**pixel-exact** against **within 5 m** (a blue strip next to a red strip is often the same
building, a few metres apart), and write your two finds in the blue box (a few words each).
""")
code("hunt()")
md(r"""
**Your result card.** Run the cell; if you change an answer afterwards, press **Update the
card**. Enter your guess and your rescue or failure in the poll (the link is on the slide).
""")
code("result_card()")

md(r"""
---
## For the discussion: all five places

The same scores for every place. Where does super-resolution help most? Where does it make
no difference? Is that what Session 3 would predict?
""")
code("all_places_view(DATA_URL)")
md(RESULTS_TEXT)

md(r"""
## 7. Going further: fine-tune the model

We used the land-cover model **as it is**. It learned from aerial images of other countries,
and in steps 5 and 6 you saw what that costs: narrow streets it does not know, roofs it takes
for roads. The usual next step is to **fine-tune** it: keep everything it has learned, and
train it a little more on labelled examples from your own area.

**What you need**

* **Labels for your area.** Public maps (Open Buildings, OpenStreetMap) are a start, but you
  saw their errors; a few hundred tiles checked or drawn by people who know the place are
  worth more.
* **The images you will use.** Fine-tune on the same kind of image you will run the model on:
  if you will map from Stage 2, fine-tune on Stage 2.
* **A test area the model never sees during training**, to score it honestly, in the same way
  as in step 5.
* **A GPU for a few hours** (a free Colab GPU is enough for a first try).

In code it looks roughly like this (a sketch, not run here):

```python
import torch
from satlaspretrain_models.model import Model
from satlaspretrain_models.utils import Backbone, Head

model = Model(num_channels=3, multi_image=False, backbone=Backbone.SWINB, fpn=True,
              head=Head.SEGMENT, num_categories=8, weights=None)
state = torch.load("landcover_oem_satlas_swinb_fp16.pth")   # from Hugging Face, see below
model.load_state_dict({k: v.float() for k, v in state.items()})

# keep what it knows: the backbone learns slowly, the rest faster
backbone = list(model.backbone.parameters())
rest = [p for n, p in model.named_parameters() if not n.startswith("backbone.")]
opt = torch.optim.AdamW([{"params": backbone, "lr": 1e-5}, {"params": rest, "lr": 1e-4}],
                        weight_decay=1e-4)
model.train()
for images, labels in tiles_of_your_area:     # (B, 3, H, W) images; (B, H, W) classes 0-7
    _, loss = model(images, labels)
    opt.zero_grad()
    loss.backward()
    opt.step()
```

**One trap: compare fairly.** Once you train, train *each* input. Before the workshop we tried
the simplest version: a quick model trained from scratch on the west half of each area, on
each of the three images, and scored on the east half. Look at the table below: **the gap
between the images almost disappears.** Part of what super-resolution gave us above is that
it makes Sentinel-2 *look like* the images the land-cover model was trained on. A model
trained on Sentinel-2 itself learns to read Sentinel-2. So:

* if a good model trained on high-resolution images exists for your task, super-resolution
  lets you run it on free Sentinel-2;
* if you train or fine-tune your own model anyway, test whether super-resolution still helps
  before you rely on it. Sometimes plain Sentinel-2 is just as good.

Tomorrow's hackathon starts here, with expert labels and your own scenario.
""")
code("all_places_view(DATA_URL, own_model=True)")
md(OWN_TEXT)

md(r"""
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
OpenEarthMap tiles and labels: OpenEarthMap (Xia et al., 2023), CC BY-NC-SA 4.0.
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
