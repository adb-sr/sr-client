# ---- "your scenario": the team chooses a decision, then judges whether SR fits ----------------
# Pasted after hk.py, hk_widgets.py and areas.py by build.py (scenario notebook only).
# Parts: 1 scenario, 2 area and dates, 3 cost, 4 compare the images, 5 cheat sheet and test
# plan, 6 slide card. Nothing waits for input; the service is needed only for an own area (or
# if the ready-made images did not download).

LEVEL_NAME = {k: n for k, n, _ in LEVELS}
LEVEL_TAU = {k: t for k, _, t in LEVELS if t}
PKG = {}          # ready-made areas whose images came with the download: slug -> facts
OWN = "own"
_COLAB = "https://colab.research.google.com/github/adb-sr/sr-client/blob/main/notebooks/hackathon/"
MEASURED = {
    "ifs": ("Informal settlements, Metro Manila",
            _COLAB + "informal_settlements/hackathon_informal_settlements.ipynb"),
    "lc": ("Land cover around Hanoi", _COLAB + "land_cover/hackathon_land_cover.ipynb"),
    "ai4": ("Field boundaries of smallholder farms",
            _COLAB + "field_boundaries/hackathon_field_boundaries.ipynb"),
}
# computing cost of the SR service per km² of a large area (240 m between tiles; stage 2 costs
# tau steps per tile). Sentinel-2 itself is free.
SR_USD_KM2 = {"stage1": 0.0002, "t100": 0.005, "t250": 0.013, "t500": 0.026}


