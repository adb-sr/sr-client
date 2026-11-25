# SSTA mini-hackathon: is super-resolution a fit for your decision?

*SSTA workshop, 27 November 2026, 11:00–15:00. In the room and online.*

**Your team chooses the decision.** Pick one that an office in your agency makes regularly and
that a satellite image could support, such as "which 20 blocks do our field teams visit this
quarter?". Then check, step by step, whether super-resolved (SR) Sentinel-2 images fit it. By
14:15 you answer on one slide: **pilot it**, **test it first** or **not a fit**, and how you
would test it.

There is no ranking and no coding. "Not a fit" is a good answer.

## Start here

**[Your scenario](scenario/README.md)**: [open the notebook in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/scenario/hackathon_scenario.ipynb)

## How it works

1. **Start the notebook**: choose **Runtime → Run all**. You need a Google account. Nothing to
   install.
2. **Write your scenario** (before lunch): who decides what, and how often; what the image must
   show and how big it is; the number that shows success, and the **minimum** you need.
3. **Choose your area** (before lunch): a ready-made area, or your own (up to 2 km × 2 km; the
   SR service makes the images while you are at lunch).
4. **Check the cost**: what the images cost for your whole area, and what real high-resolution
   images must save to be worth their price.
5. **Compare five images**: free Sentinel-2, SR stage 1, and SR stage 2 at three strengths.
   Choose the one you would use.
6. **Cheat sheet and test plan**: what we measured for tasks like yours, whether it agrees with
   your choice, and how you would test this at home.
7. **Your slide**: the notebook collects your answers on a card.

## Measured tasks

For three tasks, experts mapped the ground, so we could measure results. The cheat sheet uses
them. If one fits your scenario, part 5 of the notebook links to it, and you can try your own
numbers there.

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
| Sceptic | asks "what if the image is wrong?" |
| Rapporteur | fills the slide and presents |

If Colab does not open on your office network, follow on a teammate's screen. You can take
part without touching the notebook.

## Your slide

One slide per team, in the shared team-slide file: the scenario, what you found, your
recommendation and your test plan. From 14:30, each team has three minutes, then one question
from the "decision-maker".

---
The example scenarios in the notebooks are invented for this workshop. The data packages are
workshop material: they contain modified Copernicus Sentinel data and third-party labels and
imagery under their own licences (see each task README). Please do not redistribute them.
