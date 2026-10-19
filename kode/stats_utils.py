"""Fungsi statistik bantu."""
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

AREAS = ["Urban", "Transisi", "Rural"]


def fmt_p(p):
    if pd.isna(p):
        return ""
    return "<0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")


def kw(df, col, by="wilayah"):
    groups = [df.loc[df[by] == a, col].dropna() for a in AREAS]
    H, p = stats.kruskal(*groups)
    n = sum(len(g) for g in groups)
    eps2 = H / (n - 1)  # epsilon-squared (Tomczak & Tomczak 2014)
    return H, p, eps2


def dunn(df, col, by="wilayah"):
    """Uji Dunn (koreksi Holm) untuk perbandingan berpasangan antarwilayah."""
    d = df[[col, by]].dropna()
    d["r"] = d[col].rank()
    n = len(d)
    ties = d[col].value_counts()
    tie_corr = (ties ** 3 - ties).sum() / (12 * (n - 1))
    res = []
    for a, b in [("Urban", "Transisi"), ("Urban", "Rural"), ("Transisi", "Rural")]:
        ra, rb = d.loc[d[by] == a, "r"], d.loc[d[by] == b, "r"]
        se = np.sqrt((n * (n + 1) / 12 - tie_corr) * (1 / len(ra) + 1 / len(rb)))
        z = (ra.mean() - rb.mean()) / se
        res.append([f"{a} vs {b}", z, 2 * stats.norm.sf(abs(z))])
    out = pd.DataFrame(res, columns=["pasangan", "z", "p"])
    out["p_holm"] = multipletests(out["p"], method="holm")[1]
    return out


def chi2(df, col, by="wilayah"):
    tab = pd.crosstab(df[col], df[by])
    chi, p, dof, _ = stats.chi2_contingency(tab)
    n = tab.values.sum()
    k = min(tab.shape) - 1
    v = np.sqrt(chi / (n * k)) if k > 0 else np.nan
    return chi, p, dof, v


def fdr(pvals):
    return multipletests(pvals, method="fdr_bh")[1]


def adj_ols(df, y, extra=""):
    """OLS y ~ wilayah + jk + kelas, SE robust HC3. Referensi: Urban.
    Juga uji tren linear (urban=0, transisi=1, rural=2)."""
    d = df.copy()
    d["urb"] = d["wilayah"].astype(str).map({"Urban": 0, "Transisi": 1, "Rural": 2}).astype(float)
    f = f"{y} ~ C(wilayah, Treatment('Urban')) + C(jk) + C(kelas){extra}"
    m = smf.ols(f, data=d).fit(cov_type="HC3")
    mt = smf.ols(f"{y} ~ urb + C(jk) + C(kelas){extra}", data=d).fit(cov_type="HC3")
    out = {}
    for a in ["Transisi", "Rural"]:
        k = f"C(wilayah, Treatment('Urban'))[T.{a}]"
        ci = m.conf_int().loc[k]
        out[a] = (m.params[k], ci[0], ci[1], m.pvalues[k])
    out["p_global"] = m.wald_test(f"C(wilayah, Treatment('Urban'))[T.Transisi] = 0, C(wilayah, Treatment('Urban'))[T.Rural] = 0", scalar=True).pvalue
    out["p_tren"] = mt.pvalues["urb"]
    return out


def adj_logit(df, y, extra=""):
    d = df.copy()
    d["urb"] = d["wilayah"].astype(str).map({"Urban": 0, "Transisi": 1, "Rural": 2}).astype(float)
    f = f"{y} ~ C(wilayah, Treatment('Urban')) + C(jk) + C(kelas){extra}"
    m = smf.logit(f, data=d).fit(disp=0, cov_type="HC1")
    mt = smf.logit(f"{y} ~ urb + C(jk) + C(kelas){extra}", data=d).fit(disp=0, cov_type="HC1")
    out = {}
    for a in ["Transisi", "Rural"]:
        k = f"C(wilayah, Treatment('Urban'))[T.{a}]"
        ci = np.exp(m.conf_int().loc[k])
        out[a] = (np.exp(m.params[k]), ci[0], ci[1], m.pvalues[k])
    out["p_global"] = m.wald_test(f"C(wilayah, Treatment('Urban'))[T.Transisi] = 0, C(wilayah, Treatment('Urban'))[T.Rural] = 0", scalar=True).pvalue
    out["p_tren"] = mt.pvalues["urb"]
    return out


def mixed_icc(df, y):
    """Model campuran dengan intersep acak sekolah: estimasi ICC (model kosong) dan efek wilayah."""
    d = df[[y, "wilayah", "jk", "kelas", "sekolah"]].dropna()
    d = d[d.sekolah != "SMPN 2 KUTA"]
    m0 = smf.mixedlm(f"{y} ~ 1", d, groups=d["sekolah"]).fit(reml=True)
    var_s = float(m0.cov_re.iloc[0, 0])
    icc = var_s / (var_s + m0.scale)
    m1 = smf.mixedlm(f"{y} ~ C(wilayah, Treatment('Urban')) + C(jk) + C(kelas)", d, groups=d["sekolah"]).fit(reml=True)
    res = {"icc": icc}
    for a in ["Transisi", "Rural"]:
        k = f"C(wilayah, Treatment('Urban'))[T.{a}]"
        ci = m1.conf_int().loc[k]
        res[a] = (m1.params[k], ci[0], ci[1], m1.pvalues[k])
    return res


def cronbach(df):
    d = df.dropna()
    k = d.shape[1]
    return k / (k - 1) * (1 - d.var(ddof=1).sum() / d.sum(axis=1).var(ddof=1))


def wkappa(a, b, cats):
    """Kappa berbobot kuadratik."""
    a, b = np.asarray(a), np.asarray(b)
    m = ~(pd.isna(a) | pd.isna(b))
    a, b = a[m], b[m]
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    O = np.zeros((k, k))
    for x, y in zip(a, b):
        O[idx[x], idx[y]] += 1
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / (k - 1) ** 2
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    return 1 - (W * O).sum() / (W * E).sum()


def icc21(x, y):
    """ICC(2,1) absolute agreement untuk dua pengukuran."""
    d = np.column_stack([x, y])
    d = d[~np.isnan(d).any(axis=1)]
    n, k = d.shape
    gm = d.mean()
    msr = k * ((d.mean(1) - gm) ** 2).sum() / (n - 1)
    msc = n * ((d.mean(0) - gm) ** 2).sum() / (k - 1)
    sse = ((d - d.mean(1, keepdims=True) - d.mean(0, keepdims=True) + gm) ** 2).sum()
    mse = sse / ((n - 1) * (k - 1))
    return (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)
