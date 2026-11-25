"""Builds notebooks/demo2_use_cases.ipynb: Practical demonstration 2.

    python tools/demos/build_demo2.py

Like Demo 1 it zig-zags: each part has a one-line cell that everyone runs, where it helps a
collapsed "Under the hood" cell with the code and the method behind it, and a task for the
participants. Everything the notebook shows was computed before the workshop by
build_demo2_package.py; the notebook only downloads it. It needs no API key, no GPU and no
installation.
"""
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


def found(title, key):
    """A collapsed cell that shows one of the longer texts (what we found) when it is run."""
    code(f'# @title {title} {{ display-mode: "form" }}\nexplain("{key}")', hidden=True)


def hood(title, s):
    """A collapsed cell: Colab shows only its title and the run button until it is opened."""
    code(f'# @title Under the hood: {title} {{ display-mode: "form" }}\n' + s.strip("\n"),
         hidden=True)


place_default = "Cebu City and Mandaue"
assert place_default in PLACES

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


FINETUNE_TEXT = r"""
**What you need to fine-tune**

* **Labels for your area.** Public maps (Open Buildings, OpenStreetMap) are a start, but you
  saw their errors; a few hundred tiles checked or drawn by people who know the place are
  worth more.
* **The images you will use.** Fine-tune on the same kind of image you will run the model on:
  if you will map from Stage 2, fine-tune on Stage 2.
* **A test area the model never sees during training**, to score it honestly, as in part 5.
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
"""

md(r"""
# Practical demonstration 2: from super-resolved images to maps

*SSTA workshop, 26 November 2026. Goes with Session 3, "Sample use cases".*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo2_use_cases.ipynb)

Session 3's rule: **test super-resolution on a small labelled sample before you use it.**
Here you run that test for the place you worked on this morning.

One **land-cover model** draws all the maps. It was trained on real high-resolution images
only: it has never seen Sentinel-2, a super-resolved image, or the Philippines.

Same three beats as this morning, and no code to write:

* **▶ Look**: run the cell (**Shift + Enter**). Pictures and controls appear under it.
* **⚙ Under the hood** (optional): a collapsed cell with the code and the method. Double-click
  its title to open it.
* **✎ Your turn**: explore with the controls, in pairs.

## 0. Setup

Run the next cell. No key and no GPU needed.
""")
code('# @title Helper functions (run this cell; you do not need to read it) { display-mode: "form" }\n'
     + (HERE / "d2_helpers.py").read_text() + "\n\n"
     + as_code("PLACES", {k: {f: v[f] for f in ("lat", "lon", "date", "note")}
                          for k, v in PLACES.items()})
     + f'PLACE_DEFAULT = "{place_default}"\n'
     + f'DATA_URL = os.environ.get("DEMO2_DATA_URL", "{DATA_URL}")\n\n\n'
     + (HERE / "widgets_common.py").read_text() + "\n\n"
     + (HERE / "d2_widgets.py").read_text() + "\n\n"
     + as_code("FOUND", {"found_home": OEM_TEXT, "found_places": RESULTS_TEXT,
                         "found_own": OWN_TEXT, "finetune": FINETUNE_TEXT})
     + "NOTES.update(FOUND)\n", hidden=True)

# ---- part 1 ---------------------------------------------------------------------------------
md(r"""
## 1. The model at home *(8 minutes)*

**▶ Look.** First the model on home ground: tiles of 500 m, labelled by hand, from cities it
was not trained on. Top row: the hand-drawn labels, the **aerial** image the model knows, and
the three versions you will get for your place. Bottom row: the model's map from each.
""")
code("home_examples(DATA_URL)")
md(r"""
**✎ Your turn.** Click through the three examples. What does the map from Stage 2 get right,
and what does it miss?

**▶ Look.** Now in numbers, over all 79 tiles. **F1** runs from 0 (nothing right) to 1
(perfect). The **dashed line** is a useless map that says "building" everywhere: a map is
only worth something clearly above it.
""")
code("home_scores(DATA_URL)")
hood("how a score is counted", r"""
oem = get_oem(DATA_URL)                       # the scores of part 1, computed before the workshop
print(f"{oem['n_tiles']} tiles in {len(oem['cities'])} cities, labels drawn at "
      f"{oem['gsd_label_m']} m: {', '.join(oem['cities'])}\n")

counted = oem["scores"]["2.5"]["buildings"]   # try "0" or "5" (metres), and "roads"
print(f"{'map from':<12}{'recall':>8}{'precision':>11}{'F1':>7}{'IoU':>7}")
for name in ["aerial", "Sentinel-2", "Stage 1", "Stage 2", "everywhere"]:
    recall = counted[name]["recall"]          # share of the true buildings the model found
    precision = counted[name]["precision"]    # share of what the model marks that is right
    f1 = 2 * precision * recall / (precision + recall)
    iou = f1 / (2 - f1)
    print(f"{name:<12}{recall:>8.2f}{precision:>11.2f}{f1:>7.2f}{iou:>7.2f}")

explain("scores")
""")
md(r"""
**✎ Your turn.** Try the switches: they change every score in this notebook. In the
confusion matrix, compare the aerial image with Sentinel-2: where do the buildings go?
""")
found("What we found at home (open after your turn)", "found_home")

