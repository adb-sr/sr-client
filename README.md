# sr-client

Python client for the SR service, which delivers super-resolved Sentinel-2 imagery on demand.
You give it an area and a date. The service finds clear Sentinel-2 L2A scenes and runs the
`sen4x-v2` model, which takes the 10 m input to 2.5 m RGB + NIR. It returns Cloud-Optimised
GeoTIFFs.

```bash
pip install "sr-client[geo,viz] @ git+https://github.com/adb-sr/sr-client@v0.1.0"
```

```python
from sr_client import SRClient, area_around

sr = SRClient("srk_...", url="https://<service-url>")   # or set SR_API_KEY / SR_API_URL
area = area_around(14.5995, 120.9842, km=2)             # or a bbox [W, S, E, N] or GeoJSON

sr.estimate(area, "2025-12-01")       # tiles, cost, scenes found, likely warnings (free)
job = sr.submit(area, "2025-12-01")   # stages 1 + 2 by default
job.wait()                            # prints progress; stage 1 is published early
job.show()                            # RGB previews       (needs [viz])
sr2 = job.open("stage2_sr.tif")       # xarray, reflectance (needs [geo])
job.download("results/")              # every file, under results/<job id>/
```

A [Colab notebook](notebooks/workshop.ipynb) walks through the whole thing.

## What you get

Each job writes these files, kept for 30 days. Download links last 7 days, and calling
`job.results()` again issues fresh ones.

| File | Content |
|---|---|
| `stage1_sr.tif` | Stage 1 (multi-image SR): RGBN, 2.5 m, uint16 reflectance × 10000, nodata 0 |
| `stage2_sr.tif` | Stage 2 (diffusion refinement), same layout |
| `lr_reference.tif` | The 10 m Sentinel-2 input composite on the same grid |
| `validity.tif` | 0 nodata · 1 valid · 2 low-diversity (fewer than 8 distinct clear scenes) |
| `stage*_preview.png` | RGB previews |
| `manifest.json` | Scenes used per tile, parameters, model versions, cost, warnings, attribution |

Warnings never block a job: `water` (super-resolution erases shallow-water and benthic
detail, so use `lr_reference.tif` there), `low_diversity`, `nodata`, `haze` and
`missing_tiles`.

## Job options

`submit(area, target_date, **options)`, where every option is optional:

| Option | Default | Meaning |
|---|---|---|
| `stages` | `["1", "2"]` | `["1"]` is fast and cheap. You can add stage 2 later with `job.upgrade()`. |
| `time_window` | `{"days_before": 45, "days_after": 45}` | Scene search window around `target_date`. |
| `max_cloud` | 40 | Scene-level cloud cover ceiling (%). |
| `min_clear` | 0.7 | Minimum clear fraction of a scene over a tile. |
| `n_revisits` | 1 | Minimum number of distinct clear scenes per tile; tiles with fewer become nodata. |
| `tau`, `nfe` | 250, 250 | Diffusion start step and number of steps (10 ≤ nfe ≤ tau). Cost scales with `nfe`. |
| `seed` | 0 | Same inputs, same seed, same output. |

Each API key has an area limit, a budget and a queue limit; `sr.me()` shows them. The cost
estimate assumes nothing is cached, and tiles that someone already computed are free.

Results contain modified Copernicus Sentinel data.
