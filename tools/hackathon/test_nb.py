"""Run the hackathon notebooks from top to bottom (as Runtime > Run all does) and click through
their controls, for testing.

    HK_DATA_URL=/folder/with/the/zips python tools/hackathon/test_nb.py OUT_DIR [task ...]

Needs ipywidgets, nbclient, ipykernel, numpy, pandas, matplotlib, pillow. For the three task
notebooks it checks that nothing is shown before the bet is revealed, reveals it and walks
through every brief. For the scenario notebook it fills the canvas, walks through every starting
scenario, the money part, the picture viewer, the cheat sheet and the SR service (against a
stand-in). If HK_DATA_URL holds no scenario_areas.zip, it makes a small stand-in package.
Charts, cards and the executed notebooks go to OUT_DIR/<task>/ for a look.
"""
import os
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

NB_DIR = Path(__file__).resolve().parents[2] / "notebooks" / "hackathon"

CHECK = r'''
import json, pathlib
OUT = pathlib.Path(TEST_OUT); OUT.mkdir(parents=True, exist_ok=True)
log = {}
def dump(name, image):
    (OUT / f"{name}.png").write_bytes(bytes(image.value))

# 1. Run all has finished: nothing may show a result yet
assert not S["revealed"]
assert UI["decision"].result.children == ()
for part in ("sweep", "picks", "cost", "card"):
    kids = UI[part + "_holder"].children
    assert len(kids) == 1 and "Opens once" in kids[0].value, part
assert "card" not in UI and "cost" not in UI

# 2. Bet and reveal
d = UI["decision"]
for i, b in enumerate(d.bets.values()):
    b.value = min(b.max, 4 + 3 * i)
d.reveal.click()
assert S["revealed"] and len(d.result.children) == 3
for part in ("sweep", "picks", "cost", "card"):
    kids = UI[part + "_holder"].children
    assert not (len(kids) == 1 and isinstance(kids[0], W.HTML)), (part, kids[0].value[:300])
dump("decision_brief0", d.result.children[0])
dump("sweep", UI["sweep"])
dump("cost_brief0", UI["cost"].chart)
log["brief0"] = {"hits": S["res"]["hits"].to_dict(), "strategy": S.get("strategy"),
                 "needed": S["visits_needed"], "reading": d.result.children[1].value,
                 "cost_reading": UI["cost"].reading.value, "where": UI["picks"].where.value}
for j, im in enumerate(UI["picks"].galleries.children):
    dump(f"gallery{j}", im)
for j, im in enumerate(UI["picks"].detail.children):
    dump(f"detail{j}", im)

# 3. Every brief sets the scenario, the settings and the area
m = UI["mission"]
n_briefs = len(BRIEFS[task.meta["task"]])
for i in range(1, n_briefs):
    m.choose.value = i
    b = BRIEFS[task.meta["task"]][i]
    assert ANSWERS["decision"] == b["scenario"]["decision"]
    assert S["budget"] == b["settings"]["budget"], (S["budget"], b["settings"])
    assert UI["cost"].controls["Area you must watch (km²)"].value == b["area"][0]
    log[f"brief{i}"] = {"hits": S["res"]["hits"].to_dict(), "strategy": S.get("strategy"),
                        "needed": S["visits_needed"], "n": len(S["hit"]),
                        "n_hit": int(S["hit"].sum()),
                        "reading": d.result.children[1].value, "where": UI["picks"].where.value}
    dump(f"decision_brief{i}", d.result.children[0])
    dump(f"cost_brief{i}", UI["cost"].chart)
m.choose.value = -1                      # our own decision: empty fields, settings stay
assert ANSWERS["decision"] == "" and scenario_dict()["decision"] == "(not answered)"
m.choose.value = 0
m.fields["team"].value = "Team Test"

# 4. Controls of the other parts
p = UI["picks"]
for k in [o[1] for o in p.pick.options]:
    p.pick.value = k
p.which.value = "missed"
c = UI["cost"]
if "Screen everything with" in c.controls:
    c.controls["Screen everything with"].value = "s2"
    log["screen_s2"] = S["strategy"]
    c.controls["Buy real images for the top (%)"].value = 10
c.controls["Area you must watch (km²)"].value = 1000
c.controls["A fresh map"].value = 12
for wdg in UI["explore"].controls:
    if isinstance(wdg, W.Dropdown) and len(wdg.options) > 1:
        wdg.value = wdg.options[1][1]
dump("explore", UI["explore"].children[-1].children[0])

# 5. The card follows the answers
f = UI["verdict"].fields
f["VERDICT"].value = "pilot"
f["USE"].value = USES[0]
f["SAFEGUARDS"].boxes[0].value = True
f["SAFEGUARDS"].boxes[2].value = True
f["CHANGE_MIND"].value = "a field test in two cities"
UI["finds"].fields["FAILURE"].value = "a market roof flagged as a settlement"
text = card_text()
for needle in ("Team Test", "pilot", USES[0], SAFEGUARDS[2], "a field test in two cities",
               "a market roof", "OUR BETS", "MONEY ("):
    assert needle in text, needle
assert _html.escape("a field test in two cities") in UI["card"].card.value
(OUT / "card.txt").write_text(text)
UI["card"].button.click()

# 6. The SR service panel, against a stand-in for the client (no key, no network)
import sys as _sys, types
class _DA:
    def __init__(self, a): self.values = a
    def isel(self, band): return _DA(self.values[band])
class _Job:
    id, status, warnings, info = "fakejob0", "done", [], {}
    def refresh(self): pass
    def _progress_line(self, t): return "running"
    def results(self): return {"files": ["lr_reference.tif", "stage1_sr.tif", "stage2_sr.tif"]}
    def open(self, f):
        n = 50 if f.startswith("lr") else 200
        return _DA(np.random.rand(4, n, n).astype("float32"))
class _SR:
    def __init__(self, key, url=None): assert (key, url) == ("srk_test", "http://fake")
    def me(self): return {"budget": {"left_usd": 3}}
    def submit(self, area, date, stages, **options):
        assert len(area) == 4 and stages
        return _Job()
_mod, _cl = types.ModuleType("sr_client"), types.ModuleType("sr_client.client")
_mod.SRClient, _mod.SRError = _SR, type("SRError", (Exception,), {})
_cl.FINISHED = ("done", "partial", "failed", "cancelled")
_sys.modules.update({"sr_client": _mod, "sr_client.client": _cl})
c = UI["sr_connect"]
c.go.click()                              # no key yet: a clear message, no crash
assert "Could not connect" in c.status.value
c.key.value, c.url.value = "srk_test", "http://fake"
c.go.click()
assert "Connected" in c.status.value, c.status.value
UI["sr"].send.click()
assert len(UI["sr"].viewer.children) == 1, UI["sr"].status.value
UI["sr"].place.value = OWN_PLACE
UI["sr"].send.click()
assert len(UI["sr"].viewer.children) == 1, UI["sr"].status.value
dump("sr_viewer", UI["sr"].viewer.children[0].image)
(OUT / "log.json").write_text(json.dumps(log, indent=1, default=str))
print("CHECKS PASSED")
'''


