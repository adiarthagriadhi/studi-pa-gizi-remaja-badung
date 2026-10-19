"""Analisis pola aktivitas fisik, pola makan, dan hambatan menurut wilayah (urban/transisi/rural)."""
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from stats_utils import (AREAS, kw, dunn, chi2, fdr, adj_ols, adj_logit, mixed_icc, cronbach, wkappa, icc21)

warnings.filterwarnings("ignore")
d = pd.read_pickle("clean.pkl")
meta = pd.read_pickle("meta.pkl")
d["wilayah"] = pd.Categorical(d["wilayah"], AREAS, ordered=True)
N = d["wilayah"].value_counts().reindex(AREAS)
T = {}  # semua tabel hasil


def pct(s):
    return 100 * s.mean()


def msd(s):
    return f"{s.mean():.2f} ± {s.std():.2f}"


def miqr(s):
    q = s.quantile([.25, .5, .75])
    return f"{q[.5]:.2f} ({q[.25]:.2f}–{q[.75]:.2f})"


# =============================================================== 1. karakteristik
rows = []


def cat_rows(var, label, order=None):
    tab = pd.crosstab(d[var], d["wilayah"])
    if order:
        tab = tab.reindex(order)
    tot = d[var].value_counts().reindex(tab.index)
    chi, p, _, v = chi2(d, var)
    rows.append([label, "", "", "", "", f"χ²={chi:.1f}; p={p:.3g}; V={v:.2f}"])
    for lev in tab.index:
        cells = [f"{tab.loc[lev, a]} ({100 * tab.loc[lev, a] / tab[a].sum():.1f})" for a in AREAS]
        rows.append([f"   {lev}"] + cells + [f"{tot[lev]} ({100 * tot[lev] / tot.sum():.1f})", ""])


def num_rows(var, label):
    H, p, e = kw(d, var)
    cells = [msd(d.loc[d.wilayah == a, var].dropna()) for a in AREAS]
    rows.append([label] + cells + [msd(d[var].dropna()), f"KW H={H:.1f}; p={p:.3g}"])


rows.append(["n", *[str(N[a]) for a in AREAS], str(len(d)), ""])
cat_rows("jk", "Jenis kelamin, n (%)")
cat_rows("kelas", "Kelas, n (%)")
num_rows("tb_cm", "Tinggi badan (cm), rerata ± SB")
num_rows("bb_kg", "Berat badan (kg), rerata ± SB")
num_rows("imt", "IMT (kg/m²), rerata ± SB")
num_rows("baz", "IMT/U (z-skor)†, rerata ± SB")
cat_rows("status_gizi", "Status gizi IMT/U†, n (%)", ["Sangat kurus", "Kurus", "Normal", "Gizi lebih", "Obesitas"])
cat_rows("pendidikan_ortu", "Pendidikan tertinggi orang tua, n (%)", ["≤SD", "SMP", "SMA/SMK", "Perguruan tinggi"])
cat_rows("pekerjaan_ortu", "Pekerjaan orang tua (kategori tertinggi), n (%)",
         ["PNS/TNI/Polri/profesional", "Karyawan swasta", "Wiraswasta/pedagang", "Petani/peternak/nelayan",
          "Buruh/pekerja informal", "Tidak bekerja/IRT/pensiun"])
num_rows("jml_keluarga", "Jumlah anggota keluarga, rerata ± SB")
T["T1_karakteristik"] = pd.DataFrame(rows, columns=["Variabel", *AREAS, "Total", "Uji"])

# per sekolah (konsistensi dalam wilayah)
sch = d.groupby(["wilayah", "sekolah"], observed=True).agg(
    n=("id", "size"), perempuan_pct=("jk", lambda s: 100 * (s == "Perempuan").mean()),
    paqc=("paqc_skor", "mean"), gizi_lebih_obes_pct=("status_gizi", lambda s: 100 * s.isin(["Gizi lebih", "Obesitas"]).mean()))
T["T_sekolah"] = sch.reset_index()

# =============================================================== 2. aktivitas fisik
items = meta["items"]
ITEM_LAB = {"pa_item1_checklist": "Aktivitas waktu luang (rerata 10 jenis)", "pa_pjok": "Frekuensi PJOK",
            "pa_sekolah": "Aktivitas fisik di sekolah (selain PJOK)", "pa_setelah_sekolah": "Setelah pulang sekolah",
            "pa_malam": "Malam hari", "pa_akhir_pekan": "Akhir pekan", "pa_intensitas": "Aktivitas berkeringat/terengah",
            "pa_gambaran": "Gambaran umum aktivitas", "paqc_skor": "SKOR KOMPOSIT PAQ-C (8 item)",
            "paqc_skor_tanpa_pjok": "Skor komposit tanpa item PJOK"}
