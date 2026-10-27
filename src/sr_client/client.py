"""The SR service client: estimate, submit, wait, download."""

from __future__ import annotations

import math
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import httpx

FINISHED = ("done", "partial", "failed", "cancelled")


class SRError(Exception):
    """The service refused a request; ``status`` is the HTTP status."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"[{status}] {message}")
        self.status = status
        self.message = message


class JobFailed(Exception):
    """A job ended ``failed`` or ``cancelled`` (or ``wait`` timed out); ``job`` has details."""

    def __init__(self, job: Job, message: str) -> None:
        super().__init__(message)
        self.job = job


def area_around(lat: float, lon: float, km: float = 2.0) -> list[float]:
    """A ``km`` x ``km`` bounding box ``[W, S, E, N]`` centred on (lat, lon)."""
    dlat = km / 2 / 111.32
    dlon = km / 2 / (111.32 * max(math.cos(math.radians(lat)), 0.01))
    return [round(v, 6) for v in (lon - dlon, lat - dlat, lon + dlon, lat + dlat)]


def _area(area: Any) -> Any:
    """bbox ``[W, S, E, N]``, a GeoJSON geometry or Feature, or anything with
    ``__geo_interface__`` (shapely, geopandas)."""
    if hasattr(area, "__geo_interface__"):
        area = area.__geo_interface__
    if isinstance(area, dict) and area.get("type") == "FeatureCollection":
        features = area.get("features") or []
        if len(features) != 1:
            raise ValueError("pass a single polygon, not a collection of "
                             f"{len(features)} features")
        area = features[0]
    if isinstance(area, tuple):
        area = list(area)
    return area


def _detail(resp: httpx.Response) -> str:
    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        return resp.text or resp.reason_phrase
    if isinstance(detail, list):  # request validation errors
        return "; ".join(f"{'.'.join(str(p) for p in d.get('loc', [])[1:])}: {d.get('msg')}"
                         for d in detail)
    return str(detail)


class SRClient:
    """``SRClient(key, url)``; both default to $SR_API_KEY and $SR_API_URL.

    ``http`` replaces the HTTP client (tests pass an in-process one). Use it as a context
    manager, or call ``close()``, to release its connections.
    """

    def __init__(self, key: str | None = None, url: str | None = None, *,
                 http: httpx.Client | None = None, timeout: float = 60) -> None:
        key = key or os.environ.get("SR_API_KEY")
        if not key:
            raise ValueError("no API key: pass SRClient('srk_...') or set SR_API_KEY")
        if http is None:
            url = url or os.environ.get("SR_API_URL")
            if not url:
                raise ValueError("no service URL: pass SRClient(key, url=...) or set "
                                 "SR_API_URL")
            http = httpx.Client(base_url=url.rstrip("/"), timeout=timeout,
                                transport=httpx.HTTPTransport(retries=3))
        self._http = http
        self._auth = {"Authorization": f"Bearer {key}"}
        # Result links are presigned: they must be fetched without the API key.
        self._files = httpx.Client(timeout=timeout, follow_redirects=True,
                                   transport=httpx.HTTPTransport(retries=3))

    def close(self) -> None:
        self._http.close()
        self._files.close()

    def __enter__(self) -> SRClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _call(self, method: str, path: str, **kw) -> dict[str, Any]:
        resp = self._http.request(method, path, headers=self._auth, **kw)
        if resp.status_code >= 400:
            raise SRError(resp.status_code, _detail(resp))
        return resp.json()

    # ── account and models ──────────────────────────────────────────────────

    def me(self) -> dict[str, Any]:
        """Your key's limits and remaining budget."""
        return self._call("GET", "/v1/me")

    def models(self) -> list[dict[str, Any]]:
        return self._call("GET", "/v1/models")["models"]

    # ── jobs ────────────────────────────────────────────────────────────────

    def estimate(self, area: Any, target_date: str | date, **params: Any) -> dict[str, Any]:
        """Tiles, cost, the Sentinel-2 scenes found and likely warnings. Free; runs nothing."""
        return self._call("POST", "/v1/estimate", json=_body(area, target_date, params))

    def submit(self, area: Any, target_date: str | date, **params: Any) -> Job:
        """Start a job. ``params``: stages, time_window, max_cloud, min_clear, n_revisits,
        tau, nfe, seed, advanced (see ``models()`` and the service docs)."""
        info = self._call("POST", "/v1/jobs", json=_body(area, target_date, params))
        return Job(self, info["job_id"]).refresh()

    def job(self, job_id: str) -> Job:
        return Job(self, job_id).refresh()

    def jobs(self, limit: int = 50) -> list[Job]:
        """Your jobs, newest first."""
        return [Job(self, j["id"], j)
                for j in self._call("GET", "/v1/jobs", params={"limit": limit})["jobs"]]


