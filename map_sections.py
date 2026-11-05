"""Map of treated and comparison motorway sections (Figure 1, Section 3 of the report).

Rebuilds the motorway road sections, the accident linking and the treated/comparison
classification from data_exploration_Teun.ipynb (cells 1, 3 and 6), and draws the
result on a map of the Netherlands.

- Road geometry: INWEVA 2023 historie shapefile (read directly, no geopandas needed).
- Outline of the Netherlands: CBS 'landsdeel_gegeneraliseerd' 2024 via PDOK, stored in
  nl_outline.txt (RD New coordinates divided by 10, lines separated by '|').

Run from the repository root after download_data.py:
    python map_sections.py
Output: figures/Figure_map_sections.png and figures/Figure_map_sections.pdf
"""
import os
import struct

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.collections import LineCollection
from matplotlib.patches import FancyBboxPatch, Rectangle

DATA = "data"
YEARS = [2018, 2019, 2021, 2022, 2023]   # years used for the classification (as in the notebook)


# ---------------------------------------------------------------------------
# 1. Road sections, accident linking and classification (same logic as notebook)
# ---------------------------------------------------------------------------
def is_motorway_main(df):
    """Rijkswaterstaat motorway main carriageway: WEGBEHSRT = R, BST_CODE = HR, ROUTELTR = A."""
    return (df["WEGBEHSRT"] == "R") & (df["BST_CODE"] == "HR") & (df["ROUTELTR"] == "A")


def load_sections():
    """INWEVA 2023 main-carriageway sections that lie on a motorway (notebook cell 1)."""
    year_cols = [f"etmaal_AL_weekdag_{y}" for y in range(2018, 2024)]
    inweva = pd.read_excel(f"{DATA}/INWEVA/INWEVA_2023/A. Outputbestanden Excel/INWEVA_2023_historie.xlsx",
                           usecols=["VIAS_baannr", "Baantype_van", "Wegnr_van", "Ri_van", "Hm_van", "Hm_naar",
                                    "Lengte_baan_meter", "NwbId", "Traject_van", "Traject_naar"] + year_cols)
    inweva_hr = inweva[inweva["Baantype_van"] == "HR"].copy()

    nwb = pd.read_csv(f"{DATA}/BRON/01-01-2023_31-12-2023/Netwerkgegevens/wegvakken.txt",
                      encoding="latin-1", dtype=str, usecols=["WVK_ID", "WEGBEHSRT", "BST_CODE", "ROUTELTR"])
    motorway_ids = set(nwb.loc[is_motorway_main(nwb), "WVK_ID"])

    def on_motorway(nwb_ids):
        # NwbId is a comma-separated list; since 2020 each ID has a suffix H or T
        return any(x.strip().rstrip("HT") in motorway_ids for x in nwb_ids.split(","))

    sections = inweva_hr[inweva_hr["NwbId"].apply(on_motorway)].copy()
    sections["hm_low"] = sections[["Hm_van", "Hm_naar"]].min(axis=1)
    sections["hm_high"] = sections[["Hm_van", "Hm_naar"]].max(axis=1)
    # sections spanning a kilometre jump in the hectometre numbering cannot be matched reliably
    jump = (sections["hm_high"] - sections["hm_low"]) > sections["Lengte_baan_meter"] + 1000
    sections = sections[~jump].copy()
    print(f"{len(sections)} motorway road sections ({jump.sum()} spanning a kilometre jump excluded)")
    return sections


def link_year(year, sections):
    """Link the motorway accidents of one year to INWEVA sections on road, direction and position (cell 3)."""
    folder = f"{DATA}/BRON/01-01-{year}_31-12-{year}"
    acc = pd.read_csv(f"{folder}/Ongevallengegevens/ongevallen.txt", encoding="latin-1", dtype=str,
                      usecols=["VKL_NUMMER", "WVK_ID", "AP3_CODE", "LGD_ID", "MAXSNELHD", "AOL_ID"])
    nwb = pd.read_csv(f"{folder}/Netwerkgegevens/wegvakken.txt", encoding="latin-1", dtype=str,
                      usecols=["WVK_ID", "WEGBEHSRT", "BST_CODE", "ROUTELTR", "WEGNUMMER", "RPE_CODE"])
    motorway = nwb[is_motorway_main(nwb)].drop(columns=["WEGBEHSRT", "BST_CODE", "ROUTELTR"])
    acc = acc.merge(motorway, on="WVK_ID", how="inner")
    acc["road"] = pd.to_numeric(acc["WEGNUMMER"])

    # position of an accident = median hectometre of its NWB road section, in metres
    hecto = pd.read_csv(f"{folder}/Netwerkgegevens/hectopunten.txt", encoding="latin-1", dtype=str,
                        usecols=["WVK_ID", "HECTOMETER"])
    hecto["metre"] = pd.to_numeric(hecto["HECTOMETER"]) * 100
    acc["position_m"] = acc["WVK_ID"].map(hecto.groupby("WVK_ID")["metre"].median())

    candidates = acc.merge(sections[["VIAS_baannr", "Wegnr_van", "Ri_van", "hm_low", "hm_high"]],
                           left_on=["road", "RPE_CODE"], right_on=["Wegnr_van", "Ri_van"])
    hit = candidates[candidates["position_m"].between(candidates["hm_low"], candidates["hm_high"])]
    linked = hit.drop_duplicates("VKL_NUMMER").copy()
    linked["year"] = year
    print(f"{year}: {len(acc)} motorway accidents, {len(linked)} linked ({len(linked) / len(acc):.1%})")
    return linked