alpha = cronbach(d[items])
alpha_np = cronbach(d[[i for i in items if i != "pa_pjok"]])
rows = []
for it in items + ["paqc_skor", "paqc_skor_tanpa_pjok"]:
    H, p, e = kw(d, it)
    a = adj_ols(d, it)
    rows.append([ITEM_LAB[it]] + [msd(d.loc[d.wilayah == x, it].dropna()) for x in AREAS] +
                [p, e, a["Transisi"][0], a["Rural"][0], a["p_global"], a["p_tren"]])
pa = pd.DataFrame(rows, columns=["Item", *AREAS, "p_KW", "epsilon2", "β_Transisi_vs_Urban", "β_Rural_vs_Urban",
                                 "p_adj_global", "p_tren"])
pa["p_adj_FDR"] = fdr(pa["p_adj_global"])
T["T2_paqc_item"] = pa
T["T2_paqc_dunn"] = dunn(d, "paqc_skor")

# model inti skor komposit (detail + model campuran + sensitivitas)
core = []
for y, lab in [("paqc_skor", "Analisis utama (sel ganda = missing)"),
               ("paqc_skor_alt", "Sensitivitas: sel ganda = rerata centang"),
               ("paqc_skor_tanpa_pjok", "Sensitivitas: tanpa item PJOK")]:
    a = adj_ols(d, y)
    mm = mixed_icc(d, y)
    core.append([lab, *[f"{a[x][0]:+.2f} ({a[x][1]:+.2f} s.d. {a[x][2]:+.2f}); p={a[x][3]:.3g}" for x in ["Transisi", "Rural"]],
                 a["p_tren"], *[f"{mm[x][0]:+.2f} ({mm[x][1]:+.2f} s.d. {mm[x][2]:+.2f})" for x in ["Transisi", "Rural"]], mm["icc"]])
T["T2_paqc_model"] = pd.DataFrame(core, columns=["Analisis", "β Transisi vs Urban (OLS-HC3)", "β Rural vs Urban (OLS-HC3)",
                                                 "p tren", "β Transisi (model campuran)", "β Rural (model campuran)", "ICC sekolah"])

# interaksi jenis kelamin
import statsmodels.formula.api as smf
mi = smf.ols("paqc_skor ~ C(wilayah, Treatment('Urban')) * C(jk) + C(kelas)", data=d).fit(cov_type="HC3")
p_int = mi.wald_test("C(wilayah, Treatment('Urban'))[T.Transisi]:C(jk)[T.Perempuan] = 0, "
                     "C(wilayah, Treatment('Urban'))[T.Rural]:C(jk)[T.Perempuan] = 0", scalar=True).pvalue
sexarea = d.groupby(["wilayah", "jk"], observed=True)["paqc_skor"].agg(["mean", "std", "count"]).reset_index()
sexarea["se"] = sexarea["std"] / np.sqrt(sexarea["count"])
sexarea["ci_lo"] = sexarea["mean"] - 1.96 * sexarea["se"]
sexarea["ci_hi"] = sexarea["mean"] + 1.96 * sexarea["se"]
T["T2_paqc_jk_wilayah"] = sexarea
p_sex = adj_ols(d, "paqc_skor")  # placeholder for structure
ms = smf.ols("paqc_skor ~ C(wilayah) + C(jk) + C(kelas)", data=d).fit(cov_type="HC3")
beta_sex = (ms.params["C(jk)[T.Perempuan]"], *ms.conf_int().loc["C(jk)[T.Perempuan]"], ms.pvalues["C(jk)[T.Perempuan]"])

# kategori
cat = pd.crosstab(d["paqc_kategori"], d["wilayah"], normalize="columns").mul(100).round(1)
chi, p_cat, _, v_cat = chi2(d, "paqc_kategori")
T["T2_paqc_kategori"] = cat.reset_index()

