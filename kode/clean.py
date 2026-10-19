"""Pembersihan & pengodean data survei PA dan nutrisi remaja SMP (Badung, 2025).
Input : raw.csv (ekspor Google Form)
Output: clean.pkl, dup_pairs.pkl, coding_log.csv
"""
import re
import numpy as np
import pandas as pd

RAW = "raw.csv"
log = []  # (langkah, keterangan, n)


def L(step, note, n):
    log.append({"langkah": step, "keterangan": note, "n": n})


df = pd.read_csv(RAW, encoding="cp1252")
C = list(df.columns)
df["raw_row"] = df.index + 2  # nomor baris di file asli (baris 1 = header)
df["ts"] = pd.to_datetime(df["Timestamp"])
L("Data mentah", "Jumlah respons", len(df))

# ---------------------------------------------------------------- wilayah
AREA = {"SMPN 1 KUTA": "Urban", "SMPN 2 KUTA": "Urban",
        "SMPN 2 ABIANSEMAL": "Transisi", "SMPN 3 ABIANSEMAL": "Transisi",
        "SMPN 1 PETANG": "Rural", "SMPN 4 PETANG": "Rural"}
df["sekolah"] = df[C[5]].str.strip()
df["wilayah"] = df["sekolah"].map(AREA)

# ---------------------------------------------------------------- duplikat
nm = (df[C[2]].astype(str).str.upper().str.replace(r"[^A-Z ]", "", regex=True)
      .str.replace(r"\s+", " ", regex=True).str.strip())
df["_key"] = nm + "|" + df["sekolah"] + "|" + df[C[6]]
df = df.sort_values("ts")
dups = df[df["_key"].duplicated(keep=False)].copy()
L("Duplikat", "Siswa yang mengisi >1 kali (nama+sekolah+kelas sama)", dups["_key"].nunique())
L("Duplikat", "Baris duplikat dibuang (dipertahankan pengisian pertama)", int(df["_key"].duplicated().sum()))
df = df.drop_duplicates("_key", keep="first").sort_values("raw_row").reset_index(drop=True)

# ---------------------------------------------------------------- dasar
out = pd.DataFrame({"id": [f"S{i:04d}" for i in range(1, len(df) + 1)],
                    "raw_row": df["raw_row"], "tanggal_isi": df["ts"].dt.date,
                    "sekolah": df["sekolah"], "wilayah": df["wilayah"]})
out["jk"] = df[C[3]].map({"LAKI-LAKI": "Laki-laki", "PEREMPUAN": "Perempuan"})
out["kelas"] = df[C[6]].str.extract(r"(\d)")[0].astype(int)


def first_num(s):
    s = str(s).replace(",", ".")
    s = re.sub(r"(?<=\d)\s+(?=\d)", "", s)  # "1 49.5" -> "149.5"
    m = re.findall(r"\d+(?:\.\d+)?", s)
    return float(m[0]) if m else np.nan


tb = df[C[7]].map(first_num)
bb = df[C[8]].map(first_num)
fix_m = tb.between(1.2, 2.0)  # ditulis dalam meter
L("Antropometri", "TB ditulis dalam meter, dikali 100", int(fix_m.sum()))
tb[fix_m] = tb[fix_m] * 100
bad_tb = ~tb.between(120, 195)
bad_bb = ~bb.between(20, 120)
L("Antropometri", "TB di luar 120-195 cm atau tidak terbaca -> missing", int(bad_tb.sum()))
L("Antropometri", "BB di luar 20-120 kg atau tidak terbaca -> missing", int(bad_bb.sum()))
tb[bad_tb] = np.nan
bb[bad_bb] = np.nan
out["tb_cm"] = tb.round(1)
out["bb_kg"] = bb.round(1)
out["imt"] = (bb / (tb / 100) ** 2).round(2)

# Usia aproksimasi dari kelas (tidak ada tanggal lahir): survei Sep-Okt 2025
AGE_M = {7: 155, 8: 167, 9: 179}  # bulan (12,9 / 13,9 / 14,9 tahun)
out["usia_bln_aprox"] = out["kelas"].map(AGE_M)

lms = pd.read_csv("/home/claude/ext/anthroplus/data-raw/growthstandards/bfawho2007.txt", sep="\t")


