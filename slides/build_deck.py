"""Build the conference deck for "Who Can Call This MCP Tool?".

MCP Dev Summit Toronto - 2026-10-06 - Brian Benz.

Generates slides/who-can-call-this-mcp-tool.pptx, then re-opens the file and
verifies it against the deck's own contract. Re-running produces the same deck.

Run with the deck virtual environment:

    slides\\.venv\\Scripts\\python.exe slides\\build_deck.py

Bare `python` on the authoring machine resolves to a non-functional Microsoft
Store stub, so always invoke the interpreter by path.
"""

from __future__ import annotations

import io
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import segno
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
OUT_PATH = HERE / "who-can-call-this-mcp-tool.pptx"

# The talk date, used as a fixed document timestamp so rebuilds are
# byte-identical rather than differing only by when they were run.
STAMP = datetime(2026, 10, 6, 15, 40, tzinfo=timezone.utc)

# The repository has no git remote. This placeholder is deliberately obvious;
# it must be replaced before the event, and the QR code regenerated.
REPO_URL = "https://github.com/<owner>/<repo>"

# --------------------------------------------------------------------------
# Design tokens
#
# Light background, dark text: the session is at 15:40 in a lit ballroom.
# RED IS RESERVED. It means "outside your trust boundary" and nothing else.
# --------------------------------------------------------------------------

BG = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x11, 0x18, 0x27)
MUTED = RGBColor(0x37, 0x41, 0x51)
ACCENT = RGBColor(0x1E, 0x40, 0xAF)
ACCENT_SOFT = RGBColor(0xEF, 0xF6, 0xFF)
RESERVED_RED = RGBColor(0x99, 0x1B, 0x1B)
RED_SOFT = RGBColor(0xFE, 0xF2, 0xF2)
RULE = RGBColor(0xD1, 0xD5, 0xDB)
PANEL = RGBColor(0xF3, 0xF4, 0xF6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "Segoe UI"
MONO = "Consolas"

TITLE_PT = 40
BODY_PT = 28
FLOOR_PT = 24

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
MARGIN = Inches(0.6)
CONTENT_W = Inches(12.133)
# Nothing important below this line: projector crop plus the front row's heads.
SAFE_BOTTOM = Inches(6.3)


@dataclass
class SlideSpec:
    """Bookkeeping so the final report can describe what was built."""

    number: int
    title: str
    purpose: str
    hidden: bool = False
    body_words: int = 0
    notes: str = field(default="", repr=False)


SPECS: list[SlideSpec] = []


# --------------------------------------------------------------------------
# Low-level helpers
# --------------------------------------------------------------------------


def _style(run, size: int, *, bold: bool = False, color: RGBColor = INK,
           name: str = FONT, italic: bool = False) -> None:
    """Every run gets an explicit face, size and colour.

    An unset size inherits from the layout and reads as a violation when the
    deck is audited, so nothing is left to inheritance.
    """
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = name
    run.font.color.rgb = color


def _new_slide(prs: Presentation) -> "Slide":
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG
    return slide


def _textbox(slide, left, top, width, height):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    return box, tf


def add_title(slide, text: str, *, top=Inches(0.5), size: int = TITLE_PT,
              color: RGBColor = INK) -> None:
    box, tf = _textbox(slide, MARGIN, top, CONTENT_W, Inches(1.0))
    box.name = "deck-title"
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    _style(run, size, bold=True, color=color)


def add_paragraphs(tf, lines, *, size: int = BODY_PT, space_after: int = 10,
                   first_is_existing: bool = True) -> None:
    """lines: list of (text, {bold, color, size, name, italic, space_before})."""
    for idx, (text, opts) in enumerate(lines):
        if idx == 0 and first_is_existing:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.space_after = Pt(opts.get("space_after", space_after))
        if "space_before" in opts:
            p.space_before = Pt(opts["space_before"])
        segments = text if isinstance(text, list) else [(text, {})]
        for seg_text, seg_opts in segments:
            run = p.add_run()
            run.text = seg_text
            merged = {**opts, **seg_opts}
            _style(
                run,
                merged.get("size", size),
                bold=merged.get("bold", False),
                color=merged.get("color", INK),
                name=merged.get("name", FONT),
                italic=merged.get("italic", False),
            )


def set_hanging_indent(paragraph, indent_in: float = 0.42) -> None:
    """Wrapped list text aligns under the text, not under the number."""
    emu = str(int(indent_in * 914400))
    pPr = paragraph._p.get_or_add_pPr()
    pPr.set("marL", emu)
    pPr.set("indent", "-" + emu)


def add_notes(slide, text: str) -> None:
    slide.notes_slide.notes_text_frame.text = text


def hide(slide) -> None:
    slide._element.set("show", "0")


def add_rounded_box(slide, left, top, width, height, *, fill, line,
                    text_lines, line_width=Pt(2.25)):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top,
                                   width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = line_width
    shape.shadow.inherit = False
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.12)
    tf.margin_right = Inches(0.12)
    tf.margin_top = Inches(0.04)
    tf.margin_bottom = Inches(0.04)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for idx, (text, opts) in enumerate(text_lines):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        p.space_after = Pt(0)
        run = p.add_run()
        run.text = text
        _style(run, opts.get("size", FLOOR_PT), bold=opts.get("bold", False),
               color=opts.get("color", INK), italic=opts.get("italic", False))
    return shape