def get_areas(base_url, name="scenario_areas"):
    """Download the images of the ready-made areas once. Without them the notebook still
    works: the areas then come from the SR service (part 2)."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    marker = DATA_ROOT / f".{name}.done"
    if not marker.exists():
        tmp = DATA_ROOT / f"{name}.zip"
        print(f"Downloading {name}.zip ...")
        try:
            _fetch(f"{str(base_url).rstrip('/')}/{name}.zip", tmp)
            with zipfile.ZipFile(tmp) as z:
                z.extractall(DATA_ROOT)
            tmp.unlink()
            marker.touch()
        except Exception as e:
            print(f"  The ready-made images did not download ({e}). You can still work: "
                  "connect to the SR service in part 2.")
    PKG.clear()
    meta = DATA_ROOT / name / "meta.json"
    if meta.exists():
        PKG.update({k: v for k, v in json.loads(meta.read_text())["areas"].items() if k in AREAS})
    print(f"Ready-made areas with images: {len(PKG)} of {len(AREAS)}.")


def _pkg_layers(slug, name="scenario_areas"):
    out = {}
    for k, _, _ in LEVELS:
        for ext in ("jpg", "png"):
            p = DATA_ROOT / name / slug / f"{k}.{ext}"
            if p.exists():
                out[k] = np.asarray(Image.open(p).convert("RGB"))
                break
    return out


def _card(html_text, colour="#007DB7"):
    return f"<div style='{_CARD.replace('#007DB7', colour)}'>{html_text}</div>"


def _said(key):
    v = ANSWERS.get(key)
    return v if v not in ("", None, []) else "(not answered)"


# ---- part 1: the scenario ----------------------------------------------------------------------

# key, question, example, label on the card
CANVAS = [
    ("team", "Team name", "Team A", "TEAM"),
    ("decision_maker", "Who decides?", "City housing office, settlement upgrading programme",
     "WHO DECIDES"),
    ("decision", "What do they decide, and how often?",
     "Which blocks get a field validation, every quarter", "DECISION"),
    ("today", "How do they decide today?", "From a six-year-old list and from complaints",
     "TODAY"),
    ("object", "What must the image show?", "Dense small roofs with no streets between them",
     "MUST SHOW"),
    ("metric", "Which number shows success?", "Of 20 visits, how many find a settlement",
     "SUCCESS"),
    ("minimum", "The minimum you need, and why",
     "10 of 20: below that, the teams stop trusting the map", "MINIMUM"),
    ("below", "What does an error cost, and who pays?",
     "A wasted team-day; families left off the list for a year", "ERRORS COST"),
]
UPDATES = [("once a year", 1), ("twice a year", 2), ("every quarter", 4), ("every month", 12)]

# Our own example scenarios: a team that is stuck can start from one.
STARTERS = [
    dict(title="Housing office: which blocks do the validation teams visit first?",
         task="settlements", area="tondo", size_m=5, area_km2=620, updates=4, fields=dict(
             decision_maker="Regional office for housing and urban development, settlement "
                            "upgrading programme",
             decision="Which 20 city blocks get a field validation, every quarter",
             today="From a list of informal settlements that is years old",
             object="Dense small roofs with no streets between them (blocks of 100 m)",
             metric="Of 20 visits, how many find an informal settlement",
             minimum="10 of 20: below that, the teams go back to the old list",
             below="A wasted team-day; families left out of the shelter plan for a year")),
    dict(title="Space agency: a settlement watch list for local governments?",
         task="settlements", area="payatas", size_m=5, area_km2=300000, updates=4, fields=dict(
             decision_maker="National space agency, space applications team",
             decision="Whether to send every city a list of likely settlement blocks, each quarter",
             today="No regular list; cities ask one by one",
             object="Blocks where informal housing is likely",
             metric="Of the top 50 blocks on a city's list, how many are right",
             minimum="35 of 50: each wrong flag on a formal neighbourhood costs trust",
             below="Local staff stop reading the list")),
    dict(title="Environment department: which building sites get a dust inspection?",
         task="landcover", area="new_clark", size_m=20, area_km2=3360, updates=12, fields=dict(
             decision_maker="City environment department, air-quality enforcement unit",
             decision="Which 20 places get a dust-control inspection, every month",
             today="Inspectors go where complaints come from",
             object="Open, bare ground: building sites, cleared land, sand yards",
             metric="Of 20 inspections, how many find open bare ground",
             minimum="14 of 20: complaints alone already give about 10",
             below="A wasted inspector-day; a dust source uncontrolled for a month")),
    dict(title="Zoning office: are houses going up on protected farmland?",
         task="buildings", area="sjdm", size_m=8, area_km2=3360, updates=4, fields=dict(
             decision_maker="Provincial land-use and zoning office, compliance team",
             decision="Which 15 farmland sites get a check for buildings without a permit, "
                      "every quarter",
             today="No recent map; tips from neighbours",
             object="Single houses (about 8 m) among fields",
             metric="Of 15 site checks, how many find a building on farmland",
             minimum="8 of 15, and no notice is ever sent from the image alone",
             below="A wasted inspector-day; a building stands for another quarter")),
    dict(title="Public works: which parts of the road map are out of date?",
         task="roads", area="munoz", size_m=4, area_km2=5000, updates=1, fields=dict(
             decision_maker="Public works department, planning division",
             decision="Which map cells the road mappers redraw first, once a year",
             today="The inventory misses many farm-to-market roads",
             object="Roads 3 to 6 m wide, many narrower than a Sentinel-2 pixel",
             metric="Of 40 cells redrawn, how many hold a road missing from the inventory",
             minimum="25 of 40",
             below="Half a mapper-day; a road stays off the maintenance list for a year")),
    dict(title="Parks office: where is the tree cover we must protect?",
         task="landcover", area="marikina", size_m=30, area_km2=640, updates=1, fields=dict(
             decision_maker="Parks and green space office, urban greening team",
             decision="Which 20 places get a tree survey and a protection order, once a year",
             today="An old vegetation map",
             object="Groups of trees of 30 m and more",
             metric="Of 20 surveys, how many find dense tree cover",
             minimum="18 of 20: free Sentinel-2 may already reach that",
             below="A wasted surveyor-day; a group of trees stays unprotected")),
    dict(title="Agriculture office: which villages get the farmer-registry teams?",
         task="fields", area="munoz", size_m=5, area_km2=5000, updates=2, fields=dict(
             decision_maker="Department of agriculture regional office, smallholder programme",
             decision="Which 30 areas the extension workers visit to enrol farmers, twice a year",
             today="No map of the fields; the smallest farms are missing from the registry",
             object="Field boundaries: bunds and paths 1 to 3 m wide between small fields",
             metric="Of 30 visits, how many reach an area with many small farms",
             minimum="20 of 30",
             below="A wasted worker-day; about 30 smallholders not enrolled this season")),
    dict(title="Statistics office: where does the farm census need a second enumerator?",
         task="fields", area="nueva_ecija", size_m=5, area_km2=5000, updates=1, fields=dict(
             decision_maker="National statistics office, agricultural statistics division",
             decision="Which 20 square kilometres get a second enumerator, once per census",
             today="A parcel count that is ten years old",
             object="Parcels, to count them per square kilometre",
             metric="Of 20 squares chosen, how many have very many parcels",
             minimum="15 of 20",
             below="An enumerator sent where one was enough; a square counted late")),
    dict(title="Disaster office: how far did the flood reach?",
         task="flood", area="marikina", size_m=20, area_km2=640, updates=12, fields=dict(
             decision_maker="City disaster risk reduction and management office",
             decision="Which barangays get relief and damage assessment teams, after each flood",
             today="Reports by phone from barangay captains",
             object="The edge of the water, to the nearest street (about 20 m)",
             metric="Share of flooded barangays that the map shows as flooded",
             minimum="9 of 10: a missed barangay waits a day longer for help",
             below="Teams sent to dry streets; flooded families reached late")),
    dict(title="Mining regulator: which quarries dig outside their permit?",
         task="landcover", area="rodriguez", size_m=15, area_km2=1200, updates=4, fields=dict(
             decision_maker="Provincial mining regulatory board",
             decision="Which 20 quarry sites get an inspection, every quarter",
             today="By rotation: each site about every two years",
             object="Freshly dug ground next to a permit boundary (15 m and more)",
             metric="Of 20 inspections, how many find digging outside the permit area",
             minimum="8 of 20: rotation finds about 3",
             below="A wasted inspector-day; illegal digging continues for a quarter")),
    dict(title="Fisheries office: which fishponds are in use?",
         task="flood", area="hagonoy", size_m=10, area_km2=900, updates=2, fields=dict(
             decision_maker="Provincial fisheries office",
             decision="Which pond owners get a visit about lease renewal, twice a year",
             today="Lease records on paper; no map of which ponds hold water",
             object="Pond dikes (2 to 5 m wide) and whether a pond holds water",
             metric="Of 30 visits, how many ponds are in the state the map showed",
             minimum="24 of 30",
             below="A wasted visit by boat; a lapsed lease goes unnoticed")),
]


def canvas():
    """Part 1: the team's own scenario. Every field saves itself. 'Stuck?' offers our example
    scenarios; one click fills the fields, which stay editable."""
    form = ask(*[(k, t, "text", ex) for k, t, ex, _ in CANVAS], show=False)
    size = W.BoundedFloatText(value=5, min=0.3, max=500, step=0.5, style=_LABEL,
                              description="Smallest thing you must see (m)")
    area = W.BoundedFloatText(value=600, min=1, max=1e8, step=10, style=_LABEL,
                              description="Area to cover (km²)")
    updates = W.ToggleButtons(options=UPDATES, value=4, description="New map needed",
                              style=_buttons("110px"))
    hint = W.HTML()

    def on_num(_=None):
        ANSWERS.update(size_m=size.value, area_km2=area.value, updates=updates.value)
        hint.value = _note(_size_rule(size.value), "#555")
        for redraw in list(ANSWER_REFRESH.values()):
            redraw()
    for c in (size, area, updates):
        c.observe(on_num, names="value")

    pick = W.Dropdown(options=[("(choose one)", -1)] + [(s["title"], i)
                                                        for i, s in enumerate(STARTERS)],
                      value=-1, layout=W.Layout(width="720px"))
    fill = W.Button(description="Use this example", icon="clipboard",
                    layout=W.Layout(width="260px"))
    told = W.HTML()

    def on_fill(_):
        if pick.value < 0:
            return
        s = STARTERS[pick.value]
        for k, f in form.fields.items():
            if k != "team":
                f.value = s["fields"].get(k, "")
        size.value, area.value, updates.value = s["size_m"], s["area_km2"], s["updates"]
        ANSWERS["starter"] = s["title"]
        for name, key in (("area", "place"), ("cheat", "task")):
            if name in UI and hasattr(UI[name], key):
                try:
                    getattr(UI[name], key).value = s["area" if name == "area" else "task"]
                except Exception:
                    pass
        told.value = _note("Done. Now change the fields to fit <b>your</b> agency. Part 2 has "
                           "chosen a matching area.", "#1a7f37")
    fill.on_click(on_fill)
    stuck = W.Accordion(children=[W.VBox([
        W.HTML(_note("Example scenarios. The decisions are realistic; the offices and the "
                     "numbers are invented.")), pick, fill, told])])
    stuck.set_title(0, "Stuck? Start from an example")
    stuck.selected_index = None
    ui = W.VBox([form, W.HTML("<b>Three numbers for the next parts</b>"), size, hint, area,
                 updates, stuck])
    ui.fields, ui.size, ui.area, ui.updates = form.fields, size, area, updates
    ui.pick, ui.fill = pick, fill
    UI["canvas"] = ui
    on_num()
    display(ui)


def _size_rule(m):
    if m < 2.5:
        return (f"{m:g} m is smaller than an SR pixel (2.5 m). SR cannot show it; anything it "
                "draws at that size is invented. You need real high-resolution images.")
    if m < 10:
        return (f"{m:g} m is between an SR pixel (2.5 m) and a Sentinel-2 pixel (10 m). SR can "
                "help here, and it can also invent. Test it.")
    if m < 20:
        return (f"{m:g} m is one to two Sentinel-2 pixels. Try Sentinel-2 first; SR may "
                "sharpen it.")
    return f"{m:g} m is several Sentinel-2 pixels. Free Sentinel-2 probably shows it already."


def canvas_dict():
    return {k: (ANSWERS.get(k) or "").strip() or "(not answered)" for k, *_ in CANVAS}


# ---- part 2: area and dates --------------------------------------------------------------------

def _scene_html(info):
    """Sentinel-2 images found, cost and warnings, from the service's estimate or the package."""
    scenes = info.get("scenes") or []
    dates = sorted({s["date"] for s in scenes})
    rows = [f"<b>Sentinel-2 images found:</b> {len(scenes)} images on {len(dates)} days"
            + (f", {dates[0]} to {dates[-1]}" if dates else "")]
    clouds = [s["cloud_cover"] for s in scenes if s.get("cloud_cover") is not None]
    if clouds:
        rows.append(f"<b>Cloud cover:</b> {min(clouds):.0f} % to {max(clouds):.0f} %")
    if len(dates) < 4:
        rows.append("<span style='color:#b00020'><b>Fewer than 4 days with images.</b> "
                    "Super-resolution needs several. Try another date, ideally in the dry "
                    "season.</span>")
    usd = info.get("usd") or {}
    if usd:
        rows.append("<b>Computing cost for this area:</b> " + ", ".join(
            f"{LEVEL_NAME[k].replace('SR ', '')} USD {v:.2f}" for k, v in usd.items()))
    codes = [w if isinstance(w, str) else w.get("code", "?")
             for w in info.get("warnings") or []]
    if codes:
        rows.append("<b>Warnings:</b> " + ", ".join(codes)
                    + ("  (SR removes detail in shallow water; use Sentinel-2 there)"
                       if "water" in codes else ""))
    for p in info.get("problems") or []:
        rows.append(f"<span style='color:#b00020'><b>Problem:</b> {_html.escape(str(p))}</span>")
    return "<br>".join(rows)


