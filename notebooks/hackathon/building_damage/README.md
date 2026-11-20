# Building damage after disasters

[Open the notebook in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/building_damage/hackathon_building_damage.ipynb)

**Question:** after a typhoon, would you use super-resolved Sentinel-2 to decide where to send
damage-assessment teams first, and how?

## The data

- **Places:** 1,577 test areas of the xBD benchmark, each about 0.2–0.25 km², from five
  disasters: Hurricane Matthew (Haiti, 2016; 405 areas), floods in Nepal (2017; 619), the Santa
  Rosa wildfire (USA, 2017; 377), the Sunda Strait tsunami (Indonesia, 2018; 148) and the Fuego
  volcano eruption (Guatemala, 2018; 28). The last two are too small to rank.
- **Labels:** every building outlined by experts on Maxar images (~0.5 m) and marked intact or
  damaged.
- **Inputs:** before and after images for each of Sentinel-2 (bicubic to 2.5 m), SR stage 1
  (τ = 0), SR stage 2 (τ = 250) and the real Maxar images resampled to ~2.5 m. Sentinel-2-based
  inputs are colour-matched to the Maxar image of each area. The Sentinel-2 images are the
  clearest before and after the event and can be weeks after it, so some damage may already be
  cleared or rebuilt.
- **Task model:** one SatlasPretrain Swin-B model trained on the Maxar before-and-after images.
  It labels every pixel as background, intact building or damaged building. It has never seen a
  super-resolved image.

## How good is the model (pixel scores, all 1,577 areas)

| Input | Finds buildings (F1) | Finds damaged buildings (F1) | mIoU |
|---|---|---|---|
| Sentinel-2 | 0.313 | 0.207 | 0.360 |
| SR stage 1 | 0.482 | 0.139 | 0.388 |
| SR stage 2 | 0.541 | 0.211 | 0.404 |
| Real high-res | 0.792 | 0.357 | 0.552 |

SR helps the model find buildings but not tell damaged from intact. These are the paper's
numbers; stage 1's damage F1 and mIoU are not in the paper.

## Example scenario (use it if you have none of your own)

> **Provincial disaster office (PDRRMO), first 72 hours after a typhoon.** Rapid
> damage-assessment teams are sent to the worst-hit areas first. **Budget:** 20 team
> deployments, one 0.25 km² area each. **Hit:** an area with at least 5,000 m² of damaged
> buildings, about 50 houses. **A wasted deployment** costs one team-day. **A missed area**
> means relief to about 50 households delayed by days, worth about five team-days.

Questions to sharpen it:
- Is the decision about **damage** (where to assess) or about **exposure** (where people live,
  for pre-positioning relief)? Try both: the notebook has a switch.
- How fast do you need the map? Sentinel-2 passes every 5 days, but typhoon clouds can hide the
  ground for weeks.
- Would your teams go anyway to the places they already know are dense? What does the map add?

## Things to watch

- For ranking the worst-hit areas, damage tends to sit where buildings are dense, so even a
  rough map can pick good areas. Check whether SR changes **which** areas you pick.
- Pixels are not exactly square (2.0–2.6 m); areas in m² use the true pixel size.
- 312 areas had to use their event's average image alignment (`registration_ok: false`).
- Large parts of some Maxar images are blank; those pixels are not scored.

Licence: xBD (Gupta et al. 2019; Maxar Open Data / xView2), CC BY-NC-SA 4.0, non-commercial use.
Contains modified Copernicus Sentinel data.