def baz(sex, age_m, bmi):
    if np.isnan(bmi):
        return np.nan
    r = lms[(lms.sex == sex) & (lms.age == age_m)].iloc[0]
    l, m, s = r.l, r.m, r.s
    z = ((bmi / m) ** l - 1) / (l * s)
    sd = lambda k: m * (1 + l * s * k) ** (1 / l)
    if z > 3:
        z = 3 + (bmi - sd(3)) / (sd(3) - sd(2))
    elif z < -3:
        z = -3 + (bmi - sd(-3)) / (sd(-2) - sd(-3))
    return z


sexc = out["jk"].map({"Laki-laki": 1, "Perempuan": 2})
out["baz"] = [round(baz(s, a, b), 2) for s, a, b in zip(sexc, out["usia_bln_aprox"], out["imt"])]
flag = out["baz"].abs() > 5
L("Antropometri", "IMT/U |z|>5 (flag WHO) -> missing", int(flag.sum()))
out.loc[flag, ["baz"]] = np.nan
out.loc[flag, ["imt"]] = np.nan
# batas Permenkes 2/2020: <-3 sangat kurus; -3 s.d <-2 kurus; -2 s.d +1 normal; >+1 s.d +2 gizi lebih; >+2 obesitas
out["status_gizi"] = pd.cut(out["baz"], [-np.inf, -3, -2, 1.0000001, 2.0000001, np.inf],
                            labels=["Sangat kurus", "Kurus", "Normal", "Gizi lebih", "Obesitas"], right=False)

# jumlah anggota keluarga
WORD = {"DUA": 2, "TIGA": 3, "EMPAT": 4, "LIMA": 5, "ENAM": 6, "TUJUH": 7, "DELAPAN": 8, "SEMBILAN": 9, "SEPULUH": 10}


def fam(s):
    s = str(s).upper()
    n = first_num(s)
    if np.isnan(n):
        for w, v in WORD.items():
            if w in s:
                return v
    return n


fm = df[C[11]].map(fam)
bad = ~fm.between(2, 20)
L("Sosiodemografi", "Jumlah anggota keluarga tidak terbaca/di luar 2-20 -> missing", int(bad.sum()))
fm[bad] = np.nan
out["jml_keluarga"] = fm

# pendidikan orang tua: jenjang tertinggi yang disebut
def edu(s):
    s = " " + re.sub(r"[^A-Z0-9 ]", " ", str(s).upper()) + " "
    s = re.sub(r"\s+", " ", s)
    if "SMPN" in s:
        return np.nan
    pt = r" (S ?[123]|S ?E|SPD|S ?S|S ?H|S ?ARS|MH|SARJANA\w*|STRATA|KULIAH|D ?([1-4]|II|III|IV)|DIPLOMA\w*|DIPELOMA|DIKLOMA|DIVOLMA|DEPLOMA|DGLOMA|AKADEMI|PASCA\w*|WISUDA|STP|KEBI\w*|SP2) "
    sma = r" (SMA|SMK\w*|SLTA|SL TA|SL ?TA|STM|SMU|SMEA|ALIYAH|PGAN?|SGO|STLPA|SEKOLAH MENENGAH ATAS|SEKOLAH MENENGAH) "
    smp = r" (SMP\d?|SLTP|MTS|STLP) "
    sd = r" (SD|SEKOLAH DASAR|TIDAK SEKOLAH|BELUM TAMAT|TK|SDE) "
    if re.search(pt, s):
        return "Perguruan tinggi"
    if re.search(sma, s):
        return "SMA/SMK"
    if re.search(smp, s):
        return "SMP"
    if re.search(sd, s):
        return "≤SD"
    return np.nan


out["pendidikan_ortu"] = df[C[9]].map(edu)
L("Sosiodemografi", "Pendidikan orang tua tidak dapat dikode (mis. 'baik', 'tidak tahu') -> missing",
  int(out["pendidikan_ortu"].isna().sum()))

