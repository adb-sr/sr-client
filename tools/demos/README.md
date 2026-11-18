# Workshop demo notebooks: how they are built

| File | What it is |
|---|---|
| `places.py` | the five places, the worksheet's dial experiments, the walkthrough's jobs: the single source |
| `d1_helpers.py` | helper code pasted into both Demo 1 notebooks (hidden cell) |
| `build_demo1.py` | → `notebooks/demo1_super_resolution.ipynb` (presenter walkthrough) |
| `build_demo1_worksheet.py` | → `notebooks/demo1_your_turn.ipynb` (participants) |
| `d2_helpers.py` | helper code pasted into the Demo 2 notebook |
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

python tools/demos/run_nb.py notebooks/demo1_your_turn.ipynb /tmp/out.ipynb 'PLACE="Nueva Ecija rice farms"'
DEMO2_DATA_URL=OUT python tools/demos/run_nb.py notebooks/demo2_use_cases.ipynb /tmp/out2.ipynb
```
