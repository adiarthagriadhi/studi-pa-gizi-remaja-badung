# Metode analisis

Analisis dijalankan oleh Claude (Anthropic) dalam sesi claude.ai pada 19 Okt 2026, atas permintaan penulis. Kode tersedia di `context/` (`clean.py`, `stats_utils.py`, `analysis.py`, `make_tables.py`, `make_figures.py`), dengan sidik jari SHA-256 di `SHA256SUMS`. Data mentah (berisi nama, email, dan alamat siswa di bawah umur) dan dataset per siswa **tidak** ada di repo ini; keduanya disimpan penulis.

**Perangkat lunak:** Python 3.13.16; pandas 3.0.5; NumPy 2.5.3; statsmodels 0.15.0; SciPy 1.18.1; scikit-learn 1.9.1; matplotlib 3.11.2. Tabel LMS IMT/U WHO 2007 diambil dari paket WHO `anthroplus` (`data-raw/growthstandards/bfawho2007.txt`, GitHub WorldHealthOrganization/anthroplus).

## 1. Pembersihan data (log lengkap: `data/tables/cleaning_log.csv`)

- **Duplikat:** siswa dengan nama + sekolah + kelas yang sama (79 siswa) hanya dipertahankan pengisian pertamanya.
- **TB/BB:** teks diparse (koma desimal, satuan "cm"/"kg").
    - TB yang tertulis dalam meter (1,2–2,0) dikali 100.
    - TB di luar 120–195 cm dan BB di luar 20–120 kg dijadikan missing.
    - IMT/U dengan |z| > 5 (flag WHO) dijadikan missing.
- **Jumlah anggota keluarga:** angka diparse (termasuk kata "lima", "enam", dst.); nilai di luar 2–20 dijadikan missing.
- **Pendidikan orang tua:** jenjang tertinggi yang disebut, dikode ≤SD / SMP / SMA-SMK / Perguruan tinggi. Jawaban tidak relevan ("baik", "tidak tahu") dijadikan missing (133).
- **Pekerjaan orang tua:** kategori tertinggi yang disebut dalam rumah tangga, dengan urutan prioritas PNS/TNI/Polri/profesional > karyawan swasta > wiraswasta/pedagang > petani/peternak/nelayan > buruh/informal > tidak bekerja/IRT/pensiun. Yang tidak dapat dikode (22) dijadikan missing.

## 2. Aktivitas fisik

- **Item 1 (waktu luang):** 10 jenis aktivitas dikode 1–5. Sel dengan centang ganda dijadikan missing (394 sel dari 271 siswa). Item 1 = rerata jenis aktivitas yang terisi.
    - Sensitivitas: sel ganda diganti rerata kategori yang dicentang.
- **Item 2–8:** dikode 1–5 sesuai urutan pilihan.
- **Skor komposit:** rerata 8 item (α Cronbach 0,71).
    - Sensitivitas: tanpa item PJOK, 7 item (α 0,75).
    - Kategori: rendah < 2,33; sedang 2,33–3,66; tinggi > 3,66 (indikatif, karena instrumen diadaptasi).
- **Jenis aktivitas:** "ikut" = ≥ 1–2 kali per 7 hari; "sering" = ≥ 3–4 kali. Jumlah jenis aktivitas = banyaknya jenis dengan "ikut".

## 3. Pola makan

- **Frekuensi** dikonversi ke kali/minggu: 0; 0,47 (2/30 × 7); 1,5; 3,5; 7; 14. "Sering" = ≥ 3–4×/minggu; "setiap hari" = ≥ 1×/hari.
- **Porsi:** URT dikonversi ke satuan relatif per item (mis. nasi ½ piring = 0,5, piring kecil = 0,75, piring penuh = 1).
    - Frekuensi > 0 dengan porsi "tidak pernah" → porsi diisi modus item (145 sel).
    - Frekuensi "tidak pernah" → asupan 0 (286 sel).
- **Porsi buah dan sayur per hari** (bahan makanan penukar Pedoman Gizi Seimbang):
    - Sayur: 1 mangkok = 1 porsi.
    - Pisang: 1 buah = 1 porsi.
    - Mangga: 1 buah sedang = 2 porsi.
    - Jeruk: 1 buah sedang = 0,5 porsi.
