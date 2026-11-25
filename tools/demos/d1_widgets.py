# ---- the controls of Demo 1: dropdowns, buttons and sliders that act at once ---------------
S = {}          # this session: the place, the jobs and the images that are already loaded
OWN_PLACE = "My own place"
_DONE = ("done", "partial", "failed", "cancelled")


def _ready(*keys):
    """True if the earlier steps were done; otherwise says which step is missing."""
    if "job" not in S:
        display(W.HTML(_note("<b>Pick a place in part 1 first</b>: choose it and press the "
                             "button, then run this cell again.", "#b00020")))
        return False
    return True


def _wait(job, status=None, until_stage=None):
    """Poll a job until it is finished (or until a stage is published), showing progress."""
    t0 = time.monotonic()
    while True:
        job.refresh()
        steps = " · ".join(f"{p['step']} {p['state']}" for p in (job.info.get("progress") or [])
                           if p["state"] != "waiting")
        line = f"{job.status}, {(time.monotonic() - t0) / 60:.1f} min   {steps}"
        if status is not None:
            status.value = _note(line)
        if job.status in _DONE:
            return job
        if until_stage:
            try:
                if until_stage in job.results()["stages_done"]:
                    return job
            except SRError as exc:
                if exc.status != 409:   # 409 = no result yet
                    raise
        time.sleep(5)


def _need(name):
    """Load an image of the main job once and keep it."""
    files = {"lr": "lr_reference.tif", "s1": "stage1_sr.tif", "s2": "stage2_sr.tif"}
    if name not in S:
        S[name] = load(S["job"], files[name])
    return S[name]


# ---- step 1: pick a place -----------------------------------------------------------------

