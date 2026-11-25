# ---- the notebook's controls (ipywidgets): menus, sliders and buttons that act at once ------
# Pasted after hk.py by build.py. Each part's cell is run once (Runtime > Run all does it);
# its controls redraw at once. Parts 3b to 6 stay closed until the bet of part 3 is revealed,
# then follow the decision settings of part 3. Test by setting widget values in UI.
import contextlib
import html as _html
import importlib
import io
import subprocess

import ipywidgets as W
from IPython.display import display

ANSWERS = {}     # your team's answers; saved as soon as you type or click
UI = {}          # the controls of each part (used for testing)
S = {}           # this session: the task, the brief and the current decision
REFRESH = {}     # what to redraw when the decision settings of part 3 change (by part)
ANSWER_REFRESH = {}   # what to redraw when an answer changes
_WIDE = W.Layout(width="600px")
_LABEL = {"description_width": "200px"}
_CARD = ("border:1px solid #c9c9c9; border-left:6px solid #007DB7; background:#fafafa; "
         "color:#222; padding:10px 16px; max-width:860px; line-height:1.5")
LOCKED = "&#128274; Opens once you reveal the result in part 3."


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
    return ("<pre style='margin:4px 0; line-height:1.35; font-family:monospace; "
            f"white-space:pre-wrap'>{_html.escape(text)}</pre>")


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
        display(W.HTML(_note("<b>Run the cell of part 3 first</b>, then run this cell again.",
                             "#b00020")))
        return False
    return True


def _gated(name, build):
    """A part that stays closed until the result of part 3 is revealed. build() makes the
    part once and returns (its widgets, a function that redraws it); afterwards the part
    follows every change of the decision settings."""
    holder = W.VBox([W.HTML(_note(LOCKED, "#8a6d00"))])
    state = {}

    def refresh():
        if not S.get("revealed"):
            return
        try:
            if "redraw" not in state:
                children, state["redraw"] = build()
                holder.children = tuple(children)
            else:
                state["redraw"]()
        except Exception as exc:  # say what went wrong instead of failing silently
            holder.children = (W.HTML(_error(exc)),)
    REFRESH[name] = refresh
    UI[name + "_holder"] = holder
    display(holder)
    refresh()


def _num(x):
    """6 for 6.04, 6.1 for 6.12: numbers as people say them."""
    return f"{x:,.0f}" if abs(x - round(x)) < 0.05 else f"{x:,.1f}"


# ---- answers that save themselves ------------------------------------------------------------

def ask(*questions, fill=None, show=True):
    """Each question is (key, text, kind[, example]): kind is "text", "checks" (tick any of
    the examples, a list) or a list of choices (pick one). The answer is saved in ANSWERS the
    moment it changes; nothing to run. ``fill`` adds a button that copies the examples into
    the empty fields."""
    rows, fields = [], {}
    for q in questions:
        key, text, kind = q[:3]
        example = q[3] if len(q) > 3 else ""
        saved = W.HTML()
        if kind == "checks":
            boxes = [W.Checkbox(value=c in ANSWERS.get(key, ()), description=c, indent=False,
                                layout=W.Layout(width="760px")) for c in example]

            def on_tick(_, key=key, boxes=boxes, saved=saved):
                ANSWERS[key] = [b.description for b in boxes if b.value]
                saved.value = _note("saved ✓", "#1a7f37") if ANSWERS[key] else ""
                for redraw in list(ANSWER_REFRESH.values()):
                    redraw()
            for b in boxes:
                b.observe(on_tick, names="value")
            field = W.VBox(boxes)
            field.boxes = boxes
            fields[key] = field
            rows.append(W.VBox([W.HTML(f"<b>{text}</b>"), field, saved],
                               layout=W.Layout(margin="4px 0 8px 0")))
            continue
        if kind == "text":
            field = W.Text(value=ANSWERS.get(key, ""), continuous_update=True, layout=_WIDE,
                           placeholder=f"e.g. {example}" if example else "type here")
        else:
            field = W.ToggleButtons(options=list(kind), value=ANSWERS.get(key),
                                    style={"button_width": "auto"})

        def on_change(change, key=key, saved=saved):
            ANSWERS[key] = change["new"]
            saved.value = _note("saved ✓", "#1a7f37") if change["new"] not in ("", None) else ""
            for redraw in list(ANSWER_REFRESH.values()):
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
    if show:
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


# ---- part 1: the brief -----------------------------------------------------------------------
# Mock policy briefs: invented for the workshop. Each sets the scenario text of part 1, the
# decision settings of part 3 and the area and rhythm of part 5.

SCENARIO_FIELDS = [("team", "Team name"),
                   ("decision_maker", "Who decides?"),
                   ("decision", "What do they decide?"),
                   ("budget", "Budget: how many places can they act on?"),
                   ("hit", "What counts as a hit (a place worth the visit)?"),
                   ("cost_of_wasted_visit", "What does a wasted visit cost?"),
                   ("cost_of_missed_place", "What does a missed place cost?")]