def add_table(slide, rows_data, left, top, width, col_widths, *,
              header_fill=PANEL, size: int = FLOOR_PT, row_height=Inches(0.62),
              emphasis_row: int | None = None):
    rows = len(rows_data)
    cols = len(rows_data[0])
    shape = slide.shapes.add_table(rows, cols, left, top, width,
                                   row_height * rows)
    table = shape.table
    table.first_row = False
    table.horz_banding = False
    for i, w in enumerate(col_widths):
        table.columns[i].width = w
    for r, row in enumerate(rows_data):
        table.rows[r].height = row_height
        for c, cell_text in enumerate(row):
            cell = table.cell(r, c)
            cell.margin_left = Inches(0.10)
            cell.margin_right = Inches(0.10)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if r == 0:
                cell.fill.fore_color.rgb = header_fill
            elif emphasis_row is not None and r == emphasis_row:
                cell.fill.fore_color.rgb = ACCENT_SOFT
            else:
                cell.fill.fore_color.rgb = WHITE
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.space_after = Pt(0)
            bold = r == 0 or (emphasis_row is not None and r == emphasis_row)
            colour = INK
            if emphasis_row is not None and r == emphasis_row:
                colour = ACCENT
            run = p.add_run()
            run.text = cell_text
            _style(run, size, bold=bold, color=colour)
    return shape


def qr_stream(url: str) -> io.BytesIO:
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="png", scale=12, border=2,
                                    dark="111827", light="ffffff")
    buf.seek(0)
    return buf


# --------------------------------------------------------------------------
# Shared content, taken from the repository and not from memory
# --------------------------------------------------------------------------

LAYERS_TABLE = [
    ["Layer", "Owner", "What it denies", "Cannot answer"],
    ["MCP client", "Not you", "A declined call", "Whether they may"],
    ["Auth server", "Your IdP", "PKCE downgrade", "About this order"],
    ["MCP server", "You", "Audience and object", "Human intent"],
    ["Upstream API", "You", "A forwarded token", "Who typed it"],
    ["Foundry model", "You", "Nothing. It advises.", "Everything"],
]

# Sized so every cell fits on ONE line at 24pt. A wrapped cell makes the row
# grow, PowerPoint pushes the table down, and it collides with the footer.
LAYER_COLS = [Inches(2.6), Inches(1.8), Inches(4.0), Inches(3.733)]