def _connect_box(on_connected):
    key = W.Password(value=os.environ.get("SR_API_KEY", ""), description="API key (srk_...)",
                     layout=_WIDE, style=_LABEL)
    url = W.Text(value=os.environ.get("SR_API_URL", ""), description="Service address",
                 layout=_WIDE, style=_LABEL, placeholder="https://...")
    go = W.Button(description="Connect", icon="plug", button_style="primary",
                  layout=W.Layout(width="220px"))
    status = W.HTML()

    def on_go(_):
        go.disabled = True
        try:
            try:
                importlib.import_module("sr_client")
            except ImportError:
                status.value = _note("Getting the SR client (about a minute, once) ...")
                subprocess.run([sys.executable, "-m", "pip", "install", "-q", SR_CLIENT],
                               check=True)
                importlib.invalidate_caches()
            from sr_client import SRClient
            sr = SRClient(key.value.strip() or _secret("SR_API_KEY"),
                          url=url.value.strip() or _secret("SR_API_URL"))
            left = sr.me().get("budget")
            S["sr"] = sr
            status.value = _note(f"Connected. Budget of this key: {left}", "#1a7f37")
            on_connected()
        except Exception as exc:
            status.value = _note(f"Could not connect: {_html.escape(str(exc))}. Check the key "
                                 "and the address on your team card.", "#b00020")
        finally:
            go.disabled = False
    go.on_click(on_go)
    box = W.VBox([W.HTML(_note("The API key and the service address are on your team card.")),
                  key, url, go, status])
    box.key, box.url, box.go, box.status = key, url, go, status
    return box