def classify(accidents):
    """Treated = median limit 120/130 before and 100 after; comparison = 100 in both periods (cell 6)."""
    accidents["limit"] = pd.to_numeric(accidents["MAXSNELHD"], errors="coerce")
    before = accidents[accidents["year"].isin([2018, 2019])].groupby("VIAS_baannr")["limit"].median()
    after = accidents[accidents["year"].isin([2021, 2022, 2023])].groupby("VIAS_baannr")["limit"].median()
    df = pd.DataFrame({"limit_before": before, "limit_after": after})
    conditions = [df["limit_before"].isin([120, 130]) & (df["limit_after"] == 100),
                  (df["limit_before"] == 100) & (df["limit_after"] == 100)]
    df["treated"] = np.select(conditions, [True, False], default=None)
    print("Treated:", (df["treated"] == True).sum(), "Comparison:", (df["treated"] == False).sum(),
          "Unclassified:", df["treated"].isna().sum())
    return df


# ---------------------------------------------------------------------------
# 2. Minimal shapefile reader (polylines), so the map does not need geopandas
# ---------------------------------------------------------------------------
def read_shp_lines(path):
    """Return, per record, a list of (n, 2) arrays with the parts of a polyline shapefile."""
    b = open(path + ".shp", "rb").read()
    pos, lines = 100, []
    while pos < len(b):
        _, length = struct.unpack(">ii", b[pos:pos + 8]); pos += 8
        rec = b[pos:pos + length * 2]; pos += length * 2
        if struct.unpack("<i", rec[:4])[0] == 0:          # null shape
            lines.append([]); continue
        nparts, npts = struct.unpack("<ii", rec[36:44])
        parts = list(struct.unpack(f"<{nparts}i", rec[44:44 + 4 * nparts])) + [npts]
        pts = np.frombuffer(rec[44 + 4 * nparts:44 + 4 * nparts + 16 * npts], dtype="<f8").reshape(-1, 2)
        lines.append([pts[parts[k]:parts[k + 1]] for k in range(nparts)])
    return lines


def read_dbf(path):
    """Read the attribute table (.dbf) of a shapefile into a DataFrame of strings."""
    b = open(path + ".dbf", "rb").read()
    n, header_len, record_len = struct.unpack("<IHH", b[4:12])
    fields, p = [], 32
    while b[p] != 0x0D:
        fields.append((b[p:p + 11].split(b"\0")[0].decode(), b[p + 16])); p += 32
    rows = []
    for i in range(n):
        r = b[header_len + i * record_len + 1: header_len + (i + 1) * record_len]
        o, row = 0, {}
        for name, size in fields:
            row[name] = r[o:o + size].decode("latin-1").strip(); o += size
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Build the data
# ---------------------------------------------------------------------------
sections = load_sections()
accidents = pd.concat([link_year(y, sections) for y in YEARS], ignore_index=True)
speed = classify(accidents)

group = speed["treated"].map({True: "Treated", False: "Comparison"})
sections["group"] = sections["VIAS_baannr"].map(group).fillna("Not included")

shp = f"{DATA}/INWEVA/INWEVA_2023/B. Outputbestanden Shapes/INWEVA_2023_historie"
geom, attr = read_shp_lines(shp), read_dbf(shp)
attr["VIAS_baannr"] = pd.to_numeric(attr["BAANNR"], errors="coerce")
attr["group"] = attr["VIAS_baannr"].map(sections.set_index("VIAS_baannr")["group"])

km = {g: sections.loc[sections["group"] == g, "Lengte_baan_meter"].sum() / 1000
      for g in ["Treated", "Comparison", "Not included"]}
print({g: round(v) for g, v in km.items()})


def lines_of(g):
    """All line parts of the sections in group g."""
    return [part for i in np.where(attr["group"] == g)[0] for part in geom[i]]


# ---------------------------------------------------------------------------
# 4. Draw the map
# ---------------------------------------------------------------------------
ORANGE, BLUE, GREY = "#ff7f0e", "#1f77b4", "#c9ccd1"   # same colours as the other figures in the report
TEXT, MUTED = "#2b2f36", "#6b7280"
plt.rcParams["font.family"] = "DejaVu Sans"

fig = plt.figure(figsize=(7.2, 8.6), facecolor="white")
ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])

# outline of the Netherlands
outline = [np.array([[float(v) * 10 for v in p.split(",")] for p in line.split(";")])
           for line in open("nl_outline.txt").read().split("|")]
ax.add_collection(LineCollection(outline, colors="#1a1a1a", linewidths=0.55, zorder=1))