def pick_place(sr):
    """Choose a place and send it to the service with one button."""
    place = W.Dropdown(options=[*PLACES, OWN_PLACE], value="Cebu City and Mandaue",
                       description="Place", layout=_WIDE, style=_LABEL)
    lat = W.FloatText(value=14.6760, description="Latitude", style=_LABEL)
    lon = W.FloatText(value=121.0437, description="Longitude", style=_LABEL)
    own = W.VBox([W.HTML(_note("A point (in Google Maps: right-click, then click the "
                               "coordinates to copy them). Set a date in the dry season "
                               "under Options.")),
                  lat, lon])
    own.layout.display = "none"
    # the options of the request: the service's defaults until someone changes them
    wide = {"description_width": "330px"}
    slider = W.Layout(width="640px")
    day = W.Text(value=PLACES["Cebu City and Mandaue"]["date"], style=wide,
                 description="Target date (YYYY-MM-DD)", layout=W.Layout(width="480px"))
    max_cloud = W.IntSlider(value=40, min=5, max=100, step=5, style=wide, layout=slider,
                            description="Skip images with more cloud than (%, whole image)")
    window = W.IntSlider(value=45, min=10, max=180, step=5, style=wide, layout=slider,
                         description="Search this many days before and after")
    min_clear = W.IntSlider(value=70, min=0, max=100, step=5, style=wide, layout=slider,
                            description="Per 320 m tile: use an image if this % is clear")
    reset = W.Button(description="Back to the defaults", icon="undo",
                     layout=W.Layout(width="220px"))
    options = W.Accordion(children=[W.VBox([
        day, max_cloud, window, min_clear, reset,
        W.HTML(_note("<i>Whole image</i>: the cloud share of the full Sentinel-2 image, 110 km "
                     "across, from the catalogue. It says little about your 2 km. <i>Per "
                     "tile</i>: the share of each 320 m tile that ESA's classification calls "
                     "clear in that image.", "#555"))])])
    options.set_title(0, "Options: date, clouds, search window")
    options.selected_index = None        # closed until someone opens it

    def on_reset(_):
        max_cloud.value, window.value, min_clear.value = 40, 45, 70
        if place.value != OWN_PLACE:
            day.value = PLACES[place.value]["date"]
    reset.on_click(on_reset)

    def chosen():
        """Only what differs from the service's defaults, as options of sr.submit."""
        opts = {}
        if max_cloud.value != 40:
            opts["max_cloud"] = max_cloud.value
        if window.value != 45:
            opts["time_window"] = {"days_before": window.value, "days_after": window.value}
        if min_clear.value != 70:
            opts["min_clear"] = min_clear.value / 100
        return opts
    about = W.HTML()
    send = W.Button(description="Send to the service", button_style="primary", icon="rocket",
                    layout=W.Layout(width="220px"))
    status = W.HTML()
    waiting = W.HTML()
    picture = W.Image(format="png", layout=W.Layout(display="none"))

    def describe(_=None):
        own.layout.display = "" if place.value == OWN_PLACE else "none"
        about.value = _note("" if place.value == OWN_PLACE else PLACES[place.value]["note"],
                            "#555")
        if place.value != OWN_PLACE:
            day.value = PLACES[place.value]["date"]     # the date we tried for this place
    place.observe(describe, names="value")
    describe()

    def on_send(_):
        send.disabled = True
        try:
            if place.value == OWN_PLACE:
                la, lo = float(lat.value), float(lon.value)
            else:
                la, lo = PLACES[place.value]["lat"], PLACES[place.value]["lon"]
            d, opts = day.value.strip(), chosen()
            date.fromisoformat(d)
            status.value = _note("Asking the service which Sentinel-2 images exist ...")
            area = area_around(la, lo, km=2)
            est = sr.estimate(area, d, **opts)
            changed = ", ".join(
                ([f"images up to {max_cloud.value} % cloud"] if "max_cloud" in opts else []) +
                ([f"{window.value} days before and after"] if "time_window" in opts else []) +
                ([f"tiles at least {min_clear.value} % clear"] if "min_clear" in opts else []))
            lines = [f"{place.value}, {d}" + (f"   (options: {changed})" if changed else ""),
                     f"{len(est['scenes'])} Sentinel-2 images found between "
                     f"{est['search_window'][0]} and {est['search_window'][1]}",
                     f"{est['tiles']} tiles of 320 m; cost if nothing was computed before: "
                     f"${est['estimated_usd']:.2f}"]
            lines += [f"warning: {w['message']}" for w in est["warnings_likely"]]
            if est["problems"]:
                lines += [f"cannot send this job: {p}" for p in est["problems"]]
                status.value = _pre("\n".join(lines)) + _note(
                    "Change the place, the date or the options and press the button again.",
                    "#b00020")
                return
            job = sr.submit(area, d, **opts)
            S.clear()
            S.update(sr=sr, place=place.value, lat=la, lon=lo, date=d, area=area, est=est,
                     job=job, options=opts)
            ANSWERS["PLACE"] = f"{place.value} ({d})"
            sent = _pre("\n".join(lines)) + _note(
                f"<b>Job sent</b> ({job.id[:8]}).", "#1a7f37")
            status.value = sent
            picture.layout.display = "none"
            try:    # the main Sentinel-2 image: known as soon as the service has chosen it
                _wait(job, waiting, until_stage="1")
                waiting.value = _note("Reading the main Sentinel-2 image from the archive ...")
                tile = middle_tile(manifest(job))
                _, img, _ = scene_images(tile["scene_ids"][:1], la, lo, km=2)[0]
                fig, ax = plt.subplots(figsize=(5.6, 5.9))
                ax.imshow(img, interpolation="nearest")
                ax.set_title(f"The main Sentinel-2 image of your area ({tile['dates'][0]})\n"
                             "10 m pixels: this is what the satellite gives you", fontsize=10)
                ax.axis("off")
                fig.tight_layout()
                picture.value = _png(fig)
                picture.layout.display = ""
                waiting.value = ""
            except Exception as exc:    # the picture is an extra: the job itself is sent
                waiting.value = _note("(The Sentinel-2 image could not be shown: "
                                      f"{_html.escape(str(exc))})", "#555")
            status.value = sent + _note("Go on with part 2.", "#1a7f37")
        except ValueError:
            status.value = _note("The date must look like 2026-04-15.", "#b00020")
        except SRError as exc:
            status.value = _note(f"The service said: {_html.escape(exc.message)}", "#b00020")
        finally:
            send.disabled = False
    send.on_click(on_send)

    ui = W.VBox([place, about, own, options, send, status, waiting, picture])
    ui.place, ui.send, ui.status, ui.own_fields = place, send, status, (lat, lon, day)
    ui.options = dict(day=day, max_cloud=max_cloud, window=window, min_clear=min_clear,
                      reset=reset)
    ui.picture = picture
    UI["place"] = ui
    display(ui)


