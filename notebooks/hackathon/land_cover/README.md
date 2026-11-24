# Land cover around Hanoi

[Open the notebook in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/land_cover/hackathon_land_cover.ipynb)

**Question:** would you use super-resolved Sentinel-2 to decide which places to inspect (for
example open construction sites that raise dust, new buildings on farmland, or missing roads),
and how?

## The data

- **Places:** 92 tiles of 640 m × 640 m (about 38 km²) around Hanoi, Vietnam: dense villages,
  rice fields, ponds, the Red River and its sandbanks, and building sites.
- **Labels:** experts mapped seven classes on Pléiades Neo images (0.5 m): building, road,
  water, tree, low vegetation, cropland, bare soil or sand. About a third of the pixels are
  unlabelled and not scored.
- **Inputs:** Sentinel-2 (one revisit, bicubic to 2.5 m), SR stage 1 (τ = 0), SR stage 2
  (τ = 250), and the real Pléiades Neo image resampled to 2.5 m.
- **Task model:** one segmentation model (SatlasPretrain Swin-B, four bands), trained on the
  real images only. It has never seen a super-resolved image: this is the "reuse the model you
  have" path.

## How good is the model (IoU per class, pooled over the 92 tiles)

| Input | Building | Road | Water | Tree | Low veg. | Cropland | Bare soil | mIoU | Paper |
|---|---|---|---|---|---|---|---|---|---|
| Sentinel-2 | 0.51 | 0.20 | 0.51 | 0.21 | 0.19 | 0.45 | 0.19 | 0.324 | 0.324 |
| SR stage 1 | 0.63 | 0.30 | 0.58 | 0.21 | 0.20 | 0.57 | 0.21 | 0.384 | 0.384 |
| SR stage 2 | 0.70 | 0.34 | 0.70 | 0.48 | 0.23 | 0.61 | 0.25 | 0.474 | 0.474 |
| Real high-res | 0.72 | 0.50 | 0.81 | 0.57 | 0.35 | 0.68 | 0.34 | 0.567 | 0.567 |

## Example scenario (use it if you have none of your own)

> **City environment department, air-quality enforcement unit.** Each month, inspectors check
> places that raise dust: open construction sites, cleared land and sand yards. **Budget:** 20
> inspections, one 80 m × 80 m cell each. **Hit:** a cell where at least 20 % of the ground is
> bare soil or sand. **A wasted inspection** costs one inspector-day. **A missed site** means a
> dust source left uncontrolled for a month, worth about three inspector-days.

Other decisions the same notebook supports: buildings appearing on farmland (land-use
enforcement), roads (map updates, access), built-up or green cover (heat, drainage planning).

Questions to sharpen it:
- Is bare soil really what you are after? Riverbanks and fallow fields are bare too.
- Would the inspectors go anyway, with or without a map? Then what does the map change?
- How fresh must the map be? Building sites open and close within months.

## Things to watch

- Large, uniform classes (water, trees, cropland) are easy to rank on every input, even plain
  Sentinel-2. Small or thin things (building sites, roads, scattered houses) are where inputs
  differ.
- Stage 2 synthesises texture; check its false alarms before you trust a pick.
- The real images are licensed for the workshop only (separate download). The notebook works
  without them.

Licence: workshop use only. Labels and Pléiades Neo images: benchmark of Retnanto et al. (2026,
IEEE JSTARS); real high-resolution images: Pléiades Neo (Airbus), do not redistribute. Contains
modified Copernicus Sentinel data.
