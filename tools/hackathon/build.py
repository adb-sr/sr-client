"""Build the three hackathon notebooks from hk.py and the task texts below.

    python tools/hackathon/build.py          # writes notebooks/hackathon/*.ipynb

The helper code (hk.py, then the ipywidgets controls in hk_widgets.py) is pasted into a
hidden form cell of each notebook, so each notebook runs on its own in Colab with nothing but
the data download. The controls act at once (Colab ships ipywidgets 7.7.1); test them by
setting widget values in code (see UI in hk_widgets.py).
"""
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "notebooks" / "hackathon"
REPO = "adb-sr/sr-client"
BRANCH = "main"
DATA_URL = "https://huggingface.co/datasets/adbsr-internal/ssta-hackathon/resolve/main"

HELPERS = (HERE / "hk.py").read_text() + "\n\n" + (HERE / "hk_widgets.py").read_text()


def md(s):
    return nbf.v4.new_markdown_cell(s.strip("\n"))


def code(s, hidden=False):
    c = nbf.v4.new_code_cell(s.strip("\n"))
    if hidden:
        c.metadata["cellView"] = "form"
    return c


FOLDER = {"hackathon_informal_settlements": "informal_settlements",
          "hackathon_land_cover": "land_cover",
          "hackathon_field_boundaries": "field_boundaries"}


def badge(name):
    url = (f"https://colab.research.google.com/github/{REPO}/blob/{BRANCH}/notebooks/hackathon/"
           f"{FOLDER[name]}/{name}.ipynb")
    return f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})"


# --------------------------------------------------------------------------- shared cells

def header(name, title, question, minutes_note):
    return [md(f"""
# Mini-hackathon: {title}

*SSTA workshop, 27 November 2026.*

{badge(name)}

**The question for your team:** {question}

There is no leaderboard. Your result is a **verdict** for a real decision in your agency:
*deploy*, *pilot* or *don't use*, backed by the numbers from this notebook. "Super-resolution
doesn't help here" is a perfectly good result.

**How this notebook works.** All model predictions were computed before the workshop, so
everything runs in a few seconds on a normal computer. You do not need a GPU. You may use any
AI assistant you like to change the code.

| Part | What you do | Time |
|---|---|---|
| 0–2 | Load the data, see what the model does on each input | 10 min |
| 3 | Look at examples, including failures | 10 min |
| 4 | Write down **your** scenario | 15 min |
| 5–6 | The decision cell: does super-resolution change your decision? | main work |
| 7–8 | Optional: improve the baseline, or try your own area | if time |
| 9 | Numbers for your slide | 15 min |

{minutes_note}
"""),
            md("## 0. Setup\n\nRun the cells one by one (Shift+Enter), each once. The first one "
               "holds the helper code; you do not need to read it. Most cells show **controls** "
               "(menus, sliders, buttons, text fields): they act at once, so you do not need to "
               "run the cell again after changing them. Your answers are saved as you type. If a "
               "control seems to do nothing, run its cell again."),
            code("# @title Helper functions (run this cell; you do not need to read it) { display-mode: \"form\" }\n"
                 + HELPERS, hidden=True)]


def load_cell(task, extras=()):
    ex = f", extras={tuple(extras)!r}" if extras else ""
    return code(f"""
import os

DATA_URL = os.environ.get("HK_DATA_URL", "{DATA_URL}")

task = get_task("{task}", DATA_URL{ex})
labels = {{k: SHORT[k] for k in task.inputs}}
task
""")


INPUTS_MD = """
**The inputs.** Every place in this dataset comes in up to four versions, and the same task
model is applied to each:

| Name in this notebook | What it is |
|---|---|
| **Sentinel-2** | the free 10 m image, enlarged to 2.5 m pixels by plain interpolation (bicubic). This is the "do nothing" option. |
| **SR stage 1** | our model's first stage: combines 8 Sentinel-2 images into one sharper 2.5 m image. Conservative: it does not invent texture. |
| **SR stage 2** | the full model: stage 1 plus the diffusion refiner (τ = 250), which adds realistic texture. Sharper, but some detail is made up. |
| **Real high-res** | the real commercial image resampled to 2.5 m: the ceiling, what you would get if you bought imagery. |
"""