# ---- a viewer: move and zoom, the picture follows -------------------------------------------

class Viewer:
    """Images side by side with sliders to move the view and buttons to zoom. ``layers`` is
    a list of (title, image) or (title, image, "difference")."""

    def __init__(self, layers, size_m=500, panel=5.2, footer=None):
        self.layers, self.panel, self.footer = layers, panel, footer
        self.east = W.IntSlider(value=0, min=-750, max=750, step=50, continuous_update=False,
                                description="← west | east →", layout=_WIDE, style=_LABEL)
        self.north = W.IntSlider(value=0, min=-750, max=750, step=50, continuous_update=False,
                                 description="← south | north →", layout=_WIDE, style=_LABEL)
        self.size = W.ToggleButtons(options=[("250 m", 250), ("500 m", 500), ("1 km", 1000),
                                             ("whole area", 2000)], value=size_m,
                                    description="Zoom", style={"button_width": "90px",
                                                               "description_width": "150px"})
        self.image = W.Image(format="png")
        for w in (self.east, self.north, self.size):
            w.observe(self.draw, names="value")
        self.box = W.VBox([self.size, self.east, self.north, self.image])
        self.draw()

    def draw(self, _=None):
        size, east, north = self.size.value, self.east.value, self.north.value
        lat, lon = S["lat"], S["lon"]
        n = len(self.layers)
        fig, axes = plt.subplots(1, n + 1, figsize=(self.panel * n + 2.6, self.panel + 0.5),
                                 gridspec_kw={"width_ratios": [2.6] + [self.panel] * n})
        # where am I: the whole area with a frame around the current view
        whole = self.layers[-1 if len(self.layers[-1]) == 2 else 0][1]
        thumb = whole.isel(x=slice(None, None, 4), y=slice(None, None, 4))
        x0, y0 = float(whole.x.mean()), float(whole.y.mean())
        ext = [float(whole.x.min()), float(whole.x.max()), float(whole.y.min()),
               float(whole.y.max())]
        axes[0].imshow(rgb(thumb), extent=ext, interpolation="nearest")
        axes[0].add_patch(plt.Rectangle((x0 + east - size / 2, y0 + north - size / 2), size,
                                        size, fill=False, ec="#ffd400", lw=2))
        axes[0].set_title("where you are", fontsize=9)
        for ax, layer in zip(axes[1:], self.layers):
            cut = view(layer[1], lat, lon, size, east, north)
            if len(layer) == 3:     # a difference map
                ax.imshow(np.clip(cut.values / 0.05, 0, 1), cmap="magma", vmin=0, vmax=1,
                          interpolation="nearest")
            else:
                ax.imshow(rgb(cut), interpolation="nearest")
            ax.set_title(layer[0])
        for ax in axes:
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle(f"{S['place']}: {size} m across" + (f"   {self.footer}" if self.footer
                                                         else ""), y=1.0, fontsize=10)
        fig.tight_layout()
        self.image.value = _png(fig)


# ---- steps 2 to 4 -------------------------------------------------------------------------

