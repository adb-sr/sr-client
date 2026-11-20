# ---- the notebook's controls: menus, buttons and sliders that act at once ---------------------
S = {}          # this session: the place that is loaded, the scores
REFRESH = []    # what to redraw when the place changes
SCORE_REFRESH = []   # what to redraw when the tolerance or the metric changes
SCORING = {"metres": TOLERANCE_M, "metric": "F1"}
BEST = ["Sentinel-2", "Stage 1", "Stage 2", "no real difference"]
_SWITCHES = {"metres": [], "metric": []}
_BUSY = [False]


def _place_needed():
    if "place" not in S:
        display(W.HTML(_note("<b>Run the cell of step 2 first</b>, then run this cell again.",
                             "#b00020")))
        return False
    return True


def _refresh_all():
    for redraw in REFRESH:
        redraw()


# ---- the scoring switches: every copy shows the same value, and every score follows ---------

def _on_switch(change, key):
    if _BUSY[0]:
        return
    _BUSY[0] = True
    try:
        SCORING[key] = change["new"]
        for w in _SWITCHES[key]:
            w.value = change["new"]          # the other copies follow
    finally:
        _BUSY[0] = False
    for redraw in SCORE_REFRESH:
        redraw()


def _switch(key):
    if key == "metres":
        w = W.ToggleButtons(options=[("pixel-exact", 0), ("within 2.5 m", 2.5),
                                     ("within 5 m", 5)], value=SCORING["metres"],
                            description="A pixel counts", style={"button_width": "105px",
                                                                 "description_width": "150px"},
                            tooltips=["the two maps must agree on the very pixel",
                                      "one pixel of shift is forgiven",
                                      "two pixels of shift are forgiven"])
    else:
        w = W.ToggleButtons(options=METRICS, value=SCORING["metric"], description="Score",
                            style={"button_width": "80px", "description_width": "150px"},
                            tooltips=["precision and recall combined",
                                      "intersection over union: lower than F1, same order",
                                      "of what the model marks, the share that is right",
                                      "of what the public map has, the share the model found"])
    w.observe(lambda change: _on_switch(change, key), names="value")
    _SWITCHES[key].append(w)
    return w


def _switches(metric=True):
    return W.VBox([_switch("metres")] + ([_switch("metric")] if metric else []))


# ---- a viewer: move and zoom, the picture follows -------------------------------------------

class Viewer:
    """A figure of the current place with sliders to move the view and buttons to zoom.
    ``render(place, size_m, east_m, north_m, *extra)`` returns the figure; ``extra`` are
    more controls (for example buildings or roads) whose values are passed on."""

    def __init__(self, render, size_m=1000, extra=()):
        self.render, self.extra = render, list(extra)
        self.size = W.ToggleButtons(options=[("250 m", 250), ("500 m", 500), ("1 km", 1000),
                                             ("whole area", 2000)], value=size_m,
                                    description="Zoom", style={"button_width": "90px",
                                                               "description_width": "150px"})
        self.east = W.IntSlider(value=0, min=-750, max=750, step=50, continuous_update=False,
                                description="← west | east →", layout=_WIDE, style=_LABEL)
        self.north = W.IntSlider(value=0, min=-750, max=750, step=50, continuous_update=False,
                                 description="← south | north →", layout=_WIDE, style=_LABEL)
        self.locator = W.Image(format="png", layout=W.Layout(width="190px"))
        self.image = W.Image(format="png")
        for w in (self.size, self.east, self.north, *self.extra):
            w.observe(self.draw, names="value")
        controls = W.VBox([*self.extra, self.size, self.east, self.north])
        self.box = W.VBox([W.HBox([controls, self.locator]), self.image])
        REFRESH.append(self.draw)
        self.draw()

    def draw(self, _=None):
        place = S["place"]
        args = (self.size.value, self.east.value, self.north.value)
        self.locator.value = _png(fig_locator(place, *args))
        self.image.value = _png(self.render(place, *args, *[w.value for w in self.extra]))


def _task_buttons(value="buildings"):
    return W.ToggleButtons(options=list(TASK_CLASS), value=value, description="Map of",
                           style={"button_width": "110px", "description_width": "150px"})


# ---- step 1: the model at home --------------------------------------------------------------

