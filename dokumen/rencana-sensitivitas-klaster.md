# Rencana analisis sensitivitas: pengelompokan siswa dalam sekolah (E1)

**Dikunci:** 19 Okt 2026, sebelum dijalankan (aturan riset §1.7). Data sudah pernah dilihat; analisis ini bersifat
sensitivitas, bukan konfirmatori. Naskah menulis: "analysis plan fixed after data inspection, before re-analysis".
Alasan: simulasi reviewer Gate 5 (M1) — wilayah identik dengan sekolah (urban = 1 sekolah; suburban dan rural = 2),
dan uji wilayah di analisis utama memperlakukan siswa sebagai independen.

## Data
`clean.pkl` (1.898 siswa). Satu responden "SMPN 2 KUTA" dikeluarkan (sama seperti model campuran utama), sehingga ada
lima sekolah: SMPN 1 Kuta (urban), SMPN 2 dan 3 Abiansemal (suburban), SMPN 1 dan 4 Petang (rural).

## Luaran (ditetapkan sekarang; hanya klaim di abstrak/klaim primer)
| Kode | Definisi (sama dengan analisis utama) |
|---|---|
| paqc_skor | skor komposit 8 item (kontinu) |
| walking, swimming, volleyball, gymnastics | aktivitas waktu luang ≥ 1–2 kali/7 hari (`pa_*` ≥ 2) |
| barrier_time, barrier_injury, barrier_dislike | `hb_waktu`, `hb_sakit_cedera`, `hb_tidak_suka` |
| animal_protein_7, milk_daily, ssb_daily | indikator analisis utama (`ind_hewani_harian`, `ind_susu_harian`, `ind_ssb_harian`) |
| banana_3, orange_3 | frekuensi ≥ 3–4 kali/minggu (`ffq_pisang_frek` ≥ 3, `ffq_jeruk_frek` ≥ 3) |

## Model (kovariat: jenis kelamin, kelas; referensi urban)
1. **Model campuran linear dengan intersep acak sekolah** (REML). Luaran biner dianalisis sebagai model probabilitas
   linear; estimasi = selisih proporsi (poin persentase) suburban/rural vs urban dengan CI 95 %. Skor PAQ-A: selisih skor.
   *Revisi sebelum dijalankan pada data asli (19 Okt 2026):* rencana awal memakai GEE dengan kovarians robust; dengan satu
   sekolah urban, varians robust untuk kontras urban tidak terdefinisi (uji pada data sintetis memberi CI tak hingga), dan SE
   berbasis model GEE tidak stabil. Model campuran linear dipilih karena sama dengan model sensitivitas skor PAQ-A di analisis utama.
2. **Uji permutasi tingkat sekolah (eksak):** statistik = koefisien tren wilayah (0/1/2) dari model tingkat siswa
   (logit atau OLS, + jenis kelamin + kelas). Label wilayah diacak di antara 5 sekolah dengan ukuran kelompok 1/2/2
   → 30 penugasan. p dua sisi = proporsi penugasan dengan |statistik| ≥ |statistik teramati|. p terkecil yang mungkin
   1/30 ≈ 0,033; karena itu hasil dibaca sebagai "arah konsisten antarsekolah" (p kecil) atau "tidak dapat dibedakan dari
   variasi antarsekolah" (p besar), bukan sebagai uji signifikansi biasa.

Tidak ada koreksi FDR tambahan (13 luaran, sensitivitas). Semua hasil dilaporkan, apa pun arahnya.

## Keluaran
`hasil/tables/table11_school_cluster_sensitivity.csv`: outcome, model, contrast, estimate, ci_low, ci_high, p, n_students,
n_schools, n_permutations. Tabel agregat saja; tidak ada baris per siswa.

## Pelaksanaan (19 Okt 2026)
Dijalankan oleh Claude di sesi hub atas permintaan penulis, pada data bersih yang dibangun ulang dari ekspor Google Form
mentah dengan `clean.py` (di folder sementara di luar git; data per siswa tidak disimpan di repo). Reproduksi: log pembersihan,
22 tabel hasil, dan `key_numbers.json` identik dengan kiriman 7771e2d. Hasil: `hasil/tables/table11_school_cluster_sensitivity.csv`
(n = 1.897; responden SMPN 2 Kuta dikeluarkan sesuai rencana).
