"""Build the three hackathon notebooks from hk.py and the task texts below.

    python tools/hackathon/build.py          # writes notebooks/hackathon/*.ipynb

The helper code (hk.py) is pasted into a hidden form cell of each notebook, so each
notebook runs on its own in Colab with nothing but the data download.
"""
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "notebooks" / "hackathon"
REPO = "adb-sr/sr-client"
BRANCH = "main"
DATA_URL = "https://huggingface.co/datasets/adbsr-internal/ssta-hackathon/resolve/main"

HELPERS = (HERE / "hk.py").read_text()


def md(s):
    return nbf.v4.new_markdown_cell(s.strip("\n"))


def code(s, hidden=False):
    c = nbf.v4.new_code_cell(s.strip("\n"))
    if hidden:
        c.metadata["cellView"] = "form"
    return c


FOLDER = {"hackathon_informal_settlements": "informal_settlements",
          "hackathon_building_damage": "building_damage",
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
            md("## 0. Setup\n\nRun the next two cells (Shift+Enter). The first one holds the helper "
               "code; you do not need to read it."),
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


def scenario_cells(example):
    return [md(f"""
## 4. Your scenario

Before you look at any decision numbers, agree as a team on **a real decision** this map would
feed. Be concrete; the numbers in part 5 only mean something for a concrete decision.

* **Who decides**, and what do they decide?
* **Budget**: how many places can they act on (visits, audits, teams, km² of map updates)?
* **What counts as a hit**: when is a place worth the visit?
* **What does a wasted visit cost**, and **what does a missed place cost**? Money, days, people,
  or harm. Rough is fine; the ratio matters most.

If you have no idea of your own, use the example below and change what does not fit your agency.
"""),
            code(example)]


def overlap_md():
    return md("""
## 6. Did super-resolution change *which* places you picked?

A better score does not always mean a different decision. The table shows how many of the
places picked with one input are also picked with another (100 % = the same list). Then look at
the places themselves: green frames are hits, red frames are wasted visits.
""")


SLIDE_MD = """
## 9. Numbers for your slide

Fill in the scenario in part 4 first. This cell prints everything your slide needs and saves the
chart as `my_slide_chart.png`.

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


def api_cells(places_code, note):
    return [md(f"""
## 8. Optional: super-resolve an area of your own

With the SR service you can make stage 1 and stage 2 images for any area up to 5 km × 5 km.
Your API key (`srk_...`) and the service address are on your team card; in Colab, store them
under **Secrets** (key icon on the left) as `SR_API_KEY` and `SR_API_URL`, or paste them when
asked. The areas below were run before the workshop, so they come back in seconds and cost
nothing. Each new area takes 3–6 minutes.

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
            code("""
def run_place(name, stages=("1", "2")):
    p = READY_MADE[name]
    job = sr.submit(p["area"], p["date"], stages=list(stages), **p.get("options", {}))
    job.wait()
    for w in job.warnings:
        print(f"[{w['code']}] {w['message']}")
    return job


def show_job(job, size=400, y0=None, x0=None):
    lr, s1, s2 = (job.open(f) for f in ("lr_reference.tif", "stage1_sr.tif", "stage2_sr.tif"))
    h, w = s2.sizes["y"], s2.sizes["x"]
    y0 = (h - size) // 2 if y0 is None else y0
    x0 = (w - size) // 2 if x0 is None else x0
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    for ax, da, t in zip(axes, (lr, s1, s2), ("Sentinel-2 (10 m)", "SR stage 1", "SR stage 2")):
        a = da.isel(band=[0, 1, 2], y=slice(y0, y0 + size), x=slice(x0, x0 + size)).values
        a = np.moveaxis(np.nan_to_num(a.astype("float32")), 0, -1)
        ax.imshow(autostretch((a / max(a.max(), 1e-6) * 255)))
        ax.set_title(t), ax.set_xticks([]), ax.set_yticks([])
    plt.tight_layout()
    plt.show()


job = run_place(list(READY_MADE)[0])
show_job(job)
""")]


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

