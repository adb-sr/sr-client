"""Builds notebooks/demo1_your_turn.ipynb: the participants' worksheet for Practical
demonstration 1 (about 20 minutes, self-led, in pairs).

    python tools/demos/build_demo1_worksheet.py

The helper code (d1_helpers.py), the controls (d1_widgets.py: dropdowns, buttons and sliders
made with ipywidgets) and the list of places (places.py) are pasted into a hidden form cell,
so the notebook runs on its own in Colab.
"""
import json
from pathlib import Path

import nbformat as nbf

from places import AREA_KM, EXPERIMENTS, PLACES, as_code

HERE = Path(__file__).parent
OUT = HERE.parent.parent / "notebooks" / "demo1_your_turn.ipynb"
PIP = '%pip install -q "sr-client[geo,viz] @ git+https://github.com/adb-sr/sr-client@v0.1.0"'
cells = []


def md(s):
    cells.append(nbf.v4.new_markdown_cell(s.strip("\n")))


def code(s, hidden=False):
    c = nbf.v4.new_code_cell(s.strip("\n"))
    if hidden:
        c.metadata["cellView"] = "form"
    cells.append(c)


def options(values):
    return json.dumps(list(values), ensure_ascii=False)


place_rows = "\n".join(f"| **{name}** | {p['note']} |" for name, p in PLACES.items())

md(rf"""
# Practical demonstration 1: your turn

*SSTA workshop, 26 November 2026. Goes with Session 2, "ADB's approach to super-resolution".*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo1_your_turn.ipynb)

You have just seen the service at work on one example. Now you make a super-resolved image
of **a place you know** and judge it yourself. Work in pairs: one person runs the cells, the
other looks closely and answers the questions.

**About 20 minutes, five steps, four questions.** You do not need to write code:

* **run each grey cell once**, from top to bottom, with **Shift + Enter** (or the ▶ button);
* then use the **menus, buttons and sliders that appear under the cell**. They act at once,
  and your answers are saved as you type. You never need to run a cell twice.

| Step | What you do | Question |
|---|---|---|
| 1 | Pick a place and send it to the service | |
| 2 | Look at the 8 Sentinel-2 images the model uses | **Q1** How many are really clear? |
| 3 | Compare Stage 1 with Sentinel-2 | **Q2** What can you see now that you could not see before? |
| 4 | Look at Stage 2, the full result | **Q3** One detail it got right, one it got wrong |
| 5 | Turn one dial and compare | **Q4** Which version would you use, and for what? |

At the end, the notebook shows a **result card** with your answers. We compare the cards in
the room.

**Stuck?** Raise your hand, or carry on with *Cebu City and Mandaue*: every step works with
it.
""")

md("## 0. Setup\n\nRun the next three cells. The first takes about a minute.")
code(PIP)
md(r"""
Your API key starts with `srk_`. The cell asks for the key and the service URL (both are on
your card). In Colab you can also store them under **Secrets** (the key icon on the left) as
`SR_API_KEY` and `SR_API_URL`.
""")
code(r"""
import getpass
import os

from sr_client import SRClient, SRError, area_around


def secret(name, prompt):
    if os.environ.get(name):
        return os.environ[name]
    try:
        from google.colab import userdata
        return userdata.get(name)
    except Exception:
        return getpass.getpass(prompt) if "KEY" in name else input(prompt)


os.environ["SR_API_KEY"] = secret("SR_API_KEY", "API key (srk_...): ")
os.environ["SR_API_URL"] = secret("SR_API_URL", "Service URL: ")

sr = SRClient()
me = sr.me()
print(f"Key {me['prefix']} ({me['owner']}): ${me['budget']['remaining_usd']:.2f} of budget left")
""")
code('# @title Helper functions (run this cell; you do not need to read it) { display-mode: "form" }\n'
     + (HERE / "d1_helpers.py").read_text() + "\n\n"
     + as_code("PLACES", {k: {f: v[f] for f in ("lat", "lon", "date", "note")}
                          for k, v in PLACES.items()})
     + as_code("EXPERIMENTS", EXPERIMENTS) + "\n\n"
     + (HERE / "d1_widgets.py").read_text(), hidden=True)

md(rf"""
## 1. Pick a place *(2 minutes)*

Run the cell, choose the place you know best, and press **Send to the service**. All five
were run before the workshop, so they come back quickly and cost nothing.

| Place | What is there |
|---|---|
{place_rows}

Each area is a {AREA_KM} km square. The service first makes an **estimate**, which is free
(how many Sentinel-2 images exist around the date, and what the job would cost), and then
starts the job. Both stages run; Stage 1 is ready first.

*My own place* is the last entry in the menu: fill in a point and a date. It takes a few
minutes longer and uses your budget, so do the five steps with a listed place first if you
are short of time. If you change the place later, run the cells of steps 2 to 5 again.
""")
code("pick_place(sr)")

md(r"""
## 2. What did the satellite see? *(4 minutes)*

For every 320 m square, the model gets the **8 clearest Sentinel-2 images** closest to your
date. The cell shows the 8 for the middle of your area, read from the public Sentinel-2
archive (this takes about half a minute).

* Pixels outlined in **red** are masked: ESA's classification marks them as cloud, cirrus or
  shadow. The model fills them from the other images.
* Image 1 is the **reference**: the result follows its layout and colours.
* The classification is not perfect. It misses thin cloud and haze, and sometimes masks
  bright roofs.

Answer **Q1** in the blue box under the images.
""")
code("step2_inputs()")

