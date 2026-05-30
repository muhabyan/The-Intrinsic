"""
================================================================================
THE INTRINSIC — Stock Research & Portfolio Management
Streamlit + Supabase | arsitektur modular
================================================================================

Instalasi:
    pip install -r requirements.txt

Menjalankan:
    streamlit run app.py

Catatan versi:
    - Diuji dengan streamlit-authenticator==0.3.2. API library ini sering
      berubah antar versi (login()/register_user()). Jika versimu beda,
      sesuaikan tanda tangan fungsi di bagian AUTENTIKASI.

Alur aplikasi:
    Disclaimer (wajib setuju)  ->  Login/Registrasi  ->  Aplikasi utama

Filosofi compliance:
    Output mesin = KONDISI OBJEKTIF berbasis data (Bullish/Bearish/Neutral)
    + pertimbangan umum. BUKAN ajakan jual/beli, BUKAN nasihat berlisensi.
    Disclaimer mengikat ditampilkan sebelum fitur apa pun terbuka.
================================================================================
"""

import urllib.parse
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st

from broksum_core import classify_nets

# --- Dependensi eksternal (dibungkus agar pesan errornya jelas) ---
try:
    import yfinance as yf
except ImportError:
    yf = None
try:
    import feedparser
except ImportError:
    feedparser = None
try:
    import streamlit_authenticator as stauth
except ImportError:
    stauth = None
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None
try:
    import requests
except ImportError:
    requests = None

WIB = ZoneInfo("Asia/Jakarta")
LOT_SIZE = 100  # 1 lot = 100 lembar

