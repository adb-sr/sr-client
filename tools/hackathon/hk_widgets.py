# ---- the notebook's controls (ipywidgets): menus, sliders and buttons that act at once ------
# Pasted after hk.py by build.py. Each part's cell is run once; its controls redraw at once.
# Parts 6 and 9 follow the decision settings of part 5. Test by setting widget values in UI.
import contextlib
import html as _html
import io

import ipywidgets as W
from IPython.display import display

ANSWERS = {}     # your team's answers; saved as soon as you type or click
UI = {}          # the controls of each part (used for testing)
S = {}           # this session: the task and the current decision (units, preds, hit, res)
REFRESH = []     # what to redraw when the decision settings of part 5 change
ANSWER_REFRESH = []   # what to redraw when an answer changes
_WIDE = W.Layout(width="600px")
_LABEL = {"description_width": "200px"}


def _buttons(width):
    return {"button_width": width, "description_width": "200px"}


def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=90, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _note(text, colour="#333"):
    return f"<div style='color:{colour}; line-height:1.5'>{text}</div>"


def _pre(text):
    return f"<pre style='margin:4px 0; line-height:1.35'>{_html.escape(text)}</pre>"


def _error(exc):
    return _note(f"Something went wrong: {_html.escape(str(exc))}. Run the cell again, or ask "
                 "a facilitator.", "#b00020")


def _run(fn, *args, **kwargs):
    """Call fn with plt.show switched off. Returns (its result, PNGs of the figures it drew,
    what it printed), so the figures can go into image widgets."""
    plt.close("all")
    show, plt.show = plt.show, (lambda *a, **k: None)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            out = fn(*args, **kwargs)
    finally:
        plt.show = show
    pngs = [_png(plt.figure(n)) for n in list(plt.get_fignums())]
    plt.close("all")
    return out, pngs, buf.getvalue().strip()


def _images(pngs):
    return [W.Image(value=p, format="png", layout=W.Layout(max_width="100%")) for p in pngs]


def _html_table(t):
    try:
        return t.to_html()
    except TypeError:
        return t.to_html(float_format="%.2f")


def _short(task):
    return {k: SHORT[k] for k in task.inputs}


def _kind(task):
    return task.meta["task"]


def _need_decision():
    if "res" not in S:
        display(W.HTML(_note("<b>Run the cell of part 5 first</b>, then run this cell again.",
                             "#b00020")))
        return False
    return True


# ---- answers that save themselves ------------------------------------------------------------

def ask(*questions, fill=None):
    """Each question is (key, text, kind[, example]): kind is "text" or a list of choices. The
    answer is saved in ANSWERS the moment it changes; nothing to run. ``fill`` adds a button
    that copies the examples into the empty fields."""
    rows, fields = [], {}
    for q in questions:
        key, text, kind = q[:3]
        example = q[3] if len(q) > 3 else ""
        saved = W.HTML()
        if kind == "text":
            field = W.Text(value=ANSWERS.get(key, ""), continuous_update=True, layout=_WIDE,
                           placeholder=f"e.g. {example}" if example else "type here")
        else:
            field = W.ToggleButtons(options=list(kind), value=ANSWERS.get(key),
                                    style={"button_width": "auto"})

        def on_change(change, key=key, saved=saved):
            ANSWERS[key] = change["new"]
            saved.value = _note("saved ✓", "#1a7f37") if change["new"] not in ("", None) else ""
            for redraw in ANSWER_REFRESH:
                redraw()
        field.observe(on_change, names="value")
        field.example = example
        fields[key] = field
        rows.append(W.VBox([W.HTML(f"<b>{text}</b>"), W.HBox([field, saved])],
                           layout=W.Layout(margin="4px 0 8px 0")))
    if fill:
        button = W.Button(description=fill, icon="clipboard", layout=W.Layout(width="300px"))

        def on_fill(_):
            for f in fields.values():
                if isinstance(f, W.Text) and not f.value.strip():
                    f.value = f.example
        button.on_click(on_fill)
        rows.insert(0, button)
    box = W.VBox(rows, layout=W.Layout(border="1px solid #007DB7", padding="8px 12px",
                                       margin="8px 0"))
    box.fields = fields
    display(box)
    return box


