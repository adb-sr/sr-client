"""Run the hackathon notebooks from top to bottom (as Runtime > Run all does) and click through
their controls, for testing.

    HK_DATA_URL=/folder/with/the/zips python tools/hackathon/test_nb.py OUT_DIR [task ...]

Needs ipywidgets, nbclient, ipykernel, numpy, pandas, matplotlib, pillow. For every notebook it
checks that nothing is shown before the bet is revealed, reveals it, walks through every brief
and writes the charts, the card and the executed notebook to OUT_DIR/<task>/ for a look.
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


def main():
    out = Path(sys.argv[1]).resolve()
    wanted = sys.argv[2:]
    for nb_path in sorted(NB_DIR.glob("*/*.ipynb")):
        task = nb_path.parent.name
        if wanted and task not in wanted:
            continue
        work = out / task
        work.mkdir(parents=True, exist_ok=True)
        nb = nbformat.read(nb_path, as_version=4)
        nb.cells.append(nbformat.v4.new_code_cell(f"TEST_OUT = {str(work)!r}\n" + CHECK))
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
