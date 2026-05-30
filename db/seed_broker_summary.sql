-- =====================================================================
-- THE INTRINSIC — Seed contoh: BROKER_SUMMARY
-- Tujuan: memberi data broksum demo agar "The Engine" menampilkan skor
--         broksum non-nol (Big/Medium/Small Acc/Dist) saat demo.
-- Jalankan SETELAH schema.sql.
--
-- ⚠️ DATA CONTOH — bukan broker summary nyata. Net value dalam Rupiah,
--    positif = net beli (akumulasi), negatif = net jual (distribusi).
--    Untuk produksi, isi via scraper / endpoint POST /broksum di api.py.
--
-- Idempotent: upsert pada kunci unik (kode_saham, tanggal, kode_broker).
-- =====================================================================

insert into broker_summary (kode_saham, tanggal, kode_broker, net_value)
values
    -- BMRI: dominan akumulasi besar (-> "Big Acc")
    ('BMRI', '2026-05-29', 'MG', 18000000000),
    ('BMRI', '2026-05-29', 'BK',  9000000000),
    ('BMRI', '2026-05-29', 'CC', -4000000000),
    ('BMRI', '2026-05-29', 'AK', -2500000000),

    -- BBCA: cenderung distribusi sedang (-> "Medium Dist")
    ('BBCA', '2026-05-29', 'AK', -6000000000),
    ('BBCA', '2026-05-29', 'CC', -1500000000),
    ('BBCA', '2026-05-29', 'MG',  3000000000),

    -- TLKM: campur, mendekati netral kecil
    ('TLKM', '2026-05-29', 'DR',  500000000),
    ('TLKM', '2026-05-29', 'YP', -400000000),
    ('TLKM', '2026-05-29', 'PD',  200000000)
on conflict (kode_saham, tanggal, kode_broker)
do update set net_value = excluded.net_value;

-- Verifikasi:
-- select kode_saham, sum(net_value) as total_net
-- from broker_summary group by kode_saham order by total_net desc;