# ---- part 3: look around ---------------------------------------------------------------------

def _stretch_buttons():
    return W.ToggleButtons(options=[("auto contrast", "auto"), ("as delivered", "none")],
                           value="auto", description="Colours", style=_buttons("110px"),
                           tooltips=["each image stretched for viewing",
                                     "the colours the package stores"])


def explore(task):
    """Menus and sliders to move through the places; the picture follows at once."""
    kind = _kind(task)
    image = W.VBox([])
    status = W.HTML()
    stretch = _stretch_buttons()
    if kind == "ifs_manila":
        sc = task.scenes.sort_values("informal_share", ascending=False)
        tile = W.Dropdown(options=[(f"{sid}  ({s:.0%} informal)", sid)
                                   for sid, s in sc.informal_share.items()],
                          description="Tile (most informal first)", layout=_WIDE, style=_LABEL)
        n_models = len(task.meta.get("models", [])) or 6
        model = W.Dropdown(options=[("mean of the six models", None)]
                           + [(f"model {i + 1} only", i) for i in range(n_models)],
                           description="Model output", style=_LABEL)
        thr = W.FloatSlider(value=0.5, min=0.1, max=0.9, step=0.05, continuous_update=False,
                            readout_format=".2f", description="Flag a pixel above",
                            layout=_WIDE, style=_LABEL)
        controls = [tile, model, thr, stretch]

        def render():
            ifs_show(task, tile.value, model=model.value, thr=thr.value, stretch=stretch.value)
    elif kind == "hanoi_landcover":
        sort_by = W.Dropdown(options=[(n, i) for i, n in enumerate(LC_NAMES)], value=6,
                             description="Sort tiles by", layout=_WIDE, style=_LABEL)
        tile = W.Dropdown(description="Tile (most first)", layout=_WIDE, style=_LABEL)
        outline = W.Checkbox(value=True, description="Outline that class (expert map) in black",
                             layout=_WIDE, style=_LABEL)
        controls = [sort_by, tile, outline, stretch]

        def tiles(_=None):
            col = f"share_{sort_by.value}"
            sc = task.scenes.sort_values(col, ascending=False)
            tile.options = [(f"{sid}  ({v:.0%} {LC_NAMES[sort_by.value]})", sid)
                            for sid, v in sc[col].items()]
        sort_by.observe(tiles, names="value")
        tiles()

        def render():
            lc_show(task, tile.value, stretch=stretch.value,
                    target=sort_by.value if outline.value else None)
    else:
        area = W.Dropdown(options=[(f"{sid}  ({int(s.n_fields):,} fields)", sid)
                                   for sid, s in task.scenes.iterrows()],
                          value="16_cambodia", description="Area", layout=_WIDE, style=_LABEL)
        size = W.ToggleButtons(options=[("250 m", 100), ("500 m", 200), ("1 km", 400),
                                        ("2 km", 800)], value=400, description="Window",
                               style=_buttons("80px"))
        east = W.IntSlider(value=2000, min=0, max=4000, step=100, continuous_update=False,
                           description="← west | east → (m)", layout=_WIDE, style=_LABEL)
        south = W.IntSlider(value=2000, min=0, max=4000, step=100, continuous_update=False,
                            description="↑ north | south ↓ (m)", layout=_WIDE, style=_LABEL)
        seed = W.ToggleButtons(options=[("model 1", 0), ("model 2", 1), ("model 3", 2)], value=0,
                               description="Trained model (seed)", style=_buttons("80px"))
        controls = [area, size, east, south, seed, stretch]

        def limits(_=None):
            s = task.scenes.loc[area.value]
            east.max = int((int(s.w) - size.value) * task.px) // 100 * 100
            south.max = int((int(s.h) - size.value) * task.px) // 100 * 100
        area.observe(limits, names="value")
        size.observe(limits, names="value")
        limits()

        def render():
            y0, x0 = int(south.value / task.px), int(east.value / task.px)
            ai4_show(task, area.value, y0=y0, x0=x0, size=size.value, seed=seed.value,
                     stretch=stretch.value)

    def draw(_=None):
        try:
            _, pngs, _ = _run(render)
            image.children = _images(pngs)
        except Exception as exc:  # say what went wrong instead of failing silently
            status.value = _error(exc)
    for w in controls:
        w.observe(draw, names="value")
    ui = W.VBox([*controls, status, image])
    ui.controls = controls
    UI["explore"] = ui
    display(ui)
    draw()