def area_panel():
    """Part 2: choose a ready-made area (its images come with the notebook) or your own area
    (the SR service makes the images; send before lunch). Shows which Sentinel-2 images exist
    and what the computing costs."""
    themed = [(f"{a['theme']}  ·  {a['name']}" + ("  ★" if a.get("measured") else ""), slug)
              for slug, a in AREAS.items()]
    place = W.Dropdown(options=themed + [("Our own area (needs the API key)", OWN)],
                       value=themed[0][1], description="Area", layout=W.Layout(width="760px"),
                       style={"description_width": "60px"})
    info = W.HTML()
    lat = W.FloatText(value=14.5960, description="Latitude", style=_LABEL)
    lon = W.FloatText(value=120.9620, description="Longitude", style=_LABEL)
    km = W.BoundedFloatText(value=2, min=0.5, max=2, step=0.5, description="Size (km, up to 2)",
                            style=_LABEL)
    day = W.Text(value="2026-03-15", description="Date (YYYY-MM-DD)", style=_LABEL)
    own = W.VBox([W.HTML(_note(
        "Enter a point, a size and a date. In Google Maps, right-click the place and click "
        "the coordinates to copy them. Pick a date in the dry season. The service takes 5 to "
        "10 minutes, so <b>send before lunch</b>.")),
        lat, lon, km, day])
    check = W.Button(description="Check Sentinel-2 images (free)", icon="search",
                     layout=W.Layout(width="300px"))
    send = W.Button(description="Send to the SR service", icon="rocket", button_style="primary",
                    layout=W.Layout(width="300px"))
    status = W.HTML()

    def chosen():
        if place.value == OWN:
            return dict(slug=OWN, name=f"Our own area ({lat.value:.4f}, {lon.value:.4f})",
                        lat=lat.value, lon=lon.value, km=km.value, date=day.value.strip())
        return dict(slug=place.value, **AREAS[place.value])

    def refresh(_=None):
        a = chosen()
        S["area"] = a
        S.pop("layers", None)
        ANSWERS["area"] = f"{a['name']}, {a['km']:g} km × {a['km']:g} km, around {a['date']}"
        ready = a["slug"] in PKG
        own.layout.display = "" if a["slug"] == OWN else "none"
        if a["slug"] == OWN:
            info.value = ""
        else:
            lines = [f"<b>{a['name']}</b>: {a['theme'].lower()}. {a['km']} km × {a['km']} km, "
                     f"images around {a['date']}."]
            if a.get("measured"):
                t, link = MEASURED[a["measured"]]
                lines.append("★ Experts mapped this place, so we have measured results for it: "
                             f"see the notebook <a href='{link}' target='_blank'>{t}</a>.")
            if ready:
                S["scene_info"] = PKG[a["slug"]]
                lines += [_scene_html(PKG[a["slug"]]),
                          "<span style='color:#1a7f37'><b>The images are ready.</b> No key "
                          "needed. Go on to part 3.</span>"]
            else:
                S.pop("scene_info", None)
                lines.append("<span style='color:#8a6d00'>The images for this area did not "
                             "download. Connect to the SR service below and press "
                             "<b>Send</b>.</span>")
            info.value = _card("<br>".join(lines))
        service.layout.display = "none" if ready else ""
        for redraw in list(ANSWER_REFRESH.values()):
            redraw()

    def need_sr():
        if "sr" not in S:
            status.value = _note("Connect first: type the key and the address, then press "
                                 "Connect.", "#b00020")
            return None
        return S["sr"]

    def on_check(_):
        sr = need_sr()
        if not sr:
            return
        check.disabled = True
        try:
            a = chosen()
            box = area_around(a["lat"], a["lon"], km=a["km"])
            out = {"usd": {}}
            for k, tau in LEVEL_TAU.items():
                est = sr.estimate(box, a["date"], tau=tau)
                out["usd"][k] = est.get("estimated_usd", 0)
                out.update({f: est.get(f) for f in ("scenes", "problems")})
                out["warnings"] = est.get("warnings_likely", [])
            S["scene_info"] = out
            status.value = _card(_scene_html(out))
            for redraw in list(ANSWER_REFRESH.values()):
                redraw()
        except Exception as exc:
            status.value = _note(f"The service said: {_html.escape(str(exc))}", "#b00020")
        finally:
            check.disabled = False

    def on_send(_):
        sr = need_sr()
        if not sr:
            return
        send.disabled = True
        try:
            a = chosen()
            box = area_around(a["lat"], a["lon"], km=a["km"])
            jobs = {}
            for k, tau in LEVEL_TAU.items():
                jobs[k] = sr.submit(box, a["date"], tau=tau)
            S["jobs"], S["jobs_area"] = jobs, a
            status.value = _card(
                "<b>Sent.</b> The service is working. After lunch, press <b>Load the "
                "images</b> in part 4.<br>If the notebook restarts: enter the same area and "
                "date and press Send again. The result comes back at once, at no cost."
                "<br><span style='color:#777'>Jobs: "
                + ", ".join(f"{k} {j.id[:8]}" for k, j in jobs.items()) + "</span>", "#1a7f37")
        except Exception as exc:
            status.value = _note(f"The service said: {_html.escape(str(exc))}", "#b00020")
        finally:
            send.disabled = False

    connect = _connect_box(lambda: None)
    service = W.VBox([W.HTML("<b>The SR service</b>"), connect, own, W.HBox([check, send]),
                      status])
    for c in (place, lat, lon, km, day):
        c.observe(refresh, names="value")
    check.on_click(on_check)
    send.on_click(on_send)
    ui = W.VBox([place, W.HTML(_note("★ = experts mapped this place, so we have measured "
                                     "results for it.", "#777")),
                 info, service])
    ui.place, ui.info, ui.connect, ui.check, ui.send, ui.status = (place, info, connect, check,
                                                                   send, status)
    ui.own_fields = (lat, lon, km, day)
    UI["area"] = ui
    refresh()
    display(ui)


# ---- part 3: cost ------------------------------------------------------------------------------

def money_panel():
    """Part 3: the image cost for the whole area, per kind of image, and what real images
    would have to save to be worth their price."""
    price_hr = W.BoundedFloatText(value=10, min=0, max=1000, step=1, style=_LABEL,
                                  description="Real images, USD per km²")
    min_order = W.BoundedFloatText(value=25, min=0, max=10000, step=25, style=_LABEL,
                                   description="Smallest order (km²)")
    level = W.ToggleButtons(options=[(LEVEL_NAME[k].replace("SR ", ""), k) for k in SR_USD_KM2],
                            value="t250", description="SR image", style=_buttons("150px"))
    price_sr = W.BoundedFloatText(value=SR_USD_KM2["t250"], min=0, max=100, step=0.001,
                                  style=_LABEL, description="Super-resolution, USD per km²")
    share = W.IntSlider(value=5, min=1, max=50, continuous_update=False, layout=_WIDE,
                        style=_LABEL, description="Mix: real images for (%)")
    wasted = W.BoundedFloatText(value=150, min=1, max=1e6, step=10, style=_LABEL,
                                description="One wasted visit costs (USD)")
    chart = W.Image(format="png", layout=W.Layout(max_width="100%"))
    reading, status = W.HTML(), W.HTML()

    def on_level(_):
        price_sr.value = SR_USD_KM2[level.value]
    level.observe(on_level, names="value")

    def draw(_=None):
        try:
            status.value = ""
            area = float(ANSWERS.get("area_km2", 600))
            n = int(ANSWERS.get("updates", 4))
            every = next(t for t, v in UPDATES if v == n)
            sr = area * price_sr.value * n
            real = max(area, min_order.value) * price_hr.value * n
            part = max(area * share.value / 100, min_order.value) * price_hr.value * n
            mixed = sr + part
            name = LEVEL_NAME[level.value]
            rows = [("Sentinel-2 only", 0.0, COLOURS["s2"]), (name, sr, COLOURS["stage2"]),
                    (f"{name} + real images\nfor {share.value} % of the area", mixed, "#f2a900"),
                    ("Real images everywhere", real, COLOURS["hr"])]
            fig, ax = plt.subplots(figsize=(8.6, 2.9))
            top = max(real, mixed, sr, 1)
            for i, (label, usd, colour) in enumerate(rows):
                ax.barh(i, max(usd, top * 0.004), color=colour)
                ax.text(max(usd, top * 0.004) + top * 0.01, i,
                        "free" if usd == 0 else f"USD {usd:,.0f}", va="center")
            ax.set_yticks(range(len(rows)))
            ax.set_yticklabels([r[0] for r in rows])
            ax.invert_yaxis()
            ax.set_xlim(0, top * 1.2)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
            ax.set_xlabel(f"image cost per year (USD): {area:,.0f} km², {every}")
            chart.value = _png(fig)
            gap = real - sr
            visits = gap / wasted.value
            lines = [
                f"<b>Per year:</b> Sentinel-2 free; {name} about <b>USD {sr:,.0f}</b>; real "
                f"images about <b>USD {real:,.0f}</b>"
                + (f" (the smallest order, {min_order.value:,.0f} km², is larger than your "
                   "area)" if min_order.value > area else "") + ".",
                f"<b>What must real images save?</b> They cost USD {gap:,.0f} more per year "
                f"than {name}. That equals <b>{visits:,.0f} wasted visits a year</b> at USD "
                f"{wasted.value:,.0f} each ({visits / n:,.0f} per map). Real images pay off "
                "only if they prevent more than that.",
                f"<b>The mix:</b> {name} for the whole area, real images for {share.value} % "
                f"of it: about <b>USD {mixed:,.0f}</b> a year.",
            ]
            info = S.get("scene_info") or {}
            a = S.get("area") or {}
            if info.get("usd") and a.get("km"):
                lines.append("<span style='color:#777'>Your area in part 2 "
                             f"({a['km'] ** 2:g} km²) costs USD "
                             f"{info['usd'].get(level.value, 0):.2f} to compute. Small areas "
                             "cost more per km² than large ones.</span>")
            lines.append("<span style='color:#777'>Default prices: real images USD 4–19 per "
                         "km² at list price, often with a smallest order of 25–100 km² "
                         "(Sessions 1 and 3). Super-resolution: computing cost only "
                         "(Session 4). Staff, field checks and storage are extra for every "
                         "option. Change the numbers to yours.</span>")
            reading.value = _card("".join(f"<p style='margin:6px 0'>{x}</p>" for x in lines))
            S["money"] = [f"{area:,.0f} km², {every}",
                          f"Sentinel-2 free; {name} USD {sr:,.0f}; real images USD {real:,.0f} "
                          "a year",
                          f"real images pay off only if they prevent more than {visits:,.0f} "
                          f"wasted visits a year (USD {wasted.value:,.0f} each)",
                          f"mix ({name} + real images for {share.value} %): USD {mixed:,.0f} "
                          "a year"]
            if "scenario_card" in ANSWER_REFRESH:
                ANSWER_REFRESH["scenario_card"]()
        except Exception as exc:
            status.value = _error(exc)
    controls = [price_hr, min_order, level, price_sr, share, wasted]
    for w in controls:
        w.observe(draw, names="value")
    seen = {}

    def on_answer():          # only the numbers of part 1 matter here, not every keystroke
        now = (ANSWERS.get("area_km2"), ANSWERS.get("updates"), id(S.get("scene_info")))
        if seen.get("now") != now:
            seen["now"] = now
            draw()
    ANSWER_REFRESH["money"] = on_answer
    numbers = W.HTML(_note("The area and how often you need a new map come from part 1.",
                           "#777"))
    ui = W.VBox([numbers, price_hr, min_order, level, price_sr, share, wasted, status, chart,
                 reading])
    ui.controls = {w.description: w for w in controls}
    ui.chart, ui.reading = chart, reading
    UI["money"] = ui
    draw()
    display(ui)