def build() -> Presentation:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # ---------------- 1 - Title ----------------
    s = _new_slide(prs)
    box, tf = _textbox(s, MARGIN, Inches(2.05), CONTENT_W, Inches(3.2))
    add_paragraphs(tf, [
        ("Who Can Call This MCP Tool?", {"size": 54, "bold": True,
                                         "space_after": 14}),
        ("OAuth, Resource Binding, and Runtime Policy",
         {"size": 32, "color": MUTED, "space_after": 34}),
        ("Brian Benz", {"size": 28, "bold": True, "space_after": 6}),
        ("MCP Dev Summit Toronto  \u00b7  6 October 2026",
         {"size": 26, "color": MUTED}),
    ])
    add_notes(s, (
        "Segment 1 - 00:00-02:00. Stop-time 02:00. Window: Slides.\n\n"
        "Start the timer at your first word. Do not demo here, and do not "
        "apologise for the size of the topic.\n\n"
        "NEXT WINDOW: stay on slides through slide 4."
    ))
    SPECS.append(SlideSpec(1, "Title", "Session, speaker, event. Nothing else."))

    # ---------------- 2 - The question ----------------
    s = _new_slide(prs)
    add_title(s, "Someone builds an MCP server")
    box, tf = _textbox(s, MARGIN, Inches(1.75), CONTENT_W, Inches(2.0))
    add_paragraphs(tf, [
        ([("It has a tool called ", {}),
          ("refund_order", {"name": MONO}),
          (". It works. Money moves.", {})], {"space_after": 16}),
        ("Then someone asks: who can call this tool?",
         {"bold": True, "space_after": 0}),
    ])
    box, tf = _textbox(s, Inches(1.0), Inches(3.9), Inches(11.4), Inches(1.6))
    add_paragraphs(tf, [
        ("\u2014  \u201cThe user signed in.\u201d", {"color": MUTED,
                                                     "space_after": 6}),
        ("\u2014  \u201cThere\u2019s an approval dialog.\u201d",
         {"color": MUTED, "space_after": 6}),
        ("\u2014  \u201cIt\u2019s only on the internal server.\u201d",
         {"color": MUTED, "space_after": 0}),
    ])
    box, tf = _textbox(s, MARGIN, Inches(5.55), CONTENT_W, Inches(0.70))
    add_paragraphs(tf, [
        ("None of them answers the question.", {"bold": True, "size": 32}),
    ])
    add_notes(s, (
        "Segment 1 - 00:00-02:00. Stop-time 02:00. Window: Slides.\n\n"
        "\"It works - the model calls it, money moves, everyone's happy. Then "
        "someone asks the question in the title: who can call this tool?\"\n\n"
        "Those are three real things. None of them is an answer to the "
        "question.\n\n"
        "NEXT WINDOW: stay on slides."
    ))
    SPECS.append(SlideSpec(2, "The question",
                           "Sets up the title question and the three usual "
                           "non-answers."))

    # ---------------- 3 - Three different questions ----------------
    s = _new_slide(prs)
    add_title(s, "Three different questions")
    rows = [
        ("Authentication", "Who are you?", "The authorization server", False),
        ("Approval", "Did the human mean it?",
         "The client \u2014 not yours", False),
        ("Authorization",
         "May this principal do this, to this object, now?",
         "Nobody, unless you write it", True),
    ]
    y = Inches(1.62)
    for label, question, owner, emphasise in rows:
        h = Inches(1.04)
        fill = ACCENT_SOFT if emphasise else WHITE
        line = ACCENT if emphasise else RULE
        shape = add_rounded_box(
            s, MARGIN, y, CONTENT_W, h,
            fill=fill, line=line, text_lines=[("", {})],
            line_width=Pt(2.5) if emphasise else Pt(1.25))
        tf = shape.text_frame
        tf.margin_left = Inches(0.28)
        tf.margin_right = Inches(0.28)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        for run in list(p.runs):
            run._r.getparent().remove(run._r)
        r1 = p.add_run()
        r1.text = f"{label}  "
        _style(r1, 26, bold=True, color=ACCENT if emphasise else INK)
        r2 = p.add_run()
        r2.text = question
        _style(r2, 26, color=INK if emphasise else MUTED)
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.LEFT
        p2.space_before = Pt(2)
        r3 = p2.add_run()
        r3.text = owner
        _style(r3, FLOOR_PT, bold=emphasise, color=ACCENT if emphasise else MUTED)
        y = y + h + Inches(0.12)

    box, tf = _textbox(s, MARGIN, Inches(5.30), CONTENT_W, Inches(0.94))
    add_paragraphs(tf, [
        ("Authentication, approval, and authorization are three different "
         "questions. Only one of them is yours to answer.",
         {"bold": True, "size": FLOOR_PT}),
    ])
    add_notes(s, (
        "Segment 1 - 00:00-02:00. Stop-time 02:00. Window: Slides.\n\n"
        "Three different things, and we keep using them interchangeably.\n\n"
        "Authentication is who are you - the authorization server answers "
        "that. Approval is did the human mean it - the client answers that, "
        "on the user's machine, in software you don't control. Authorization "
        "is is this principal allowed to do this specific thing to this "
        "specific object, right now. Nobody answers that unless you write "
        "it.\n\n"
        "LOAD-BEARING: \"Authentication, approval, and authorization are "
        "three different questions. Only one of them is yours to answer.\"\n\n"
        "NEXT WINDOW: slide 4, then Terminal A."
    ))
    SPECS.append(SlideSpec(3, "Three different questions",
                           "Separates authn / approval / authz and marks the "
                           "third as the one you must write."))

    # ---------------- 4 - Trust boundary ----------------
    s = _new_slide(prs)
    add_title(s, "Trust boundary")

    red_l, red_w = MARGIN, Inches(3.45)
    blue_l = Inches(4.75)
    blue_w = Inches(7.983)
    panel_t, panel_h = Inches(2.14), Inches(2.76)

    # Bottom-anchored so the two-line red caption and the one-line blue
    # caption still align on the panel tops.
    box, tf = _textbox(s, red_l, Inches(1.30), red_w, Inches(0.80))
    tf.vertical_anchor = MSO_ANCHOR.BOTTOM
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "Outside your trust boundary"
    _style(r, FLOOR_PT, bold=True, color=RESERVED_RED)

    box, tf = _textbox(s, blue_l, Inches(1.30), blue_w, Inches(0.80))
    tf.vertical_anchor = MSO_ANCHOR.BOTTOM
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "Your trust boundary"
    _style(r, FLOOR_PT, bold=True, color=ACCENT)

    red_panel = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, red_l,
                                   panel_t, red_w, panel_h)
    red_panel.fill.solid()
    red_panel.fill.fore_color.rgb = RED_SOFT
    red_panel.line.color.rgb = RESERVED_RED
    red_panel.line.width = Pt(2.5)
    red_panel.shadow.inherit = False

    blue_panel = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, blue_l,
                                    panel_t, blue_w, panel_h)
    blue_panel.fill.solid()
    blue_panel.fill.fore_color.rgb = ACCENT_SOFT
    blue_panel.line.color.rgb = ACCENT
    blue_panel.line.width = Pt(2.5)
    blue_panel.shadow.inherit = False

    row1_t, row2_t = Inches(2.40), Inches(3.54)
    box_h = Inches(0.94)

    bw = Inches(3.0)
    bx = red_l + Inches(0.225)
    add_rounded_box(s, bx, row1_t, bw, box_h, fill=WHITE, line=RESERVED_RED,
                    text_lines=[("MCP client", {"color": RESERVED_RED,
                                                "bold": True}),
                                ("owns approval", {"color": RESERVED_RED,
                                                   "italic": True})])
    add_rounded_box(s, bx, row2_t, bw, box_h, fill=WHITE, line=RESERVED_RED,
                    text_lines=[("Foundry model", {"color": RESERVED_RED,
                                                   "bold": True}),
                                ("reads hostile text", {"color": RESERVED_RED,
                                                        "italic": True})])

    cw = Inches(3.65)
    cx1 = blue_l + Inches(0.2)
    cx2 = blue_l + Inches(4.12)
    add_rounded_box(s, cx1, row1_t, cw, box_h, fill=WHITE, line=ACCENT,
                    text_lines=[("Authorization server", {"color": ACCENT})])
    add_rounded_box(s, cx2, row1_t, cw, box_h, fill=WHITE, line=ACCENT,
                    text_lines=[("Upstream refund API", {"color": ACCENT})])
    add_rounded_box(s, cx1, row2_t, cw, box_h, fill=ACCENT, line=ACCENT,
                    text_lines=[("MCP server", {"color": WHITE, "bold": True}),
                                ("the decision point", {"color": WHITE,
                                                        "italic": True})])
    add_rounded_box(s, cx2, row2_t, cw, box_h, fill=WHITE, line=ACCENT,
                    text_lines=[("Ledger", {"color": ACCENT})])

    box, tf = _textbox(s, MARGIN, Inches(5.24), CONTENT_W, Inches(0.9))
    add_paragraphs(tf, [
        ("Every denial prints the ledger digest before and after, so "
         "\u201cnothing happened\u201d is shown, not asserted.",
         {"size": FLOOR_PT, "bold": True}),
    ])
    add_notes(s, (
        "Segment 1 - 00:00-02:00. Stop-time 02:00. Window: Slides.\n\n"
        "Everything red is outside your trust boundary even though it is part "
        "of your system. The client is red - it runs on someone else's "
        "laptop. The model is red - it reads text that attackers can "
        "write.\n\n"
        "Flow, if asked: client discovers the authorization server, gets an "
        "audience-bound token, calls the MCP server. The MCP server decides, "
        "then exchanges its token on-behalf-of for the upstream API, which "
        "re-checks and writes the ledger.\n\n"
        "\"Twenty-two minutes, a refund API, and a small synthetic ledger.\"\n\n"
        "NEXT WINDOW: Terminal A. Nineteen minutes of terminal from here."
    ))
    SPECS.append(SlideSpec(4, "Trust boundary",
                           "Architecture with red marking everything outside "
                           "your control."))

    # ---------------- 5 - Five layers ----------------
    s = _new_slide(prs)
    add_title(s, "Five layers, and who owns each")
    add_table(s, LAYERS_TABLE, MARGIN, Inches(1.58), CONTENT_W, LAYER_COLS,
              row_height=Inches(0.52), emphasis_row=3)
    box, tf = _textbox(s, MARGIN, Inches(5.12), CONTENT_W, Inches(0.94))
    add_paragraphs(tf, [
        ("If a model\u2019s refusal is your security boundary, your security "
         "boundary is a probability distribution.",
         {"size": FLOOR_PT, "bold": True}),
    ])
    add_notes(s, (
        "Segment 6 - 20:00-23:00. Stop-time 23:00. Window: Slides.\n\n"
        "Five layers, and they are not interchangeable. The client owns "
        "approval - that's the user's control, and it isn't yours. The "
        "authorization server owns authentication and audience binding. The "
        "MCP server owns the decision, and that one is yours, and nobody else "
        "can do it for you. The upstream API re-checks, because it shouldn't "
        "trust its callers either. The model owns nothing - it advises.\n\n"
        "LOAD-BEARING: \"If a model's refusal is your security boundary, your "
        "security boundary is a probability distribution.\"\n\n"
        "NEXT WINDOW: stay on slides to the end."
    ))
    SPECS.append(SlideSpec(5, "Five layers",
                           "Control map: owner, denial and limitation per "
                           "layer; MCP server emphasised."))

    # ---------------- 6 - The answer ----------------
    s = _new_slide(prs)
    box, tf = _textbox(s, MARGIN, Inches(1.15), CONTENT_W, Inches(0.7))
    add_paragraphs(tf, [
        ("So: who can call this MCP tool?", {"size": 30, "color": MUTED}),
    ])
    box, tf = _textbox(s, MARGIN, Inches(2.25), CONTENT_W, Inches(3.4))
    add_paragraphs(tf, [
        ("Only the principal your server decided may call it, on the object "
         "it decided they may touch, at the moment they asked.",
         {"size": 44, "bold": True}),
    ])
    add_notes(s, (
        "Segment 6 - 20:00-23:00. Stop-time 23:00. Window: Slides.\n\n"
        "Say it slowly. This is the answer the talk exists to deliver. Let it "
        "sit before moving on.\n\n"
        "NEXT WINDOW: slide 7."
    ))
    SPECS.append(SlideSpec(6, "The answer",
                           "The one-sentence answer, alone on the slide."))

    # ---------------- 7 - Take this home ----------------
    s = _new_slide(prs)
    add_title(s, "Take this home")
    box, tf = _textbox(s, MARGIN, Inches(1.60), CONTENT_W, Inches(4.66))
    lines = [
        ("Bind every token to one resource.", True),
        ("A scope is a verb, not an object. refund.write never named "
         "ORD-1003.", True),
        ("A confirmation dialog is not server authorization. Assume Approve "
         "was clicked, then decide anyway.", True),
        ("Never forward an incoming token downstream. Exchange it \u2014 and "
         "if the exchange fails, fail.", False),
        ("Annotations are hints from a process you don\u2019t control.", False),
        ("Model output is advice about untrusted input. Record it; never "
         "obey it.", False),
        ("Audit at the decision point, including denials. Deny by default.",
         False),
    ]
    specs = []
    for idx, (text, emphasise) in enumerate(lines, start=1):
        specs.append(([
            (f"{idx}.  ", {"bold": True,
                           "color": ACCENT if emphasise else MUTED}),
            (text, {"bold": emphasise,
                    "color": INK if emphasise else MUTED}),
        ], {"size": FLOOR_PT, "space_after": 5}))
    add_paragraphs(tf, specs)
    for para in tf.paragraphs:
        set_hanging_indent(para, 0.46)
    add_notes(s, (
        "Segment 6 - 20:00-23:00. Stop-time 23:00. Window: Slides.\n\n"
        "\"Seven things to take home. If you remember three: bind every token "
        "to one resource. Scopes are verbs, not objects. Assume Approve was "
        "clicked, and decide anyway.\" Those three are numbered 1-3 and set "
        "in black; the rest are grey.\n\n"
        "LOAD-BEARING, verbatim on this slide: rule 2 (a scope is a verb), "
        "rule 4 (never forward an incoming token), rule 5 "
        "(annotations are hints).\n\n"
        "NEXT WINDOW: slide 8 and leave it up for Q&A."
    ))
    SPECS.append(SlideSpec(7, "Take this home",
                           "The seven rules; the three the script says to "
                           "remember are emphasised."))

    # ---------------- 8 - Q&A backdrop ----------------
    s = _new_slide(prs)
    add_title(s, "Who can call this MCP tool?")
    add_table(s, LAYERS_TABLE, MARGIN, Inches(1.5), CONTENT_W, LAYER_COLS,
              row_height=Inches(0.52), emphasis_row=3)

    qr_size = Inches(1.15)
    s.shapes.add_picture(qr_stream(REPO_URL), MARGIN, Inches(4.92), qr_size,
                         qr_size)
    box, tf = _textbox(s, Inches(1.95), Inches(5.08), Inches(10.7),
                       Inches(1.02))
    add_paragraphs(tf, [
        (REPO_URL, {"size": FLOOR_PT, "bold": True, "name": MONO,
                    "space_after": 4}),
        ("14 scenarios  \u00b7  207 tests  \u00b7  one command: "
         "scripts\\check.ps1", {"size": FLOOR_PT, "color": MUTED}),
    ])
    add_notes(s, (
        "Segment 7 - 23:00-25:00. Stop-time 25:00. Window: Slides.\n\n"
        "Leave this up for the whole of Q&A. The control map is the answer to "
        "most questions, and the repository link is what the room wants "
        "during exactly these two minutes.\n\n"
        "PLACEHOLDER: the repository URL and its QR code are "
        "https://github.com/<owner>/<repo> and must be replaced before the "
        "event.\n\n"
        "Prepared answers are in docs/RUNBOOK.md: why scopes are "
        "insufficient; why a dialog is not authorization; why you cannot "
        "forward the token; why a local IdP; whether the log is "
        "tamper-proof.\n\n"
        "NEXT WINDOW: none. This is the last visible slide."
    ))
    SPECS.append(SlideSpec(8, "Q&A backdrop",
                           "Control map plus repository URL and QR; stays up "
                           "through Q&A."))

    # ---------------- 9 - What I did not prove ----------------
    s = _new_slide(prs)
    add_title(s, "What I did not prove")
    box, tf = _textbox(s, MARGIN, Inches(1.68), CONTENT_W, Inches(4.3))
    add_paragraphs(tf, [
        ("Microsoft Entra ID is implemented, not executed. No tenant was "
         "authorized for this build.", {"size": FLOOR_PT, "space_after": 15}),
        ("The audit log is a JSONL file on a disk. Not immutable, not "
         "tamper-proof.", {"size": FLOOR_PT, "space_after": 15}),
        ("Resource binding stops reuse at a different resource. It does not "
         "stop replay at its own.", {"size": FLOOR_PT, "space_after": 15}),
        ("The injection demo is a harness replay, not a fresh model attack.",
         {"size": FLOOR_PT, "space_after": 15}),
        ("In cloud mode the platform content filter refused the prompt \u2014 "
         "not the model, and not this application.",
         {"size": FLOOR_PT, "space_after": 0}),
    ])
    add_notes(s, (
        "Segment 6/7 - optional, 20:00-25:00. Window: Slides.\n\n"
        "Use this if the room is sceptical or if a question probes what was "
        "actually demonstrated. It is also a good Q&A backdrop.\n\n"
        "Say platform, not model, for the content filter. Two independent "
        "layers declined the injected content and neither is what stops the "
        "refund.\n\n"
        "NEXT WINDOW: back to slide 8 for Q&A."
    ))
    SPECS.append(SlideSpec(9, "What I did not prove",
                           "Honesty slide; the five claims the talk "
                           "deliberately does not make."))

    # ---------------- 10 - Try it yourself ----------------
    s = _new_slide(prs)
    add_title(s, "Try it yourself")
    box, tf = _textbox(s, MARGIN, Inches(1.7), CONTENT_W, Inches(4.2))
    add_paragraphs(tf, [
        (REPO_URL, {"size": 28, "bold": True, "name": MONO,
                    "space_after": 20}),
        ([("scripts\\bootstrap.ps1", {"name": MONO, "bold": True}),
          ("  \u2014 set up, no Azure subscription needed", {"color": MUTED})],
         {"size": FLOOR_PT, "space_after": 12}),
        ([("scripts\\check.ps1", {"name": MONO, "bold": True}),
          ("  \u2014 207 tests + 14 scenarios \u2192 READY", {"color": MUTED})],
         {"size": FLOOR_PT, "space_after": 12}),
        ([("scripts\\scenario.ps1 -All", {"name": MONO, "bold": True}),
          ("  \u2014 every claim in this talk", {"color": MUTED})],
         {"size": FLOOR_PT, "space_after": 12}),
        ([("scripts\\audit.ps1 -Last 5", {"name": MONO, "bold": True}),
          ("  \u2014 the evidence trail", {"color": MUTED})],
         {"size": FLOOR_PT, "space_after": 20}),
        ("Bash twins for every script. docs/CONTROL-MAP.md is the one-page "
         "takeaway.", {"size": FLOOR_PT, "color": MUTED, "space_after": 0}),
    ])
    add_notes(s, (
        "Segment 7 - optional, 23:00-25:00. Window: Slides.\n\n"
        "Everything runs locally in about ten minutes, with no Azure "
        "subscription and no Entra tenant.\n\n"
        "PLACEHOLDER: replace the repository URL before the event.\n\n"
        "NEXT WINDOW: back to slide 8 for Q&A."
    ))
    SPECS.append(SlideSpec(10, "Try it yourself",
                           "Repository, the four commands, and where the "
                           "one-page takeaway lives."))

    # ---------------- Hidden appendix ----------------
    appendix = [
        ("no-token  +  discovery",
         "The client is told where to authenticate, and the token it gets "
         "back is bound to one resource.",
         ["401 with WWW-Authenticate naming Protected Resource Metadata",
          "PRM \u2192 authorization server metadata",
          "PKCE S256, and RFC 8707 resource=api://refund-mcp-a",
          "Token returns with exactly one audience",
          "Field names and redacted values only \u2014 never a token"]),
        ("allowed-refund",
         "An authorized refund succeeds exactly once; a retry does not "
         "double-spend.",
         ["Refund RFND-\u2026 applied; ledger CHANGED, total 0 \u2192 4000",
          "Retry with the same idempotency key: replayed=True, total 4000",
          "upstream_audience: api://refund-upstream",
          "delegated_identity_preserved: True",
          "No token was forwarded; an on-behalf-of exchange was performed"]),
        ("scope-denial",
         "Sam can read but has no write scope. The tool was visible; the "
         "call was refused.",
         ["POLICY_MISSING_SCOPE, rule R003",
          "Policy version refund-policy/2026-10-06.1",
          "Ledger: UNCHANGED",
          "Denied at tools/call, not at tools/list",
          "Hiding a tool is a UI preference, not access control"]),
        ("wrong-audience",
         "A completely valid token for Resource B is rejected at Resource A.",
         ["AUTH_WRONG_AUDIENCE, rejected before any tool executes",
          "The control: the same token at Resource B succeeds",
          "Ledger: UNCHANGED",
          "A signature check is not an audience check"]),
        ("ownership-denial",
         "The confused deputy: right scope, someone else\u2019s order.",
         ["POLICY_ORDER_NOT_ASSIGNED, rule R006",
          "Riley holds refund.write and a valid token for this resource",
          "ORD-1003 is on another employee\u2019s book",
          "Ledger: UNCHANGED",
          "The scope said the verb. It never said the object."]),
        ("prompt-injection",
         "A hostile note in order data; the policy decision does not move.",
         ["ORD-1004 carries an attacker-written customer note",
          "The model\u2019s answer is recorded, never obeyed",
          "The harness then forces the refund call through",
          "Denied. Ledger: UNCHANGED",
          "Harness replay, not a fresh model attack"]),
        ("audit record",
         "One allowed call and one denied call, followed all the way "
         "through.",
         ["trace ID \u2192 MCP request ID \u2192 pseudonymized user",
          "tenant \u2192 client \u2192 resource audience \u2192 tool",
          "policy version \u2192 rule \u2192 decision \u2192 ledger change",
          "Arguments allowlisted: _omitted_keys includes idempotency_key",
          "Rejected token recorded as identity: untrusted, no user"]),
    ]
    for name, proves, evidence in appendix:
        s = _new_slide(prs)
        add_title(s, f"Fallback \u00b7 {name}", size=34)
        box, tf = _textbox(s, MARGIN, Inches(1.48), CONTENT_W, Inches(0.96))
        add_paragraphs(tf, [(proves, {"size": FLOOR_PT, "bold": True})])
        box, tf = _textbox(s, MARGIN, Inches(2.56), CONTENT_W, Inches(3.5))
        add_paragraphs(tf, [
            ([("\u2022  ", {"color": ACCENT, "bold": True}), (item, {})],
             {"size": FLOOR_PT, "space_after": 12})
            for item in evidence
        ])
        for para in tf.paragraphs:
            set_hanging_indent(para, 0.32)
        hide(s)
        add_notes(s, (
            f"HIDDEN FALLBACK for scenario `{name}`.\n\n"
            "Use only if the terminal is unavailable. Read the expected "
            "evidence aloud and say plainly that you are reading prepared "
            "evidence rather than showing a live run.\n\n"
            "Source: docs/COVERAGE-MATRIX.md and docs/RUNBOOK.md degradation "
            "ladder (Tier A)."
        ))
        SPECS.append(SlideSpec(len(SPECS) + 1, f"Fallback - {name}",
                               "Hidden: expected evidence if the demo dies.",
                               hidden=True))

    return prs