# pekerjaan orang tua: kategori tertinggi yang disebut dalam rumah tangga
OCC = [
    ("PNS/TNI/Polri/profesional", r"PNS|ASN|PPPK|P3K|PEGAWAI NEGE?RI|GURU|DOSEN|DOKTER|BIDAN|PERAWAT|TNI|POLRI|POLISI|POLRES|TENTARA|PURNAWIRAWAN|NOTARIS|PENGACARA|LAWYER|ARSITEK|BUMN|PLN|PERANGKA?T? DESA|KANTOR DESA|PEGAWAI DESA|KEPALA LINGKUNGAN|HONOR|PENGADILAN|DINAS|DLHK|POL-PP|DKP|PAGAWAI NEGERI|PEGAWAI TU|LPD|PANGAWAS"),
    ("Karyawan swasta", r"KAR\w*W\w*N|PEGAW|PEKERJA SW|PEKERJAAN SW|KERJA SW|SW?U?A?S?TA\b|SWASTA|SUASTA|SWASRA|SUASPA|SWSTA|SWAATA|KANTOR|HOTEL|VILLA|VILA|MANAGER|STAF|BANK|KAPAL PESIAR|CHEF|PARIWISATA|PARAWISATA|PRAWISATA|PRAMUWISATA|GUIDE|GAID|TURIS|TAMU|TRAVEL|SATPAM|SAP PAM|SECURITY|SCURITY|SEKURITI|PRAMUNIAGA|KASIR|AKUNTING|AIRPORT|AQUA|RAFTING|PELAYAN|HOUS KIPING|BAR |WISATA|MONEY CHANGER|KOPERASI|KOPRASI|TEKNISI|PEKERJA PARIWISATA|PEKERJA KANTOR"),
    ("Wiraswasta/pedagang", r"WIR\w*|WARIWASTA|USAHA|PEDAGANG|PEDANGANG|DAGANG|JUAL|PENJUAL|PENGUSAHA|KONTRAKTOR|PEMBORONG|TOKO|WARUNG|LAUNDR|LOUNDRE|RENTAL|HOMESTAY|BENGKEL|SEMBAKO|DISTRIBUTOR|SUPLIER|MEBEL|DEKORASI|BOS|ARSHOP|SUMUR BOR|FREELANCE|SENIMAN|TATTOO|KERA\w*JINAN|TAYLOR|PENJAHIT|JAHIT"),
    ("Petani/peternak/nelayan", r"PETANI|PENTANI|TANI\b|BERTANI|PERTANIAN|PETERNA|NELAYAN|PEKEBUN|BERKEBUN|PERKEBUNAN|SAWAH|BURUH CABAI"),
    ("Buruh/pekerja informal", r"BURU\w*|KULI|ULI BANGUNAN|TUKANG|SOPIR|SUPIR|NYOPIR|DRIVER|GOJEK|GRAB|GRAP|OJEK|SERABUT\w*|BANGUNAN|PROYEK|MEKANIK|PIJAT|PANDE|INTALASI|TRANSPORTASI|ASSISTEN RUMAH|BABY SISTER|\bART\b|SATGAS|PENGANTAR|PENGATAR|PEKERJA\b|PERKERJA|PEGAWE|KERJA DI TOKO|SAMPAH"),
    ("Tidak bekerja/IRT/pensiun", r"RUMAH TAN|RUMAH TUMAH|IRT|TIDAK BEKERJA|TIDAK KERJA|TIDAK PEKERJA|MENGANGGUR|PENSIUN|ALMA"),
]


def occ(s):
    s = " " + re.sub(r"\s+", " ", str(s).upper()) + " "
    nonwork = re.search(OCC[-1][1], s)
    s = re.sub(r"TIDAK (PE|BE)?KERJA", " ", s)
    s_noWira = re.sub(r"WIA?RA ?\w*|WARIWASTA", " ", s)  # cegah 'WIRASWASTA' terbaca 'SWASTA'
    for lab, pat in OCC[:-1]:  # urutan = prioritas (tertinggi dulu)
        target = s_noWira if lab == "Karyawan swasta" else s
        if re.search(pat, target):
            return lab
    if nonwork:
        return OCC[-1][0]
    return np.nan


out["pekerjaan_ortu"] = df[C[10]].map(occ)
L("Sosiodemografi", "Pekerjaan orang tua tidak dapat dikode -> missing", int(out["pekerjaan_ortu"].isna().sum()))

