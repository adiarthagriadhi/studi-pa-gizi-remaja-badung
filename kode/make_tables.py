"""Ekspor tabel agregat (tanpa baris per siswa) untuk hub artikel. Label Inggris untuk naskah.
Input: analysed.pkl, results.pkl (dari analysis.py). Output: pkg/results/tables/*.csv + key_numbers.json
"""
import json
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from stats_utils import AREAS, kw, chi2, fdr, adj_ols, adj_logit, mixed_icc

warnings.filterwarnings("ignore")
OUT = Path("pkg/results/tables")
OUT.mkdir(parents=True, exist_ok=True)
d = pd.read_pickle("analysed.pkl")
R = pd.read_pickle("results.pkl")
T, rt = R["T"], R["rt"]
EN = {"Urban": "urban", "Transisi": "transitional", "Rural": "rural"}
AR = ["Urban", "Transisi", "Rural"]


def save(df, name):
    num = df.select_dtypes("number").columns
    pcols = [c for c in num if c == "p" or c.startswith("p_") or c.endswith("_p")]
    rest = [c for c in num if c not in pcols]
    df[rest] = df[rest].round(4)
    for c in pcols:  # p-values: 3 significant digits, never rounded to 0
        df[c] = df[c].map(lambda v: float(f"{v:.3g}") if pd.notna(v) else v)
    assert not ({c.lower() for c in df.columns} & {"id", "participant", "subject", "peserta", "sesi", "session"})
    df.to_csv(OUT / name, index=False)


# ---------------------------------------------------------------- Table 1
SEX = {"Laki-laki": "Boys", "Perempuan": "Girls"}
EDU = {"≤SD": "Primary or less", "SMP": "Junior secondary", "SMA/SMK": "Senior secondary", "Perguruan tinggi": "Tertiary"}
OCC = {"PNS/TNI/Polri/profesional": "Civil servant/military/police/professional", "Karyawan swasta": "Private employee",
       "Wiraswasta/pedagang": "Self-employed/trader", "Petani/peternak/nelayan": "Farmer/livestock/fisher",
       "Buruh/pekerja informal": "Labourer/informal worker", "Tidak bekerja/IRT/pensiun": "Not working/homemaker/retired"}
NUT = {"Sangat kurus": "Severe thinness", "Kurus": "Thinness", "Normal": "Normal", "Gizi lebih": "Overweight", "Obesitas": "Obesity"}
rows, tests = [], []
rows.append(["n", "", "n"] + [int((d.wilayah == a).sum()) for a in AR] + [len(d)])
for var, lab, mp, order in [("jk", "sex", SEX, list(SEX)), ("kelas", "grade", None, [7, 8, 9]),
                            ("status_gizi", "bmi_for_age_category", NUT, list(NUT)),
                            ("pendidikan_ortu", "highest_parental_education", EDU, list(EDU)),
                            ("pekerjaan_ortu", "highest_parental_occupation", OCC, list(OCC))]:
    tab = pd.crosstab(d[var], d["wilayah"]).reindex(order).reindex(columns=AR)
    tot = tab.sum(axis=1)
    for lev in order:
        name = mp[lev] if mp else str(lev)
        rows.append([lab, name, "n"] + [int(tab.loc[lev, a]) for a in AR] + [int(tot[lev])])
        rows.append([lab, name, "pct"] + [100 * tab.loc[lev, a] / tab[a].sum() for a in AR] + [100 * tot[lev] / tot.sum()])
    rows.append([lab, "(valid n)", "n"] + [int(tab[a].sum()) for a in AR] + [int(tot.sum())])
    c, p, dof, v = chi2(d, var)
    tests.append([lab, "chi-square", c, dof, p, "cramers_v", v])