# --------------------------------------------------------------------------
# Verification - re-open the saved file and check it
# --------------------------------------------------------------------------

def _est_char_w(pt: float, bold: bool) -> float:
    """Segoe UI advance width in inches, calibrated against exported PNGs.

    Measured: "Authorization server" at 24pt spans 2.96in (0.148in/char) and
    the 40pt bold title spans 0.283in/char.
    """
    return pt * (0.0071 if bold else 0.0062)


def est_lines(text: str, width_in: float, pt: float, bold: bool) -> int:
    if not text.strip():
        return 1
    words = text.split()
    per_line = max(1.0, width_in / _est_char_w(pt, bold))
    lines, cur = 1, 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if cur + add > per_line:
            lines += 1
            cur = len(w)
        else:
            cur += add
    return lines


def check_geometry(prs: Presentation) -> list[str]:
    """Catch the two failures that rendering revealed: a table row growing
    because a cell wrapped, and anything sliding into the bottom margin."""
    problems: list[str] = []
    for i, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if getattr(shape, "has_table", False) and shape.has_table:
                table = shape.table
                widths = [c.width / 914400 for c in table.columns]
                grown = 0.0
                for r, row in enumerate(table.rows):
                    worst = 1
                    for c, cell in enumerate(row.cells):
                        for para in cell.text_frame.paragraphs:
                            for run in para.runs:
                                pt = run.font.size.pt if run.font.size else 18
                                n = est_lines(run.text, widths[c] - 0.20, pt,
                                              bool(run.font.bold))
                                if n > 1:
                                    problems.append(
                                        f"slide {i}: table cell r{r}c{c} "
                                        f"wraps to {n} lines "
                                        f"({run.text!r}) - the row will grow"
                                    )
                                worst = max(worst, n)
                    grown += max(row.height / 914400,
                                 worst * (24 / 72) + 0.10)
                bottom = shape.top / 914400 + grown
                if bottom > SAFE_BOTTOM / 914400:
                    problems.append(
                        f"slide {i}: table reaches {bottom:.2f}in, past the "
                        f"{SAFE_BOTTOM / 914400:.2f}in safe line")
                for other in slide.shapes:
                    if other is shape or not other.has_text_frame:
                        continue
                    if other.top / 914400 < bottom <= (
                            other.top + other.height) / 914400:
                        problems.append(
                            f"slide {i}: table (bottom {bottom:.2f}in) "
                            f"overlaps shape at {other.top / 914400:.2f}in")
            elif shape.has_text_frame and shape.text_frame.text.strip():
                bottom = (shape.top + shape.height) / 914400
                if bottom > SAFE_BOTTOM / 914400 + 0.02:
                    problems.append(
                        f"slide {i}: shape bottom {bottom:.2f}in is inside "
                        f"the reserved bottom margin "
                        f"({shape.text_frame.text[:34]!r})")
                # A caption that wraps past its box height is silently
                # clipped by PowerPoint, which is how "Outside your trust
                # boundary" lost its last word.
                box_w = shape.width / 914400
                box_h = shape.height / 914400
                inset = ((shape.text_frame.margin_left or 0)
                         + (shape.text_frame.margin_right or 0)) / 914400
                needed = 0.0
                for para in shape.text_frame.paragraphs:
                    text = "".join(r.text for r in para.runs)
                    if not text:
                        continue
                    pt = max((r.font.size.pt for r in para.runs
                              if r.font.size), default=18)
                    bold = any(r.font.bold for r in para.runs)
                    n = est_lines(text, box_w - inset, pt, bold)
                    needed += n * (pt / 72.0) * 1.2
                    needed += ((para.space_after or 0) / 12700) / 72.0
                if needed > box_h + 0.06:
                    problems.append(
                        f"slide {i}: text needs {needed:.2f}in in a "
                        f"{box_h:.2f}in box, will clip "
                        f"({shape.text_frame.text[:34]!r})")
    return problems


