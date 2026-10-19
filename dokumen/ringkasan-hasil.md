# Ringkasan hasil (untuk penulisan; angka resmi ada di `data/tables/`)

Ringkasan ini menunjukkan di tabel mana setiap temuan berada. Saat menulis naskah, ambil angka dari tabel, bukan dari dokumen ini. Laporan hasil lengkap dalam bahasa Indonesia, dengan grafik interaktif, ada di Claude Docs penulis ("Pola Aktivitas Fisik, Pola Makan, dan Hambatan pada Remaja SMP Urban, Transisi, dan Rural", 19 Okt 2026).

## Sampel (table1_*)

- **Jumlah:** 1.898 siswa (urban 628, transisi 758, rural 512); perempuan 56%.
- **Komposisi kelas:** berbeda antarwilayah (urban lebih sedikit kelas 7), sehingga semua model disesuaikan kelas.
- **Gradien sosial-ekonomi:**
    - Orang tua berpendidikan tinggi: urban 37%, rural 16%.
    - Orang tua petani: rural 24%, urban < 1%.
- **Gizi lebih + obesitas (dilaporkan sendiri):** urban 32,8%, transisi 24,0%, rural 24,7%.

## Aktivitas fisik

**Tingkat total setara antarwilayah** (table2_paqc_items.csv, table2_paqc_models.csv).

- Skor komposit: urban 2,44, transisi 2,46, rural 2,39 (ε² = 0,002).
- β terkoreksi vs urban:
    - Transisi: +0,02 (−0,04 s.d. 0,08).
    - Rural: −0,06 (−0,12 s.d. 0,00).
- ICC sekolah < 0,01.
- Sekitar separuh siswa di kategori rendah; proporsinya tidak berbeda antarwilayah.

**Jenis kelamin lebih menentukan daripada wilayah.**

- Perempuan −0,25 (−0,30 s.d. −0,20) dibanding laki-laki.
- Tidak ada interaksi dengan wilayah (p = 0,33).

**Komposisi aktivitas berbeda** (table3_activity_types.csv).

- **Lebih tinggi di urban:**
    - Berjalan kaki: 80% vs 60% rural.
    - Renang: 48% vs 34%.
- **Lebih tinggi di transisi dan rural:**
    - Voli: 47% dan 42% vs 23% urban.
    - Senam/aerobik: 68% dan 74% vs 53%.
- Hasil bertahan setelah penyesuaian pendidikan orang tua (kolom `*_ses`) dan searah di kedua sekolah per wilayah (table9).
- **Basket:** tidak konsisten antarsekolah, sehingga ini efek sekolah, bukan efek wilayah.
- **Ragam aktivitas:** transisi 5,3 dan rural 5,2 jenis vs 4,8 jenis di urban (table3_number_of_activity_types.csv).

## Pola makan

**Pola diet PCA tidak berbeda bermakna antarwilayah** (table7_*).

- Pola 1 (lauk nabati–sayur–buah) sedikit lebih tinggi di rural; pola 2 (jajanan–minuman manis) sedikit lebih tinggi di urban.
- p tren 0,05–0,06.

**Ada gradien urban → rural pada item tertentu** (table4_food_frequency.csv, table6_diet_indicators.csv).

- **Lebih tinggi di urban:**
    - Lauk hewani ≥7×/minggu: 58,6% → 44,7%.
    - Susu setiap hari: 25,2% → 16,6%.
    - Minuman manis/soda setiap hari: 20,7% → 12,1%.
    - Gradien ini bertahan setelah penyesuaian pendidikan orang tua.
- **Lebih tinggi di transisi dan rural:** pisang, jeruk, tahu, sambal, gorengan/jajanan.

**Buah dan sayur rendah di semua wilayah** (table6_fruit_vegetable_ssb_amounts.csv).

- Median 1,6 porsi/hari.
- Hanya 12,7% yang mencapai ≥5 porsi/hari, tanpa perbedaan antarwilayah.

## Hambatan aktivitas fisik (table8_*)

**"Tidak ada waktu" adalah hambatan utama (57,7%) dan tertinggi di urban** (65,8% vs 52,5% di rural; OR rural 0,59).

| Hambatan | Pola antarwilayah | OR rural vs urban |
|---|---|---|
| Sakit/cedera | Tertinggi di rural: 30,5% vs 16,9% | 2,13 |
| Tidak suka olahraga | Tertinggi di urban: 11,3% vs 5,3% | 0,43 |
| Fasilitas | Setara, ±26% di setiap wilayah | — |

- **Jenis kelamin:**
    - Perempuan lebih sering menyebut waktu (66,9% vs 45,8%) dan tidak suka olahraga.
    - Laki-laki lebih sering menyebut sakit/cedera.
- **Hubungan dengan skor PA:**
    - "Tidak suka olahraga" paling kuat terkait skor PA lebih rendah (−0,41).
    - Sakit/cedera justru terkait skor lebih tinggi (+0,20), kemungkinan karena siswa aktif lebih sering cedera.
- **Hambatan nutrisi tidak diukur.**

## Reliabilitas (table10_test_retest.csv)

- Skor komposit: ICC 0,75.
- Item PAQ-C: kappa berbobot 0,39–0,70.
- Item FFQ: median kappa 0,58.
- Dasarnya 79 pasangan pengisi ganda.

## Implikasi penulisan

- **Pesan utama yang didukung data:**
    - Urbanisasi tidak menurunkan **jumlah** aktivitas fisik remaja di Badung, tetapi mengubah **jenisnya** (lebih banyak berjalan kaki dan berenang, lebih sedikit voli dan senam) dan **hambatannya** (waktu).
    - Pola makan urban lebih banyak lauk hewani dan susu, tetapi juga lebih banyak minuman manis.
    - Kekurangan buah dan sayur bersifat umum di semua wilayah.
- **Hal yang tidak boleh diklaim:**
    - Kausalitas.
    - Efek "urban" yang terlepas dari efek SMPN 1 Kuta.
    - Apa pun tentang hambatan nutrisi.
    - Asupan energi atau zat gizi.