# ---- part 4: compare the images ----------------------------------------------------------------

def _job_layers(jobs):
    """Finished jobs (image key -> job) to display layers. Sentinel-2 and stage 1 come from
    the first job; stage 2 from each."""
    raw = {}

    def rgb(job, name):
        da = job.open(name)
        return np.moveaxis(da.isel(band=[0, 1, 2]).values.astype("float32"), 0, -1)
    first = next(iter(jobs.values()))
    files = first.results()["files"]
    if "lr_reference.tif" in files:
        raw["s2"] = rgb(first, "lr_reference.tif")
    if "stage1_sr.tif" in files:
        raw["stage1"] = rgb(first, "stage1_sr.tif")
    for k, job in jobs.items():
        if "stage2_sr.tif" in job.results()["files"]:
            raw[k] = rgb(job, "stage2_sr.tif")
    return stretch_u8(raw)


def _compare_viewer(layers, px=2.5):
    """The images side by side (or two of them, large), with zoom and position sliders."""
    keys = [k for k, _, _ in LEVELS if k in layers]
    ref = max(keys, key=lambda k: layers[k].shape[0])
    h, w = layers[ref].shape[:2]
    half = int(min(h, w) * px / 2)
    sizes = [(t, v) for t, v in (("250 m", 100), ("500 m", 200), ("1 km", 400)) if v < max(h, w)]
    size = W.ToggleButtons(options=sizes + [("whole area", max(h, w))],
                           value=200 if max(h, w) > 200 else max(h, w), description="Zoom",
                           style=_buttons("90px"))
    mode = W.ToggleButtons(options=[("all side by side", "all"), ("two, large", "two")],
                           value="all", description="Show", style=_buttons("130px"))
    names = [(LEVEL_NAME[k], k) for k in keys]
    left = W.Dropdown(options=names, value=keys[0], description="Left", style=_LABEL)
    right = W.Dropdown(options=names, value=keys[-1], description="Right", style=_LABEL)
    pair = W.HBox([left, right])
    pair.layout.display = "none"
    colours = W.ToggleButtons(options=[("same for all", "shared"), ("each its own", "own")],
                              value="shared", description="Contrast", style=_buttons("110px"),
                              tooltips=["one stretch for all images: a fair comparison",
                                        "each image stretched by itself"])
    east = W.IntSlider(value=0, min=-half, max=half, step=50, continuous_update=False,
                       description="← west | east → (m)", layout=_WIDE, style=_LABEL)
    north = W.IntSlider(value=0, min=-half, max=half, step=50, continuous_update=False,
                        description="← south | north → (m)", layout=_WIDE, style=_LABEL)
    image = W.Image(format="png", layout=W.Layout(max_width="100%"))

    def crop(k, cy, cx, s):
        a = layers[k]
        f = a.shape[0] / h           # the 10 m image has fewer pixels
        return a[int((cy - s / 2) * f):int((cy + s / 2) * f),
                 int((cx - s / 2) * f):int((cx + s / 2) * f)]

    def draw(_=None):
        pair.layout.display = "" if mode.value == "two" else "none"
        s = min(size.value, h, w)
        cy = int(np.clip(h / 2 - north.value / px, s / 2, h - s / 2))
        cx = int(np.clip(w / 2 + east.value / px, s / 2, w - s / 2))
        show = keys if mode.value == "all" else list(dict.fromkeys([left.value, right.value]))
        crops = {k: crop(k, cy, cx, s).astype("float32") for k in show}
        if colours.value == "shared":
            base = crop("stage1" if "stage1" in layers else ref, cy, cx, s).astype("float32")
            lo, hi = np.percentile(base.reshape(-1, 3), [2, 98], axis=0)
            crops = {k: np.clip((a - lo) / np.maximum(hi - lo, 1), 0, 1) for k, a in crops.items()}
        else:
            crops = {k: autostretch(a) for k, a in crops.items()}
        wide = 4.2 if mode.value == "all" else 7.2
        fig, axes = plt.subplots(1, len(show), figsize=(wide * len(show), wide + 0.4),
                                 squeeze=False)
        for ax, k in zip(axes[0], show):
            ax.imshow(crops[k], interpolation="nearest")
            ax.set_title(LEVEL_NAME[k]), ax.set_xticks([]), ax.set_yticks([])
        fig.suptitle(f"{s * px:,.0f} m across", y=0.02, fontsize=9, color="#555")
        plt.tight_layout()
        fig.savefig("my_comparison.png", dpi=150, bbox_inches="tight")
        image.value = _png(fig)
    for c in (size, mode, left, right, colours, east, north):
        c.observe(draw, names="value")
    draw()
    box = W.VBox([size, mode, pair, colours, east, north, image])
    box.size, box.mode, box.left, box.right, box.colours = size, mode, left, right, colours
    box.east, box.north, box.image = east, north, image
    return box


