# SSTA mini-hackathon: would you use super-resolved imagery for this?

*SSTA workshop, 27 November 2026, 11:00–15:00.*

Every team works on one question the whole afternoon: **would you use super-resolved (SR)
Sentinel-2 for this task in your agency, and how?** There is no leaderboard. Each team ends with
a verdict on a real decision (*deploy*, *pilot* or *don't use*), backed by numbers.

Pick one task:

| Task | Decision it feeds (example) | Notebook |
|---|---|---|
| [Informal settlements, Metro Manila](informal_settlements/README.md) | Which city blocks get a field survey | [Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/informal_settlements/hackathon_informal_settlements.ipynb) |
| [Land cover around Hanoi](land_cover/README.md) | Which places to inspect (e.g. dust from building sites, buildings on farmland) | [Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/land_cover/hackathon_land_cover.ipynb) |
| [Field boundaries of smallholder farms](field_boundaries/README.md) | Which areas get extension-worker visits | [Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/field_boundaries/hackathon_field_boundaries.ipynb) |

Each notebook:

1. downloads a small data package (7–170 MB) with the images, expert labels and the task model's
   predictions on each input, all computed before the workshop, so it runs on a normal
   computer in seconds;
2. shows how good the model is on Sentinel-2, SR stage 1, SR stage 2 and real high-resolution
   images, with examples and failure cases;
3. has a **decision cell**: you set a budget (e.g. 20 site visits), what counts as a hit, and
   what errors cost, and it counts how many of your picks would have been right with each input;
4. prints the numbers for your team slide.

You may use any AI assistant to change the code. Improving the model is optional; the verdict
is what counts.

**Your deliverable** is one slide (template from the facilitators): the scenario, the numbers,
the verdict, and what would change your mind. "SR doesn't help" and "SR hurts because of
invented detail" are valid results.

The optional part 8 of each notebook uses the SR service (your team's API key) to make SR
images of an area of your choice.

---
The data packages are workshop material. They contain modified Copernicus Sentinel data and
third-party labels and imagery under their own licences (see each task README). Please do not
redistribute them.
