"""
================================================================================
THE INTRINSIC — Stock Research & Portfolio Management
Streamlit + Supabase | tema "Dark Elegant (fintech)"
================================================================================

Instalasi:
    pip install -r requirements.txt
Menjalankan:
    streamlit run app.py

Mode Tamu tersedia (tanpa Supabase/secrets) untuk mencoba aplikasi.

Filosofi compliance:
    Output mesin = KONDISI OBJEKTIF berbasis data (Bullish/Bearish/Neutral)
    + pertimbangan umum. BUKAN ajakan jual/beli, BUKAN nasihat berlisensi.
================================================================================
"""

import urllib.parse
from datetime import datetime, time as dtime

import numpy as np
import pandas as pd
import streamlit as st

from broksum_core import classify_nets

# --- Dependensi eksternal (dibungkus agar pesan errornya jelas) ---
try:
    from zoneinfo import ZoneInfo
    WIB = ZoneInfo("Asia/Jakarta")
except Exception:
    WIB = None
try:
    import yfinance as yf
except ImportError:
    yf = None
try:
    import feedparser
except ImportError:
    feedparser = None
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    go = None
    make_subplots = None
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

LOT_SIZE = 100  # 1 lot = 100 lembar

# Palet tema
ACCENT_A = "#6366f1"
ACCENT_B = "#a855f7"
UP = "#34d399"
DOWN = "#f87171"
GRID = "rgba(148,163,184,0.12)"