def step2_inputs():
    """The 8 Sentinel-2 images behind the middle of the area, and question 1."""
    if not _ready():
        return
    wait_for_stage(S["job"], "1")
    S["tile"] = show_inputs(S["job"], S["lat"], S["lon"], S["date"])
    UI["q1"] = ask(("Q1_CLEAR_IMAGES", "Q1. How many of the 8 images are really clear over your "
                "place?", [str(i) for i in range(9)]),
               ("Q1_MISSED_CLOUD", "Is there cloud, haze or shadow that the red outline "
                "missed?", ["no", "yes", "not sure"]))


def step3_stage1():
    """Sentinel-2 next to Stage 1, and question 2."""
    if not _ready():
        return
    wait_for_stage(S["job"], "1")
    viewer = Viewer([("Sentinel-2, 10 m", _need("lr")), ("Stage 1, 2.5 m", _need("s1"))],
                    panel=6.2)
    display(viewer.box)
    UI["view3"] = viewer
    UI["q2"] = ask(("Q2_NEW_IN_STAGE_1", "Q2. Name one thing you can make out in Stage 1 that you could "
         "not make out in Sentinel-2.", "text"))


def step4_stage2():
    """Sentinel-2, Stage 1 and Stage 2, and question 3."""
    if not _ready():
        return
    status = W.HTML()
    display(status)
    job = _wait(S["job"], status)
    if job.status not in ("done", "partial"):
        status.value = _note(f"The job {job.status}: {job.info.get('error')}", "#b00020")
        return
    status.value = _pre("\n".join(
        [f"warning ({w['code']}): {WARNING_MEANING.get(w['code'], w.get('message', ''))}"
         for w in job.warnings] or ["warnings: none"]))
    viewer = Viewer([("Sentinel-2, 10 m", _need("lr")), ("Stage 1", _need("s1")),
                     ("Stage 2", _need("s2"))])
    display(viewer.box)
    UI["view4"] = viewer
    UI["q3"] = ask(("Q3_RIGHT", "Q3. One detail Stage 2 got right:", "text"),
        ("Q3_WRONG", "One detail Stage 2 got wrong or invented:", "text"))


# ---- step 5: one experiment -----------------------------------------------------------------

def step5_experiment():
    """Choose one change to the dials, guess, press the button, compare."""
    if not _ready():
        return
    choice = W.Dropdown(options=list(EXPERIMENTS), value="much more noise (tau 999)",
                        description="My experiment", layout=_WIDE, style=_LABEL)
    guess = W.ToggleButtons(options=["sharper, and I would still trust it",
                                     "sharper, but I would not trust the detail",
                                     "less sharp", "hardly any difference"], value=None,
                            style={"button_width": "auto"})
    guess.observe(lambda c: ANSWERS.__setitem__("MY_GUESS", c["new"]), names="value")
    run = W.Button(description="Run my experiment", button_style="primary", icon="flask",
                   layout=W.Layout(width="220px"))
    status = W.HTML()
    result = W.VBox([])

    def on_run(_):
        run.disabled = True
        try:
            name = choice.value
            status.value = _note("Sending the job ...")
            trial = S["sr"].submit(S["area"], S["date"], **S.get("options", {}),
                                   **EXPERIMENTS[name])
            _wait(trial, status)
            if trial.status not in ("done", "partial"):
                status.value = _note(f"The job {trial.status}: {trial.info.get('error')}",
                                     "#b00020")
                return
            status.value = _note("Loading the image ...")
            s1, s2, lr = _need("s1"), _need("s2"), _need("lr")
            s2_trial = load(trial, "stage2_sr.tif")
            diff = seed_difference(s2, s2_trial)
            S.update(trial=trial, s2_trial=s2_trial, experiment=name)
            ANSWERS["EXPERIMENT"] = name
            rows = [("Stage 1", s1), ("default Stage 2", s2), (name, s2_trial)]
            table = (f"{'':<34}{'agreement with':>16}{'fine':>10}\n"
                     f"{'':<34}{'Sentinel-2':>16}{'detail':>10}\n" +
                     "\n".join(f"{label:<34}{agreement(da, lr):>16.2f}{detail(da):>10.4f}"
                               for label, da in rows) +
                     f"\n\npixels that differ clearly between the two versions: "
                     f"{float((diff > 0.02).mean()):.0%}")
            viewer = Viewer([("default (tau 250, 250 steps, seed 0)", s2), (name, s2_trial),
                             ("where they differ (bright = more)", diff, "difference")],
                            size_m=250)
            UI["view5"] = viewer
            result.children = (viewer.box, W.HTML(_pre(table)))
            status.value = _note("Done. Move the view to compare.", "#1a7f37")
        except SRError as exc:
            status.value = _note(f"The service said: {_html.escape(exc.message)}", "#b00020")
        finally:
            run.disabled = False
    run.on_click(on_run)

    ui = W.VBox([choice, W.HTML("<b>Before you run it: what do you expect?</b>"), guess, run,
                 status, result])
    ui.choice, ui.guess, ui.run, ui.status, ui.result = choice, guess, run, status, result
    UI["experiment"] = ui
    display(ui)


