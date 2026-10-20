#!/usr/bin/env python3
"""BNEF Korea costs as an Excel workbook: original, GCAM input, MACRO input.

Sheets
  README        the currency and unit chain, and what the model actually uses
  BNEF original 2024$, exactly as published, Low/Mid/High, 2018-2050
  For GCAM      1975$, GCAM units
  For MACRO     2021$, MACRO units
  Model input   Mid only, 7 periods, the form pasted into the asset CSVs
"""
import csv
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
YR = [2021, 2025, 2030, 2035, 2040, 2045, 2050]

INK  = "1C2A3A"; MUTE = "6B7A8C"; ACC = "C0392B"
HDRF = PatternFill("solid", fgColor="1C2A3A")
BANDF= PatternFill("solid", fgColor="F2F4F6")
WARNF= PatternFill("solid", fgColor="FDF3E3")
THIN = Side(style="thin", color="D5DBE0")
BOX  = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

rows = list(csv.DictReader(open(OUT / "bnef_korea_three_units_long.csv")))

# CCS: BNEF has no Korean row, so Japan is the proxy
for r in csv.DictReader(open(OUT / "ccs_japan_proxy.csv")):
    rows.append({k: r[k] for k in
                 ("metric", "technology_bnef", "technology_model", "scenario",
                  "year", "bnef_value", "bnef_unit", "macro_value",
                  "macro_unit", "gcam_value", "gcam_unit")})

# nuclear is not in the BNEF workbook; it comes from the model's asset files
for r in csv.DictReader(open(OUT / "nuclear_from_macro.csv")):
    rows.append({
        "metric": r["metric"], "technology_bnef": "(not in BNEF)",
        "technology_model": "Nuclear", "scenario": "Mid", "year": r["year"],
        "bnef_value": "", "bnef_unit": "",
        "macro_value": r["macro_value"], "macro_unit": r["macro_unit"],
        "gcam_value": r["gcam_value"], "gcam_unit": r["gcam_unit"],
    })
years = sorted({int(r["year"]) for r in rows})

wb = openpyxl.Workbook()

# ---------------- README -------------------------------------------------
ws = wb.active; ws.title = "README"
ws.column_dimensions["A"].width = 30
ws.column_dimensions["B"].width = 22
ws.column_dimensions["C"].width = 22
ws.column_dimensions["D"].width = 52
def line(r, a, b="", c="", d="", bold=False, color=INK, size=11):
    for col, v in zip("ABCD", (a, b, c, d)):
        cell = ws[f"{col}{r}"]; cell.value = v
        cell.font = Font(bold=bold, color=color, size=size, name="Calibri")
        cell.alignment = Alignment(vertical="center", wrap_text=(col == "D"))

line(1, "BNEF Korea cost metrics", bold=True, size=16)
line(2, "Source: 20251205 BNEF Korea data .xlsx, Sheet1, region South Korea", color=MUTE)
line(3, "The model uses the Mid scenario.", color=MUTE)

line(5, "CURRENCY", bold=True, color=ACC)
line(6, "BNEF 2024$  ->  MACRO 2021$", "x 0.870", "", "deflator used for the model's capital costs", bold=False)
line(7, "MACRO 2021$ ->  GCAM 1975$", "/ 5.0400", "", "US CPI ratio; same factor used in reverse for GCAM fuel prices")
line(8, "BNEF 2024$  ->  GCAM 1975$", "x 0.172619", "", "the two combined")

line(10, "UNITS", bold=True, color=ACC)
line(11, "metric", "BNEF", "MACRO", "GCAM", bold=True)
for i, (m, b, mm, g) in enumerate([
        ("Capex", "$/kW", "$/MW", "$/kW"),
        ("Fixed O&M", "$/MW/yr", "$/MW-yr", "$/kW/yr"),
        ("Variable O&M", "$/MWh", "$/MWh", "$/GJ"),
        ("LCOE", "$/MWh", "$/MWh", "$/GJ"),
        ("Short-run marginal cost", "$/MWh", "$/MWh", "$/GJ")]):
    line(12 + i, m, b, mm, g)

line(18, "GCAM caveat", bold=True, color=ACC)
line(19, "", "", "", "1975$/kW and 1975$/kW/yr follow GCAM's electricity capital and fixed-O&M convention.")
line(20, "", "", "", "Variable terms are in 1975$/GJ because GCAM's energy unit is EJ.")
line(21, "", "", "", "If the GCAM input expects 1975$/MWh, multiply the GCAM value by 3.6.")