def scenario_cells():
    return [md("""
## 4. Your scenario

Before you look at any decision numbers, agree as a team on **a real decision** this map would
feed. Be concrete; the numbers in part 5 only mean something for a concrete decision.

* **Who decides**, and what do they decide?
* **Budget**: how many places can they act on (visits, audits, teams, km² of map updates)?
* **What counts as a hit**: when is a place worth the visit?
* **What does a wasted visit cost**, and **what does a missed place cost**? Money, days, people,
  or harm. Rough is fine; the ratio matters most.

Type your answers into the fields: they are saved as you type and end up on your slide card in
part 9. The grey text is an example; if you have no idea of your own, the button copies the
example into the empty fields, and you change what does not fit your agency.
"""),
            code("scenario(task)")]


def overlap_cells():
    return [md("""
## 6. Did super-resolution change *which* places you picked?

A better score does not always mean a different decision. The table shows how many of the
places picked with one input are also picked with another (100 % = the same list). Then look at
the places themselves: green frames are hits, red frames are wasted visits. Choose the input
whose picks you want to see; below them are its most confident false alarms and the clear hits
it would not visit. Everything here follows the settings of part 5.
"""),
            code("picks_view()")]


SLIDE_MD = """
## 9. Numbers for your slide

Choose your verdict below. The card collects your scenario (part 4), the decision settings
(part 5) and your answers; it follows any change by itself. The button downloads the chart.

**Your slide** (one slide, template from the facilitators) has four parts:
1. **Scenario**: who decides, budget, what a hit is, what errors cost.
2. **Numbers**: hits for Sentinel-2, SR stage 1, SR stage 2 (and real high-res if you have it).
3. **Verdict**: *deploy*, *pilot* or *don't use*, and for which decision.
4. **What would change your mind**: data, validation, partners, costs.

Questions to discuss before you write the verdict:
* Would you act on the map directly, or only use it to decide where to look?
* Who checks the output, and what would make them stop trusting it?
* What is missing to run this for real: data, validation, partners?
"""


def api_cells(places_code, note, lat, lon):
    return [md(f"""
## 8. Optional: super-resolve an area of your own

With the SR service you can make stage 1 and stage 2 images for any area up to 5 km × 5 km.
Your API key (`srk_...`) and the service address are on your team card; in Colab, store them
under **Secrets** (key icon on the left) as `SR_API_KEY` and `SR_API_URL`, or paste them when
asked. The ready-made areas were run before the workshop, so they come back in seconds and cost
nothing. A new area takes 3–6 minutes, and the button waits until it is done. You can add your
own areas to `READY_MADE`, or choose "My own place" in the menu.

{note}
"""),
            code('%pip install -q "sr-client[geo,viz] @ git+https://github.com/adb-sr/sr-client@v0.1.0"'),
            code("""
import getpass

from sr_client import SRClient, area_around


def secret(name, prompt):
    if os.environ.get(name):
        return os.environ[name]
    try:
        from google.colab import userdata
        return userdata.get(name)
    except Exception:
        return getpass.getpass(prompt)


sr = SRClient(secret("SR_API_KEY", "API key (srk_...): "), url=secret("SR_API_URL", "Service URL: "))
sr.me()["budget"]
"""),
            code(places_code),
            code(f"sr_panel(sr, READY_MADE, default_lat={lat}, default_lon={lon})")]


FOOTER = """
---
Contains modified Copernicus Sentinel data. Super-resolution: ADB SSTA model (stage 1 Sen4x,
stage 2 diffusion refiner). Workshop material: please do not redistribute the data packages.
"""


# --------------------------------------------------------------------------- informal settlements

