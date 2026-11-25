"""Run the Demo 1 notebook with its buttons pressed in code, for testing.

    python tools/demos/drive_demo1.py IN.ipynb OUT.ipynb "Cebu City and Mandaue" [STOP]

Picks the place, answers the questions and runs the default experiment, the way a participant
would with the controls. STOP: a piece of code; the run ends before the first cell that
contains it (e.g. "checks.status()" to leave out the check against 1 m images, which the
offline stand-in cannot serve). The %pip cell is skipped. SR_API_KEY / SR_API_URL come from
the environment; with FAKE_JOBS_DIR and FAKE_JOBS_URL set, fake_api.py stands in for the
service (serve FAKE_JOBS_DIR with `python -m RangeHTTPServer`).
"""
import os
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

src, dst, place = sys.argv[1:4]
stop = sys.argv[4] if len(sys.argv) > 4 else None
CLICKS = {
    "pick_place(sr)": f'UI["place"].place.value = {place!r}; UI["place"].send.click(); '
                      'print(UI["place"].status.value)',
    "step2_inputs()": 'UI["q1"].fields[0].value = "6"; UI["q1"].fields[1].value = "yes"',
    "step3_stage1()": 'UI["q2"].fields[0].value = "the road grid"; '
                      'UI["view3"].east.value = 300; UI["view3"].size.value = 250',
    "step4_stage2()": 'UI["q3"].fields[0].value = "main road"; '
                      'UI["q3"].fields[1].value = "roof texture"',
    "step5_experiment()": 'UI["experiment"].guess.value = "less sharp"; '
                          'UI["experiment"].run.click(); print(UI["experiment"].status.value)',
    "step5_question()": 'UI["q4"].fields[0].value = "default Stage 2"; '
                        'UI["q4"].fields[1].value = "Stage 1"',
    "result_card()": 'UI["card"].again.click(); print(card_text())',
}
nb = nbformat.read(src, as_version=4)
cells = []
for c in nb.cells:
    if c.source.lstrip().startswith("%pip"):
        continue
    if stop and stop in c.source:
        break
    cells.append(c)
    if c.source.strip() in CLICKS:
        cells.append(nbformat.v4.new_code_cell(CLICKS[c.source.strip()]))
if os.environ.get("FAKE_JOBS_DIR"):
    fake = Path(__file__).parent / "fake_api.py"
    cells.insert(0, nbformat.v4.new_code_cell(f"exec(open({str(fake)!r}).read())"))
    os.environ.setdefault("SR_API_KEY", "srk_fake")
    os.environ.setdefault("SR_API_URL", "http://fake")
nb.cells = cells
t = time.time()
client = NotebookClient(nb, timeout=3600, kernel_name="python3",
                        resources={"metadata": {"path": os.path.dirname(os.path.abspath(dst))}})
try:
    client.execute()
finally:
    nbformat.write(nb, dst)
    print(f"executed in {time.time() - t:.0f} s -> {dst}")
