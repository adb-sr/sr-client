# Field boundaries of smallholder farms

[Open the notebook in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/field_boundaries/hackathon_field_boundaries.ipynb)

**Question:** would you use super-resolved Sentinel-2 to decide which areas your teams visit
first to reach small farms, and how?

## The data

- **Places:** the 10 test areas of the AI4SmallFarms benchmark, each about 5.4 km × 5.4 km, five
  in Vietnam and five in Cambodia (2021). Fields average under one hectare, much like rice and
  corn farms in Central Luzon or Mindanao.
- **Labels:** 51,062 fields outlined by experts on high-resolution images that are not
  distributed with the benchmark, so there is **no real high-resolution input** for this task.
- **Inputs:** Sentinel-2 (per-pixel median of 8 clear dates, bicubic to 2.5 m), SR stage 1
  (τ = 0) and SR stage 2 (τ = 250), all from the same 8 dates.
- **Task models:** unlike the other two tasks, a field-boundary model (U-Net, ResNet-34) was
  **trained on each input**, three times with different random starts. Fields are cut out of
  each model's boundary map by a watershed. This is the "train on the images you will use" path.

## How good is the model (mean of 3 training runs)

| Input | Field F1 | Small fields (< 1,000 m²) found |
|---|---|---|
| Sentinel-2 | 0.420 | 6.8 % |
| SR stage 1 | 0.461 | 12.2 % |
| SR stage 2 | 0.438 | 10.4 % |

A field counts as found when a drawn field overlaps it well (IoU > 0.5). Stage 1 is best; the
invented texture of stage 2 adds edges that are not field boundaries.

## The briefs (mock: the kind of decision is real, the office and numbers are invented)

| Brief | Decision | Settings |
|---|---|---|
| **Which villages get the farmer-registry teams?** (department of agriculture) | Which areas extension workers visit to enrol small farms | 30 visits, 500 m squares, hit = at least 30 fields under 0.25 ha |
| **Where does the farm census need a second enumerator?** (statistics office) | Which 1 km squares get a second enumerator | 20 squares, hit = at least 200 parcels of any size |

Or write your own. Questions to sharpen it:
- Do you need to know **where** the small farms are, or only **how many** there are?
- Would a 10 m map plus local knowledge be enough?
- Who would check the boundaries, and how often do they change?

## Things to watch

- Area `46_vietnam` is a hazy composite: plain Sentinel-2 nearly fails there (455 fields drawn
  against 6,130), while both SR inputs cope. Part 4 of the notebook shows what that means: no
  visit goes there with Sentinel-2.
- Counts can be right for the wrong reason: one field split in two plus two fields merged into
  one still gives the right count.
- The models were trained on these regions. A model for the Philippines would need Philippine
  labels.

Licence: AI4SmallFarms (Persello et al. 2023), CC BY 4.0. Contains modified Copernicus Sentinel
data.
