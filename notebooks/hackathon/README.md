# SSTA mini-hackathon: is super-resolution a fit for your decision?

*SSTA workshop, 27 November 2026, 11:00–15:00. In the room and online.*

**Your team writes the brief.** Pick a decision that someone in your agencies really makes and
that an image could inform, such as "which 20 blocks do our field teams visit this quarter?".
Then walk through what it takes to judge whether super-resolved (SR) Sentinel-2 fits. By 14:15
you answer on one slide: **pilot it**, **test it first** or **not a fit**, with your test plan.

There is no leaderboard and no coding. "Super-resolution is not a fit here" is a good answer.

## Start here

| Notebook | What it is |
|---|---|
| **[Your scenario](scenario/README.md)** | The hackathon. [Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/scenario/hackathon_scenario.ipynb) |

## How it works

1. **Open the notebook** and choose **Runtime → Run all**. You need a Google account. Nothing
   to install.
2. **Write your scenario** (before lunch): who decides what, and how often; what the image must
   show and how big it is; the number you would report, and the **minimum** you need.
3. **Choose your area and dates** (before lunch): a ready-made area whose pictures come with
   the notebook, or a place of your own (up to 2 km × 2 km; the SR service makes it while you
   are at lunch). See which Sentinel-2 images exist.
4. **Check the money**: what the images cost for your whole area, and what real
   high-resolution images would have to save to be worth their price.
5. **Look**: free Sentinel-2, SR stage 1 and three strengths of SR stage 2, side by side.
   Commit to the image you would use.
6. **Cheat sheet and next steps**: what we measured for tasks like yours, whether it agrees
   with you, and how you would test it at home.
7. **Your slide**: the notebook fills a card for it.

## Measured cases

Three tasks for which experts labelled the ground, so results were measured. The cheat sheet
draws on them. If one fits your scenario, part 5 of the scenario notebook sends you there to
try your own budget and your own rule for a hit.

| Task | Decisions you can test | Notebook |
|---|---|---|
| [Informal settlements, Metro Manila](informal_settlements/README.md) | Where should the validation teams go first? · A settlement watch list for local governments? | [Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/informal_settlements/hackathon_informal_settlements.ipynb) |
| [Land cover around Hanoi](land_cover/README.md) | Dust inspections · Houses on protected farmland · Roads missing from the map · Trees to protect | [Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/land_cover/hackathon_land_cover.ipynb) |
| [Field boundaries of smallholder farms](field_boundaries/README.md) | Which villages get the farmer-registry teams? · Where does the farm census need a second enumerator? | [Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/field_boundaries/hackathon_field_boundaries.ipynb) |

## Working as a team

One person shares their screen and operates the notebook. Everyone else has a role:

| Role | Job |
|---|---|
| Decision-maker | speaks for the office that decides |
| Field lead | keeps the numbers realistic: places, visits, money |
| Sceptic | asks "what if the picture is wrong?" |
| Rapporteur | fills the slide and presents |

If Colab does not open on your office network, join a teammate's screen: you can do the whole
exercise without touching the notebook.

## Your slide

One slide per team, in the shared team-slide file: the scenario, what you found, your
recommendation and your test plan. Three minutes per team from 14:30, then one question from
the "decision-maker".

---
The starting scenarios in the notebooks are invented for this workshop. The data packages are
workshop material: they contain modified Copernicus Sentinel data and third-party labels and
imagery under their own licences (see each task README). Please do not redistribute them.