# ==============================================================================
# KONFIGURASI HALAMAN & CSS (tampilan unik, modern, minimalis)
# ==============================================================================
st.set_page_config(page_title="The Intrinsic", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp { background: #f7f8fa; }
section[data-testid="stSidebar"] { background:#ffffff; border-right:1px solid #ececf1; }
.brand { font-size:1.6rem; font-weight:800; color:#0f172a; letter-spacing:-0.5px; }
.brand-sub { font-size:0.72rem; color:#94a3b8; letter-spacing:2px; text-transform:uppercase; }
div[data-testid="stMetric"] {
    background:#fff; border:1px solid #ececf1; border-radius:14px;
    padding:18px 20px; box-shadow:0 1px 3px rgba(15,23,42,0.04);
}
div[data-testid="stMetricLabel"] { color:#94a3b8; font-size:0.78rem; font-weight:600; }
div[data-testid="stMetricValue"] { color:#0f172a; }
.section-h { font-size:1.15rem; font-weight:700; color:#0f172a; margin:8px 0 4px; }
.badge { display:inline-block; padding:8px 22px; border-radius:10px; font-weight:800; font-size:1.2rem; }
.bull { background:#dcfce7; color:#15803d; }
.bear { background:#fee2e2; color:#b91c1c; }
.neut { background:#fef9c3; color:#a16207; }
.pill { display:inline-block; padding:3px 12px; border-radius:999px; font-size:0.78rem; font-weight:700; }
.pill-open { background:#dcfce7; color:#15803d; }
.pill-closed { background:#f1f5f9; color:#64748b; }
.disclaimer-card {
    background:#fff; border:1px solid #ececf1; border-radius:18px;
    padding:34px 40px; box-shadow:0 8px 30px rgba(15,23,42,0.08); max-width:760px; margin:auto;
}
#MainMenu, footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# KONEKSI SUPABASE
# ==============================================================================
@st.cache_resource
def get_supabase() -> "Client":
    """Inisialisasi klien Supabase dari secrets.toml. Cache resource."""
    if create_client is None:
        return None
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception:
        # Tidak dikonfigurasi / gagal -> diam saja. Mode Tamu tetap jalan tanpa
        # Supabase; halaman yang butuh database akan memberi tahu sendiri.
        return None


# ==============================================================================
# LAPISAN DATA PASAR (yfinance)
# ==============================================================================
@st.cache_data(ttl=900, show_spinner=False)
def get_info(ticker: str) -> dict:
    if yf is None:
        return {}
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}


@st.cache_data(ttl=900, show_spinner=False)
def get_history(ticker: str, period="1y", interval="1d") -> pd.DataFrame:
    if yf is None:
        return pd.DataFrame()
    try:
        h = yf.Ticker(ticker).history(period=period, interval=interval)
        return h if h is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def to_jk(kode: str) -> str:
    """Normalisasi kode saham IDX ke format Yahoo (xxxx.JK)."""
    kode = kode.strip().upper()
    return kode if kode.endswith(".JK") else f"{kode}.JK"


# ==============================================================================
# STATUS BURSA & KALENDER LIBUR
# ==============================================================================
# WAJIB diverifikasi & diperbarui dari kalender resmi IDX setiap tahun.
# Format ISO 'YYYY-MM-DD'. Ini hanya kerangka; ISI dengan data resmi.
IDX_HOLIDAYS_2026 = {
    # "2026-01-01",  # contoh — ganti dengan daftar resmi IDX
}


def market_status() -> tuple:
    """
    Hitung status bursa IDX (perkiraan, WIB).
    Catatan: jam Jumat sedikit berbeda (sesi 1 lebih pendek). Ini disederhanakan;
    sesuaikan bila perlu presisi penuh untuk pre-opening/pre-closing.
    """
    now = datetime.now(WIB)
    if now.weekday() >= 5:
        return "Closed", "Akhir pekan", now
    if now.date().isoformat() in IDX_HOLIDAYS_2026:
        return "Closed", "Hari libur bursa", now
    t = now.time()
    if now.weekday() == 4:  # Jumat
        sesi1 = dtime(9, 0) <= t <= dtime(11, 30)
        sesi2 = dtime(14, 0) <= t <= dtime(15, 49)
    else:  # Senin–Kamis
        sesi1 = dtime(9, 0) <= t <= dtime(12, 0)
        sesi2 = dtime(13, 30) <= t <= dtime(15, 49)
    if sesi1:
        return "Open", "Sesi I berlangsung", now
    if sesi2:
        return "Open", "Sesi II berlangsung", now
    if dtime(12, 0) < t < dtime(13, 30):
        return "Closed", "Istirahat sesi", now
    return "Closed", "Di luar jam bursa", now


# ==============================================================================
# MESIN INDIKATOR TEKNIKAL
# ==============================================================================
def compute_indicators(hist: pd.DataFrame) -> pd.DataFrame:
    df = hist.copy()
    c = df["Close"]
    df["SMA20"] = c.rolling(20).mean()
    df["SMA50"] = c.rolling(50).mean()
    df["SMA200"] = c.rolling(200).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    e12 = c.ewm(span=12, adjust=False).mean()
    e26 = c.ewm(span=26, adjust=False).mean()
    df["MACD"] = e12 - e26
    df["MACD_SIG"] = df["MACD"].ewm(span=9, adjust=False).mean()
    return df


def technical_score(df: pd.DataFrame, style: str) -> tuple:
    """
    Skor teknikal -1..+1, dibobot menurut gaya investasi.
    style: 'Jangka Panjang' | 'Jangka Pendek' | 'Kombinasi'
    """
    if df.empty or len(df) < 50:
        return 0.0, ["Data historis tidak cukup."]
    last = df.iloc[-1]
    reasons, signals = [], {}

    # Sinyal individual (-1..+1)
    signals["trend_long"] = 1 if (pd.notna(last["SMA200"]) and last["Close"] > last["SMA200"]) else -1
    signals["trend_mid"] = 1 if (pd.notna(last["SMA50"]) and last["Close"] > last["SMA50"]) else -1
    signals["cross"] = 1 if (pd.notna(last["SMA20"]) and pd.notna(last["SMA50"]) and last["SMA20"] > last["SMA50"]) else -1
    if pd.notna(last["RSI"]):
        signals["rsi"] = 1 if last["RSI"] < 30 else (-1 if last["RSI"] > 70 else 0)
        reasons.append(f"RSI {last['RSI']:.0f}")
    else:
        signals["rsi"] = 0
    signals["macd"] = 1 if last["MACD"] > last["MACD_SIG"] else -1

    # Bobot per gaya
    weights = {
        "Jangka Panjang": {"trend_long": 0.45, "trend_mid": 0.25, "cross": 0.10, "rsi": 0.05, "macd": 0.15},
        "Jangka Pendek":  {"trend_long": 0.05, "trend_mid": 0.15, "cross": 0.20, "rsi": 0.30, "macd": 0.30},
        "Kombinasi":      {"trend_long": 0.25, "trend_mid": 0.20, "cross": 0.15, "rsi": 0.20, "macd": 0.20},
    }.get(style, None)
    if weights is None:
        weights = {k: 1 / len(signals) for k in signals}

    score = sum(signals[k] * weights.get(k, 0) for k in signals)
    reasons.append("Harga di atas SMA200" if signals["trend_long"] > 0 else "Harga di bawah SMA200")
    reasons.append("MACD bullish" if signals["macd"] > 0 else "MACD bearish")
    return float(np.clip(score, -1, 1)), reasons


# ==============================================================================
# MESIN BROKSUM (sumber: API FastAPI atau Supabase; logika di broksum_core)
# ==============================================================================
def _broksum_api_url() -> str:
    """Ambil base URL layanan broksum (api.py) dari secrets, bila ada."""
    try:
        url = st.secrets["broksum"]["api_url"]
        return url.rstrip("/") if url else ""
    except Exception:
        return ""


def broksum_score(sb, kode: str) -> tuple:
    """
    Skor broker summary -1..+1 + label + total net.

    Sumber data (berurutan):
      1) Layanan FastAPI (api.py) bila [broksum].api_url diisi di secrets.toml.
         Endpoint: GET {api_url}/broksum/{kode}/score
      2) Fallback: baca langsung tabel broker_summary di Supabase.

    Logika klasifikasi terpusat di broksum_core.classify_nets agar hasil di
    Streamlit dan API selalu identik.
    """
    # 1) Coba layanan API broksum bila dikonfigurasi
    api_url = _broksum_api_url()
    if api_url and requests is not None:
        try:
            resp = requests.get(f"{api_url}/broksum/{kode}/score", timeout=8)
            if resp.ok:
                d = resp.json()
                return float(d["score"]), str(d["label"]), int(d["total_net"])
        except Exception:
            pass  # diam-diam fallback ke Supabase

    # 2) Fallback: baca langsung dari Supabase
    if sb is None:
        return 0.0, "Data broksum tidak tersedia", 0
    try:
        res = sb.table("broker_summary").select("net_value").eq("kode_saham", kode).execute()
        rows = res.data or []
    except Exception:
        return 0.0, "Gagal membaca broksum", 0
    if not rows:
        return 0.0, "Belum ada data broksum", 0

    result = classify_nets([r.get("net_value", 0) for r in rows])
    return result["score"], result["label"], result["total_net"]


# ==============================================================================
# MESIN BERITA & SENTIMEN (RSS Google News — real)
# ==============================================================================
POS_WORDS = {"laba", "naik", "untung", "ekspansi", "akuisisi", "dividen", "rekor",
             "tumbuh", "positif", "stock split", "buyback", "kontrak"}
NEG_WORDS = {"rugi", "turun", "anjlok", "gugatan", "default", "pailit", "phk",
             "negatif", "denda", "investigasi", "suspensi", "delisting"}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news(kode_polos: str) -> list:
    """Ambil berita emiten via RSS Google News (Bahasa Indonesia)."""
    if feedparser is None:
        return []
    q = urllib.parse.quote(f"{kode_polos} saham emiten")
    url = f"https://news.google.com/rss/search?q={q}&hl=id&gl=ID&ceid=ID:id"
    try:
        feed = feedparser.parse(url)
        return [{"judul": e.get("title", ""), "link": e.get("link", ""),
                 "tanggal": e.get("published", "")} for e in feed.entries[:8]]
    except Exception:
        return []


def news_score(news: list) -> tuple:
    """Sentimen sederhana berbasis kata kunci pada judul berita. Skor -1..+1."""
    if not news:
        return 0.0, "Tidak ada berita terbaru"
    s = 0
    for n in news:
        t = n["judul"].lower()
        s += sum(1 for w in POS_WORDS if w in t)
        s -= sum(1 for w in NEG_WORDS if w in t)
    norm = float(np.clip(s / max(len(news), 1), -1, 1))
    label = "Sentimen positif" if norm > 0.1 else ("Sentimen negatif" if norm < -0.1 else "Sentimen netral")
    return norm, label


# ==============================================================================
# MESIN REKOMENDASI GABUNGAN (objektif, data-driven)
# ==============================================================================
def recommendation_engine(sb, ticker: str, style: str) -> dict:
    """Gabungkan teknikal + broksum + berita -> kondisi objektif + saran umum."""
    kode_polos = ticker.replace(".JK", "")
    df = compute_indicators(get_history(ticker, period="1y"))
    tech, tech_reasons = technical_score(df, style)
    bk_score, bk_label, bk_net = broksum_score(sb, kode_polos)
    news = fetch_news(kode_polos)
    nw_score, nw_label = news_score(news)

    # Bobot komponen (teknikal dominan, broksum & berita pendukung)
    composite = 0.55 * tech + 0.30 * bk_score + 0.15 * nw_score

    if composite >= 0.2:
        condition, cls, action = "BULLISH", "bull", "Pertimbangkan Tambah Muatan (Buy)"
    elif composite <= -0.2:
        condition, cls, action = "BEARISH", "bear", "Pertimbangkan Kurangi Risiko (Sell)"
    else:
        condition, cls, action = "NEUTRAL", "neut", "Pertahankan (Hold)"

    return {
        "composite": composite, "condition": condition, "cls": cls, "action": action,
        "tech": tech, "tech_reasons": tech_reasons,
        "broksum": bk_label, "broksum_net": bk_net,
        "news_label": nw_label, "news": news, "df": df, "style": style,
    }


# ==============================================================================
# GERBANG 1: DISCLAIMER (wajib setuju sebelum fitur terbuka)
# ==============================================================================
def disclaimer_gate() -> bool:
    if st.session_state.get("agreed_disclaimer"):
        return True
    st.write(""); st.write("")
    st.markdown('<div class="disclaimer-card">', unsafe_allow_html=True)
    st.markdown('<p class="brand">The Intrinsic</p>', unsafe_allow_html=True)
    st.markdown('<p class="brand-sub">Equity Research Platform</p>', unsafe_allow_html=True)
    st.markdown("### ⚠️ Disclaimer & Ketentuan Penggunaan")
    st.markdown("""
**The Intrinsic bukan penasihat keuangan berlisensi.** Seluruh informasi, skor,
dan "kondisi" (Bullish/Bearish/Neutral) yang ditampilkan adalah **hasil pengolahan
data objektif** (teknikal, broker summary, berita publik) untuk **tujuan edukasi
dan riset mandiri**.

- Ini **bukan ajakan, rekomendasi, atau solicitation** untuk membeli/menjual efek.
- Kinerja masa lalu **tidak menjamin** hasil di masa depan.
- **Keputusan investasi sepenuhnya tanggung jawab Anda.** Pertimbangkan konsultasi
  dengan penasihat keuangan/Wakil Manajer Investasi berizin OJK.
- Data dapat tertunda, tidak lengkap, atau keliru.

Dengan menekan **"Saya Setuju"**, Anda menyatakan memahami dan menerima ketentuan ini.
    """)
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("✅ Saya Setuju", type="primary", use_container_width=True):
            st.session_state["agreed_disclaimer"] = True
            st.rerun()
    with c2:
        st.caption("Anda harus menyetujui untuk melanjutkan.")
    st.markdown('</div>', unsafe_allow_html=True)
    return False


# ==============================================================================
# GERBANG 2: AUTENTIKASI (streamlit-authenticator + Supabase)
# ==============================================================================
def load_credentials(sb) -> dict:
    """Muat kredensial user dari Supabase ke format streamlit-authenticator."""
    creds = {"usernames": {}}
    if sb is None:
        return creds
    try:
        rows = sb.table("users").select("username,name,email,password_hash").execute().data or []
        for r in rows:
            creds["usernames"][r["username"]] = {
                "name": r.get("name", r["username"]),
                "email": r.get("email", ""),
                "password": r["password_hash"],
            }
    except Exception as exc:
        st.error(f"Gagal memuat kredensial: {exc}")
    return creds


def _authenticator_configured() -> bool:
    """True bila blok [authenticator] ada di secrets.toml."""
    try:
        return bool(st.secrets["authenticator"]["cookie_name"])
    except Exception:
        return False


def auth_gate(sb):
    """Tangani login & registrasi. Return (status, username, name) atau None."""
    # --- Sesi tamu yang sudah aktif: lewati seluruh gerbang ---
    if st.session_state.get("is_guest"):
        return True, "guest", "Tamu"

    st.markdown('<p class="brand">The Intrinsic</p>', unsafe_allow_html=True)

    # --- Mode Tamu: jelajahi tanpa akun / tanpa Supabase ---
    st.info("**Mode Tamu** — lihat-lihat aplikasi tanpa akun. "
            "Halaman yang butuh database (Portofolio, Konglo Tracker) "
            "dinonaktifkan sampai Supabase dikonfigurasi.")
    if st.button("👤 Masuk sebagai Tamu", type="primary", use_container_width=False):
        st.session_state["is_guest"] = True
        st.rerun()

    # Bila auth berbasis akun belum bisa dipakai (paket/secrets/Supabase belum
    # siap), berhenti di sini — Mode Tamu sudah cukup untuk mencoba situs.
    if stauth is None or sb is None or not _authenticator_configured():
        st.caption("Login akun dinonaktifkan (streamlit-authenticator/Supabase/secrets "
                   "belum siap). Gunakan **Masuk sebagai Tamu** di atas.")
        return False, None, None

    st.markdown("---")
    creds = load_credentials(sb)
    authenticator = stauth.Authenticate(
        creds,
        st.secrets["authenticator"]["cookie_name"],
        st.secrets["authenticator"]["cookie_key"],
        int(st.secrets["authenticator"]["cookie_expiry_days"]),
    )

    tab_login, tab_register = st.tabs(["🔑 Masuk", "📝 Daftar"])

    with tab_login:
        # API 0.3.2: login() menulis ke st.session_state
        authenticator.login(location="main")
        status = st.session_state.get("authentication_status")
        if status is False:
            st.error("Username atau password salah.")
        elif status is None:
            st.info("Silakan masuk dengan akun Anda.")
        elif status:
            authenticator.logout("Keluar", "sidebar")
            return True, st.session_state.get("username"), st.session_state.get("name")

    with tab_register:
        st.caption("Buat akun baru. Data tersimpan aman di Supabase.")
        new_user = st.text_input("Username", key="reg_user")
        new_name = st.text_input("Nama Lengkap", key="reg_name")
        new_email = st.text_input("Email", key="reg_email")
        new_pass = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Daftar", type="primary"):
            if not all([new_user, new_name, new_pass]):
                st.warning("Lengkapi username, nama, dan password.")
            elif sb is None:
                st.error("Supabase tidak terhubung.")
            else:
                # Hash password dengan hasher library (0.3.2)
                try:
                    hashed = stauth.Hasher([new_pass]).generate()[0]
                except Exception:
                    hashed = stauth.Hasher.hash(new_pass)  # versi lebih baru
                try:
                    sb.table("users").insert({
                        "username": new_user, "name": new_name,
                        "email": new_email, "password_hash": hashed,
                    }).execute()
                    st.success("Registrasi berhasil! Silakan masuk lewat tab 'Masuk'.")
                except Exception as exc:
                    st.error(f"Gagal mendaftar (username/email mungkin sudah dipakai): {exc}")
    return False, None, None


# ==============================================================================
# HALAMAN APLIKASI
# ==============================================================================
def page_dashboard():
    st.markdown('<p class="section-h" style="font-size:1.6rem;">Dashboard</p>', unsafe_allow_html=True)
    status, note, now = market_status()
    pill = "pill-open" if status == "Open" else "pill-closed"
    st.markdown(
        f'Status Bursa (IHSG): <span class="pill {pill}">{status}</span> '
        f'&nbsp;·&nbsp; {note} &nbsp;·&nbsp; {now.strftime("%A, %d %b %Y — %H:%M WIB")}',
        unsafe_allow_html=True,
    )
    st.caption("Jam bursa IDX (perkiraan): Sesi I 09:00, Sesi II s/d ~15:49 WIB. Jumat lebih singkat.")
    st.write(""); st.markdown("---")

    ihsg = get_info("^JKSE")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("IHSG", f"{ihsg.get('regularMarketPrice', '—'):,}" if ihsg.get("regularMarketPrice") else "—")
    c2.metric("Jam Sekarang", now.strftime("%H:%M"))
    c3.metric("Status", status)
    c4.metric("Hari Libur Terdaftar", f"{len(IDX_HOLIDAYS_2026)}")

    st.write("")
    if IDX_HOLIDAYS_2026:
        st.markdown('<p class="section-h">Kalender Libur Bursa</p>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(sorted(IDX_HOLIDAYS_2026), columns=["Tanggal Libur"]),
                     use_container_width=True, hide_index=True)
    else:
        st.info("Daftar libur bursa masih kosong — isi `IDX_HOLIDAYS_2026` dari kalender resmi IDX.")


def page_engine(sb, ticker):
    st.markdown('<p class="section-h" style="font-size:1.6rem;">The Engine — Rekomendasi Objektif</p>', unsafe_allow_html=True)
    style = st.radio("Gaya Investasi", ["Jangka Panjang", "Jangka Pendek", "Kombinasi"], horizontal=True)
    st.caption(f"Menganalisis {ticker} dengan profil: {style}")
    st.write("")

    r = recommendation_engine(sb, ticker, style)

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f'<span class="badge {r["cls"]}">{r["condition"]} CONDITION</span>', unsafe_allow_html=True)
        st.metric("Skor Komposit", f"{r['composite']:+.2f}", help="-1 (bearish) s/d +1 (bullish)")
        st.markdown(f"**Rekomendasi Aset:** {r['action']}")
    with c2:
        st.markdown('<p class="section-h">Komponen Penilaian</p>', unsafe_allow_html=True)
        st.write(f"📡 **Teknikal** ({r['style']}): skor {r['tech']:+.2f} — {', '.join(r['tech_reasons'][:3])}")
        st.write(f"🏦 **Broksum**: {r['broksum']} (net Rp {r['broksum_net']:,.0f})")
        st.write(f"📰 **Berita**: {r['news_label']}")

    st.write(""); st.markdown("---")
    if not r["df"].empty:
        st.markdown('<p class="section-h">Harga vs Moving Average</p>', unsafe_allow_html=True)
        st.line_chart(r["df"][["Close", "SMA20", "SMA50", "SMA200"]], height=300)
        cc1, cc2 = st.columns(2)
        cc1.line_chart(r["df"]["RSI"], height=200, color="#7c3aed")
        cc2.line_chart(r["df"][["MACD", "MACD_SIG"]], height=200)

    st.info("Kondisi & rekomendasi adalah hasil pengolahan data objektif untuk edukasi — "
            "bukan ajakan jual/beli, bukan nasihat investasi berlisensi.")


def page_fundamental(ticker):
    st.markdown('<p class="section-h" style="font-size:1.6rem;">Analisis Fundamental</p>', unsafe_allow_html=True)
    info = get_info(ticker)
    if not info:
        st.warning("Data fundamental tidak tersedia."); return
    st.subheader(info.get("shortName", ticker))

    def pv(k, mult=1, suf=""):
        v = info.get(k)
        return f"{v * mult:,.2f}{suf}" if v is not None else "—"

    metrics = pd.DataFrame({
        "Metrik": ["PER (P/E)", "PBV (P/B)", "ROE", "DER", "Dividend Yield", "EPS"],
        "Nilai": [
            pv("trailingPE", suf="x"), pv("priceToBook", suf="x"),
            pv("returnOnEquity", 100, "%"),
            pv("debtToEquity", 0.01, "x") if info.get("debtToEquity") else "—",
            pv("dividendYield", 100, "%") if info.get("dividendYield") else "—",
            pv("trailingEps"),
        ],
    })
    st.dataframe(metrics, use_container_width=True, hide_index=True)


def page_konglo(sb):
    st.markdown('<p class="section-h" style="font-size:1.6rem;">Radar Konglomerat (Konglo Tracker)</p>', unsafe_allow_html=True)
    st.caption("Kepemilikan ≥ 5% oleh taipan/institusi. Sumber: keterbukaan IDX/KSEI (diisi admin).")
    if sb is None:
        st.warning("Supabase tidak terhubung."); return
    try:
        rows = sb.table("konglo_tracker").select("*").order("persen_kepemilikan", desc=True).execute().data
    except Exception as exc:
        st.error(f"Gagal memuat data: {exc}"); return
    if not rows:
        st.info("Belum ada data. Isi tabel `konglo_tracker` di Supabase."); return
    df = pd.DataFrame(rows)
    cols = [c for c in ["kode_saham", "nama_pemilik", "tipe", "persen_kepemilikan", "tanggal_update", "sumber"] if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)


def page_news(ticker):
    st.markdown('<p class="section-h" style="font-size:1.6rem;">Portal Berita Emiten</p>', unsafe_allow_html=True)
    kode = ticker.replace(".JK", "")
    news = fetch_news(kode)
    if not news:
        st.info("Tidak ada berita terbaru ditemukan."); return
    score, label = news_score(news)
    st.markdown(f"**Sentimen agregat:** {label} ({score:+.2f})")
    st.write("")
    for n in news:
        st.markdown(f"🔗 [{n['judul']}]({n['link']})")
        if n.get("tanggal"):
            st.caption(n["tanggal"])
        st.write("")


def page_portfolio(sb, username, ticker):
    st.markdown('<p class="section-h" style="font-size:1.6rem;">Portofolio Saya</p>', unsafe_allow_html=True)
    if sb is None:
        st.warning("Supabase tidak terhubung."); return

    # Form tambah holding
    with st.expander("➕ Tambah / Perbarui Holding"):
        kode = st.text_input("Kode Saham", value=ticker.replace(".JK", ""))
        harga = st.number_input("Harga Rata-rata (Rp)", min_value=0.0, step=50.0)
        lot = st.number_input("Jumlah Lot", min_value=0, step=1)
        if st.button("Simpan", type="primary"):
            try:
                sb.table("portfolios").insert({
                    "username": username, "kode_saham": kode.strip().upper(),
                    "harga_rata2": harga, "jumlah_lot": int(lot),
                }).execute()
                st.success("Tersimpan."); st.rerun()
            except Exception as exc:
                st.error(f"Gagal menyimpan: {exc}")

    # Tampilkan holding milik user
    try:
        rows = sb.table("portfolios").select("*").eq("username", username).execute().data or []
    except Exception as exc:
        st.error(f"Gagal memuat portofolio: {exc}"); return
    if not rows:
        st.info("Portofolio masih kosong."); return

    out, total_modal, total_kini = [], 0, 0
    for r in rows:
        t = to_jk(r["kode_saham"])
        price = get_info(t).get("currentPrice")
        lot = r["jumlah_lot"]; avg = float(r["harga_rata2"])
        modal = avg * lot * LOT_SIZE
        kini = (price * lot * LOT_SIZE) if price else None
        pl = (kini - modal) if kini is not None else None
        plpct = (pl / modal * 100) if (pl is not None and modal) else None
        total_modal += modal
        if kini is not None:
            total_kini += kini
        out.append({"Kode": r["kode_saham"], "Lot": lot, "Avg": avg, "Harga Kini": price,
                    "Modal": modal, "Nilai Kini": kini, "P/L": pl, "P/L %": plpct})

    total_pl = total_kini - total_modal
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Modal", f"Rp {total_modal:,.0f}")
    c2.metric("Nilai Sekarang", f"Rp {total_kini:,.0f}")
    c3.metric("Total P/L", f"Rp {total_pl:,.0f}",
              f"{(total_pl / total_modal * 100) if total_modal else 0:+.2f}%")
    st.dataframe(pd.DataFrame(out), use_container_width=True, hide_index=True)


# ==============================================================================
# MAIN — alur gerbang & router
# ==============================================================================
def main():
    sb = get_supabase()

    # Gerbang 1: disclaimer
    if not disclaimer_gate():
        st.stop()

    # Gerbang 2: autentikasi
    auth_ok, username, name = auth_gate(sb)
    if not auth_ok:
        st.stop()

    # ---- Aplikasi utama ----
    with st.sidebar:
        st.markdown('<p class="brand">The Intrinsic</p>', unsafe_allow_html=True)
        st.markdown('<p class="brand-sub">Equity Research Platform</p>', unsafe_allow_html=True)
        if st.session_state.get("is_guest"):
            st.caption("👤 Tamu · mode demo")
            if st.button("Keluar", use_container_width=True):
                for k in ("is_guest", "authentication_status", "username", "name"):
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            st.caption(f"👤 {name}")
        st.markdown("---")
        page = st.radio("Navigasi", [
            "📊 Dashboard", "⚙️ The Engine", "🔍 Fundamental",
            "👑 Konglo Tracker", "📰 Berita", "💼 Portofolio",
        ], label_visibility="collapsed")
        st.markdown("---")
        ticker_input = st.text_input("Kode Saham", value="BMRI").strip().upper()
        ticker = to_jk(ticker_input)
        st.caption("Tanpa `.JK` — otomatis ditambahkan.")
        st.markdown("---")
        st.caption("⚠️ Bukan nasihat investasi.")

    if "Dashboard" in page:
        page_dashboard()
    elif "Engine" in page:
        page_engine(sb, ticker)
    elif "Fundamental" in page:
        page_fundamental(ticker)
    elif "Konglo" in page:
        page_konglo(sb)
    elif "Berita" in page:
        page_news(ticker)
    else:
        page_portfolio(sb, username, ticker)


if __name__ == "__main__":
    main()