# jenis aktivitas waktu luang: % >= 1x/minggu & % >= 3x/minggu
act_lab = {"jalan_kaki": "Berjalan kaki", "lari_jogging": "Lari/jogging", "sepak_bola": "Sepak bola", "voli": "Voli",
           "basket": "Basket", "renang": "Renang", "senam_aerobik": "Senam/aerobik", "pencak_silat": "Pencak silat",
           "bersepeda": "Bersepeda", "lainnya": "Lainnya"}
rows = []
for n_, lab in act_lab.items():
    c = f"pa_{n_}"
    sub = d[d[c].notna()].copy()
    sub["ikut"] = (sub[c] >= 2).astype(int)
    sub["sering"] = (sub[c] >= 3).astype(int)
    _, p1, _, v1 = chi2(sub, "ikut")
    _, p3, _, v3 = chi2(sub, "sering")
    a = adj_logit(sub, "ikut")
    rows.append([lab, *[pct(sub.loc[sub.wilayah == x, "ikut"]) for x in AREAS], p1, v1,
                 *[pct(sub.loc[sub.wilayah == x, "sering"]) for x in AREAS], p3, v3,
                 a["Transisi"][0], a["Rural"][0], a["p_global"]])
acts = pd.DataFrame(rows, columns=["Aktivitas", *[f"ikut_{x}" for x in AREAS], "p_ikut", "V_ikut",
                                   *[f"sering_{x}" for x in AREAS], "p_sering", "V_sering",
                                   "OR_ikut_Transisi", "OR_ikut_Rural", "p_adj_ikut"])
acts["p_ikut_FDR"] = fdr(acts["p_ikut"])
acts["p_sering_FDR"] = fdr(acts["p_sering"])
T["T3_jenis_aktivitas"] = acts

# jenis aktivitas menurut jenis kelamin x wilayah (% ikut)
rows = []
for n_, lab in act_lab.items():
    c = f"pa_{n_}"
    for jk in ["Laki-laki", "Perempuan"]:
        rows.append([lab, jk] + [pct(d.loc[(d.wilayah == x) & (d.jk == jk) & d[c].notna(), c] >= 2) for x in AREAS])
T["T3_aktivitas_jk"] = pd.DataFrame(rows, columns=["Aktivitas", "JK", *AREAS])

# distribusi kategori item domain waktu (untuk grafik bertumpuk)
dist = {}
for it in ["pa_sekolah", "pa_setelah_sekolah", "pa_malam", "pa_akhir_pekan", "pa_intensitas", "pa_gambaran", "pa_pjok"]:
    dist[it] = pd.crosstab(d["wilayah"], d[it], normalize="index").mul(100).round(1)
T["T2_distribusi_item"] = pd.concat(dist, names=["item"]).reset_index()

d["n_jenis_aktivitas"] = d["n_jenis_aktivitas"]
H, p_nj, e_nj = kw(d, "n_jenis_aktivitas")
nj = d.groupby("wilayah", observed=True)["n_jenis_aktivitas"].agg(["mean", "std", "median"])

pa_summary = {"alpha": alpha, "alpha_tanpa_pjok": alpha_np, "p_interaksi_jk": p_int, "beta_perempuan": beta_sex,
              "p_kategori": p_cat, "V_kategori": v_cat, "p_n_jenis": p_nj, "eps_n_jenis": e_nj, "n_jenis": nj}

# sensitivitas: + pendidikan orang tua untuk temuan jenis aktivitas utama
rows = []
dd = d[d.pendidikan_ortu.notna()].copy()
for n_ in ["jalan_kaki", "voli", "senam_aerobik", "renang", "basket"]:
    c = f"pa_{n_}"
    sub = dd[dd[c].notna()].copy()
    sub["ikut"] = (sub[c] >= 2).astype(int)
    a0 = adj_logit(sub, "ikut")
    a1 = adj_logit(sub, "ikut", " + C(pendidikan_ortu)")
    rows.append([act_lab[n_], a0["Transisi"][0], a0["Rural"][0], a1["Transisi"][0], a1["Rural"][0], a1["p_global"]])
T["S_aktivitas_ses"] = pd.DataFrame(rows, columns=["Aktivitas", "OR_Transisi", "OR_Rural", "OR_Transisi_+pendidikan",
                                                   "OR_Rural_+pendidikan", "p_global_+pendidikan"])