# roads: grey first, then orange and blue on top with a thin white casing
casing = [pe.Stroke(linewidth=3.4, foreground="white"), pe.Normal()]
ax.add_collection(LineCollection(lines_of("Not included"), colors=GREY, linewidths=1.3, capstyle="round"))
for g, colour in [("Treated", ORANGE), ("Comparison", BLUE)]:
    lc = LineCollection(lines_of(g), colors=colour, linewidths=1.9, capstyle="round", joinstyle="round")
    lc.set_path_effects(casing)
    ax.add_collection(lc)

ax.autoscale()
ax.set_aspect("equal")
ax.set_axis_off()
x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
ax.set_xlim(x0 - 8000, x1 + 8000); ax.set_ylim(y0 - 10000, y1 + 30000)

# cities (RD New coordinates, rounded)
cities = {"Amsterdam": (121500, 487000, "left"), "Rotterdam": (92500, 437500, "right"),
          "The Hague": (81000, 455000, "right"), "Utrecht": (136000, 456000, "left"),
          "Eindhoven": (161000, 383000, "left"), "Groningen": (233500, 582000, "left"),
          "Arnhem": (190500, 444000, "left"), "Zwolle": (203000, 502000, "left"),
          "Maastricht": (176000, 317500, "left"), "Breda": (112500, 400000, "right"),
          "Enschede": (258000, 471000, "right")}
for name, (x, y, side) in cities.items():
    ax.plot(x, y, "o", ms=4.2, mfc="white", mec=TEXT, mew=1.1, zorder=5)
    ax.text(x + (3500 if side == "left" else -3500), y + 1500, name, fontsize=8, color=TEXT, ha=side,
            va="bottom", zorder=6, path_effects=[pe.withStroke(linewidth=3, foreground="white")])

# title
ax.text(x0, y1 + 26000, "Treated and comparison motorway sections", fontsize=14, fontweight="bold",
        color=TEXT, va="top")
ax.text(x0, y1 + 15000, "Dutch motorway main carriageways, classified by speed limit before and after March 2020",
        fontsize=8.5, color=MUTED, va="top")

# legend box (bottom left, in the North Sea corner)
lx, ly, bw, bh = x0 - 2000, y0 + 2000, 112000, 62000
ax.add_patch(FancyBboxPatch((lx, ly), bw, bh, boxstyle="round,pad=0,rounding_size=5000",
                            fc="white", ec="#e3e6ea", lw=1, zorder=7,
                            path_effects=[pe.SimplePatchShadow(offset=(1.5, -1.5), alpha=0.12), pe.Normal()]))
legend = [("Treated", ORANGE, "120/130 → 100 km/h (06:00–19:00)"),
          ("Comparison", BLUE, "100 km/h before and after 2020"),
          ("Not included", GREY, "other / unclear limit")]
for k, (g, colour, note) in enumerate(legend):
    yy = ly + bh - 13000 - k * 17000
    ax.plot([lx + 7000, lx + 19000], [yy, yy], color=colour, lw=3.2, solid_capstyle="round", zorder=8)
    ax.text(lx + 24000, yy + 1200, g, fontsize=8.5, fontweight="bold", color=TEXT, va="bottom", zorder=8)
    ax.text(lx + bw - 6000, yy + 1200, f"{km[g]:,.0f} km", fontsize=8.5, color=TEXT, ha="right",
            va="bottom", zorder=8)
    ax.text(lx + 24000, yy - 1200, note, fontsize=7, color=MUTED, va="top", zorder=8)

# scale bar and north arrow (bottom right)
sx, sy = x1 - 66000, y0 + 6000
for i in range(2):
    ax.add_patch(Rectangle((sx + i * 25000, sy), 25000, 1800, fc=TEXT if i == 0 else "white",
                           ec=TEXT, lw=0.8, zorder=8))
for i, t in enumerate(["0", "25", "50 km"]):
    ax.text(sx + i * 25000, sy + 3800, t, fontsize=7, color=TEXT, ha="center", va="bottom")
nx, ny = x1 - 6000, y0 + 22000
ax.annotate("", xy=(nx, ny + 20000), xytext=(nx, ny), zorder=8,
            arrowprops=dict(arrowstyle="-|>,head_width=0.35,head_length=0.6", color=TEXT, lw=1.4))
ax.text(nx, ny + 22000, "N", fontsize=9, fontweight="bold", color=TEXT, ha="center", va="bottom")

# source
ax.text(x1 + 6000, y0 - 8000, "Data: INWEVA 2023, BRON 2018–2023 (Rijkswaterstaat); outline: CBS/PDOK",
        fontsize=6.5, color=MUTED, ha="right", va="bottom")

os.makedirs("figures", exist_ok=True)
for ext, kw in [("png", dict(dpi=300)), ("pdf", {})]:
    fig.savefig(f"figures/Figure_map_sections.{ext}", bbox_inches="tight", pad_inches=0.15,
                facecolor="white", **kw)
print("Saved figures/Figure_map_sections.png and .pdf")