# ---- part 4: the scenario --------------------------------------------------------------------

SCENARIO_FIELDS = [("team", "Team name"),
                   ("decision_maker", "Who decides?"),
                   ("decision", "What do they decide?"),
                   ("budget", "Budget: how many places can they act on?"),
                   ("hit", "What counts as a hit (a place worth the visit)?"),
                   ("cost_of_wasted_visit", "What does a wasted visit cost?"),
                   ("cost_of_missed_place", "What does a missed place cost?")]

EXAMPLES = {
    "ifs_manila": dict(
        team="Team A",
        decision_maker="DHSUD regional office, informal settlement upgrading programme",
        decision="Which city blocks get a field survey this quarter",
        budget="20 survey visits, one 100 m x 100 m block each",
        hit="a block where at least a quarter of the area is informal settlement",
        cost_of_wasted_visit="1 survey day for a team of 2",
        cost_of_missed_place="a settlement left out of the programme for a year: about 3 survey "
                             "days' worth"),
    "hanoi_landcover": dict(
        team="Team B",
        decision_maker="City environment department, air-quality enforcement unit",
        decision="Which 80 m x 80 m cells get a dust-control inspection this month (open construction "
                 "sites, cleared land, sand yards)",
        budget="20 inspections",
        hit="a cell where at least 20 % of the ground is bare soil or sand",
        cost_of_wasted_visit="1 inspector-day",
        cost_of_missed_place="a dust source left uncontrolled for a month: about 3 inspector-days' "
                             "worth"),
    "ai4_fields": dict(
        team="Team C",
        decision_maker="Department of Agriculture regional office, smallholder support programme",
        decision="Which 500 m x 500 m squares get an extension-worker visit to enrol small farms",
        budget="30 visits",
        hit="a square with at least 30 fields smaller than 0.25 ha",
        cost_of_wasted_visit="1 extension-worker day",
        cost_of_missed_place="~30 smallholders not enrolled this season: about 2 worker-days' "
                             "worth"),
}


def scenario(task):
    """Text fields for the team's scenario; saved as you type. The example is in grey."""
    ex = EXAMPLES[_kind(task)]
    UI["scenario"] = ask(*[(k, t, "text", ex[k]) for k, t in SCENARIO_FIELDS],
                         fill="Fill the empty fields with the example")


def scenario_dict():
    """The scenario as typed in part 4 (empty fields: '(not answered)')."""
    return {k: (ANSWERS.get(k) or "").strip() or "(not answered)" for k, _ in SCENARIO_FIELDS}


# ---- part 5: the decision cell ---------------------------------------------------------------

def _int_slider(value, lo, hi, step, text):
    return W.IntSlider(value=value, min=lo, max=hi, step=step, continuous_update=False,
                       description=text, layout=_WIDE, style=_LABEL)


def _cost(value, text):
    return W.BoundedFloatText(value=value, min=0, max=10000, step=0.5, description=text,
                              style=_LABEL)