LOAD_BEARING = [
    "Authentication, approval, and authorization are three different "
    "questions. Only one of them is yours to answer.",
    "A scope is a verb, not an object.",
    "Annotations are hints from a process you don\u2019t control.",
    "Never forward an incoming token downstream. Exchange it \u2014 and if "
    "the exchange fails, fail.",
    "If a model\u2019s refusal is your security boundary, your security "
    "boundary is a probability distribution.",
]


def iter_runs(shapes):
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from iter_runs(shape.shapes)
            continue
        if getattr(shape, "has_table", False) and shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    for para in cell.text_frame.paragraphs:
                        for run in para.runs:
                            yield shape, run
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    yield shape, run


def verify(path: Path) -> int:
    prs = Presentation(path)
    failures: list[str] = []
    notes: list[str] = []

    slides = list(prs.slides)
    visible, hidden_idx = [], []
    for i, slide in enumerate(slides, start=1):
        (hidden_idx if slide._element.get("show") == "0" else visible).append(i)

    print(f"slides total          : {len(slides)}")
    print(f"visible               : {len(visible)} -> {visible}")
    print(f"hidden (appendix)     : {len(hidden_idx)} -> {hidden_idx}")

    if len(visible) > 12:
        failures.append(f"visible slide count {len(visible)} exceeds 12")

    w_ok = abs(prs.slide_width - Inches(13.333)) < 5000
    h_ok = abs(prs.slide_height - Inches(7.5)) < 5000
    print(f"dimensions 13.333x7.5 : {w_ok and h_ok}")
    if not (w_ok and h_ok):
        failures.append("slide dimensions are not 13.333in x 7.5in")

    small = []
    for i, slide in enumerate(slides, start=1):
        for shape, run in iter_runs(slide.shapes):
            if run.font.size is None:
                small.append((i, "INHERITED", run.text[:48]))
            elif run.font.size < Pt(FLOOR_PT):
                small.append((i, f"{run.font.size.pt:g}pt", run.text[:48]))
    print(f"runs below {FLOOR_PT}pt      : {len(small)}")
    for entry in small:
        print(f"    slide {entry[0]:>2}  {entry[1]:>9}  {entry[2]!r}")
        failures.append(f"slide {entry[0]} has a run at {entry[1]}")

    missing_notes = [
        i for i, s in enumerate(slides, start=1)
        if not (s.has_notes_slide
                and s.notes_slide.notes_text_frame.text.strip())
    ]
    print(f"slides missing notes  : {missing_notes or 'none'}")
    if missing_notes:
        failures.append(f"slides missing speaker notes: {missing_notes}")

    all_text_by_slide = {}
    for i, slide in enumerate(slides, start=1):
        parts = [run.text for _, run in iter_runs(slide.shapes)]
        all_text_by_slide[i] = " ".join(parts)
    corpus = " ".join(all_text_by_slide.values())

    print("load-bearing sentences:")
    for sentence in LOAD_BEARING:
        found = sentence in corpus
        print(f"    {'OK ' if found else 'MISS'}  {sentence[:62]}...")
        if not found:
            failures.append(f"missing verbatim sentence: {sentence[:48]}")

    leaked = []
    if "eyJ" in corpus:
        leaked.append("eyJ")
    for match in re.finditer(r"[A-Za-z0-9]{40,}", corpus):
        leaked.append(match.group(0)[:24] + "...")
    print(f"credential-shaped     : {leaked or 'none'}")
    if leaked:
        failures.append(f"credential-shaped strings: {leaked}")

    identifiers = ["AUTH_WRONG_AUDIENCE", "POLICY_MISSING_SCOPE",
                   "POLICY_ORDER_NOT_ASSIGNED", "R003", "R006",
                   "refund-policy/2026-10-06.1", "api://refund-mcp-a",
                   "api://refund-upstream"]
    src = HERE.parent / "demo" / "src" / "refund_demo"
    blob = "\n".join(
        (src / f).read_text(encoding="utf-8")
        for f in ("policy.py", "tokens.py", "config.py")
    )
    print("identifiers traced to repository:")
    for ident in identifiers:
        on_slide = ident in corpus
        in_repo = ident in blob
        if on_slide:
            print(f"    {'OK ' if in_repo else 'MISS'}  {ident}")
            if not in_repo:
                failures.append(f"identifier not found in source: {ident}")

    print("body words per visible slide (title excluded):")
    for i in visible:
        slide = slides[i - 1]
        words = 0
        for shape, run in iter_runs(slide.shapes):
            if shape.name == "deck-title":
                continue
            words += len(run.text.split())
        flag = "" if words <= 40 else "  <- structured, see report"
        print(f"    slide {i:>2}: {words:>3} words{flag}")

    geom = check_geometry(prs)
    print(f"geometry problems     : {len(geom)}")
    for g in geom:
        print(f"    {g}")
    failures.extend(geom)

    print()
    if failures:
        print(f"FAILED CHECKS ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


def write_slide_notes(path: Path, prs: Presentation) -> Path:
    """Emit the markdown outline from the deck itself, so the two cannot drift."""
    md = [
        "# Slide Notes \u2014 Who Can Call This MCP Tool?",
        "",
        "**OAuth, Resource Binding, and Runtime Policy**  ",
        "Brian Benz \u00b7 MCP Dev Summit Toronto \u00b7 2026-10-06 \u00b7 "
        "15:40\u201316:05",
        "",
        "Generated by [build_deck.py](./build_deck.py) from the deck itself. "
        "Edit the script, not this file, then re-run it.",
        "",
        "A `.pptx` does not diff in git; this file is how the deck gets "
        "reviewed and corrected.",
        "",
        "> **Placeholder:** the repository URL and its QR code are "
        f"`{REPO_URL}`. Replace both before the event.",
        "",
        "---",
        "",
    ]
    for idx, (slide, spec) in enumerate(zip(prs.slides, SPECS), start=1):
        state = "hidden" if spec.hidden else "visible"
        md.append(f"## Slide {idx} \u2014 {spec.title}  *({state})*")
        md.append("")
        md.append(f"*{spec.purpose}*")
        md.append("")
        title_text = ""
        body: list[str] = []
        for shape in slide.shapes:
            if getattr(shape, "has_table", False) and shape.has_table:
                for r, row in enumerate(shape.table.rows):
                    cells = [c.text_frame.text.strip() for c in row.cells]
                    body.append("| " + " | ".join(cells) + " |")
                    if r == 0:
                        body.append("| " + " | ".join(["---"] * len(cells))
                                    + " |")
                continue
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            if not text:
                continue
            if shape.name == "deck-title" and not title_text:
                title_text = text
            else:
                body.extend(line for line in text.splitlines() if line.strip())
        if title_text:
            md.append(f"**On screen:** {title_text}")
            md.append("")
        if body:
            md.append("```text")
            md.extend(body)
            md.append("```")
            md.append("")
        notes = (slide.notes_slide.notes_text_frame.text
                 if slide.has_notes_slide else "")
        md.append("**Speaker notes**")
        md.append("")
        for line in notes.splitlines():
            md.append(f"> {line}" if line.strip() else ">")
        md.append("")
        md.append("---")
        md.append("")
    path.write_text("\n".join(md), encoding="utf-8")
    return path


def normalize_zip(path: Path) -> None:
    """Rewrite the package with fixed entry timestamps.

    python-pptx stamps each zip entry with the current time, so two builds of
    identical content still differ byte for byte. Presentations are zip
    archives, so normalising the entries makes rebuilds verifiable.
    """
    import zipfile

    fixed = (2026, 10, 6, 15, 40, 0)
    with zipfile.ZipFile(path) as zf:
        items = [(i.filename, i.compress_type, zf.read(i.filename))
                 for i in sorted(zf.infolist(), key=lambda x: x.filename)]
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, ctype, data in items:
            info = zipfile.ZipInfo(name, date_time=fixed)
            info.compress_type = ctype
            info.external_attr = 0o600 << 16
            zf.writestr(info, data)
    tmp.replace(path)


def main() -> int:
    prs = build()
    cp = prs.core_properties
    cp.title = "Who Can Call This MCP Tool?"
    cp.subject = "OAuth, Resource Binding, and Runtime Policy"
    cp.author = "Brian Benz"
    cp.comments = ("MCP Dev Summit Toronto, 2026-10-06. Generated by "
                   "slides/build_deck.py.")
    # Pinned so re-running produces a byte-identical file.
    cp.created = STAMP
    cp.modified = STAMP
    cp.last_modified_by = "build_deck.py"
    cp.revision = 1
    prs.save(OUT_PATH)
    normalize_zip(OUT_PATH)
    print(f"wrote {OUT_PATH}")
    notes_path = write_slide_notes(HERE / "SLIDE-NOTES.md",
                                   Presentation(OUT_PATH))
    print(f"wrote {notes_path}")
    print()
    return verify(OUT_PATH)


if __name__ == "__main__":
    sys.exit(main())