LEVEL_CHOICES = ["Sentinel-2", "SR stage 1", "stage 2 light", "stage 2 standard",
                 "stage 2 strong", "none: we need real images"]
_CHOICE_KEY = dict(zip(LEVEL_CHOICES, ["s2", "stage1", "t100", "t250", "t500", "hr"]))


def look_panel():
    """Part 4: load the images of your area (ready-made: at once; your own: from the SR
    service), compare them and choose the one you would use."""
    load = W.Button(description="Load the images", icon="image", button_style="primary",
                    layout=W.Layout(width="260px"))
    status = W.HTML()
    viewer = W.VBox([])
    save = W.Button(description="Download this view (my_comparison.png)", icon="download",
                    layout=W.Layout(width="360px"))
    note = W.HTML()

    def on_load(_=None):
        load.disabled = True
        try:
            a = S.get("area") or {}
            if a.get("slug") in PKG:
                layers = _pkg_layers(a["slug"])
                status.value = _note(f"{a['name']}: ready-made images.", "#1a7f37")
            elif S.get("jobs"):
                from sr_client.client import FINISHED
                jobs, t0 = S["jobs"], time.monotonic()
                while any(j.status not in FINISHED for j in jobs.values()):
                    status.value = _pre("\n".join(
                        f"{LEVEL_NAME[k]:<26}{j._progress_line(time.monotonic() - t0)}"
                        for k, j in jobs.items()))
                    time.sleep(5)
                    for j in jobs.values():
                        if j.status not in FINISHED:
                            j.refresh()
                good = {k: j for k, j in jobs.items() if j.status in ("done", "partial")}
                lines = [f"{LEVEL_NAME[k]}: {j.status}"
                         + "".join(f"; warning [{w['code']}]" for w in j.warnings)
                         + (f"; {j.info.get('error')}" if j.status == "failed" else "")
                         for k, j in jobs.items()]
                status.value = _pre("\n".join(lines))
                if not good:
                    status.value += _note("No image was made. In part 2, check that Sentinel-2 "
                                          "images exist for your date, then send again.",
                                          "#b00020")
                    return
                layers = _job_layers(good)
                info = S.setdefault("scene_info", {})
                info["warnings"] = sorted({w["code"] for j in good.values() for w in j.warnings})
            else:
                status.value = _note("Nothing to load yet. In part 2, choose a ready-made area, "
                                     "or connect to the SR service and press Send.", "#b00020")
                return
            S["layers"] = layers
            viewer.children = (_compare_viewer(layers), save, note)
        except Exception as exc:
            status.value = _error(exc)
        finally:
            load.disabled = False
    load.on_click(on_load)

    def on_save(_):
        try:
            from google.colab import files
            files.download("my_comparison.png")
            note.value = _note("Downloading ...", "#1a7f37")
        except Exception:  # not in Colab
            note.value = _note("Saved as my_comparison.png next to this notebook.", "#1a7f37")
    save.on_click(on_save)
    form = ask(("SEE_S2", "Can you see what you need on Sentinel-2?", ["yes", "partly", "no"]),
               ("LEVEL", "Which image would you use?", LEVEL_CHOICES),
               ("WHY", "What does it show that you need?", "text",
                "the edges of single roofs; Sentinel-2 shows only a grey patch"),
               ("INVENTED", "Does anything look invented or wrong? Where?", "text",
                "strong draws streets in the settlement that stage 1 does not show"),
               show=False)
    ui = W.VBox([load, status, viewer,
                 W.HTML("<br><b>Your choice</b> (part 5 opens after you choose an image)"),
                 form])
    ui.load, ui.status, ui.viewer, ui.fields = load, status, viewer, form.fields
    UI["look"] = ui
    display(ui)
    if (S.get("area") or {}).get("slug") in PKG:
        on_load()


# ---- part 5: cheat sheet and test plan ---------------------------------------------------------