def decision_panel(task):
    """The decision controls. Every change recomputes the hits at once, and parts 6 and 9
    follow. The places (blocks, areas or squares) are computed once per setting and kept."""
    kind = _kind(task)
    labels = _short(task)
    S.update(task=task, cache={})
    if kind == "ifs_manila":
        budget = _int_slider(20, 5, 100, 5, "Budget (blocks you survey)")
        size = W.ToggleButtons(options=[("50 m", 50), ("100 m", 100), ("200 m", 200)],
                               value=100, description="Block size", style=_buttons("80px"))
        hit_at = W.FloatSlider(value=0.25, min=0.05, max=0.9, step=0.05, continuous_update=False,
                               readout_format=".0%", layout=_WIDE, style=_LABEL,
                               description="Hit = informal share at least")
        cw, cm = _cost(1, "Cost of a wasted visit"), _cost(3, "Cost of a missed place")
        unit_controls, controls = [size], [budget, size, hit_at, cw, cm]

        def places():
            return ifs_units(task, cell_m=size.value)

        def settings():
            return {"block": f"{size.value} m", "hit": f"informal share ≥ {hit_at.value:.0%}"}

        def title():
            return f"Survey {budget.value} blocks of {size.value} m: how many are hits?"
        place_word = "blocks"
    elif kind == "hanoi_landcover":
        target = W.Dropdown(options=[(n, i) for i, n in enumerate(LC_NAMES)]
                            + [("built-up (building + road)", (0, 1)),
                               ("green (tree + low vegetation)", (3, 4))],
                            value=6, description="Land cover you look for", layout=_WIDE,
                            style=_LABEL)
        size = W.ToggleButtons(options=[("40 m", 40), ("80 m", 80), ("160 m", 160)],
                               value=80, description="Cell size", style=_buttons("80px"))
        budget = _int_slider(20, 5, 100, 5, "Budget (cells you inspect)")
        hit_at = W.FloatSlider(value=0.2, min=0.05, max=0.9, step=0.05, continuous_update=False,
                               readout_format=".0%", layout=_WIDE, style=_LABEL,
                               description="Hit = share of the cell at least")
        cw, cm = _cost(1, "Cost of a wasted visit"), _cost(3, "Cost of a missed place")
        unit_controls, controls = [target, size], [target, size, budget, hit_at, cw, cm]

        def what():
            return next(n for n, v in target.options if v == target.value)

        def places():
            return lc_units(task, cell_m=size.value, target=target.value)

        def settings():
            return {"looking for": what(), "cell": f"{size.value} m",
                    "hit": f"{what()} ≥ {hit_at.value:.0%} of the cell"}

        def title():
            return f"Inspect {budget.value} cells of {size.value} m ({what()}): how many are hits?"
        place_word = "cells"
    else:
        budget = _int_slider(30, 5, 100, 5, "Budget (squares you visit)")
        size = W.ToggleButtons(options=[("250 m", 250), ("500 m", 500), ("1 km", 1000)],
                               value=500, description="Square size", style=_buttons("80px"))
        small = W.ToggleButtons(options=[("all fields", 0), ("< 0.1 ha", 1000),
                                         ("< 0.25 ha", 2500), ("< 0.5 ha", 5000)], value=2500,
                                description="Count fields", style=_buttons("90px"))
        hit_at = _int_slider(30, 1, 150, 1, "Hit = at least this many fields")
        cw, cm = _cost(1, "Cost of a wasted visit"), _cost(2, "Cost of a missed place")
        unit_controls, controls = [size, small], [budget, size, small, hit_at, cw, cm]

        def places():
            return ai4_units(task, cell_m=size.value, small_m2=small.value or None)

        def settings():
            what = "fields" if not small.value else f"fields < {small.value / 10000:g} ha"
            return {"square": f"{size.value} m", "hit": f"≥ {hit_at.value} {what}"}

        def title():
            return f"Visit {budget.value} squares of {size.value} m: how many are hits?"
        place_word = "squares"

    status = W.HTML()
    chart = W.Image(format="png", layout=W.Layout(max_width="100%"))
    table = W.HTML()

    def compute(_=None):
        key = tuple(w.value for w in unit_controls)
        try:
            if key not in S["cache"]:
                status.value = _note(f"Cutting the map into {place_word} ... (the first time "
                                     "for a setting can take up to 20 seconds)")
                (units, preds), _, said = _run(places)
                S["cache"][key] = (units, preds, said)
            units, preds, said = S["cache"][key]
            hit = units.truth.values >= hit_at.value
            res, _, said2 = _run(decide, units, preds, hit, budget.value, cw.value, cm.value,
                                 labels=labels)
            S.update(units=units, preds=preds, hit=hit, res=res, budget=budget.value,
                     target=target.value if kind == "hanoi_landcover" else None,
                     hit_at=hit_at.value,
                     cost_wasted=cw.value, cost_missed=cm.value, title=title(),
                     settings={"budget": budget.value, **settings(),
                               "cost of a wasted visit": cw.value,
                               "cost of a missed place": cm.value},
                     place_word=place_word)
            _, pngs, _ = _run(plot_decision, res, budget.value, title())
            chart.value = pngs[0]
            table.value = res.to_html()
            status.value = _pre("\n".join(x for x in (said, said2) if x))
        except Exception as exc:  # say what went wrong instead of failing silently
            status.value = _error(exc)
            return
        for redraw in REFRESH:
            try:
                redraw()
            except Exception:  # a later part must not break the decision cell
                pass
    for w in controls:
        w.observe(compute, names="value")
    ui = W.VBox([*controls, status, chart, table])
    ui.controls = {w.description: w for w in controls}
    UI["decision"] = ui
    display(ui)
    compute()