BRIEFS = {
    "ifs_manila": [
        dict(title="Where should the validation teams go first?",
             frm="Regional Director, housing and urban development office",
             to="Planning and monitoring team (you)",
             situation="The city is updating its Local Shelter Plan. Its list of informal "
                       "settlements is years old, and families missing from the list cannot be "
                       "planned for. Your teams can validate 20 blocks this quarter. There is "
                       "no budget for new commercial images of the whole city every year.",
             question="Can free Sentinel-2 images, sharpened by super-resolution, show us "
                      "which 20 blocks to validate first? Or do we have to buy real "
                      "high-resolution images?",
             scenario=dict(
                 decision_maker="Regional office for housing and urban development, settlement "
                                "upgrading programme",
                 decision="Which city blocks get a field validation this quarter",
                 budget="20 validation visits, one 100 m x 100 m block each",
                 hit="a block where at least a quarter of the area is informal settlement",
                 cost_of_wasted_visit="1 day for a team of 2",
                 cost_of_missed_place="families left out of the shelter plan for a year: about "
                                      "3 survey days' worth"),
             settings=dict(budget=20, size=100, hit_at=0.25, cw=1, cm=3),
             area=(620, "Metro Manila is about 620 km²"), updates=4),
        dict(title="A settlement watch list for local governments?",
             frm="Deputy Director General, national space agency",
             to="Space applications team (you)",
             situation="Local governments ask the agency where informal settlements are "
                       "likely, so they can plan services. From free images, the agency could "
                       "send every city a fresh list each quarter. But local staff are busy: a "
                       "city will check only the top 50 blocks, and every wrong flag on a "
                       "formal neighbourhood costs the agency trust.",
             question="Is a list made from super-resolved images good enough to send out as "
                      "'look here first'? Or should we wait until we can pay for real "
                      "high-resolution images?",
             scenario=dict(
                 decision_maker="National space agency, space applications team",
                 decision="Whether to send local governments a quarterly list of blocks that "
                          "likely hold informal settlements",
                 budget="the 50 blocks at the top of a city's list, 100 m x 100 m each",
                 hit="a block where at least 10 % of the area is informal settlement",
                 cost_of_wasted_visit="a wrong flag costs trust and local staff time: 2",
                 cost_of_missed_place="a settlement that stays off the list this quarter: 1"),
             settings=dict(budget=50, size=100, hit_at=0.10, cw=2, cm=1),
             area=(300000, "the Philippines is about 300,000 km²"), updates=4),
    ],
    "hanoi_landcover": [
        dict(title="Which building sites get a dust inspection?",
             frm="Head, city environment department",
             to="Air-quality enforcement unit (you)",
             situation="In the dry season, dust from building sites, cleared land and sand "
                       "yards is a main source of the city's air pollution. Your inspectors "
                       "can make 20 inspections a month. Today they go where complaints come "
                       "from.",
             question="Can super-resolved Sentinel-2 images point the inspectors to open, bare "
                      "ground each month? Or would free Sentinel-2 do?",
             scenario=dict(
                 decision_maker="City environment department, air-quality enforcement unit",
                 decision="Which 80 m x 80 m cells get a dust-control inspection this month "
                          "(open construction sites, cleared land, sand yards)",
                 budget="20 inspections a month",
                 hit="a cell where at least 20 % of the ground is bare soil or sand",
                 cost_of_wasted_visit="1 inspector-day",
                 cost_of_missed_place="a dust source left uncontrolled for a month: about 3 "
                                      "inspector-days' worth"),
             settings=dict(target=6, size=80, budget=20, hit_at=0.20, cw=1, cm=3),
             area=(3360, "the city of Hanoi is about 3,360 km²"), updates=12),
        dict(title="Are houses going up on protected farmland?",
             frm="Director, provincial land-use and zoning office",
             to="Zoning compliance team (you)",
             situation="Rice land at the city's edge is protected: building on it needs a "
                       "conversion permit. Buildings appear anyway, a few at a time. Your team "
                       "can make 15 site checks a quarter and has no recent map.",
             question="Can super-resolved images show where buildings stand in farmland, so "
                      "the team knows where to check? (A real system would compare two dates. "
                      "Here you test the first step: finding buildings among fields.)",
             scenario=dict(
                 decision_maker="Provincial land-use and zoning office, zoning compliance team",
                 decision="Which 160 m x 160 m cells of farmland get a site check for buildings "
                          "without a permit",
                 budget="15 site checks a quarter",
                 hit="a cell that is at least half cropland and where buildings cover at least "
                     "5 % of the ground",
                 cost_of_wasted_visit="1 inspector-day",
                 cost_of_missed_place="a building without a permit that stands for another "
                                      "quarter: about 3 inspector-days' worth"),
             settings=dict(target=FARM_BUILDINGS, size=160, budget=15, hit_at=0.05, cw=1, cm=3),
             area=(3360, "the city of Hanoi is about 3,360 km²"), updates=4),
        dict(title="Which parts of the road map are out of date?",
             frm="Chief, planning division, public works department",
             to="Road inventory team (you)",
             situation="The road inventory decides which farm-to-market roads get maintenance "
                       "money, and many small roads are missing from it. Your mappers can "
                       "redraw 40 map cells a month. They should start where there is most "
                       "road to draw.",
             question="Can super-resolved images show the mappers which cells hold the most "
                      "road? Many roads are narrower than a Sentinel-2 pixel.",
             scenario=dict(
                 decision_maker="Public works department, planning division",
                 decision="Which 160 m x 160 m cells the mappers redraw first",
                 budget="40 cells a month",
                 hit="a cell where roads cover at least 10 % of the ground",
                 cost_of_wasted_visit="half a mapper-day",
                 cost_of_missed_place="a road that stays off the inventory, and off the "
                                      "maintenance list, for a year: about 2 mapper-days' worth"),
             settings=dict(target=1, size=160, budget=40, hit_at=0.10, cw=0.5, cm=2),
             area=(3360, "the city of Hanoi is about 3,360 km²"), updates=1),
        dict(title="Where is the tree cover we must protect?",
             frm="Head, parks and green space office",
             to="Urban greening team (you)",
             situation="The city's heat action plan protects its last large groups of trees. "
                       "The office wants to survey the 20 greenest cells this year and declare "
                       "them protected.",
             question="Do we need super-resolution for this, or is free Sentinel-2 enough?",
             scenario=dict(
                 decision_maker="Parks and green space office, urban greening team",
                 decision="Which 80 m x 80 m cells get a tree survey and a protection order",
                 budget="20 surveys this year",
                 hit="a cell where trees cover at least 30 % of the ground",
                 cost_of_wasted_visit="1 surveyor-day",
                 cost_of_missed_place="a grove that stays unprotected: about 1 surveyor-day's "
                                      "worth"),
             settings=dict(target=3, size=80, budget=20, hit_at=0.30, cw=1, cm=1),
             area=(3360, "the city of Hanoi is about 3,360 km²"), updates=1),
    ],
    "ai4_fields": [
        dict(title="Which villages get the farmer-registry teams?",
             frm="Regional Executive Director, department of agriculture",
             to="Smallholder support programme (you)",
             situation="Seeds, fertiliser vouchers and crop insurance reach only registered "
                       "farmers, and the smallest farms are most often missing from the "
                       "registry. Your extension workers can visit 30 areas this season to "
                       "enrol farmers.",
             question="Can super-resolved images show where the small farms are, so the teams "
                      "go there first? Or would free Sentinel-2 do?",
             scenario=dict(
                 decision_maker="Department of agriculture regional office, smallholder support "
                                "programme",
                 decision="Which 500 m x 500 m squares get an extension-worker visit to enrol "
                          "small farms",
                 budget="30 visits this season",
                 hit="a square with at least 30 fields smaller than 0.25 ha",
                 cost_of_wasted_visit="1 extension-worker day",
                 cost_of_missed_place="about 30 smallholders not enrolled this season: about 2 "
                                      "worker-days' worth"),
             settings=dict(budget=30, size=500, small=2500, hit_at=30, cw=1, cm=2),
             area=(5000, "a large province is about 5,000 km²"), updates=2),
        dict(title="Where does the farm census need a second enumerator?",
             frm="Chief, agricultural statistics division, national statistics office",
             to="Census planning team (you)",
             situation="In the census of agriculture, one enumerator covers one square "
                       "kilometre. Squares with very many parcels need a second enumerator, "
                       "and the office can pay for 20. The last parcel count is ten years old.",
             question="Can satellite images count parcels well enough to choose those 20 "
                      "squares? Does super-resolution add anything to free Sentinel-2?",
             scenario=dict(
                 decision_maker="National statistics office, agricultural statistics division",
                 decision="Which 1 km squares get a second enumerator",
                 budget="20 extra enumerators",
                 hit="a square with at least 200 parcels (fields of any size)",
                 cost_of_wasted_visit="an enumerator sent where one was enough: 1",
                 cost_of_missed_place="a square counted late or badly: 1"),
             settings=dict(budget=20, size=1000, small=0, hit_at=200, cw=1, cm=1),
             area=(5000, "a large province is about 5,000 km²"), updates=1),
    ],
}
OWN_DECISION = "Our own decision (we write the brief)"


