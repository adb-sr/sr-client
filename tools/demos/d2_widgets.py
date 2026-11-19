# ---- the notebook's controls: menus, buttons and sliders that act at once ---------------------
S = {}          # this session: the place that is loaded, the scores, the decision
REFRESH = []    # what to redraw when the place changes
BEST = ["Sentinel-2", "Stage 1", "Stage 2", "no real difference"]


def _place_needed():
    if "place" not in S:
        display(W.HTML(_note("<b>Run the cell of step 1 first</b>, then run this cell again.",
                             "#b00020")))
        return False
    return True


def _refresh_all():
    for redraw in REFRESH:
        redraw()


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


# ---- step 1: pick your place ----------------------------------------------------------------

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
            S.pop("table", None)
            S.pop("hits", None)
            ANSWERS["PLACE"] = menu.value
            p = S["place"]
            status.value = _note(_html.escape(repr(p)), "#555")
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


# ---- step 2: guess --------------------------------------------------------------------------

def step2_guess():
    UI["guess"] = ask(("GUESS_BUILDINGS", "Which image will give the best map of buildings?",
                       BEST),
                      ("GUESS_ROADS", "And the best map of roads?", BEST))


# ---- step 3: the maps -----------------------------------------------------------------------

def step3_maps():
    if not _place_needed():
        return
    viewer = Viewer(fig_landcover, size_m=1000)
    UI["view3"] = viewer
    display(viewer.box)


# ---- step 4: the scores ---------------------------------------------------------------------

def step4_scores():
    """A button that shows the scores (after you have guessed)."""
    if not _place_needed():
        return
    show = W.Button(description="Show the scores", button_style="primary", icon="eye",
                    layout=W.Layout(width="220px"))
    out = W.VBox([])

    def draw(_=None):
        if not show.disabled:
            return                      # not revealed yet
        p = S["place"]
        table = score_table(p)
        S["table"] = table
        guess = {"buildings": ANSWERS.get("GUESS_BUILDINGS"),
                 "roads": ANSWERS.get("GUESS_ROADS")}
        tab = table.copy()
        tab.index = [f"{t}, {i}" for t, i in tab.index]
        out.children = (
            W.HBox([W.Image(value=_png(fig_reference(p)), format="png",
                            layout=W.Layout(width="400px")),
                    W.Image(value=_png(fig_scores(table, f"{p.name}: the land-cover model "
                                                          "against the public maps")),
                            format="png", layout=W.Layout(width="560px"))]),
            W.HTML(_pre("\n".join(guess_lines(table, guess)))),
            W.HTML(tab.to_html(float_format="%.2f")))

    def reveal(_):
        if not (ANSWERS.get("GUESS_BUILDINGS") and ANSWERS.get("GUESS_ROADS")):
            note.value = _note("Make both guesses in step 2 first (or press again to see the "
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
    ui = W.VBox([show, note, out])
    ui.show = show
    UI["scores"] = ui
    display(ui)


# ---- step 5: hunt ---------------------------------------------------------------------------

def step5_hunt():
    if not _place_needed():
        return
    viewer = Viewer(fig_errors, size_m=500, extra=[_task_buttons()])
    UI["view5"] = viewer
    display(viewer.box)
    UI["finds"] = ask(("RESCUE", "A rescue: something Sentinel-2 missed and super-resolution "
                       "found", "text"),
                      ("FAILURE", "A failure: something the super-resolved map gets wrong",
                       "text"))


# ---- step 6: decision and verdict -----------------------------------------------------------

def step6_decision():
    if not _place_needed():
        return
    task = _task_buttons()
    budget = W.IntSlider(value=10, min=3, max=30, step=1, continuous_update=False,
                         description="Squares you can visit", layout=_WIDE, style=_LABEL)
    image = W.Image(format="png")
    text = W.HTML()

    def draw(_=None):
        fig, hits, summary = decision(S["place"], task.value, budget.value)
        S["hits"], S["decision"] = hits, (task.value, budget.value)
        image.value = _png(fig)
        text.value = _pre(summary)
    for w in (task, budget):
        w.observe(draw, names="value")
    REFRESH.append(draw)
    draw()
    ui = W.VBox([task, budget, image, text])
    ui.task, ui.budget = task, budget
    UI["decision"] = ui
    display(ui)


def step6_verdict():
    UI["verdict"] = ask(
        ("VERDICT_FOR", "For which use? (for example: a screening map of built-up areas)",
         "text"),
        ("VERDICT", "Your verdict", ["deploy", "pilot", "do not use"]),
        ("WOULD_CHANGE_MY_MIND", "What would change your mind?", "text"))


# ---- the result card ------------------------------------------------------------------------

def card_text():
    def get(key):
        v = ANSWERS.get(key)
        return "(not answered)" if v in ("", None) else v

    lines = ["=" * 68, f"PLACE     {get('PLACE')}"]
    if "place" in S:
        table = S.get("table")
        if table is None:
            table = score_table(S["place"])
        for t in TASK_CLASS:
            f1 = table["F1"][t]
            lines.append(f"F1        {t:<10} " + ", ".join(f"{i} {f1[i]:.2f}" for i in INPUTS))
    if "hits" in S:
        t, b = S["decision"]
        lines.append(f"DECISION  {t}, {b} squares: hits " +
                     ", ".join(f"{i} {S['hits'][i]}" for i in INPUTS))
    lines += ["-" * 68,
              f"my guess, buildings:     {get('GUESS_BUILDINGS')}",
              f"my guess, roads:         {get('GUESS_ROADS')}",
              f"rescued by SR:           {get('RESCUE')}",
              f"failure:                 {get('FAILURE')}",
              f"VERDICT for {get('VERDICT_FOR')}: {get('VERDICT')}",
              f"what would change it:    {get('WOULD_CHANGE_MY_MIND')}",
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