for var, lab in [("tb_cm", "height_cm"), ("bb_kg", "weight_kg"), ("imt", "bmi_kg_m2"), ("baz", "bmi_for_age_z"), ("jml_keluarga", "household_size")]:
    for st in ["mean", "sd"]:
        f = (lambda s: s.mean()) if st == "mean" else (lambda s: s.std())
        rows.append([lab, "", st] + [f(d.loc[d.wilayah == a, var].dropna()) for a in AR] + [f(d[var].dropna())])
    rows.append([lab, "(valid n)", "n"] + [int(d.loc[d.wilayah == a, var].notna().sum()) for a in AR] + [int(d[var].notna().sum())])
    H, p, e = kw(d, var)
    tests.append([lab, "kruskal-wallis", H, 2, p, "epsilon_squared", e])
save(pd.DataFrame(rows, columns=["variable", "level", "statistic", *[EN[a] for a in AR], "total"]), "table1_characteristics.csv")
save(pd.DataFrame(tests, columns=["variable", "test", "statistic", "df", "p", "effect_size_type", "effect_size"]), "table1_tests.csv")

# ---------------------------------------------------------------- Table 2: PAQ-C
ITEM = {"pa_item1_checklist": "Leisure-time activity checklist (mean of 10)", "pa_pjok": "Physical education lessons (frequency)",
        "pa_sekolah": "Activity at school outside PE", "pa_setelah_sekolah": "Right after school", "pa_malam": "Evenings",
        "pa_akhir_pekan": "Weekend", "pa_intensitas": "Activity causing sweating/hard breathing",
        "pa_gambaran": "Overall description of activity", "paqc_skor": "PAQ-C composite score (8 items)",
        "paqc_skor_tanpa_pjok": "Composite without PE item (7 items)"}
p2 = T["T2_paqc_item"]
rows = []
for k, lab in ITEM.items():
    r = p2[p2["Item"].str.strip() != ""].iloc[list(ITEM).index(k)]
    a = adj_ols(d, k)
    rows.append([lab] + sum([[d.loc[d.wilayah == x, k].mean(), d.loc[d.wilayah == x, k].std()] for x in AR], []) +
                [r["p_KW"], r["epsilon2"], *a["Transisi"][:3], *a["Rural"][:3], a["p_global"], a["p_tren"], r["p_adj_FDR"]])
save(pd.DataFrame(rows, columns=["item", "urban_mean", "urban_sd", "transitional_mean", "transitional_sd", "rural_mean", "rural_sd",
                                 "p_kruskal", "epsilon_squared", "beta_transitional_vs_urban", "ci_low_transitional", "ci_high_transitional",
                                 "beta_rural_vs_urban", "ci_low_rural", "ci_high_rural", "p_adjusted_global", "p_trend", "p_adjusted_fdr"]),
     "table2_paqc_items.csv")
rows = []
for y, lab in [("paqc_skor", "primary (double-ticked cells missing)"), ("paqc_skor_alt", "sensitivity: double-ticked = mean of ticks"),
               ("paqc_skor_tanpa_pjok", "sensitivity: without PE item")]:
    a = adj_ols(d, y)
    mm = mixed_icc(d, y)
    for x in ["Transisi", "Rural"]:
        rows.append([lab, "OLS, HC3 robust SE", f"{EN[x]} vs urban", *a[x], a["p_tren"], np.nan])
        rows.append([lab, "linear mixed model, random school intercept", f"{EN[x]} vs urban", *mm[x], np.nan, mm["icc"]])
save(pd.DataFrame(rows, columns=["analysis", "model", "contrast", "beta", "ci_low", "ci_high", "p", "p_trend", "icc_school"]),
     "table2_paqc_models.csv")
import statsmodels.formula.api as smf
ms = smf.ols("paqc_skor ~ C(wilayah) + C(jk) + C(kelas)", data=d).fit(cov_type="HC3")
mi = smf.ols("paqc_skor ~ C(wilayah, Treatment('Urban')) * C(jk) + C(kelas)", data=d).fit(cov_type="HC3")
p_int = mi.wald_test("C(wilayah, Treatment('Urban'))[T.Transisi]:C(jk)[T.Perempuan] = 0, "
                     "C(wilayah, Treatment('Urban'))[T.Rural]:C(jk)[T.Perempuan] = 0", scalar=True).pvalue