# =============================================================== 3. pola makan
FOODS = meta["FOODS"]
FOOD_LAB = {"nasi": "Nasi", "mie_instan": "Mi instan", "tempe": "Tempe", "tahu": "Tahu", "ayam": "Ayam",
            "ikan": "Ikan", "telur": "Telur", "sayur_kol_wortel": "Sayur (kol/wortel)", "bayam": "Bayam",
            "kangkung": "Kangkung", "sambal": "Sambal", "pisang": "Pisang", "mangga": "Mangga", "jeruk": "Jeruk",
            "minuman_manis": "Minuman manis", "minuman_bersoda": "Minuman bersoda", "susu": "Susu",
            "gorengan": "Gorengan", "jajanan": "Jajanan kemasan"}
rows = []
for name, unit, _ in FOODS:
    fq = f"ffq_{name}_frek"
    xw = f"ffq_{name}_x_mgg"
    d["_sering"] = (d[fq] >= 3).astype(int)   # >= 3-4 kali/minggu
    d["_harian"] = (d[fq] >= 4).astype(int)   # >= 1 kali/hari
    H, p, e = kw(d, fq)
    a = adj_logit(d, "_sering")
    cons = d[d[fq] > 0]
    Hp, pp, ep = kw(cons, f"ffq_{name}_porsi")
    rows.append([FOOD_LAB[name], unit,
                 *[d.loc[d.wilayah == x, xw].median() for x in AREAS],
                 *[pct(d.loc[d.wilayah == x, "_sering"]) for x in AREAS],
                 *[pct(d.loc[d.wilayah == x, "_harian"]) for x in AREAS],
                 p, e, a["Transisi"][0], a["Rural"][0], a["p_global"],
                 *[cons.loc[cons.wilayah == x, f"ffq_{name}_porsi"].mean() for x in AREAS], pp])
ffq = pd.DataFrame(rows, columns=["Makanan", "Satuan porsi", *[f"med_x_mgg_{x}" for x in AREAS],
                                  *[f"sering_{x}" for x in AREAS], *[f"harian_{x}" for x in AREAS],
                                  "p_KW", "epsilon2", "OR_sering_Transisi", "OR_sering_Rural", "p_adj_sering",
                                  *[f"porsi_{x}" for x in AREAS], "p_porsi"])
ffq["p_KW_FDR"] = fdr(ffq["p_KW"])
ffq["p_porsi_FDR"] = fdr(ffq["p_porsi"])
T["T4_ffq_item"] = ffq

# distribusi frekuensi per item (untuk lampiran)
FLAB = ["Tidak pernah", "1–3×/bulan", "1–2×/minggu", "3–4×/minggu", "1×/hari", "≥2×/hari"]
dist = []
for name, _, _ in FOODS:
    t = pd.crosstab(d["wilayah"], d[f"ffq_{name}_frek"], normalize="index").mul(100).reindex(columns=range(6), fill_value=0)
    t.columns = FLAB
    t.insert(0, "Makanan", FOOD_LAB[name])
    dist.append(t.reset_index())
T["L_ffq_distribusi"] = pd.concat(dist).round(1)

# kelompok pangan (frekuensi total kali/minggu)
GROUPS = meta["GROUPS"]
rows = []
for g in GROUPS:
    c = "kel_" + "".join(ch if ch.isalnum() else "_" for ch in g.lower())
    c = [k for k in d.columns if k.startswith("kel_") and k.endswith("_x_mgg") and
         k.replace("kel_", "").replace("_x_mgg", "").replace("_", "") == "".join(ch for ch in g.lower() if ch.isalnum())][0]
    H, p, e = kw(d, c)
    a = adj_ols(d, c)
    rows.append([g, *[miqr(d.loc[d.wilayah == x, c]) for x in AREAS], p, e, a["Transisi"][0], a["Rural"][0], a["p_global"], a["p_tren"]])
grp = pd.DataFrame(rows, columns=["Kelompok pangan", *AREAS, "p_KW", "epsilon2", "β_Transisi", "β_Rural", "p_adj", "p_tren"])
grp["p_adj_FDR"] = fdr(grp["p_adj"])
T["T5_kelompok_pangan"] = grp

