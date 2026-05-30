-- =====================================================================
-- THE INTRINSIC — Seed contoh: KONGLO_TRACKER
-- Tujuan: mengisi tabel agar tidak kosong saat DEMO / pengembangan.
-- Jalankan SETELAH schema.sql, di Supabase SQL Editor.
--
-- ⚠️ PENTING — DATA CONTOH, BUKAN DATA RESMI:
--   Angka persen kepemilikan di bawah adalah ILUSTRASI untuk demo UI.
--   JANGAN dipakai sebagai dasar keputusan. Untuk produksi, ganti dengan
--   data terverifikasi dari keterbukaan informasi IDX / KSEI (e-IPO, IDXnet)
--   dan perbarui kolom `tanggal_update` serta `sumber`.
--
-- Idempotent: baris demo lama (sumber diawali 'DEMO') dihapus dulu agar
-- aman dijalankan berulang tanpa menggandakan baris.
-- =====================================================================

begin;

delete from konglo_tracker where sumber like 'DEMO%';

insert into konglo_tracker
    (kode_saham, nama_pemilik, tipe, persen_kepemilikan, tanggal_update, sumber)
values
    -- Perbankan
    ('BBCA', 'PT Dwimuria Investama Andalan', 'Institusi', 54.94, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),
    ('BBCA', 'Keluarga Hartono (pengendali akhir)', 'Keluarga', 54.94, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),
    ('BMRI', 'Negara Republik Indonesia', 'Institusi', 52.00, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),
    ('BBRI', 'Negara Republik Indonesia', 'Institusi', 53.19, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),
    ('BBNI', 'Negara Republik Indonesia', 'Institusi', 60.00, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),

    -- Grup Barito / Prajogo Pangestu
    ('TPIA', 'PT Barito Pacific Tbk', 'Institusi', 33.00, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),
    ('BRPT', 'Prajogo Pangestu', 'Individu', 70.00, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),
    ('BREN', 'Prajogo Pangestu (via entitas pengendali)', 'Individu', 54.00, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),

    -- Grup Salim
    ('INDF', 'PT Indofood Sukses Makmur (pengendali Grup Salim)', 'Keluarga', 50.07, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),
    ('ICBP', 'PT Indofood Sukses Makmur Tbk', 'Institusi', 80.53, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),

    -- Grup Djarum (selain BBCA)
    ('TOWR', 'Grup Djarum (via entitas pengendali)', 'Keluarga', 52.00, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),

    -- Astra / Jardine
    ('ASII', 'Jardine Cycle & Carriage', 'Institusi', 50.11, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),

    -- Pertambangan / energi
    ('AMMN', 'PT Amman Mineral Internasional (pengendali)', 'Institusi', 51.00, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),
    ('ADRO', 'Garibaldi Thohir & afiliasi (pengendali)', 'Individu', 43.91, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI'),

    -- GoTo (institusi/teknologi)
    ('GOTO', 'SoftBank Vision Fund / pemegang institusi', 'Institusi', 7.50, '2026-01-31', 'DEMO — verifikasi via IDX/KSEI');

commit;

-- Verifikasi cepat:
-- select kode_saham, nama_pemilik, tipe, persen_kepemilikan
-- from konglo_tracker order by persen_kepemilikan desc;