st.set_page_config(page_title="The Intrinsic", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

# ==============================================================================
# CSS — dark elegant + animasi
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root { --accent-a:#6366f1; --accent-b:#a855f7; }

html, body, [class*="css"] { font-family:'Plus Jakarta Sans', sans-serif; }

/* Latar gradient + blob beranimasi */
.stApp {
    background:
        radial-gradient(900px 600px at 12% -8%, rgba(99,102,241,0.18), transparent 60%),
        radial-gradient(800px 600px at 100% 0%, rgba(168,85,247,0.16), transparent 55%),
        radial-gradient(700px 700px at 60% 120%, rgba(16,185,129,0.10), transparent 55%),
        linear-gradient(180deg, #0b1020 0%, #0a0f1e 100%);
    background-attachment: fixed;
}
.stApp::before {
    content:""; position:fixed; inset:-20% -10% auto -10%; height:60vh; z-index:0;
    background: radial-gradient(closest-side, rgba(99,102,241,0.20), transparent);
    filter: blur(40px); animation: float1 16s ease-in-out infinite; pointer-events:none;
}
@keyframes float1 { 0%,100%{transform:translateY(0) translateX(0)} 50%{transform:translateY(40px) translateX(30px)} }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(19,26,48,0.92), rgba(11,16,32,0.92));
    border-right:1px solid rgba(255,255,255,0.06); backdrop-filter: blur(8px);
}
.block-container { padding-top:2.2rem; }

/* Brand / logo */
.brand-wrap { display:flex; align-items:center; gap:12px; }
.brand-mark { width:38px; height:38px; border-radius:11px; flex:0 0 auto;
    background:linear-gradient(135deg,var(--accent-a),var(--accent-b));
    box-shadow:0 8px 24px rgba(99,102,241,0.45); display:grid; place-items:center;
    animation: pop .6s cubic-bezier(.2,.8,.2,1) both; }
.brand-mark svg { width:22px; height:22px; }
.brand {
    font-size:1.5rem; font-weight:800; letter-spacing:-0.6px; line-height:1;
    background:linear-gradient(90deg,#fff, #c7d2fe 60%, #e9d5ff);
    -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
}
.brand-xl { font-size:2.6rem; }
.brand-sub { font-size:0.68rem; color:#8b93a7; letter-spacing:3px; text-transform:uppercase; margin-top:4px; }
@keyframes pop { from{transform:scale(.6) rotate(-8deg); opacity:0} to{transform:none; opacity:1} }

/* Glass cards */
.glass {
    background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
    border:1px solid rgba(255,255,255,0.08); border-radius:18px; padding:18px 20px;
    box-shadow:0 10px 30px rgba(2,6,23,0.45); backdrop-filter: blur(10px);
    animation: rise .6s cubic-bezier(.2,.8,.2,1) both;
}
.glass:hover { border-color: rgba(99,102,241,0.45); transform: translateY(-3px);
    transition: all .25s ease; box-shadow:0 18px 40px rgba(99,102,241,0.18); }
@keyframes rise { from{opacity:0; transform:translateY(14px)} to{opacity:1; transform:none} }

.kpi-label { color:#8b93a7; font-size:0.72rem; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; }
.kpi-value { font-family:'JetBrains Mono',monospace; font-size:1.9rem; font-weight:700; color:#f1f5f9; margin-top:6px; }
.kpi-sub { font-size:0.82rem; margin-top:4px; }
.up { color:#34d399; } .down { color:#f87171; } .muted{ color:#8b93a7; }

.section-h { font-size:1.05rem; font-weight:700; color:#e5e7eb; margin:6px 0 10px;
    display:flex; align-items:center; gap:8px; }
.section-h::before { content:""; width:4px; height:18px; border-radius:6px;
    background:linear-gradient(180deg,var(--accent-a),var(--accent-b)); }
.page-title { font-size:1.9rem; font-weight:800; color:#f8fafc; letter-spacing:-0.5px;
    animation: rise .5s ease both; }

/* Badge kondisi */
.badge { display:inline-block; padding:10px 26px; border-radius:12px; font-weight:800;
    font-size:1.15rem; letter-spacing:0.5px; animation: pop .5s ease both; }
.bull { background:rgba(52,211,153,0.16); color:#34d399; border:1px solid rgba(52,211,153,0.4); }
.bear { background:rgba(248,113,113,0.16); color:#f87171; border:1px solid rgba(248,113,113,0.4); }
.neut { background:rgba(250,204,21,0.16); color:#fde047; border:1px solid rgba(250,204,21,0.35); }

/* Pills & chips */
.pill { display:inline-block; padding:4px 14px; border-radius:999px; font-size:0.76rem; font-weight:700; }
.pill-open { background:rgba(52,211,153,0.18); color:#34d399; }
.pill-closed { background:rgba(148,163,184,0.16); color:#94a3b8; }
.dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; vertical-align:middle; }
.dot-open { background:#34d399; box-shadow:0 0 0 0 rgba(52,211,153,0.7); animation: ping 1.6s infinite; }
.dot-closed { background:#64748b; }
@keyframes ping { 0%{box-shadow:0 0 0 0 rgba(52,211,153,0.6)} 70%{box-shadow:0 0 0 10px rgba(52,211,153,0)} 100%{box-shadow:0 0 0 0 rgba(52,211,153,0)} }
.chip { display:inline-block; padding:3px 11px; border-radius:8px; font-size:0.74rem; font-weight:700; }
.chip-up { background:rgba(52,211,153,0.16); color:#34d399; }
.chip-down { background:rgba(248,113,113,0.16); color:#f87171; }
.chip-neut { background:rgba(148,163,184,0.16); color:#cbd5e1; }

/* Signal row */
.sig-row { display:flex; align-items:center; justify-content:space-between;
    padding:10px 14px; border-radius:12px; margin-bottom:8px;
    background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06);
    animation: rise .5s ease both; }
.sig-name { font-weight:600; color:#e5e7eb; }
.sig-val { font-family:'JetBrains Mono',monospace; color:#94a3b8; font-size:0.85rem; }

/* News card */
.news-card { display:block; text-decoration:none; padding:16px 18px; border-radius:16px; margin-bottom:12px;
    background:linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
    border:1px solid rgba(255,255,255,0.07); transition: all .2s ease; animation: rise .5s ease both; }
.news-card:hover { border-color:rgba(99,102,241,0.5); transform:translateX(4px); }
.news-title { color:#f1f5f9; font-weight:700; font-size:1rem; line-height:1.35; }
.news-meta { color:#8b93a7; font-size:0.76rem; margin-top:6px; }

/* Disclaimer hero */
.hero { text-align:center; padding:22px 0 8px; animation: rise .6s ease both; }
.disclaimer-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
    border:1px solid rgba(255,255,255,0.09); border-radius:22px; padding:30px 40px;
    box-shadow:0 24px 60px rgba(2,6,23,0.6); max-width:820px; margin:auto; backdrop-filter:blur(12px);
}

/* Inputs & radio nav */
.stTextInput input, .stNumberInput input { background:rgba(255,255,255,0.04)!important;
    border:1px solid rgba(255,255,255,0.1)!important; color:#e5e7eb!important; border-radius:10px!important; }
div[role="radiogroup"] label { padding:6px 10px; border-radius:10px; transition:all .15s ease; }
div[role="radiogroup"] label:hover { background:rgba(99,102,241,0.12); }

/* Buttons */
.stButton>button { border-radius:12px; font-weight:700; border:1px solid rgba(255,255,255,0.12);
    transition: all .2s ease; }
.stButton>button[kind="primary"] { background:linear-gradient(135deg,var(--accent-a),var(--accent-b));
    border:none; box-shadow:0 10px 26px rgba(99,102,241,0.4); }
.stButton>button[kind="primary"]:hover { transform:translateY(-2px); box-shadow:0 14px 34px rgba(99,102,241,0.55); }

/* Streamlit metric fallback */
div[data-testid="stMetricValue"] { color:#f1f5f9; font-family:'JetBrains Mono',monospace; }
div[data-testid="stMetricLabel"] { color:#8b93a7; }

#MainMenu, footer, header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# Logo SVG (kurva naik dalam kotak gradient)
_MARK_SVG = (
    '<svg viewBox="0 0 24 24" fill="none">'
    '<path d="M3 16.5L8.5 11L12 14L21 5" stroke="white" stroke-width="2.4" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '<circle cx="21" cy="5" r="2" fill="white"/></svg>'
)


def render_brand(big: bool = False, sub: bool = True):
    cls = "brand brand-xl" if big else "brand"
    html = f'<div class="brand-wrap"><div class="brand-mark">{_MARK_SVG}</div>' \
           f'<div><div class="{cls}">The Intrinsic</div>'
    if sub:
        html += '<div class="brand-sub">Equity Research Platform</div>'
    html += '</div></div>'
    st.markdown(html, unsafe_allow_html=True)


# ==============================================================================
# KONEKSI SUPABASE
# ==============================================================================
@st.cache_resource
def get_supabase() -> "Client":
    if create_client is None:
        return None
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception:
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


@st.cache_data(ttl=3600, show_spinner=False)
def get_financials(ticker: str) -> dict:
    """Ambil laporan laba-rugi tahunan & riwayat dividen (untuk grafik)."""
    if yf is None:
        return {}
    out = {}
    try:
        t = yf.Ticker(ticker)
        try:
            out["income"] = t.income_stmt
        except Exception:
            out["income"] = None
        try:
            out["dividends"] = t.dividends
        except Exception:
            out["dividends"] = None
    except Exception:
        return {}
    return out


def to_jk(kode: str) -> str:
    kode = kode.strip().upper()
    return kode if kode.endswith(".JK") else f"{kode}.JK"


def fmt_rp(v, dec=0):
    try:
        return f"Rp {v:,.{dec}f}"
    except Exception:
        return "—"


# ==============================================================================
# STATUS BURSA
# ==============================================================================
IDX_HOLIDAYS_2026 = set()


def _now_wib():
    return datetime.now(WIB) if WIB else datetime.now()


def market_status() -> tuple:
    now = _now_wib()
    if now.weekday() >= 5:
        return "Closed", "Akhir pekan", now
    if now.date().isoformat() in IDX_HOLIDAYS_2026:
        return "Closed", "Hari libur bursa", now
    t = now.time()
    if now.weekday() == 4:
        sesi1 = dtime(9, 0) <= t <= dtime(11, 30)
        sesi2 = dtime(14, 0) <= t <= dtime(15, 49)
    else:
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
# PLOTLY — styling konsisten (dark, transparan)
# ==============================================================================
def _style_fig(fig, height=320, legend=True):
    fig.update_layout(
        height=height, margin=dict(l=6, r=6, t=24, b=6),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", color="#cbd5e1", size=12),
        hoverlabel=dict(bgcolor="#131a30", font_size=12),
        showlegend=legend,
        legend=dict(orientation="h", y=1.14, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, showline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, showline=False)
    return fig


def _plot(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ==============================================================================
# MESIN INDIKATOR TEKNIKAL (kaya: EMA/SMA/RSI/MACD/BB/Stoch/ADX/ATR/ROC/OBV)
# ==============================================================================
def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _true_range(h, l, c):
    pc = c.shift(1)
    return pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)


def _adx(h, l, c, period=14):
    up = h.diff()
    dn = -l.diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = _true_range(h, l, c)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    pdi = 100 * pd.Series(plus_dm, index=h.index).ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)
    ndi = 100 * pd.Series(minus_dm, index=h.index).ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return adx, pdi, ndi


def compute_indicators(hist: pd.DataFrame) -> pd.DataFrame:
    if hist is None or hist.empty:
        return pd.DataFrame()
    df = hist.copy()
    c, h, l = df["Close"], df["High"], df["Low"]
    v = df["Volume"] if "Volume" in df else None

    df["EMA9"] = c.ewm(span=9, adjust=False).mean()
    df["EMA21"] = c.ewm(span=21, adjust=False).mean()
    df["SMA20"] = c.rolling(20).mean()
    df["SMA50"] = c.rolling(50).mean()
    df["SMA100"] = c.rolling(100).mean()
    df["SMA200"] = c.rolling(200).mean()

    df["RSI14"] = _rsi(c, 14)
    df["RSI7"] = _rsi(c, 7)

    e12 = c.ewm(span=12, adjust=False).mean()
    e26 = c.ewm(span=26, adjust=False).mean()
    df["MACD"] = e12 - e26
    df["MACD_SIG"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIG"]

    m = c.rolling(20).mean()
    s = c.rolling(20).std()
    df["BB_MID"], df["BB_UP"], df["BB_LO"] = m, m + 2 * s, m - 2 * s
    df["BB_PCTB"] = (c - df["BB_LO"]) / (df["BB_UP"] - df["BB_LO"]).replace(0, np.nan)

    ll, hh = l.rolling(14).min(), h.rolling(14).max()
    df["STOCH_K"] = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
    df["STOCH_D"] = df["STOCH_K"].rolling(3).mean()

    tr = _true_range(h, l, c)
    df["ATR"] = tr.rolling(14).mean()
    df["ATR_PCT"] = df["ATR"] / c * 100
    df["ADX"], df["PDI"], df["NDI"] = _adx(h, l, c, 14)
    df["ROC"] = c.pct_change(12) * 100
    if v is not None:
        df["OBV"] = (np.sign(c.diff()).fillna(0) * v).cumsum()
    df["HI52"] = c.rolling(252, min_periods=20).max()
    df["LO52"] = c.rolling(252, min_periods=20).min()
    return df


def _zone(v, low, high):
    if pd.isna(v):
        return 0
    if v < low:
        return 1
    if v > high:
        return -1
    return 0


def _short_signals(last):
    sig = {}
    det = []
    sig["ema_fast"] = 1 if (pd.notna(last["EMA9"]) and last["EMA9"] > last["EMA21"]) else -1
    det.append(("Tren cepat (EMA9 vs EMA21)", f"{last['EMA9']:.0f} / {last['EMA21']:.0f}", sig["ema_fast"]))

    sig["rsi7"] = _zone(last["RSI7"], 30, 70)
    det.append(("RSI(7)", f"{last['RSI7']:.0f}" if pd.notna(last['RSI7']) else "—", sig["rsi7"]))

    k, d = last["STOCH_K"], last["STOCH_D"]
    if pd.isna(k):
        sig["stoch"] = 0
    elif k < 20:
        sig["stoch"] = 1
    elif k > 80:
        sig["stoch"] = -1
    else:
        sig["stoch"] = 1 if (pd.notna(d) and k > d) else -1
    det.append(("Stochastic %K/%D", f"{k:.0f}/{d:.0f}" if pd.notna(k) else "—", sig["stoch"]))

    sig["macd_h"] = 1 if (pd.notna(last["MACD_HIST"]) and last["MACD_HIST"] > 0) else -1
    det.append(("Momentum MACD (hist)", f"{last['MACD_HIST']:+.2f}" if pd.notna(last['MACD_HIST']) else "—", sig["macd_h"]))

    sig["roc"] = 1 if (pd.notna(last["ROC"]) and last["ROC"] > 0) else -1
    det.append(("ROC(12)", f"{last['ROC']:+.1f}%" if pd.notna(last['ROC']) else "—", sig["roc"]))

    w = {"ema_fast": 0.25, "stoch": 0.20, "rsi7": 0.20, "macd_h": 0.20, "roc": 0.15}
    score = sum(sig[k] * w[k] for k in w)
    return float(np.clip(score, -1, 1)), det


def _long_signals(last):
    sig = {}
    det = []
    sig["t200"] = 1 if (pd.notna(last["SMA200"]) and last["Close"] > last["SMA200"]) else -1
    det.append(("Harga vs SMA200", "di atas" if sig["t200"] > 0 else "di bawah", sig["t200"]))

    sig["gcross"] = 1 if (pd.notna(last["SMA50"]) and pd.notna(last["SMA200"]) and last["SMA50"] > last["SMA200"]) else -1
    det.append(("Golden/Death Cross (50/200)", "golden" if sig["gcross"] > 0 else "death", sig["gcross"]))

    adx, pdi, ndi = last["ADX"], last["PDI"], last["NDI"]
    if pd.isna(adx) or adx <= 20:
        sig["adx"] = 0
        adx_note = f"lemah (ADX {adx:.0f})" if pd.notna(adx) else "—"
    else:
        sig["adx"] = 1 if pdi > ndi else -1
        adx_note = f"kuat {'naik' if pdi>ndi else 'turun'} (ADX {adx:.0f})"
    det.append(("Kekuatan tren (ADX/DI)", adx_note, sig["adx"]))

    sig["rsi14"] = _zone(last["RSI14"], 30, 70)
    det.append(("RSI(14)", f"{last['RSI14']:.0f}" if pd.notna(last['RSI14']) else "—", sig["rsi14"]))

    if pd.notna(last["HI52"]) and pd.notna(last["LO52"]) and last["HI52"] > last["LO52"]:
        pos = (last["Close"] - last["LO52"]) / (last["HI52"] - last["LO52"])
        sig["pos52"] = 1 if pos > 0.7 else (-1 if pos < 0.3 else 0)
        det.append(("Posisi di rentang 52 minggu", f"{pos*100:.0f}%", sig["pos52"]))
    else:
        sig["pos52"] = 0
        det.append(("Posisi di rentang 52 minggu", "—", 0))

    sig["macd"] = 1 if (pd.notna(last["MACD"]) and last["MACD"] > last["MACD_SIG"]) else -1
    det.append(("MACD vs Signal", "bullish" if sig["macd"] > 0 else "bearish", sig["macd"]))

    w = {"t200": 0.30, "gcross": 0.20, "adx": 0.20, "rsi14": 0.10, "pos52": 0.10, "macd": 0.10}
    score = sum(sig[k] * w[k] for k in w)
    return float(np.clip(score, -1, 1)), det


def technical_score(df: pd.DataFrame, style: str):
    """Skor -1..+1 + rincian sinyal. Indikator BERBEDA per gaya investasi."""
    if df is None or df.empty or len(df) < 30:
        return 0.0, [("Data historis tidak cukup", "—", 0)]
    last = df.iloc[-1]
    s_score, s_det = _short_signals(last)
    l_score, l_det = _long_signals(last)
    if style == "Jangka Pendek":
        return s_score, s_det
    if style == "Jangka Panjang":
        return l_score, l_det
    # Kombinasi: gabungan kedua kerangka
    return float(np.clip(0.5 * s_score + 0.5 * l_score, -1, 1)), (l_det + s_det)


# ==============================================================================
# BROKSUM (API FastAPI atau Supabase; logika di broksum_core)
# ==============================================================================
def _broksum_api_url() -> str:
    try:
        url = st.secrets["broksum"]["api_url"]
        return url.rstrip("/") if url else ""
    except Exception:
        return ""


def broksum_score(sb, kode: str):
    api_url = _broksum_api_url()
    if api_url and requests is not None:
        try:
            resp = requests.get(f"{api_url}/broksum/{kode}/score", timeout=8)
            if resp.ok:
                d = resp.json()
                return float(d["score"]), str(d["label"]), int(d["total_net"])
        except Exception:
            pass
    if sb is None:
        return 0.0, "Data broksum tidak tersedia", 0
    try:
        res = sb.table("broker_summary").select("net_value").eq("kode_saham", kode).execute()
        rows = res.data or []
    except Exception:
        return 0.0, "Gagal membaca broksum", 0
    if not rows:
        return 0.0, "Belum ada data broksum", 0
    r = classify_nets([x.get("net_value", 0) for x in rows])
    return r["score"], r["label"], r["total_net"]


# ==============================================================================
# BERITA & SENTIMEN (RSS Google News)
# ==============================================================================
POS_WORDS = {"laba", "naik", "untung", "ekspansi", "akuisisi", "dividen", "rekor",
             "tumbuh", "positif", "stock split", "buyback", "kontrak", "melonjak", "cuan"}
NEG_WORDS = {"rugi", "turun", "anjlok", "gugatan", "default", "pailit", "phk",
             "negatif", "denda", "investigasi", "suspensi", "delisting", "merosot", "tekan"}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news(kode_polos: str) -> list:
    if feedparser is None:
        return []
    q = urllib.parse.quote(f"{kode_polos} saham emiten")
    url = f"https://news.google.com/rss/search?q={q}&hl=id&gl=ID&ceid=ID:id"
    try:
        feed = feedparser.parse(url)
        out = []
        for e in feed.entries[:10]:
            title = e.get("title", "")
            tl = title.lower()
            sc = sum(1 for w in POS_WORDS if w in tl) - sum(1 for w in NEG_WORDS if w in tl)
            src = ""
            if " - " in title:
                src = title.rsplit(" - ", 1)[-1]
            out.append({"judul": title, "link": e.get("link", ""),
                        "tanggal": e.get("published", ""), "sumber": src, "skor": sc})
        return out
    except Exception:
        return []


def news_score(news: list):
    if not news:
        return 0.0, "Tidak ada berita terbaru"
    s = sum(n.get("skor", 0) for n in news)
    norm = float(np.clip(s / max(len(news), 1), -1, 1))
    label = "Sentimen positif" if norm > 0.1 else ("Sentimen negatif" if norm < -0.1 else "Sentimen netral")
    return norm, label


# ==============================================================================
# MESIN REKOMENDASI GABUNGAN
# ==============================================================================
def recommendation_engine(sb, ticker: str, style: str) -> dict:
    kode_polos = ticker.replace(".JK", "")
    period = {"Jangka Panjang": "2y", "Jangka Pendek": "6mo"}.get(style, "1y")
    df = compute_indicators(get_history(ticker, period=period))
    tech, tech_det = technical_score(df, style)
    bk_score, bk_label, bk_net = broksum_score(sb, kode_polos)
    news = fetch_news(kode_polos)
    nw_score, nw_label = news_score(news)

    composite = 0.55 * tech + 0.30 * bk_score + 0.15 * nw_score
    if composite >= 0.2:
        condition, cls, action = "BULLISH", "bull", "Pertimbangkan Tambah Muatan (Buy)"
    elif composite <= -0.2:
        condition, cls, action = "BEARISH", "bear", "Pertimbangkan Kurangi Risiko (Sell)"
    else:
        condition, cls, action = "NEUTRAL", "neut", "Pertahankan (Hold)"
    return {"composite": composite, "condition": condition, "cls": cls, "action": action,
            "tech": tech, "tech_det": tech_det, "broksum": bk_label, "broksum_net": bk_net,
            "news_label": nw_label, "news_score": nw_score, "news": news, "df": df, "style": style}


# ==============================================================================
# KOMPONEN UI
# ==============================================================================
def kpi_card(label, value, sub_html="", accent=False):
    border = f"border-color:rgba(99,102,241,0.4);" if accent else ""
    return (f'<div class="glass" style="{border}">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-sub">{sub_html}</div></div>')


def signal_row(name, val, sig):
    if sig > 0:
        chip = '<span class="chip chip-up">Bullish</span>'
    elif sig < 0:
        chip = '<span class="chip chip-down">Bearish</span>'
    else:
        chip = '<span class="chip chip-neut">Netral</span>'
    return (f'<div class="sig-row"><div><span class="sig-name">{name}</span>'
            f'<br><span class="sig-val">{val}</span></div>{chip}</div>')


# ==============================================================================
# GERBANG 1: DISCLAIMER
# ==============================================================================
def disclaimer_gate() -> bool:
    if st.session_state.get("agreed_disclaimer"):
        return True
    st.write("")
    st.markdown('<div class="disclaimer-card">', unsafe_allow_html=True)
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    render_brand(big=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("### ⚠️ Disclaimer & Ketentuan Penggunaan")
    st.markdown("""
**The Intrinsic bukan penasihat keuangan berlisensi.** Seluruh informasi, skor, dan "kondisi"
(Bullish/Bearish/Neutral) adalah **hasil pengolahan data objektif** (teknikal, broker summary,
berita publik) untuk **edukasi & riset mandiri**.

- Ini **bukan ajakan, rekomendasi, atau solicitation** untuk membeli/menjual efek.
- Kinerja masa lalu **tidak menjamin** hasil di masa depan.
- **Keputusan investasi sepenuhnya tanggung jawab Anda.** Pertimbangkan konsultasi dengan
  penasihat keuangan/Wakil Manajer Investasi berizin OJK.
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
# GERBANG 2: AUTENTIKASI + MODE TAMU
# ==============================================================================
def load_credentials(sb) -> dict:
    creds = {"usernames": {}}
    if sb is None:
        return creds
    try:
        rows = sb.table("users").select("username,name,email,password_hash").execute().data or []
        for r in rows:
            creds["usernames"][r["username"]] = {
                "name": r.get("name", r["username"]), "email": r.get("email", ""),
                "password": r["password_hash"]}
    except Exception as exc:
        st.error(f"Gagal memuat kredensial: {exc}")
    return creds


def _authenticator_configured() -> bool:
    try:
        return bool(st.secrets["authenticator"]["cookie_name"])
    except Exception:
        return False


def auth_gate(sb):
    if st.session_state.get("is_guest"):
        return True, "guest", "Tamu"

    st.write("")
    cL, cM, cR = st.columns([1, 2, 1])
    with cM:
        st.markdown('<div class="hero">', unsafe_allow_html=True)
        render_brand(big=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.info("**Mode Tamu** — jelajahi aplikasi tanpa akun. Portofolio & Konglo Tracker "
                "(butuh database) dinonaktifkan sampai Supabase dikonfigurasi.")
        if st.button("👤 Masuk sebagai Tamu", type="primary", use_container_width=True):
            st.session_state["is_guest"] = True
            st.rerun()

        if stauth is None or sb is None or not _authenticator_configured():
            st.caption("Login akun dinonaktifkan (streamlit-authenticator/Supabase/secrets belum siap).")
            return False, None, None

        st.markdown("---")
        creds = load_credentials(sb)
        authenticator = stauth.Authenticate(
            creds, st.secrets["authenticator"]["cookie_name"],
            st.secrets["authenticator"]["cookie_key"],
            int(st.secrets["authenticator"]["cookie_expiry_days"]))
        tab_login, tab_register = st.tabs(["🔑 Masuk", "📝 Daftar"])
        with tab_login:
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
            nu = st.text_input("Username", key="reg_user")
            nn = st.text_input("Nama Lengkap", key="reg_name")
            ne = st.text_input("Email", key="reg_email")
            npw = st.text_input("Password", type="password", key="reg_pass")
            if st.button("Daftar", type="primary"):
                if not all([nu, nn, npw]):
                    st.warning("Lengkapi username, nama, dan password.")
                else:
                    try:
                        hashed = stauth.Hasher([npw]).generate()[0]
                    except Exception:
                        hashed = stauth.Hasher.hash(npw)
                    try:
                        sb.table("users").insert({"username": nu, "name": nn,
                                                  "email": ne, "password_hash": hashed}).execute()
                        st.success("Registrasi berhasil! Silakan masuk lewat tab 'Masuk'.")
                    except Exception as exc:
                        st.error(f"Gagal mendaftar (username/email mungkin sudah dipakai): {exc}")
    return False, None, None


# ==============================================================================
# HALAMAN: DASHBOARD
# ==============================================================================
def page_dashboard():
    st.markdown('<p class="page-title">Dashboard</p>', unsafe_allow_html=True)
    status, note, now = market_status()
    pill = "pill-open" if status == "Open" else "pill-closed"
    dot = "dot-open" if status == "Open" else "dot-closed"
    st.markdown(
        f'<div style="margin:-4px 0 14px;color:#cbd5e1;">'
        f'<span class="dot {dot}"></span>Status Bursa (IHSG): '
        f'<span class="pill {pill}">{status}</span> &nbsp;·&nbsp; {note} '
        f'&nbsp;·&nbsp; <span class="muted">{now.strftime("%A, %d %b %Y — %H:%M WIB")}</span></div>',
        unsafe_allow_html=True)

    # Data IHSG
    hist = get_history("^JKSE", period="6mo")
    info = get_info("^JKSE")
    last_px = info.get("regularMarketPrice")
    chg = chg_pct = None
    if not hist.empty and "Close" in hist:
        closes = hist["Close"].dropna()
        if last_px is None and len(closes):
            last_px = float(closes.iloc[-1])
        if len(closes) >= 2:
            prev = float(closes.iloc[-2])
            chg = float(closes.iloc[-1]) - prev
            chg_pct = (chg / prev * 100) if prev else None

    def delta_html(c, p):
        if c is None:
            return '<span class="muted">—</span>'
        cls = "up" if c >= 0 else "down"
        arrow = "▲" if c >= 0 else "▼"
        return f'<span class="{cls}">{arrow} {c:,.2f} ({p:+.2f}%)</span>'

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi_card("IHSG", f"{last_px:,.2f}" if last_px else "—",
                         delta_html(chg, chg_pct), accent=True), unsafe_allow_html=True)
    c2.markdown(kpi_card("Jam (WIB)", now.strftime("%H:%M"),
                         f'<span class="muted">{now.strftime("%d %b %Y")}</span>'), unsafe_allow_html=True)
    c3.markdown(kpi_card("Status Bursa", status,
                         f'<span class="muted">{note}</span>'), unsafe_allow_html=True)
    hi = f"{hist['Close'].max():,.0f}" if not hist.empty else "—"
    c4.markdown(kpi_card("Tertinggi 6 Bln", hi,
                         '<span class="muted">penutupan harian</span>'), unsafe_allow_html=True)

    st.write("")
    st.markdown('<p class="section-h">Pergerakan IHSG — 6 Bulan</p>', unsafe_allow_html=True)
    if not hist.empty and go is not None:
        closes = hist["Close"].dropna()
        line_color = UP if (chg is None or chg >= 0) else DOWN
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=closes.index, y=closes.values, mode="lines", name="IHSG",
            line=dict(color=line_color, width=2.4),
            fill="tozeroy", fillcolor="rgba(52,211,153,0.10)" if line_color == UP else "rgba(248,113,113,0.10)"))
        fig.update_yaxes(range=[closes.min() * 0.985, closes.max() * 1.01])
        _plot(_style_fig(fig, height=340, legend=False))
    else:
        st.markdown('<div class="glass"><span class="muted">Grafik IHSG tidak tersedia '
                    '(butuh koneksi internet untuk yfinance).</span></div>', unsafe_allow_html=True)

    st.caption("Jam bursa IDX (perkiraan): Sesi I 09:00, Sesi II s/d ~15:49 WIB. Jumat lebih singkat.")


# ==============================================================================
# HALAMAN: THE ENGINE
# ==============================================================================
def page_engine(sb, ticker):
    st.markdown('<p class="page-title">The Engine — Rekomendasi Objektif</p>', unsafe_allow_html=True)
    style = st.radio("Gaya Investasi", ["Jangka Panjang", "Jangka Pendek", "Kombinasi"], horizontal=True)
    desc = {"Jangka Panjang": "SMA50/200, Golden Cross, ADX/DI, posisi 52 minggu, MACD.",
            "Jangka Pendek": "EMA9/21, RSI(7), Stochastic, momentum MACD, ROC.",
            "Kombinasi": "Gabungan kerangka jangka panjang + jangka pendek."}
    st.caption(f"Menganalisis **{ticker}** · profil **{style}** — indikator: {desc[style]}")
    st.write("")

    with st.spinner("Menghitung sinyal…"):
        r = recommendation_engine(sb, ticker, style)

    c1, c2 = st.columns([1, 1.6])
    with c1:
        st.markdown(f'<span class="badge {r["cls"]}">{r["condition"]}</span>', unsafe_allow_html=True)
        st.write("")
        st.markdown(kpi_card("Skor Komposit", f'{r["composite"]:+.2f}',
                             '<span class="muted">−1 bearish · +1 bullish</span>', accent=True),
                    unsafe_allow_html=True)
        st.write("")
        bnet = fmt_rp(r["broksum_net"])
        st.markdown(
            f'<div class="glass">'
            f'<div class="kpi-label">Komponen</div>'
            f'<div style="margin-top:8px;line-height:2.0">'
            f'📡 Teknikal <b class="{"up" if r["tech"]>=0 else "down"}">{r["tech"]:+.2f}</b><br>'
            f'🏦 Broksum <b>{r["broksum"]}</b> <span class="muted">({bnet})</span><br>'
            f'📰 Berita <b class="{"up" if r["news_score"]>=0 else ("down" if r["news_score"]<0 else "muted")}">{r["news_label"]}</b>'
            f'</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<p class="section-h">Rincian Sinyal Teknikal</p>', unsafe_allow_html=True)
        for name, val, sig in r["tech_det"]:
            st.markdown(signal_row(name, val, sig), unsafe_allow_html=True)

    st.write("")
    df = r["df"]
    if not df.empty and go is not None:
        st.markdown('<p class="section-h">Grafik Harga & Indikator</p>', unsafe_allow_html=True)
        _engine_charts(df, style)
    st.info("Kondisi & rekomendasi = hasil pengolahan data objektif untuk edukasi — "
            "bukan ajakan jual/beli, bukan nasihat investasi berlisensi.", icon="⚠️")


def _engine_charts(df, style):
    tail = df.tail(180) if style == "Jangka Pendek" else df.tail(400)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.56, 0.22, 0.22],
                        vertical_spacing=0.04,
                        subplot_titles=("Harga", "RSI", "MACD"))
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=tail.index, open=tail["Open"], high=tail["High"], low=tail["Low"], close=tail["Close"],
        name="Harga", increasing_line_color=UP, decreasing_line_color=DOWN,
        increasing_fillcolor=UP, decreasing_fillcolor=DOWN), row=1, col=1)
    if style == "Jangka Pendek":
        for col, color in [("EMA9", "#60a5fa"), ("EMA21", "#f59e0b")]:
            fig.add_trace(go.Scatter(x=tail.index, y=tail[col], name=col,
                                     line=dict(width=1.5, color=color)), row=1, col=1)
        for col in ["BB_UP", "BB_LO"]:
            fig.add_trace(go.Scatter(x=tail.index, y=tail[col], name="Bollinger",
                                     line=dict(width=1, color="rgba(148,163,184,0.4)"),
                                     showlegend=(col == "BB_UP")), row=1, col=1)
        rsi_col = "RSI7"
    else:
        for col, color in [("SMA50", "#60a5fa"), ("SMA200", "#f59e0b")]:
            fig.add_trace(go.Scatter(x=tail.index, y=tail[col], name=col,
                                     line=dict(width=1.6, color=color)), row=1, col=1)
        rsi_col = "RSI14"
    # RSI
    fig.add_trace(go.Scatter(x=tail.index, y=tail[rsi_col], name=rsi_col,
                             line=dict(width=1.6, color=ACCENT_B)), row=2, col=1)
    fig.add_hline(y=70, line=dict(color="rgba(248,113,113,0.4)", dash="dot"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="rgba(52,211,153,0.4)", dash="dot"), row=2, col=1)
    # MACD
    colors = [UP if v >= 0 else DOWN for v in tail["MACD_HIST"].fillna(0)]
    fig.add_trace(go.Bar(x=tail.index, y=tail["MACD_HIST"], name="Hist", marker_color=colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=tail.index, y=tail["MACD"], name="MACD",
                             line=dict(width=1.4, color="#60a5fa")), row=3, col=1)
    fig.add_trace(go.Scatter(x=tail.index, y=tail["MACD_SIG"], name="Signal",
                             line=dict(width=1.4, color="#f59e0b")), row=3, col=1)
    fig.update_layout(xaxis_rangeslider_visible=False)
    for a in fig.layout.annotations:
        a.font.update(size=12, color="#94a3b8")
    _plot(_style_fig(fig, height=620))


# ==============================================================================
# HALAMAN: FUNDAMENTAL
# ==============================================================================
def _gauge(title, value, vmin, vmax, good="low", suffix=""):
    """Gauge Plotly. good='low' artinya makin kecil makin baik (hijau di kiri)."""
    if value is None:
        return None
    bar = ACCENT_A
    g, y, r = ("rgba(52,211,153,0.25)", "rgba(250,204,21,0.25)", "rgba(248,113,113,0.25)")
    third = (vmax - vmin) / 3
    if good == "low":
        steps = [{"range": [vmin, vmin + third], "color": g},
                 {"range": [vmin + third, vmin + 2 * third], "color": y},
                 {"range": [vmin + 2 * third, vmax], "color": r}]
    else:
        steps = [{"range": [vmin, vmin + third], "color": r},
                 {"range": [vmin + third, vmin + 2 * third], "color": y},
                 {"range": [vmin + 2 * third, vmax], "color": g}]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={"suffix": suffix, "font": {"size": 26, "color": "#f1f5f9"}},
        gauge={"axis": {"range": [vmin, vmax], "tickcolor": "#64748b"},
               "bar": {"color": bar, "thickness": 0.28},
               "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0, "steps": steps},
        title={"text": title, "font": {"size": 13, "color": "#94a3b8"}}))
    fig.update_layout(height=200, margin=dict(l=18, r=18, t=46, b=8),
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Plus Jakarta Sans"))
    return fig


def page_fundamental(ticker):
    st.markdown('<p class="page-title">Analisis Fundamental</p>', unsafe_allow_html=True)
    info = get_info(ticker)
    if not info:
        st.markdown('<div class="glass"><span class="muted">Data fundamental tidak tersedia '
                    '(butuh koneksi internet / kode salah).</span></div>', unsafe_allow_html=True)
        return

    name = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector", "—")
    industry = info.get("industry", "—")
    mcap = info.get("marketCap")
    price = info.get("currentPrice") or info.get("regularMarketPrice")

    # Header profil
    st.markdown(
        f'<div class="glass" style="border-color:rgba(99,102,241,0.4)">'
        f'<div style="font-size:1.4rem;font-weight:800;color:#f8fafc">{name}</div>'
        f'<div class="muted" style="margin-top:4px">{sector} · {industry}</div>'
        f'<div style="margin-top:10px">'
        f'<span class="chip chip-neut">Harga: {fmt_rp(price)}</span> &nbsp;'
        f'<span class="chip chip-neut">Market Cap: {fmt_rp(mcap)}</span></div>'
        f'</div>', unsafe_allow_html=True)
    st.write("")

    # Gauges
    per = info.get("trailingPE")
    pbv = info.get("priceToBook")
    roe = info.get("returnOnEquity")
    der = info.get("debtToEquity")
    dy = info.get("dividendYield")
    st.markdown('<p class="section-h">Rasio Kunci</p>', unsafe_allow_html=True)
    if go is not None:
        g1, g2, g3 = st.columns(3)
        with g1:
            f = _gauge("PER (P/E) — makin rendah makin murah", per, 0, 40, "low", "x")
            if f: _plot(f)
            else: st.caption("PER: —")
        with g2:
            f = _gauge("PBV (P/B) — makin rendah makin murah", pbv, 0, 8, "low", "x")
            if f: _plot(f)
            else: st.caption("PBV: —")
        with g3:
            f = _gauge("ROE — makin tinggi makin baik", roe * 100 if roe is not None else None, 0, 40, "high", "%")
            if f: _plot(f)
            else: st.caption("ROE: —")
        g4, g5, g6 = st.columns(3)
        with g4:
            f = _gauge("DER — makin rendah makin aman", der, 0, 200, "low", "")
            if f: _plot(f)
            else: st.caption("DER: —")
        with g5:
            f = _gauge("Dividend Yield", dy * 100 if dy is not None else None, 0, 12, "high", "%")
            if f: _plot(f)
            else: st.caption("Dividend Yield: —")
        with g6:
            eps = info.get("trailingEps")
            st.markdown(kpi_card("EPS (TTM)", f"{eps:,.0f}" if eps is not None else "—",
                                 '<span class="muted">laba per saham</span>'), unsafe_allow_html=True)

    # 52-week position bar
    lo, hi = info.get("fiftyTwoWeekLow"), info.get("fiftyTwoWeekHigh")
    if lo and hi and price and hi > lo:
        pos = max(0, min(1, (price - lo) / (hi - lo))) * 100
        st.write("")
        st.markdown('<p class="section-h">Posisi Harga · Rentang 52 Minggu</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="glass"><div style="display:flex;justify-content:space-between;'
            f'font-size:0.8rem;color:#94a3b8"><span>{fmt_rp(lo)}</span><span>{fmt_rp(hi)}</span></div>'
            f'<div style="position:relative;height:12px;border-radius:999px;margin:8px 0;'
            f'background:linear-gradient(90deg,#f87171,#fde047,#34d399)">'
            f'<div style="position:absolute;left:{pos}%;top:-5px;width:4px;height:22px;'
            f'border-radius:4px;background:#fff;box-shadow:0 0 10px rgba(255,255,255,0.8);'
            f'transform:translateX(-2px)"></div></div>'
            f'<div style="text-align:center;color:#cbd5e1">Berada di <b>{pos:.0f}%</b> rentang 52 minggu</div>'
            f'</div>', unsafe_allow_html=True)

    # Revenue / Net income chart
    fin = get_financials(ticker)
    inc = fin.get("income") if fin else None
    if go is not None and inc is not None and not getattr(inc, "empty", True):
        try:
            cols = list(inc.columns)[:4][::-1]
            years = [pd.Timestamp(c).year for c in cols]
            rev = [inc.loc["Total Revenue", c] if "Total Revenue" in inc.index else None for c in cols]
            ni = [inc.loc["Net Income", c] if "Net Income" in inc.index else None for c in cols]
            if any(v is not None for v in rev):
                st.write("")
                st.markdown('<p class="section-h">Pendapatan & Laba Bersih (Tahunan)</p>', unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(go.Bar(x=years, y=rev, name="Pendapatan", marker_color=ACCENT_A))
                fig.add_trace(go.Bar(x=years, y=ni, name="Laba Bersih", marker_color=UP))
                fig.update_layout(barmode="group", xaxis=dict(type="category"))
                _plot(_style_fig(fig, height=320))
        except Exception:
            pass

    st.caption("Sumber: yfinance. Data dapat tertunda/tidak lengkap — verifikasi ke laporan resmi emiten.")


# ==============================================================================
# HALAMAN: KONGLO TRACKER
# ==============================================================================
def page_konglo(sb):
    st.markdown('<p class="page-title">Radar Konglomerat</p>', unsafe_allow_html=True)
    st.caption("Kepemilikan ≥ 5% oleh taipan/institusi. Sumber: keterbukaan IDX/KSEI (diisi admin).")
    if sb is None:
        st.markdown('<div class="glass"><span class="muted">Supabase tidak terhubung. '
                    'Fitur ini butuh database (nonaktif di Mode Tamu).</span></div>', unsafe_allow_html=True)
        return
    try:
        rows = sb.table("konglo_tracker").select("*").order("persen_kepemilikan", desc=True).execute().data
    except Exception as exc:
        st.error(f"Gagal memuat data: {exc}")
        return
    if not rows:
        st.info("Belum ada data. Isi tabel `konglo_tracker` di Supabase (lihat db/seed_konglo.sql).")
        return
    df = pd.DataFrame(rows)
    cols = [c for c in ["kode_saham", "nama_pemilik", "tipe", "persen_kepemilikan", "tanggal_update", "sumber"] if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)


# ==============================================================================
# HALAMAN: BERITA
# ==============================================================================
def _time_ago(published: str) -> str:
    if not published:
        return ""
    try:
        dt = pd.to_datetime(published, utc=True, errors="coerce")
        if pd.isna(dt):
            return published
        delta = pd.Timestamp.utcnow() - dt
        h = int(delta.total_seconds() // 3600)
        if h < 1:
            return "baru saja"
        if h < 24:
            return f"{h} jam lalu"
        return f"{h // 24} hari lalu"
    except Exception:
        return published


def page_news(ticker):
    st.markdown('<p class="page-title">Portal Berita Emiten</p>', unsafe_allow_html=True)
    kode = ticker.replace(".JK", "")
    news = fetch_news(kode)
    if not news:
        st.markdown('<div class="glass"><span class="muted">Tidak ada berita ditemukan '
                    '(butuh koneksi internet).</span></div>', unsafe_allow_html=True)
        return
    score, label = news_score(news)
    pos = sum(1 for n in news if n.get("skor", 0) > 0)
    neg = sum(1 for n in news if n.get("skor", 0) < 0)
    cls = "up" if score > 0.1 else ("down" if score < -0.1 else "muted")

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(kpi_card("Sentimen Agregat", f"{score:+.2f}",
                             f'<span class="{cls}">{label}</span>', accent=True), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Ringkasan", f"{len(news)} berita",
                             f'<span class="up">▲ {pos} positif</span> &nbsp; '
                             f'<span class="down">▼ {neg} negatif</span> &nbsp; '
                             f'<span class="muted">● {len(news)-pos-neg} netral</span>'),
                    unsafe_allow_html=True)
    st.write("")

    for n in news:
        sc = n.get("skor", 0)
        if sc > 0:
            chip = '<span class="chip chip-up">Positif</span>'
        elif sc < 0:
            chip = '<span class="chip chip-down">Negatif</span>'
        else:
            chip = '<span class="chip chip-neut">Netral</span>'
        meta = " · ".join(x for x in [n.get("sumber", ""), _time_ago(n.get("tanggal", ""))] if x)
        st.markdown(
            f'<a class="news-card" href="{n["link"]}" target="_blank">'
            f'<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start">'
            f'<span class="news-title">{n["judul"]}</span>{chip}</div>'
            f'<div class="news-meta">{meta}</div></a>', unsafe_allow_html=True)


# ==============================================================================
# HALAMAN: PORTOFOLIO
# ==============================================================================
def page_portfolio(sb, username, ticker):
    st.markdown('<p class="page-title">Portofolio Saya</p>', unsafe_allow_html=True)
    if sb is None:
        st.markdown('<div class="glass"><span class="muted">Supabase tidak terhubung. '
                    'Portofolio butuh database & akun (nonaktif di Mode Tamu).</span></div>',
                    unsafe_allow_html=True)
        return

    with st.expander("➕ Tambah / Perbarui Holding"):
        kode = st.text_input("Kode Saham", value=ticker.replace(".JK", ""))
        harga = st.number_input("Harga Rata-rata (Rp)", min_value=0.0, step=50.0)
        lot = st.number_input("Jumlah Lot", min_value=0, step=1)
        if st.button("Simpan", type="primary"):
            try:
                sb.table("portfolios").insert({
                    "username": username, "kode_saham": kode.strip().upper(),
                    "harga_rata2": harga, "jumlah_lot": int(lot)}).execute()
                st.success("Tersimpan.")
                st.rerun()
            except Exception as exc:
                st.error(f"Gagal menyimpan: {exc}")

    try:
        rows = sb.table("portfolios").select("*").eq("username", username).execute().data or []
    except Exception as exc:
        st.error(f"Gagal memuat portofolio: {exc}")
        return
    if not rows:
        st.info("Portofolio masih kosong.")
        return

    out, total_modal, total_kini = [], 0, 0
    for r in rows:
        t = to_jk(r["kode_saham"])
        price = get_info(t).get("currentPrice")
        lot = r["jumlah_lot"]
        avg = float(r["harga_rata2"])
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
    c1.markdown(kpi_card("Total Modal", fmt_rp(total_modal)), unsafe_allow_html=True)
    c2.markdown(kpi_card("Nilai Sekarang", fmt_rp(total_kini), accent=True), unsafe_allow_html=True)
    pcls = "up" if total_pl >= 0 else "down"
    pct = (total_pl / total_modal * 100) if total_modal else 0
    c3.markdown(kpi_card("Total P/L", fmt_rp(total_pl),
                         f'<span class="{pcls}">{pct:+.2f}%</span>'), unsafe_allow_html=True)
    st.write("")
    st.dataframe(pd.DataFrame(out), use_container_width=True, hide_index=True)


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    sb = get_supabase()
    if not disclaimer_gate():
        st.stop()
    auth_ok, username, name = auth_gate(sb)
    if not auth_ok:
        st.stop()

    with st.sidebar:
        render_brand()
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
            "👑 Konglo Tracker", "📰 Berita", "💼 Portofolio"],
            label_visibility="collapsed")
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