# indikator pola makan
d["ind_bs_5"] = (d["porsi_buahsayur_hari"] >= 5).astype(int)
d["ind_sayur_3"] = (d["porsi_sayur_hari"] >= 3).astype(int)
d["ind_buah_2"] = (d["porsi_buah_hari"] >= 2).astype(int)
d["ind_ssb_harian"] = ((d["ffq_minuman_manis_frek"] >= 4) | (d["ffq_minuman_bersoda_frek"] >= 4)).astype(int)
d["ind_soda_mingguan"] = (d["ffq_minuman_bersoda_frek"] >= 2).astype(int)
d["ind_mie_3x"] = (d["ffq_mie_instan_frek"] >= 3).astype(int)
d["ind_jajan_harian"] = ((d["ffq_jajanan_frek"] >= 4) | (d["ffq_gorengan_frek"] >= 4)).astype(int)
d["ind_susu_harian"] = (d["ffq_susu_frek"] >= 4).astype(int)
d["ind_hewani_harian"] = (d[["ffq_ayam_x_mgg", "ffq_ikan_x_mgg", "ffq_telur_x_mgg"]].sum(axis=1) >= 7).astype(int)
IND = {"ind_bs_5": "Buah+sayur ≥5 porsi/hari", "ind_sayur_3": "Sayur ≥3 porsi/hari", "ind_buah_2": "Buah ≥2 porsi/hari",
       "ind_hewani_harian": "Lauk hewani (ayam/ikan/telur) ≥7×/minggu", "ind_susu_harian": "Susu setiap hari",
       "ind_ssb_harian": "Minuman manis/soda setiap hari", "ind_soda_mingguan": "Minuman bersoda ≥1×/minggu",
       "ind_mie_3x": "Mi instan ≥3×/minggu", "ind_jajan_harian": "Gorengan/jajanan setiap hari"}
rows = []
for k, lab in IND.items():
    _, p, _, v = chi2(d, k)
    a = adj_logit(d, k)
    ases = adj_logit(d[d.pendidikan_ortu.notna()], k, " + C(pendidikan_ortu)")
    rows.append([lab, *[pct(d.loc[d.wilayah == x, k]) for x in AREAS], pct(d[k]), p, v,
                 *[f"{a[x][0]:.2f} ({a[x][1]:.2f}–{a[x][2]:.2f})" for x in ["Transisi", "Rural"]], a["p_global"], a["p_tren"],
                 *[ases[x][0] for x in ["Transisi", "Rural"]], ases["p_global"]])
ind = pd.DataFrame(rows, columns=["Indikator", *AREAS, "Total", "p_chi2", "V", "OR Transisi (95% CI)", "OR Rural (95% CI)",
                                  "p_adj", "p_tren", "OR_Transisi_+pend", "OR_Rural_+pend", "p_adj_+pend"])
ind["p_adj_FDR"] = fdr(ind["p_adj"])
T["T6_indikator_makan"] = ind
cont = []
for k, lab in [("porsi_sayur_hari", "Porsi sayur/hari"), ("porsi_buah_hari", "Porsi buah/hari"),
               ("porsi_buahsayur_hari", "Porsi buah+sayur/hari"), ("ssb_ml_hari", "Minuman manis+soda (ml/hari)")]:
    H, p, e = kw(d, k)
    cont.append([lab, *[miqr(d.loc[d.wilayah == x, k]) for x in AREAS], miqr(d[k]), p, e])
T["T6_indikator_kontinu"] = pd.DataFrame(cont, columns=["Variabel", *AREAS, "Total", "p_KW", "epsilon2"])

# pola diet empiris (PCA + varimax) pada frekuensi 19 item
from sklearn.preprocessing import StandardScaler


def varimax(L, gamma=1.0, q=50, tol=1e-6):
    p, k = L.shape
    R = np.eye(k)
    dd_ = 0
    for _ in range(q):
        d_old = dd_
        Lam = L @ R
        u, s, vh = np.linalg.svd(L.T @ (Lam ** 3 - (gamma / p) * Lam @ np.diag(np.diag(Lam.T @ Lam))))
        R = u @ vh
        dd_ = s.sum()
        if d_old != 0 and dd_ / d_old < 1 + tol:
            break
    return L @ R


xcols = [f"ffq_{n}_x_mgg" for n, _, _ in FOODS]
X = StandardScaler().fit_transform(d[xcols])
corr = np.corrcoef(X, rowvar=False)
ev, evec = np.linalg.eigh(corr)
order = np.argsort(ev)[::-1]
ev, evec = ev[order], evec[:, order]
k_keep = int((ev > 1).sum())
k_use = 3
load = evec[:, :k_use] * np.sqrt(ev[:k_use])
rot = varimax(load)
# orientasi: muatan dominan positif
for j in range(k_use):
    if rot[:, j].sum() < 0:
        rot[:, j] *= -1
