"""Sensitivitas pengelompokan siswa dalam sekolah (rencana: dokumen/rencana-sensitivitas-klaster.md, dikunci 19 Okt 2026).

Jalankan di komputer penulis (data per siswa tidak pernah masuk git):
    python3 sensitivity_school.py /path/ke/clean.pkl ../hasil/tables/table11_school_cluster_sensitivity.csv
"""
import itertools
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
AREAS = ["Urban", "Transisi", "Rural"]
COV = "C(jk) + C(kelas)"


def prepare(d):
    d = d[d["sekolah"] != "SMPN 2 KUTA"].copy()
    d["wilayah"] = pd.Categorical(d["wilayah"].astype(str), AREAS)
    d["urb"] = d["wilayah"].astype(str).map({"Urban": 0, "Transisi": 1, "Rural": 2}).astype(float)
    y = {"paqc_skor": d["paqc_skor"]}
    for k, c in [("walking", "pa_jalan_kaki"), ("swimming", "pa_renang"), ("volleyball", "pa_voli"),
                 ("gymnastics", "pa_senam_aerobik")]:
        y[k] = (d[c] >= 2).astype(float).where(d[c].notna())
    y["barrier_time"], y["barrier_injury"], y["barrier_dislike"] = d["hb_waktu"], d["hb_sakit_cedera"], d["hb_tidak_suka"]
    y["animal_protein_7"] = (d[["ffq_ayam_x_mgg", "ffq_ikan_x_mgg", "ffq_telur_x_mgg"]].sum(axis=1) >= 7).astype(float)
    y["milk_daily"] = (d["ffq_susu_frek"] >= 4).astype(float)
    y["ssb_daily"] = ((d["ffq_minuman_manis_frek"] >= 4) | (d["ffq_minuman_bersoda_frek"] >= 4)).astype(float)
    y["banana_3"] = (d["ffq_pisang_frek"] >= 3).astype(float)
    y["orange_3"] = (d["ffq_jeruk_frek"] >= 3).astype(float)
    for k, v in y.items():
        d[f"y_{k}"] = v
    return d, list(y)


def mixed(d, k):
    """Model campuran linear, intersep acak sekolah. Luaran biner sebagai model probabilitas linear:
    estimasi = selisih proporsi (poin persentase) vs urban."""
    sub = d[[f"y_{k}", "wilayah", "jk", "kelas", "sekolah"]].dropna()
    m = smf.mixedlm(f"y_{k} ~ C(wilayah, Treatment('Urban')) + {COV}", sub, groups=sub["sekolah"]).fit(reml=True)
    scale = 1.0 if k == "paqc_skor" else 100.0
    rows = []
    for a, lab in [("Transisi", "suburban vs urban"), ("Rural", "rural vs urban")]:
        t = f"C(wilayah, Treatment('Urban'))[T.{a}]"
        lo, hi = m.conf_int().loc[t]
        rows.append([k, "linear mixed model, random school intercept" + ("" if k == "paqc_skor" else " (risk difference, %-points)"),
                     lab, scale * m.params[t], scale * lo, scale * hi, m.pvalues[t]])
    return rows, len(sub)


def trend_stat(sub, k):
    f = f"y_{k} ~ urb + {COV}"
    m = smf.ols(f, sub).fit() if k == "paqc_skor" else smf.logit(f, sub).fit(disp=0)
    return m.params["urb"]


def permutation(d, k):
    sub = d[[f"y_{k}", "urb", "jk", "kelas", "sekolah"]].dropna().copy()
    school_area = sub.groupby("sekolah")["urb"].first()
    schools = list(school_area.index)
    sizes = school_area.value_counts().sort_index()          # {0: 1, 1: 2, 2: 2}
    obs = trend_stat(sub, k)
    stats = []
    for urban in itertools.combinations(schools, int(sizes[0.0])):
        rest = [s for s in schools if s not in urban]
        for sub_ in itertools.combinations(rest, int(sizes[1.0])):
            lab = {s: 0.0 if s in urban else 1.0 if s in sub_ else 2.0 for s in schools}
            perm = sub.assign(urb=sub["sekolah"].map(lab))
            stats.append(trend_stat(perm, k))
    stats = np.array(stats)
    p = float(np.mean(np.abs(stats) >= abs(obs) - 1e-12))
    est = obs if k == "paqc_skor" else np.exp(obs)
    return [k, "school-level permutation of area labels (trend)", "trend per area step", est, np.nan, np.nan, p], len(stats)


def main(src, out):
    d, outcomes = prepare(pd.read_pickle(src))
    rows = []
    for k in outcomes:
        r, n = mixed(d, k)
        pr, nperm = permutation(d, k)
        for x in r + [pr]:
            rows.append(x + [n, d["sekolah"].nunique(), nperm if "permutation" in x[1] else np.nan])
    cols = ["outcome", "model", "contrast", "estimate", "ci_low", "ci_high", "p", "n_students", "n_schools", "n_permutations"]
    t = pd.DataFrame(rows, columns=cols)
    t.to_csv(out, index=False, float_format="%.4g")
    print(t.to_string())


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
