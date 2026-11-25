"""Build the hackathon notebooks from hk.py and the texts below: the scenario notebook (teams
write their own brief) and the three task notebooks with measured results.

    python tools/hackathon/build.py          # writes notebooks/hackathon/*.ipynb

The helper code (hk.py, then the ipywidgets controls in hk_widgets.py) is pasted into a
hidden form cell of each notebook, so each notebook runs on its own in Colab with nothing but
the data download. Participants press Runtime > Run all once and then only use the controls,
which act at once (Colab ships ipywidgets 7.7.1); nothing waits for input and nothing after
part 3 shows a result before the team has placed its bet. Test with tools/hackathon/test_nb.py.
"""
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "notebooks" / "hackathon"
REPO = "adb-sr/sr-client"
BRANCH = "main"
DATA_URL = "https://huggingface.co/datasets/adbsr-internal/ssta-hackathon/resolve/main"

HELPERS = (HERE / "hk.py").read_text() + "\n\n" + (HERE / "hk_widgets.py").read_text()
SCENARIO_HELPERS = "\n\n".join([HELPERS, (HERE / "areas.py").read_text(),
                                (HERE / "hk_scenario.py").read_text()])


def md(s):
    return nbf.v4.new_markdown_cell(s.strip("\n"))


def code(s, hidden=False):
    c = nbf.v4.new_code_cell(s.strip("\n"))
    if hidden:
        c.metadata["cellView"] = "form"
    return c


FOLDER = {"hackathon_informal_settlements": "informal_settlements",
          "hackathon_land_cover": "land_cover",
          "hackathon_field_boundaries": "field_boundaries",
          "hackathon_scenario": "scenario"}


def badge(name):
    url = (f"https://colab.research.google.com/github/{REPO}/blob/{BRANCH}/notebooks/hackathon/"
           f"{FOLDER[name]}/{name}.ipynb")
    return f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})"


# --------------------------------------------------------------------------- shared cells