var_expl = (rot ** 2).sum(0) / len(xcols) * 100
load_df = pd.DataFrame(rot, index=[FOOD_LAB[n] for n, _, _ in FOODS], columns=[f"Pola {j + 1}" for j in range(k_use)])
# skor regresi (Thurstone)
W = np.linalg.solve(corr, rot)
scores = X @ W
for j in range(k_use):
    d[f"pola{j + 1}"] = scores[:, j]
T["T7_pola_muatan"] = load_df.round(2).reset_index().rename(columns={"index": "Makanan"})
kmo_num = None
rows = []
for j in range(k_use):
    c = f"pola{j + 1}"
    H, p, e = kw(d, c)
    a = adj_ols(d, c)
    rows.append([f"Pola {j + 1}", var_expl[j], *[msd(d.loc[d.wilayah == x, c]) for x in AREAS], p, e,
                 *[f"{a[x][0]:+.2f} ({a[x][1]:+.2f} s.d. {a[x][2]:+.2f})" for x in ["Transisi", "Rural"]], a["p_global"], a["p_tren"]])
T["T7_pola_wilayah"] = pd.DataFrame(rows, columns=["Pola", "% varians", *AREAS, "p_KW", "epsilon2",
                                                   "β Transisi vs Urban", "β Rural vs Urban", "p_adj", "p_tren"])
diet_summary = {"eigen": ev[:8], "k_eigen_gt1": k_keep, "var_expl": var_expl}

# =============================================================== 4. hambatan
HB_LAB = {"hb_waktu": "Tidak ada waktu (belajar, les, tugas)", "hb_fasilitas": "Tidak ada fasilitas",
          "hb_sakit_cedera": "Sakit atau cedera", "hb_tidak_suka": "Tidak suka olahraga",
          "hb_kegiatan_keluarga_adat": "Kegiatan keluarga/adat/agama/seni*", "hb_cuaca": "Cuaca/hujan*",
          "hb_lelah_malas": "Lelah/malas/kurang motivasi*", "hb_tidak_ada_teman": "Tidak ada teman*",
          "hb_tidak_ada_hambatan": "Menyatakan tidak ada hambatan*"}
rows = []
for k, lab in HB_LAB.items():
    _, p, _, v = chi2(d, k)
    try:
        a = adj_logit(d, k)
        ors = [f"{a[x][0]:.2f} ({a[x][1]:.2f}–{a[x][2]:.2f})" for x in ["Transisi", "Rural"]]
        pg, pt = a["p_global"], a["p_tren"]
    except Exception:
        ors, pg, pt = ["", ""], np.nan, np.nan
    rows.append([lab, *[pct(d.loc[d.wilayah == x, k]) for x in AREAS], pct(d[k]), p, v, *ors, pg, pt,
                 *[pct(d.loc[d.jk == s, k]) for s in ["Laki-laki", "Perempuan"]]])
hb = pd.DataFrame(rows, columns=["Hambatan", *AREAS, "Total", "p_chi2", "V", "OR Transisi (95% CI)", "OR Rural (95% CI)",
                                 "p_adj", "p_tren", "Laki-laki", "Perempuan"])
hb["p_chi2_FDR"] = fdr(hb["p_chi2"])
T["T8_hambatan"] = hb
H, p_hbn, e_hbn = kw(d, "hb_jumlah")
hbn = d.groupby("wilayah", observed=True)["hb_jumlah"].agg(["mean", "std"])

# hubungan hambatan dengan skor PA (disesuaikan wilayah, jk, kelas)
rows = []
for k in ["hb_waktu", "hb_fasilitas", "hb_sakit_cedera", "hb_tidak_suka"]:
    m = smf.ols(f"paqc_skor ~ {k} + C(wilayah) + C(jk) + C(kelas)", data=d).fit(cov_type="HC3")
    ci = m.conf_int().loc[k]
    rows.append([HB_LAB[k], m.params[k], ci[0], ci[1], m.pvalues[k]])
T["T8_hambatan_vs_PA"] = pd.DataFrame(rows, columns=["Hambatan", "β skor PAQ-C", "CI_bawah", "CI_atas", "p"])

# kontribusi hambatan 'tidak ada waktu' menurut kelas
T["T8_waktu_kelas"] = (d.groupby(["wilayah", "kelas"], observed=True)["hb_waktu"].mean() * 100).unstack().round(1).reset_index()