def _memo(b):
    return (f"<div style='{_CARD}'>"
            "<div style='color:#8a6d00; font-size:12px; letter-spacing:.5px'>MOCK BRIEF · "
            "invented for this workshop. The kind of decision is real; the office and the "
            "numbers are not.</div>"
            f"<div style='margin-top:6px'><b>From:</b> {b['frm']}<br><b>To:</b> {b['to']}<br>"
            f"<b>Subject:</b> {b['title']}</div>"
            f"<p style='margin:8px 0'>{b['situation']}</p>"
            f"<p style='margin:8px 0'><b>What I need from you:</b> {b['question']}</p>"
            "<p style='margin:8px 0 0 0'><b>Reply on one slide:</b> deploy, pilot or don't "
            "use; the numbers; your safeguards.</p></div>")


_OWN_MEMO = (f"<div style='{_CARD}'><b>Your own brief.</b> Pick a decision that someone in your "
             "agency really makes and that a map could inform. Fill in the fields below, then "
             "set the same budget and hit rule in part 3.</div>")


def mission(task):
    """Part 1: choose a mock brief (or write your own). The choice fills the scenario fields
    below it, the decision settings of part 3 and the area of part 5; everything stays
    editable."""
    kind = _kind(task)
    briefs = BRIEFS[kind]
    S["task"] = task
    choose = W.RadioButtons(options=[(b["title"], i) for i, b in enumerate(briefs)]
                            + [(OWN_DECISION, -1)], value=0, layout=W.Layout(width="100%"))
    memo = W.HTML()
    form = ask(*[(k, t, "text", briefs[0]["scenario"].get(k, "Team A"))
                 for k, t in SCENARIO_FIELDS], show=False)

    def on_choose(_=None):
        b = briefs[choose.value] if choose.value >= 0 else None
        S["brief"] = b
        ANSWERS["brief"] = b["title"] if b else OWN_DECISION
        memo.value = _memo(b) if b else _OWN_MEMO
        for key, field in form.fields.items():
            if key != "team":
                field.value = b["scenario"][key] if b else ""
        for apply in (S.get("apply_settings"), S.get("apply_area")):
            if b and apply:
                apply(b)
        for redraw in list(ANSWER_REFRESH.values()):
            redraw()
    choose.observe(on_choose, names="value")
    on_choose()
    ui = W.VBox([W.HTML("<b>Choose your brief</b>"), choose, memo,
                 W.HTML("<br><b>Your scenario</b> (from the brief; change what does not fit "
                        "your agency)"), form])
    ui.choose, ui.memo, ui.fields = choose, memo, form.fields
    UI["mission"] = UI["scenario"] = ui
    display(ui)


def scenario_dict():
    """The scenario as typed in part 1 (empty fields: '(not answered)')."""
    return {k: (ANSWERS.get(k) or "").strip() or "(not answered)" for k, _ in SCENARIO_FIELDS}


# ---- part 3: the bet and the decision --------------------------------------------------------