line(23, "WHAT THE MODEL ACTUALLY USES", bold=True, color=ACC)
line(24, "Capital cost", "BNEF Mid x 0.870", "", "matches to within 0.1% for 2025-2050, all technologies")
line(25, "2021 capital cost", "not BNEF", "", "27-30% below BNEF Mid; a different source. 2021 is the calibrated base year with can_expand FALSE, so it does not affect results")
line(26, "Fixed O&M, solar and wind", "BNEF Mid x 0.910", "", "a different deflator from capex; 4.6% high relative to the 0.870 convention. OPEN ITEM")
line(27, "Coal and gas O&M", "BNEF Mid x 0.870", "", "set to Mid on 2026-10-19; previously flat values of unrecorded provenance")
for r in (24, 25, 26, 27):
    for col in "ABCD":
        ws[f"{col}{r}"].fill = WARNF if r == 26 else BANDF
        ws[f"{col}{r}"].border = BOX

line(26, "NUCLEAR", bold=True, color=ACC)
line(27, "Not in BNEF", "from asset files", "", "Capex 2,886 -> 2,625 $/kW, fixed O&M 199 $/kW-yr, variable O&M 10.34 $/MWh, all 2021$. Treated as Mid. Original source not recorded")
for col in "ABCD":
    ws[f"{col}30"].fill = WARNF
    ws[f"{col}30"].border = BOX

line(29, "CCS", bold=True, color=ACC)
line(30, "Japan proxy", "no Korea row in BNEF", "", "Coal CCS and gas CCS from BNEF Sheet3, Japan, Mid. China 878 vs US 5,646 $/kW, so a 3-country mean is dominated by the US. Japan also matches the model's existing CCS fixed O&M to 0.12%. 2021 omitted")
for col in "ABCD":
    ws[f"{col}30"].fill = WARNF
    ws[f"{col}30"].border = BOX

line(32, "SHEETS", bold=True, color=ACC)
line(33, "BNEF original", "", "", "2024$ as published, Low / Mid / High, 2018-2050")
line(34, "For GCAM", "", "", "1975$ in GCAM units")
line(35, "For MACRO", "", "", "2021$ in MACRO units")
line(36, "Model input", "", "", "Mid only, the 7 model periods")
line(37, "GCAM mapping", "", "", "current GCAM values against the Korean values, with the XML line number of each")

line(39, "Generated by build_bnef_harmonised.py, build_mapping.py and build_excel.py", color=MUTE, size=10)

