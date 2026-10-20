#!/usr/bin/env python3
"""Discussion deck for the MACRO technical meeting."""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

D = Path("/Users/hanwoongkim/Desktop/repo_runs/figures/meeting")
INK   = RGBColor(0x1C, 0x2A, 0x3A)
MUTE  = RGBColor(0x6B, 0x7A, 0x8C)
ACC   = RGBColor(0xC0, 0x39, 0x2B)
WARN  = RGBColor(0xD9, 0x8C, 0x1F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
W, H = prs.slide_width, prs.slide_height

def blank(): return prs.slides.add_slide(prs.slide_layouts[6])

def tb(sl, x, y, w, h, text, size=18, bold=False, color=INK,
       align=PP_ALIGN.LEFT, space=4, font="Calibri"):
    box = sl.shapes.add_textbox(x, y, w, h); f = box.text_frame
    f.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        p = f.paragraphs[0] if i == 0 else f.add_paragraph()
        p.text = line; p.alignment = align; p.space_after = Pt(space)
        for r in p.runs:
            r.font.size = Pt(size); r.font.bold = bold
            r.font.color.rgb = color; r.font.name = font
    return box

def rule(sl, y, x=Inches(0.6), w=None, color=WARN, h=Emu(34000)):
    w = w or (W - Inches(1.2))
    s = sl.shapes.add_shape(1, x, y, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background()
    s.shadow.inherit = False

def header(sl, kicker, title):
    rule(sl, Inches(0.42), w=Inches(1.5))
    tb(sl, Inches(0.6), Inches(0.52), Inches(11), Inches(0.3), kicker, 13, True, WARN)
    tb(sl, Inches(0.6), Inches(0.82), Inches(12), Inches(0.7), title, 27, True, INK)

def pic_fit(sl, img, top, bottom_margin=Inches(0.35)):
    from PIL import Image
    iw, ih = Image.open(D/img).size
    avail_w, avail_h = W - Inches(1.2), H - top - bottom_margin
    sc = min(avail_w/iw, avail_h/ih)
    w, h = int(iw*sc), int(ih*sc)
    sl.shapes.add_picture(str(D/img), int((W-w)/2), top, w, h)

def question(sl, text, y=None):
    y = y or (H - Inches(0.92))
    bar = sl.shapes.add_shape(1, Inches(0.6), y, W-Inches(1.2), Inches(0.62))
    bar.fill.solid(); bar.fill.fore_color.rgb = RGBColor(0xF4, 0xF1, 0xEC)
    bar.line.color.rgb = WARN; bar.line.width = Pt(1.25); bar.shadow.inherit = False
    tf = bar.text_frame; tf.word_wrap = True
    tf.margin_left = Inches(0.18); tf.margin_top = Inches(0.06)
    p = tf.paragraphs[0]; p.text = text
    for r in p.runs:
        r.font.size = Pt(14); r.font.bold = True; r.font.color.rgb = INK; r.font.name = "Calibri"

# ---------- 1  title ----------------------------------------------------
s = blank()
rule(s, Inches(2.25), x=Inches(1.0), w=Inches(2.2), h=Emu(52000))
tb(s, Inches(1.0), Inches(2.45), Inches(11.5), Inches(1.2),
   "MACRO-Korea: open technical questions", 40, True, INK)
tb(s, Inches(1.0), Inches(3.5), Inches(11), Inches(0.5),
   "Provincial power-sector model · 17 provinces · 8,760 chronological hours · 2021–2050 myopic",
   16, False, MUTE)
tb(s, Inches(1.0), Inches(4.35), Inches(11), Inches(1.4),
   "Six questions where the answer depends on how MacroEnergy itself works.\n"
   "Results shown are from 13 October and predate three staged base-year fixes.",
   16, False, INK)
tb(s, Inches(1.0), Inches(6.3), Inches(11), Inches(0.4),
   "Hanwoong Kim · Net Zero Korea", 13, False, MUTE)

# ---------- 2  where we are --------------------------------------------
s = blank()
header(s, "STATUS", "Where the model is")
rows = [("Structure",   "Complete. 7 periods, 8,760 h, linear-relaxed UC, myopic, Gurobi barrier.", INK),
        ("Solve",       "Ref 2.5 h · NDC 4.6 h on 24 cores / 192 GB. ~13.6M rows.", INK),
        ("Transmission","99.1 GW network from NREL ITLs, calibrated to the KPX metro limit. Expands.", INK),
        ("Base year",   "NOT calibrated. Coal 300 TWh vs 198 observed; gas 58 vs 167.", ACC),
        ("Staged fixes","Coal availability 0.65 · nuclear 0.85→0.78 · 2021 gas retirement blocked.", WARN)]
y = Inches(1.85)
for k, v, c in rows:
    tb(s, Inches(0.7), y, Inches(2.5), Inches(0.4), k, 16, True, MUTE)
    tb(s, Inches(3.3), y, Inches(9.4), Inches(0.75), v, 16, False, c)
    y += Inches(0.82)
question(s, "Everything that follows is a question about MacroEnergy, not about Korean data.", Inches(6.45))

# ---------- 3  base year ------------------------------------------------
s = blank()
header(s, "CONTEXT", "The results you are about to see predate the base-year fix")
pic_fit(s, "F1_base_year.png", Inches(1.75), Inches(1.05))
question(s, "Flagged so the known gap is not re-diagnosed. Fixes are staged, not yet run.")

# ---------- 4  Q1 -------------------------------------------------------
s = blank()
header(s, "QUESTION 1  ·  HIGHEST PRIORITY", "MaxNewCapacityConstraint is per-asset, so we cannot cap a national build rate")
pic_fit(s, "F2_solar_cap.png", Inches(1.72), Inches(1.05))
question(s, "We need \u2264 5 GW/yr nationally. The only lever is 6,000 MW per province per period. Is a grouped MaxNewCapacityConstraint available upstream?")

# ---------- 5  Q2 -------------------------------------------------------
s = blank()
header(s, "QUESTION 2", "MinFlowConstraint on all five thermal technologies ran us out of memory")
t = [("Rows, MinFlow on coal + gas CCGT only", "13.60 M", INK),
     ("Rows, MinFlow on all five", "14.05 M", ACC),
     ("Added by three technologies", "≈ 450,000 rows", ACC),
     ("Outcome at 128 GB", "killed — two jobs", ACC),
     ("Current state", "off for nuclear, coal CCS, gas CCS; mem raised to 192 GB", WARN)]
y = Inches(2.0)
for k, v, c in t:
    tb(s, Inches(0.7), y, Inches(7.4), Inches(0.45), k, 17, False, MUTE)
    tb(s, Inches(8.3), y, Inches(4.4), Inches(0.45), v, 17, True, c)
    y += Inches(0.72)
tb(s, Inches(0.7), Inches(5.75), Inches(12), Inches(1.0),
   "min_flow_fraction values are still in the CSVs for those three technologies but the constraint is not declared.",
   15, False, MUTE)
question(s, "Is that row growth expected? Is there a cheaper MinFlow formulation under relaxed UC — and are the undeclared min_flow_fraction values truly inert?")

# ---------- 6  Q3 -------------------------------------------------------
s = blank()
header(s, "QUESTION 3", "Nuclear is completely rigid, and the carbon price absorbs the consequence")
pic_fit(s, "F3_nuclear_co2.png", Inches(1.72), Inches(1.05))
question(s, "What is the idiomatic way to represent near-baseload nuclear in MACRO? Drop MustRun for a low min_flow_fraction instead?")

# ---------- 7  Q4 -------------------------------------------------------
s = blank()
header(s, "QUESTION 4", "Transmission: signed bidirectional edges, and a transport formulation")
pic_fit(s, "F4_transmission.png", Inches(1.72), Inches(1.05))
question(s, "Does MACRO offer DC power flow? To charge a per-MWh cost, should each corridor be split into two unidirectional edges?")

# ---------- 8  Q5 + Q6 --------------------------------------------------
s = blank()
header(s, "QUESTIONS 5 AND 6", "Solution algorithm, and staging a sector that does not exist yet")
tb(s, Inches(0.7), Inches(1.95), Inches(5.8), Inches(0.4), "Q5 · Myopic vs perfect foresight", 20, True, INK)
tb(s, Inches(0.7), Inches(2.5), Inches(5.6), Inches(2.6),
   "NDC builds 14.9 GW of nuclear in the single\n2025–2030 period, with no build-rate limit.\n\n"
   "Myopic now: 17–19 min per period,\n2.5 h (Ref) and 4.6 h (NDC) end to end.\n\n"
   "Is perfect foresight tractable at 8,760 hours\nby 7 periods? What does it cost?", 16, False, INK)
tb(s, Inches(7.0), Inches(1.95), Inches(5.8), Inches(0.4), "Q6 · Heat demand with no supply", 20, True, INK)
tb(s, Inches(7.0), Inches(2.5), Inches(5.6), Inches(2.6),
   "17 Steam nodes carry demand but no asset\nproduces Steam.\n\n"
   "76,212 GWh is non-served every period in\nevery scenario, identically.\n\n"
   "Best practice for staging a sector: drop the\nnodes, or keep them at zero penalty?", 16, False, INK)
tb(s, Inches(7.0), Inches(5.15), Inches(5.6), Inches(0.5),
   "Heat is the next sector, due November 2026.", 15, True, WARN)
question(s, "Q6 matters now: it determines how we wire the heat sector in next month.")

# ---------- 9  minor ----------------------------------------------------
s = blank()
header(s, "SHORTER ITEMS", "Three things to confirm")
items = [("HydroRes duration is 475 hours",
          "1,471.8 GWh of storage against 3.1 GW of turbine, fixed in every period. Generates only 0.6 TWh.\nLooks inherited from the MacroEnergy example data — can you confirm the provenance?"),
         ("Battery picks 5.6–5.7 h duration",
          "Given a 2–10 h range, the model settles here in both cases. Plausible, but worth a sanity check."),
         ("Solver settings",
          "Barrier, Method=2, Crossover=0, BarConvTol=1e-3, Threads=22, BarHomogeneous=1,\nover 8,760 hours in a single subperiod. Any advice?")]
y = Inches(1.95)
for k, v in items:
    tb(s, Inches(0.7), y, Inches(12), Inches(0.4), k, 18, True, INK)
    tb(s, Inches(0.7), y + Inches(0.42), Inches(12), Inches(1.0), v, 15, False, MUTE)
    y += Inches(1.6)

# ---------- 10  asks ----------------------------------------------------
s = blank()
header(s, "SUMMARY", "What we are asking for")
asks = [("1", "Grouped MaxNewCapacityConstraint", "unblocks every build-rate limit we need", ACC),
        ("2", "A cheaper MinFlow formulation", "or confirmation that 450k rows is simply the cost", INK),
        ("3", "The right construct for near-baseload nuclear", "drives the carbon price and the curtailment", ACC),
        ("4", "Transmission: DC flow, or split edges", "we are using loop-flow ITLs in a transport model", INK),
        ("5", "Is perfect foresight tractable here", "affects how we read the nuclear build path", INK),
        ("6", "How to stage an unbuilt sector", "needed before heat, next month", WARN)]
y = Inches(1.9)
for n, k, v, c in asks:
    tb(s, Inches(0.7), y, Inches(0.5), Inches(0.45), n, 19, True, c)
    tb(s, Inches(1.3), y, Inches(6.3), Inches(0.45), k, 17, True, INK)
    tb(s, Inches(7.7), y, Inches(5.0), Inches(0.6), v, 14, False, MUTE)
    y += Inches(0.78)
question(s, "Priority: 1 and 3. They decide whether the solar and carbon-price results are defensible.", Inches(6.6))

out = D / "MACRO_technical_questions.pptx"
prs.save(out); print("saved", out, f"({len(prs.slides.__iter__.__self__._sldIdLst)} slides)")