def step5_question():
    options = ["Sentinel-2", "Stage 1", "default Stage 2", "my experiment"]
    UI["q4"] = ask(("Q4_REPORT_PICTURE", "Q4. Which version would you use for a picture in a "
                "report?", options),
               ("Q4_COUNTING", "And which for counting buildings or measuring roads?", options))


# ---- step 6: the result card ----------------------------------------------------------------

def card_text():
    def get(key):
        v = ANSWERS.get(key)
        return "(not answered)" if v in ("", None) else v

    lines = ["=" * 66, f"PLACE       {get('PLACE')}"]
    if "s1" in S and "lr" in S:
        lines.append(f"AGREEMENT   with Sentinel-2 at 10 m: Stage 1 "
                     f"{agreement(S['s1'], S['lr']):.2f}" +
                     (f", Stage 2 {agreement(S['s2'], S['lr']):.2f}" if "s2" in S else ""))
    if "job" in S:
        codes = [w["code"] for w in S["job"].warnings]
        lines.append(f"WARNINGS    {', '.join(dict.fromkeys(codes)) if codes else 'none'}")
    lines += ["-" * 66,
              f"Q1  clear images out of 8:        {get('Q1_CLEAR_IMAGES')}",
              f"    a cloud the mask missed:      {get('Q1_MISSED_CLOUD')}",
              f"Q2  new in Stage 1:               {get('Q2_NEW_IN_STAGE_1')}",
              f"Q3  Stage 2 got right:            {get('Q3_RIGHT')}",
              f"    Stage 2 got wrong:            {get('Q3_WRONG')}",
              f"Q4  my experiment:                {get('EXPERIMENT')}",
              f"    my guess was:                 {get('MY_GUESS')}",
              f"    for a picture in a report:    {get('Q4_REPORT_PICTURE')}",
              f"    for counting buildings:       {get('Q4_COUNTING')}",
              "=" * 66]
    return "\n".join(lines)


def result_card():
    """Your answers on one card; the button brings it up to date."""
    card = W.HTML(_pre(card_text()))
    again = W.Button(description="Update the card", icon="refresh")
    again.on_click(lambda _: setattr(card, "value", _pre(card_text())))
    ui = W.VBox([card, again])
    ui.card, ui.again = card, again
    UI["card"] = ui
    display(ui)


# ---- "under the hood" cells: the plain code behind each step ---------------------------------

def picked():
    """The place sent in part 1: (lat, lon, date, area, job)."""
    if "job" not in S:
        raise NotYet("Pick a place in part 1 first (choose it and press the button), then run "
                     "this cell again.")
    return S["lat"], S["lon"], S["date"], S["area"], S["job"]


def my_options():
    """What was changed under "Options" in part 1, as options of sr.submit ({} = defaults)."""
    return dict(S.get("options", {}))