def _int_slider(value, lo, hi, step, text):
    return W.IntSlider(value=value, min=lo, max=hi, step=step, continuous_update=False,
                       description=text, layout=_WIDE, style=_LABEL)


def _cost(value, text):
    return W.BoundedFloatText(value=value, min=0, max=10000, step=0.5, description=text,
                              style=_LABEL)


def _list(items):
    """'a, b and c'."""
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _same_result_more_visits(preds, hit, k, labels):
    """How many visits each input needs to find what the best input finds in k visits."""
    means = {i: np.mean([expected_hits(pm, hit, k) for pm in np.atleast_2d(p)])
             for i, p in preds.items()}
    ref = "hr" if "hr" in preds else max(means, key=means.get)
    if means[ref] < 0.5:
        return "", {}
    need = {}
    for i, p in preds.items():
        if i != ref:
            n = [visits_needed(pm, hit, means[ref]) or len(hit) for pm in np.atleast_2d(p)]
            need[i] = int(np.median(n))
    more = [f"<b>{need[i]:,}</b> with {labels[i]}" for i in sorted(need, key=need.get)
            if need[i] > k]
    if more:
        more[0] = more[0].replace("</b> with", "</b> visits with")
    same = [labels[i] for i in need if need[i] <= k]
    text = (f"<b>Same result, more visits.</b> {labels[ref]} finds {_num(means[ref])} hits in "
            f"{k} visits. ")
    if more:
        text += f"To match it, you need about {_list(more)}. "
    if same:
        text += f"{_list(same)} {'does' if len(same) == 1 else 'do'} just as well."
    return text, {labels[i]: v for i, v in need.items()}


def _reading(res, k, labels, more, bets):
    """The result in plain words, for people who do not read charts every day."""
    items = []
    for n, name in enumerate(labels.values()):
        r = res.loc[name]
        spread = r["range over models"].replace("–", " to ")
        if n == 0:
            spread = f" ({spread}, depending on the model)" if spread else ""
            items.append(f"<b>{name}</b>: <b>{_num(r['hits'])}</b> of your {k} visits are "
                         f"hits{spread}.")
        else:
            items.append(f"<b>{name}</b>: <b>{_num(r['hits'])}</b>"
                         + (f" ({spread})." if spread else "."))
    items.append(f"No map (random picks): {_num(res.loc['random', 'hits'])}. Perfect "
                 f"knowledge: {_num(res.loc['perfect', 'hits'])}.")
    if more:
        items.append(more)
    if bets:
        items.append("<b>Your bets:</b> " + "; ".join(
            f"{n} {b} (result {_num(res.loc[n, 'hits'])})" for n, b in bets.items()) + ".")
    return (f"<div style='{_CARD}'><b>In plain words</b><ul style='margin:4px 0'>"
            + "".join(f"<li>{i}</li>" for i in items) + "</ul></div>")