# ---------------------------------------------------------------- aktivitas fisik (adaptasi PAQ-C)
GRID = {"Tidak Pernah": 1, "1 - 2 kali": 2, "3 - 4 kali": 3, "5 - 6 kali": 4, "7 kali atau lebih": 5}
act_names = ["jalan_kaki", "lari_jogging", "sepak_bola", "voli", "basket", "renang", "senam_aerobik",
             "pencak_silat", "bersepeda", "lainnya"]
multi_cells = 0
multi_resp = 0
for name, col in zip(act_names, C[12:22]):
    s = df[col].astype(str).str.strip()
    single = s.map(GRID)
    ticks = s.str.split(r",\s*").map(lambda xs: [GRID.get(x.strip()) for x in xs])
    multi = s.str.contains(",")
    multi_cells += int(multi.sum())
    out[f"pa_{name}"] = single  # sel ganda -> NaN (analisis utama)
    out[f"pa_{name}_alt"] = np.where(multi, ticks.map(lambda v: np.mean([x for x in v if x])), single)  # sensitivitas: rerata centang
    out[f"pa_{name}_ganda"] = multi.astype(int)
multi_resp = int(out[[f"pa_{n}_ganda" for n in act_names]].any(axis=1).sum())
L("Aktivitas fisik", "Responden dengan >=1 sel ganda di grid aktivitas waktu luang", multi_resp)
L("Aktivitas fisik", "Sel grid dengan centang ganda -> missing (analisis utama)", multi_cells)

FREQ5 = {"Tidak Pernah": 1, "1 - 2 kali": 2, "3 - 4 kali": 3, "Hampir setiap hari": 4, "Setiap hari": 5}
OFTEN = {"Tidak pernah": 1, "Kadang-kadang": 2, "Sering": 3, "Hampir selalu": 4, "Selalu": 5}
out["pa_pjok"] = df[C[22]].map({"Tidak ada": 1, "1 kali": 2, "2 kali": 3, "3 kali": 4, "4 kali atau lebih": 5})
out["pa_sekolah"] = df[C[23]].map(FREQ5)
out["pa_setelah_sekolah"] = df[C[24]].map(FREQ5)
out["pa_malam"] = df[C[25]].map(FREQ5)
out["pa_akhir_pekan"] = df[C[26]].map(OFTEN)
out["pa_intensitas"] = df[C[27]].map(OFTEN)
out["pa_gambaran"] = df[C[28]].str.strip().map({
    "Tidak ada aktivitas fisik": 1, "Aktivitas fisik ringan, tidak terlalu lelah": 2,
    "Aktivitas sedang, kadang berkeringat": 3, "Aktivitas berat, sering berkeringat": 4,
    "Aktivitas sangat berat, selalu berkeringat dan lelah": 5})
assert out[["pa_pjok", "pa_sekolah", "pa_setelah_sekolah", "pa_malam", "pa_akhir_pekan",
            "pa_intensitas", "pa_gambaran"]].notna().all().all()

act_cols = [f"pa_{n}" for n in act_names]
out["pa_item1_checklist"] = out[act_cols].mean(axis=1)
out["pa_item1_checklist_alt"] = out[[c + "_alt" for c in act_cols]].mean(axis=1)
items = ["pa_item1_checklist", "pa_pjok", "pa_sekolah", "pa_setelah_sekolah", "pa_malam",
         "pa_akhir_pekan", "pa_intensitas", "pa_gambaran"]
out["paqc_skor"] = out[items].mean(axis=1)
out["paqc_skor_tanpa_pjok"] = out[[i for i in items if i != "pa_pjok"]].mean(axis=1)
out["paqc_skor_alt"] = out[["pa_item1_checklist_alt"] + items[1:]].mean(axis=1)
out["paqc_kategori"] = pd.cut(out["paqc_skor"], [0, 2.33, 3.66, 5.01],
                              labels=["Rendah", "Sedang", "Tinggi"], right=False)
out["paqc_aktif_2_75"] = (out["paqc_skor"] >= 2.75).astype(int)
out["n_jenis_aktivitas"] = (out[act_cols] >= 2).sum(axis=1)