CHECK_SCENARIO = r'''
import json, pathlib
OUT = pathlib.Path(TEST_OUT); OUT.mkdir(parents=True, exist_ok=True)
def dump(name, image):
    (OUT / f"{name}.png").write_bytes(bytes(image.value))

# 1. Run all has finished: the first area is ready-made, its pictures are loaded, part 5 is shut
assert set(PKG) == {"tondo", "manila_south", "hanoi"}, PKG.keys()
a, look, c = UI["area"], UI["look"], UI["canvas"]
assert a.place.value == "tondo" and "pictures are ready" in a.info.value
assert len(look.viewer.children) == 3, look.status.value
assert "cheat" not in UI and "Opens once" in UI["cheat_holder"].children[0].value
dump("viewer_all", look.viewer.children[0].image)

# 2. The canvas: typing saves; a starting scenario fills fields, numbers and the area
c.fields["team"].value = "Team Test"
c.fields["decision"].value = "Which blocks we visit"
assert ANSWERS["decision"] == "Which blocks we visit" and ANSWERS["size_m"] == 5
for i in range(len(STARTERS)):
    c.pick.value = i
    c.fill.click()
    s = STARTERS[i]
    assert ANSWERS["decision"] == s["fields"]["decision"] and ANSWERS["area_km2"] == s["area_km2"]
    assert a.place.value == s["area"] and s["task"] in CHEAT and s["area"] in AREAS
    assert set(s["fields"]) == {k for k, _, _ in CANVAS} - {"team"}, s["title"]
c.pick.value = 0
c.fill.click()
assert c.fields["team"].value == "Team Test" and a.place.value == "tondo"
for m in (1, 3, 8, 15, 40):
    c.size.value = m
c.size.value = 5

# 3. Money follows the canvas and its own controls
m = UI["money"]
assert "620 km²" in S["money"][0], S["money"]
before = S["money"][1]
m.controls["SR level"].value = "t500"
assert m.controls["Super-resolution, USD per km²"].value == SR_USD_KM2["t500"]
assert S["money"][1] != before
c.area.value = 10                       # smaller than the smallest order
assert "smallest order" in m.reading.value
c.area.value, c.updates.value = 620, 12
m.controls["One wasted action costs (USD)"].value = 80
m.controls["Mixed: real images for (%)"].value = 10
dump("money", m.chart)
(OUT / "money.html").write_text(m.reading.value)

# 4. The viewer
v = look.viewer.children[0]
v.size.value = 100
v.east.value, v.north.value = 300, -200
v.colours.value = "own"
v.mode.value = "two"
v.left.value, v.right.value = "stage1", "t500"
dump("viewer_two", v.image)
assert pathlib.Path("my_comparison.png").exists()
look.viewer.children[1].click()         # download button: no crash outside Colab

# 5. Committing to an image opens the cheat sheet; it follows the task and the choice
look.fields["SEE_S2"].value = "partly"
look.fields["WHY"].value = "single roofs"
look.fields["INVENTED"].value = "streets in the settlement"
look.fields["LEVEL"].value = "stage 2 strong"
ch = UI["cheat"]
assert ch.task.value == "settlements" and "measurements agree" in ch.sheet.value
look.fields["LEVEL"].value = "Sentinel-2"
assert "more careful image" in ch.sheet.value
for k in CHEAT:
    ch.task.value = k
    assert CHEAT[k]["verdict"] in ch.sheet.value
    assert all(b in _CHOICE_KEY.values() for b in CHEAT[k]["best"]), k
    assert CHEAT[k]["notebook"] in (None, *MEASURED)
(OUT / "cheat_all.html").write_text("<hr>".join(
    f"<h3>{r['title']}</h3>" for r in CHEAT.values()))
ch.task.value = "fields"
look.fields["LEVEL"].value = "stage 2 strong"
assert "stronger image" in ch.sheet.value
(OUT / "cheat.html").write_text(ch.sheet.value)
ch.fields["TEST_DATA"].value = "200 validated blocks"
ch.fields["TEST_BASELINE"].boxes[0].value = True
ch.fields["TEST_PASS"].value = "10 of 20 in two cities"
ch.fields["NEEDS"].value = "labels from the housing office"
f = UI["scenario_card"].fields
f["VERDICT"].value = "test it first"
f["SAFEGUARDS"].boxes[0].value = True
text = scenario_card_text()
for needle in ("Team Test", "Tondo and Baseco", "scenes on", "620 km²", "stage 2 strong",
               "single roofs", "disagree", "200 validated blocks", BASELINES[0],
               "10 of 20 in two cities", "test it first", SAFEGUARDS[0]):
    assert needle in text, needle
assert _html.escape("10 of 20 in two cities") in UI["scenario_card"].card.value
(OUT / "card.txt").write_text(text)

# 6. An area without ready-made pictures, and an own place, against a stand-in for the client
import sys as _sys, types
class _DA:
    def __init__(self, a): self.values = a
    def isel(self, band): return _DA(self.values[band])
class _Job:
    warnings, info = [{"code": "water", "message": "m"}], {}
    def __init__(self, tau): self.id, self.status, self.n = f"fakejob{tau}", "running", 0
    def refresh(self):
        self.n += 1
        self.status = "done" if self.n >= 1 else "running"
    def _progress_line(self, t): return "running"
    def results(self): return {"files": {f: "u" for f in ("lr_reference.tif", "stage1_sr.tif",
                                                           "stage2_sr.tif")}}
    def open(self, f):
        n = 50 if f.startswith("lr") else 200
        return _DA(np.random.rand(4, n, n).astype("float32") * 0.3)
class _SR:
    sent = []
    def __init__(self, key, url=None): assert (key, url) == ("srk_test", "http://fake")
    def me(self): return {"budget": {"left_usd": 3}}
    def estimate(self, area, date, tau):
        assert len(area) == 4
        return {"tiles": 81, "estimated_usd": tau / 2500, "problems": [],
                "scenes": [{"id": i, "date": f"2026-03-{i + 1:02d}", "cloud_cover": 3.0 * i}
                           for i in range(9)], "warnings_likely": []}
    def submit(self, area, date, tau):
        _SR.sent.append((tuple(area), date, tau))
        return _Job(tau)
_mod, _cl = types.ModuleType("sr_client"), types.ModuleType("sr_client.client")
_mod.SRClient, _mod.SRError = _SR, type("SRError", (Exception,), {})
_cl.FINISHED = ("done", "partial", "failed", "cancelled")
_sys.modules.update({"sr_client": _mod, "sr_client.client": _cl})
time.sleep = lambda s: None
a.place.value = "payatas"                 # not in the package
assert "not in the download" in a.info.value and a.connect.layout.display != "none"
look.load.click()
assert "Nothing to load yet" in look.status.value
a.send.click()
assert "Connect first" in a.status.value
a.connect.go.click()                      # no key yet: a clear message, no crash
assert "Could not connect" in a.connect.status.value
a.connect.key.value, a.connect.url.value = "srk_test", "http://fake"
a.connect.go.click()
assert "Connected" in a.connect.status.value, a.connect.status.value
a.check.click()
assert "9 scenes on 9 days" in a.status.value, a.status.value
a.send.click()
assert "Sent." in a.status.value and [t for _, _, t in _SR.sent] == [100, 250, 500]
assert _SR.sent[0][:2] == (tuple(area_around(14.7130, 121.1000, km=3)), "2026-03-15")
look.load.click()
assert len(look.viewer.children) == 3, look.status.value
assert set(S["layers"]) == {"s2", "stage1", "t100", "t250", "t500"}
assert "water" in scenario_card_text()
dump("viewer_service", look.viewer.children[0].image)
a.place.value = OWN
lat, lon, km, day = a.own_fields
lat.value, lon.value, km.value, day.value = 10.3, 123.9, 5, "2026-02-01"
assert km.value == 2                      # capped
a.check.click()
a.send.click()
assert _SR.sent[-1] == (tuple(area_around(10.3, 123.9, km=2)), "2026-02-01", 500)
look.load.click()
assert len(look.viewer.children) == 3 and "Our own area" in scenario_card_text()
a.place.value = "hanoi"                   # back to a ready-made area with measured results
assert "measured results" in a.info.value
look.load.click()
assert set(S["layers"]) == {"s2", "stage1", "t100", "t250", "t500"}
print("CHECKS PASSED")
'''