sa = T["T2_paqc_jk_wilayah"].copy()
sa["area"] = sa["wilayah"].astype(str).map(EN)
sa["sex"] = sa["jk"].map(SEX)
sa = sa[["area", "sex", "count", "mean", "std", "ci_lo", "ci_hi"]].rename(columns={"count": "n", "std": "sd", "ci_lo": "ci_low", "ci_hi": "ci_high"})
save(sa, "table2_paqc_by_sex_area.csv")
cat = pd.crosstab(d["paqc_kategori"], d["wilayah"]).reindex(columns=AR)
catp = pd.crosstab(d["paqc_kategori"], d["wilayah"], normalize="columns").reindex(columns=AR) * 100
_, p_cat, _, v_cat = chi2(d, "paqc_kategori")
rows = [[str(c).replace("Rendah", "Low (<2.33)").replace("Sedang", "Moderate (2.33-3.66)").replace("Tinggi", "High (>3.66)")] +
        sum([[int(cat.loc[c, a]), catp.loc[c, a]] for a in AR], []) for c in cat.index]
save(pd.DataFrame(rows, columns=["category", "urban_n", "urban_pct", "transitional_n", "transitional_pct", "rural_n", "rural_pct"]),
     "table2_paqc_categories.csv")

# ---------------------------------------------------------------- Table 3: activity types
ACT = {"jalan_kaki": "Walking", "lari_jogging": "Running/jogging", "sepak_bola": "Football", "voli": "Volleyball",
       "basket": "Basketball", "renang": "Swimming", "senam_aerobik": "Gymnastics/aerobics", "pencak_silat": "Pencak silat",
       "bersepeda": "Cycling", "lainnya": "Other"}
rows, rows_s = [], []
for k, lab in ACT.items():
    c = f"pa_{k}"
    sub = d[d[c].notna()].copy()
    sub["any_"] = (sub[c] >= 2).astype(int)
    sub["freq_"] = (sub[c] >= 3).astype(int)
    _, p1, _, v1 = chi2(sub, "any_")
    _, p3, _, v3 = chi2(sub, "freq_")
    a = adj_logit(sub, "any_")
    ss = sub[sub.pendidikan_ortu.notna()]
    a2 = adj_logit(ss, "any_", " + C(pendidikan_ortu)")
    rows.append([lab] + [int((sub.wilayah == x).sum()) for x in AR] +
                [100 * sub.loc[sub.wilayah == x, "any_"].mean() for x in AR] + [p1, v1] +
                [100 * sub.loc[sub.wilayah == x, "freq_"].mean() for x in AR] + [p3, v3] +
                [*a["Transisi"][:3], *a["Rural"][:3], a["p_global"], a["p_tren"]] +
                [*a2["Transisi"][:3], *a2["Rural"][:3], a2["p_global"]])
    for jk in ["Laki-laki", "Perempuan"]:
        rows_s.append([lab, SEX[jk]] + [100 * sub.loc[(sub.wilayah == x) & (sub.jk == jk), "any_"].mean() for x in AR])
act = pd.DataFrame(rows, columns=["activity", "urban_n_valid", "transitional_n_valid", "rural_n_valid",
                                  "urban_pct_weekly", "transitional_pct_weekly", "rural_pct_weekly", "p_chi2_weekly", "cramers_v_weekly",
                                  "urban_pct_3plus", "transitional_pct_3plus", "rural_pct_3plus", "p_chi2_3plus", "cramers_v_3plus",
                                  "or_transitional", "or_transitional_ci_low", "or_transitional_ci_high",
                                  "or_rural", "or_rural_ci_low", "or_rural_ci_high", "p_adjusted_global", "p_trend",
                                  "or_transitional_ses", "or_transitional_ses_ci_low", "or_transitional_ses_ci_high",
                                  "or_rural_ses", "or_rural_ses_ci_low", "or_rural_ses_ci_high", "p_adjusted_global_ses"])