md(r"""
## 3. Stage 1: eight images become one *(4 minutes)*

Stage 1 combines the 8 images into one image with 2.5 m pixels. It is sharper than
Sentinel-2 but still soft.

Use the **sliders** to move to a spot you know: a street you walk, your office, a market, a
field. The small picture on the left shows where you are in the area; the **Zoom** buttons
change how much you see. Then answer **Q2**.
""")
code("step3_stage1()")

md(r"""
## 4. Stage 2: the model adds detail *(5 minutes)*

Stage 2 adds noise to the Stage 1 image and removes it step by step. While it removes the
noise, it draws small details the way it learned them from 1.8 million real high-resolution
images. The result looks sharp. Some of that detail is real, and some is only *plausible*.

You know this place, so you can tell the difference. Move the view again and look for:

* something Stage 2 shows **correctly** (a road that is really there, the shape of a building
  you know);
* something that is **wrong or invented** (a roof pattern that does not exist, a road that
  ends nowhere, a building that became trees).

Then answer **Q3**.
""")
code("step4_stage2()")

md(r"""
## 5. One experiment: turn a dial *(5 minutes)*

Stage 2 has the two dials from Session 2:

* **Dial 1, `tau`**: how much noise is added, from 0 (Stage 1 only) to 999 (almost only
  noise). More noise lets the model draw more of its own detail. The default is 250. (The
  noise experiments keep the default 250 steps, so only one dial changes.)
* **Dial 2, `nfe`**: in how many steps the noise is removed. Fewer steps are faster and
  cheaper, and less sharp.
* The noise is random. The **seed** fixes it: another seed gives another version of the
  invented detail, while everything that was measured stays the same.

Choose **one** experiment in the menu; other pairs will choose others, and we compare at the
end. Click what you expect, then press **Run my experiment**. A setting that was run before
comes back at once; a new one takes about 4 minutes.

The result shows the default image, yours, and **where the two differ** (bright = large
difference). If your experiment was the other seed, that third picture is a map of where the
model invented detail. Under the pictures are two numbers for each version:

* *agreement with Sentinel-2*: averaged back to 10 m, does the image still match what the
  satellite measured (1 = same pattern)?
* *fine detail*: how much the brightness changes from one pixel to the next (higher =
  sharper).
""")
code("step5_experiment()")
md("When you have compared the two versions, answer **Q4**.")
code("step5_question()")

md(r"""
## 6. Your result card

Run the cell. If you change an answer afterwards, press **Update the card**. Enter your
answers in the poll (the link is on the slide), and be ready to say in one sentence what you
found at your place.
""")
code("result_card()")

md(r"""
---
## If you have time

**Take the images home.** The files open in QGIS or ArcGIS. In Colab they appear in the file
browser on the left, under `sr_results/<job id>/`.

| File | What it holds |
|---|---|
| `stage1_sr.tif`, `stage2_sr.tif` | the 2.5 m images: red, green, blue, near-infrared; reflectance × 10,000 |
| `lr_reference.tif` | the Sentinel-2 input, 10 m |
| `validity.tif` | 0 no data · 1 valid · 2 low diversity (fewer than 4 different clear images) |
| `manifest.json` | the images used for every tile, the settings, model versions, cost |
""")
code(r"""
job = S["job"]                      # the job of the place you picked in step 1
paths = job.download("sr_results")
for name, path in paths.items():
    print(f"  {path}  ({path.stat().st_size / 1e6:.1f} MB)")
""")
md(r"""
**Near-infrared and vegetation.** The model also sharpens the near-infrared band, which our
eyes cannot see. Plants reflect a lot of it. The false-colour image shows near-infrared as
red; NDVI turns it into a vegetation index (green = dense vegetation).
""")
code(r"""
LAT, LON, lr, s2 = S["lat"], S["lon"], S["lr"], S["s2"]
show([view(lr, LAT, LON, 1000), view(s2, LAT, LON, 1000)],
     ["Sentinel-2, false colour", "Stage 2, false colour"], bands=(4, 1, 2), ceiling=0.45,
     size=5.5)
fig, axes = plt.subplots(1, 2, figsize=(11, 5))
for ax, (title, da) in zip(axes, [("Sentinel-2, 10 m", lr), ("Stage 2, 2.5 m", s2)]):
    im = ax.imshow(view(ndvi(da), LAT, LON, 1000).values, cmap="RdYlGn", vmin=-0.2, vmax=0.8,
                   interpolation="nearest")
    ax.set_title(f"NDVI, {title}")
    ax.axis("off")
fig.colorbar(im, ax=axes, shrink=0.8)
plt.show()
""")
md(r"""
**Another place, another dial.** In step 1, choose another place (or *My own place*) and
press the button again, then run the cells of steps 2 to 5 again. Or choose another
experiment in step 5 and press its button. Tips for your own place:

* pick a dry-season date (in Luzon, December to May) so there are enough clear images;
* near the coast you will get the `water` warning: the sea and reefs are not reliable;
* the area is a 2 km square around your point.

**The full walkthrough.** The notebook the presenter used,
[`demo1_super_resolution.ipynb`](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/demo1_super_resolution.ipynb),
has more: all dial settings side by side, the trade-off between sharp and truthful as a
chart, and a check against real 1 m images.

---
Results contain modified Copernicus Sentinel data. Sentinel-2 scenes are read from the public
archive on AWS (Element 84 Earth Search).
""")

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python",
                                 "name": "python3"},
                  "language_info": {"name": "python"}, "colab": {"provenance": []}}
nbf.write(nb, OUT)
print("wrote", OUT, len(cells), "cells")
