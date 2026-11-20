"""Run the hackathon notebooks' ready-made areas on the SR service before the workshop.

Teams then get these jobs back from the cache in seconds and at no cost. The areas are read
from the READY_MADE cell of each notebook, so the notebooks stay the single source.

    export SR_API_KEY=srk_... SR_API_URL=https://...
    python tools/hackathon/prestage.py            # estimates only (free)
    python tools/hackathon/prestage.py --run      # submit all, wait, print job ids and warnings
"""
import argparse
import json
from pathlib import Path

from sr_client import SRClient, area_around  # noqa: F401  (used by the exec'd cells)

NB_DIR = Path(__file__).resolve().parents[2] / "notebooks" / "hackathon"


def ready_made():
    out = {}
    for nb in sorted(NB_DIR.glob("*/*.ipynb")):
        for cell in json.loads(nb.read_text())["cells"]:
            src = "".join(cell["source"])
            if cell["cell_type"] == "code" and src.lstrip().startswith(("READY_MADE", "EVENT_DAY")) or \
                    "\nREADY_MADE = {" in src:
                ns = {"area_around": area_around}
                exec(src, ns)
                for name, p in ns["READY_MADE"].items():
                    out[f"{nb.parent.name}: {name}"] = p
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="submit the jobs (costs GPU budget)")
    args = ap.parse_args()
    sr = SRClient()  # SR_API_KEY / SR_API_URL from the environment
    places = ready_made()
    total = 0.0
    for name, p in places.items():
        est = sr.estimate(p["area"], p["date"], **p.get("options", {}))
        total += est.get("estimated_usd", 0)
        warn = ", ".join(w.get("code", "?") for w in est.get("warnings_likely", []))
        warn += "".join(f" PROBLEM: {x}" for x in est.get("problems", []))
        print(f"{name}: {est.get('tiles')} tiles, ~${est.get('estimated_usd', 0):.2f}, "
              f"{len(est.get('scenes', []))} scenes {('[' + warn + ']') if warn else ''}")
    print(f"total ~${total:.2f} (before caching)")
    if not args.run:
        return
    for name, p in places.items():
        job = sr.submit(p["area"], p["date"], **p.get("options", {}))
        job.wait()
        print(f"{name}: job {job.id}, warnings {[w['code'] for w in job.warnings]}")


if __name__ == "__main__":
    main()
