"""Execute a demo notebook from top to bottom, for testing.

    python tools/demos/run_nb.py IN.ipynb OUT.ipynb [NAME=VALUE ...]

NAME=VALUE replaces the value of a form field or constant (a line `NAME = ...`) wherever it is
set, e.g. PLACE='"Nueva Ecija rice farms"'. The %pip cell is skipped (use an environment with
sr-client[geo,viz] installed). SR_API_KEY / SR_API_URL come from the environment; with
FAKE_JOBS_DIR and FAKE_JOBS_URL set, fake_api.py stands in for the service.
"""
import os
import re
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

src, dst, *overrides = sys.argv[1:]
nb = nbformat.read(src, as_version=4)
nb.cells = [c for c in nb.cells if not c.source.lstrip().startswith("%pip")]
for item in overrides:
    name, value = item.split("=", 1)
    pat = re.compile(rf"^{name} = .*?(?=\s+# @param|$)", re.M)
    hit = 0
    for c in nb.cells:
        if c.cell_type == "code" and "# @title Helper functions" not in c.source:
            c.source, n = pat.subn(lambda m: f"{name} = {value}", c.source)
            hit += n
    print(f"{name}: set in {hit} place(s)")
if os.environ.get("FAKE_JOBS_DIR"):
    fake = Path(__file__).parent / "fake_api.py"
    nb.cells.insert(0, nbformat.v4.new_code_cell(f"exec(open({str(fake)!r}).read())"))
    os.environ.setdefault("SR_API_KEY", "srk_fake")
    os.environ.setdefault("SR_API_URL", "http://fake")
t = time.time()
client = NotebookClient(nb, timeout=3600, kernel_name="python3",
                        resources={"metadata": {"path": os.path.dirname(os.path.abspath(dst))}})
try:
    client.execute()
finally:
    nbformat.write(nb, dst)
    print(f"executed in {time.time() - t:.0f} s -> {dst}")