def ifs():
    name = "hackathon_informal_settlements"
    cells = header(
        name, "informal settlements in Metro Manila",
        "Would you use super-resolved Sentinel-2 to decide **where to send survey teams** to find "
        "and verify informal settlements, and how?",
        "*Data: expert-drawn informal-settlement outlines for 40 sample tiles (about 20 km²) in "
        "Manila South and Quezon City.*")
    cells += [load_cell("ifs_manila", extras=("ifs_manila_hr",)),
              md(f"""
## 1. The data

Experts outlined informal settlements on real high-resolution images (Google satellite imagery,
about 0.5 m). The tiles were chosen to contain informal settlements of different sizes, so
settlements are much more common here than in the city as a whole.

Six task models were trained on the real high-resolution images (resampled to 2.5 m). They have
**never seen a super-resolved image**: we simply give them each input and see what they find.
This is the "reuse a model you already have" path from Session 3.
{INPUTS_MD}
The real high-resolution images are licensed for this workshop only. If they did not
download, everything still works: you just will not see those pictures.
"""),
              code("""
# The tile with the most informal settlement: images (top) and what the models flag (bottom)
example = task.scenes.informal_share.idxmax()
ifs_show(task, example)
"""),
              md("""
## 2. How good is the model on each input?

The usual way to judge a map: pixel by pixel against the expert outlines. **F1** combines false
alarms and misses: 0 % = nothing right, 100 % = perfect. "Lowest" and "highest" show the spread
over the six task models; "paper" is the value in our paper, which scores overlapping patches
and so differs slightly.
"""),
              code("ifs_f1_table(task)"),
              md("""
**What this says.** On plain Sentinel-2 the models find almost nothing; on super-resolved images
they find about half of what they find on real high-resolution images. Stage 2, with its
synthesised roof texture, does best. But a pixel score is not a decision. The rest of the
notebook asks whether these differences change **where you would send people**.

## 3. Look around, including failures

Choose a tile in the menu (sorted from most to least informal settlement); the picture follows
at once. Top row: what the model sees. Bottom row: orange = flagged as informal (pixels where the
six models' mean probability is above the threshold, 0.5 unless you move the slider), black
line = expert outline. You can also look at one model at a time. Look for:
* places flagged on super-resolved images but not on real images: **invented** settlements?
* settlements missed everywhere: what do they look like?
"""),
              code("explore(task)"),
              *scenario_cells(),
              md("""
## 5. The decision cell

The map is cut into square blocks. For every block and every input, the models' map gives a
score: the share of the block flagged as informal. You visit the **highest-scoring blocks**, up
to your budget. Afterwards, the expert outlines tell us which visits were hits.

Set the controls to match your scenario: the chart and the table follow at once, and so do
parts 6 and 9.
"""),
              code("decision_panel(task)"),
              md("""
**How to read it.** *Hits* is the mean over the six task models; *range* shows the worst and
best model, a reminder that a single model can be lucky or unlucky. *Random* is what you would
expect without any map; *perfect* is the best your budget allows. *Cost* = wasted visits ×
their cost + missed places × their cost, in your units.

Does the advantage hold for a smaller or bigger budget? (This chart follows part 5 too.)
"""),
              code("sweep_view()"),
              *overlap_cells(),
              md("""
## 7. Optional: improve the baseline

Only if you have time, and only if it helps your decision. Ideas:
* **Threshold**: `ifs_units(task, cell_m=100, thr=0.3)` flags more pixels. Does a lower
  threshold help the Sentinel-2 or stage 1 inputs? (worked example in the next cell)
* **Score**: rank blocks by the mean probability instead of the share above the threshold
  (the arrays are in `task.arr(tile, "prob_stage2")`, values 0–255, one slice per model).
* **One model or six?** Use `preds[key][m]` for model `m` and see how much the decision depends
  on the model you happen to have.
* **Combine inputs**: e.g. visit a block only if both stage 1 and stage 2 flag it.

`current()` gives the decision of part 5 as it is set now; `decide`, `plot_decision` and
`sweep` work on anything of the same shape.
"""),
              code("""
units, preds, hit, res = current()   # the decision of part 5, as it is set now

# Worked example: a lower threshold (0.3) with the same block size, hit rule and budget
block_m = int(units["size"].iloc[0] * task.px)
units_low, preds_low = ifs_units(task, cell_m=block_m, thr=0.3)
hit_low = units_low.truth.values >= S["hit_at"]
decide(units_low, preds_low, hit_low, S["budget"], S["cost_wasted"], S["cost_missed"], labels=labels)
"""),
              *api_cells('''
READY_MADE = {
    # name: area, date and options; run before the workshop, so they come back fast
    "Tondo and Baseco, Manila": dict(area=area_around(14.5960, 120.9620, km=3), date="2026-03-15"),
    "Payatas, Quezon City": dict(area=area_around(14.7130, 121.1000, km=3), date="2026-03-15"),
    "Manila South test area": dict(area=area_around(14.5560, 121.0136, km=2), date="2025-06-01"),
}
''', "There is no informal-settlement model in this part (its weights are not public). Use it to "
     "look: would *you* spot the settlements you know on stage 1 or stage 2?", 14.5960, 120.9620),
              md(SLIDE_MD),
              code("slide_card()"),
              md(FOOTER + "\nInformal-settlement outlines: ADB technical assistance, expert annotators. "
                 "Real high-resolution images: Google satellite imagery, workshop use only.")]
    return name, cells