Pick a tile in the list (sorted from most to least informal settlement) and run the cell. Top row: what the model sees. Bottom row: orange = flagged as informal (pixels
where the six models' mean probability is above 0.5), black line = expert outline. Look for:
* places flagged on super-resolved images but not on real images: **invented** settlements?
* settlements missed everywhere: what do they look like?
"""),
              code("""
TILE = "manila_south_r008_c006"  # @param ["manila_south_r008_c006", "manila_south_r011_c003", "quezon_city_100km2_r008_c005", "manila_south_r006_c014", "manila_south_r011_c001", "manila_south_r008_c001", "quezon_city_100km2_r006_c001", "quezon_city_100km2_r006_c004", "quezon_city_100km2_r002_c004", "quezon_city_100km2_r005_c001", "manila_south_r007_c002", "quezon_city_100km2_r007_c004", "manila_south_r005_c008", "quezon_city_100km2_r008_c000", "manila_south_r014_c000", "quezon_city_100km2_r008_c003", "manila_south_r006_c007", "manila_south_r006_c001", "quezon_city_100km2_r001_c007", "quezon_city_100km2_r007_c005", "quezon_city_100km2_r004_c000", "manila_south_r004_c002", "manila_south_r004_c004", "manila_south_r005_c004", "manila_south_r005_c005", "manila_south_r007_c009", "manila_south_r008_c012", "manila_south_r010_c009", "manila_south_r010_c011", "manila_south_r011_c004", "manila_south_r011_c009", "manila_south_r011_c011", "manila_south_r011_c012", "manila_south_r013_c011", "manila_south_r013_c012", "quezon_city_100km2_r000_c003", "quezon_city_100km2_r004_c002", "quezon_city_100km2_r004_c003", "quezon_city_100km2_r006_c005", "quezon_city_100km2_r007_c003"]
ifs_show(task, TILE)
"""),
              *scenario_cells('''
SCENARIO = dict(
    team="Team A",
    decision_maker="DHSUD regional office, informal settlement upgrading programme",
    decision="Which city blocks get a field survey this quarter",
    budget="20 survey visits, one 100 m x 100 m block each",
    hit="a block where at least a quarter of the area is informal settlement",
    cost_of_wasted_visit="1 survey day for a team of 2",
    cost_of_missed_place="a settlement left out of the programme for a year: about 3 survey days' worth",
)
'''),
              md("""
## 5. The decision cell

The map is cut into square blocks. For every block and every input, the models' map gives a
score: the share of the block flagged as informal. You visit the **highest-scoring blocks**, up
to your budget. Afterwards, the expert outlines tell us which visits were hits.

Change the settings to match your scenario, then run the cell. In Colab you can use the sliders.
"""),
              code("""
BUDGET = 20  # @param {type:"slider", min:5, max:100, step:5}
BLOCK_M = 100  # @param [50, 100, 200] {type:"raw"}
HIT_SHARE = 0.25  # @param {type:"slider", min:0.05, max:0.9, step:0.05}
COST_WASTED_VISIT = 1  # @param {type:"number"}
COST_MISSED_PLACE = 3  # @param {type:"number"}

units, preds = ifs_units(task, cell_m=BLOCK_M)
hit = units.truth.values >= HIT_SHARE
res = decide(units, preds, hit, BUDGET, COST_WASTED_VISIT, COST_MISSED_PLACE, labels=labels)
plot_decision(res, BUDGET, f"Survey {BUDGET} blocks of {BLOCK_M} m: how many are hits?")
plt.show()
res
"""),
              md("""
**How to read it.** *Hits* is the mean over the six task models; *range* shows the worst and
best model, a reminder that a single model can be lucky or unlucky. *Random* is what you would
expect without any map; *perfect* is the best your budget allows. *Cost* = wasted visits ×
their cost + missed places × their cost, in your units.

Does the advantage hold for a smaller or bigger budget?
"""),
              code("sweep(preds, hit, labels=labels, title='Share of visits that are hits')"),
              overlap_md(),
              code("""
overlap_table(preds, BUDGET, labels=labels)
"""),
              code("""
for key in ["s2", "stage2"]:
    picks = top_k(preds[key].mean(0), BUDGET)
    ifs_gallery(task, units, picks, key="stage2", hit=hit,
                title=f"The {BUDGET} blocks you would visit using {SHORT[key]} (shown on the stage 2 image)")

# Failure cases: stage 2's most confident false alarms, and the clearest settlements it ranks low
score = preds["stage2"].mean(0)
order = np.argsort(-score)
false_alarms = [i for i in order if not hit[i]][:8]
missed = [i for i in np.argsort(-units.truth.values) if i not in set(order[:BUDGET])][:8]
ifs_gallery(task, units, false_alarms, key="stage2", hit=hit, title="Stage 2: highest-scoring blocks that are NOT hits")
ifs_gallery(task, units, missed, key="stage2", hit=hit, title="Clearest settlements that stage 2 would NOT visit")
"""),
              code("""
# Look at one of them in detail (change the number to pick another)
i = false_alarms[0]
u = units.iloc[i]
ifs_show(task, u.scene, box=(u.y0, u.x0, u["size"]))
"""),
              md("""
## 7. Optional: improve the baseline

Only if you have time, and only if it helps your decision. Ideas:
* **Threshold**: `ifs_units(task, cell_m=BLOCK_M, thr=0.3)` flags more pixels. Does a lower
  threshold help the Sentinel-2 or stage 1 inputs?
* **Score**: rank blocks by the mean probability instead of the share above the threshold
  (the arrays are in `task.arr(tile, "prob_stage2")`, values 0–255, one slice per model).
* **One model or six?** Use `preds[key][m]` for model `m` and see how much the decision depends
  on the model you happen to have.
* **Combine inputs**: e.g. visit a block only if both stage 1 and stage 2 flag it.
"""),
              *api_cells('''
READY_MADE = {
    # name: area, date and options; run before the workshop, so they come back fast
    "Tondo and Baseco, Manila": dict(area=area_around(14.5960, 120.9620, km=3), date="2026-03-15"),
    "Payatas, Quezon City": dict(area=area_around(14.7130, 121.1000, km=3), date="2026-03-15"),
    "Manila South test area": dict(area=area_around(14.5560, 121.0136, km=2), date="2025-06-01"),
}
''', "There is no informal-settlement model in this part (its weights are not public). Use it to "
     "look: would *you* spot the settlements you know on stage 1 or stage 2?"),
              md(SLIDE_MD),
              code("slide_numbers(res, SCENARIO, BUDGET, task.meta['title'])"),
              md(FOOTER + "\nInformal-settlement outlines: ADB technical assistance, expert annotators. "
                 "Real high-resolution images: Google satellite imagery, workshop use only.")]
    return name, cells


# --------------------------------------------------------------------------- building damage

def xbd():
    name = "hackathon_building_damage"
    cells = header(
        name, "building damage after disasters",
        "After a typhoon, would you use super-resolved Sentinel-2 to decide **where to send damage "
        "assessment teams first**, and how?",
        "*Data: xBD benchmark, 1,577 areas of about 0.25 km² from five disasters (Hurricane "
        "Matthew in Haiti, floods in Nepal, the Santa Rosa wildfire, the Sunda Strait tsunami and "
        "the Fuego volcano eruption), with every building marked intact or damaged by experts.*")
    cells += [load_cell("xbd_damage"),
              md(f"""
## 1. The data

For each area there is an image **before** and **after** the event. Experts outlined every
building on the real high-resolution images (Maxar, about 0.5 m) and marked it intact or
damaged.

The task model was trained on the real high-resolution before-and-after images. It has **never
seen a super-resolved image**: we give it each input and see what it finds. It labels every
pixel as background, intact building or damaged building.
{INPUTS_MD}
Note: the Sentinel-2 images were taken on different days from the high-resolution ones, up to
a few weeks after the event, so some damage may already be cleared or rebuilt.
"""),
              code("""
# The Hurricane Matthew area with the largest share of damaged buildings among areas whose
# high-res image is complete (also the example in our paper)
example = "hurricane-matthew_00000089"
xbd_show(task, example)
"""),
              md("""
## 2. How good is the model on each input?

Pixel by pixel against the expert labels. **F1** combines false alarms and misses (0 = nothing
right, 1 = perfect). Two questions are scored separately: *where are the buildings?* and *which
buildings are damaged?*
"""),
              code("xbd_metric_table(task)"),
              md("""
**What this says.** Super-resolution helps the model **find buildings** (F1 from 0.31 to 0.54;
real images 0.79). It does **not** help it tell **damaged** from intact buildings (0.21 on
plain Sentinel-2 and on stage 2; stage 1 is worse). The rest of the notebook asks which of these
matters for **where you send teams**.

## 3. Look around, including failures

Pick an event and an area (1 = the most damaged area of that event) and run the cell. Rows: before, after, model output (blue intact, orange damaged). Look
for:
* damage the model sees on real images but not on super-resolved ones, and the reverse;
* areas where the after image is cloudy, hazy or taken long after the event.
"""),
              code("""
EVENT_VIEW = "hurricane-matthew"  # @param ["hurricane-matthew", "nepal-flooding", "santa-rosa-wildfire", "sunda-tsunami", "guatemala-volcano"]
RANK = 1  # @param {type:"slider", min:1, max:100, step:1}
# RANK 1 = the area of this event with the most damaged buildings, 2 = the next, ...
areas = task.scenes[task.scenes.event == EVENT_VIEW].sort_values("n_damaged_px", ascending=False)
xbd_show(task, areas.index[min(RANK, len(areas)) - 1])
"""),
              *scenario_cells('''
SCENARIO = dict(
    team="Team B",
    decision_maker="Provincial disaster office (PDRRMO), first 72 hours after a typhoon",
    decision="Which areas get a rapid damage assessment team first",
    budget="20 team deployments, one 0.25 km2 area each",
    hit="an area with at least 5,000 m2 of damaged buildings (about 50 houses)",
    cost_of_wasted_visit="1 team-day that could have gone to a badly hit area",
    cost_of_missed_place="relief to ~50 households delayed by days: about 5 team-days' worth",
)
'''),
              md("""
## 5. The decision cell

For every area and every input, the model's map gives a score: the square metres it labels as
**damaged** building (or as any building, if your decision is about where people live). You send
teams to the **highest-scoring areas**, up to your budget. Afterwards, the expert labels tell us
which deployments were hits.

Pick the event that is closest to your hazards. The Guatemala and Sunda events are too small to
rank. Then change the settings to match your scenario and run the cell.
"""),
              code("""
EVENT = "hurricane-matthew"  # @param ["hurricane-matthew", "nepal-flooding", "santa-rosa-wildfire", "all"]
TARGET = "damaged"  # @param ["damaged", "buildings"]
BUDGET = 20  # @param {type:"slider", min:5, max:100, step:5}
HIT_M2 = 5000  # @param {type:"number"}
COST_WASTED_VISIT = 1  # @param {type:"number"}
COST_MISSED_PLACE = 5  # @param {type:"number"}

units, preds = xbd_units(task, EVENT, target=TARGET)
hit = units.truth.values >= HIT_M2
res = decide(units, preds, hit, BUDGET, COST_WASTED_VISIT, COST_MISSED_PLACE, labels=labels)
plot_decision(res, BUDGET, f"{EVENT}: send {BUDGET} teams, how many reach a hit?")
plt.show()
res
"""),
              md("""
**How to read it.** *Hits* = deployments to an area that meets your hit rule. *Random* is what
you would expect without any map; *perfect* is the best your budget allows. *Cost* = wasted
deployments × their cost + missed areas × their cost, in your units. There is one task model
here, so there is no range.

Try `TARGET = "buildings"`: knowing **where buildings are** is a different decision (e.g. where
to pre-position relief) and may give a different answer. Does the advantage hold for other
budgets?
"""),
              code("sweep(preds, hit, labels=labels, title='Share of deployments that are hits')"),
              overlap_md(),
              code("overlap_table(preds, BUDGET, labels=labels)"),
              code("""
for key in ["s2", "stage2"]:
    picks = top_k(preds[key][0], BUDGET)
    xbd_gallery(task, units, picks, key="hr" if task.has_image["hr"] else "stage2", hit=hit,
                title=f"The {BUDGET} areas you would visit using {SHORT[key]} (after image; orange = damaged buildings)")

# Failure cases for stage 2: confident false alarms and badly hit areas it ranks low
score = preds["stage2"][0]
order = np.argsort(-score)
false_alarms = [i for i in order if not hit[i]][:8]
missed = [i for i in np.argsort(-units.truth.values) if i not in set(order[:BUDGET])][:8]
xbd_gallery(task, units, false_alarms, key="stage2", hit=hit, title="Stage 2: highest-scoring areas that are NOT hits")
xbd_gallery(task, units, missed, key="stage2", hit=hit, title="Worst-hit areas that stage 2 would NOT visit")
"""),
              code("""
# Look at one of them in detail (change the number to pick another)
xbd_show(task, units.iloc[missed[0]].scene)
"""),
              md("""
## 7. Optional: improve the baseline

Only if you have time, and only if it helps your decision. Ideas:
* **Damage share instead of damage area**: rank by damaged ÷ all building pixels. Does it help
  find the worst-hit areas, or only the small ones?
* **Mix inputs**: buildings from stage 2 (best at finding buildings) and damage from plain
  Sentinel-2. The predicted maps are in `task.arr(area, "pred_stage2")` (0 background, 1 intact,
  2 damaged).
* **Change, not state**: the model looks at before and after together and cannot use the change
  between them. A simple before/after difference of Sentinel-2 brightness inside predicted
  buildings is a cheap damage signal: try it.
"""),
              *api_cells('''
EVENT_DAY = "2021-12-16"   # Typhoon Odette (Rai) made landfall on Siargao
READY_MADE = {
    "Siargao, General Luna: before Odette": dict(
        area=area_around(9.7840, 126.1560, km=3), date="2021-12-15",
        options=dict(time_window={"days_before": 90, "days_after": 0})),
    "Siargao, General Luna: after Odette": dict(
        area=area_around(9.7840, 126.1560, km=3), date="2021-12-17",
        options=dict(time_window={"days_before": 0, "days_after": 60})),
}
''', "December is cloudy in Siargao, so these may have few clear Sentinel-2 images: check "
     "`sr.estimate(...)` and the `low_diversity` warning. Compare before and after: would you "
     "trust what you see for a damage decision?"),
              md(SLIDE_MD),
              code("slide_numbers(res, SCENARIO, BUDGET, task.meta['title'])"),
              md(FOOTER + "\nxBD (Gupta et al. 2019; Maxar Open Data / xView2): CC BY-NC-SA 4.0, "
                 "non-commercial use.")]
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

Pick an area and a 1 km window and run the cell. Look for fields that are split in two, or merged with their
neighbours, and for the hazy area `46_vietnam`, where plain Sentinel-2 nearly fails.
"""),
              code("""
AREA = "16_cambodia"  # @param ["12_cambodia", "16_cambodia", "21_cambodia", "26_vietnam", "27_vietnam", "30_vietnam", "46_vietnam", "56_vietnam", "58_cambodia", "8_cambodia"]
Y0 = 800  # @param {type:"slider", min:0, max:1700, step:100}
X0 = 800  # @param {type:"slider", min:0, max:1700, step:100}
# a 1 km window (400 x 400 pixels of 2.5 m) starting Y0 pixels from the top and X0 from the left
ai4_show(task, AREA, y0=Y0, x0=X0, size=400)
"""),
              *scenario_cells('''
SCENARIO = dict(
    team="Team C",
    decision_maker="Department of Agriculture regional office, smallholder support programme",
    decision="Which 500 m x 500 m squares get an extension-worker visit to enrol small farms",
    budget="30 visits",
    hit="a square with at least 30 fields smaller than 0.25 ha",
    cost_of_wasted_visit="1 extension-worker day",
    cost_of_missed_place="~30 smallholders not enrolled this season: about 2 worker-days' worth",
)
'''),
              md("""
## 5. The decision cell

The areas are cut into squares. For every square and every input, the model's fields give a
score: the **number of small fields** in the square (counted by the field's centre). You visit
the **highest-scoring squares**, up to your budget. Afterwards, the expert outlines tell us which
visits were hits. The first run takes about 15 seconds.
"""),
              code("""
BUDGET = 30  # @param {type:"slider", min:5, max:100, step:5}
SQUARE_M = 500  # @param [250, 500, 1000] {type:"raw"}
SMALL_FIELD_M2 = 2500  # @param {type:"number"}
HIT_FIELDS = 30  # @param {type:"number"}
COST_WASTED_VISIT = 1  # @param {type:"number"}
COST_MISSED_PLACE = 2  # @param {type:"number"}

units, preds = ai4_units(task, cell_m=SQUARE_M, small_m2=SMALL_FIELD_M2 or None)
hit = units.truth.values >= HIT_FIELDS
res = decide(units, preds, hit, BUDGET, COST_WASTED_VISIT, COST_MISSED_PLACE, labels=labels)
plot_decision(res, BUDGET, f"Visit {BUDGET} squares of {SQUARE_M} m: how many are hits?")
plt.show()
res
"""),
              md("""
**How to read it.** *Hits* is the mean over the three trained models; *range* shows the worst
and best. *Random* is what you would expect without any map; *perfect* is the best your budget
allows. Set `SMALL_FIELD_M2 = 0` to count all fields instead of small ones.

Does the advantage hold for a smaller or bigger budget?
"""),
              code("sweep(preds, hit, labels=labels, title='Share of visits that are hits')"),
              overlap_md(),
              code("overlap_table(preds, BUDGET, labels=labels)"),
              code("""
for key in ["s2", "stage1"]:
    picks = top_k(preds[key].mean(0), BUDGET)
    ai4_gallery(task, units, picks, key="stage1", hit=hit,
                title=f"The {BUDGET} squares you would visit using {SHORT[key]} (stage 1 image, red = reference fields)")

score = preds["stage2"].mean(0)
order = np.argsort(-score)
false_alarms = [i for i in order if not hit[i]][:8]
ai4_gallery(task, units, false_alarms, key="stage2", hit=hit,
            title="Stage 2: highest-scoring squares that are NOT hits (invented boundaries?)")
"""),
              code("""
# Look at one of them in detail (change the number to pick another)
u = units.iloc[false_alarms[0]]
ai4_show(task, u.scene, y0=int(u.y0), x0=int(u.x0), size=int(u["size"]))
"""),
              md("""
## 7. Optional: improve the baseline

Only if you have time, and only if it helps your decision. Ideas:
* **Ignore tiny fields**: `ai4_units(..., min_px=64)` drops drawn fields under 400 m², which
  are often fragments of one field.
* **Seeds**: `preds[key][s]` is the model trained with seed `s`. How much does your decision
  depend on which training run you happen to have?
* **Area, not count**: score squares by the share of their area in small fields.
* The boundary-probability maps are in `task.arr(area, "prob_stage1_s0")` if you want to draw
  your own fields.
"""),
              *api_cells('''
READY_MADE = {
    "Nueva Ecija rice farms (Science City of Munoz)": dict(area=area_around(15.7150, 120.9050, km=3), date="2026-03-15"),
    "Nueva Ecija (as in practical demonstration 2)": dict(area=area_around(15.5784, 120.9726, km=2), date="2026-03-15"),
}
''', "There is no field model in this part. Use it to look: are the boundaries you know visible on "
     "stage 1? Does stage 2 draw boundaries that are not there?"),
              md(SLIDE_MD),
              code("slide_numbers(res, SCENARIO, BUDGET, task.meta['title'])"),
              md(FOOTER + "\nAI4SmallFarms (Persello et al. 2023): CC BY 4.0.")]
    return name, cells


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for build in (ifs, xbd, ai4):
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