def decision_panel(task):
    """Part 3: the settings of your decision, your bet and, after the reveal, the result. Every
    later change of a setting recomputes at once, and parts 3b to 6 follow. The places
    (blocks, cells or squares) are computed once per setting and kept."""
    kind = _kind(task)
    labels = _short(task)
    S.update(task=task, cache={}, revealed=False)
    brief = S.get("brief") or BRIEFS[kind][0]
    d = brief["settings"]
    if kind == "ifs_manila":
        budget = _int_slider(d["budget"], 5, 100, 5, "Budget (blocks you visit)")
        size = W.ToggleButtons(options=[("50 m", 50), ("100 m", 100), ("200 m", 200)],
                               value=d["size"], description="Block size", style=_buttons("80px"))
        hit_at = W.FloatSlider(value=d["hit_at"], min=0.05, max=0.9, step=0.05,
                               continuous_update=False, readout_format=".0%", layout=_WIDE,
                               style=_LABEL, description="Hit = informal share at least")
        w = dict(budget=budget, size=size, hit_at=hit_at)
        unit_controls = [size]

        def places():
            return ifs_units(task, cell_m=size.value)

        def settings():
            return {"block": f"{size.value} m", "hit": f"informal share ≥ {hit_at.value:.0%}"}

        def title():
            return f"Visit {budget.value} blocks of {size.value} m: how many are hits?"
        place_word = "blocks"
    elif kind == "hanoi_landcover":
        target = W.Dropdown(options=[(n, i) for i, n in enumerate(LC_NAMES)]
                            + [("built-up (building + road)", (0, 1)),
                               ("green (tree + low vegetation)", (3, 4)),
                               ("buildings in farmland (cells at least half cropland)",
                                FARM_BUILDINGS)],
                            value=d["target"], description="Land cover you look for",
                            layout=_WIDE, style=_LABEL)
        size = W.ToggleButtons(options=[("40 m", 40), ("80 m", 80), ("160 m", 160)],
                               value=d["size"], description="Cell size", style=_buttons("80px"))
        budget = _int_slider(d["budget"], 5, 100, 5, "Budget (cells you visit)")
        hit_at = W.FloatSlider(value=d["hit_at"], min=0.05, max=0.9, step=0.05,
                               continuous_update=False, readout_format=".0%", layout=_WIDE,
                               style=_LABEL, description="Hit = share of the cell at least")
        w = dict(target=target, size=size, budget=budget, hit_at=hit_at)
        unit_controls = [target, size]

        def what():
            name = next(n for n, v in target.options if v == target.value)
            return name.split(" (cells")[0]

        def places():
            return lc_units(task, cell_m=size.value, target=target.value)

        def settings():
            extra = " (in cells at least half cropland)" if target.value == FARM_BUILDINGS else ""
            return {"looking for": what(), "cell": f"{size.value} m",
                    "hit": f"{what().split(' in farmland')[0]} ≥ {hit_at.value:.0%} of the cell"
                           + extra}

        def title():
            return f"Visit {budget.value} cells of {size.value} m ({what()}): how many are hits?"
        place_word = "cells"
    else:
        budget = _int_slider(d["budget"], 5, 100, 5, "Budget (squares you visit)")
        size = W.ToggleButtons(options=[("250 m", 250), ("500 m", 500), ("1 km", 1000)],
                               value=d["size"], description="Square size", style=_buttons("80px"))
        small = W.ToggleButtons(options=[("all fields", 0), ("< 0.1 ha", 1000),
                                         ("< 0.25 ha", 2500), ("< 0.5 ha", 5000)],
                                value=d["small"], description="Count fields",
                                style=_buttons("90px"))
        hit_at = _int_slider(d["hit_at"], 1, 400, 1, "Hit = at least this many fields")
        w = dict(budget=budget, size=size, small=small, hit_at=hit_at)
        unit_controls = [size, small]

        def places():
            return ai4_units(task, cell_m=size.value, small_m2=small.value or None)

        def settings():
            what = "fields" if not small.value else f"fields < {small.value / 10000:g} ha"
            return {"square": f"{size.value} m", "hit": f"≥ {hit_at.value} {what}"}

        def title():
            return f"Visit {budget.value} squares of {size.value} m: how many are hits?"
        place_word = "squares"
    w["cw"], w["cm"] = _cost(d["cw"], "Cost of a wasted visit"), _cost(d["cm"],
                                                                         "Cost of a missed place")
    controls = list(w.values())

    status = W.HTML()
    bets = {k: W.IntSlider(value=0, min=0, max=budget.value, continuous_update=False,
                           description=f"Hits with {labels[k]}", layout=_WIDE, style=_LABEL)
            for k in task.inputs}
    reveal = W.Button(description="Lock in our bet and show the result", icon="unlock",
                      button_style="primary", layout=W.Layout(width="320px"))
    skip = W.Button(description="Show the result without a bet",
                    layout=W.Layout(width="260px"))
    bet_head = W.HTML()
    bet_box = W.VBox([bet_head, *bets.values(), W.HBox([reveal, skip])],
                     layout=W.Layout(border="1px solid #007DB7", padding="8px 12px",
                                     margin="10px 0"))
    chart = W.Image(format="png", layout=W.Layout(max_width="100%"))
    reading = W.HTML()
    table = W.HTML()
    result = W.VBox([])

    def bet_text():
        bet_head.value = (
            f"<b>Your bet.</b> Of your {budget.value} visits, how many will be hits? Agree on "
            "one number per kind of image, then lock it in.")

    def compute(_=None):
        if S.get("hold"):
            return
        key = tuple(c.value for c in unit_controls)
        try:
            for b in bets.values():
                b.max = budget.value
            bet_text()
            if key not in S["cache"]:
                status.value = _note(f"Cutting the map into {place_word} ... (the first time "
                                     "for a setting can take up to 20 seconds)")
                (units, preds), _, said = _run(places)
                S["cache"][key] = (units, preds, said)
            units, preds, said = S["cache"][key]
            hit = units.truth.values >= hit_at.value
            res, _, said2 = _run(decide, units, preds, hit, budget.value, w["cw"].value,
                                 w["cm"].value, labels=labels)
            more, need = _same_result_more_visits(preds, hit, min(budget.value, len(hit)), labels)
            S.update(units=units, preds=preds, hit=hit, res=res, budget=budget.value,
                     target=target.value if kind == "hanoi_landcover" else None,
                     hit_at=hit_at.value, visits_needed=need,
                     cost_wasted=w["cw"].value, cost_missed=w["cm"].value, title=title(),
                     settings={"budget": budget.value, **settings(),
                               "cost of a wasted visit": f"{w['cw'].value:g}",
                               "cost of a missed place": f"{w['cm'].value:g}"},
                     place_word=place_word)
            status.value = _pre("\n".join(x for x in (said, said2) if x))
            if not S["revealed"]:
                return
            guess = {labels[k]: b.value for k, b in bets.items()} if S.get("bets") else None
            _, pngs, _ = _run(plot_decision, res, budget.value, title(), guess)
            chart.value = pngs[0]
            reading.value = _reading(res, budget.value, labels, more, S.get("bets"))
            shown = res if len(np.atleast_2d(next(iter(preds.values())))) > 1 else res.drop(
                columns="range over models")
            table.value = shown.to_html()
            result.children = (chart, reading, table)
        except Exception as exc:  # say what went wrong instead of failing silently
            status.value = _error(exc)
            return
        for redraw in list(REFRESH.values()):
            try:
                redraw()
            except Exception:  # a later part must not break the decision cell
                pass

    def on_reveal(button):
        if button is reveal:
            S["bets"] = {labels[k]: b.value for k, b in bets.items()}
            ANSWERS["bets"] = dict(S["bets"])
        S["revealed"] = True
        for b in bets.values():
            b.disabled = True
        reveal.disabled = skip.disabled = True
        reveal.description = "Bet locked in" if S.get("bets") else "No bet placed"
        compute()
    reveal.on_click(on_reveal)
    skip.on_click(on_reveal)

    def apply_settings(b):
        """Set the controls to a brief's settings (one recomputation at the end)."""
        S["hold"] = True
        try:
            for name, value in b["settings"].items():
                if name in w:
                    w[name].value = value
        finally:
            S["hold"] = False
        compute()
    S["apply_settings"] = apply_settings

    for c in controls:
        c.observe(compute, names="value")
    ui = W.VBox([W.HTML("<b>Settings of your decision</b> (from your brief; change them to "
                        "fit your case). Costs are in your own units, such as staff-days. "
                        "Only the ratio matters."),
                 *controls, status, bet_box, result])
    ui.controls = {c.description: c for c in controls}
    ui.w, ui.bets, ui.reveal, ui.skip, ui.result = w, bets, reveal, skip, result
    UI["decision"] = ui
    display(ui)
    compute()


