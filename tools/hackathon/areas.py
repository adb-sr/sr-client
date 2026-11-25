# ---- the ready-made areas and the five images of the "your scenario" notebook ----------------
# Plain data, used three ways: pasted into the notebook by build.py, imported by make_areas.py
# (which runs the areas on the SR service and packs the images) and read by the tests.
import numpy as np

# key, name on screen, tau of stage 2 (None: no stage 2). nfe = tau, so cost scales with tau.
LEVELS = [("s2", "Sentinel-2 (free, 10 m)", None),
          ("stage1", "SR stage 1", None),
          ("t100", "SR stage 2, light", 100),
          ("t250", "SR stage 2, standard", 250),
          ("t500", "SR stage 2, strong", 500)]

# slug: name, what the area shows, centre, size (km), date (dry season where we could), and the
# notebook with measured results for this very place, if there is one.
AREAS = {
    # Philippines
    "tondo": dict(name="Tondo and Baseco, Manila", theme="Dense city, port, informal settlements",
                  lat=14.5960, lon=120.9620, km=3, date="2026-03-15"),
    "payatas": dict(name="Payatas, Quezon City", theme="Informal settlements at the city edge",
                    lat=14.7130, lon=121.1000, km=3, date="2026-03-15"),
    "manila_south": dict(name="Manila South", theme="Dense city, informal settlements",
                         lat=14.5560, lon=121.0136, km=2, date="2025-06-01", measured="ifs"),
    "sjdm": dict(name="San Jose del Monte, Bulacan", theme="City edge, new housing estates",
                 lat=14.8139, lon=121.0453, km=3, date="2026-03-15"),
    "marikina": dict(name="Marikina River, Marikina City", theme="River and flood plain in a city",
                     lat=14.6350, lon=121.0900, km=3, date="2026-03-15"),
    "rodriguez": dict(name="Rodriguez and San Mateo, Rizal", theme="Quarries at the forest edge",
                      lat=14.7450, lon=121.1500, km=3, date="2026-03-15"),
    "hagonoy": dict(name="Hagonoy, Bulacan", theme="Fishponds and coast",
                    lat=14.8340, lon=120.7330, km=3, date="2026-03-15"),
    "munoz": dict(name="Science City of Muñoz, Nueva Ecija", theme="Small rice farms, farm roads",
                  lat=15.7150, lon=120.9050, km=3, date="2026-03-15"),
    "nueva_ecija": dict(name="Nueva Ecija (from practical demonstration 2)",
                        theme="Rice farms and a town", lat=15.5784, lon=120.9726, km=2,
                        date="2026-03-15"),
    "new_clark": dict(name="New Clark City, Tarlac", theme="Large construction sites, new roads",
                      lat=15.3450, lon=120.5300, km=3, date="2026-03-15"),
    "tacloban": dict(name="Tacloban City, Leyte", theme="Coastal city rebuilt after a typhoon",
                     lat=11.2433, lon=125.0040, km=3, date="2026-04-15"),
    # other countries
    "hanoi": dict(name="Hanoi, Red River banks",
                  theme="City edge: villages, rice fields, building sites",
                  lat=21.0787, lon=105.7822, km=3, date="2025-11-15", measured="lc"),
    "phnom_penh": dict(name="Phnom Penh, southern edge", theme="City growing into wetland",
                       lat=11.5000, lon=104.9200, km=3, date="2026-02-01"),
    "bangkok": dict(name="Bangkok, old city on the Chao Phraya",
                    theme="Dense historic city, river, temples",
                    lat=13.7500, lon=100.4915, km=3, date="2026-01-15"),
        "jakarta": dict(name="North Jakarta coast", theme="Dense coastal city, port",
                    lat=-6.1150, lon=106.8000, km=3, date="2026-08-15"),
    "dhaka": dict(name="Dhaka, eastern edge", theme="City growing into flood plain",
                  lat=23.7800, lon=90.4500, km=3, date="2026-01-15"),
}


def stretch_u8(arrays, ref=None):
    """Float RGB arrays (H, W, 3; any range, NaN = no data) to uint8 with ONE contrast stretch
    for all of them, taken from ``ref`` (default: stage 1, else the first). So the images can
    be compared: none is brightened more than another."""
    ref = ref or ("stage1" if "stage1" in arrays else next(iter(arrays)))
    r = np.nan_to_num(np.asarray(arrays[ref], dtype="float32"))
    lo, hi = np.percentile(r[r.sum(-1) > 0] if (r.sum(-1) > 0).any() else r.reshape(-1, 3),
                           [0.5, 99.5], axis=0)
    out = {}
    for k, a in arrays.items():
        a = np.nan_to_num(np.asarray(a, dtype="float32"))
        out[k] = (np.clip((a - lo) / np.maximum(hi - lo, 1e-6), 0, 1) * 255).round().astype("uint8")
    return out
