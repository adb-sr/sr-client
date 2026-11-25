"""The places and settings the workshop demos use: one source for the notebooks, the
prestage script and the Demo 2 data package.

`confirmed: False` marks coordinates and dates that still need a check against the free
estimate (enough clear images, no warnings) before the workshop.
"""

PLACES = {
    "ADB headquarters, Mandaluyong": dict(
        lat=14.5878, lon=121.0585, date="2026-04-15", confirmed=False,
        note="dense city: office towers, malls, residential blocks"),
    "DHSUD office, Quezon City": dict(
        lat=14.6447, lon=121.0514, date="2026-04-15", confirmed=False,
        note="city: government offices, tree-lined streets, housing"),
    "PhilSA office, Quezon City": dict(
        lat=14.6096, lon=121.0803, date="2026-04-15", confirmed=False,
        note="city by the Marikina river: towers, subdivisions, riverside"),
    "Cebu City and Mandaue": dict(
        lat=10.3300, lon=123.9200, date="2026-03-20", confirmed=True,
        note="dense city by the coast: port, warehouses, small houses"),
    "Nueva Ecija rice farms": dict(
        lat=15.5784, lon=120.9726, date="2026-03-15", confirmed=True,
        note="rice fields, villages and farm-to-market roads"),
}
OWN_PLACE = "My own place"
AREA_KM = 2

# Demo 1, part 5: one change to the Stage 2 dials, on the same area
EXPERIMENTS = {
    "less noise (tau 100)": dict(tau=100),
    "more noise (tau 500)": dict(tau=500, nfe=250),
    "much more noise (tau 999)": dict(tau=999, nfe=250),
    "fewer steps (10 steps)": dict(tau=250, nfe=10),
    "another random seed (seed 1)": dict(tau=250, seed=1),
}
# The noise experiments keep the default 250 steps: only one dial changes, and the job takes
# as long as the default (with 999 steps it took 8.6 minutes on dev when not cached).

# Demo 1, "Going deeper" (sections 8 to 10), Cebu only
PRESENTER_PLACE = "Cebu City and Mandaue"
PRESENTER_DIALS = {
    "tau 100": dict(tau=100),
    "tau 250": dict(tau=250),
    "tau 500": dict(tau=500),
    "tau 999": dict(tau=999),
    "tau 250, 10 steps": dict(tau=250, nfe=10),
    "tau 250, 50 steps": dict(tau=250, nfe=50),
    "tau 250, seed 1": dict(tau=250, seed=1),
}
PRESENTER_CHECKS = {
    "Ningbo, China: houses, gardens and greenhouses": "20220808_022419_SN18_51N_361530_3312762",
    "near Yangon, Myanmar: factories": "20221106_044416_SN27_47N_204846_1870691",
    "near Faisalabad, Pakistan: farmland": "20221206_095550_SN22_43N_329899_3480761",
}


def as_code(name, value):
    """A Python assignment of a constant, for pasting into a notebook cell."""
    import pprint
    return f"{name} = {pprint.pformat(value, width=96, sort_dicts=False)}\n"