def current():
    """The current decision of part 3: units (one row per place), preds ({input: array
    (models, places)}), hit (bool per place) and res (the table)."""
    return S["units"], S["preds"], S["hit"], S["res"]


def peek(value):
    """Show a result only once the bet of part 3 is revealed (so Run all spoils nothing)."""
    if S.get("revealed"):
        return value
    print("Reveal the result in part 3 first, then run this cell again.")


# ---- part 3b: other budgets ------------------------------------------------------------------

def sweep_view():
    """Share of hits for budgets from 5 to 100; follows the settings of part 3."""
    if not _need_decision():
        return

    def build():
        chart = W.Image(format="png", layout=W.Layout(max_width="100%"))

        def draw():
            _, pngs, _ = _run(sweep, S["preds"], S["hit"], labels=_short(S["task"]),
                              title=f"Share of visits that are hits ({S['place_word']}, "
                                    f"{S['settings']['hit']})")
            chart.value = pngs[0]
        draw()
        UI["sweep"] = chart
        return [chart], draw
    _gated("sweep", build)


# ---- part 4: which places, who is left out, and the failures ---------------------------------

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


_WHERE = {"ifs_manila": ("group", "city"), "hanoi_landcover": ("group", "source image"),
          "ai4_fields": ("scene", "area")}


def _where_html(task):
    by, word = _WHERE[_kind(task)]
    t = where_table(S["units"], S["preds"], S["hit"], S["budget"], by=by, labels=_short(task))
    visits = [c for c in t.columns if c.startswith("visits")]
    left_out = [str(a) for a, r in t.iterrows() if r["true hits"] >= 5 and r[visits].max() == 0]
    note = (f"<br><b>Left out by every kind of image:</b> {', '.join(left_out)}."
            if left_out else "")
    return (f"<b>Where would your visits go?</b> One row per {word}: its {S['place_word']}, "
            f"its true hits, and the visits each kind of image sends there (of {S['budget']}). "
            f"Many hits and no visits means the {word} is left out.{note}" + _html_table(t))


def picks_view(max_shown=16):
    """Where the visits go, how much the lists overlap, the places each input would pick, its
    failures and one place in detail. Follows the settings of part 3."""
    if not _need_decision():
        return

    def build():
        task = S["task"]
        labels = _short(task)
        shown = [k for k in task.inputs if task.has_image[k]]
        where = W.HTML()
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
                where.value = _where_html(task)
                overlap.value = _html_table(overlap_table(S["preds"], S["budget"], labels=labels))
                picks, false, missed = lists()
                name, word = labels[pick.value], S["place_word"]
                note = (f" (the first {max_shown} of {len(picks)})"
                        if len(picks) > max_shown else "")
                pngs = (_gallery(task, picks[:max_shown], on.value,
                                 f"The {S['budget']} {word} you would visit using {name}{note}")
                        + _gallery(task, false, on.value,
                                   f"{name}: highest-scoring {word} that are NOT hits")
                        + _gallery(task, missed, on.value,
                                   f"Clear hits that {name} would NOT visit"))
                galleries.children = _images(pngs)
                draw_detail()
            except Exception as exc:
                status.value = _error(exc)
        for c in (pick, on):
            c.observe(draw, names="value")
        for c in (which, number):
            c.observe(draw_detail, names="value")
        finds = ask(("RESCUE", "A place where super-resolution changed the decision for the "
                     "better (which, and why)", "text"),
                    ("FAILURE", "A failure worth telling the room about (where, and what went "
                     "wrong)", "text"), show=False)
        ui = W.VBox([where,
                     W.HTML("<br><b>Do the images pick the same places?</b> Share of picks "
                            "that two kinds of image have in common (100 % = the same list)"),
                     overlap,
                     W.HTML("<br><b>The places themselves</b> (green frame = hit, red frame = "
                            "wasted visit)"),
                     pick, on, status, galleries,
                     W.HTML("<br><b>One place in detail</b> (for the kind of image picked above)"),
                     which, number, detail, finds])
        ui.pick, ui.on, ui.which, ui.number, ui.galleries, ui.detail, ui.where = (
            pick, on, which, number, galleries, detail, where)
        UI["picks"], UI["finds"] = ui, finds
        draw()
        return [ui], draw
    _gated("picks", build)


# ---- part 5: is it worth the money? ----------------------------------------------------------

PRICE_NOTE = ("Starting prices: real images about USD 4–19 per km² at list price (Sessions 1 "
              "and 3); super-resolution about USD 0.004–0.013 per km² in computing (Session 4); "
              "Sentinel-2 free. Change them to yours.")