act["p_chi2_weekly_fdr"] = fdr(act["p_chi2_weekly"])
act["p_adjusted_global_fdr"] = fdr(act["p_adjusted_global"])
act["n_activity_types_mean_urban"] = np.nan
save(act.drop(columns=["n_activity_types_mean_urban"]), "table3_activity_types.csv")
save(pd.DataFrame(rows_s, columns=["activity", "sex", "urban_pct_weekly", "transitional_pct_weekly", "rural_pct_weekly"]),
     "table3_activity_types_by_sex.csv")
H, p_nj, e_nj = kw(d, "n_jenis_aktivitas")
nj = d.groupby("wilayah", observed=True)["n_jenis_aktivitas"].agg(["mean", "std", "median"]).reindex(AR)
save(pd.DataFrame([[EN[a], nj.loc[a, "mean"], nj.loc[a, "std"], nj.loc[a, "median"], p_nj, e_nj] for a in AR],
                  columns=["area", "mean", "sd", "median", "p_kruskal", "epsilon_squared"]), "table3_number_of_activity_types.csv")

# ---------------------------------------------------------------- Table 4-7: diet
FOOD = {"nasi": "Rice", "mie_instan": "Instant noodles", "tempe": "Tempeh", "tahu": "Tofu", "ayam": "Chicken",
        "ikan": "Fish", "telur": "Egg", "sayur_kol_wortel": "Vegetables (cabbage/carrot)", "bayam": "Spinach",
        "kangkung": "Water spinach", "sambal": "Chilli sauce (sambal)", "pisang": "Banana", "mangga": "Mango", "jeruk": "Orange",
        "minuman_manis": "Sweetened drinks (tea/syrup)", "minuman_bersoda": "Soft drinks (soda)", "susu": "Milk",
        "gorengan": "Fried snacks (gorengan)", "jajanan": "Packaged snacks"}
UNIT_EN = {"piring penuh": "full plate", "bungkus": "pack", "potong": "piece", "potong sedang": "medium piece", "butir": "egg",
           "mangkok": "bowl", "sendok makan": "tablespoon", "buah": "fruit/piece", "buah sedang": "medium fruit", "gelas": "glass",
           "kaleng": "can", "bungkus sedang": "medium pack"}
rows = []
for name, unit, _ in pd.read_pickle("meta.pkl")["FOODS"]:
    fq, xw, po = f"ffq_{name}_frek", f"ffq_{name}_x_mgg", f"ffq_{name}_porsi"
    d["_s"] = (d[fq] >= 3).astype(int)
    d["_h"] = (d[fq] >= 4).astype(int)
    H, p, e = kw(d, fq)
    a = adj_logit(d, "_s")
    cons = d[d[fq] > 0]
    Hp, pp, ep = kw(cons, po)
    rows.append([FOOD[name], UNIT_EN[unit]] + [d.loc[d.wilayah == x, xw].median() for x in AR] +
                [100 * d.loc[d.wilayah == x, "_s"].mean() for x in AR] + [100 * d.loc[d.wilayah == x, "_h"].mean() for x in AR] +
                [p, e, *a["Transisi"][:3], *a["Rural"][:3], a["p_global"], a["p_tren"]] +
                [cons.loc[cons.wilayah == x, po].mean() for x in AR] + [pp])