def current():
    """The current decision of part 5: units (one row per place), preds ({input: array
    (models, places)}), hit (bool per place) and res (the table)."""
    return S["units"], S["preds"], S["hit"], S["res"]


# ---- part 5b: other budgets ------------------------------------------------------------------

def sweep_view():
    """Share of hits for budgets from 5 to 100; follows the settings of part 5."""
    if not _need_decision():
        return
    chart = W.Image(format="png", layout=W.Layout(max_width="100%"))

    def draw():
        _, pngs, _ = _run(sweep, S["preds"], S["hit"], labels=_short(S["task"]),
                          title=f"Share of visits that are hits ({S['place_word']}, "
                                f"{S['settings']['hit']})")
        chart.value = pngs[0]
    REFRESH.append(draw)
    draw()
    UI["sweep"] = chart
    display(chart)


# ---- part 6: which places, and the failures --------------------------------------------------

def _gallery(task, idx, key, title):
    fn = {"ifs_manila": ifs_gallery, "hanoi_landcover": lc_gallery, "ai4_fields": ai4_gallery}[
        _kind(task)]
    if not len(idx):
        return []
    extra = {"target": S["target"]} if _kind(task) == "hanoi_landcover" else {}
    _, pngs, _ = _run(fn, task, S["units"], idx, key=key, hit=S["hit"], title=title, **extra)
    return pngs


def _detail(task, i):
    u = S["units"].iloc[i]
    kind = _kind(task)
    if kind == "ifs_manila":
        return _run(ifs_show, task, u.scene, box=(u.y0, u.x0, u["size"]))[1]
    if kind == "hanoi_landcover":
        return _run(lc_show, task, u.scene, target=S["target"], box=(u.y0, u.x0, u["size"]))[1]
    return _run(ai4_show, task, u.scene, y0=int(u.y0), x0=int(u.x0), size=int(u["size"]))[1]