def fake_areas(folder):
    """A small stand-in for scenario_areas.zip (three areas, made-up pictures), so the
    scenario notebook can be tested without the SR service."""
    import json
    import zipfile

    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(0)
    folder.mkdir(parents=True, exist_ok=True)
    meta = {"areas": {}}
    with zipfile.ZipFile(folder / "scenario_areas.zip", "w") as z:
        for slug in ("tondo", "manila_south", "hanoi"):
            base = np.kron(rng.integers(40, 200, (20, 20, 3)), np.ones((16, 16, 1)))
            for key, noise in (("s2", 0), ("stage1", 4), ("t100", 8), ("t250", 14), ("t500", 24)):
                a = base[::4, ::4] if key == "s2" else base + rng.normal(0, noise, base.shape)
                name = f"{key}.{'png' if key == 's2' else 'jpg'}"
                path = folder / name
                Image.fromarray(np.clip(a, 0, 255).astype("uint8")).save(path)
                z.write(path, f"scenario_areas/{slug}/{name}")
                path.unlink()
            meta["areas"][slug] = {
                "tiles": 81, "warnings": [], "usd": {"stage1": 0.02, "t100": 0.05, "t250": 0.1,
                                                     "t500": 0.18},
                "scenes": [{"date": f"2026-03-{d:02d}", "cloud_cover": float(d)}
                           for d in (2, 7, 12, 17, 22, 27)]}
        z.writestr("scenario_areas/meta.json", json.dumps(meta))


