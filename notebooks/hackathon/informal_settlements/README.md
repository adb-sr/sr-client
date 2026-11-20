# Informal settlements in Metro Manila

[Open the notebook in Colab](https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/informal_settlements/hackathon_informal_settlements.ipynb)

**Question:** would you use super-resolved Sentinel-2 to decide where to send survey teams to
find and verify informal settlements, and how?

## The data

- **Places:** 40 sample tiles, about 20 km² in all, in Manila South (24 tiles of 560 m) and
  Quezon City (16 tiles of 760–920 m). The tiles were chosen to contain informal settlements
  of different sizes, so settlements are far more common here than in the city as a whole.
- **Labels:** expert annotators outlined informal-settlement clusters on Google satellite
  imagery (~0.5 m). Areas they marked as uncertain, and clusters smaller than 225 m², are not
  scored.
- **Inputs:** Sentinel-2 (one revisit, bicubic to 2.5 m), SR stage 1 (τ = 0), SR stage 2
  (τ = 250), and the real Google imagery resampled to 2.5 m. Sentinel-2 images are from around
  1 June 2025 (±6 months); the date of the Google imagery is unknown.
- **Task models:** six segmentation models (SatlasPretrain Swin-B), trained on the real images
  only. They have never seen a super-resolved image: this is the "reuse the model you have"
  path.

## How good is the model (pixel F1 for informal settlement, mean of 6 models)

| Input | F1 (notebook) | F1 (paper) |
|---|---|---|
| Sentinel-2 | 8.7 % | 8.0 % |
| SR stage 1 | 21.0 % | 17.9 % |
| SR stage 2 | 23.4 % | 21.5 % |
| Real high-res | 41.0 % | 39.7 % |

The notebook counts each pixel once; the paper scores overlapping 320 m patches, so the values
differ a little. The model-to-model spread is large on Sentinel-2 (0.3–19.6 %) and much smaller
on stage 2 (19.4–28.6 %).

## Example scenario (use it if you have none of your own)

> **DHSUD regional office, informal settlement upgrading programme.** Each quarter, two-person
> teams survey city blocks to verify and enumerate informal settlements. **Budget:** 20 survey
> visits, one 100 m × 100 m block each. **Hit:** a block where at least a quarter of the area
> is informal settlement. **A wasted visit** costs one survey day. **A missed block** means a
> settlement left out of the programme for a year, worth about three survey days.

Questions to sharpen it:
- Is a site visit really the action, or is it a desk review of the high-resolution image?
- Is it worse to miss a settlement, or to label a formal neighbourhood "informal"? For whom?
- Would you trust a map that shows informal settlements in places your staff know well?

## Things to watch

- Stage 2 synthesises roof texture. It finds more settlements, but look at its false alarms:
  dense formal housing, markets and warehouses.
- The models disagree a lot on Sentinel-2. With a single model, which you would have in
  practice, the result can be much better or much worse than the mean.
- The real imagery is licensed for the workshop only (separate download). The notebook works
  without it.

Licence: workshop use only. Labels: ADB technical assistance. Real high-resolution images:
Google satellite imagery, do not redistribute. Contains modified Copernicus Sentinel data.
