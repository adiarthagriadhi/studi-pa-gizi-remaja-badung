"""De-identify the E1/E2 student-level survey data for open sharing (Data in Brief, E2).

PROPOSAL (19 Oct 2026) — to be moved to the research repo adiarthagriadhi/studi-pa-gizi-remaja-badung and approved by
the author before use. Run it on the author's own computer only:

    python3 deidentify.py /path/to/clean.pkl /path/outside/any/git/repo/

Input : clean.pkl written by the research repo's clean.py (one row per student, Indonesian column names).
Output: in OUT_DIR (refused if it lies inside a git working tree)
    e2_dataset.csv          de-identified student-level data (to upload to Mendeley Data / Zenodo, never to GitHub)
    e2_data_dictionary.csv  variable, label, type, codes
    e2_risk_report.md       aggregate re-identification risk report (counts only; safe to send to the hub)

Rules (see review/deidentifikasi.md):
- dropped: name, e-mail, address, timestamp/date, school, raw row number, internal id, all free text,
  height, weight, BMI, BMI-for-age z, approximate age;
- kept: area (urban/suburban/rural), sex, grade, BMI-for-age in 4 categories, parental education (4),
  parental occupation (3 groups), household size (4 groups), all coded PAQ-C, barrier and FFQ answers;
- rows shuffled and given new random ids not linked to any other file;
- local suppression: quasi-identifier cells are set to missing, most detailed first, until every record shares its
  combination of quasi-identifiers with at least K-1 others."""
import secrets
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

K = 5
QI_BASE = ["area", "sex", "grade"]
# Released quasi-identifiers beyond area/sex/grade. Design B (recommended 19 Oct 2026, from the risk report on the real data):
# BMI-for-age category + parental education. Parental occupation and household size are NOT released (design D would
# suppress 58% of household-size cells). Suppression order: last first.
QI_EXTRA = ["bmi_for_age_cat", "parental_education"]
NOT_RELEASED = ["parental_occupation_group", "household_size_group"]

AREA = {"Urban": "urban", "Transisi": "suburban", "Rural": "rural"}
SEX = {"Laki-laki": "boy", "Perempuan": "girl"}
EDU = {"≤SD": "primary_or_less", "SMP": "junior_secondary", "SMA/SMK": "senior_secondary", "Perguruan tinggi": "tertiary"}
OCC = {"PNS/TNI/Polri/profesional": "formal_employment", "Karyawan swasta": "formal_employment",
       "Wiraswasta/pedagang": "self_employed_trader",
       "Petani/peternak/nelayan": "agriculture_informal_or_not_working", "Buruh/pekerja informal": "agriculture_informal_or_not_working",
       "Tidak bekerja/IRT/pensiun": "agriculture_informal_or_not_working"}
BMI = {"Sangat kurus": "thinness", "Kurus": "thinness", "Normal": "normal", "Gizi lebih": "overweight", "Obesitas": "obesity"}
ACT = {"jalan_kaki": "walking", "lari_jogging": "running", "sepak_bola": "football", "voli": "volleyball", "basket": "basketball",
       "renang": "swimming", "senam_aerobik": "gymnastics_aerobics", "pencak_silat": "pencak_silat", "bersepeda": "cycling",
       "lainnya": "other"}
PA = {"pa_pjok": "pe_lessons", "pa_sekolah": "school_outside_pe", "pa_setelah_sekolah": "after_school", "pa_malam": "evenings",
      "pa_akhir_pekan": "weekend", "pa_intensitas": "sweat_hard_breathing", "pa_gambaran": "week_description"}
HB = {"hb_waktu": "no_time", "hb_fasilitas": "no_facilities", "hb_sakit_cedera": "illness_injury", "hb_tidak_suka": "dislike_sport",
      "hb_cuaca": "other_weather", "hb_lelah_malas": "other_tired_low_motivation", "hb_tidak_ada_teman": "other_no_companion",
      "hb_kegiatan_keluarga_adat": "other_family_customary_religious_arts", "hb_lainnya": "other_uncoded",
      "hb_tidak_ada_hambatan": "no_barrier_written"}
FOOD = {"nasi": "rice", "mie_instan": "instant_noodles", "tempe": "tempeh", "tahu": "tofu", "ayam": "chicken", "ikan": "fish",
        "telur": "egg", "sayur_kol_wortel": "vegetables_cabbage_carrot", "bayam": "spinach", "kangkung": "water_spinach",
        "sambal": "chilli_sauce", "pisang": "banana", "mangga": "mango", "jeruk": "orange", "minuman_manis": "sweetened_drinks",
        "minuman_bersoda": "soft_drinks", "susu": "milk", "gorengan": "fried_snacks", "jajanan": "packaged_snacks"}