def main():
    out = Path(sys.argv[1]).resolve()
    wanted = sys.argv[2:]
    data_url = os.environ["HK_DATA_URL"]
    for nb_path in sorted(NB_DIR.glob("*/*.ipynb")):
        task = nb_path.parent.name
        if wanted and task not in wanted:
            continue
        work = out / task
        work.mkdir(parents=True, exist_ok=True)
        check = CHECK
        os.environ["HK_DATA_URL"] = data_url
        if task == "scenario":
            check = CHECK_SCENARIO
            if not (Path(data_url) / "scenario_areas.zip").exists() or os.environ.get("HK_FAKE_AREAS"):
                fake_areas(work / "data")       # no real pictures here: use stand-ins
                os.environ["HK_DATA_URL"] = str(work / "data")
        nb = nbformat.read(nb_path, as_version=4)
        nb.cells.append(nbformat.v4.new_code_cell(f"TEST_OUT = {str(work)!r}\n" + check))
        client = NotebookClient(nb, timeout=1800, kernel_name="python3",
                                resources={"metadata": {"path": str(work)}})
        try:
            client.execute()
        finally:
            nbformat.write(nb, work / "executed.ipynb")
        errors = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", [])
                  if o.get("output_type") == "error"]
        last = "".join(o.get("text", "") for o in nb.cells[-1].outputs if o.get("name") == "stdout")
        assert not errors and "CHECKS PASSED" in last, (task, errors[:1])
        print(f"{task}: ok")


if __name__ == "__main__":
    if not os.environ.get("HK_DATA_URL"):
        sys.exit("set HK_DATA_URL to a folder (or URL) that holds the data zips")
    main()