def cost_view():
    """Part 5: what the images would cost for your whole area, and a mixed strategy: screen
    everything with a cheap input, buy real images only where it flags, then pick the visits.
    Follows the settings of part 3."""
    if not _need_decision():
        return

    def build():
        task = S["task"]
        labels = _short(task)
        has_hr = "hr" in task.inputs
        b = S.get("brief") or BRIEFS[_kind(task)][0]
        area = W.BoundedFloatText(value=b["area"][0], min=1, max=1e8, step=10,
                                  description="Area you must watch (km²)", style=_LABEL)
        area_note = W.HTML(_note(f"({b['area'][1]})", "#777"))
        updates = W.ToggleButtons(options=[("once a year", 1), ("each season", 2),
                                           ("every quarter", 4), ("every month", 12)],
                                  value=b["updates"], description="A fresh map",
                                  style=_buttons("110px"))
        price_hr = W.BoundedFloatText(value=10, min=0, max=1000, step=1, style=_LABEL,
                                      description="Real images, USD per km²")
        price_sr = W.BoundedFloatText(value=0.01, min=0, max=100, step=0.005, style=_LABEL,
                                      description="Super-resolution, USD per km²")
        cheap = [k for k in task.inputs if k != "hr"]
        screen = W.ToggleButtons(options=[(labels[k], k) for k in cheap], value=cheap[-1],
                                 description="Screen everything with", style=_buttons("120px"))
        share = W.IntSlider(value=5, min=1, max=30, continuous_update=False, layout=_WIDE,
                            style=_LABEL, description="Buy real images for the top (%)")
        chart = W.Image(format="png", layout=W.Layout(max_width="100%"))
        reading = W.HTML()
        status = W.HTML()

        def apply_area(brief):
            area.value, updates.value = brief["area"][0], brief["updates"]
            area_note.value = _note(f"({brief['area'][1]})", "#777")
        S["apply_area"] = apply_area

        def draw(_=None):
            try:
                status.value = ""
                res, preds, hit, k = S["res"], S["preds"], S["hit"], S["budget"]
                k = min(k, len(hit))
                a = area.value * updates.value
                rows = [dict(name=f"{labels[i]} only", hits=float(res.loc[labels[i], "hits"]),
                             cost=0 if i == "s2" else a * price_sr.value, colour=COLOURS[i])
                        for i in cheap]
                lines = []
                if has_hr:
                    m = max(k, int(round(share.value / 100 * len(hit))))
                    mixed = float(np.mean([screen_then_confirm(ps, ph, hit, k, m) for ps, ph in zip(
                        np.atleast_2d(preds[screen.value]), np.atleast_2d(preds["hr"]))]))
                    bill = a * share.value / 100 * price_hr.value + (
                        0 if screen.value == "s2" else a * price_sr.value)
                    full = float(res.loc[labels["hr"], "hits"])
                    rows.append(dict(name=f"{labels[screen.value]} to screen, real images\n"
                                          f"for the top {share.value} %", hits=mixed, cost=bill,
                                     colour="#f2a900"))
                    rows.append(dict(name="Real images everywhere", hits=full,
                                     cost=a * price_hr.value, colour=COLOURS["hr"]))
                    alone = float(res.loc[labels[screen.value], "hits"])
                    lines.append(
                        f"<b>Screen, then buy.</b> {labels[screen.value]} screens every "
                        f"{S['place_word'][:-1]}. You buy real images for the top "
                        f"{share.value} % and choose your {k} visits there. Result: "
                        f"<b>{_num(mixed)} hits</b> ({labels[screen.value]} alone: "
                        f"{_num(alone)}; real images everywhere: {_num(full)}). Imagery bill: "
                        f"<b>USD {bill:,.0f}</b> a year instead of USD "
                        f"{a * price_hr.value:,.0f}.")
                    S["strategy"] = [
                        f"{labels[screen.value]} screens, real images for the top "
                        f"{share.value} %: {_num(mixed)} hits, USD {bill:,.0f} a year",
                        f"real images everywhere: {_num(full)} hits, USD "
                        f"{a * price_hr.value:,.0f} a year",
                        f"{labels[screen.value]} only: {_num(alone)} hits, USD "
                        f"{0 if screen.value == 's2' else a * price_sr.value:,.0f} a year"]
                else:
                    best = max(cheap, key=lambda i: res.loc[labels[i], "hits"])
                    lines.append(
                        "<b>This dataset has no real high-resolution images</b>, so buying "
                        "them cannot be tested here. For scale: real images of your area "
                        f"would cost about <b>USD {a * price_hr.value:,.0f}</b> a year; "
                        f"super-resolution about USD {a * price_sr.value:,.0f}.")
                    S["strategy"] = [
                        f"{labels[best]}: {_num(res.loc[labels[best], 'hits'])} hits, USD "
                        f"{a * price_sr.value:,.0f} a year",
                        f"Sentinel-2: {_num(res.loc[labels['s2'], 'hits'])} hits, free",
                        f"real images (not tested): USD {a * price_hr.value:,.0f} a year"]
                lines.append("<span style='color:#777'>Hits come from this dataset's sample; the "
                             "bill is for your whole area. Read the pattern, not the decimals. "
                             + PRICE_NOTE + "</span>")
                scale = (f"{area.value:,.0f} km², "
                         f"{next(n for n, v in updates.options if v == updates.value)}")
                S["strategy_scale"] = scale
                _, pngs, _ = _run(plot_strategies, rows, k, scale)
                chart.value = pngs[0]
                reading.value = (f"<div style='{_CARD}'>"
                                 + "".join(f"<p style='margin:6px 0'>{x}</p>" for x in lines)
                                 + "</div>")
                for redraw in list(ANSWER_REFRESH.values()):
                    redraw()
            except Exception as exc:
                status.value = _error(exc)
        controls = [area, updates, price_hr, price_sr] + ([screen, share] if has_hr else [])
        for c in controls:
            c.observe(draw, names="value")
        ui = W.VBox([W.HBox([area, area_note]), updates, price_hr, price_sr,
                     *([W.HTML("<br><b>A mixed strategy: screen, then buy</b>"), screen, share]
                       if has_hr else []), status, chart, reading])
        ui.controls = {c.description: c for c in controls}
        ui.chart, ui.reading = chart, reading
        UI["cost"] = ui
        draw()
        return [ui], draw
    _gated("cost", build)


# ---- going further: the SR service -----------------------------------------------------------

OWN_PLACE = "My own place"
SR_CLIENT = "sr-client[geo,viz] @ git+https://github.com/adb-sr/sr-client@v0.1.0"


