# ---- the worksheet's controls: dropdowns, buttons and sliders that act at once ---------------
S = {}          # this session: the place, the jobs and the images that are already loaded
OWN_PLACE = "My own place"
_DONE = ("done", "partial", "failed", "cancelled")


def _ready(*keys):
    """True if the earlier steps were done; otherwise says which step is missing."""
    if "job" not in S:
        display(W.HTML(_note("<b>Pick a place in step 1 first</b>: choose it and press the "
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
    day = W.Text(value="2026-04-15", description="Date (YYYY-MM-DD)", style=_LABEL)
    own = W.VBox([W.HTML(_note("A point (in Google Maps: right-click, then click the "
                               "coordinates to copy them) and a date in the dry season.")),
                  lat, lon, day])
    own.layout.display = "none"
    about = W.HTML()
    send = W.Button(description="Send to the service", button_style="primary", icon="rocket",
                    layout=W.Layout(width="220px"))
    status = W.HTML()

    def describe(_=None):
        own.layout.display = "" if place.value == OWN_PLACE else "none"
        about.value = _note("" if place.value == OWN_PLACE else PLACES[place.value]["note"],
                            "#555")
    place.observe(describe, names="value")
    describe()

    def on_send(_):
        send.disabled = True
        try:
            if place.value == OWN_PLACE:
                la, lo, d = float(lat.value), float(lon.value), day.value.strip()
                date.fromisoformat(d)
            else:
                p = PLACES[place.value]
                la, lo, d = p["lat"], p["lon"], p["date"]
            status.value = _note("Asking the service which Sentinel-2 images exist ...")
            area = area_around(la, lo, km=2)
            est = sr.estimate(area, d)
            lines = [f"{place.value}, {d}",
                     f"{len(est['scenes'])} Sentinel-2 images found between "
                     f"{est['search_window'][0]} and {est['search_window'][1]}",
                     f"{est['tiles']} tiles of 320 m; cost if nothing was computed before: "
                     f"${est['estimated_usd']:.2f}"]
            lines += [f"warning: {w['message']}" for w in est["warnings_likely"]]
            if est["problems"]:
                lines += [f"cannot send this job: {p}" for p in est["problems"]]
                status.value = _pre("\n".join(lines)) + _note(
                    "Choose another place or date and press the button again.", "#b00020")
                return
            job = sr.submit(area, d)
            S.clear()
            S.update(sr=sr, place=place.value, lat=la, lon=lo, date=d, area=area, est=est,
                     job=job)
            ANSWERS["PLACE"] = f"{place.value} ({d})"
            status.value = _pre("\n".join(lines)) + _note(
                f"<b>Job sent</b> ({job.id[:8]}, {job.status}). Go on with step 2.", "#1a7f37")
        except ValueError:
            status.value = _note("The date must look like 2026-04-15.", "#b00020")
        except SRError as exc:
            status.value = _note(f"The service said: {_html.escape(exc.message)}", "#b00020")
        finally:
            send.disabled = False
    send.on_click(on_send)

    ui = W.VBox([place, about, own, send, status])
    ui.place, ui.send, ui.status, ui.own_fields = place, send, status, (lat, lon, day)
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
            trial = S["sr"].submit(S["area"], S["date"], **EXPERIMENTS[name])
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
