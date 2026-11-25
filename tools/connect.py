# ---- connecting to the SR service: your email is enough ---------------------------------------
# (tools/connect.py, pasted into every notebook that uses the service. The sign-up is the
# workshop's: the service gives each email a key, and the same email gets the same key back.)
import os

SERVICE_URL = "https://sr-service-dev--sr-service-api.modal.run"


def sr_signup(email, url=None):
    """Get the workshop key of an email address from the service and keep it, with the
    service address, in the environment (SR_API_KEY, SR_API_URL), where the client finds
    them. Raises RuntimeError with the service's message if it does not work."""
    import json
    import urllib.error
    import urllib.request

    url = (url or os.environ.get("SR_API_URL") or SERVICE_URL).rstrip("/")
    req = urllib.request.Request(f"{url}/v1/signup",
                                 data=json.dumps({"email": email.strip()}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            got = json.load(r)
    except urllib.error.HTTPError as exc:
        try:
            detail = json.load(exc)["detail"]
        except Exception:
            detail = f"the service answered with error {exc.code}"
        raise RuntimeError(detail if isinstance(detail, str)
                           else "that does not look like an email address") from None
    except OSError as exc:
        raise RuntimeError(f"the service could not be reached ({exc})") from None
    os.environ["SR_API_KEY"], os.environ["SR_API_URL"] = got["key"], url
    return got


def _stored_key():
    """A key that is already there: in the environment, or in Colab's Secrets (SR_API_KEY)."""
    if os.environ.get("SR_API_KEY"):
        return os.environ["SR_API_KEY"]
    try:
        from google.colab import userdata
        return userdata.get("SR_API_KEY") or ""
    except Exception:
        return ""


def connect():
    """Ask for your email address, get your key from the service, and return the connected
    client. (If you were given a key, type it instead of the email.)"""
    from sr_client import SRClient

    os.environ.setdefault("SR_API_URL", SERVICE_URL)
    key = _stored_key()
    while not key:
        answer = input("Your email address: ").strip()
        if answer.startswith("srk_"):
            key = answer
            break
        try:
            key = sr_signup(answer)["key"]
        except RuntimeError as exc:
            print(f"That did not work: {exc}. Try again, or ask an instructor.")
    os.environ["SR_API_KEY"] = key
    sr = SRClient()
    me = sr.me()
    print(f"Connected as {me['owner']}: areas up to {me['limits']['max_area_km']} km per side, "
          f"${me['budget']['remaining_usd']:.2f} of budget left.")
    return sr