ffq = pd.DataFrame(rows, columns=["food", "portion_unit", "urban_median_times_week", "transitional_median_times_week", "rural_median_times_week",
                                  "urban_pct_3plus_week", "transitional_pct_3plus_week", "rural_pct_3plus_week",
                                  "urban_pct_daily", "transitional_pct_daily", "rural_pct_daily",
                                  "p_kruskal_frequency", "epsilon_squared", "or_3plus_transitional", "or_3plus_transitional_ci_low",
                                  "or_3plus_transitional_ci_high", "or_3plus_rural", "or_3plus_rural_ci_low", "or_3plus_rural_ci_high",
                                  "p_adjusted_global", "p_trend", "urban_mean_portion_consumers", "transitional_mean_portion_consumers",
                                  "rural_mean_portion_consumers", "p_kruskal_portion"])
ffq["p_kruskal_frequency_fdr"] = fdr(ffq["p_kruskal_frequency"])
ffq["p_adjusted_global_fdr"] = fdr(ffq["p_adjusted_global"])
ffq["p_kruskal_portion_fdr"] = fdr(ffq["p_kruskal_portion"])
save(ffq, "table4_food_frequency.csv")
d = d.drop(columns=["_s", "_h"])

GRP_EN = {"Makanan pokok": "Staples (rice, instant noodles)", "Lauk nabati": "Plant protein (tempeh, tofu)",
          "Lauk hewani & susu": "Animal protein and milk", "Sayur": "Vegetables (3 items)", "Buah": "Fruit (3 items)",
          "Minuman manis & soda": "Sweetened drinks and soda", "Gorengan & jajanan": "Fried and packaged snacks"}
g = T["T5_kelompok_pangan"]
rows = []
for _, r in g.iterrows():
    gname = r["Kelompok pangan"]
    col = [c for c in d.columns if c.startswith("kel_") and c.replace("kel_", "").replace("_x_mgg", "").replace("_", "") ==
           "".join(ch for ch in gname.lower() if ch.isalnum())][0]
    q = [d.loc[d.wilayah == x, col].quantile([.25, .5, .75]).tolist() for x in AR]
    a = adj_ols(d, col)
    rows.append([GRP_EN[gname]] + sum(q, []) + [r["p_KW"], r["epsilon2"], *a["Transisi"][:3], *a["Rural"][:3], a["p_global"], a["p_tren"], r["p_adj_FDR"]])
save(pd.DataFrame(rows, columns=["food_group", "urban_q1", "urban_median", "urban_q3", "transitional_q1", "transitional_median",
                                 "transitional_q3", "rural_q1", "rural_median", "rural_q3", "p_kruskal", "epsilon_squared",
                                 "beta_transitional", "ci_low_transitional", "ci_high_transitional", "beta_rural", "ci_low_rural",
                                 "ci_high_rural", "p_adjusted_global", "p_trend", "p_adjusted_fdr"]), "table5_food_groups_times_week.csv")

IND = {"ind_hewani_harian": "Animal protein (chicken/fish/egg) >=7 times/week", "ind_susu_harian": "Milk daily",
       "ind_ssb_harian": "Sweetened drinks or soda daily", "ind_soda_mingguan": "Soft drinks >=1 time/week",
       "ind_mie_3x": "Instant noodles >=3 times/week", "ind_jajan_harian": "Fried or packaged snacks daily",
       "ind_buah_2": "Fruit >=2 servings/day", "ind_sayur_3": "Vegetables >=3 servings/day",
       "ind_bs_5": "Fruit + vegetables >=5 servings/day"}
rows = []
for k, lab in IND.items():
    _, p, _, v = chi2(d, k)
    a = adj_logit(d, k)
    a2 = adj_logit(d[d.pendidikan_ortu.notna()], k, " + C(pendidikan_ortu)")
    rows.append([lab] + [100 * d.loc[d.wilayah == x, k].mean() for x in AR] + [100 * d[k].mean(), p, v,
                 *a["Transisi"][:3], *a["Rural"][:3], a["p_global"], a["p_tren"], *a2["Transisi"][:3], *a2["Rural"][:3], a2["p_global"]])