def model_at_home(url):
    """The land-cover model on hand-labelled OpenEarthMap tiles: scores and three examples."""
    try:
        S["oem"] = oem = get_oem(url)
    except Exception as exc:  # no network, wrong address: say so, do not crash
        display(W.HTML(_note(f"Could not load the data: {_html.escape(str(exc))}", "#b00020")))
        return
    chart = W.Image(format="png", layout=W.Layout(width="720px"))
    table = W.HTML()
    tile = W.ToggleButtons(options=[(f"example {i + 1}: " +
                                     str(n).rsplit("_", 1)[0].replace("_", " ").title(), i)
                                    for i, n in enumerate(oem["ex"]["names"])],
                           value=0, description="Look at", style={"button_width": "190px",
                                                                  "description_width": "150px"})
    example = W.Image(format="png")
    which = W.ToggleButtons(options=OEM_INPUTS, value="Stage 2", description="Map from",
                            style={"button_width": "100px", "description_width": "150px"})
    matrix = W.Image(format="png", layout=W.Layout(width="560px"))

    def draw_matrix(_=None):
        matrix.value = _png(fig_oem_confusion(oem, which.value))
    which.observe(draw_matrix, names="value")

    def draw_scores(_=None):
        m, metric = SCORING["metres"], SCORING["metric"]
        chart.value = _png(fig_oem_scores(oem, metric, m))
        tab = oem_table(oem, m).copy()
        tab.index = [f"{t}, {i}" for t, i in tab.index]
        table.value = tab.to_html(float_format="%.2f")

    def draw_example(_=None):
        example.value = _png(fig_oem_example(oem, tile.value))
    tile.observe(draw_example, names="value")
    SCORE_REFRESH.append(draw_scores)
    draw_scores()
    draw_example()
    draw_matrix()
    ui = W.VBox([_switches(), chart, table, W.HTML("<br>"), tile, example,
                 W.HTML("<br><b>Which classes does the model confuse?</b> (pixel-exact)"),
                 which, matrix])
    ui.tile, ui.which, ui.matrix = tile, which, matrix
    UI["home"] = ui
    display(ui)


# ---- step 2: pick your place ----------------------------------------------------------------

def pick_place(url):
    """A menu of the five places: choosing one loads it, and every step below follows."""
    menu = W.Dropdown(options=list(PLACES), value=PLACE_DEFAULT, description="Place",
                      layout=_WIDE, style=_LABEL)
    status = W.HTML()
    holder = W.VBox([])

    def load(_=None):
        menu.disabled = True
        status.value = _note(f"Loading {_html.escape(menu.value)} ...")
        try:
            S["place"] = Place(menu.value, url)
            ANSWERS["PLACE"] = menu.value
            status.value = _note(_html.escape(repr(S["place"])), "#555")
            if holder.children:
                _refresh_all()          # every step below follows the new place
            else:
                holder.children = (Viewer(fig_inputs, size_m=1000).box,)
        except Exception as exc:  # no network, wrong address: say so, do not crash
            status.value = _note(f"Could not load the data: {_html.escape(str(exc))}",
                                 "#b00020")
        finally:
            menu.disabled = False
    menu.observe(load, names="value")
    ui = W.VBox([menu, status, holder])
    ui.menu, ui.status = menu, status
    UI["place"] = ui
    display(ui)
    load()


# ---- step 3: guess --------------------------------------------------------------------------

def guess():
    UI["guess"] = ask(("GUESS_BUILDINGS", "Which image will give the best map of buildings?",
                       BEST),
                      ("GUESS_ROADS", "And the best map of roads?", BEST))


# ---- step 4: the maps -----------------------------------------------------------------------

def show_maps():
    if not _place_needed():
        return
    viewer = Viewer(fig_landcover, size_m=1000)
    UI["maps"] = viewer
    display(viewer.box)


# ---- step 5: the scores ---------------------------------------------------------------------