# ---------------- data sheets -------------------------------------------
def sheet(name, vkey, ukey, note, year_list, scen_filter=None, ndigits=4):
    ws = wb.create_sheet(name)
    ws["A1"] = name
    ws["A1"].font = Font(bold=True, size=14, color=INK, name="Calibri")
    ws["A2"] = note
    ws["A2"].font = Font(size=10, color=MUTE, name="Calibri")

    hdr = ["metric", "technology", "scenario", "unit"] + [str(y) for y in year_list]
    for j, h in enumerate(hdr, 1):
        c = ws.cell(row=4, column=j, value=h)
        c.font = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
        c.fill = HDRF; c.border = BOX
        c.alignment = Alignment(horizontal="center" if j > 4 else "left")

    order = {"Low": 0, "Mid": 1, "High": 2}
    keys, data, units = [], {}, {}
    for r in rows:
        if scen_filter and r["scenario"] != scen_filter:
            continue
        k = (r["metric"], r["technology_model"], r["scenario"])
        v = r[vkey]
        if v == "" or v is None:          # nuclear has no BNEF column
            continue
        data.setdefault(k, {})[int(r["year"])] = float(v)
        units[k] = r[ukey]
        if k not in keys:
            keys.append(k)
    keys.sort(key=lambda k: (k[0], k[1], order.get(k[2], 9)))

    row = 5
    for k in keys:
        vals = [data[k].get(y) for y in year_list]
        if all(v is None for v in vals):
            continue
        flag = " *" if k[1] == "Nuclear" else (" †" if "CCS" in k[1] else "")
        for j, v in enumerate([k[0], k[1], k[2] + flag, units[k]], 1):
            c = ws.cell(row=row, column=j, value=v)
            c.font = Font(size=11, name="Calibri",
                          bold=(k[2] == "Mid"), color=INK if k[2] == "Mid" else MUTE)
            c.border = BOX
            if k[2] == "Mid":
                c.fill = BANDF
        for j, v in enumerate(vals, 5):
            c = ws.cell(row=row, column=j, value=round(v, ndigits) if v is not None else None)
            c.font = Font(size=11, name="Calibri", bold=(k[2] == "Mid"),
                          color=INK if k[2] == "Mid" else MUTE)
            c.border = BOX
            c.number_format = "#,##0.000" if abs(v or 0) < 100 else "#,##0"
            if k[2] == "Mid":
                c.fill = BANDF
        row += 1

    for j, w in enumerate([24, 15, 10, 14], 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    for j in range(5, 5 + len(year_list)):
        ws.column_dimensions[get_column_letter(j)].width = 12
    note_row = row + 1
    if any(k[1] == "Nuclear" for k in keys):
        c = ws.cell(row=note_row, column=1,
                    value="*  Nuclear is not in the BNEF workbook. Values are taken from the "
                          "model's own asset files (nuclear_<year>.csv) and treated as Mid. "
                          "Source not recorded; see the main README.")
        c.font = Font(size=10, color=ACC, name="Calibri")
        note_row += 1
    if any("CCS" in k[1] for k in keys):
        c = ws.cell(row=note_row, column=1,
                    value="\u2020  CCS has no South Korea row in BNEF. Japan is used as the proxy "
                          "(China is 878 $/kW against the United States at 5,646, so a three-country "
                          "mean is dominated by the US). 2021 omitted: the first year available, 2022, "
                          "is a first-of-a-kind cost.")
        c.font = Font(size=10, color=ACC, name="Calibri")
    ws.freeze_panes = "E5"
    return ws

sheet("BNEF original", "bnef_value", "bnef_unit",
      "As published. 2024$. Low / Mid / High. Mid is shaded.", years)
sheet("For GCAM", "gcam_value", "gcam_unit",
      "1975$, GCAM units. Variable terms are $/GJ — multiply by 3.6 for $/MWh.", years)
sheet("For MACRO", "macro_value", "macro_unit",
      "2021$, MACRO units. Capex is $/MW, not $/kW.", years)
sheet("Model input", "macro_value", "macro_unit",
      "Mid only, the 7 model periods. These are the numbers that go into the asset CSVs.",
      YR, scen_filter="Mid")

# ---------------- GCAM mapping ------------------------------------------
ws = wb.create_sheet("GCAM mapping")
ws["A1"] = "MACRO / BNEF Korea  ->  GCAM electricity_water_cost_updated.xml"
ws["A1"].font = Font(bold=True, size=14, color=INK, name="Calibri")
ws["A2"] = ("Values in 1975$. Change them in the `electricity` sector of "
            "<global-technology-database>, not in the elec_<fuel> cooling variants "
            "(those carry the incremental cooling cost, OCC about 10).")
ws["A2"].font = Font(size=10, color=MUTE, name="Calibri")
ws["A3"] = ("GCAM is a global technology database: editing these applies to all 32 regions. "
            "To change Korea only, override inside the region block instead.")
ws["A3"].font = Font(size=10, color=ACC, name="Calibri")

mrows = list(csv.DictReader(open(OUT / "macro_to_gcam_mapping.csv")))
hdr = ["macro_technology", "gcam_subsector", "gcam_technology", "metric",
       "gcam_parameter", "unit_1975usd", "year", "gcam_current",
       "proposed_korea", "pct_change", "xml_line"]
for j, h in enumerate(hdr, 1):
    c = ws.cell(row=5, column=j, value=h)
    c.font = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
    c.fill = HDRF; c.border = BOX
    c.alignment = Alignment(horizontal="center", wrap_text=True)
for i, r in enumerate(mrows):
    row = 6 + i
    for j, h in enumerate(hdr, 1):
        v = r[h]
        if h in ("year", "xml_line"):
            v = int(v) if v else None
        elif h in ("gcam_current", "proposed_korea", "pct_change"):
            v = float(v) if v != "" else None
        c = ws.cell(row=row, column=j, value=v)
        c.font = Font(size=11, name="Calibri")
        c.border = BOX
        if h in ("gcam_current", "proposed_korea"):
            c.number_format = "#,##0.000" if abs(v or 0) < 100 else "#,##0"
        if h == "pct_change" and v is not None:
            c.number_format = "+0.0;-0.0"
            c.font = Font(size=11, name="Calibri", bold=True,
                          color=ACC if abs(v) > 40 else INK)
        if r["metric"] == "Capacity factor":
            c.fill = WARNF
for j, w in enumerate([17, 14, 20, 15, 16, 13, 8, 14, 15, 12, 11], 1):
    ws.column_dimensions[get_column_letter(j)].width = w
ws.freeze_panes = "A6"

f = OUT / "BNEF_Korea_costs_BNEF_GCAM_MACRO.xlsx"
wb.save(f)
print(f"  + {f.name}  ({len(wb.sheetnames)} sheets: {', '.join(wb.sheetnames)})")