ind = pd.DataFrame(rows, columns=["indicator", "urban_pct", "transitional_pct", "rural_pct", "total_pct", "p_chi2", "cramers_v",
                                  "or_transitional", "or_transitional_ci_low", "or_transitional_ci_high", "or_rural", "or_rural_ci_low",
                                  "or_rural_ci_high", "p_adjusted_global", "p_trend", "or_transitional_ses", "or_transitional_ses_ci_low",
                                  "or_transitional_ses_ci_high", "or_rural_ses", "or_rural_ses_ci_low", "or_rural_ses_ci_high",
                                  "p_adjusted_global_ses"])
ind["p_adjusted_global_fdr"] = fdr(ind["p_adjusted_global"])
save(ind, "table6_diet_indicators.csv")
rows = []
for k, lab in [("porsi_sayur_hari", "Vegetable servings/day"), ("porsi_buah_hari", "Fruit servings/day"),
               ("porsi_buahsayur_hari", "Fruit + vegetable servings/day"), ("ssb_ml_hari", "Sweetened drinks + soda (ml/day)")]:
    H, p, e = kw(d, k)
    rows.append([lab] + sum([d.loc[d.wilayah == x, k].quantile([.25, .5, .75]).tolist() for x in AR], []) +
                d[k].quantile([.25, .5, .75]).tolist() + [p, e])
save(pd.DataFrame(rows, columns=["variable", "urban_q1", "urban_median", "urban_q3", "transitional_q1", "transitional_median",
                                 "transitional_q3", "rural_q1", "rural_median", "rural_q3", "total_q1", "total_median", "total_q3",
                                 "p_kruskal", "epsilon_squared"]), "table6_fruit_vegetable_ssb_amounts.csv")
lo = T["T7_pola_muatan"].copy()
lo["Makanan"] = [FOOD[n] for n, _, _ in pd.read_pickle("meta.pkl")["FOODS"]]
lo.columns = ["food", "pattern1_plant_protein_veg_fruit", "pattern2_snacks_sweet_drinks", "pattern3_rice_chicken_sambal"]
save(lo, "table7_diet_pattern_loadings.csv")
rows = []
ve = R["diet_summary"]["var_expl"]
for j, lab in enumerate(["Pattern 1: plant protein-vegetables-fruit", "Pattern 2: snacks-sweetened drinks", "Pattern 3: rice-chicken-sambal"]):
    c = f"pola{j + 1}"
    H, p, e = kw(d, c)
    a = adj_ols(d, c)
    rows.append([lab, ve[j]] + sum([[d.loc[d.wilayah == x, c].mean(), d.loc[d.wilayah == x, c].std()] for x in AR], []) +
                [p, e, *a["Transisi"][:3], *a["Rural"][:3], a["p_global"], a["p_tren"]])
save(pd.DataFrame(rows, columns=["pattern", "pct_variance_explained", "urban_mean", "urban_sd", "transitional_mean", "transitional_sd",
                                 "rural_mean", "rural_sd", "p_kruskal", "epsilon_squared", "beta_transitional", "ci_low_transitional",
                                 "ci_high_transitional", "beta_rural", "ci_low_rural", "ci_high_rural", "p_adjusted_global", "p_trend"]),
     "table7_diet_pattern_scores.csv")
ev = R["diet_summary"]["eigen"]
save(pd.DataFrame({"component": range(1, len(ev) + 1), "eigenvalue": ev}), "table7_diet_pattern_eigenvalues.csv")

# ---------------------------------------------------------------- Table 8: barriers
HB = {"hb_waktu": "No time (study, tutoring, homework)", "hb_fasilitas": "No facilities", "hb_sakit_cedera": "Illness or injury",
      "hb_tidak_suka": "Dislike of sport", "hb_kegiatan_keluarga_adat": "Family/customary/religious/arts activities (recoded 'other')",
      "hb_cuaca": "Weather/rain (recoded 'other')", "hb_lelah_malas": "Tired/lazy/low motivation (recoded 'other')",
      "hb_tidak_ada_teman": "No companion (recoded 'other')", "hb_tidak_ada_hambatan": "No barrier stated (written in 'other')"}