def _body(area: Any, target_date: str | date, params: dict[str, Any]) -> dict[str, Any]:
    if isinstance(target_date, date):
        target_date = target_date.isoformat()
    return {"area": _area(area), "target_date": target_date, **params}


class Job:
    def __init__(self, client: SRClient, job_id: str, info: dict[str, Any] | None = None):
        self._client = client
        self.id = job_id
        self.info: dict[str, Any] = info or {}

    def __repr__(self) -> str:
        return f"Job({self.id!r}, status={self.status!r})"

    @property
    def status(self) -> str | None:
        return self.info.get("status")

    @property
    def warnings(self) -> list[dict[str, Any]]:
        return self.info.get("warnings", [])

    def refresh(self) -> Job:
        self.info = self._client._call("GET", f"/v1/jobs/{self.id}")
        return self

    def wait(self, poll_s: float = 10, timeout_s: float = 3 * 3600, quiet: bool = False) -> Job:
        """Poll until the job finishes; prints progress unless ``quiet``. Raises JobFailed if
        it failed, was cancelled or timed out; a ``partial`` job returns (check
        ``warnings``)."""
        t0 = time.monotonic()
        while True:
            self.refresh()
            if not quiet:
                print(f"\r{self._progress_line(time.monotonic() - t0)}", end="", flush=True)
            if self.status in FINISHED:
                break
            if time.monotonic() - t0 > timeout_s:
                raise JobFailed(self, f"job {self.id} still {self.status} after "
                                      f"{timeout_s:.0f} s")
            time.sleep(poll_s)
        if not quiet:
            print()
            for w in self.warnings:
                print(f"warning [{w['code']}]: {w['message']}", file=sys.stderr)
        if self.status in ("failed", "cancelled"):
            raise JobFailed(self, f"job {self.id} {self.status}: {self.info.get('error')}")
        return self

    def _progress_line(self, elapsed: float) -> str:
        steps = " · ".join(
            f"{p['step']} {p['done']}/{p['total']}" if p["total"] > 1 else
            f"{p['step']} {p['state']}"
            for p in self.info.get("progress", []) if p["state"] != "waiting")
        return f"{self.status:<9} {elapsed / 60:5.1f} min  {steps}".ljust(100)

    def cancel(self) -> Job:
        self._client._call("DELETE", f"/v1/jobs/{self.id}")
        return self.refresh()

    def upgrade(self) -> Job:
        """Add stage 2 to a finished stage-1 job (reuses its stage-1 tiles)."""
        self._client._call("POST", f"/v1/jobs/{self.id}/upgrade")
        return self.refresh()

    def results(self) -> dict[str, Any]:
        """Download links (valid 7 days; call again for fresh ones), warnings, attribution."""
        return self._client._call("GET", f"/v1/jobs/{self.id}/results")

    def download(self, dest: str | Path = "sr_results",
                 files: list[str] | None = None) -> dict[str, Path]:
        """Save the job's files (or just ``files``) under ``dest/<job id>/``."""
        links = self.results()["files"]
        out = Path(dest) / self.id
        out.mkdir(parents=True, exist_ok=True)
        paths = {}
        for name, url in links.items():
            if files is not None and name not in files:
                continue
            path = out / name
            with self._client._files.stream("GET", url) as resp:
                if resp.status_code >= 400:
                    raise SRError(resp.status_code, f"download of {name} failed")
                with open(path, "wb") as fh:
                    for chunk in resp.iter_bytes(1 << 20):
                        fh.write(chunk)
            paths[name] = path
        return paths

    def show(self, figsize: tuple[float, float] = (14, 7)) -> None:
        """Side-by-side RGB previews of the published stages (needs ``[viz]``)."""
        import io

        import matplotlib.pyplot as plt
        from PIL import Image

        links = self.results()["files"]
        previews = [n for n in ("stage1_preview.png", "stage2_preview.png") if n in links]
        if not previews:
            print(f"job {self.id} has no previews yet (status {self.status})")
            return
        fig, axes = plt.subplots(1, len(previews), figsize=figsize, squeeze=False)
        for ax, name in zip(axes[0], previews):
            img = Image.open(io.BytesIO(self._client._files.get(links[name]).content))
            ax.imshow(img)
            ax.set_title(name.replace("_preview.png", "").replace("stage", "stage "))
            ax.axis("off")
        fig.tight_layout()
        plt.show()

    def open(self, name: str = "stage2_sr.tif", reflectance: bool = True):
        """The raster as an xarray DataArray read straight from its link (needs ``[geo]``).

        ``reflectance`` scales the stored uint16 to reflectance and masks nodata (0).
        """
        import rioxarray

        da = rioxarray.open_rasterio(self.results()["files"][name])
        if reflectance and name != "validity.tif":
            da = da.where(da != 0) / 10000.0
        return da
