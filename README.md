# The Intrinsic

Platform riset saham & manajemen portofolio untuk emiten IDX.
**Streamlit + Supabase**, dengan layanan **FastAPI** terpisah untuk broker summary.

> ⚠️ **Bukan nasihat investasi.** Output mesin adalah *kondisi objektif* berbasis
> data (Bullish/Bearish/Neutral) untuk edukasi & riset mandiri — bukan ajakan
> jual/beli efek. Lihat disclaimer di dalam aplikasi.

---

## Arsitektur

```
                       ┌──────────────────────┐
   yfinance ───────────►                      │
   Google News RSS ────►   app.py (Streamlit) │  ← UI, mesin rekomendasi
                       │                      │
                       └─────────┬────────────┘
                                 │ GET /broksum/{kode}/score
                                 ▼
   scraper ──POST /broksum──►  api.py (FastAPI)  ──►  Supabase (broker_summary)
                                 ▲                         ▲
                                 └── broksum_core ─────────┘
                                  (logika skor dipakai bersama)
```

- **`app.py`** — aplikasi Streamlit (disclaimer → auth → dashboard, engine,
  fundamental, konglo tracker, berita, portofolio).
- **`api.py`** — layanan FastAPI: ingest broker summary (`POST /broksum`) dan
  sajikan skor agregat (`GET /broksum/{kode}/score`).
- **`broksum_core.py`** — logika klasifikasi akumulasi/distribusi, diimpor oleh
  `app.py` **dan** `api.py` agar hasilnya selalu konsisten.
- **`db/`** — skema & seed SQL untuk Supabase.

### Bagaimana broksum "otomatis masuk ke mesin"
`broksum_score()` di `app.py`:
1. Jika `[broksum].api_url` diisi di `secrets.toml` → ambil skor dari
   `GET {api_url}/broksum/{kode}/score` (data terbaru hasil ingest).
2. Jika tidak / API gagal → fallback membaca tabel `broker_summary` langsung.

Skor broksum lalu masuk ke komposit: `0.55·teknikal + 0.30·broksum + 0.15·berita`.

---

## Setup

### 1. Database (Supabase SQL Editor)
```sql
-- urut:
\i db/schema.sql              -- buat tabel
\i db/seed_konglo.sql         -- (opsional) data demo Konglo Tracker
\i db/seed_broker_summary.sql -- (opsional) data demo broksum
```
> Seed bertanda **DEMO** — ganti dengan data terverifikasi IDX/KSEI untuk produksi.

### 2. Secrets
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# isi url + anon key Supabase, cookie_key acak, dan (opsional) [broksum].api_url
```

### 3. Install
```bash
pip install -r requirements.txt
```

### 4. Jalankan
```bash
# Streamlit
streamlit run app.py

# (opsional) layanan broksum — di terminal lain
export SUPABASE_URL="https://xxxx.supabase.co"
export SUPABASE_KEY="<service_role_key>"   # server-side saja
uvicorn api:app --reload --port 8000
```

### Contoh ingest broksum
```bash
curl -X POST http://localhost:8000/broksum \
  -H "Content-Type: application/json" \
  -d '{"records":[
        {"kode_saham":"BMRI","tanggal":"2026-05-29","kode_broker":"MG","net_value":15000000000},
        {"kode_saham":"BMRI","tanggal":"2026-05-29","kode_broker":"CC","net_value":-4000000000}
      ]}'
```

---

## Catatan

- **streamlit-authenticator** dipin ke `0.3.2` (API-nya sering berubah).
- Gunakan **anon key** Supabase di klien Streamlit; **service_role** hanya di
  server `api.py`.
- `IDX_HOLIDAYS_2026` dan jam bursa di `app.py` adalah kerangka — verifikasi dari
  kalender resmi IDX.
- Kepatuhan: untuk operasi publik di Indonesia, telaah ketentuan OJK soal
  penyebaran informasi/rekomendasi efek dan konsultasikan dengan penasihat hukum.