rows = []
for k, lab in HB.items():
    _, p, _, v = chi2(d, k)
    try:
        a = adj_logit(d, k)
        oc = [*a["Transisi"][:3], *a["Rural"][:3], a["p_global"], a["p_tren"]]
    except Exception:
        oc = [np.nan] * 8
    rows.append([lab] + [100 * d.loc[d.wilayah == x, k].mean() for x in AR] + [100 * d[k].mean()] +
                [100 * d.loc[d.jk == s, k].mean() for s in ["Laki-laki", "Perempuan"]] + [p, v] + oc)
hb = pd.DataFrame(rows, columns=["barrier", "urban_pct", "transitional_pct", "rural_pct", "total_pct", "boys_pct", "girls_pct", "p_chi2",
                                 "cramers_v", "or_transitional", "or_transitional_ci_low", "or_transitional_ci_high", "or_rural",
                                 "or_rural_ci_low", "or_rural_ci_high", "p_adjusted_global", "p_trend"])
hb["p_chi2_fdr"] = fdr(hb["p_chi2"])
save(hb, "table8_barriers.csv")
bp = T["T8_hambatan_vs_PA"].copy()
bp["Hambatan"] = [HB[k] for k in ["hb_waktu", "hb_fasilitas", "hb_sakit_cedera", "hb_tidak_suka"]]
bp.columns = ["barrier", "beta_paqc_composite", "ci_low", "ci_high", "p"]
save(bp, "table8_barriers_vs_paqc.csv")
wk = (d.groupby(["wilayah", "kelas"], observed=True)["hb_waktu"].mean() * 100).unstack().reindex(AR)
save(pd.DataFrame([[EN[a]] + wk.loc[a].tolist() for a in AR], columns=["area", "grade7_pct", "grade8_pct", "grade9_pct"]),
     "table8_time_barrier_by_grade.csv")

# ---------------------------------------------------------------- Table 9: school consistency (aggregate per school)
s = d[d.sekolah != "SMPN 2 KUTA"].copy()
for k, c in [("walking", "pa_jalan_kaki"), ("volleyball", "pa_voli"), ("gymnastics", "pa_senam_aerobik"), ("swimming", "pa_renang"),
             ("basketball", "pa_basket")]:
    s[k] = (s[c] >= 2).where(s[c].notna()).astype(float) * 100
s["chicken_3plus"] = (s.ffq_ayam_frek >= 3) * 100.0
s["banana_3plus"] = (s.ffq_pisang_frek >= 3) * 100.0
s["orange_3plus"] = (s.ffq_jeruk_frek >= 3) * 100.0
for k in ["ind_susu_harian", "ind_ssb_harian", "hb_waktu", "hb_sakit_cedera", "hb_tidak_suka"]:
    s[k] = s[k] * 100.0
agg = s.groupby(["wilayah", "sekolah"], observed=True).agg(
    n=("paqc_skor", "size"), paqc_mean=("paqc_skor", "mean"), walking_pct=("walking", "mean"), volleyball_pct=("volleyball", "mean"),
    gymnastics_pct=("gymnastics", "mean"), swimming_pct=("swimming", "mean"), basketball_pct=("basketball", "mean"),
    chicken_3plus_pct=("chicken_3plus", "mean"), milk_daily_pct=("ind_susu_harian", "mean"), ssb_daily_pct=("ind_ssb_harian", "mean"),
    banana_3plus_pct=("banana_3plus", "mean"), orange_3plus_pct=("orange_3plus", "mean"), barrier_time_pct=("hb_waktu", "mean"),
    barrier_injury_pct=("hb_sakit_cedera", "mean"), barrier_dislike_pct=("hb_tidak_suka", "mean")).reset_index()