# --------------------------------------------------------------------------- land cover (Hanoi)

HANOI_INPUTS_MD = INPUTS_MD.replace("the real commercial image resampled",
                                    "the real Pléiades Neo image resampled")


def hanoi():
    name = "hackathon_land_cover"
    cells = header(
        name, "land cover around Hanoi",
        "Would you use super-resolved Sentinel-2 to decide **which places to inspect** (for example "
        "open construction sites that raise dust, new buildings on farmland, or missing roads), "
        "and how?",
        "*Data: 92 tiles of 640 m × 640 m around Hanoi, Vietnam (about 38 km²), where experts "
        "mapped seven kinds of land cover on 0.5 m Pléiades Neo images. Hanoi's mix of dense "
        "villages, rice fields, ponds and building sites looks much like the edges of Metro Manila, "
        "Bulacan or Pampanga.*")
    cells += [load_cell("hanoi_landcover", extras=("hanoi_landcover_hr",)),
              md(f"""
## 1. The data

Experts mapped seven classes on real high-resolution images (Pléiades Neo, 0.5 m): **building,
road, water, tree, low vegetation, cropland, bare soil or sand**. About a third of the pixels
were left unlabelled (white in the expert map); they do not count anywhere.

One task model was trained on the real high-resolution images (resampled to 2.5 m). It has
**never seen a super-resolved image**: we give it each input and see what it draws. This is the
"reuse a model you already have" path from Session 3.
{HANOI_INPUTS_MD}
The real high-resolution images are licensed for this workshop only. If they did not
download, everything still works: you just will not see those pictures.
"""),
              code("""
# A well-labelled tile with much bare soil and sand: images (top), what the model draws (bottom)
example = task.scenes[task.scenes.valid_share >= 0.8].share_6.idxmax()
lc_show(task, example, target=6)
"""),
              md("""
## 2. How good is the model on each input?

Pixel by pixel against the expert map. **IoU** (intersection over union) per class: 0 = nothing
right, 1 = perfect. *mIoU* is the mean over the seven classes; "paper" is the value in our paper.
"""),
              code("lc_metric_table(task)"),
              md("""
**What this says.** Super-resolution closes about two thirds of the gap between Sentinel-2 and
real images (mIoU 0.32 → 0.47; real 0.57), and stage 2, with its synthesised texture, does best.
Look at the columns, though: trees, water and buildings gain the most, while bare soil and sand
barely move (0.19 → 0.25; real 0.34). A pixel score is not a decision. The rest of the notebook
asks whether these differences change **where you would send inspectors**, and the answer is not
always the one this table suggests.

## 3. Look around, including failures

Choose a class to sort the tiles by, then a tile; the picture follows at once. Top row: what the
model sees. Bottom row: the land cover it draws, and the expert map on the right; the black line
outlines the chosen class in the expert map. Look for:
* buildings, roads or bare soil drawn on super-resolved images but not on real ones: **invented**?
* small things (a lane, a house in the fields, a building site) that only the real image shows;
* river sandbanks drawn as bare soil: a dust source, a sand mine, or a false alarm for you?
"""),
              code("explore(task)"),
              *scenario_cells(),
              md("""
## 5. The decision cell

The map is cut into square cells. For every cell and every input, the model's map gives a
score: the share of the cell it draws as the land cover you look for. You inspect the
**highest-scoring cells**, up to your budget. Afterwards, the expert map tells us which
inspections were hits.

Set the controls to match your scenario: the chart and the table follow at once, and so do
parts 6 and 9. Try other classes too: some decisions change with super-resolution, others do
not.
"""),
              code("decision_panel(task)"),
              md("""
**How to read it.** *Hits* = inspections of a cell that meets your hit rule. *Random* is what
you would expect without any map; *perfect* is the best your budget allows. *Cost* = wasted
inspections × their cost + missed places × their cost, in your units. There is one task model
here, so there is no range.

Does the advantage hold for a smaller or bigger budget? (This chart follows part 5 too.)
"""),
              code("sweep_view()"),
              *overlap_cells(),
              md("""
## 7. Optional: improve the baseline

Only if you have time, and only if it helps your decision. Ideas:
* **Combine classes**: e.g. buildings on farmland (worked example in the next cell).
* **Mix inputs**: e.g. inspect a cell only if both stage 1 and stage 2 draw bare soil there.
* The predicted maps are in `task.arr(tile, "pred_stage2")` (class numbers 0–6, in the order of
  the table in part 2) if you want to compute your own score.

`current()` gives the decision of part 5 as it is set now; `decide`, `plot_decision` and
`sweep` work on anything of the same shape.
"""),
              code("""
units, preds, hit, res = current()   # the decision of part 5, as it is set now

# Worked example: buildings on farmland (cells with >= 5 % buildings and >= 30 % cropland)
u_b, p_b = lc_units(task, cell_m=80, target=0)
u_c, p_c = lc_units(task, cell_m=80, target=5)
hit_bf = (u_b.truth.values >= 0.05) & (u_c.truth.values >= 0.3)
score = {k: p_b[k] * (p_c[k] >= 0.3) for k in p_b}
decide(u_b, score, hit_bf, 20, labels=labels)
"""),
              *api_cells("""
READY_MADE = {
    # name: area, date and options; run before the workshop, so they come back fast
    "Hanoi, Red River banks (the area of this dataset)": dict(area=area_around(21.0787, 105.7822, km=3), date="2025-11-15"),
    "Payatas, Quezon City": dict(area=area_around(14.7130, 121.1000, km=3), date="2026-03-15"),
}
""", "There is no land-cover model in this part. Use it to look: would *you* spot the building "
     "sites, sand yards or new roads you know on stage 1 or stage 2?", 21.0787, 105.7822),
              md(SLIDE_MD),
              code("slide_card()"),
              md(FOOTER + "\nLand-cover labels and Pléiades Neo images: benchmark of Retnanto et al. "
                 "(2026, IEEE JSTARS). Real high-resolution images: Pléiades Neo (Airbus), workshop "
                 "use only.")]
    return name, cells


