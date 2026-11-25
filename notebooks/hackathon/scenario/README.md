# Your scenario: is super-resolution a fit for your decision?

[Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/scenario/hackathon_scenario.ipynb)
· [back to the hackathon page](../README.md)

Your team chooses a decision and checks whether super-resolved (SR) Sentinel-2 images fit it.

| Part | What you do | When |
|---|---|---|
| 0 | Runtime → Run all | 11:15 |
| 1 | Write your scenario: the decision, what the image must show and its size, your minimum | 11:15–11:50 |
| 2 | Choose your area. Your own area: send it before lunch | 11:50–12:00 |
| 3 | What would the images cost? | 13:00 |
| 4 | Compare five images and choose one | 13:25 |
| 5 | Cheat sheet and test plan | 13:55 |
| 6 | Your slide | 14:15 |

## The five images

| Image | What it is |
|---|---|
| Sentinel-2 | The free 10 m image, enlarged. The "do nothing" option. |
| SR stage 1 | Blends several Sentinel-2 images into one sharper image. Invents nothing. |
| SR stage 2, light | AI adds a little detail (`tau=100` in the SR service). |
| SR stage 2, standard | AI adds more detail. The service's default (`tau=250`). |
| SR stage 2, strong | AI adds the most detail (`tau=500`). Sharpest, and the most invented. |

## Areas

* **Ready-made areas.** We prepared these before the workshop: dense city, city edge, small
  farms, quarries, fishponds and coast, a river and its flood plain. No key needed. ★ marks
  places that experts mapped, so we have measured results for them.
* **Your own area.** Up to 2 km × 2 km. In part 2, type your email address (the service gives you
  a key for it), check which Sentinel-2 images exist, and press **Send**. The service
  takes 5 to 10 minutes.

## For organisers

The areas are listed in `tools/hackathon/areas.py`. `tools/hackathon/make_areas.py` runs them
on the SR service and writes `scenario_areas.zip` (upload it next to the other data packages)
and a contact sheet to check. `tools/hackathon/build.py` writes the notebook;
`tools/hackathon/test_nb.py` runs it and clicks through every control.

---
Contains modified Copernicus Sentinel data. The example scenarios are invented for this
workshop.
