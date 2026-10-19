# studi-pa-gizi-remaja-badung (E1)

Survei potong lintang aktivitas fisik, pola makan dan hambatan aktivitas fisik pada siswa SMP negeri di daerah
urban (Kuta), suburban (Abiansemal) dan rural (Petang), Kabupaten Badung, Bali. Respons: 17 Sep – 2 Okt 2025;
1.898 siswa unik dari 1.977 respons. Protokol etik: Komisi Etik Penelitian FK Unud No. 2614/UN14.2.2.VII.14/LT/2025
(protokol 2025.02.1.1185), ditetapkan 22 Okt 2025 — **setelah** pengambilan data; status Gate 0 dicatat di hub.

Naskah: hub `adiarthagriadhi/Article-Preparation`, `articles/2026-tbd-adolescent-pa-diet-urbanicity` (kode portofolio E1).

## Isi
| Folder | Isi |
|---|---|
| `kode/` | `clean.py` → `analysis.py` → `make_tables.py` → `make_figures.py` (+ `stats_utils.py`). `SHA256SUMS` adalah sidik jari versi sesi analisis 19 Okt 2026; `make_figures.py` sesudahnya diubah (jalur ke `hasil/`, label "Suburban") |
| `dokumen/` | protokol, pertanyaan penelitian, metode analisis, ringkasan hasil (dari sesi analisis) |
| `hasil/tables/` | tabel agregat + `key_numbers.json` (tanpa baris per siswa) |
| `hasil/figures/` | Gambar 1–3 (PNG 300 dpi + PDF) |
| `hasil/manifest.yaml` | tujuan file di hub |
| `labels.yaml` | kunci kode → label tampilan |

## Data
Data mentah dan dataset bersih per siswa memuat data anak (nama, email, alamat) dan **tidak pernah masuk git**
(`.gitignore`). Disimpan penulis secara lokal. `clean.py`, `analysis.py` dan `make_tables.py` masih memakai jalur file
sesi analisis; sesuaikan ke `data/` lokal sebelum menjalankan ulang. `make_figures.py` hanya membaca tabel agregat.

## Kirim ke hub
```
python3 shared/scripts/receive_results.py --results ../studi-pa-gizi-remaja-badung/hasil \
  --repo adiarthagriadhi/studi-pa-gizi-remaja-badung --commit <SHA> \
  --repo-root ../studi-pa-gizi-remaja-badung
```
Kesimpulan, keterbatasan dan butir `[AUTHOR: …]` ada di hub (`status.md`, `claims.md`).
