#!/usr/bin/env bash
# Menjalankan ulang seluruh analisis E1 dari ekspor Google Form mentah (Gate 4).
#   kode/jalankan_semua.sh /jalur/ke/ekspor_google_form.csv
# Berkas per siswa (pickle, log) ditulis ke data/kerja/ (di-.gitignore, tidak pernah masuk git).
# Tabel agregat ke hasil/tables/, gambar ke hasil/figures/. Dataset E2 dibuat terpisah dengan deidentify.py.
set -euo pipefail
RAW=$(realpath "$1")
ROOT=$(cd "$(dirname "$0")/.." && pwd)
W="$ROOT/data/kerja"
mkdir -p "$W"
cd "$W"
export PYTHONPATH="$ROOT/kode"
python3 "$ROOT/kode/clean.py" "$RAW"
python3 "$ROOT/kode/analysis.py" > analysis.log
HASIL_TABLES="$ROOT/hasil/tables" python3 "$ROOT/kode/make_tables.py"
python3 "$ROOT/kode/sensitivity_school.py" clean.pkl "$ROOT/hasil/tables/table11_school_cluster_sensitivity.csv"
python3 "$ROOT/kode/make_figures.py"
echo "Selesai. Periksa: git diff --stat hasil/  (tanpa perubahan = hasil tereproduksi)"