# What we measured, by kind of task. best: the images that measured best (within noise).
CHEAT = {
    "settlements": dict(
        title="Finding informal settlements or dense housing",
        verdict="A fit for choosing where to look. Not for mapping or counting.",
        best=("t250", "t500"), best_text="SR stage 2, standard",
        lines=["Metro Manila, six models trained on real images. Map score (F1): Sentinel-2 "
               "8 %, stage 1 18 %, stage 2 standard 22 %, real images 40 %.",
               "By strength: light 15 %, standard 22 %, strong 24 %. Standard and strong do "
               "not differ reliably; light is no better than stage 1.",
               "Of 20 field visits, how many found a settlement: Sentinel-2 6, stage 1 9, "
               "stage 2 standard 9, real images 13. With Sentinel-2 the result varied a lot "
               "between models (1 to 11); with SR much less."],
        watch="False alarms on dense formal housing, markets and warehouses. Real images are "
              "still clearly better.",
        notebook="ifs"),
    "buildings": dict(
        title="Mapping or counting buildings",
        verdict="SR helps, but real images are much better. The best image depends on your "
                "model.",
        best=("stage1", "t100", "t250"),
        best_text="stage 1 for outlines; stage 2 standard with a model trained on sharp images",
        lines=["Building outlines (SpaceNet 7, a model trained on 4.7 m images). F1: "
               "Sentinel-2 0.21, stage 1 0.27, stage 2 standard 0.25, real images 0.62. The "
               "stronger the stage 2, the lower the score.",
               "Finding buildings in disaster areas (xBD, a model trained on 0.5 m images). "
               "F1: Sentinel-2 0.31, stage 1 0.48, stage 2 light 0.53, standard 0.54, strong "
               "0.53, real images 0.79.",
               "Houses on farmland near Hanoi. Of 15 site checks, how many found one: "
               "Sentinel-2 1, stage 1 5, stage 2 5, real images 8."],
        watch="In the outline test, SR found only about one fifth of the building area. Do "
              "not count buildings with SR. Stage 2 can draw roofs that look real.",
        notebook="lc"),
    "damage": dict(
        title="Damage to buildings after a disaster",
        verdict="Not a fit for judging damage.",
        best=("hr",), best_text="none of the SR images: real images",
        lines=["xBD, five disasters. F1 for damaged buildings: Sentinel-2 0.21, stage 2 "
               "standard 0.21, real images 0.36. SR adds nothing.",
               "SR does help to find where the buildings are (see \"Mapping or counting "
               "buildings\")."],
        watch="Damage to one roof is smaller than an SR pixel. An image that looks convincing "
              "is not evidence.",
        notebook=None),
    "landcover": dict(
        title="Land cover (built-up, trees, crops, bare soil, water)",
        verdict="A fit for small or mixed features. Large uniform areas do not need SR.",
        best=("t100", "t250"), best_text="SR stage 2, light or standard (light is cheaper)",
        lines=["Near Hanoi, seven classes. Map score (mean IoU): Sentinel-2 0.32, stage 1 "
               "0.38, stage 2 standard 0.47, real images 0.57.",
               "By strength (test tiles only): light 0.54, standard 0.53, strong 0.52. No "
               "reliable difference.",
               "The map score does not settle the decision. Bare soil, hits in 20 "
               "inspections: Sentinel-2 12, stage 1 13, stage 2 16, real images 17. Trees, "
               "hits in 20 surveys: Sentinel-2 18, real images 19. For trees, free images "
               "are enough."],
        watch="Bright factory roofs and river sandbanks are mistaken for bare soil.",
        notebook="lc"),
    "roads": dict(
        title="Roads and tracks",
        verdict="A fit for finding where roads are. Check narrow roads on a real image.",
        best=("t250",), best_text="SR stage 2, standard",
        lines=["Near Hanoi: choosing the 40 map cells with the most road. Correct choices: "
               "Sentinel-2 19, stage 1 24, stage 2 standard 30, real images 33.",
               "Map score for roads (IoU): Sentinel-2 0.20, stage 1 0.30, stage 2 standard "
               "0.34, real images 0.50. Good enough to choose cells, not to draw the roads."],
        watch="No satellite image shows roads under trees. Stage 2 can join or break a road.",
        notebook="lc"),
    "fields": dict(
        title="Field boundaries, small farms, parcels",
        verdict="A fit, with stage 1. Stage 2 adds detail that lowers accuracy.",
        best=("stage1",), best_text="SR stage 1",
        lines=["Viet Nam and Cambodia, one model trained on each kind of image. Field F1: "
               "Sentinel-2 0.42, stage 1 0.46, light 0.45, standard 0.44, strong 0.44.",
               "Finding small farms, hits in 30 visits: Sentinel-2 13, stage 1 24, stage 2 "
               "standard 22. Counting parcels per square kilometre, hits in 20: Sentinel-2 "
               "16, stage 1 19. Here Sentinel-2 is nearly as good."],
        watch="With Sentinel-2, one hazy area got no visits at all. A model needs training "
              "data from your own country.",
        notebook="ai4"),
    "flood": dict(
        title="Water: floods, ponds, shorelines",
        verdict="Not a fit. Free Sentinel-2 does as well.",
        best=("s2",), best_text="Sentinel-2",
        lines=["Flood water (FloodPlanet). Map score (mean IoU): Sentinel-2 0.62; every SR "
               "image 0.61 to 0.62. SR adds nothing.",
               "SR removes detail in shallow water. The service warns you when an area has "
               "water."],
        watch="For floods, the date matters more than the detail. You need a clear image on "
              "the right day, and clouds often prevent that.",
        notebook=None),
    "change": dict(
        title="Change between two dates (new buildings, new clearing)",
        verdict="Not measured. Test first.",
        best=("stage1", "s2"), best_text="stage 1 (our judgement, not measured)",
        lines=["We have not measured change detection.",
               "Stage 2 adds new detail on every date. Two stage 2 images can differ where "
               "nothing changed on the ground. Stage 1 invents nothing."],
        watch="Compare like with like: stage 1 with stage 1. Confirm any change on a real "
              "image or on the ground.",
        notebook=None),
    "small": dict(
        title="Small objects: cars, boats, single trees, roof material",
        verdict="Not a fit. These are smaller than an SR pixel (2.5 m).",
        best=("hr",), best_text="real high-resolution images",
        lines=["SR cannot show what Sentinel-2 did not record. At this size, stage 2 invents.",
               "SR can still tell you where to buy real images."],
        watch="An image that looks convincing is not evidence.",
        notebook=None),
    "other": dict(
        title="Something else",
        verdict="Not measured. Use the rules of thumb below and plan a test.",
        best=(), best_text="unknown: test it",
        lines=["Also read the measured task closest to yours."],
        watch="",
        notebook=None),
}
RULES = [
    "<b>Size.</b> 10 m and more: try free Sentinel-2 first. 2.5 to 10 m: SR may help, test it. "
    "Under 2.5 m: real images.",
    "<b>Sharper is not more accurate.</b> Strong stage 2 looks best, but it never clearly "
    "measured best.",
    "<b>Edges or surfaces?</b> Tasks that need exact edges (fields, building outlines) did "
    "best with stage 1. Tasks that need to tell surfaces apart (settlements, land cover) did "
    "best with stage 2.",
    "<b>Use SR to decide where to look.</b> Confirm on a real image or on the ground before "
    "anyone acts.",
    "<b>The model matters as much as the image.</b> The same image gave different results "
    "with different models.",
]


def _agreement(choice, row):
    key = _CHOICE_KEY.get(choice)
    if not key or not row["best"]:
        return ""
    if key in row["best"]:
        return (f"<b>You chose {choice}. The measurements agree.</b> How would you show that "
                "this also holds in your country?")
    head = f"<b>You chose {choice}. Measured best: {row['best_text']}.</b> "
    if key == "hr":
        return head + "Which test would show whether SR is good enough for you?"
    if row["best"] == ("hr",):
        return head + "What makes you trust the SR image?"
    order = ["s2", "stage1", "t100", "t250", "t500"]
    best = [order.index(b) for b in row["best"]]
    if order.index(key) > max(best):
        return head + ("Your image is sharper than the one that measured best. Is the extra "
                       "detail real, or does it only look better? Which test would settle it?")
    if order.index(key) < min(best):
        return head + ("Your image is less sharp than the one that measured best. What did "
                       "you not trust in the sharper ones?")
    return head + "Which test would settle it?"


BASELINES = ["Sentinel-2 alone (does SR add anything?)",
             "real images for a sample of places (how close is SR?)",
             "how we decide today (is SR better?)"]
VERDICTS = ["pilot it", "test it first", "not a fit"]


