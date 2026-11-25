# SSTA mini-hackathon: would you use super-resolved imagery for this?

*SSTA workshop, 27 November 2026, 11:00–15:00. In the room and online.*

Your team gets a **mock policy brief**: a realistic question from a government office, such as
"which blocks should our field teams validate first?". By 14:15 you answer it on one slide:
**deploy**, **pilot** or **don't use** super-resolved (SR) Sentinel-2, with the numbers behind
it and the safeguards you would insist on.

There is no leaderboard and no coding. "Super-resolution doesn't help here" is a good answer.

## Pick one task

| Task | Briefs (choose one in the notebook, or write your own) | Notebook |
|---|---|---|
| [Informal settlements, Metro Manila](informal_settlements/README.md) | Where should the validation teams go first? · A settlement watch list for local governments? | [Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/informal_settlements/hackathon_informal_settlements.ipynb) |
| [Land cover around Hanoi](land_cover/README.md) | Dust inspections · Houses on protected farmland · Roads missing from the map · Trees to protect | [Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/land_cover/hackathon_land_cover.ipynb) |
| [Field boundaries of smallholder farms](field_boundaries/README.md) | Which villages get the farmer-registry teams? · Where does the farm census need a second enumerator? | [Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/field_boundaries/hackathon_field_boundaries.ipynb) |

## How it works

1. **Open the notebook** and choose **Runtime → Run all**. You need a Google account. Nothing
   to install; it runs in a minute.
2. **Choose your brief** and adapt it to a decision your own agency makes.
3. **Look at the images**: free Sentinel-2, SR stage 1, SR stage 2 and real high-resolution.
4. **Place your bet**: of your 20 field visits, how many will find what you look for with each
   kind of image? Then see the result.
5. **Check who is left out** and what the mistakes look like.
6. **Check the money**: what the images cost for your whole area, and whether SR can tell you
   where real images are worth buying.
7. **Recommend**: deploy, pilot or don't use, with safeguards. The notebook fills a card for
   your slide.

## Working as a team

One person shares their screen and operates the notebook. Everyone else has a role:

| Role | Job |
|---|---|
| Decision-maker | speaks for the office in the brief |
| Field lead | keeps the budget and the visits realistic |
| Sceptic | asks "what if the map is wrong?" |
| Rapporteur | fills the slide and presents |

If Colab does not open on your office network, join a teammate's screen: you can do the whole
exercise without touching the notebook.

## Your slide

One slide per team, in the shared team-slide file: the decision, the numbers, your
recommendation, your safeguards and what would change your mind. Three minutes per team from
14:30, then questions from the "decision-maker".

---
The briefs are invented for this workshop. The data packages are workshop material: they
contain modified Copernicus Sentinel data and third-party labels and imagery under their own
licences (see each task README). Please do not redistribute them.