def my_experiment():
    """The experiment run in part 5: (its name, its job)."""
    if "trial" not in S:
        raise NotYet("Run an experiment in part 5 first (press 'Run my experiment'), then run "
                     "this cell again.")
    return S["experiment"], S["trial"]


NOTES = {
    "request": """
**What happened.** Two calls: `sr.estimate(area, date)` is free and only searches;
`sr.submit(area, date)` starts the job. The search looks **45 days before and after** the date
and keeps images with **less than 40 % cloud** over the whole Sentinel-2 tile (110 km across).
Both stages run by default; Stage 1 is published first.

| Option of `sr.submit` | Default | What it does |
|---|---|---|
| `stages` | `["1", "2"]` | `["1"]` is fast and cheap; add Stage 2 later with `job.upgrade()` |
| `time_window` | 45 days before and after | how far from the date the search may go |
| `max_cloud` | 40 | skip images with more cloud than this (%, whole Sentinel-2 image of 110 km) |
| `min_clear` | 0.7 | per 320 m tile: use an image only if at least this share of the tile is clear |
| `tau` | 250 | Dial 1: how much noise Stage 2 adds (10 to 999) |
| `nfe` | same as `tau` | Dial 2: in how many steps the noise is removed |
| `seed` | 0 | the random noise; same inputs and same seed give the same image |
""",
    "search": """
**How to read the chart.** Each dot is one Sentinel-2 image that the search found. Its height
is how much of *this area* is under cloud or cloud shadow in that image (ESA's scene
classification). Blue dots were used; the larger the dot, the more of the area it was used
for. Grey rings were not used.

**Why are some cloudy images used?** The model works on squares of 320 m, and the 8 images are
chosen **for each square separately**: the clearest, closest in time. An image that is cloudy
over most of the area can still be clear over a few squares, and is used only there (a small
dot). The manifest records the choice for every square, so every pixel can be traced back to
the Sentinel-2 images behind it.
""",
    "tiles": """
**From tiles to one image.** The model always works on squares of **320 m** (32 Sentinel-2
pixels). A larger area is cut into such tiles; each goes through the model on its own, with
its own 8 images. The service then stitches the results:

* neighbouring tiles **overlap by 80 m** (yellow and blue on the left); in the overlap one
  result fades into the other, so there is no hard edge;
* the **colours of neighbouring tiles are matched**, because two tiles may have used
  different images;
* a tile with no clear image at all stays empty (a black square).

On the right: how many different images each tile had. Tiles with fewer different images hold
less real detail (some images are then used twice).
""",
    "result": """
**What comes with every result.** The images, and the information you need to judge them:

| File | What it holds |
|---|---|
| `stage1_sr.tif`, `stage2_sr.tif` | the 2.5 m images: red, green, blue, near-infrared; reflectance × 10,000 |
| `lr_reference.tif` | the Sentinel-2 input, 10 m (the average of the images the model saw) |
| `validity.tif` | 0 no data · 1 valid · 2 low diversity (fewer than 4 different clear images) |
| `manifest.json` | the images used for every tile, the settings, model versions, cost |

**Warnings** never stop a job, but read them: `water` (detail in shallow water and on reefs is
not reliable), `low_diversity`, `nodata` and `haze`. The files open in QGIS or ArcGIS; in
Colab they are in the file browser on the left, under `sr_results/`. Links last 7 days.
""",
    "dials": """
**What the experiment changed.** Only the options of `sr.submit`; the area, the date and the
8 input images are the same, and so is Stage 1.

**The two numbers.** *Agreement with Sentinel-2*: average each 4 × 4 block of the 2.5 m image
back to one 10 m pixel and correlate it with the Sentinel-2 input (1 = the same pattern of
light and dark). It cannot see anything smaller than 10 m, so detail the model draws below
that size is not checked by it. *Fine detail*: the average change in brightness from one pixel
to the next. The cost of Stage 2 grows with the number of steps (`nfe`).
""",
}
