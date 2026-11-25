# ---- controls shared by the workshop notebooks: answers that save themselves, figures as images
import html as _html
import io

import ipywidgets as W
from IPython.display import display

ANSWERS = {}    # your answers; saved as soon as you type or click
UI = {}         # the controls of each step (used for testing)
_WIDE = W.Layout(width="520px")
_LABEL = {"description_width": "150px"}


def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=90, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _note(text, colour="#333"):
    return f"<div style='color:{colour}; line-height:1.5'>{text}</div>"


def _pre(text):
    return f"<pre style='margin:4px 0; line-height:1.35'>{_html.escape(text)}</pre>"


# ---- answers that save themselves ------------------------------------------------------------

def ask(*questions):
    """Each question is (key, text, kind): kind is "text" or a list of choices. The answer
    is saved in ANSWERS the moment it changes; nothing to run."""
    rows = []
    for key, text, kind in questions:
        saved = W.HTML()
        if kind == "text":
            field = W.Text(value=ANSWERS.get(key, ""), placeholder="type here",
                           continuous_update=True, layout=_WIDE)
        else:
            field = W.ToggleButtons(options=list(kind), value=ANSWERS.get(key),
                                    style={"button_width": "auto"})

        def on_change(change, key=key, saved=saved):
            ANSWERS[key] = change["new"]
            saved.value = _note("saved ✓", "#1a7f37") if change["new"] not in ("", None) else ""
        field.observe(on_change, names="value")
        rows.append(W.VBox([W.HTML(f"<b>{text}</b>"), W.HBox([field, saved])],
                           layout=W.Layout(margin="6px 0 10px 0")))
        rows[-1].field = field
    box = W.VBox(rows, layout=W.Layout(border="1px solid #007DB7", padding="8px 12px",
                                       margin="8px 0"))
    box.fields = [r.field for r in rows]
    display(box)
    return box