def picks_view(max_shown=16):
    """The overlap table, the places each input would pick, its failures and one place in
    detail. Follows the settings of part 5."""
    if not _need_decision():
        return
    task = S["task"]
    labels = _short(task)
    shown = [k for k in task.inputs if task.has_image[k]]
    overlap = W.HTML()
    pick = W.ToggleButtons(options=[(labels[k], k) for k in task.inputs],
                           value="stage2" if "stage2" in task.inputs else task.inputs[-1],
                           description="Places picked with", style=_buttons("120px"))
    default_img = "stage1" if _kind(task) == "ai4_fields" else "stage2"
    on = W.ToggleButtons(options=[(labels[k], k) for k in shown], value=default_img,
                         description="Shown on the image of", style=_buttons("120px"))
    galleries = W.VBox([])
    which = W.ToggleButtons(options=[("a confident false alarm", "false"),
                                     ("a missed hit", "missed")], value="false",
                            description="Look closer at", style=_buttons("170px"))
    number = W.IntSlider(value=1, min=1, max=8, continuous_update=False, layout=_WIDE,
                         style=_LABEL, description="Number (1 = most striking)")
    detail = W.VBox([])
    status = W.HTML()

    def lists():
        score = np.atleast_2d(S["preds"][pick.value]).mean(0)
        hit, k = S["hit"], S["budget"]
        order = np.argsort(-score)
        chosen = set(order[:k])
        false = [i for i in order if not hit[i]][:8]
        missed = [i for i in np.argsort(-S["units"].truth.values)
                  if hit[i] and i not in chosen][:8]
        return top_k(score, k), false, missed

    def draw_detail(_=None):
        try:
            _, false, missed = lists()
            idx = false if which.value == "false" else missed
            if not idx:
                detail.children = (W.HTML(_note("None: nothing to show for this setting.")),)
                return
            number.max = len(idx)
            detail.children = _images(_detail(task, idx[min(number.value, len(idx)) - 1]))
        except Exception as exc:
            status.value = _error(exc)

    def draw(_=None):
        try:
            status.value = ""
            overlap.value = _html_table(overlap_table(S["preds"], S["budget"], labels=labels))
            picks, false, missed = lists()
            name, w = labels[pick.value], S["place_word"]
            note = (f" (the first {max_shown} of {len(picks)})" if len(picks) > max_shown else "")
            pngs = (_gallery(task, picks[:max_shown], on.value,
                             f"The {S['budget']} {w} you would visit using {name}{note}")
                    + _gallery(task, false, on.value,
                               f"{name}: highest-scoring {w} that are NOT hits")
                    + _gallery(task, missed, on.value, f"Clear hits that {name} would NOT visit"))
            galleries.children = _images(pngs)
            draw_detail()
        except Exception as exc:
            status.value = _error(exc)
    for w in (pick, on):
        w.observe(draw, names="value")
    for w in (which, number):
        w.observe(draw_detail, names="value")
    REFRESH.append(draw)
    ui = W.VBox([W.HTML("<b>Share of the picked places that two inputs have in common</b>"),
                 overlap, pick, on, status, galleries,
                 W.HTML("<br><b>One place in detail</b> (for the input picked above)"),
                 which, number, detail])
    ui.pick, ui.on, ui.which, ui.number, ui.galleries, ui.detail = (pick, on, which, number,
                                                                     galleries, detail)
    UI["picks"] = ui
    display(ui)
    draw()
    UI["finds"] = ask(("RESCUE", "A place where super-resolution changed the decision for the "
                       "better (which one, and why)", "text"),
                      ("FAILURE", "A failure worth telling the room about (which place, what went "
                       "wrong)", "text"))


# ---- part 8: the SR service ------------------------------------------------------------------

OWN_PLACE = "My own place"