def cheat_panel():
    """Part 5: opens once the team has chosen an image in part 4. The cheat sheet for the
    kind of task, how it compares with the team's choice, and the team's test plan."""
    holder = W.VBox([W.HTML(_note("&#128274; Opens once you have chosen an image in part 4.",
                                  "#8a6d00"))])
    state = {}

    def build():
        task = W.Dropdown(options=[(r["title"], k) for k, r in CHEAT.items()], value="other",
                          description="Our task is closest to", layout=W.Layout(width="760px"),
                          style={"description_width": "170px"})
        starter = next((s for s in STARTERS if s["title"] == ANSWERS.get("starter")), None)
        if starter:
            task.value = starter["task"]
        sheet = W.HTML()

        def draw(_=None):
            r = CHEAT[task.value]
            ANSWERS["task_type"] = r["title"]
            S["cheat"] = r
            parts = [f"<div style='font-size:15px'><b>{r['verdict']}</b></div>",
                     f"<p style='margin:6px 0'><b>Measured best:</b> {r['best_text']}</p>",
                     "<ul style='margin:4px 0'>" + "".join(f"<li>{x}</li>" for x in r["lines"])
                     + "</ul>"]
            if r["watch"]:
                parts.append(f"<p style='margin:6px 0'><b>Watch out:</b> {r['watch']}</p>")
            parts.append(f"<p style='margin:6px 0'><b>Your size:</b> "
                         f"{_size_rule(float(ANSWERS.get('size_m', 5)))}</p>")
            agree = _agreement(ANSWERS.get("LEVEL"), r)
            if agree:
                parts.append(f"<p style='margin:8px 0; padding:6px 10px; background:#fff7e0'>"
                             f"{agree}</p>")
            if r["notebook"]:
                t, link = MEASURED[r["notebook"]]
                parts.append("<p style='margin:6px 0'><b>Try your own numbers:</b> the "
                             f"notebook <a href='{link}' target='_blank'>{t}</a> has measured "
                             "results for this task. Set your own budget and your own rule "
                             "for a hit.</p>")
            rules = "<ul style='margin:4px 0'>" + "".join(f"<li>{x}</li>" for x in RULES) + "</ul>"
            sheet.value = _card("".join(parts)) + _card("<b>Rules of thumb</b>" + rules, "#777")
        task.observe(draw, names="value")
        plan = ask(("TEST_DATA", "What would you check the map against?", "text",
                    "200 blocks our field teams validated in 2025"),
                   ("TEST_BASELINE", "What would you compare it with? (tick all that apply)",
                    "checks", BASELINES),
                   ("TEST_PASS", "Pass mark (your minimum from part 1)", "text",
                    "at least 10 hits in 20 visits, in two different cities"),
                   ("NEEDS", "What do you need to start? (data, people, partners, money)",
                    "text", "labels from the housing office; two weeks of an analyst"),
                   show=False)
        state["draw"] = draw
        ui = W.VBox([task, sheet, W.HTML("<br><b>Your test plan: how would you test this at "
                                         "home?</b>"), plan])
        ui.task, ui.sheet, ui.fields = task, sheet, plan.fields
        UI["cheat"] = ui
        draw()
        return ui

    def refresh():
        if not ANSWERS.get("LEVEL"):
            return
        if "draw" not in state:
            try:
                holder.children = (build(),)
            except Exception as exc:
                holder.children = (W.HTML(_error(exc)),)
        else:
            state["draw"]()
    ANSWER_REFRESH["cheat"] = refresh
    UI["cheat_holder"] = holder
    display(holder)
    refresh()


# ---- part 6: the slide card --------------------------------------------------------------------

def scenario_card_text():
    lines = ["=" * 78]
    answers = canvas_dict()
    for k, _, _, label in CANVAS:
        lines.append(f"{label:<16}{answers[k]}")
    lines.append(f"{'SIZE':<16}{ANSWERS.get('size_m', 0):g} m")
    lines += ["-" * 78, f"{'AREA':<16}{ANSWERS.get('area', '(none chosen)')}"]
    info = S.get("scene_info") or {}
    if info.get("scenes"):
        days = sorted({s["date"] for s in info["scenes"]})
        lines.append(f"{'SENTINEL-2':<16}{len(info['scenes'])} images on {len(days)} days, "
                     f"{days[0]} to {days[-1]}")
    if info.get("warnings"):
        lines.append(f"{'WARNINGS':<16}" + ", ".join(
            w if isinstance(w, str) else w.get("code", "?") for w in info["warnings"]))
    if S.get("money"):
        lines.append(f"{'COST':<16}{S['money'][0]}")
        lines += [f"  - {x}" for x in S["money"][1:]]
    lines += ["-" * 78,
              f"{'visible on Sentinel-2:':<28}{_said('SEE_S2')}",
              f"{'we would use:':<28}{_said('LEVEL')}",
              f"{'because it shows:':<28}{_said('WHY')}",
              f"{'invented or wrong:':<28}{_said('INVENTED')}"]
    r = S.get("cheat")
    if r:
        lines += [f"{'closest measured task:':<28}{r['title']}",
                  f"{'cheat sheet:':<28}{r['verdict']} Measured best: {r['best_text']}."]
        key = _CHOICE_KEY.get(ANSWERS.get("LEVEL"))
        if key and r["best"]:
            lines.append(f"{'cheat sheet agrees with us:':<28}"
                         + ("yes" if key in r["best"] else "no"))
    lines += ["-" * 78, "TEST PLAN",
              f"{'check against:':<28}{_said('TEST_DATA')}",
              f"{'compare with:':<28}" + ("; ".join(ANSWERS.get("TEST_BASELINE") or [])
                                         or "(none ticked)"),
              f"{'pass mark:':<28}{_said('TEST_PASS')}",
              f"{'we need:':<28}{_said('NEEDS')}",
              "-" * 78, f"{'recommendation:':<28}{_said('VERDICT')}"]
    guards = ANSWERS.get("SAFEGUARDS") or []
    lines.append(f"{'safeguards:':<28}" + ("(none ticked)" if not guards else ""))
    lines += [f"  - {g}" for g in guards]
    lines.append("=" * 78)
    return "\n".join(lines)


def scenario_card():
    """Part 6: the recommendation, then a card with everything the slide needs. It follows
    every answer above."""
    form = ask(("VERDICT", "Is super-resolution a fit for your scenario?", VERDICTS),
               ("SAFEGUARDS", "Your safeguards (tick all that apply)", "checks",
                SAFEGUARDS), show=False)
    card = W.HTML()

    def update(_=None):
        card.value = _pre(scenario_card_text())
    ANSWER_REFRESH["scenario_card"] = update
    update()
    ui = W.VBox([form, W.HTML("<b>Your card.</b> Copy it to your team slide and add the image "
                              "you downloaded in part 4."), card])
    ui.card, ui.fields = card, form.fields
    UI["scenario_card"] = ui
    display(ui)