# ---------------------------------------------------------------- hambatan
H = df[C[29]].astype(str)
FIX = {"hb_waktu": "Tidak ada waktu (karena belajar, les dll)",
       "hb_fasilitas": "Tidak ada fasilitas (misalnya lapangan, sepeda)",
       "hb_sakit_cedera": "Sakit atau cedera",
       "hb_tidak_suka": "Tidak suka olahraga"}
rem = H.copy()
for k, o in FIX.items():
    out[k] = H.str.contains(o, regex=False).astype(int)
    rem = rem.str.replace(o, "", regex=False)
rem = rem.str.replace(r"^[\s,]+|[\s,]+$", "", regex=True).str.upper()
out["hb_lainnya_teks"] = rem.where(rem != "", None)

RULES = [
    ("hb_waktu", r"SIBUK|SEMPAT|SEKOLAH SIANG|SEKOLAH MASUK SIANG|TUGAS|BUAT TUGAS|TIDAK ADA WAKTU|WAKTU SENGGANG|KEGIATAN SEKOLAH|EXTRA|LUAMAYAN SORE|PULANGYA SORE|KESIBUKAN|BERKEGIATAN DI LUAR"),
    ("hb_fasilitas", r"FASILITAS|SEPEDA RUSAK|KENDARAAN|LAPANGAN BOLA|HALAMAN SEMPIT|KURANG ALAT"),
    ("hb_sakit_cedera", r"SAKIT|ASMA|SESAK|CEDERA|FISIK KURANG"),
    ("hb_tidak_suka", r"TIDAK TERLALU SUKA|TIDAK INGIN"),
    ("hb_cuaca", r"HUJAN|CUACA|PANAS"),
    ("hb_lelah_malas", r"MALAS|MALES|CAPEK|LELAH|MOOD|BOSAN|MOTIVASI|MENUNDA|TIDAK TERBIASA"),
    ("hb_tidak_ada_teman", r"TEMAN|TEMANI|MENEMANI|DIAJAK|YANG AJAK|DI AJAK"),
    ("hb_kegiatan_keluarga_adat", r"UPACARA|RERAINAN|ODALAH|ODALAN|ADAT|NGAJI|GAMBEL|MEGAMBEL|TARI\b|BANTU|CANANG|SAWAH|WARUNG|PEKERJAAN RUMAH|KERJAAN RUMAH|MENYAPU|ACARA|PULANG KAMPUNG|ORDERAN|MENGEDIT|TEMENIN"),
]
for k in ["hb_cuaca", "hb_lelah_malas", "hb_tidak_ada_teman", "hb_kegiatan_keluarga_adat"]:
    out[k] = 0
coded_other = pd.Series(False, index=out.index)
for k, pat in RULES:
    m = rem.str.contains(pat, regex=True) & (rem != "")
    out.loc[m, k] = 1
    coded_other |= m
none_pat = r"^(TIDAK|TIDA|GAK|NGGAK|KARENA TIDAK|HAMPIR TIDAK)( PERNAH)? (ADA|AD|ABA)\b|^-$|SELALU AKTIVITAS|HAMPIR SETIAP HARI MELAKUKAN|SELALU SENPAT|TIDAK ADA (HALANGAN|HAMBATAN|PENGHALANG|YANG MENGHALANGI|YG MENGHALANG)|TIDAK AD MENGHALANG"
none_m = rem.str.contains(none_pat, regex=True) & ~coded_other
out["hb_tidak_ada_hambatan"] = (none_m & (out[list(FIX)].sum(axis=1) == 0)).astype(int)
out["hb_lainnya"] = ((rem != "") & ~coded_other & ~none_m).astype(int)
L("Hambatan", "Jawaban 'lainnya' (teks bebas) yang dikode ulang ke kategori", int(coded_other.sum()))
L("Hambatan", "Jawaban 'lainnya' = tidak ada hambatan", int(out["hb_tidak_ada_hambatan"].sum()))
hb_cols = ["hb_waktu", "hb_fasilitas", "hb_sakit_cedera", "hb_tidak_suka", "hb_cuaca", "hb_lelah_malas",
           "hb_tidak_ada_teman", "hb_kegiatan_keluarga_adat", "hb_lainnya"]
out["hb_jumlah"] = out[hb_cols].sum(axis=1)

