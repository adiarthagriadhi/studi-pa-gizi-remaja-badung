"""Gambar naskah (tanpa judul di dalam gambar; keterangan ditulis di naskah) (PNG 300 dpi + PDF) dari tabel agregat di hasil/tables/.
Wilayah = ramp ordinal satu hue (biru gelap → terang, divalidasi), ditambah bentuk penanda untuk cetak abu-abu."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
TAB = ROOT / "hasil/tables"
FIG = ROOT / "hasil/figures"
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 9, "axes.edgecolor": "#8a8a85",
                     "axes.linewidth": 0.6, "xtick.color": "#4a4a46", "ytick.color": "#1f1f1c",
                     "pdf.fonttype": 42, "svg.fonttype": "none"})
AREAS = [("urban", "Urban", "#104281", "o"), ("transitional", "Suburban", "#3987e5", "s"), ("rural", "Rural", "#86b6ef", "^")]
INK, MUTED, GRID = "#1f1f1c", "#6b6b66", "#e4e3df"


def dotplot(df, label_col, col_fmt, title, xlabel, keys, fname, height):
    df = df.copy()
    df["diff"] = df[col_fmt.format("rural")] - df[col_fmt.format("urban")]
    df = df.sort_values("diff", ascending=False).reset_index(drop=True)  # top row = largest rural excess? -> plot bottom-up
    fig, ax = plt.subplots(figsize=(6.5, height))
    for i, r in df.iterrows():
        vals = [r[col_fmt.format(a)] for a, *_ in AREAS]
        ax.plot([min(vals), max(vals)], [i, i], color="#cfcec9", lw=2.2, zorder=1, solid_capstyle="round")
        for (a, lab, col, mk), v in zip(AREAS, vals):
            ax.scatter(v, i, s=34, marker=mk, color=col, edgecolor="#0d366b", linewidth=0.6, zorder=3,
                       label=lab if i == 0 else None)
        if r[label_col] in keys:
            u, ru = r[col_fmt.format("urban")], r[col_fmt.format("rural")]
            hi, lo = max(vals), min(vals)
            for v, tag in [(u, "U"), (ru, "R")]:
                if v == hi:
                    ax.text(hi + 1.6, i, f"{tag} {v:.0f}%", va="center", ha="left", fontsize=7.5, color=MUTED)
                elif v == lo:
                    ax.text(lo - 1.6, i, f"{tag} {v:.0f}%", va="center", ha="right", fontsize=7.5, color=MUTED)
                else:  # nilai di tengah: label di bawah penandanya sendiri
                    ax.text(v, i - 0.3, f"{tag} {v:.0f}%", va="top", ha="center", fontsize=7.5, color=MUTED)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df[label_col])
    for t in ax.get_yticklabels():
        if t.get_text() in keys:
            t.set_fontweight("bold")
    ax.set_ylim(-0.95, len(df) - 0.3)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels([f"{t}%" for t in [0, 25, 50, 75, 100]])
    ax.xaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=8, handletextpad=0.3, columnspacing=1.4)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(FIG / f"{fname}.{ext}", dpi=300)
    plt.close(fig)


act = pd.read_csv(TAB / "table3_activity_types.csv")
dotplot(act, "activity", "{}_pct_weekly",
        "Fig. 1. Participation in leisure-time activities by area",
        "Students doing the activity at least once in the past 7 days (%)",
        {"Walking", "Swimming", "Volleyball", "Gymnastics/aerobics"}, "fig1_activity_types_by_area", 3.6)
ffq = pd.read_csv(TAB / "table4_food_frequency.csv")
dotplot(ffq, "food", "{}_pct_3plus_week",
        "Fig. 2. Frequent consumption of foods and drinks by area",
        "Students consuming the item at least 3–4 times per week in the past month (%)",
        {"Chicken", "Milk", "Sweetened drinks (tea/syrup)", "Banana", "Orange"}, "fig2_food_frequency_by_area", 5.4)

# Fig 3: hambatan utama (batang horizontal berkelompok, dari nol)
hb = pd.read_csv(TAB / "table8_barriers.csv").head(4)
fig, ax = plt.subplots(figsize=(6.5, 3.4))
bh, gap = 0.26, 0.02
for gi, (_, r) in enumerate(hb.iterrows()):
    for j, (a, lab, col, _) in enumerate(AREAS):
        y = gi + (j - 1) * (bh + gap)
        v = r[f"{a}_pct"]
        ax.barh(y, v, height=bh, color=col, edgecolor="#0d366b", linewidth=0.5, label=lab if gi == 0 else None)
        ax.text(v + 0.8, y, f"{v:.1f}%", va="center", fontsize=7.5, color=MUTED)
ax.set_yticks(range(len(hb)))
ax.set_yticklabels(hb["barrier"])
ax.invert_yaxis()
ax.set_xlim(0, 75)
ax.set_xticks([])
for s in ["top", "right", "bottom"]:
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=8)
fig.text(0.01, 0.01, "Multiple answers allowed; 'other' answers recoded into matching categories.", fontsize=7, color=MUTED)
fig.tight_layout(rect=(0, 0.04, 1, 1))
for ext in ["png", "pdf"]:
    fig.savefig(FIG / f"fig3_pa_barriers_by_area.{ext}", dpi=300)
plt.close(fig)
print(sorted(p.name for p in FIG.iterdir()))