def header(name, title, question, data_note):
    return [md(f"""
# Mini-hackathon: {title}

*SSTA workshop, 27 November 2026.*

{badge(name)}

**Your team has a brief on its desk.** {question}

By 14:15, answer on one slide: **deploy**, **pilot** or **don't use**, with your numbers and
your safeguards. There is no leaderboard. "Super-resolution doesn't help here" is a good answer.

**No coding needed.** Everything was computed before the workshop. You press one button, then
scroll, click and discuss.

| Part | What you do | When |
|---|---|---|
| 0 | Start the notebook with one click | 11:20 |
| 1 | Choose your brief and make it yours | before lunch |
| 2 | Look at the images | before lunch |
| 3 | Place your bet, then see the result | 13:00 |
| 4 | Which places, and who is left out? | 13:25 |
| 5 | Is it worth the money? | 13:45 |
| 6 | Your recommendation | 14:00, slide by 14:15 |
| Going further | Map scores, your own code, your own area | only if time |

{data_note}
"""),
            md("""
## 0. Start with one click

1. In the top menu, choose **Runtime → Run all**.
2. Colab warns that Google did not write this notebook. Choose **Run anyway**.
3. Wait about a minute for the data, then scroll down.

After that, use only the **controls**: menus, sliders, buttons and text fields. They act at
once and save your answers. If a control does nothing, click the ▶ to the left of its cell.

**Working online?** One person shares their screen and operates the controls. Give out four
roles:

| Role | Job |
|---|---|
| Decision-maker | speaks for the office in the brief |
| Field lead | keeps the budget and the visits realistic |
| Sceptic | asks "what if the map is wrong?" |
| Rapporteur | fills the slide and presents |
"""),
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
**Four kinds of image.** Every place comes in four versions. The same computer model reads each:

| Name | What it is | Cost |
|---|---|---|
| **Sentinel-2** | The free 10 m satellite image, simply enlarged. The "do nothing" option. | free |
| **SR stage 1** | Super-resolution, careful: blends 8 Sentinel-2 images into one sharper image. Invents nothing. | computing only |
| **SR stage 2** | Super-resolution, full: adds realistic texture with AI. Sharper, but some detail is made up. | computing only |
| **Real high-res** | A commercial image, as if you had bought it. The best one can hope for. | paid per km² |
"""


def mission_cells(extra=""):
    return [md(f"""
## 1. Your brief

This is a **mock brief**: the office and the numbers are invented, the kind of decision is real.
Choose the one closest to your work, or write your own. {extra}

Then make it yours. Change the fields until they describe a decision someone in your agency
really makes:

* **Who decides**, and what?
* **Budget**: how many places can they act on?
* **Hit**: when is a place worth the visit?
* **Errors**: what does a wasted visit cost, and a missed place? Rough numbers are fine; the
  ratio matters.

Everything below follows your choice.
"""),
            code("mission(task)")]


def decision_cells(place, score, check, extra=""):
    return [md(f"""
## 3. Place your bet, then see the result

**How the count works.** The map is cut into square {place}. For each one, the model gives a
score: {score}. You visit the **highest-scoring {place}**, up to your budget. Then {check} show
which visits were **hits**.

1. **Check the settings.** They come from your brief.
2. **Place your bet.** How many of your visits will be hits with each kind of image?
3. **Read the result.** After that, any change to a setting updates everything below.
{extra}"""),
            code("decision_panel(task)"),
            md("""
**Reading the table.** *Hits*: visits that found what you were looking for. *Wasted visits*: the
rest of your budget. *Missed places*: hits you did not visit. *Cost*: wasted visits and missed
places, each times its cost. *Random*: no map at all. *Perfect*: the best your budget allows.

**Other budgets.** Does the advantage hold with fewer or more visits?
"""),
            code("sweep_view()")]


def picks_cells(extra=""):
    return [md(f"""
## 4. Which places, and who is left out?

A better score does not always change the decision, and an average hides who is missed.

* **Where the visits go.** An area with many hits and no visits is left out.
* **The same places?** How much the pick lists of two kinds of image overlap.
* **The places themselves.** Green frame: hit. Red frame: wasted visit. Below them: the most
  confident false alarms, and the clear hits nobody visits. For each false alarm, ask: would
  acting on it harm someone?
{extra}"""),
            code("picks_view()")]


def cost_cells(extra=""):
    return [md(f"""
## 5. Is it worth the money?

Free, super-resolved and real images differ in price by a factor of about a thousand. Here you
see your result next to the imagery bill for your **whole** area.

Also try a **mixed strategy**: a cheap kind of image screens everything, you buy real images
only for the places it flags, and you choose your visits there. Change the share you buy. Then
screen with plain Sentinel-2: does super-resolution earn its place?
{extra}"""),
            code("cost_view()")]


SLIDE_MD = """
## 6. Your recommendation

Answer the brief: choose a recommendation, say how you would use the map, and tick your
safeguards. The card collects everything for your slide and updates by itself.

**Your slide** has four parts:
1. **The decision**: who decides, budget, hit, cost of errors.
2. **The numbers**: hits per kind of image, and the cost.
3. **The recommendation**: *deploy*, *pilot* or *don't use*.
4. **Safeguards**, and what would change your mind.

Before you choose, the sceptic asks:
* Would you act on the map, or only use it to decide where to look?
* Who checks a flagged place?
* Who is harmed by a false alarm, and who by a miss?
* What is missing to run this for real?
"""


FURTHER_MD = """
---
# Going further (only if you have time)

Nothing below changes your recommendation.
"""


def code_cells(ideas, example):
    return [md(f"""
## B. Change the code

For teams with a programmer or an AI assistant. Ideas:
{ideas}

`current()` returns the decision of part 3 as it is set now. `decide`, `plot_decision`, `sweep`,
`visits_needed` and `screen_then_confirm` work on anything of the same shape. `peek(...)` shows
a result only after you have revealed part 3.
"""),
            code(example)]


def api_cells(places_code, note, lat, lon):
    return [md(f"""
## C. Super-resolve an area of your own

The SR service makes stage 1 and stage 2 images of any area up to 5 km × 5 km. Type the API key
(`srk_...`) and the service address from your team card, then press **Connect**. The ready-made
areas come back in seconds and cost nothing. A new area takes 3–6 minutes. Choose "My own
place" to try a place you know.

{note}
"""),
            code(places_code),
            code(f"sr_connect(READY_MADE, default_lat={lat}, default_lon={lon})")]


FOOTER = """
---
Contains modified Copernicus Sentinel data. Super-resolution: ADB SSTA model (stage 1 Sen4x,
stage 2 diffusion refiner). The briefs are invented for this workshop. Workshop material:
please do not redistribute the data packages.
"""


# --------------------------------------------------------------------------- informal settlements

def ifs():
    name = "hackathon_informal_settlements"
    cells = header(
        name, "informal settlements in Metro Manila",
        "A housing office must decide **where to send its field teams** to find informal "
        "settlements. It cannot afford new commercial images of the whole city. Would you use "
        "super-resolved Sentinel-2 for this, and how?",
        "*Data: informal-settlement outlines drawn by experts for 40 sample tiles (about "
        "20 km²) in Manila South and Quezon City.*")
    cells += [load_cell("ifs_manila", extras=("ifs_manila_hr",)),
              *mission_cells("The first is for a housing office, the second for a space "
                             "agency that serves local governments."),
              md(f"""
## 2. Look at the images

Experts outlined informal settlements on real high-resolution images. The sample tiles were
chosen to contain settlements, so settlements are far more common here than in the city as a
whole.

Six computer models learned to find informal settlements on real high-resolution images. They
have **never seen a super-resolved image**: we show them each kind of image and see what they
find. This is the "reuse a model you already have" path from Session 3.
{INPUTS_MD}
The real images are licensed for this workshop only. If they did not download, everything
still works; you just will not see those pictures.

**Look around, including failures.** Choose a tile (sorted from most to least informal
settlement). Top row: what the model sees. Bottom row: orange = flagged as informal, black
line = the experts' outline. Look for:
* places flagged on super-resolved images but not on real ones: **invented** settlements?
* settlements missed on every image: what do they look like?
* Would *you* find the settlement on the Sentinel-2 image?
"""),
              code("explore(task)"),
              *decision_cells(
                  "blocks", "the share of the block it flags as informal settlement",
                  "the experts' outlines",
                  "\n*Hits* is the mean of the six models. The *range* shows the unluckiest "
                  "and the luckiest model; in practice you have only one.\n"),
              *picks_cells(),
              *cost_cells(),
              md(SLIDE_MD),
              code("slide_card()"),
              md(FURTHER_MD + """
## A. What papers report: the map score

Papers judge a map pixel by pixel against the experts' outlines. **F1** combines false alarms
and misses: 0 % = nothing right, 100 % = perfect. "Lowest" and "highest" show the spread over
the six models. "Paper" is the value in our paper, which scores overlapping patches and so
differs slightly. Compare with part 3: does the best map score also give the best decision?
"""),
              code("ifs_f1_table(task)"),
              *code_cells("""
* **Threshold**: `ifs_units(task, cell_m=100, thr=0.3)` flags more pixels. Does a lower
  threshold help the Sentinel-2 or stage 1 inputs? (worked example in the next cell)
* **Score**: rank blocks by the mean probability instead of the share above the threshold
  (the arrays are in `task.arr(tile, "prob_stage2")`, values 0–255, one slice per model).
* **One model or six?** Use `preds[key][m]` for model `m` and see how much the decision depends
  on the model you happen to have.
* **Combine inputs**: e.g. visit a block only if both stage 1 and stage 2 flag it.""", """
units, preds, hit, res = current()   # the decision of part 3, as it is set now

# Worked example: a lower threshold (0.3) with the same block size, hit rule and budget
block_m = int(units["size"].iloc[0] * task.px)
units_low, preds_low = ifs_units(task, cell_m=block_m, thr=0.3)
hit_low = units_low.truth.values >= S["hit_at"]
peek(decide(units_low, preds_low, hit_low, S["budget"], S["cost_wasted"], S["cost_missed"], labels=labels))
"""),
              *api_cells("""
READY_MADE = {
    # name: area, date and options; run before the workshop, so they come back fast
    "Tondo and Baseco, Manila": dict(area=area_around(14.5960, 120.9620, km=3), date="2026-03-15"),
    "Payatas, Quezon City": dict(area=area_around(14.7130, 121.1000, km=3), date="2026-03-15"),
    "Manila South test area": dict(area=area_around(14.5560, 121.0136, km=2), date="2025-06-01"),
}
""", "There is no informal-settlement model in this part (its weights are not public). Use it to "
     "look: would *you* spot the settlements you know on stage 1 or stage 2?", 14.5960, 120.9620),
              md(FOOTER + "\nInformal-settlement outlines: ADB technical assistance, expert annotators. "
                 "Real high-resolution images: Google satellite imagery, workshop use only.")]
    return name, cells


# --------------------------------------------------------------------------- land cover (Hanoi)

HANOI_INPUTS_MD = INPUTS_MD.replace("A commercial image,", "A commercial image (Pléiades Neo),")


def hanoi():
    name = "hackathon_land_cover"
    cells = header(
        name, "land cover around Hanoi",
        "A city office must decide **which places to inspect or map first**: dusty building "
        "sites, houses on protected farmland, roads missing from the map, or trees to protect. "
        "Would you use super-resolved Sentinel-2 for this, and how?",
        "*Data: 92 tiles of 640 m × 640 m around Hanoi, Viet Nam (about 38 km²), where experts "
        "mapped seven kinds of land cover. Its mix of dense villages, rice fields, ponds and "
        "building sites is typical of the growing edge of many Asian cities, including Metro "
        "Manila, Bulacan and Pampanga.*")
    cells += [load_cell("hanoi_landcover", extras=("hanoi_landcover_hr",)),
              *mission_cells("The four briefs use the same map for different decisions, and "
                             "the answer differs between them."),
              md(f"""
## 2. Look at the images

Experts mapped seven kinds of land cover on real high-resolution images: **building, road,
water, tree, low vegetation, cropland, bare soil or sand**. About a third of the ground is
unlabelled (white in the expert map) and never counts.

One computer model learned to draw this map from real high-resolution images. It has **never
seen a super-resolved image**: we show it each kind of image and see what it draws. This is the
"reuse a model you already have" path from Session 3.
{HANOI_INPUTS_MD}
The real images are licensed for this workshop only. If they did not download, everything
still works; you just will not see those pictures.

**Look around, including failures.** Choose a land cover to sort the tiles by, then a tile. Top
row: what the model sees. Bottom row: the land cover it draws, with the expert map on the
right. The black line outlines your land cover in the expert map. Look for:
* buildings, roads or bare soil drawn on super-resolved images but not on real ones:
  **invented**?
* small things (a lane, a house in the fields, a building site) that only the real image shows;
* river sandbanks drawn as bare soil: a dust source, a sand mine, or a false alarm for you?
"""),
              code("explore(task)"),
              *decision_cells(
                  "cells", "the share of the cell it draws as the land cover you look for",
                  "the expert map",
                  "\nThere is one model here, so the table shows no range. Later, try the "
                  "other briefs in part 1: super-resolution changes some decisions, not "
                  "others.\n"),
              *picks_cells(),
              *cost_cells(),
              md(SLIDE_MD),
              code("slide_card()"),
              md(FURTHER_MD + """
## A. What papers report: the map score

Papers judge a map pixel by pixel against the expert map. **IoU** (intersection over union)
per land cover: 0 = nothing right, 1 = perfect. *mIoU* is the mean of the seven. "Paper" is the
value in our paper. Compare with part 3: the land cover that gains most pixel by pixel is not
always the one where the decision changes most.
"""),
              code("lc_metric_table(task)"),
              *code_cells("""
* **Combine classes**: e.g. buildings near water, or bare soil next to roads (the worked example
  in the next cell rebuilds "buildings in farmland" by hand, with your own shares).
* **Mix inputs**: e.g. inspect a cell only if both stage 1 and stage 2 draw bare soil there.
* The predicted maps are in `task.arr(tile, "pred_stage2")` (class numbers 0–6, in the order of
  the table in part A) if you want to compute your own score.""", """
units, preds, hit, res = current()   # the decision of part 3, as it is set now

# Worked example: buildings in farmland, by hand (cells with >= 5 % buildings and >= 30 % cropland)
u_b, p_b = lc_units(task, cell_m=80, target=0)
u_c, p_c = lc_units(task, cell_m=80, target=5)
hit_bf = (u_b.truth.values >= 0.05) & (u_c.truth.values >= 0.3)
score = {k: p_b[k] * (p_c[k] >= 0.3) for k in p_b}
peek(decide(u_b, score, hit_bf, 20, labels=labels))
"""),
              *api_cells("""
READY_MADE = {
    # name: area, date and options; run before the workshop, so they come back fast
    "Hanoi, Red River banks (the area of this dataset)": dict(area=area_around(21.0787, 105.7822, km=3), date="2025-11-15"),
    "Payatas, Quezon City": dict(area=area_around(14.7130, 121.1000, km=3), date="2026-03-15"),
}
""", "There is no land-cover model in this part. Use it to look: would *you* spot the building "
     "sites, sand yards or new roads you know on stage 1 or stage 2?", 21.0787, 105.7822),
              md(FOOTER + "\nLand-cover labels and Pléiades Neo images: benchmark of Retnanto et al. "
                 "(2026, IEEE JSTARS). Real high-resolution images: Pléiades Neo (Airbus), workshop "
                 "use only.")]
    return name, cells


# --------------------------------------------------------------------------- field boundaries

def ai4():
    name = "hackathon_field_boundaries"
    cells = header(
        name, "field boundaries of smallholder farms",
        "An agriculture office must decide **which areas its teams visit first** to reach "
        "small farms. It has no map of the fields. Would you use super-resolved Sentinel-2 for "
        "this, and how?",
        "*Data: AI4SmallFarms benchmark, 10 areas of about 5 km × 5 km in Viet Nam and "
        "Cambodia, with 51,062 field outlines drawn by experts. Fields average under one hectare, "
        "much like rice and corn farms in Central Luzon or Mindanao.*")
    cells += [load_cell("ai4_fields"),
              *mission_cells("The first looks for small farms; the second only needs a "
                             "count."),
              md("""
## 2. Look at the images

Experts drew every field in 10 areas. This dataset has **no real high-resolution images**, so
it works differently from the other two tasks: a separate computer model was **trained on each
kind of image**, three times each to see how much luck is involved. Each draws the fields it
sees. This is the "train a model on the images you will use" path from Session 3.

| Name | What it is | Cost |
|---|---|---|
| **Sentinel-2** | The free 10 m satellite image (typical value of 8 clear days), simply enlarged. The "do nothing" option. | free |
| **SR stage 1** | Super-resolution, careful: blends the same 8 images into one sharper image. Invents nothing. | computing only |
| **SR stage 2** | Super-resolution, full: adds realistic texture with AI. Sharper, but some detail is made up. | computing only |

**Look around, including failures.** Choose an area and a window size, then move the sliders.
Top row: the images, with the experts' field outlines in red. Bottom row: the fields each model
draws, in green. Look for fields split in two or merged with their neighbours, and for the hazy
area `46_vietnam`. The three trained models of each kind of image can differ: compare them.
"""),
              code("explore(task)"),
              *decision_cells(
                  "squares", "the **number of small fields** it draws in the square (a field "
                  "counts where its centre lies)", "the experts' outlines",
                  "\n*Hits* is the mean of the three trained models; the *range* shows the "
                  "worst and the best. A new square or field size takes about 15 seconds the "
                  "first time.\n"),
              *picks_cells("\nThe first table has one row per area. Look at `46_vietnam`, and "
                           "at areas that get no visit from any kind of image.\n"),
              *cost_cells("\nThis dataset has no real high-resolution images, so the mixed "
                          "strategy cannot be tested here. The bill is shown for scale.\n"),
              md(SLIDE_MD),
              code("slide_card()"),
              md(FURTHER_MD + """
## A. What papers report: the map score

A field counts as **found** when a drawn field overlaps it well (IoU > 0.5). **Field F1**
combines missed and invented fields (0 = nothing right, 1 = perfect). The second line is the
share of **small fields** (under 1,000 m²) found. Stage 1 finds the most fields; the invented
texture of stage 2 adds edges that are not field boundaries.
"""),
              code("""
pd.DataFrame(task.meta["metric_table"]).assign(input=lambda d: d.input.map(labels)).pivot(
    index="input", columns="metric", values="value").round(3)
"""),
              md("""
Many programmes only need a count: **how many farms are there?** Below, the number of fields
each model draws per area, against the experts' count. A count can be right for the wrong
reason: one field split in two and two fields merged still give the right number.
"""),
              code("ai4_tile_counts(task)"),
              *code_cells("""
* **Ignore tiny fields**: `ai4_units(task, cell_m=500, small_m2=2500, min_px=64)` drops drawn
  fields under 400 m², which are often fragments of one field.
* **Seeds**: `preds[key][s]` is the model trained with seed `s`. How much does your decision
  depend on which training run you happen to have?
* **Area, not count**: score squares by the share of their area in small fields.
* The boundary-probability maps are in `task.arr(area, "prob_stage1_s0")` if you want to draw
  your own fields.""", """
units, preds, hit, res = current()   # the decision of part 3, as it is set now
units.drop(columns="truth").head()
"""),
              *api_cells("""
READY_MADE = {
    "Nueva Ecija rice farms (Science City of Munoz)": dict(area=area_around(15.7150, 120.9050, km=3), date="2026-03-15"),
    "Nueva Ecija (as in practical demonstration 2)": dict(area=area_around(15.5784, 120.9726, km=2), date="2026-03-15"),
}
""", "There is no field model in this part. Use it to look: are the boundaries you know visible on "
     "stage 1? Does stage 2 draw boundaries that are not there?", 15.7150, 120.9050),
              md(FOOTER + "\nAI4SmallFarms (Persello et al. 2023): CC BY 4.0.")]
    return name, cells


# --------------------------------------------------------------------------- your scenario

def scenario():
    name = "hackathon_scenario"
    cells = [md(f"""
# Mini-hackathon: is super-resolution a fit for your decision?

*SSTA workshop, 27 November 2026.*

{badge(name)}

**Your team chooses the decision.** Pick one that an office in your agency makes regularly and
that a satellite image could support. Then check, step by step, whether super-resolved (SR)
Sentinel-2 images fit it.

By 14:15 you answer on one slide: **pilot it**, **test it first** or **not a fit**, and how you
would test it. There is no ranking. "Not a fit" is a good answer.

| Part | What you do | When |
|---|---|---|
| 0 | Start the notebook | 11:15 |
| 1 | Write your scenario | 11:15–11:50 |
| 2 | Choose your area. Your own area: send it **before lunch** | 11:50–12:00 |
| 3 | What would the images cost? | 13:00 |
| 4 | Compare the images and choose one | 13:25 |
| 5 | Cheat sheet and test plan | 13:55 |
| 6 | Your slide | 14:15 |

**No coding needed.** You type, click and discuss.
"""),
             md("""
## 0. Start the notebook

1. In the top menu, choose **Runtime → Run all**.
2. Colab warns that Google did not write this notebook. Choose **Run anyway**.
3. Wait about a minute, then scroll down.

After that, use only the **controls**: text fields, menus, sliders and buttons. Changes apply
at once and your answers are saved. If a control does nothing, click the ▶ to the left of its
cell. Keep this browser tab open over lunch.

**Working online?** One person shares their screen and operates the controls. Give out four
roles:

| Role | Job |
|---|---|
| Decision-maker | speaks for the office that decides |
| Field lead | keeps the numbers realistic: places, visits, money |
| Sceptic | asks "what if the image is wrong?" |
| Rapporteur | fills the slide and presents |
"""),
             code("# @title Helper functions (run this cell; you do not need to read it) { display-mode: \"form\" }\n"
                  + SCENARIO_HELPERS, hidden=True),
             code(f"""
import os

DATA_URL = os.environ.get("HK_DATA_URL", "{DATA_URL}")

get_areas(DATA_URL)
"""),
             md("""
## 1. Your scenario

Agree on **one decision** that an office makes regularly and that an image could support. Keep
it narrow: "which 20 blocks do we visit this quarter" works; "monitor urban growth" does not.

* **Who decides what, and how often?** How do they decide today?
* **What must the image show?** Name the thing and its size. A house is about 8 m, a farm road
  4 m, a car 2 m. Sentinel-2 pixels are 10 m; super-resolved pixels are 2.5 m.
* **Success.** Which number would you report to your director? What is the **minimum** you
  need, and why? What happens below it: wasted visits, people left out, a wrong notice? Would
  real images then be worth their price?

Write your answers before you look at any image. No idea after ten minutes? Open "Stuck?"
below the fields, or ask a facilitator.
"""),
             code("canvas()"),
             md("""
## 2. Your area and dates

Choose an area where your decision applies.

* **Ready-made areas.** We prepared these before the workshop. Take the one most like your
  scenario. No key needed.
* **Your own area.** Up to 2 km × 2 km. You need the API key on your team card. The SR service
  takes 5 to 10 minutes, so **send it before lunch**.

For each area you see **how many Sentinel-2 images exist** around your date. Super-resolution
needs several. In a cloudy season there may be too few.

**Five images.** You will compare them in part 4:

| Image | What it is |
|---|---|
| **Sentinel-2** | The free 10 m image, enlarged. The "do nothing" option. |
| **SR stage 1** | Blends several Sentinel-2 images into one sharper image. Invents nothing. |
| **SR stage 2, light** | AI adds a little detail. |
| **SR stage 2, standard** | AI adds more detail. The service's default. |
| **SR stage 2, strong** | AI adds the most detail. Sharpest, and the most invented. |
"""),
             code("area_panel()"),
             md("""
## 3. What would the images cost?

The area and how often you need a new map come from part 1. Real high-resolution images cost
about a thousand times more than super-resolution. So ask: **what must real images save to be
worth their price?**

* Enter what **one wasted visit** costs you.
* Read how many wasted visits a year real images must prevent.
* Try the **mix**: SR for the whole area to decide where to look, real images for a small part.
* Look at your **minimum** in part 1. If SR stays below it, are real images worth the extra
  money?
"""),
             code("money_panel()"),
             md("""
## 4. Compare the images and choose one

Press **Load the images**. Zoom to 250 m, move around, and look for the thing your decision
depends on.

* Can you already see it on Sentinel-2?
* What does stage 1 add? What does each strength of stage 2 add?
* Find a place you know. Does stage 2 show something that is **not there**? Stage 1 invents
  nothing, so detail that only stage 2 shows is a guess.
* "Two, large" puts two images side by side.

Then **choose**: which image would you use, and why? Part 5 opens after you choose.
"""),
             code("look_panel()"),
             md("""
## 5. Cheat sheet and test plan

The cheat sheet shows what we **measured** for tasks like yours, in other places, against maps
drawn by experts. Choose the task closest to yours.

* Does it agree with your choice in part 4? If not, that is your most useful finding today.
* Our results come from other places and other models. **How would you test this at home?**
  Fill in the test plan: what you check the map against, what you compare it with, and the
  pass mark (your minimum).
* If one of our measured tasks fits your scenario, open its notebook and try your own numbers
  there.
"""),
             code("cheat_panel()"),
             md("""
## 6. Your slide

Choose your recommendation and tick your safeguards. The card below collects all your answers.

**Your slide** has three parts:
1. **The scenario**: who decides what, what the image must show, your minimum.
2. **What you found**: the area, the cost, the image you would use, and whether the cheat
   sheet agrees. Add the image you downloaded in part 4.
3. **Recommendation and test plan**: *pilot it*, *test it first* or *not a fit*; how you would
   test it and what you need.
"""),
             code("scenario_card()"),
             md(FOOTER.replace("The briefs are invented", "The example scenarios are invented"))]
    return name, cells


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for build in (ifs, hanoi, ai4, scenario):
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