# ---------------------------------------------------------------- FFQ
FREQ_DAY = {"Tidak pernah": 0.0, "1 - 3 kali per bulan": 2 / 30, "1 - 2 kali per minggu": 1.5 / 7,
            "3 - 4 kali per minggu": 3.5 / 7, "1 kali perhari": 1.0, "2 kali per hari atau lebih": 2.0}
FREQ_ORD = {"Tidak pernah": 0, "1 - 3 kali per bulan": 1, "1 - 2 kali per minggu": 2,
            "3 - 4 kali per minggu": 3, "1 kali perhari": 4, "2 kali per hari atau lebih": 5}
SUHARDJO = {"Tidak pernah": 0, "1 - 3 kali per bulan": 1, "1 - 2 kali per minggu": 10,
            "3 - 4 kali per minggu": 15, "1 kali perhari": 25, "2 kali per hari atau lebih": 50}
FOODS = [  # nama, satuan porsi, peta porsi
    ("nasi", "piring penuh", {"1/2 PIRING": 0.5, "1 PIRING KECIL": 0.75, "1 PIRING PENUH": 1}),
    ("mie_instan", "bungkus", {"1/2 BUNGKUS": 0.5, "1 BUNGKUS": 1, "2 BUNGKUS": 2}),
    ("tempe", "potong", {"1 POTONG KECIL (3 X 3 CM)": 1, "2 POTONG": 2, "3 POTONG": 3}),
    ("tahu", "potong", {"1 POTONG SEDANG": 1, "2 POTONG": 2, "3 POTONG": 3}),
    ("ayam", "potong sedang", {"1 POTONG KECIL (SAYAP)": 0.5, "1 POTONG SEDANG (DADA/PAHA)": 1, "2 POTONG": 2}),
    ("ikan", "potong", {"1 POTONG KECIL": 1, "Option 2": 2, "3 POTONG": 3}),
    ("telur", "butir", {"1/2 BUTIR": 0.5, "1 BUTIR": 1, "2 BUTIR": 2}),
    ("sayur_kol_wortel", "mangkok", {"1/2 MANGKOK SAYUR": 0.5, "1 MANGKOK SAYUR": 1, "2 MANGKOK SAYUR": 2}),
    ("bayam", "mangkok", {"1/2 MANGKOK SAYUR": 0.5, "1 MANGKOK SAYUR": 1, "2 MANGKOK SAYUR": 2}),
    ("kangkung", "mangkok", {"1/2 MANGKOK SAYUR": 0.5, "1 MANGKOK SAYUR": 1, "2 MANGKOK SAYUR": 2}),
    ("sambal", "sendok makan", {"1 SENDOK TEH": 1 / 3, "1 SENDOK MAKAN": 1, "2 SENDOK MAKAN": 2}),
    ("pisang", "buah", {"1/2 BUAH": 0.5, "1 BUAH": 1, "2 BUAH": 2}),
    ("mangga", "buah sedang", {"1/2 BUAH SEDANG": 0.5, "1 BUAH SEDANG": 1, "2 BUAH": 2}),
    ("jeruk", "buah sedang", {"1 BUAH KECIL": 0.75, "1 BUAH SEDANG": 1, "2 BUAH": 2}),
    ("minuman_manis", "gelas", {"1/2 GELAS": 0.5, "1 GELAS": 1, "2 GELAS": 2}),
    ("minuman_bersoda", "kaleng", {"1/2 KALENG": 0.5, "1 KALENG": 1, "2 KALENG": 2}),
    ("susu", "gelas", {"1/2 GELAS": 0.5, "1 GELAS": 1, "2 GELAS": 2}),
    ("gorengan", "buah", {"1 BUAH": 1, "2 BUAH": 2, "3 BUAH": 3}),
    ("jajanan", "bungkus sedang", {"1 BUNGKUS KECIL": 0.5, "1 BUNGKUS SEDANG": 1, "2 BUNGKUS": 2}),
]
fcols = C[30:68:2]
pcols = C[31:68:2]
n_imp = 0
for (name, unit, pmap), fc, pc in zip(FOODS, fcols, pcols):
    f = df[fc].str.strip()
    p = df[pc].str.strip()
    out[f"ffq_{name}_frek"] = f.map(FREQ_ORD)
    out[f"ffq_{name}_x_mgg"] = (f.map(FREQ_DAY) * 7).round(3)
    out[f"ffq_{name}_suhardjo"] = f.map(SUHARDJO)
    por = p.map(pmap)
    mode_val = por.mode().iloc[0]
    need = (out[f"ffq_{name}_frek"] > 0) & por.isna()
    n_imp += int(need.sum())
    por[need] = mode_val
    por[out[f"ffq_{name}_frek"] == 0] = 0
    out[f"ffq_{name}_porsi"] = por
    out[f"ffq_{name}_jml_hari"] = (f.map(FREQ_DAY) * por).round(3)  # satuan porsi per hari
    assert out[f"ffq_{name}_frek"].notna().all()
