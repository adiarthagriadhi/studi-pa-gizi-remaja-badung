# studi-pa-gizi-remaja-badung (E1)

**English summary.** Analysis code and aggregate results for a cross-sectional school survey of physical activity,
barriers to physical activity and eating patterns among 1,898 students in grades 7–9 at five public junior high schools
in urban (Kuta), suburban (Abiansemal) and rural (Petang) Badung Regency, Bali, Indonesia (17 September – 2 October 2025;
Research Ethics Committee, Faculty of Medicine, Universitas Udayana, No. 2614/UN14.2.2.VII.14/LT/2025). The repository
contains **no student-level data**. The de-identified student-level dataset is in Mendeley Data
(doi:10.17632/f2mvjrf32w.1). Re-run: `pip install -r requirements.txt`, then `kode/jalankan_semua.sh <Google Form export>`.
Code: MIT; aggregate results and documents: CC BY 4.0 (see `LICENSE`). Cite via `CITATION.cff`.

Survei potong lintang aktivitas fisik, pola makan dan hambatan aktivitas fisik pada siswa SMP negeri di daerah
urban (Kuta), suburban (Abiansemal) dan rural (Petang), Kabupaten Badung, Bali. Respons: 17 Sep – 2 Okt 2025;
1.898 siswa unik dari 1.977 respons. Protokol etik: Komisi Etik Penelitian FK Unud No. 2614/UN14.2.2.VII.14/LT/2025
(protokol 2025.02.1.1185): persetujuan awal 8 Sep 2025, amandemen bernomor sama 22 Okt 2025.

Naskah: hub `adiarthagriadhi/Article-Preparation`, `articles/2026-josh-adolescent-pa-types-barriers` (kode portofolio E1).

## Isi
| Folder | Isi |
|---|---|
| `kode/` | `clean.py` → `analysis.py` → `make_tables.py` → `make_figures.py` (+ `stats_utils.py`); `sensitivity_school.py` = sensitivitas pengelompokan sekolah; `deidentify.py` = dataset terbuka E2 (desain B, k ≥ 5; keluaran per siswa hanya di komputer penulis/sesi, agregat di `hasil/e2/`) (rencana dikunci di `dokumen/rencana-sensitivitas-klaster.md`). `SHA256SUMS` adalah sidik jari versi sesi analisis 19 Okt 2026; `make_figures.py` sesudahnya diubah (jalur ke `hasil/`, label "Suburban") |
| `dokumen/` | protokol, pertanyaan penelitian, metode analisis, ringkasan hasil (dari sesi analisis) |
| `hasil/tables/` | tabel agregat + `key_numbers.json` (tanpa baris per siswa) |
| `hasil/figures/` | Gambar 1–3 (PNG 300 dpi + PDF) |
| `hasil/manifest.yaml` | tujuan file di hub |
| `labels.yaml` | kunci kode → label tampilan |
| `referensi/` | rujukan WHO 2007 BMI-for-age (LMS) |
| `requirements.txt` | versi paket terkunci |

## Data
Data mentah dan dataset bersih per siswa memuat data anak (nama, email, alamat) dan **tidak pernah masuk git**
(`.gitignore`). Disimpan penulis secara lokal.

## Menjalankan ulang (Gate 4)
```
pip install -r requirements.txt
kode/jalankan_semua.sh /jalur/ke/ekspor_google_form.csv
git diff --stat hasil/        # tanpa perubahan tabel = hasil tereproduksi
```
Berkas kerja per siswa ditulis ke `data/kerja/` (di-.gitignore). Rujukan WHO 2007 BMI-for-age ada di
`referensi/bfawho2007.txt` (paket anthroplus WHO). Tidak ada langkah acak dalam analysis; uji permutasi sekolah bersifat
eksak (30 penugasan). Pengacakan baris dataset E2 (`deidentify.py`) sengaja tidak diberi seed.

## Kirim ke hub
```
python3 shared/scripts/receive_results.py --results ../studi-pa-gizi-remaja-badung/hasil \
  --repo adiarthagriadhi/studi-pa-gizi-remaja-badung --commit <SHA> \
  --repo-root ../studi-pa-gizi-remaja-badung
```
Kesimpulan, keterbatasan dan butir `[AUTHOR: …]` ada di hub (`status.md`, `claims.md`).