FREQ5 = "1 = never, 2 = 1-2 times, 3 = 3-4 times, 4 = 5-6 times, 5 = 7 times or more (past 7 days)"
ITEM = {"pe_lessons": "PE lessons attended in past 7 days: 1 = none, 2 = once, 3 = twice, 4 = three times, 5 = four times or more",
        "school_outside_pe": "Activity at school outside PE: 1 = never, 2 = 1-2 times, 3 = 3-4 times, 4 = almost every day, 5 = every day",
        "after_school": "Activity right after school: same codes as school_outside_pe",
        "evenings": "Activity in the evenings: same codes as school_outside_pe",
        "weekend": "Activity at the weekend: 1 = never, 2 = sometimes, 3 = often, 4 = almost always, 5 = always",
        "sweat_hard_breathing": "Activities causing sweating or hard breathing: same codes as weekend",
        "week_description": "Description of past 7 days: 1 = no activity, 2 = light, 3 = moderate, 4 = vigorous, 5 = very vigorous"}
FFQ_F = "0 = never, 1 = 1-3 times/month, 2 = 1-2 times/week, 3 = 3-4 times/week, 4 = once a day, 5 = twice a day or more"


def describe(v):
    if v == "record_id":
        return {"label": "Random record identifier (not linked to any other file)", "codes": "R0001-R1898"}
    if v == "area":
        return {"label": "Area of the school", "codes": "urban (Kuta), suburban (Abiansemal), rural (Petang)"}
    if v == "sex":
        return {"label": "Sex", "codes": "boy, girl"}
    if v == "grade":
        return {"label": "School grade", "codes": "7, 8, 9"}
    if v == "bmi_for_age_cat":
        return {"label": "BMI-for-age category (WHO 2007, self-reported height and weight, age approximated from grade)",
                "codes": "thinness, normal, overweight, obesity; missing = not available or suppressed"}
    if v == "parental_education":
        return {"label": "Highest parental education mentioned",
                "codes": "primary_or_less, junior_secondary, senior_secondary, tertiary; missing = not codable or suppressed"}
    if v.startswith("pa1_") and v.endswith("_multi_tick"):
        return {"label": f"More than one frequency ticked for {v[4:-11]} (cell set to missing in pa1_{v[4:-11]})", "codes": "0 = no, 1 = yes"}
    if v.startswith("pa1_"):
        return {"label": f"Leisure-time activity in past 7 days: {v[4:]}", "codes": FREQ5 + "; missing = more than one frequency ticked"}
    if v.startswith("pa_"):
        return {"label": "PAQ-A-based item", "codes": ITEM[v[3:]]}
    if v.startswith("barrier_"):
        return {"label": f"Barrier to physical activity in past 7 days: {v[8:]}", "codes": "0 = not reported, 1 = reported"}
    if v.endswith("_freq"):
        return {"label": f"Consumption frequency, past month: {v[4:-5]}", "codes": FFQ_F}
    if v.endswith("_portion"):
        return {"label": f"Usual portion of {v[4:-8]} in household-measure units (0 when never eaten)", "codes": "numeric"}
    return {"label": "", "codes": ""}


def inside_git(path):
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def hh_group(x):
    if pd.isna(x):
        return np.nan
    return "2_3" if x <= 3 else "4" if x == 4 else "5" if x == 5 else "6_plus"


def build(c):
    d = pd.DataFrame({"area": c["wilayah"].map(AREA), "sex": c["jk"].map(SEX), "grade": c["kelas"].astype(int)})
    d["bmi_for_age_cat"] = c["status_gizi"].astype(object).map(BMI)
    d["parental_education"] = c["pendidikan_ortu"].map(EDU)
    d["parental_occupation_group"] = c["pekerjaan_ortu"].map(OCC)
    d["household_size_group"] = c["jml_keluarga"].map(hh_group)
    for k, v in ACT.items():
        d[f"pa1_{v}"] = c[f"pa_{k}"]                  # 1-5; missing when more than one frequency was ticked
        d[f"pa1_{v}_multi_tick"] = c[f"pa_{k}_ganda"]
    for k, v in PA.items():
        d[f"pa_{v}"] = c[k]
    for k, v in HB.items():
        d[f"barrier_{v}"] = c[k]
    for k, v in FOOD.items():
        d[f"ffq_{v}_freq"] = c[f"ffq_{k}_frek"]        # 0-5
        d[f"ffq_{v}_portion"] = c[f"ffq_{k}_porsi"]    # household-measure units, after imputation rules
    return d