# ---- part 2 ---------------------------------------------------------------------------------
md(r"""
## 2. Your place *(5 minutes)*

**▶ Look.** Now the model leaves home. Choose the place you used this morning. You get three
images of the same 2 km square: **Sentinel-2** (enlarged), **Stage 1** and **Stage 2**.
""")
code("pick_place(DATA_URL)")
hood("what the data of your place holds", r"""
place = picked_place()                        # the place chosen in the menu above
print(place, "\n")

for name in INPUTS:
    image, model_map = place.images[name], place.maps[name]
    print(f"{name:<11} image {image.shape} (4 bands, reflectance 0-1);  "
          f"the model's map {model_map.shape} (one class per pixel)")
print("\nclasses:", dict(enumerate(place.classes)))
for task, public_map in place.refs.items():
    print(f"public map of {task}: {public_map[place.valid].mean():.0%} of the area")

fig_reference(place)                          # the public maps on the Stage 2 image
plt.show()

explain("package")
""")
md(r"""
**✎ Your turn.** Move to a spot you know with the sliders. If you change the place later,
everything below follows.

## 3. Guess first *(2 minutes)*

**✎ Your turn.** The model has never seen the Philippines. Which image will give the best
map of **buildings**, and of **roads**? Click your guess before you go on.
""")
code("guess()")

# ---- part 4 ---------------------------------------------------------------------------------
md(r"""
## 4. The maps *(5 minutes)*

**▶ Look.** Top row: the three images. Bottom row: the map the same model drew from each.
Nobody labelled or trained anything on these images.
""")
code("show_maps()")
hood("how the maps were made", r"""
place = picked_place()

# how much of the area the model gives to each class, from each image (%)
valid = place.valid                           # where the images have data
shares = pd.DataFrame({name: np.bincount(place.maps[name][valid], minlength=8) / valid.sum()
                       for name in INPUTS}, index=place.classes)
print((100 * shares).round(0).astype(int).to_string())

explain("model")
""")
md(r"""
**✎ Your turn.** Where do the three maps differ most? What does the map from Sentinel-2 make
of the buildings?
""")

# ---- part 5 ---------------------------------------------------------------------------------
md(r"""
## 5. Hunt: one rescue, one failure *(8 minutes)*

**▶ Look.** Now check the maps against two public maps: **Open Buildings** and
**OpenStreetMap roads**. **Green** is right, **blue** is a false alarm (only the model says
"building"), **red** is missed (only the public map says so).
""")
code("hunt()")
md(r"""
**✎ Your turn.** Find a **rescue** (Sentinel-2 missed it, super-resolution found it) and a
**failure** (the super-resolved map is wrong; or is the public map wrong?). Try roads too.
Write both in the blue box.
""")

# ---- part 6 ---------------------------------------------------------------------------------
md(r"""
## 6. The scores *(8 minutes)*

**▶ Look.** The same comparison in numbers, counted as in part 1. Press **Show the scores**
to see them, and whether your guess was right.
""")
code("show_scores()")
hood("the score of your place, counted in code", r"""
place = picked_place()
task, metres = "buildings", 2.5               # try "roads", and 0 or 5 metres

truth = place.refs[task]                      # the public map: True where it has a building
valid = place.valid                           # where the images have data

print(f"{task}, {tol_text(metres)}\n{'map from':<22}{'recall':>8}{'precision':>11}{'F1':>7}")
maps = {name: place.prediction(task, name) for name in INPUTS}   # True where the model says so
maps['"yes" everywhere'] = np.ones_like(valid)                    # the dashed line
for name, marked in maps.items():
    # near(x, metres): True wherever x has a pixel within that distance
    recall = (truth & near(marked, metres) & valid).sum() / max((truth & valid).sum(), 1)
    precision = (marked & near(truth, metres) & valid).sum() / max((marked & valid).sum(), 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    print(f"{name:<22}{recall:>8.2f}{precision:>11.2f}{f1:>7.2f}")

explain("public")
""")
md(r"""
**✎ Your turn.** Compare the three images with each other and with the dashed line, not with
1: the public maps have errors too. Try the tolerances: what changes, what stays? Does
super-resolution help the model *find* more (recall) or make *fewer false alarms*
(precision)?

**Your result card.** Run the next cell and enter your guess and your finds in the poll (the
link is on the slide).
""")
code("result_card()")

md(r"""
---
## For the discussion: all five places

Where does super-resolution help most? Where does it make no difference?
""")
code("all_places_view(DATA_URL)")
found("What we found in the five places", "found_places")

md(r"""
## 7. Going further: fine-tune the model

We used the model **as it is**. The usual next step is to **fine-tune** it on labelled
examples from your own area.

**One trap: compare fairly.** Before the workshop we trained a quick model on each of the
three images. Look at the chart: **the gap between the images almost disappears.** A model
trained on Sentinel-2 learns to read Sentinel-2. So:

* if a good model trained on high-resolution images exists for your task, super-resolution
  lets you run it on free Sentinel-2;
* if you train your own model anyway, test whether super-resolution still helps.

Tomorrow's hackathon starts here.
""")
code("all_places_view(DATA_URL, own_model=True)")
found("What we found with a model trained on each image", "found_own")
found("How to fine-tune: what you need, and a code sketch", "finetune")

md(r"""
**Before you use a map**

* **Check the warnings and the validity map** of every job. Near water, use Sentinel-2.
* **Spot-check** the map against a real image or a field visit before acting on it.
* **Use maps for areas, not single objects**: screening, planning, trends.
* **Each map shows a period** (45 days before and after the date), not a single day.

The land-cover model is public:
[adbsr-internal/satlas-downstream](https://huggingface.co/adbsr-internal/satlas-downstream).
The script that made this data:
[`build_demo2_package.py`](https://github.com/adb-sr/sr-client/blob/main/tools/demos/build_demo2_package.py).

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