def _secret(name):
    """An API setting from the environment or from Colab's Secrets panel ('' if not there)."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        from google.colab import userdata
        return userdata.get(name) or ""
    except Exception:
        return ""


def sr_connect(ready_made, default_lat, default_lon):
    """Type the API key and the service address from your team card (or keep them in Colab's
    Secrets as SR_API_KEY and SR_API_URL), press Connect, then choose an area. Nothing here
    runs before you press the button, so Run all never waits for a key."""
    key = W.Password(value=os.environ.get("SR_API_KEY", ""), description="API key (srk_...)",
                     layout=_WIDE, style=_LABEL)
    url = W.Text(value=os.environ.get("SR_API_URL", ""), description="Service address",
                 layout=_WIDE, style=_LABEL, placeholder="https://...")
    go = W.Button(description="Connect", icon="plug", button_style="primary",
                  layout=W.Layout(width="220px"))
    status = W.HTML()
    panel = W.VBox([])

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
            status.value = _note(f"Connected. Budget of this key: {left}", "#1a7f37")
            S["sr"] = sr
            panel.children = (sr_panel(sr, ready_made, default_lat, default_lon, show=False),)
        except Exception as exc:
            status.value = _note(f"Could not connect: {_html.escape(str(exc))}. Check the key "
                                 "and the address on your team card.", "#b00020")
        finally:
            go.disabled = False
    go.on_click(on_go)
    ui = W.VBox([key, url, go, status, panel])
    ui.key, ui.url, ui.go, ui.status, ui.panel = key, url, go, status, panel
    UI["sr_connect"] = ui
    display(ui)


def sr_panel(sr, ready_made, default_lat, default_lon, show=True):
    """Pick a ready-made area (or your own point), send it with one button and look at the
    result with sliders. The button waits until the job is done (3–6 minutes for a new area)."""
    from sr_client import SRError
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
    if show:
        display(ui)
    return ui


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




# ---- part 6: your recommendation -------------------------------------------------------------

USES = ["to decide where to look first", "as evidence to act on", "not at all"]
SAFEGUARDS = [
    "A person checks every flagged place before anyone acts",
    "Never the only evidence for enforcement, eviction or eligibility",
    "Tested first on places our staff know well",
    "Maps are labelled as AI-enhanced, with the image date",
    "People and local governments can contest a flag",
]


def card_text():
    task = S["task"]

    def said(key):
        v = ANSWERS.get(key)
        return v if v not in ("", None, []) else "(not answered)"
    lines = ["=" * 78, f"TASK      {task.meta['title']}",
             f"BRIEF     {ANSWERS.get('brief', '(none)')}"]
    for k, v in scenario_dict().items():
        lines.append(f"{k.replace('_', ' ').upper():<22}{v}")
    lines += ["-" * 78, "SETTINGS  " + ", ".join(f"{k} {v}" for k, v in S["settings"].items()),
              "", S["res"][[c for c in ("hits", "range over models", "hit rate", "missed places",
                                        "cost") if S["res"][c].astype(str).str.len().max()]]
              .to_string(), ""]
    need = {n: v for n, v in (S.get("visits_needed") or {}).items() if v > S["budget"]}
    if need:
        lines.append("SAME RESULT, MORE VISITS: " + ", ".join(
            f"{v:,} visits with {n}" for n, v in sorted(need.items(), key=lambda x: x[1])))
    if S.get("bets"):
        lines.append("OUR BETS: " + ", ".join(
            f"{n} {b} (result {S['res'].loc[n, 'hits']:g})" for n, b in S["bets"].items()))
    if S.get("strategy"):
        lines.append(f"MONEY ({S['strategy_scale']}):")
        lines += [f"  - {x}" for x in S["strategy"]]
    lines.append("-" * 78)
    lines.append(f"{'recommendation:':<28}{said('VERDICT')}")
    lines.append(f"{'we would use the map:':<28}{said('USE')}")
    guards = ANSWERS.get("SAFEGUARDS") or []
    lines.append(f"{'safeguards:':<28}" + ("(none ticked)" if not guards else ""))
    lines += [f"  - {g}" for g in guards]
    for key, text in (("CHANGE_MIND", "what would change our mind"), ("RESCUE", "where SR helped"),
                      ("FAILURE", "a failure")):
        lines.append(f"{text + ':':<28}{said(key)}")
    lines.append("=" * 78)
    return "\n".join(lines)


def slide_card(fname="my_slide_chart.png"):
    """Part 6: your recommendation, then a card with everything the slide needs; it follows the
    decision settings and your answers. The button downloads the chart."""
    if not _need_decision():
        return

    def build():
        form = ask(("VERDICT", "Your recommendation to the decision-maker",
                    ["deploy", "pilot", "don't use"]),
                   ("USE", "How would you use the map?", USES),
                   ("SAFEGUARDS", "Safeguards you insist on (tick all that apply)",
                    "checks", SAFEGUARDS),
                   ("CHANGE_MIND", "What would change your mind?", "text",
                    "a test on 50 places in our own city, checked in the field"), show=False)
        card = W.HTML()
        chart = W.Image(format="png", layout=W.Layout(max_width="100%"))
        button = W.Button(description=f"Download the chart ({fname})", icon="download",
                          layout=W.Layout(width="320px"))
        note = W.HTML()

        def update(_=None):
            card.value = _pre(card_text())
            guess = S.get("bets")
            fig = plot_decision(S["res"], S["budget"], scenario_dict()["decision"], guess)
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
        ANSWER_REFRESH["card"] = update
        update()
        ui = W.VBox([form, W.HTML("<b>Your card</b> (copy it onto your team slide)"), card,
                     chart, button, note])
        ui.card, ui.chart, ui.button, ui.form = card, chart, button, form
        UI["card"], UI["verdict"] = ui, form
        return [ui], update
    _gated("card", build)