def compatible_k(d, extra):
    """k for each record, treating suppressed (missing) cells as wildcards that match any value."""
    k = pd.Series(0, index=d.index)
    for _, g in d.groupby(QI_BASE):
        vals = g[extra].to_numpy(object)
        miss = pd.isna(g[extra]).to_numpy()
        for i, ix in enumerate(g.index):
            ok = np.ones(len(g), bool)
            for j in range(len(extra)):
                if not miss[i, j]:
                    ok &= miss[:, j] | (vals[:, j] == vals[i, j])
            k[ix] = ok.sum()
    return k


def suppress(d):
    log = {c: 0 for c in QI_EXTRA}
    for _ in range(50):
        small = compatible_k(d, QI_EXTRA) < K
        if not small.any():
            break
        for col in reversed(QI_EXTRA):
            m = small & d[col].notna()
            if m.any():
                log[col] += int(m.sum())
                d.loc[m, col] = np.nan
                break
    left = int((compatible_k(d, QI_EXTRA) < K).sum())
    return d, list(log.items()), left


def risk_table(d, sets):
    rows = []
    for name, cols in sets:
        s = d.groupby(cols, dropna=False)[cols[0]].transform("size")
        rows.append({"quasi-identifiers": name, "classes": d.groupby(cols, dropna=False).ngroups,
                     "k=1": int((s == 1).sum()), "k<3": int((s < 3).sum()), "k<5": int((s < 5).sum()), "min k": int(s.min())})
    return pd.DataFrame(rows)


def md(df):
    head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return head + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False))


def main(src, out):
    out = Path(out).resolve()
    probe = next(p for p in [out, *out.parents] if p.exists())
    if inside_git(probe):
        sys.exit(f"Refused: {out} is inside a git working tree. Student-level data must never enter a git repository.")
    out.mkdir(parents=True, exist_ok=True)
    c = pd.read_pickle(src)
    d = build(c).drop(columns=NOT_RELEASED)
    # risk before suppression, including the school (to document why the school is not released)
    pre = build(c).assign(school=c["sekolah"].values)
    sets_pre = [("area × sex × grade", QI_BASE),
                ("school × sex × grade (not released)", ["school", "sex", "grade"]),
                ("area × sex × grade × BMI category", QI_BASE + ["bmi_for_age_cat"]),
                ("released quasi-identifiers", QI_BASE + QI_EXTRA),
                ("all candidate quasi-identifiers (incl. not released)", QI_BASE + QI_EXTRA + NOT_RELEASED)]
    before = risk_table(pre, sets_pre)
    d, log, left = suppress(d)
    after = risk_table(d, [s for s in sets_pre if "school" not in s[0] and "not released" not in s[0]])
    kmin = int(compatible_k(d, QI_EXTRA).min())
    d = d.sample(frac=1, random_state=secrets.randbits(32)).reset_index(drop=True)
    d.insert(0, "record_id", [f"R{i:04d}" for i in range(1, len(d) + 1)])
    d.to_csv(out / "e2_dataset.csv", index=False)
    dic = pd.DataFrame([dict(variable=v, **describe(v), n_missing=int(d[v].isna().sum())) for v in d.columns])
    dic.to_csv(out / "e2_data_dictionary.csv", index=False)
    import json
    (out / "e2_key_numbers.json").write_text(json.dumps({
        "n_records": int(len(d)), "n_variables": int(d.shape[1]), "k": K,
        "suppressed_cells": dict(log), "records_k_below_K": left, "k_min": kmin,
        "unique_before_all_candidate_qi": int(before.iloc[-1]["k=1"])}, indent=2), encoding="utf-8")
    with open(out / "e2_risk_report.md", "w", encoding="utf-8") as fh:
        fh.write(f"# E2 re-identification risk report (aggregate)\n\nRecords: {len(d)}; variables: {d.shape[1]}; K = {K}\n\n")
        fh.write("## Before suppression\n\n" + md(before) + "\n\n")
        fh.write("## Suppression (cells set to missing)\n\n" + "\n".join(f"- {col}: {n}" for col, n in log) + f"\n\nRecords with k < {K} (suppressed cells as wildcards): {left}; minimum k: {kmin}\n\n")
        fh.write("## After suppression (exact match, missing treated as its own category; conservative view)\n\n" + md(after) + "\n")
    print((out / "e2_risk_report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
