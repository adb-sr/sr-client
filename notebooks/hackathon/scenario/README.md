# Your scenario: is super-resolution a fit for your decision?

[Open in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/scenario/hackathon_scenario.ipynb)
· [back to the hackathon page](../README.md)

Your team writes its own brief and judges whether super-resolved (SR) Sentinel-2 fits it.

| Part | What you do | When |
|---|---|---|
| 0 | Runtime → Run all | 11:15 |
| 1 | Write your scenario: the decision, the thing the image must show and its size, your minimum | 11:15–11:50 |
| 2 | Choose your area and dates. A place of your own: send it before lunch | 11:50–12:00 |
| 3 | What would the images cost? What must real images save? | 13:00 |
| 4 | Look at five images and commit to one | 13:25 |
| 5 | Cheat sheet and next steps: how would you test it at home? | 13:55 |
| 6 | Your slide | 14:15 |

## The five images

| Image | What it is |
|---|---|
| Sentinel-2 | The free 10 m image, simply enlarged. The "do nothing" option. |
| SR stage 1 | Careful: blends several Sentinel-2 images into one sharper image. Invents nothing. |
| SR stage 2, light | AI adds a little texture (`tau=100` in the SR service). |
| SR stage 2, standard | The setting of the service (`tau=250`). |
| SR stage 2, strong | AI redraws a lot (`tau=500`). Sharpest, and the most invented detail. |

## Areas

* **Ready-made areas**: places we ran before the workshop, sorted by what you find there (dense
  city, city edge, small farms, quarries, fishponds and coast, a river and its flood plain).
  Their pictures come with the notebook; you need no key. ★ marks places where experts
  labelled the ground.
* **A place of your own**: up to 2 km × 2 km. Type the API key and the service address from
  your team card in part 2, check which Sentinel-2 images exist, and press **Send**. The three
  strengths take 5 to 10 minutes together.

## For organisers

The list of areas is `tools/hackathon/areas.py`. `tools/hackathon/make_areas.py` runs them on
the SR service and writes `scenario_areas.zip` (upload it next to the other data packages) and
a contact sheet to check. `tools/hackathon/build.py` writes the notebook;
`tools/hackathon/test_nb.py` runs it and clicks through every control.

---
Contains modified Copernicus Sentinel data. The starting scenarios are invented for this
workshop.