# --------------------------------------------------------------------------- field boundaries

def ai4():
    name = "hackathon_field_boundaries"
    cells = header(
        name, "field boundaries of smallholder farms",
        "Would you use super-resolved Sentinel-2 to find **the most fragmented smallholder "
        "farmland** for a farm-support programme, and how?",
        "*Data: AI4SmallFarms benchmark, 10 test areas of about 5 km × 5 km in Vietnam and "
        "Cambodia, with 51,062 field outlines drawn by experts. Fields average under one hectare, "
        "much like rice and corn farms in Central Luzon or Mindanao.*")
    cells += [load_cell("ai4_fields"),
              md("""
## 1. The data

Experts drew every field in 10 areas. There are **no real high-resolution images** in this
dataset, so this task works differently from the other two: a separate field-boundary model was
**trained on each input** (three times, with different random starts), and each one draws the
fields it sees. This is the "train a model on the images you will use" path from Session 3.

| Name in this notebook | What it is |
|---|---|
| **Sentinel-2** | the free 10 m image (median of 8 clear dates), enlarged to 2.5 m pixels |
| **SR stage 1** | our model's first stage, from the same 8 dates. Conservative: no invented texture. |
| **SR stage 2** | the full model (τ = 250): adds realistic texture, some of it made up |
"""),
              code("""
# A 1 km window in Cambodia: reference fields (red, top) and the fields each model draws (green, bottom)
ai4_show(task, "16_cambodia", y0=800, x0=800, size=400)
"""),
              md("""
## 2. How good is the model on each input?

A reference field counts as **found** when a drawn field overlaps it well (IoU > 0.5). **Field
F1** combines missed and invented fields (0 = nothing right, 1 = perfect). The second line is the
share of **small fields** (below 1,000 m²) found. Computed when the data package was built, from
the same files you have.
"""),
              code("""
pd.DataFrame(task.meta["metric_table"]).assign(input=lambda d: d.input.map(labels)).pivot(
    index="input", columns="metric", values="value").round(3)
"""),
              md("""
**What this says.** Stage 1 finds the most fields and nearly doubles the share of small fields
found. Stage 2 is in between: its invented texture adds edges that are not field boundaries. All
inputs miss most small fields.

A simpler question many programmes need answered: **how many farms are there?** Below, the number
of fields each model draws per area, against the reference.
"""),
              code("ai4_tile_counts(task)"),
              md("""
## 3. Look around, including failures

Choose an area, a window size and move the sliders; the picture follows at once. Look for fields
that are split in two, or merged with their neighbours, and for the hazy area `46_vietnam`, where
plain Sentinel-2 nearly fails. The three trained models (seeds) of each input can differ: compare
them.
"""),
              code("explore(task)"),
              *scenario_cells(),
              md("""
## 5. The decision cell

The areas are cut into squares. For every square and every input, the model's fields give a
score: the **number of small fields** in the square (counted by the field's centre). You visit
the **highest-scoring squares**, up to your budget. Afterwards, the expert outlines tell us which
visits were hits.

Set the controls to match your scenario: the chart and the table follow at once, and so do
parts 6 and 9. A new square size or field size takes about 15 seconds the first time.
"""),
              code("decision_panel(task)"),
              md("""
**How to read it.** *Hits* is the mean over the three trained models; *range* shows the worst
and best. *Random* is what you would expect without any map; *perfect* is the best your budget
allows. Choose **all fields** to count every field instead of the small ones.

Does the advantage hold for a smaller or bigger budget? (This chart follows part 5 too.)
"""),
              code("sweep_view()"),
              *overlap_cells(),
              md("""
## 7. Optional: improve the baseline

Only if you have time, and only if it helps your decision. Ideas:
* **Ignore tiny fields**: `ai4_units(task, cell_m=500, small_m2=2500, min_px=64)` drops drawn
  fields under 400 m², which are often fragments of one field.
* **Seeds**: `preds[key][s]` is the model trained with seed `s`. How much does your decision
  depend on which training run you happen to have?
* **Area, not count**: score squares by the share of their area in small fields.
* The boundary-probability maps are in `task.arr(area, "prob_stage1_s0")` if you want to draw
  your own fields.

`current()` gives the decision of part 5 as it is set now; `decide`, `plot_decision` and
`sweep` work on anything of the same shape.
"""),
              code("""
units, preds, hit, res = current()   # the decision of part 5, as it is set now
units.head()
"""),
              *api_cells('''
READY_MADE = {
    "Nueva Ecija rice farms (Science City of Munoz)": dict(area=area_around(15.7150, 120.9050, km=3), date="2026-03-15"),
    "Nueva Ecija (as in practical demonstration 2)": dict(area=area_around(15.5784, 120.9726, km=2), date="2026-03-15"),
}
''', "There is no field model in this part. Use it to look: are the boundaries you know visible on "
     "stage 1? Does stage 2 draw boundaries that are not there?", 15.7150, 120.9050),
              md(SLIDE_MD),
              code("slide_card()"),
              md(FOOTER + "\nAI4SmallFarms (Persello et al. 2023): CC BY 4.0.")]
    return name, cells


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for build in (ifs, hanoi, ai4):
        name, cells = build()
        nb = nbf.v4.new_notebook(cells=cells)
        nb.metadata.update({"colab": {"provenance": [], "toc_visible": True},
                            "kernelspec": {"name": "python3", "display_name": "Python 3"},
                            "language_info": {"name": "python"}})
        (OUT / FOLDER[name]).mkdir(exist_ok=True)
        nbf.write(nb, OUT / FOLDER[name] / f"{name}.ipynb")
        print("wrote", OUT / FOLDER[name] / f"{name}.ipynb")


if __name__ == "__main__":
    main()
