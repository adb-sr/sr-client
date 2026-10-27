"""Python client for the SR service: super-resolved Sentinel-2 imagery on demand.

    from sr_client import SRClient, area_around

    sr = SRClient("srk_...", url="https://...")        # or set SR_API_KEY / SR_API_URL
    job = sr.submit(area_around(14.60, 120.98, km=2), "2025-12-01")
    job.wait()
    job.show()                                          # needs sr-client[viz]
    paths = job.download()
"""

from .client import Job, SRClient, SRError, area_around

__all__ = ["Job", "SRClient", "SRError", "area_around"]
__version__ = "0.1.0"