def sr_panel(sr, ready_made, default_lat, default_lon):
    """Pick a ready-made area (or your own point), send it with one button and look at the
    result with sliders. The button waits until the job is done (3–6 minutes for a new area)."""
    from sr_client import SRError, area_around
    from sr_client.client import FINISHED
    place = W.Dropdown(options=[*ready_made, OWN_PLACE], description="Area", layout=_WIDE,
                       style=_LABEL)
    lat = W.FloatText(value=default_lat, description="Latitude", style=_LABEL)
    lon = W.FloatText(value=default_lon, description="Longitude", style=_LABEL)
    km = W.BoundedFloatText(value=2, min=0.5, max=5, step=0.5, description="Size (km)",
                            style=_LABEL)
    day = W.Text(value="2026-03-15", description="Date (YYYY-MM-DD)", style=_LABEL)
    own = W.VBox([W.HTML(_note("A point (in Google Maps: right-click, then click the "
                               "coordinates to copy them), a size and a date, ideally in the "
                               "dry season.")), lat, lon, km, day])
    own.layout.display = "none"
    stages = W.ToggleButtons(options=[("stage 1 and 2", "12"), ("stage 1 only (faster)", "1")],
                             value="12", description="Make", style=_buttons("170px"))
    send = W.Button(description="Send and wait", button_style="primary", icon="rocket",
                    layout=W.Layout(width="220px"))
    status = W.HTML()
    viewer = W.VBox([])

    def toggle(_=None):
        own.layout.display = "" if place.value == OWN_PLACE else "none"
    place.observe(toggle, names="value")

    def on_send(_):
        send.disabled = True
        viewer.children = ()
        try:
            if place.value == OWN_PLACE:
                area, d, options = area_around(lat.value, lon.value, km=km.value), \
                    day.value.strip(), {}
            else:
                p = ready_made[place.value]
                area, d, options = p["area"], p["date"], p.get("options", {})
            job = sr.submit(area, d, stages=list(stages.value), **options)
            t0 = time.monotonic()
            while job.status not in FINISHED:
                status.value = _pre(job._progress_line(time.monotonic() - t0))
                time.sleep(5)
                job.refresh()
            lines = [f"job {job.id[:8]}: {job.status} after "
                     f"{(time.monotonic() - t0) / 60:.1f} min"]
            lines += [f"warning [{w['code']}]: {w['message']}" for w in job.warnings]
            status.value = _pre("\n".join(lines))
            if job.status not in ("done", "partial"):
                status.value += _note(f"The job did not finish: {job.info.get('error')}",
                                      "#b00020")
                return
            S["job"] = job
            viewer.children = (_job_viewer(job),)
        except SRError as exc:
            status.value = _note(f"The service said: {_html.escape(exc.message)}", "#b00020")
        except Exception as exc:
            status.value = _error(exc)
        finally:
            send.disabled = False
    send.on_click(on_send)
    ui = W.VBox([place, own, stages, send, status, viewer])
    ui.place, ui.send, ui.status, ui.viewer, ui.own_fields = place, send, status, viewer, (
        lat, lon, km, day)
    UI["sr"] = ui
    display(ui)


def _rgb(da):
    a = np.moveaxis(np.nan_to_num(da.isel(band=[0, 1, 2]).values.astype("float32")), 0, -1)
    return a / max(float(a.max()), 1e-6) * 255