agg.insert(0, "area", agg.pop("wilayah").astype(str).map(EN))
agg = agg.rename(columns={"sekolah": "school"})
save(agg, "table9_school_consistency.csv")

# ---------------------------------------------------------------- Table 10: test-retest
rows = [["paqc_composite", "ICC(2,1) absolute agreement", rt["icc_komposit"], rt["n_pasang"]]]
LABK = {"pjok": "pe_lessons", "sekolah": "school_outside_pe", "setelah": "after_school", "malam": "evenings",
        "akhir_pekan": "weekend", "intensitas": "sweating_hard_breathing", "gambaran": "overall_description"}
for k, v in rt["kappa_pa_items"].items():
    rows.append([f"paqc_item_{LABK[k]}", "quadratic weighted kappa", v, rt["n_pasang"]])
rows.append(["ffq_frequency_items_median", "quadratic weighted kappa (median of 19 items)", rt["kappa_ffq_median"], rt["n_pasang"]])
rows.append(["ffq_frequency_items_min", "quadratic weighted kappa (minimum of 19 items)", rt["kappa_ffq_range"][0], rt["n_pasang"]])
rows.append(["ffq_frequency_items_max", "quadratic weighted kappa (maximum of 19 items)", rt["kappa_ffq_range"][1], rt["n_pasang"]])
rows.append(["interval_days_median", "median days between the two submissions", rt["median_jarak_hari"], rt["n_pasang"]])
save(pd.DataFrame(rows, columns=["measure", "statistic", "value", "n_pairs"]), "table10_test_retest.csv")

# ---------------------------------------------------------------- cleaning log + key numbers
log = pd.read_csv("coding_log.csv")
save(log.rename(columns={"langkah": "step", "keterangan": "decision", "n": "n"}), "cleaning_log.csv")
a = adj_ols(d, "paqc_skor")
key = {
    "n_responses_raw": 1977, "n_duplicate_rows_removed": 79, "n_students": int(len(d)),
    "n_by_area": {EN[x]: int((d.wilayah == x).sum()) for x in AR},
    "n_girls": int((d.jk == "Perempuan").sum()), "n_boys": int((d.jk == "Laki-laki").sum()),
    "n_schools": 5, "data_collection": "2025-09-17 to 2025-10-02",
    "paqc_cronbach_alpha_8_items": R["pa_summary"]["alpha"], "paqc_cronbach_alpha_7_items": R["pa_summary"]["alpha_tanpa_pjok"],
    "paqc_composite_mean_by_area": {EN[x]: d.loc[d.wilayah == x, "paqc_skor"].mean() for x in AR},
    "paqc_beta_girls_vs_boys": {"beta": float(ms.params["C(jk)[T.Perempuan]"]),
                                "ci_low": float(ms.conf_int().loc["C(jk)[T.Perempuan]"][0]),
                                "ci_high": float(ms.conf_int().loc["C(jk)[T.Perempuan]"][1]), "p": float(ms.pvalues["C(jk)[T.Perempuan]"])},
    "paqc_area_by_sex_interaction_p": float(p_int),
    "paqc_category_chi2_p": float(p_cat), "paqc_category_cramers_v": float(v_cat),
    "n_double_ticked_respondents": int(d[[c for c in d.columns if c.endswith("_ganda")]].any(axis=1).sum()),
    "bmi_for_age_valid_n": int(d.status_gizi.notna().sum()),
    "diet_pattern_total_variance_pct": float(sum(ve)),
    "fruit_veg_5plus_total_pct": float(100 * d["ind_bs_5"].mean()),
    "fruit_veg_servings_median_total": float(d["porsi_buahsayur_hari"].median()),
    "barrier_time_total_pct": float(100 * d["hb_waktu"].mean()),
    "test_retest_pairs": int(rt["n_pasang"]),
}
(OUT / "key_numbers.json").write_text(json.dumps(key, indent=2, default=float), encoding="utf-8")
print(sorted(p.name for p in OUT.iterdir()))
