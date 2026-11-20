# Workshop demo notebooks: how they are built

| File | What it is |
|---|---|
| `places.py` | the five places, the worksheet's dial experiments, the walkthrough's jobs: the single source |
| `d1_helpers.py` | helper code pasted into both Demo 1 notebooks (hidden cell) |
| `widgets_common.py` | controls shared by the worksheets: answers that save themselves, figures shown as images (ipywidgets) |
| `d1_widgets.py` | the Demo 1 worksheet's steps: place menu and send button, viewers with sliders, experiment button, result card |
| `build_demo1.py` | → `notebooks/demo1_super_resolution.ipynb` (presenter walkthrough) |
| `build_demo1_worksheet.py` | → `notebooks/demo1_your_turn.ipynb` (participants) |
| `d2_helpers.py` | data loading, figures and scores pasted into the Demo 2 notebook |
| `d2_widgets.py` | the Demo 2 steps: OpenEarthMap scores, place menu (every step follows a change), viewers, score button, result card, all-places views; the tolerance and metric switches are shared (changing one copy changes all and redraws every score) |
| `build_demo2.py` | → `notebooks/demo2_use_cases.ipynb`; `DATA_URL` is where the data package is hosted |
| `build_demo2_package.py` | makes the Demo 2 data package (needs the service, torch and the land-cover model) |
| `old_d2_helpers.py` | the model, reference-map and scoring code of the first Demo 2 notebook; used by the package builder |
| `prestage.py` | sends every job the demos use, so the service has them cached |
| `run_nb.py` | runs a notebook top to bottom for testing, with form values replaced |
| `fake_api.py` | offline stand-in for the service, serving stored job outputs |

Run the scripts from this folder's parent with an environment that has `sr-client[geo,viz]`,
`nbformat` and (for `run_nb.py`) `nbclient` and `ipykernel`:

```bash
python tools/demos/build_demo1.py && python tools/demos/build_demo1_worksheet.py && python tools/demos/build_demo2.py

export SR_API_KEY=srk_... SR_API_URL=https://...
python tools/demos/prestage.py                 # free estimates
python tools/demos/prestage.py --run --all     # fill the cache (about $3 on an empty cache)
python tools/demos/build_demo2_package.py OUT  # then upload OUT/* to DATA_URL
python tools/demos/build_demo2_package.py OUT --rescore   # scores only (all tolerances)

python tools/demos/run_nb.py notebooks/demo1_your_turn.ipynb /tmp/out.ipynb 'PLACE="Nueva Ecija rice farms"'
DEMO2_DATA_URL=OUT python tools/demos/run_nb.py notebooks/demo2_use_cases.ipynb /tmp/out2.ipynb
```

The worksheets use ipywidgets (Colab ships version 7.7.1): each cell is run once and the
controls under it act at once. Test them by setting widget values in code (see `UI` in
`widgets_common.py`); `run_nb.py` only replaces constants.

The OpenEarthMap part of Demo 2 (`oem_reference.json`, `oem_examples.npz` in the package) was
made with an internal script (`services/downstream-analysis/newstack_rerun/oem_demo2_reference.py`
in the research repo): the land-cover model on the 79 labelled OpenEarthMap validation tiles,
from the aerial image, bicubic Sentinel-2 and the sen4x-v2 stages run on 8-date stacks of
each tile, scored like the notebook (0 / 2.5 / 5 m, on the 0.5 m label grid).