L("FFQ", "Porsi ikan 'Option 2' dikode sebagai '2 potong' (dikonfirmasi peneliti)", int((df[C[41]] == "Option 2").sum()))
L("FFQ", "Frekuensi > 0 tetapi porsi 'TIDAK PERNAH' -> porsi diisi modus item", n_imp)
L("FFQ", "Frekuensi 'tidak pernah' -> asupan 0 meskipun porsi terisi", int(sum(
    ((df[fc] == "Tidak pernah") & (df[pc] != "TIDAK PERNAH")).sum() for fc, pc in zip(fcols, pcols))))
L("FFQ", "Item 'makanan lain' (teks bebas) tidak dianalisis", len(out))

# Porsi standar Pedoman Gizi Seimbang (daftar bahan makanan penukar):
# sayur 1 mangkok ~100 g = 1 porsi; pisang 1 buah = 1 porsi; mangga 1 buah sedang ~ 2 porsi; jeruk 2 buah sedang = 1 porsi
out["porsi_sayur_hari"] = out[["ffq_sayur_kol_wortel_jml_hari", "ffq_bayam_jml_hari", "ffq_kangkung_jml_hari"]].sum(axis=1)
out["porsi_buah_hari"] = (out["ffq_pisang_jml_hari"] * 1 + out["ffq_mangga_jml_hari"] * 2 + out["ffq_jeruk_jml_hari"] * 0.5)
out["porsi_buahsayur_hari"] = out["porsi_sayur_hari"] + out["porsi_buah_hari"]
out["ssb_ml_hari"] = out["ffq_minuman_manis_jml_hari"] * 240 + out["ffq_minuman_bersoda_jml_hari"] * 330

GROUPS = {"Makanan pokok": ["nasi", "mie_instan"],
          "Lauk nabati": ["tempe", "tahu"],
          "Lauk hewani & susu": ["ayam", "ikan", "telur", "susu"],
          "Sayur": ["sayur_kol_wortel", "bayam", "kangkung"],
          "Buah": ["pisang", "mangga", "jeruk"],
          "Minuman manis & soda": ["minuman_manis", "minuman_bersoda"],
          "Gorengan & jajanan": ["gorengan", "jajanan"]}
for g, its in GROUPS.items():
    out["kel_" + re.sub(r"\W+", "_", g.lower()).strip("_") + "_x_mgg"] = out[[f"ffq_{i}_x_mgg" for i in its]].sum(axis=1)

L("Data bersih", "Jumlah siswa unik dianalisis", len(out))

# ---------------------------------------------------------------- pasangan duplikat (test-retest)
dups = dups.sort_values("ts")
pairs = []
for k, g in dups.groupby("_key"):
    a, b = g.iloc[0], g.iloc[-1]
    pairs.append((a.name, b.name, (b.ts - a.ts).total_seconds() / 86400))
raw_all = pd.read_csv(RAW, encoding="cp1252")
dup_pairs = {"pairs": pairs, "raw": raw_all}

out.to_pickle("clean.pkl")
pd.to_pickle(dup_pairs, "dup_pairs.pkl")
pd.DataFrame(log).to_csv("coding_log.csv", index=False)
pd.to_pickle({"FOODS": FOODS, "GROUPS": GROUPS, "act_names": act_names, "items": items, "hb_cols": hb_cols}, "meta.pkl")
print(pd.DataFrame(log).to_string())
