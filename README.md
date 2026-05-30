# The Intrinsic

Platform riset saham & manajemen portofolio untuk emiten IDX.
**Streamlit + Google Sheets** (Users & Portfolios via `st-gsheets-connection`),
dwi-tema **Dark/Light**, dwi-bahasa **ID/EN**, chart interaktif **Plotly**, dan
berita real-time **RSS**. Layanan **FastAPI** opsional untuk broker summary.

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

## Coba cepat (Mode Tamu — tanpa database)

Cukup untuk melihat situs jalan, tanpa Google Sheets / akun / secrets:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Buka **http://localhost:8501**, setujui disclaimer, klik **"👤 Masuk sebagai Tamu"**.
Dashboard, The Engine, Fundamental, Radar, dan Berita berfungsi. **Portofolio**
nonaktif sampai Google Sheets dikonfigurasi. Toggle **bahasa (ID/EN)** dan
**Dark/Light** ada di sidebar.

> Tidak perlu `secrets.toml` untuk Mode Tamu.

---

## Setup penuh (akun + Google Sheets)

1. **Buat Google Spreadsheet** dengan dua worksheet: `Users` dan `Portfolios`.
   - `Users`     header: `username, name, email, password_hash, created_at`
   - `Portfolios` header: `username, kode_saham, harga_rata2, jumlah_lot, created_at`
2. **Buat Service Account** di Google Cloud (aktifkan Google Sheets API), unduh
   kunci JSON-nya, lalu **bagikan (Share)** spreadsheet ke `client_email`
   service account tersebut dengan akses **Editor**.
3. **Isi secrets** — JANGAN commit `credentials.json`. Semua dibaca dari
   `st.secrets`:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   # tempel kredensial service account ke blok [connections.gsheets]
   ```
   Lihat format TOML lengkap di `.streamlit/secrets.toml.example`.
4. **Install & jalankan**:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py

   # (opsional) layanan broksum — terminal lain
   export SUPABASE_URL=... SUPABASE_KEY=...
   uvicorn api:app --reload --port 8000
   ```

Registrasi/login menulis & membaca worksheet `Users`; password di-hash
(PBKDF2-SHA256) sebelum disimpan. Portofolio tersimpan di worksheet `Portfolios`.

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