def _job_viewer(job):
    """Sentinel-2 and the SR stages side by side, with zoom and position sliders."""
    names = [("Sentinel-2 (10 m)", "lr_reference.tif"), ("SR stage 1", "stage1_sr.tif"),
             ("SR stage 2", "stage2_sr.tif")]
    files = job.results()["files"]
    layers = [(t, _rgb(job.open(f))) for t, f in names if f in files]
    h, w = layers[-1][1].shape[:2]
    px = 2.5
    half = int(min(h, w) * px / 2)
    size = W.ToggleButtons(options=[("250 m", 100), ("500 m", 200), ("1 km", 400),
                                    ("whole area", max(h, w))], value=min(400, max(h, w)),
                           description="Zoom", style=_buttons("90px"))
    east = W.IntSlider(value=0, min=-half, max=half, step=50, continuous_update=False,
                       description="← west | east → (m)", layout=_WIDE, style=_LABEL)
    north = W.IntSlider(value=0, min=-half, max=half, step=50, continuous_update=False,
                        description="← south | north → (m)", layout=_WIDE, style=_LABEL)
    image = W.Image(format="png", layout=W.Layout(max_width="100%"))

    def draw(_=None):
        s = min(size.value, h, w)
        cy = int(np.clip(h / 2 - north.value / px, s / 2, h - s / 2))
        cx = int(np.clip(w / 2 + east.value / px, s / 2, w - s / 2))
        fig, axes = plt.subplots(1, len(layers), figsize=(5 * len(layers), 5.3), squeeze=False)
        for ax, (t, a) in zip(axes[0], layers):
            lh, lw = a.shape[:2]
            f = lh / h      # the 10 m image has fewer pixels
            crop = a[int((cy - s / 2) * f):int((cy + s / 2) * f),
                     int((cx - s / 2) * f):int((cx + s / 2) * f)]
            ax.imshow(autostretch(crop), interpolation="nearest")
            ax.set_title(t), ax.set_xticks([]), ax.set_yticks([])
        plt.tight_layout()
        image.value = _png(fig)
    for c in (size, east, north):
        c.observe(draw, names="value")
    draw()
    box = W.VBox([size, east, north, image])
    box.size, box.east, box.north, box.image = size, east, north, image
    return box


# ---- part 9: the numbers for your slide ------------------------------------------------------

def card_text():
    task = S["task"]
    lines = ["=" * 72, f"TASK      {task.meta['title']}"]
    for k, v in scenario_dict().items():
        lines.append(f"{k.replace('_', ' ').upper():<22}{v}")
    lines += ["-" * 72, "SETTINGS  " + ", ".join(f"{k} {v}" for k, v in S["settings"].items()),
              "", S["res"][["hits", "range over models", "hit rate", "missed places",
                             "cost"]].to_string(), "-" * 72]
    for key, text in (("VERDICT", "verdict"), ("CHANGE_MIND", "what would change our mind"),
                      ("RESCUE", "where SR helped"), ("FAILURE", "a failure")):
        v = ANSWERS.get(key)
        lines.append(f"{text + ':':<28}{v if v not in ('', None) else '(not answered)'}")
    lines.append("=" * 72)
    return "\n".join(lines)


def slide_card(fname="my_slide_chart.png"):
    """Your verdict, then a card with everything the slide needs; it follows the decision
    settings and your answers. The button downloads the chart."""
    if not _need_decision():
        return
    UI["verdict"] = ask(("VERDICT", "Your verdict", ["deploy", "pilot", "don't use"]),
                        ("CHANGE_MIND", "What would change your mind?", "text",
                         "a validation on 50 blocks in our own city"))
    card = W.HTML()
    chart = W.Image(format="png", layout=W.Layout(max_width="100%"))
    button = W.Button(description=f"Download the chart ({fname})", icon="download",
                      layout=W.Layout(width="320px"))
    note = W.HTML()

    def update(_=None):
        card.value = _pre(card_text())
        fig = plot_decision(S["res"], S["budget"], scenario_dict()["decision"])
        fig.savefig(fname, dpi=200, bbox_inches="tight")
        chart.value = _png(fig)

    def download(_):
        update()
        try:
            from google.colab import files
            files.download(fname)
            note.value = _note("Downloading ...", "#1a7f37")
        except Exception:  # not in Colab
            note.value = _note(f"Saved as {fname} next to this notebook.", "#1a7f37")
    button.on_click(download)
    REFRESH.append(update)
    ANSWER_REFRESH.append(update)
    update()
    ui = W.VBox([card, chart, button, note])
    ui.card, ui.chart, ui.button = card, chart, button
    UI["card"] = ui
    display(ui)