# =============================================================== 5. reliabilitas test-retest (79 pengisi ganda)
dp = pd.read_pickle("dup_pairs.pkl")
raw = dp["raw"]
RC = raw.columns
gap = np.median([g for _, _, g in dp["pairs"]])
GRID = {"Tidak Pernah": 1, "1 - 2 kali": 2, "3 - 4 kali": 3, "5 - 6 kali": 4, "7 kali atau lebih": 5}
FREQ5 = {"Tidak Pernah": 1, "1 - 2 kali": 2, "3 - 4 kali": 3, "Hampir setiap hari": 4, "Setiap hari": 5}
OFTEN = {"Tidak pernah": 1, "Kadang-kadang": 2, "Sering": 3, "Hampir selalu": 4, "Selalu": 5}
GAMB = {"Tidak ada aktivitas fisik": 1, "Aktivitas fisik ringan, tidak terlalu lelah": 2,
        "Aktivitas sedang, kadang berkeringat": 3, "Aktivitas berat, sering berkeringat": 4,
        "Aktivitas sangat berat, selalu berkeringat dan lelah": 5}
PJ = {"Tidak ada": 1, "1 kali": 2, "2 kali": 3, "3 kali": 4, "4 kali atau lebih": 5}
FREQ_ORD = {"Tidak pernah": 0, "1 - 3 kali per bulan": 1, "1 - 2 kali per minggu": 2,
            "3 - 4 kali per minggu": 3, "1 kali perhari": 4, "2 kali per hari atau lebih": 5}


def code_row(r):
    v = {}
    grid = [GRID.get(str(r[c]).strip(), np.nan) for c in RC[12:22]]
    v["checklist"] = np.nanmean(grid) if not all(np.isnan(grid)) else np.nan
    v["pjok"] = PJ.get(r[RC[22]], np.nan)
    v["sekolah"] = FREQ5.get(r[RC[23]], np.nan)
    v["setelah"] = FREQ5.get(r[RC[24]], np.nan)
    v["malam"] = FREQ5.get(r[RC[25]], np.nan)
    v["akhir_pekan"] = OFTEN.get(r[RC[26]], np.nan)
    v["intensitas"] = OFTEN.get(r[RC[27]], np.nan)
    v["gambaran"] = GAMB.get(str(r[RC[28]]).strip(), np.nan)
    for i, c in enumerate(RC[30:68:2]):
        v[f"ffq{i}"] = FREQ_ORD.get(str(r[c]).strip(), np.nan)
    return v


A = pd.DataFrame([code_row(raw.loc[a]) for a, b, g in dp["pairs"]])
B = pd.DataFrame([code_row(raw.loc[b]) for a, b, g in dp["pairs"]])
A["komposit"] = A[["checklist", "pjok", "sekolah", "setelah", "malam", "akhir_pekan", "intensitas", "gambaran"]].mean(1)
B["komposit"] = B[["checklist", "pjok", "sekolah", "setelah", "malam", "akhir_pekan", "intensitas", "gambaran"]].mean(1)
rt = {"n_pasang": len(A), "median_jarak_hari": gap,
      "icc_komposit": icc21(A["komposit"].values, B["komposit"].values),
      "kappa_pa_items": {k: wkappa(A[k], B[k], [1, 2, 3, 4, 5]) for k in ["pjok", "sekolah", "setelah", "malam", "akhir_pekan", "intensitas", "gambaran"]},
      "kappa_ffq_median": np.median([wkappa(A[f"ffq{i}"], B[f"ffq{i}"], list(range(6))) for i in range(19)]),
      "kappa_ffq_range": (np.min([wkappa(A[f"ffq{i}"], B[f"ffq{i}"], list(range(6))) for i in range(19)]),
                          np.max([wkappa(A[f"ffq{i}"], B[f"ffq{i}"], list(range(6))) for i in range(19)]))}

d.to_pickle("analysed.pkl")
pd.to_pickle({"T": T, "pa_summary": pa_summary, "diet_summary": diet_summary, "rt": rt,
              "hbn": hbn, "p_hbn": p_hbn, "e_hbn": e_hbn, "N": N}, "results.pkl")

if __name__ == "__main__":
    import sys
    pd.set_option("display.width", 250, "display.max_columns", 30)
    keys = sys.argv[1:] or list(T)
    for k in keys:
        print("\n###", k)
        print(T[k].round(3).to_string())
    print(pa_summary)
    print(diet_summary)
    print(rt)
    print(hbn, p_hbn, e_hbn)