def show_scores():
    """A button that shows the scores (after you have guessed); the switches change how they
    are counted."""
    if not _place_needed():
        return
    show = W.Button(description="Show the scores", button_style="primary", icon="eye",
                    layout=W.Layout(width="220px"))
    out = W.VBox([])

    def draw(_=None):
        if not show.disabled:
            return                      # not revealed yet
        p, m, metric = S["place"], SCORING["metres"], SCORING["metric"]
        table = score_table(p, m)
        S["table"] = table
        guesses = {"buildings": ANSWERS.get("GUESS_BUILDINGS"),
                   "roads": ANSWERS.get("GUESS_ROADS")}
        tab = table.copy()
        tab.index = [f"{t}, {i}" for t, i in tab.index]
        out.children = (
            W.HBox([W.Image(value=_png(fig_reference(p)), format="png",
                            layout=W.Layout(width="400px")),
                    W.Image(value=_png(fig_scores(table, f"{p.name}: the land-cover model "
                                                         "against the public maps", metric)),
                            format="png", layout=W.Layout(width="560px"))]),
            W.HTML(_pre("\n".join(guess_lines(table, guesses, metric)))),
            W.HTML(tab.to_html(float_format="%.2f")))

    def reveal(_):
        if not (ANSWERS.get("GUESS_BUILDINGS") and ANSWERS.get("GUESS_ROADS")):
            note.value = _note("Make both guesses in step 3 first (or press again to see the "
                               "scores without a guess).", "#b00020")
            if not note.warned:
                note.warned = True
                return
        note.value = ""
        show.disabled = True
        show.description = "Scores shown"
        draw()
    note = W.HTML()
    note.warned = False
    show.on_click(reveal)
    REFRESH.append(draw)
    SCORE_REFRESH.append(draw)
    ui = W.VBox([_switches(), show, note, out])
    ui.show = show
    UI["scores"] = ui
    display(ui)


# ---- step 6: hunt ---------------------------------------------------------------------------

def hunt():
    if not _place_needed():
        return
    viewer = Viewer(fig_errors, size_m=500,
                    extra=[_task_buttons(), _switch("metres"), _switch("metric")])
    UI["hunt"] = viewer
    display(viewer.box)
    UI["finds"] = ask(("RESCUE", "A rescue: something Sentinel-2 missed and super-resolution "
                       "found", "text"),
                      ("FAILURE", "A failure: something the super-resolved map gets wrong",
                       "text"))


# ---- the result card ------------------------------------------------------------------------

def card_text():
    def get(key):
        v = ANSWERS.get(key)
        return "(not answered)" if v in ("", None) else v

    m = SCORING["metres"]
    lines = ["=" * 68, f"PLACE     {get('PLACE')}", f"SCORED    {tol_text(m)}"]
    if "place" in S:
        table = score_table(S["place"], m)
        for metric in METRICS:
            for t in TASK_CLASS:
                v = table[metric][t]
                base = table.attrs["everywhere"][t][metric]
                lines.append(f"{metric:<9} {t:<10} " + ", ".join(f"{i} {v[i]:.2f}" for i in INPUTS)
                             + f"  (everywhere {base:.2f})")
    lines += ["-" * 68,
              f"my guess, buildings:     {get('GUESS_BUILDINGS')}",
              f"my guess, roads:         {get('GUESS_ROADS')}",
              f"rescued by SR:           {get('RESCUE')}",
              f"failure:                 {get('FAILURE')}",
              "=" * 68]
    return "\n".join(lines)


def result_card():
    card = W.HTML(_pre(card_text()))
    again = W.Button(description="Update the card", icon="refresh")
    again.on_click(lambda _: setattr(card, "value", _pre(card_text())))
    ui = W.VBox([card, again])
    ui.card, ui.again = card, again
    UI["card"] = ui
    display(ui)


# ---- for the discussion: all places, and a model trained on each input ----------------------

def all_places_view(url, own_model=False):
    """Bars and a table for all five places; the switches change how they are counted."""
    summary = get_summary(url)
    chart = W.Image(format="png")
    table = W.HTML()

    def draw(_=None):
        m, metric = SCORING["metres"], SCORING["metric"]
        chart.value = _png(fig_all_places(summary, metric, m, own_model))
        value = f"own_model_{metric}" if own_model else metric
        table.value = all_places(summary, value, m).to_html(float_format="%.2f")
    SCORE_REFRESH.append(draw)
    draw()
    ui = W.VBox([_switches(), chart, table])
    UI["own" if own_model else "all"] = ui
    display(ui)