- **Minuman manis + soda (ml/hari):** 1 gelas = 240 ml; 1 kaleng = 330 ml.
- **Indikator biner:**
    - Lauk hewani (ayam + ikan + telur) ≥ 7×/minggu.
    - Susu setiap hari.
    - Minuman manis atau soda setiap hari.
    - Soda ≥ 1×/minggu.
    - Mi instan ≥ 3×/minggu.
    - Gorengan atau jajanan setiap hari.
    - Buah ≥ 2 porsi/hari, sayur ≥ 3 porsi/hari, buah + sayur ≥ 5 porsi/hari.
- **Kelompok pangan:** jumlah frekuensi kali/minggu dari item anggotanya.
- **Pola diet:** PCA pada frekuensi (kali/minggu, distandardisasi) 19 item, dengan rotasi varimax. Empat komponen punya eigenvalue > 1 (5,01; 1,50; 1,22; 1,10); **tiga dipertahankan** berdasarkan scree dan interpretabilitas. Skor dihitung dengan metode regresi (Thurstone).
- **Item "makanan lain"** tidak dianalisis.

## 4. Status gizi

- IMT/U z-skor WHO 2007 dengan koreksi di luar ±3 SD (metode WHO AnthroPlus).
- Usia diaproksimasi dari kelas: kelas 7 = 155 bulan, kelas 8 = 167 bulan, kelas 9 = 179 bulan (12,9 / 13,9 / 14,9 tahun pada Sep–Okt 2025), karena tanggal lahir tidak tersedia.
- Kategori mengikuti Permenkes 2/2020: < −3 sangat kurus; −3 s.d. < −2 kurus; −2 s.d. +1 normal; > +1 s.d. +2 gizi lebih; > +2 obesitas.

## 5. Hambatan

- Empat opsi tetap dikode 1/0.
- Teks "lainnya" dikode ulang dengan aturan kata kunci (lihat `clean.py`):
    - Jawaban yang setara dengan opsi tetap digabung ke opsi itu.
    - Sisanya menjadi kategori baru: kegiatan keluarga/adat/agama/seni, cuaca, lelah/malas, tidak ada teman, lainnya.
    - "Tidak ada hambatan" hanya dikode bila tidak ada hambatan lain yang dicentang.

## 6. Statistik

- **Perbandingan tiga wilayah:**
    - Variabel ordinal/kontinu: Kruskal-Wallis, dengan ukuran efek ε² = H/(n−1).
    - Variabel kategorik: chi-square, dengan Cramér's V.
- **Estimasi terkoreksi** (wilayah + jenis kelamin + kelas; referensi = urban):
    - Luaran kontinu: OLS dengan SE robust HC3.
    - Luaran biner: regresi logistik dengan SE robust HC1.
    - p global wilayah: uji Wald 2 df.
    - p tren: wilayah sebagai skor 0/1/2.
- **Uji berganda:** Benjamini-Hochberg di dalam tiap famili (item PAQ-C; jenis aktivitas; item FFQ; kelompok pangan; indikator makan; hambatan).
- **Efek sekolah:** model campuran linear dengan intersep acak sekolah (5 sekolah; responden SMPN 2 Kuta dikeluarkan) untuk ICC dan sensitivitas. Konsistensi antarsekolah ditampilkan di `table9`. Urban hanya satu sekolah, sehingga efek urban tidak terpisah dari efek SMPN 1 Kuta.
- **Sensitivitas sosial-ekonomi:** model logistik ditambah pendidikan tertinggi orang tua (kolom `*_ses`).
- **Interaksi wilayah × jenis kelamin** pada skor komposit: uji Wald 2 df.
- **Reliabilitas test-retest:** 79 siswa yang mengisi dua kali (median jarak 4,6 hari).
    - Skor komposit: ICC(2,1) kesepakatan absolut.
    - Item ordinal: kappa berbobot kuadratik.
    - Indikatif saja, karena pasangan ini bukan sampel acak.
