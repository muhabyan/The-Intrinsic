"""
================================================================================
THE INTRINSIC — Stock Research & Portfolio Management
Streamlit + Google Sheets | tema dwi-mode (Dark/Light) + dwi-bahasa (ID/EN)
================================================================================

Arsitektur (modular):
    - i18n        : kamus TEXT + helper L()                (bahasa ID/EN)
    - theming     : inject_css(theme)                       (Dark/Light)
    - data store  : Google Sheets via st-gsheets-connection (Users, Portfolios)
    - market data : yfinance (harga, fundamental)
    - news        : feedparser (RSS CNBC Indonesia / Yahoo Finance)
    - engine      : indikator teknikal kaya, beda per gaya investasi
    - pages       : Dashboard, Engine, Fundamental, Konglo & Bandar Radar,
                    Berita, Portofolio

Instalasi:
    pip install -r requirements.txt
Menjalankan:
    streamlit run app.py

KREDENSIAL: tidak ada file credentials.json di repo. Semua kredensial dibaca
dari st.secrets (lihat format TOML di bawah/di README). Mode Tamu tetap jalan
tanpa konfigurasi apa pun.
================================================================================
"""

import os
import re
import html
import hmac
import hashlib
import urllib.parse
from datetime import datetime, time as dtime

import numpy as np
import pandas as pd
import streamlit as st

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
    from streamlit_gsheets import GSheetsConnection
except BaseException:
    # Tangkap apa pun (ImportError, PanicException dari binding cryptography yang
    # rusak, dll.) agar app tetap jalan di Mode Tamu meski konektor Sheets
    # bermasalah di suatu environment. PanicException turunan BaseException,
    # bukan Exception, jadi 'except Exception' saja tidak cukup.
    GSheetsConnection = None
try:
    import requests
except ImportError:
    requests = None

LOT_SIZE = 100

st.set_page_config(page_title="The Intrinsic", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

# ==============================================================================
# 1) i18n — KAMUS BAHASA
# ==============================================================================
TEXT = {
    "id": {
        "app_sub": "Equity Research Platform",
        "settings": "Pengaturan", "language": "Bahasa", "dark_mode": "Mode Gelap",
        "guest_badge": "Tamu · mode demo", "logout": "Keluar",
        "guest_info": "**Mode Tamu** — jelajahi aplikasi tanpa akun. Portofolio butuh "
                      "Google Sheets dan akan nonaktif sampai dikonfigurasi.",
        "login_as_guest": "👤 Masuk sebagai Tamu",
        "tab_login": "🔑 Masuk", "tab_register": "📝 Daftar",
        "username": "Username", "full_name": "Nama Lengkap", "email": "Email",
        "password": "Password", "btn_login": "Masuk", "btn_register": "Daftar",
        "login_prompt": "Masukkan username & password Anda.",
        "login_bad": "Username atau password salah.",
        "register_ok": "Registrasi berhasil! Silakan masuk.",
        "register_incomplete": "Lengkapi username, nama, dan password.",
        "register_dup": "Username sudah dipakai.",
        "db_off": "Database (Google Sheets) belum dikonfigurasi — gunakan Mode Tamu.",
        "disclaimer_title": "⚠️ Disclaimer & Ketentuan Penggunaan",
        "agree": "✅ Saya Setuju", "must_agree": "Anda harus menyetujui untuk melanjutkan.",
        "nav_dashboard": "📊 Dashboard", "nav_engine": "⚙️ The Engine",
        "nav_fundamental": "🔍 Fundamental", "nav_radar": "🛰️ Konglo & Bandar Radar",
        "nav_news": "📰 Berita", "nav_portfolio": "💼 Portofolio",
        "stock_code": "Kode Saham", "jk_hint": "Tanpa `.JK` — otomatis ditambahkan.",
        "not_advice": "⚠️ Bukan nasihat investasi.",
        "open": "Buka", "closed": "Tutup",
        "weekend": "Akhir pekan", "holiday": "Hari libur bursa",
        "sesi1": "Sesi I berlangsung", "sesi2": "Sesi II berlangsung",
        "rest": "Istirahat sesi", "offhours": "Di luar jam bursa",
        "dash_title": "Dashboard", "market_status": "Status Bursa (IHSG)",
        "ihsg_chart": "IHSG — Candlestick & Volume", "hour": "Jam (WIB)",
        "status_lbl": "Status Bursa", "hi6m": "Tertinggi 1 Thn",
        "no_chart": "Grafik tidak tersedia (butuh koneksi internet untuk yfinance).",
        "engine_title": "The Engine — Rekomendasi Objektif", "style": "Gaya Investasi",
        "long": "Jangka Panjang", "short": "Jangka Pendek", "combo": "Kombinasi",
        "analyzing": "Menganalisis", "profile": "profil", "indicators": "indikator",
        "calculating": "Menghitung sinyal…", "composite": "Skor Komposit",
        "comp_hint": "−1 bearish · +1 bullish", "components": "Komponen",
        "technical": "Teknikal", "broksum": "Broksum", "news_c": "Berita",
        "signal_detail": "Rincian Sinyal Teknikal", "price_ind": "Grafik Harga & Indikator",
        "engine_disclaimer": "Kondisi & rekomendasi = hasil pengolahan data objektif untuk "
                             "edukasi — bukan ajakan jual/beli, bukan nasihat berlisensi.",
        "fund_title": "Analisis Fundamental", "no_fund": "Data fundamental tidak tersedia.",
        "key_ratios": "Rasio Kunci", "eps": "EPS (TTM)", "eps_sub": "laba per saham",
        "range52": "Posisi Harga · Rentang 52 Minggu", "in_range": "Berada di",
        "of_range": "rentang 52 minggu", "rev_income": "Pendapatan & Laba Bersih (Tahunan)",
        "revenue": "Pendapatan", "net_income": "Laba Bersih",
        "fund_source": "Sumber: yfinance. Data dapat tertunda — verifikasi ke laporan resmi.",
        "radar_title": "Konglo & Bandar Radar", "radar_caption":
            "Deteksi indikasi akumulasi/distribusi (bandarmology) via VWAP, OBV & A/D line.",
        "radar_placeholder": "Data placeholder — mesin VWAP & KSEI belum diimplementasikan.",
        "radar_watchlist": "Watchlist (pisahkan dengan koma)",
        "radar_scanning": "Memindai bandarmology…",
        "radar_detail": "Detail VWAP & Volume",
        "radar_no_data": "Data tidak tersedia (butuh koneksi internet).",
        "radar_note": "Analisis VWAP/OBV/Akumulasi-Distribusi dihitung dari OHLCV publik "
                      "(yfinance). Data broker per-emiten & kepemilikan KSEI butuh sumber khusus.",
        "radar_tab_bandar": "🏦 Bandar (Broker)", "radar_tab_konglo": "👑 Konglomerat",
        "radar_tab_corp": "📋 Aksi Korporasi", "radar_tab_signal": "📡 Sinyal VWAP",
        "radar_buyers": "Broker Net Beli", "radar_sellers": "Broker Net Jual",
        "radar_source": "Sumber", "radar_konglo_pick": "Pilih konglomerat",
        "radar_portfolio": "Portofolio di IHSG", "radar_activity": "Aktivitas",
        "radar_corp_yf": "Dividen & Stock Split (yfinance)",
        "radar_corp_table": "Aksi Korporasi (right issue / akuisisi / backdoor)",
        "radar_demo_note": "Menampilkan data DEMO — isi worksheet Google Sheets "
                           "(BrokerSummary, KongloHoldings, CorpActions) atau jalankan broksum API untuk data nyata.",
        "val_under": "Undervalued", "val_over": "Overvalued", "val_fair": "Wajar (Fair)",
        "val_basis": "Dasar", "val_nodata": "data rasio tidak cukup", "val_weird": "data tidak wajar",
        "news_related": "Terkait",
        "news_all": "🌐 Semua Sumber",
        "news_title": "Portal Berita", "news_source": "Sumber Berita",
        "sentiment_agg": "Sentimen Agregat", "summary": "Ringkasan",
        "positive": "positif", "negative": "negatif", "neutral": "netral",
        "no_news": "Tidak ada berita ditemukan (butuh koneksi internet).",
        "port_title": "Portofolio Saya", "add_holding": "➕ Tambah / Perbarui Holding",
        "avg_price": "Harga Rata-rata (Rp)", "lots": "Jumlah Lot", "save": "Simpan",
        "saved": "Tersimpan.", "empty_port": "Portofolio masih kosong.",
        "total_modal": "Total Modal", "value_now": "Nilai Sekarang", "total_pl": "Total P/L",
        "port_off": "Portofolio butuh Google Sheets & akun (nonaktif di Mode Tamu).",
    },
    "en": {
        "app_sub": "Equity Research Platform",
        "settings": "Settings", "language": "Language", "dark_mode": "Dark Mode",
        "guest_badge": "Guest · demo mode", "logout": "Log out",
        "guest_info": "**Guest mode** — explore the app without an account. Portfolio "
                      "requires Google Sheets and stays disabled until configured.",
        "login_as_guest": "👤 Continue as Guest",
        "tab_login": "🔑 Sign in", "tab_register": "📝 Sign up",
        "username": "Username", "full_name": "Full Name", "email": "Email",
        "password": "Password", "btn_login": "Sign in", "btn_register": "Sign up",
        "login_prompt": "Enter your username & password.",
        "login_bad": "Wrong username or password.",
        "register_ok": "Registration successful! Please sign in.",
        "register_incomplete": "Fill username, name, and password.",
        "register_dup": "Username already taken.",
        "db_off": "Database (Google Sheets) not configured — use Guest mode.",
        "disclaimer_title": "⚠️ Disclaimer & Terms of Use",
        "agree": "✅ I Agree", "must_agree": "You must agree to continue.",
        "nav_dashboard": "📊 Dashboard", "nav_engine": "⚙️ The Engine",
        "nav_fundamental": "🔍 Fundamental", "nav_radar": "🛰️ Konglo & Bandar Radar",
        "nav_news": "📰 News", "nav_portfolio": "💼 Portfolio",
        "stock_code": "Stock Code", "jk_hint": "No `.JK` needed — added automatically.",
        "not_advice": "⚠️ Not investment advice.",
        "open": "Open", "closed": "Closed",
        "weekend": "Weekend", "holiday": "Exchange holiday",
        "sesi1": "Session I in progress", "sesi2": "Session II in progress",
        "rest": "Session break", "offhours": "Outside trading hours",
        "dash_title": "Dashboard", "market_status": "Market Status (IHSG)",
        "ihsg_chart": "IHSG — Candlestick & Volume", "hour": "Time (WIB)",
        "status_lbl": "Market", "hi6m": "1-Year High",
        "no_chart": "Chart unavailable (needs internet for yfinance).",
        "engine_title": "The Engine — Objective Read", "style": "Investing Style",
        "long": "Long Term", "short": "Short Term", "combo": "Combined",
        "analyzing": "Analyzing", "profile": "profile", "indicators": "indicators",
        "calculating": "Computing signals…", "composite": "Composite Score",
        "comp_hint": "−1 bearish · +1 bullish", "components": "Components",
        "technical": "Technical", "broksum": "Broker Sum", "news_c": "News",
        "signal_detail": "Technical Signal Breakdown", "price_ind": "Price & Indicators",
        "engine_disclaimer": "Conditions & reads are objective data processing for "
                             "education — not buy/sell solicitation, not licensed advice.",
        "fund_title": "Fundamental Analysis", "no_fund": "Fundamental data unavailable.",
        "key_ratios": "Key Ratios", "eps": "EPS (TTM)", "eps_sub": "earnings per share",
        "range52": "Price Position · 52-Week Range", "in_range": "At",
        "of_range": "of the 52-week range", "rev_income": "Revenue & Net Income (Annual)",
        "revenue": "Revenue", "net_income": "Net Income",
        "fund_source": "Source: yfinance. Data may be delayed — verify with official filings.",
        "radar_title": "Konglo & Bandar Radar", "radar_caption":
            "Accumulation/distribution detection (bandarmology) via VWAP, OBV & A/D line.",
        "radar_placeholder": "Placeholder data — VWAP & KSEI engine not yet implemented.",
        "radar_watchlist": "Watchlist (comma-separated)",
        "radar_scanning": "Scanning bandarmology…",
        "radar_detail": "VWAP & Volume Detail",
        "radar_no_data": "Data unavailable (needs internet).",
        "radar_note": "VWAP/OBV/Accumulation-Distribution computed from public OHLCV "
                      "(yfinance). Per-broker & KSEI ownership data need dedicated sources.",
        "radar_tab_bandar": "🏦 Bandar (Brokers)", "radar_tab_konglo": "👑 Conglomerates",
        "radar_tab_corp": "📋 Corporate Actions", "radar_tab_signal": "📡 VWAP Signal",
        "radar_buyers": "Net Buyers", "radar_sellers": "Net Sellers",
        "radar_source": "Source", "radar_konglo_pick": "Pick conglomerate",
        "radar_portfolio": "Holdings in IDX", "radar_activity": "Activity",
        "radar_corp_yf": "Dividends & Stock Splits (yfinance)",
        "radar_corp_table": "Corporate Actions (rights issue / acquisition / backdoor)",
        "radar_demo_note": "Showing DEMO data — fill Google Sheets worksheets "
                           "(BrokerSummary, KongloHoldings, CorpActions) or run the broksum API for live data.",
        "val_under": "Undervalued", "val_over": "Overvalued", "val_fair": "Fair",
        "val_basis": "Basis", "val_nodata": "insufficient ratio data", "val_weird": "implausible data",
        "news_related": "Related",
        "news_all": "🌐 All Sources",
        "news_title": "News Portal", "news_source": "News Source",
        "sentiment_agg": "Aggregate Sentiment", "summary": "Summary",
        "positive": "positive", "negative": "negative", "neutral": "neutral",
        "no_news": "No news found (needs internet).",
        "port_title": "My Portfolio", "add_holding": "➕ Add / Update Holding",
        "avg_price": "Average Price (Rp)", "lots": "Lots", "save": "Save",
        "saved": "Saved.", "empty_port": "Portfolio is empty.",
        "total_modal": "Total Cost", "value_now": "Current Value", "total_pl": "Total P/L",
        "port_off": "Portfolio requires Google Sheets & an account (off in Guest mode).",
    },
}


def L(key: str) -> str:
    lang = st.session_state.get("lang", "id")
    return TEXT.get(lang, TEXT["id"]).get(key, key)


# ==============================================================================
# 2) STATE & THEMING
# ==============================================================================
def init_state():
    st.session_state.setdefault("lang", "id")
    st.session_state.setdefault("theme", "dark")
    st.session_state.setdefault("agreed_disclaimer", False)
    st.session_state.setdefault("is_guest", False)
    st.session_state.setdefault("auth_user", None)
    st.session_state.setdefault("auth_name", None)


PALETTES = {
    "dark": {
        "app_bg": ("radial-gradient(900px 600px at 12% -8%, rgba(99,102,241,0.18), transparent 60%),"
                   "radial-gradient(800px 600px at 100% 0%, rgba(168,85,247,0.16), transparent 55%),"
                   "radial-gradient(700px 700px at 60% 120%, rgba(16,185,129,0.10), transparent 55%),"
                   "linear-gradient(180deg, #0b1020 0%, #0a0f1e 100%)"),
        "text": "#e5e7eb", "muted": "#8b93a7", "title": "#f8fafc",
        "card_bg": "linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
        "card_border": "rgba(255,255,255,0.08)", "sidebar": "linear-gradient(180deg, rgba(19,26,48,0.92), rgba(11,16,32,0.92))",
        "sidebar_border": "rgba(255,255,255,0.06)", "grid": "rgba(148,163,184,0.12)",
        "input_bg": "rgba(255,255,255,0.04)", "input_border": "rgba(255,255,255,0.1)",
        "plot_font": "#cbd5e1",
    },
    "light": {
        "app_bg": ("radial-gradient(900px 600px at 10% -10%, rgba(99,102,241,0.16), transparent 60%),"
                   "radial-gradient(800px 600px at 100% 0%, rgba(168,85,247,0.14), transparent 55%),"
                   "radial-gradient(700px 700px at 70% 120%, rgba(6,182,212,0.12), transparent 55%),"
                   "linear-gradient(180deg, #f7f8fc 0%, #eef1f8 100%)"),
        "text": "#0f172a", "muted": "#64748b", "title": "#0b1220",
        "card_bg": "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(255,255,255,0.65))",
        "card_border": "rgba(15,23,42,0.08)", "sidebar": "linear-gradient(180deg, rgba(255,255,255,0.92), rgba(241,245,252,0.92))",
        "sidebar_border": "rgba(15,23,42,0.08)", "grid": "rgba(15,23,42,0.08)",
        "input_bg": "rgba(15,23,42,0.03)", "input_border": "rgba(15,23,42,0.12)",
        "plot_font": "#475569",
    },
}
ACCENT_A, ACCENT_B = "#6366f1", "#a855f7"
UP, DOWN = "#10b981", "#ef4444"


def inject_css(theme: str):
    p = PALETTES.get(theme, PALETTES["dark"])
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
:root {{ --accent-a:{ACCENT_A}; --accent-b:{ACCENT_B}; --text:{p['text']}; --muted:{p['muted']};
        --card-bg:{p['card_bg']}; --card-border:{p['card_border']}; --grid:{p['grid']}; }}
html, body, [class*="css"] {{ font-family:'Plus Jakarta Sans', sans-serif; }}
.stApp {{ background:{p['app_bg']}; background-attachment:fixed; color:{p['text']}; }}
.stApp::before {{ content:""; position:fixed; inset:-20% -10% auto -10%; height:60vh; z-index:0;
    background: radial-gradient(closest-side, rgba(99,102,241,0.18), transparent);
    filter: blur(42px); animation: float1 16s ease-in-out infinite; pointer-events:none; }}
@keyframes float1 {{ 0%,100%{{transform:translate(0,0)}} 50%{{transform:translate(30px,40px)}} }}
section[data-testid="stSidebar"] {{ background:{p['sidebar']}; border-right:1px solid {p['sidebar_border']}; backdrop-filter: blur(8px); }}
.block-container {{ padding-top:2.0rem; }}
[data-testid="stMarkdownContainer"], .stMarkdown, p, li, label, span {{ color:{p['text']}; }}

.brand-wrap {{ display:flex; align-items:center; gap:12px; }}
.brand-mark {{ width:38px; height:38px; border-radius:11px; flex:0 0 auto;
    background:linear-gradient(135deg,var(--accent-a),var(--accent-b));
    box-shadow:0 8px 24px rgba(99,102,241,0.45); display:grid; place-items:center;
    animation: pop .6s cubic-bezier(.2,.8,.2,1) both; }}
.brand-mark svg {{ width:22px; height:22px; }}
.brand {{ font-size:1.5rem; font-weight:800; letter-spacing:-0.6px; line-height:1;
    background:linear-gradient(90deg,var(--accent-a),var(--accent-b));
    -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
.brand-xl {{ font-size:2.6rem; }}
.brand-sub {{ font-size:0.68rem; color:{p['muted']}; letter-spacing:3px; text-transform:uppercase; margin-top:4px; }}
@keyframes pop {{ from{{transform:scale(.6) rotate(-8deg); opacity:0}} to{{transform:none; opacity:1}} }}

.glass {{ background:{p['card_bg']}; border:1px solid {p['card_border']}; border-radius:18px;
    padding:18px 20px; box-shadow:0 10px 30px rgba(2,6,23,0.18); backdrop-filter: blur(10px);
    animation: rise .6s cubic-bezier(.2,.8,.2,1) both; }}
.glass:hover {{ border-color: rgba(99,102,241,0.45); transform: translateY(-3px);
    transition: all .25s ease; box-shadow:0 18px 40px rgba(99,102,241,0.18); }}
@keyframes rise {{ from{{opacity:0; transform:translateY(14px)}} to{{opacity:1; transform:none}} }}
.kpi-label {{ color:{p['muted']}; font-size:0.72rem; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; }}
.kpi-value {{ font-family:'JetBrains Mono',monospace; font-size:1.9rem; font-weight:700; color:{p['title']}; margin-top:6px; }}
.kpi-sub {{ font-size:0.82rem; margin-top:4px; }}
.up {{ color:#10b981!important; }} .down {{ color:#ef4444!important; }} .muted{{ color:{p['muted']}!important; }}
.section-h {{ font-size:1.05rem; font-weight:700; color:{p['text']}; margin:6px 0 10px; display:flex; align-items:center; gap:8px; }}
.section-h::before {{ content:""; width:4px; height:18px; border-radius:6px; background:linear-gradient(180deg,var(--accent-a),var(--accent-b)); }}
.page-title {{ font-size:1.9rem; font-weight:800; color:{p['title']}; letter-spacing:-0.5px; animation: rise .5s ease both; }}
.badge {{ display:inline-block; padding:10px 26px; border-radius:12px; font-weight:800; font-size:1.15rem; animation: pop .5s ease both; }}
.bull {{ background:rgba(16,185,129,0.16); color:#10b981; border:1px solid rgba(16,185,129,0.4); }}
.bear {{ background:rgba(239,68,68,0.16); color:#ef4444; border:1px solid rgba(239,68,68,0.4); }}
.neut {{ background:rgba(234,179,8,0.16); color:#d97706; border:1px solid rgba(234,179,8,0.35); }}
.pill {{ display:inline-block; padding:4px 14px; border-radius:999px; font-size:0.76rem; font-weight:700; }}
.pill-open {{ background:rgba(16,185,129,0.18); color:#10b981; }}
.pill-closed {{ background:rgba(148,163,184,0.18); color:{p['muted']}; }}
.dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; vertical-align:middle; }}
.dot-open {{ background:#10b981; animation: ping 1.6s infinite; }}
.dot-closed {{ background:#94a3b8; }}
@keyframes ping {{ 0%{{box-shadow:0 0 0 0 rgba(16,185,129,0.6)}} 70%{{box-shadow:0 0 0 10px rgba(16,185,129,0)}} 100%{{box-shadow:0 0 0 0 rgba(16,185,129,0)}} }}
.chip {{ display:inline-block; padding:3px 11px; border-radius:8px; font-size:0.74rem; font-weight:700; }}
.chip-up {{ background:rgba(16,185,129,0.16); color:#10b981; }}
.chip-down {{ background:rgba(239,68,68,0.16); color:#ef4444; }}
.chip-neut {{ background:rgba(148,163,184,0.18); color:{p['muted']}; }}
.sig-row {{ display:flex; align-items:center; justify-content:space-between; padding:10px 14px; border-radius:12px;
    margin-bottom:8px; background:{p['card_bg']}; border:1px solid {p['card_border']}; animation: rise .5s ease both; }}
.sig-name {{ font-weight:600; color:{p['text']}; }}
.sig-val {{ font-family:'JetBrains Mono',monospace; color:{p['muted']}; font-size:0.85rem; }}
.news-card {{ display:block; text-decoration:none; padding:16px 18px; border-radius:16px; margin-bottom:12px;
    background:{p['card_bg']}; border:1px solid {p['card_border']}; transition: all .2s ease; animation: rise .5s ease both; }}
.news-card:hover {{ border-color:rgba(99,102,241,0.5); transform:translateX(4px); }}
.news-title {{ color:{p['title']}; font-weight:700; font-size:1rem; line-height:1.35; }}
.news-sum {{ color:{p['text']}; opacity:0.82; font-size:0.86rem; line-height:1.45; margin-top:8px;
    display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }}
.news-meta {{ color:{p['muted']}; font-size:0.76rem; margin-top:8px; }}
.disclaimer-card {{ background:{p['card_bg']}; border:1px solid {p['card_border']}; border-radius:22px;
    padding:30px 40px; box-shadow:0 24px 60px rgba(2,6,23,0.35); max-width:820px; margin:auto; backdrop-filter:blur(12px); }}
.hero {{ text-align:center; padding:22px 0 8px; animation: rise .6s ease both; }}
.stTextInput input, .stNumberInput input {{ background:{p['input_bg']}!important; border:1px solid {p['input_border']}!important;
    color:{p['text']}!important; border-radius:10px!important; }}
div[role="radiogroup"] label {{ padding:6px 10px; border-radius:10px; transition:all .15s ease; }}
div[role="radiogroup"] label:hover {{ background:rgba(99,102,241,0.12); }}
.stButton>button {{ border-radius:12px; font-weight:700; border:1px solid {p['card_border']}; transition: all .2s ease; color:{p['text']}; }}
.stButton>button[kind="primary"] {{ background:linear-gradient(135deg,var(--accent-a),var(--accent-b)); border:none; color:#fff;
    box-shadow:0 10px 26px rgba(99,102,241,0.4); }}
.stButton>button[kind="primary"]:hover {{ transform:translateY(-2px); box-shadow:0 14px 34px rgba(99,102,241,0.55); }}
div[data-testid="stMetricValue"] {{ color:{p['title']}; font-family:'JetBrains Mono',monospace; }}
div[data-testid="stMetricLabel"] {{ color:{p['muted']}; }}
/* Sembunyikan footer/menu/Deploy TAPI JANGAN sentuh header agar kontrol
   buka-sidebar (panah) tetap muncul. Toolbar tidak di-display:none supaya
   tombol expand yang berada di area itu tidak ikut hilang. */
#MainMenu, footer {{ visibility:hidden; }}
[data-testid="stDecoration"] {{ display:none; }}
[data-testid="stToolbarActions"] {{ visibility:hidden; }}   /* sembunyikan tombol Deploy saja */
header[data-testid="stHeader"] {{ background:transparent; box-shadow:none; }}
/* Paksa kontrol buka-sidebar selalu terlihat & jelas (lintas versi Streamlit) */
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"], [data-testid="stExpandSidebarButton"] {{
    visibility:visible !important; opacity:1 !important; display:flex !important;
    z-index:1000000 !important; }}
[data-testid="stSidebarCollapsedControl"] button, [data-testid="collapsedControl"] button {{
    background:linear-gradient(135deg,var(--accent-a),var(--accent-b)) !important;
    border-radius:10px !important; box-shadow:0 6px 18px rgba(99,102,241,0.5) !important; }}
[data-testid="stSidebarCollapsedControl"] svg, [data-testid="collapsedControl"] svg,
[data-testid="stSidebarCollapseButton"] svg {{ color:#fff !important; fill:#fff !important; }}
</style>
""", unsafe_allow_html=True)


_MARK_SVG = ('<svg viewBox="0 0 24 24" fill="none"><path d="M3 16.5L8.5 11L12 14L21 5" '
             'stroke="white" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
             '<circle cx="21" cy="5" r="2" fill="white"/></svg>')


def render_brand(big=False, sub=True):
    cls = "brand brand-xl" if big else "brand"
    html = (f'<div class="brand-wrap"><div class="brand-mark">{_MARK_SVG}</div>'
            f'<div><div class="{cls}">The Intrinsic</div>')
    if sub:
        html += f'<div class="brand-sub">{L("app_sub")}</div>'
    html += '</div></div>'
    st.markdown(html, unsafe_allow_html=True)


# ==============================================================================
# 3) DATA STORE — GOOGLE SHEETS (st-gsheets-connection)
# ==============================================================================
USERS_WS = "Users"
PORTF_WS = "Portfolios"


@st.cache_resource(show_spinner=False)
def get_conn():
    """Koneksi Google Sheets dari st.secrets. None bila belum dikonfigurasi."""
    if GSheetsConnection is None:
        return None
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception:
        return None


def _read_ws(conn, worksheet, ttl=5) -> pd.DataFrame:
    try:
        df = conn.read(worksheet=worksheet, ttl=ttl)
        if df is None:
            return pd.DataFrame()
        return df.dropna(how="all")
    except Exception:
        return pd.DataFrame()


def _write_ws(conn, worksheet, df) -> bool:
    try:
        conn.update(worksheet=worksheet, data=df)
        return True
    except Exception as exc:
        st.error(f"Gagal menulis ke Google Sheets: {exc}")
        return False


# --- Password hashing (stdlib pbkdf2, tanpa dependensi tambahan) ---
def hash_pw(pw: str, salt: str = None) -> str:
    salt = salt or os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"{salt}${h}"


def verify_pw(pw: str, stored: str) -> bool:
    try:
        salt, h = str(stored).split("$", 1)
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()
        return hmac.compare_digest(calc, h)
    except Exception:
        return False


def register_user(conn, username, name, email, pw) -> tuple:
    df = _read_ws(conn, USERS_WS, ttl=0)
    if not df.empty and "username" in df and (df["username"].astype(str) == username).any():
        return False, L("register_dup")
    row = {"username": username, "name": name, "email": email,
           "password_hash": hash_pw(pw), "created_at": datetime.utcnow().isoformat()}
    new = pd.concat([df, pd.DataFrame([row])], ignore_index=True) if not df.empty else pd.DataFrame([row])
    return (True, L("register_ok")) if _write_ws(conn, USERS_WS, new) else (False, "Gagal menyimpan.")


def login_user(conn, username, pw) -> tuple:
    df = _read_ws(conn, USERS_WS, ttl=0)
    if df.empty or "username" not in df:
        return None
    hit = df[df["username"].astype(str) == username]
    if hit.empty:
        return None
    r = hit.iloc[0]
    if verify_pw(pw, r.get("password_hash", "")):
        return username, str(r.get("name", username))
    return None


# ==============================================================================
# 4) MARKET DATA (yfinance)
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
    if yf is None:
        return {}
    out = {}
    try:
        t = yf.Ticker(ticker)
        try:
            out["income"] = t.income_stmt
        except Exception:
            out["income"] = None
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
    """Return (state 'Open'/'Closed', note_key, now)."""
    now = _now_wib()
    if now.weekday() >= 5:
        return "Closed", "weekend", now
    if now.date().isoformat() in IDX_HOLIDAYS_2026:
        return "Closed", "holiday", now
    t = now.time()
    if now.weekday() == 4:
        s1 = dtime(9, 0) <= t <= dtime(11, 30)
        s2 = dtime(14, 0) <= t <= dtime(15, 49)
    else:
        s1 = dtime(9, 0) <= t <= dtime(12, 0)
        s2 = dtime(13, 30) <= t <= dtime(15, 49)
    if s1:
        return "Open", "sesi1", now
    if s2:
        return "Open", "sesi2", now
    if dtime(12, 0) < t < dtime(13, 30):
        return "Closed", "rest", now
    return "Closed", "offhours", now


# ==============================================================================
# PLOTLY — styling konsisten (theme-aware)
# ==============================================================================
def _style_fig(fig, height=320, legend=True):
    p = PALETTES.get(st.session_state.get("theme", "dark"))
    fig.update_layout(
        height=height, margin=dict(l=6, r=6, t=24, b=6),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", color=p["plot_font"], size=12),
        hoverlabel=dict(font_size=12), showlegend=legend,
        legend=dict(orientation="h", y=1.14, x=0, bgcolor="rgba(0,0,0,0)"))
    fig.update_xaxes(gridcolor=p["grid"], zeroline=False, showline=False)
    fig.update_yaxes(gridcolor=p["grid"], zeroline=False, showline=False)
    return fig


def _plot(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})


# ==============================================================================
# 5) MESIN INDIKATOR TEKNIKAL (kaya; beda per gaya)
# ==============================================================================
def _rsi(series, period):
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


def compute_indicators(hist):
    if hist is None or hist.empty:
        return pd.DataFrame()
    df = hist.copy()
    c, h, l = df["Close"], df["High"], df["Low"]
    v = df["Volume"] if "Volume" in df else None
    df["EMA9"] = c.ewm(span=9, adjust=False).mean()
    df["EMA21"] = c.ewm(span=21, adjust=False).mean()
    df["SMA20"] = c.rolling(20).mean()
    df["SMA50"] = c.rolling(50).mean()
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
    df["BB_UP"], df["BB_LO"] = m + 2 * s, m - 2 * s
    ll, hh = l.rolling(14).min(), h.rolling(14).max()
    df["STOCH_K"] = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
    df["STOCH_D"] = df["STOCH_K"].rolling(3).mean()
    df["ADX"], df["PDI"], df["NDI"] = _adx(h, l, c, 14)
    df["ROC"] = c.pct_change(12) * 100
    df["HI52"] = c.rolling(252, min_periods=20).max()
    df["LO52"] = c.rolling(252, min_periods=20).min()
    return df


def _zone(v, low, high):
    if pd.isna(v):
        return 0
    return 1 if v < low else (-1 if v > high else 0)


def _short_signals(last):
    sig, det = {}, []
    sig["ema_fast"] = 1 if (pd.notna(last["EMA9"]) and last["EMA9"] > last["EMA21"]) else -1
    det.append(("EMA9 vs EMA21", f"{last['EMA9']:.0f} / {last['EMA21']:.0f}", sig["ema_fast"]))
    sig["rsi7"] = _zone(last["RSI7"], 30, 70)
    det.append(("RSI(7)", f"{last['RSI7']:.0f}" if pd.notna(last['RSI7']) else "—", sig["rsi7"]))
    k, d = last["STOCH_K"], last["STOCH_D"]
    sig["stoch"] = 0 if pd.isna(k) else (1 if k < 20 else (-1 if k > 80 else (1 if (pd.notna(d) and k > d) else -1)))
    det.append(("Stochastic %K/%D", f"{k:.0f}/{d:.0f}" if pd.notna(k) else "—", sig["stoch"]))
    sig["macd_h"] = 1 if (pd.notna(last["MACD_HIST"]) and last["MACD_HIST"] > 0) else -1
    det.append(("MACD momentum", f"{last['MACD_HIST']:+.2f}" if pd.notna(last['MACD_HIST']) else "—", sig["macd_h"]))
    sig["roc"] = 1 if (pd.notna(last["ROC"]) and last["ROC"] > 0) else -1
    det.append(("ROC(12)", f"{last['ROC']:+.1f}%" if pd.notna(last['ROC']) else "—", sig["roc"]))
    w = {"ema_fast": 0.25, "stoch": 0.20, "rsi7": 0.20, "macd_h": 0.20, "roc": 0.15}
    return float(np.clip(sum(sig[k] * w[k] for k in w), -1, 1)), det


def _long_signals(last):
    sig, det = {}, []
    sig["t200"] = 1 if (pd.notna(last["SMA200"]) and last["Close"] > last["SMA200"]) else -1
    det.append(("Price vs SMA200", "above" if sig["t200"] > 0 else "below", sig["t200"]))
    sig["gcross"] = 1 if (pd.notna(last["SMA50"]) and pd.notna(last["SMA200"]) and last["SMA50"] > last["SMA200"]) else -1
    det.append(("Golden/Death Cross", "golden" if sig["gcross"] > 0 else "death", sig["gcross"]))
    adx, pdi, ndi = last["ADX"], last["PDI"], last["NDI"]
    if pd.isna(adx) or adx <= 20:
        sig["adx"], note = 0, (f"weak (ADX {adx:.0f})" if pd.notna(adx) else "—")
    else:
        sig["adx"] = 1 if pdi > ndi else -1
        note = f"strong {'up' if pdi > ndi else 'down'} (ADX {adx:.0f})"
    det.append(("ADX / DI", note, sig["adx"]))
    sig["rsi14"] = _zone(last["RSI14"], 30, 70)
    det.append(("RSI(14)", f"{last['RSI14']:.0f}" if pd.notna(last['RSI14']) else "—", sig["rsi14"]))
    if pd.notna(last["HI52"]) and pd.notna(last["LO52"]) and last["HI52"] > last["LO52"]:
        pos = (last["Close"] - last["LO52"]) / (last["HI52"] - last["LO52"])
        sig["pos52"] = 1 if pos > 0.7 else (-1 if pos < 0.3 else 0)
        det.append(("52-week position", f"{pos * 100:.0f}%", sig["pos52"]))
    else:
        sig["pos52"] = 0
        det.append(("52-week position", "—", 0))
    sig["macd"] = 1 if (pd.notna(last["MACD"]) and last["MACD"] > last["MACD_SIG"]) else -1
    det.append(("MACD vs Signal", "bullish" if sig["macd"] > 0 else "bearish", sig["macd"]))
    w = {"t200": 0.30, "gcross": 0.20, "adx": 0.20, "rsi14": 0.10, "pos52": 0.10, "macd": 0.10}
    return float(np.clip(sum(sig[k] * w[k] for k in w), -1, 1)), det


def technical_score(df, style):
    if df is None or df.empty or len(df) < 30:
        return 0.0, [("Insufficient history", "—", 0)]
    last = df.iloc[-1]
    s_sc, s_det = _short_signals(last)
    l_sc, l_det = _long_signals(last)
    if style == L("short"):
        return s_sc, s_det
    if style == L("long"):
        return l_sc, l_det
    return float(np.clip(0.5 * s_sc + 0.5 * l_sc, -1, 1)), (l_det + s_det)


# ==============================================================================
# BROKSUM (opsional via FastAPI; else netral)
# ==============================================================================
def broksum_score(kode: str):
    try:
        api_url = st.secrets["broksum"]["api_url"].rstrip("/")
    except Exception:
        api_url = ""
    if api_url and requests is not None:
        try:
            resp = requests.get(f"{api_url}/broksum/{kode}/score", timeout=8)
            if resp.ok:
                d = resp.json()
                return float(d["score"]), str(d["label"]), int(d["total_net"])
        except Exception:
            pass
    return 0.0, "n/a", 0


# ==============================================================================
# 6) BERITA REAL-TIME (feedparser RSS)
# ==============================================================================
NEWS_FEEDS = {
    "CNBC Indonesia": "https://www.cnbcindonesia.com/market/rss",
    "Detik Finance": "https://finance.detik.com/rss",
    "Kontan": "https://www.kontan.co.id/rss",
    "Bisnis.com": "https://www.bisnis.com/rss",
    "Investing.com": "https://www.investing.com/rss/news.rss",
    "Antara Ekonomi": "https://www.antaranews.com/rss/ekonomi",
    "Bloomberg (Google News)": "https://news.google.com/rss/search?q=site:bloomberg.com+markets&hl=en-US&gl=US&ceid=US:en",
    "Yahoo Finance (IHSG)": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EJKSE&region=US&lang=en-US",
}
POS_WORDS = {"laba", "naik", "untung", "ekspansi", "akuisisi", "dividen", "rekor", "tumbuh",
             "positif", "buyback", "kontrak", "melonjak", "cuan", "gain", "surge", "rally",
             "beat", "record", "profit", "growth", "up"}
NEG_WORDS = {"rugi", "turun", "anjlok", "gugatan", "default", "pailit", "phk", "negatif",
             "denda", "suspensi", "delisting", "merosot", "loss", "fall", "drop", "plunge",
             "cut", "down", "slump", "crash"}


# Peta kata kunci -> kode emiten untuk mendeteksi "keterkaitan" berita.
EMITEN_MAP = {
    "bca": "BBCA", "bank central asia": "BBCA", "bri": "BBRI", "bank rakyat": "BBRI",
    "mandiri": "BMRI", "bni": "BBNI", "telkom": "TLKM", "telkomsel": "TLKM",
    "astra": "ASII", "adaro": "ADRO", "alamtri": "ADRO", "antam": "ANTM", "aneka tambang": "ANTM",
    "gojek": "GOTO", "gotO": "GOTO", "tokopedia": "GOTO", "unilever": "UNVR",
    "indofood": "INDF", "icbp": "ICBP", "barito": "BRPT", "chandra asri": "TPIA",
    "barito renewables": "BREN", "merdeka": "MDKA", "amman": "AMMN", "bukalapak": "BUKA",
    "bumi resources": "BUMI", "pertamina geothermal": "PGEO", "semen indonesia": "SMGR",
    "kalbe": "KLBF", "gudang garam": "GGRM", "sampoerna": "HMSP", "bayan": "BYAN",
    "united tractors": "UNTR", "petrosea": "PTRO", "prajogo": "BREN", "djarum": "BBCA",
    "salim": "INDF", "pln": "PGEO", "garuda": "GIAA", "wijaya karya": "WIKA",
    "jasa marga": "JSMR", "vale": "INCO", "harum": "HRUM", "medco": "MEDC",
}


def news_relevance(text: str, skor: int) -> list:
    """Deteksi emiten terdampak + arah perkiraan (↑/↓/→) dari sentimen judul."""
    tl = text.lower()
    found = []
    seen = set()
    for kw, code in EMITEN_MAP.items():
        if kw in tl and code not in seen:
            seen.add(code)
            found.append(code)
    arrow = "↑" if skor > 0 else ("↓" if skor < 0 else "→")
    return [(code, arrow) for code in found[:4]]


def _clean_html(s: str, limit: int = 240) -> str:
    """Bersihkan tag HTML & entitas dari ringkasan RSS, lalu potong."""
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    # Buang ekor "View Full Coverage"/nama sumber yang sering muncul di Google News
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0] + "…"
    return s


@st.cache_data(ttl=900, show_spinner=False)
def fetch_feed(url: str, source_name: str = "") -> list:
    if feedparser is None:
        return []
    try:
        feed = feedparser.parse(url)
        out = []
        for e in feed.entries[:16]:
            title = e.get("title", "")
            tl = title.lower()
            sc = sum(1 for w in POS_WORDS if w in tl) - sum(1 for w in NEG_WORDS if w in tl)
            src = source_name or (title.rsplit(" - ", 1)[-1] if " - " in title else "")
            raw_sum = e.get("summary", "") or e.get("description", "")
            if not raw_sum and e.get("content"):
                try:
                    raw_sum = e["content"][0].get("value", "")
                except Exception:
                    raw_sum = ""
            summary = _clean_html(raw_sum)
            # Buang judul yang terduplikasi di awal ringkasan (sering di Google News)
            if summary and summary.lower().startswith(title.lower()[:30]):
                summary = summary[len(title):].strip(" -–—|") or summary
            out.append({"judul": title, "link": e.get("link", ""),
                        "tanggal": e.get("published", ""), "sumber": src,
                        "ringkas": summary, "skor": sc,
                        "terkait": news_relevance(f"{title} {summary}", sc)})
        return out
    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def fetch_all_feeds() -> list:
    """Gabungkan semua sumber, dedup judul, urutkan terbaru di atas."""
    seen, out = set(), []
    for name, url in NEWS_FEEDS.items():
        for n in fetch_feed(url, source_name=name):
            key = n["judul"].strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(n)

    def _ts(n):
        d = pd.to_datetime(n.get("tanggal", ""), utc=True, errors="coerce")
        return d.value if pd.notna(d) else -1
    out.sort(key=_ts, reverse=True)
    return out[:36]


@st.cache_data(ttl=900, show_spinner=False)
def fetch_news_emiten(kode_polos: str) -> list:
    q = urllib.parse.quote(f"{kode_polos} saham emiten")
    return fetch_feed(f"https://news.google.com/rss/search?q={q}&hl=id&gl=ID&ceid=ID:id")


def news_score(news: list):
    if not news:
        return 0.0, L("neutral")
    s = sum(n.get("skor", 0) for n in news)
    norm = float(np.clip(s / max(len(news), 1), -1, 1))
    label = L("positive") if norm > 0.1 else (L("negative") if norm < -0.1 else L("neutral"))
    return norm, label


# ==============================================================================
# REKOMENDASI GABUNGAN
# ==============================================================================
def recommendation_engine(ticker: str, style: str) -> dict:
    kode = ticker.replace(".JK", "")
    period = {L("long"): "2y", L("short"): "6mo"}.get(style, "1y")
    df = compute_indicators(get_history(ticker, period=period))
    tech, tech_det = technical_score(df, style)
    bk_score, bk_label, bk_net = broksum_score(kode)
    news = fetch_news_emiten(kode)
    nw_score, nw_label = news_score(news)
    composite = 0.55 * tech + 0.30 * bk_score + 0.15 * nw_score
    if composite >= 0.2:
        cond, cls = "BULLISH", "bull"
    elif composite <= -0.2:
        cond, cls = "BEARISH", "bear"
    else:
        cond, cls = "NEUTRAL", "neut"
    return {"composite": composite, "condition": cond, "cls": cls, "tech": tech, "tech_det": tech_det,
            "broksum": bk_label, "broksum_net": bk_net, "news_label": nw_label,
            "news_score": nw_score, "df": df, "style": style}


# ==============================================================================
# KOMPONEN UI
# ==============================================================================
def kpi_card(label, value, sub_html="", accent=False):
    border = "border-color:rgba(99,102,241,0.45);" if accent else ""
    return (f'<div class="glass" style="{border}"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div><div class="kpi-sub">{sub_html}</div></div>')


def signal_row(name, val, sig):
    chip = ('<span class="chip chip-up">Bullish</span>' if sig > 0 else
            '<span class="chip chip-down">Bearish</span>' if sig < 0 else
            '<span class="chip chip-neut">Neutral</span>')
    return (f'<div class="sig-row"><div><span class="sig-name">{name}</span><br>'
            f'<span class="sig-val">{val}</span></div>{chip}</div>')


# ==============================================================================
# GERBANG 1: DISCLAIMER
# ==============================================================================
def disclaimer_gate() -> bool:
    if st.session_state.get("agreed_disclaimer"):
        return True
    st.write("")
    render_brand(big=True)
    st.markdown(f"### {L('disclaimer_title')}")
    if st.session_state.get("lang") == "en":
        st.markdown("""
**The Intrinsic is not a licensed financial advisor.** All information, scores, and
"conditions" (Bullish/Bearish/Neutral) are **objective data processing** (technical,
broker summary, public news) for **education & self-research**.

- This is **not a solicitation** to buy/sell securities.
- Past performance **does not guarantee** future results.
- **Investment decisions are entirely your responsibility.** Consider consulting a
  licensed advisor (OJK).
- Data may be delayed, incomplete, or wrong.

By pressing **"I Agree"**, you accept these terms.
        """)
    else:
        st.markdown("""
**The Intrinsic bukan penasihat keuangan berlisensi.** Seluruh informasi, skor, dan "kondisi"
(Bullish/Bearish/Neutral) adalah **hasil pengolahan data objektif** (teknikal, broker summary,
berita publik) untuk **edukasi & riset mandiri**.

- Ini **bukan ajakan/solicitation** untuk membeli/menjual efek.
- Kinerja masa lalu **tidak menjamin** hasil di masa depan.
- **Keputusan investasi sepenuhnya tanggung jawab Anda.** Pertimbangkan konsultasi dengan
  penasihat berizin OJK.
- Data dapat tertunda, tidak lengkap, atau keliru.

Dengan menekan **"Saya Setuju"**, Anda menerima ketentuan ini.
        """)
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button(L("agree"), type="primary", use_container_width=True):
            st.session_state["agreed_disclaimer"] = True
            st.rerun()
    with c2:
        st.caption(L("must_agree"))
    return False


# ==============================================================================
# GERBANG 2: AUTENTIKASI (Google Sheets) + MODE TAMU
# ==============================================================================
def auth_gate(conn):
    if st.session_state.get("is_guest"):
        return True, "guest", "Tamu"
    if st.session_state.get("auth_user"):
        return True, st.session_state["auth_user"], st.session_state["auth_name"]

    st.write("")
    cL, cM, cR = st.columns([1, 2, 1])
    with cM:
        render_brand(big=True)
        st.write("")
        st.info(L("guest_info"))
        if st.button(L("login_as_guest"), type="primary", use_container_width=True):
            st.session_state["is_guest"] = True
            st.rerun()

        if conn is None:
            st.caption(L("db_off"))
            return False, None, None

        st.markdown("---")
        tab_login, tab_register = st.tabs([L("tab_login"), L("tab_register")])
        with tab_login:
            u = st.text_input(L("username"), key="li_user")
            pw = st.text_input(L("password"), type="password", key="li_pass")
            if st.button(L("btn_login"), type="primary", key="li_btn"):
                res = login_user(conn, u, pw)
                if res:
                    st.session_state["auth_user"], st.session_state["auth_name"] = res
                    st.rerun()
                else:
                    st.error(L("login_bad"))
            else:
                st.caption(L("login_prompt"))
        with tab_register:
            nu = st.text_input(L("username"), key="rg_user")
            nn = st.text_input(L("full_name"), key="rg_name")
            ne = st.text_input(L("email"), key="rg_email")
            npw = st.text_input(L("password"), type="password", key="rg_pass")
            if st.button(L("btn_register"), type="primary", key="rg_btn"):
                if not all([nu, nn, npw]):
                    st.warning(L("register_incomplete"))
                else:
                    ok, msg = register_user(conn, nu, nn, ne, npw)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    return False, None, None


# ==============================================================================
# 7) HALAMAN
# ==============================================================================
def page_dashboard():
    st.markdown(f'<p class="page-title">{L("dash_title")}</p>', unsafe_allow_html=True)
    state, note_key, now = market_status()
    is_open = state == "Open"
    pill = "pill-open" if is_open else "pill-closed"
    dot = "dot-open" if is_open else "dot-closed"
    st.markdown(
        f'<div style="margin:-4px 0 14px"><span class="dot {dot}"></span>{L("market_status")}: '
        f'<span class="pill {pill}">{L("open") if is_open else L("closed")}</span> &nbsp;·&nbsp; '
        f'{L(note_key)} &nbsp;·&nbsp; <span class="muted">{now.strftime("%a, %d %b %Y — %H:%M WIB")}</span></div>',
        unsafe_allow_html=True)

    hist = get_history("^JKSE", period="1y")
    info = get_info("^JKSE")
    last_px = info.get("regularMarketPrice")
    chg = pct = None
    if not hist.empty:
        closes = hist["Close"].dropna()
        if last_px is None and len(closes):
            last_px = float(closes.iloc[-1])
        if len(closes) >= 2:
            prev = float(closes.iloc[-2])
            chg = float(closes.iloc[-1]) - prev
            pct = (chg / prev * 100) if prev else None

    def dh(c, p):
        if c is None:
            return '<span class="muted">—</span>'
        cls = "up" if c >= 0 else "down"
        return f'<span class="{cls}">{"▲" if c>=0 else "▼"} {c:,.2f} ({p:+.2f}%)</span>'

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi_card("IHSG", f"{last_px:,.2f}" if last_px else "—", dh(chg, pct), accent=True), unsafe_allow_html=True)
    c2.markdown(kpi_card(L("hour"), now.strftime("%H:%M"), f'<span class="muted">{now.strftime("%d %b %Y")}</span>'), unsafe_allow_html=True)
    c3.markdown(kpi_card(L("status_lbl"), L("open") if is_open else L("closed"), f'<span class="muted">{L(note_key)}</span>'), unsafe_allow_html=True)
    hi = f"{hist['Close'].max():,.0f}" if not hist.empty else "—"
    c4.markdown(kpi_card(L("hi6m"), hi, '<span class="muted">close</span>'), unsafe_allow_html=True)

    st.write("")
    st.markdown(f'<p class="section-h">{L("ihsg_chart")}</p>', unsafe_allow_html=True)
    if not hist.empty and go is not None and make_subplots is not None:
        vol_colors = [UP if (cl >= op) else DOWN for op, cl in zip(hist["Open"], hist["Close"])]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.74, 0.26], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=hist.index, open=hist["Open"], high=hist["High"],
                      low=hist["Low"], close=hist["Close"], name="IHSG",
                      increasing_line_color=UP, decreasing_line_color=DOWN,
                      increasing_fillcolor=UP, decreasing_fillcolor=DOWN), row=1, col=1)
        fig.add_trace(go.Bar(x=hist.index, y=hist["Volume"], name="Volume",
                      marker_color=vol_colors, marker_line_width=0, opacity=0.6), row=2, col=1)
        fig.update_layout(xaxis_rangeslider_visible=False,
                          xaxis2=dict(rangeselector=dict(
                              buttons=[dict(count=1, label="1M", step="month", stepmode="backward"),
                                       dict(count=3, label="3M", step="month", stepmode="backward"),
                                       dict(count=6, label="6M", step="month", stepmode="backward"),
                                       dict(step="year", stepmode="todate", label="YTD"),
                                       dict(step="all", label="All")],
                              bgcolor="rgba(99,102,241,0.15)", x=0, y=1.02)))
        _plot(_style_fig(fig, height=480, legend=False))
    else:
        st.markdown(f'<div class="glass"><span class="muted">{L("no_chart")}</span></div>', unsafe_allow_html=True)


def page_engine(ticker):
    st.markdown(f'<p class="page-title">{L("engine_title")}</p>', unsafe_allow_html=True)
    style = st.radio(L("style"), [L("long"), L("short"), L("combo")], horizontal=True)
    st.caption(f'{L("analyzing")} **{ticker}** · {L("profile")} **{style}**')
    st.write("")
    with st.spinner(L("calculating")):
        r = recommendation_engine(ticker, style)

    c1, c2 = st.columns([1, 1.6])
    with c1:
        st.markdown(f'<span class="badge {r["cls"]}">{r["condition"]}</span>', unsafe_allow_html=True)
        st.write("")
        st.markdown(kpi_card(L("composite"), f'{r["composite"]:+.2f}',
                             f'<span class="muted">{L("comp_hint")}</span>', accent=True), unsafe_allow_html=True)
        st.write("")
        bnet = fmt_rp(r["broksum_net"]) if r["broksum_net"] else "—"
        st.markdown(
            f'<div class="glass"><div class="kpi-label">{L("components")}</div>'
            f'<div style="margin-top:8px;line-height:2.0">'
            f'📡 {L("technical")} <b class="{"up" if r["tech"]>=0 else "down"}">{r["tech"]:+.2f}</b><br>'
            f'🏦 {L("broksum")} <b>{r["broksum"]}</b> <span class="muted">({bnet})</span><br>'
            f'📰 {L("news_c")} <b class="{"up" if r["news_score"]>0 else ("down" if r["news_score"]<0 else "muted")}">{r["news_label"]}</b>'
            f'</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<p class="section-h">{L("signal_detail")}</p>', unsafe_allow_html=True)
        for name, val, sig in r["tech_det"]:
            st.markdown(signal_row(name, val, sig), unsafe_allow_html=True)

    st.write("")
    if not r["df"].empty and go is not None and make_subplots is not None:
        st.markdown(f'<p class="section-h">{L("price_ind")}</p>', unsafe_allow_html=True)
        _engine_charts(r["df"], style)
    st.info(L("engine_disclaimer"), icon="⚠️")


def _engine_charts(df, style):
    tail = df.tail(180) if style == L("short") else df.tail(400)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.56, 0.22, 0.22],
                        vertical_spacing=0.04, subplot_titles=("Price", "RSI", "MACD"))
    fig.add_trace(go.Candlestick(x=tail.index, open=tail["Open"], high=tail["High"], low=tail["Low"],
                  close=tail["Close"], name="Price", increasing_line_color=UP, decreasing_line_color=DOWN,
                  increasing_fillcolor=UP, decreasing_fillcolor=DOWN), row=1, col=1)
    if style == L("short"):
        for col, color in [("EMA9", "#60a5fa"), ("EMA21", "#f59e0b")]:
            fig.add_trace(go.Scatter(x=tail.index, y=tail[col], name=col, line=dict(width=1.5, color=color)), row=1, col=1)
        for col in ["BB_UP", "BB_LO"]:
            fig.add_trace(go.Scatter(x=tail.index, y=tail[col], name="Bollinger",
                          line=dict(width=1, color="rgba(148,163,184,0.4)"), showlegend=(col == "BB_UP")), row=1, col=1)
        rsi_col = "RSI7"
    else:
        for col, color in [("SMA50", "#60a5fa"), ("SMA200", "#f59e0b")]:
            fig.add_trace(go.Scatter(x=tail.index, y=tail[col], name=col, line=dict(width=1.6, color=color)), row=1, col=1)
        rsi_col = "RSI14"
    fig.add_trace(go.Scatter(x=tail.index, y=tail[rsi_col], name=rsi_col, line=dict(width=1.6, color=ACCENT_B)), row=2, col=1)
    fig.add_hline(y=70, line=dict(color="rgba(239,68,68,0.4)", dash="dot"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="rgba(16,185,129,0.4)", dash="dot"), row=2, col=1)
    colors = [UP if v >= 0 else DOWN for v in tail["MACD_HIST"].fillna(0)]
    fig.add_trace(go.Bar(x=tail.index, y=tail["MACD_HIST"], name="Hist", marker_color=colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=tail.index, y=tail["MACD"], name="MACD", line=dict(width=1.4, color="#60a5fa")), row=3, col=1)
    fig.add_trace(go.Scatter(x=tail.index, y=tail["MACD_SIG"], name="Signal", line=dict(width=1.4, color="#f59e0b")), row=3, col=1)
    fig.update_layout(xaxis_rangeslider_visible=False)
    p = PALETTES.get(st.session_state.get("theme", "dark"))
    for a in fig.layout.annotations:
        a.font.update(size=12, color=p["muted"])
    _plot(_style_fig(fig, height=620))


def _gauge(title, value, vmin, vmax, good="low", suffix=""):
    if value is None or go is None:
        return None
    g, y, r = "rgba(16,185,129,0.28)", "rgba(234,179,8,0.28)", "rgba(239,68,68,0.28)"
    third = (vmax - vmin) / 3
    if good == "low":
        steps = [{"range": [vmin, vmin + third], "color": g}, {"range": [vmin + third, vmin + 2 * third], "color": y}, {"range": [vmin + 2 * third, vmax], "color": r}]
    else:
        steps = [{"range": [vmin, vmin + third], "color": r}, {"range": [vmin + third, vmin + 2 * third], "color": y}, {"range": [vmin + 2 * third, vmax], "color": g}]
    p = PALETTES.get(st.session_state.get("theme", "dark"))
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={"suffix": suffix, "font": {"size": 26, "color": p["title"]}},
        gauge={"axis": {"range": [vmin, vmax], "tickcolor": p["muted"]},
               "bar": {"color": ACCENT_A, "thickness": 0.28}, "bgcolor": "rgba(0,0,0,0)",
               "borderwidth": 0, "steps": steps},
        title={"text": title, "font": {"size": 13, "color": p["muted"]}}))
    fig.update_layout(height=200, margin=dict(l=18, r=18, t=46, b=8),
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Plus Jakarta Sans"))
    return fig


def _render_gauge(col, fig, fallback):
    """Render gauge atau kartu fallback. Pakai if/else (BUKAN ternary expr)
    agar Streamlit magic tidak menulis nilai balik (None/DeltaGenerator)."""
    with col:
        if fig is not None:
            _plot(fig)
        else:
            st.markdown(f'<div class="glass"><span class="muted">{fallback}</span></div>',
                        unsafe_allow_html=True)


def _ratio_or_note(col, label, sane_val, raw_val, vmin, vmax, good, suffix):
    """Gauge bila nilai wajar; kartu 'data tidak wajar' bila absurd; '—' bila kosong."""
    with col:
        if sane_val is not None and go is not None:
            _plot(_gauge(label, sane_val, vmin, vmax, good, suffix))
        elif raw_val is not None:
            st.markdown(kpi_card(label, f"{raw_val:,.0f}{suffix}",
                                 f'<span class="muted">{L("val_weird")}</span>'), unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="glass"><span class="muted">{label}: —</span></div>',
                        unsafe_allow_html=True)


def _sane(v, hi, allow_neg=False):
    """Saring nilai rasio tak wajar (mis. PBV 13.000x dari data rusak)."""
    if v is None:
        return None
    if not allow_neg and v <= 0:
        return None
    if abs(v) > hi:
        return None
    return v


def valuation_verdict(info) -> tuple:
    """Verdict Undervalued/Wajar/Overvalued dari PER + PBV + ROE. -> (label, cls, reasons)."""
    per = _sane(info.get("trailingPE"), 1000)
    pbv = _sane(info.get("priceToBook"), 1000)
    roe = info.get("returnOnEquity")
    score, reasons = 0, []
    if per is not None:
        if per < 10:
            score += 1; reasons.append(f"PER {per:.1f}x rendah")
        elif per > 25:
            score -= 1; reasons.append(f"PER {per:.1f}x tinggi")
    if pbv is not None:
        if pbv < 1:
            score += 1; reasons.append(f"PBV {pbv:.2f}x < nilai buku")
        elif pbv > 3:
            score -= 1; reasons.append(f"PBV {pbv:.2f}x tinggi")
    if roe is not None:
        if roe > 0.15:
            score += 1; reasons.append(f"ROE {roe*100:.0f}% kuat")
        elif roe < 0:
            score -= 1; reasons.append("ROE negatif")
    if score >= 1:
        return L("val_under"), "bull", reasons
    if score <= -1:
        return L("val_over"), "bear", reasons
    return L("val_fair"), "neut", reasons


def page_fundamental(ticker):
    st.markdown(f'<p class="page-title">{L("fund_title")}</p>', unsafe_allow_html=True)
    info = get_info(ticker)
    if not info:
        st.markdown(f'<div class="glass"><span class="muted">{L("no_fund")}</span></div>', unsafe_allow_html=True)
        return
    name = info.get("longName") or info.get("shortName") or ticker
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    verdict, vcls, vreasons = valuation_verdict(info)
    reason_txt = " · ".join(vreasons) if vreasons else L("val_nodata")
    st.markdown(
        f'<div class="glass" style="border-color:rgba(99,102,241,0.45)">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">'
        f'<div><div style="font-size:1.4rem;font-weight:800">{name}</div>'
        f'<div class="muted" style="margin-top:4px">{info.get("sector","—")} · {info.get("industry","—")}</div></div>'
        f'<span class="badge {vcls}" style="font-size:0.95rem;padding:8px 18px">{verdict}</span></div>'
        f'<div style="margin-top:10px"><span class="chip chip-neut">{fmt_rp(price)}</span> &nbsp;'
        f'<span class="chip chip-neut">Market Cap: {fmt_rp(info.get("marketCap"))}</span></div>'
        f'<div class="muted" style="margin-top:8px;font-size:0.85rem">{L("val_basis")}: {reason_txt}</div></div>',
        unsafe_allow_html=True)
    st.write("")
    st.markdown(f'<p class="section-h">{L("key_ratios")}</p>', unsafe_allow_html=True)
    roe = info.get("returnOnEquity")
    dy = info.get("dividendYield")
    # yfinance kadang mengembalikan dividendYield sebagai pecahan (0.0536) atau
    # sudah persen (5.36 / 11.69). Normalisasi: <1 dianggap pecahan -> ×100.
    roe_pct = roe * 100 if roe is not None else None
    dy_pct = (dy * 100 if dy < 1 else dy) if dy is not None else None
    eps = info.get("trailingEps")
    # Saring rasio tak wajar agar gauge tidak rusak (PER/PBV); tampilkan angka mentah + catatan.
    per_s = _sane(info.get("trailingPE"), 200)
    pbv_s = _sane(info.get("priceToBook"), 60)
    der_s = _sane(info.get("debtToEquity"), 1000)
    if go is not None:
        g1, g2, g3 = st.columns(3)
        _ratio_or_note(g1, "PER (P/E)", per_s, info.get("trailingPE"), 0, 40, "low", "x")
        _ratio_or_note(g2, "PBV (P/B)", pbv_s, info.get("priceToBook"), 0, 10, "low", "x")
        _render_gauge(g3, _gauge("ROE", roe_pct, 0, 40, "high", "%"), "ROE: —")
        g4, g5, g6 = st.columns(3)
        _ratio_or_note(g4, "DER", der_s, info.get("debtToEquity"), 0, 200, "low", "")
        _render_gauge(g5, _gauge("Dividend Yield", dy_pct, 0, 12, "high", "%"), "Div Yield: —")
        with g6:
            st.markdown(kpi_card(L("eps"), f"{eps:,.0f}" if eps is not None else "—",
                                 f'<span class="muted">{L("eps_sub")}</span>'), unsafe_allow_html=True)

    lo, hi = info.get("fiftyTwoWeekLow"), info.get("fiftyTwoWeekHigh")
    if lo and hi and price and hi > lo:
        pos = max(0, min(1, (price - lo) / (hi - lo))) * 100
        st.write("")
        st.markdown(f'<p class="section-h">{L("range52")}</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="glass"><div style="display:flex;justify-content:space-between;font-size:0.8rem" class="muted">'
            f'<span>{fmt_rp(lo)}</span><span>{fmt_rp(hi)}</span></div>'
            f'<div style="position:relative;height:12px;border-radius:999px;margin:8px 0;'
            f'background:linear-gradient(90deg,#ef4444,#eab308,#10b981)">'
            f'<div style="position:absolute;left:{pos}%;top:-5px;width:4px;height:22px;border-radius:4px;'
            f'background:#fff;box-shadow:0 0 10px rgba(255,255,255,0.8);transform:translateX(-2px)"></div></div>'
            f'<div style="text-align:center">{L("in_range")} <b>{pos:.0f}%</b> {L("of_range")}</div></div>',
            unsafe_allow_html=True)

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
                st.markdown(f'<p class="section-h">{L("rev_income")}</p>', unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(go.Bar(x=years, y=rev, name=L("revenue"), marker_color=ACCENT_A))
                fig.add_trace(go.Bar(x=years, y=ni, name=L("net_income"), marker_color=UP))
                fig.update_layout(barmode="group", xaxis=dict(type="category"))
                _plot(_style_fig(fig, height=320))
        except Exception:
            pass
    st.caption(L("fund_source"))


DEFAULT_WATCHLIST = ["BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "ADRO", "ANTM", "GOTO", "UNVR"]


@st.cache_data(ttl=1800, show_spinner=False)
def bandar_metrics(kode: str) -> dict:
    """
    Bandarmology berbasis OHLCV publik (yfinance), tanpa data broker berbayar:
      - VWAP (Volume Weighted Average Price) periode 3 bulan
      - A/D Line (Accumulation/Distribution) & slope-nya
      - OBV (On-Balance Volume) & slope-nya
      - rasio volume 5 hari vs 20 hari
    Klasifikasi Indikasi: Akumulasi / Distribusi / Markup / Markdown / Netral.
    """
    df = get_history(to_jk(kode), period="3mo")
    if df is None or df.empty or len(df) < 20:
        return None
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    typ = (h + l + c) / 3
    vwap = (typ * v).cumsum() / v.cumsum().replace(0, np.nan)
    last_c, last_vwap = float(c.iloc[-1]), float(vwap.iloc[-1])

    mfm = ((c - l) - (h - c)) / (h - l).replace(0, np.nan)
    adl = (mfm.fillna(0) * v).cumsum()
    obv = (np.sign(c.diff()).fillna(0) * v).cumsum()
    n = min(10, len(df) - 1)
    adl_up = float(adl.iloc[-1] - adl.iloc[-n]) > 0
    obv_up = float(obv.iloc[-1] - obv.iloc[-n]) > 0

    vol_recent = float(v.iloc[-5:].mean())
    vol_base = float(v.iloc[-20:].mean()) or 1.0
    vol_ratio = vol_recent / vol_base
    above = last_c >= last_vwap

    if above and adl_up and obv_up:
        ind = "Akumulasi"
    elif (not above) and (not adl_up) and (not obv_up):
        ind = "Distribusi"
    elif above and obv_up:
        ind = "Markup"
    elif (not above) and (not obv_up):
        ind = "Markdown"
    else:
        ind = "Netral"

    _, bk_label, _ = broksum_score(kode)          # dari FastAPI broksum bila ada
    broker = bk_label if bk_label not in ("n/a", "") else "—"

    return {"Emiten": kode, "Harga": round(last_c, 2), "VWAP": round(last_vwap, 2),
            "vs VWAP %": round((last_c / last_vwap - 1) * 100, 2) if last_vwap else None,
            "Volume_Transaksi": int(vol_recent), "Vol Ratio": round(vol_ratio, 2),
            "Broker_Dominan": broker, "Indikasi_Nipu": ind}


def _vwap_chart(kode: str):
    df = get_history(to_jk(kode), period="3mo")
    if df is None or df.empty or go is None or make_subplots is None:
        return
    c = df["Close"]
    typ = (df["High"] + df["Low"] + c) / 3
    vwap = (typ * df["Volume"]).cumsum() / df["Volume"].cumsum().replace(0, np.nan)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Scatter(x=df.index, y=c, name="Close", line=dict(color=ACCENT_A, width=1.8)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=vwap, name="VWAP", line=dict(color="#f59e0b", width=1.6, dash="dot")), row=1, col=1)
    vc = [UP if cl >= op else DOWN for op, cl in zip(df["Open"], df["Close"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color=vc, opacity=0.6), row=2, col=1)
    _plot(_style_fig(fig, height=380))


def _ind_color(val):
    m = {"Akumulasi": "#10b981", "Markup": "#34d399",
         "Distribusi": "#ef4444", "Markdown": "#f87171", "Netral": "#94a3b8"}
    return f"color:{m.get(val, '#94a3b8')};font-weight:700"


# ---- Worksheet & data sumber untuk Bandar/Konglo (Sheets + broksum API) ----
BROKER_WS, KONGLO_WS, CORP_WS = "BrokerSummary", "KongloHoldings", "CorpActions"

KONGLO_DEMO = [
    {"Konglomerat": "Prajogo Pangestu", "Emiten": "BREN", "Persen": 54.0, "Status": "Akumulasi"},
    {"Konglomerat": "Prajogo Pangestu", "Emiten": "BRPT", "Persen": 70.0, "Status": "Hold"},
    {"Konglomerat": "Prajogo Pangestu", "Emiten": "TPIA", "Persen": 33.0, "Status": "Hold"},
    {"Konglomerat": "Prajogo Pangestu", "Emiten": "CUAN", "Persen": 68.0, "Status": "Akumulasi"},
    {"Konglomerat": "Keluarga Hartono", "Emiten": "BBCA", "Persen": 54.94, "Status": "Hold"},
    {"Konglomerat": "Anthoni Salim", "Emiten": "INDF", "Persen": 50.07, "Status": "Hold"},
    {"Konglomerat": "Anthoni Salim", "Emiten": "ICBP", "Persen": 80.53, "Status": "Hold"},
    {"Konglomerat": "Anthoni Salim", "Emiten": "DNET", "Persen": 34.0, "Status": "Right Issue"},
    {"Konglomerat": "Low Tuck Kwong", "Emiten": "BYAN", "Persen": 61.0, "Status": "Distribusi"},
    {"Konglomerat": "Garibaldi Thohir", "Emiten": "ADRO", "Persen": 35.0, "Status": "Dividen"},
    {"Konglomerat": "Grup Astra (Jardine)", "Emiten": "ASII", "Persen": 50.11, "Status": "Hold"},
    {"Konglomerat": "Grup Bakrie", "Emiten": "BUMI", "Persen": 24.0, "Status": "Akuisisi"},
]
CORP_DEMO = [
    {"Emiten": "BBRI", "Aksi": "Dividen", "Detail": "Dividen tunai final Rp135/saham", "Tanggal": "2026-03-20"},
    {"Emiten": "BREN", "Aksi": "Right Issue", "Detail": "Rencana HMETD untuk ekspansi panas bumi", "Tanggal": "2026-04-10"},
    {"Emiten": "BUMI", "Aksi": "Akuisisi", "Detail": "Akuisisi aset mineral via anak usaha", "Tanggal": "2026-02-15"},
    {"Emiten": "DNET", "Aksi": "Backdoor Listing", "Detail": "Indikasi backdoor oleh investor strategis", "Tanggal": "2026-01-30"},
]


def _broker_demo(kode: str) -> list:
    rng = np.random.default_rng(sum(ord(x) for x in kode))
    out = []
    for b in ["BK", "MG", "CC", "AK", "YP", "PD", "DR", "KZ", "RX", "NI"]:
        net = int(rng.integers(-150, 150)) * 100_000_000  # rupiah
        out.append({"Broker": b, "Net_Value": net})
    return out


def fetch_broker_rows(kode: str, conn) -> tuple:
    """Net value per broker. Urutan sumber: broksum API -> Sheets -> DEMO."""
    try:
        api = st.secrets["broksum"]["api_url"].rstrip("/")
    except Exception:
        api = ""
    if api and requests is not None:
        try:
            r = requests.get(f"{api}/broksum/{kode}", timeout=8)
            if r.ok:
                rows = r.json().get("rows", [])
                if rows:
                    agg = {}
                    for x in rows:
                        agg[x.get("kode_broker", "?")] = agg.get(x.get("kode_broker", "?"), 0) + int(x.get("net_value", 0) or 0)
                    return [{"Broker": k, "Net_Value": v} for k, v in agg.items()], "API broksum"
        except Exception:
            pass
    if conn is not None:
        df = _read_ws(conn, BROKER_WS, ttl=30)
        if not df.empty and "kode_saham" in df and "kode_broker" in df:
            sub = df[df["kode_saham"].astype(str).str.upper() == kode.upper()]
            if not sub.empty:
                return ([{"Broker": str(r.get("kode_broker", "?")),
                          "Net_Value": int(float(r.get("net_value", 0) or 0))} for _, r in sub.iterrows()],
                        BROKER_WS)
    return _broker_demo(kode), "DEMO"


def fetch_konglo(conn) -> tuple:
    if conn is not None:
        df = _read_ws(conn, KONGLO_WS, ttl=60)
        if not df.empty and "Konglomerat" in df:
            return df, KONGLO_WS
    return pd.DataFrame(KONGLO_DEMO), "DEMO"


def fetch_corp(conn) -> tuple:
    if conn is not None:
        df = _read_ws(conn, CORP_WS, ttl=60)
        if not df.empty and "Emiten" in df:
            return df, CORP_WS
    return pd.DataFrame(CORP_DEMO), "DEMO"


@st.cache_data(ttl=3600, show_spinner=False)
def get_yf_actions(ticker: str):
    if yf is None:
        return None
    try:
        a = yf.Ticker(ticker).actions
        return a if a is not None and not getattr(a, "empty", True) else None
    except Exception:
        return None


def _fmt_b(v):
    try:
        return f"{v/1e9:+.2f}"
    except Exception:
        return "—"


def _src_badge(src):
    txt = L("radar_demo_note") if src == "DEMO" else f'{L("radar_source")}: {src}'
    icon = "🚧" if src == "DEMO" else "✅"
    st.caption(f"{icon} {txt}")


def _tab_bandar(conn, ticker):
    kode = ticker.replace(".JK", "")
    st.markdown(f'<p class="section-h">{L("radar_buyers")} / {L("radar_sellers")} — {kode}</p>', unsafe_allow_html=True)
    rows, src = fetch_broker_rows(kode, conn)
    df = pd.DataFrame(rows)
    if df.empty:
        st.info(L("radar_no_data"))
        return
    df["Net (Rp M)"] = df["Net_Value"].apply(_fmt_b)
    buyers = df[df["Net_Value"] > 0].sort_values("Net_Value", ascending=False)
    sellers = df[df["Net_Value"] < 0].sort_values("Net_Value")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<span class="chip chip-up">{L("radar_buyers")}</span>', unsafe_allow_html=True)
        st.dataframe(buyers[["Broker", "Net (Rp M)"]], use_container_width=True, hide_index=True)
    with c2:
        st.markdown(f'<span class="chip chip-down">{L("radar_sellers")}</span>', unsafe_allow_html=True)
        st.dataframe(sellers[["Broker", "Net (Rp M)"]], use_container_width=True, hide_index=True)
    net = df["Net_Value"].sum()
    side = "up" if net >= 0 else "down"
    st.markdown(kpi_card(f"Net Total — {kode}", f"Rp {net/1e9:+.2f} M",
                f'<span class="{side}">{"Akumulasi bersih" if net>=0 else "Distribusi bersih"}</span>', accent=True),
                unsafe_allow_html=True)
    _src_badge(src)


def _tab_konglo(conn):
    df, src = fetch_konglo(conn)
    if df.empty:
        st.info(L("radar_no_data"))
        return
    names = sorted(df["Konglomerat"].astype(str).unique())
    pick = st.selectbox(L("radar_konglo_pick"), ["— " + L("news_all").split(" ")[-1] + " —"] + names)
    view = df if pick.startswith("—") else df[df["Konglomerat"].astype(str) == pick]

    st.markdown(f'<p class="section-h">{L("radar_portfolio")}</p>', unsafe_allow_html=True)
    cols = [c for c in ["Konglomerat", "Emiten", "Persen", "Status"] if c in view.columns]
    base = view[cols].style
    cs = base.map if hasattr(base, "map") else base.applymap
    try:
        styler = cs(_ind_color, subset=["Status"]).format({"Persen": "{:.2f}%"})
    except Exception:
        styler = view[cols]
    st.dataframe(styler, use_container_width=True, hide_index=True)

    # Aktivitas: ringkasan per status
    if "Status" in view.columns:
        st.markdown(f'<p class="section-h">{L("radar_activity")}</p>', unsafe_allow_html=True)
        counts = view["Status"].value_counts()
        chips = " ".join(f'<span class="chip chip-neut">{k}: {v}</span>' for k, v in counts.items())
        st.markdown(f'<div class="glass">{chips}</div>', unsafe_allow_html=True)
    _src_badge(src)


def _tab_corp(conn, ticker):
    kode = ticker.replace(".JK", "")
    st.markdown(f'<p class="section-h">{L("radar_corp_yf")} — {kode}</p>', unsafe_allow_html=True)
    act = get_yf_actions(ticker)
    if act is not None and go is not None:
        recent = act.tail(12)
        fig = go.Figure()
        if "Dividends" in recent:
            fig.add_trace(go.Bar(x=recent.index, y=recent["Dividends"], name="Dividen", marker_color=ACCENT_A))
        if "Stock Splits" in recent:
            sp = recent[recent["Stock Splits"] > 0]
            if not sp.empty:
                fig.add_trace(go.Scatter(x=sp.index, y=sp["Stock Splits"], name="Split",
                              mode="markers", marker=dict(color="#f59e0b", size=10)))
        _plot(_style_fig(fig, height=260))
    else:
        st.markdown(f'<div class="glass"><span class="muted">{L("radar_no_data")}</span></div>', unsafe_allow_html=True)

    df, src = fetch_corp(conn)
    st.markdown(f'<p class="section-h">{L("radar_corp_table")}</p>', unsafe_allow_html=True)
    cols = [c for c in ["Emiten", "Aksi", "Detail", "Tanggal"] if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)
    _src_badge(src)


def _tab_signal():
    raw = st.text_input(L("radar_watchlist"), value=", ".join(DEFAULT_WATCHLIST))
    tickers = [t.strip().upper() for t in raw.replace(";", ",").split(",") if t.strip()][:15]
    with st.spinner(L("radar_scanning")):
        rows = [m for m in (bandar_metrics(t) for t in tickers) if m]
    if not rows:
        st.markdown(f'<div class="glass"><span class="muted">{L("radar_no_data")}</span></div>', unsafe_allow_html=True)
        return
    df = pd.DataFrame(rows)
    akum = sum(1 for r in rows if r["Indikasi_Nipu"] in ("Akumulasi", "Markup"))
    dist = sum(1 for r in rows if r["Indikasi_Nipu"] in ("Distribusi", "Markdown"))
    c1, c2, c3 = st.columns(3)
    c1.markdown(kpi_card("Akumulasi/Markup", f"{akum}", '<span class="up">net beli arah</span>', accent=True), unsafe_allow_html=True)
    c2.markdown(kpi_card("Distribusi/Markdown", f"{dist}", '<span class="down">net jual arah</span>'), unsafe_allow_html=True)
    c3.markdown(kpi_card("Dipindai", f"{len(rows)}", '<span class="muted">emiten</span>'), unsafe_allow_html=True)
    st.write("")
    base = df.style
    cell_style = base.map if hasattr(base, "map") else base.applymap
    styler = cell_style(_ind_color, subset=["Indikasi_Nipu"]).format(
        {"Harga": "{:,.0f}", "VWAP": "{:,.0f}", "vs VWAP %": "{:+.2f}",
         "Volume_Transaksi": "{:,.0f}", "Vol Ratio": "{:.2f}"})
    st.dataframe(styler, use_container_width=True, hide_index=True)
    st.write("")
    st.markdown(f'<p class="section-h">{L("radar_detail")}</p>', unsafe_allow_html=True)
    sel = st.selectbox("Emiten", [r["Emiten"] for r in rows], label_visibility="collapsed")
    _vwap_chart(sel)
    st.caption(L("radar_note"))


def page_radar(conn, ticker):
    st.markdown(f'<p class="page-title">{L("radar_title")}</p>', unsafe_allow_html=True)
    st.caption(L("radar_caption"))
    t1, t2, t3, t4 = st.tabs([L("radar_tab_bandar"), L("radar_tab_konglo"),
                              L("radar_tab_corp"), L("radar_tab_signal")])
    with t1:
        _tab_bandar(conn, ticker)
    with t2:
        _tab_konglo(conn)
    with t3:
        _tab_corp(conn, ticker)
    with t4:
        _tab_signal()
    # TODO: Implement VWAP & KSEI logic here
    #   - VWAP/OBV/A-D: sudah diimplementasikan (tab Sinyal).
    #   - Broker flow: dari broksum API / worksheet BrokerSummary (live bila diisi).
    #   - Kepemilikan KSEI & aksi korporasi: worksheet KongloHoldings / CorpActions
    #     (butuh diisi manual / scraper, tidak ada feed gratis).


def _time_ago(published: str) -> str:
    if not published:
        return ""
    try:
        dt = pd.to_datetime(published, utc=True, errors="coerce")
        if pd.isna(dt):
            return published
        h = int((pd.Timestamp.utcnow() - dt).total_seconds() // 3600)
        if h < 1:
            return "baru saja" if st.session_state.get("lang") == "id" else "just now"
        if h < 24:
            return f"{h} jam lalu" if st.session_state.get("lang") == "id" else f"{h}h ago"
        d = h // 24
        return f"{d} hari lalu" if st.session_state.get("lang") == "id" else f"{d}d ago"
    except Exception:
        return published


def page_news(ticker):
    st.markdown(f'<p class="page-title">{L("news_title")}</p>', unsafe_allow_html=True)
    kode = ticker.replace(".JK", "")
    options = [L("news_all")] + list(NEWS_FEEDS.keys()) + [f"Google News · {kode}"]
    source = st.radio(L("news_source"), options, horizontal=True)
    with st.spinner("…"):
        if source == L("news_all"):
            news = fetch_all_feeds()
        elif source.startswith("Google News"):
            news = fetch_news_emiten(kode)
        else:
            news = fetch_feed(NEWS_FEEDS[source], source_name=source)

    if not news:
        st.markdown(f'<div class="glass"><span class="muted">{L("no_news")}</span></div>', unsafe_allow_html=True)
        return
    score, label = news_score(news)
    pos = sum(1 for n in news if n.get("skor", 0) > 0)
    neg = sum(1 for n in news if n.get("skor", 0) < 0)
    cls = "up" if score > 0.1 else ("down" if score < -0.1 else "muted")
    c1, c2 = st.columns([1, 2])
    c1.markdown(kpi_card(L("sentiment_agg"), f"{score:+.2f}", f'<span class="{cls}">{label}</span>', accent=True), unsafe_allow_html=True)
    c2.markdown(kpi_card(L("summary"), f"{len(news)}",
                f'<span class="up">▲ {pos} {L("positive")}</span> &nbsp; '
                f'<span class="down">▼ {neg} {L("negative")}</span> &nbsp; '
                f'<span class="muted">● {len(news)-pos-neg} {L("neutral")}</span>'), unsafe_allow_html=True)
    st.write("")
    for n in news:
        sc = n.get("skor", 0)
        chip = ('<span class="chip chip-up">+</span>' if sc > 0 else
                '<span class="chip chip-down">−</span>' if sc < 0 else
                '<span class="chip chip-neut">•</span>')
        meta = " · ".join(x for x in [n.get("sumber", ""), _time_ago(n.get("tanggal", ""))] if x)
        summary = n.get("ringkas", "")
        sum_html = f'<div class="news-sum">{summary}</div>' if summary else ""
        # Keterkaitan: emiten yang mungkin terdampak + arah perkiraan
        rel = n.get("terkait", [])
        if rel:
            rel_chips = " ".join(
                f'<span class="chip {"chip-up" if a=="↑" else ("chip-down" if a=="↓" else "chip-neut")}">{c} {a}</span>'
                for c, a in rel)
            rel_html = f'<div style="margin-top:8px">{L("news_related")}: {rel_chips}</div>'
        else:
            rel_html = ""
        st.markdown(
            f'<a class="news-card" href="{n["link"]}" target="_blank">'
            f'<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start">'
            f'<span class="news-title">{n["judul"]}</span>{chip}</div>'
            f'{sum_html}'
            f'{rel_html}'
            f'<div class="news-meta">{meta}</div></a>', unsafe_allow_html=True)


def page_portfolio(conn, username, ticker):
    st.markdown(f'<p class="page-title">{L("port_title")}</p>', unsafe_allow_html=True)
    if conn is None or st.session_state.get("is_guest"):
        st.markdown(f'<div class="glass"><span class="muted">{L("port_off")}</span></div>', unsafe_allow_html=True)
        return

    with st.expander(L("add_holding")):
        kode = st.text_input(L("stock_code"), value=ticker.replace(".JK", ""), key="pf_kode")
        harga = st.number_input(L("avg_price"), min_value=0.0, step=50.0, key="pf_harga")
        lot = st.number_input(L("lots"), min_value=0, step=1, key="pf_lot")
        if st.button(L("save"), type="primary", key="pf_save"):
            df = _read_ws(conn, PORTF_WS, ttl=0)
            row = {"username": username, "kode_saham": kode.strip().upper(),
                   "harga_rata2": float(harga), "jumlah_lot": int(lot),
                   "created_at": datetime.utcnow().isoformat()}
            new = pd.concat([df, pd.DataFrame([row])], ignore_index=True) if not df.empty else pd.DataFrame([row])
            if _write_ws(conn, PORTF_WS, new):
                st.success(L("saved"))
                st.rerun()

    df = _read_ws(conn, PORTF_WS, ttl=0)
    if not df.empty and "username" in df:
        df = df[df["username"].astype(str) == username]
    if df.empty:
        st.info(L("empty_port"))
        return

    out, total_modal, total_kini = [], 0.0, 0.0
    for _, r in df.iterrows():
        kode = str(r["kode_saham"])
        price = get_info(to_jk(kode)).get("currentPrice")
        lot = int(r["jumlah_lot"])
        avg = float(r["harga_rata2"])
        modal = avg * lot * LOT_SIZE
        kini = (price * lot * LOT_SIZE) if price else None
        pl = (kini - modal) if kini is not None else None
        total_modal += modal
        if kini is not None:
            total_kini += kini
        out.append({"Kode": kode, "Lot": lot, "Avg": avg, "Harga Kini": price,
                    "Modal": modal, "Nilai Kini": kini, "P/L": pl,
                    "P/L %": (pl / modal * 100) if (pl is not None and modal) else None})

    total_pl = total_kini - total_modal
    c1, c2, c3 = st.columns(3)
    c1.markdown(kpi_card(L("total_modal"), fmt_rp(total_modal)), unsafe_allow_html=True)
    c2.markdown(kpi_card(L("value_now"), fmt_rp(total_kini), accent=True), unsafe_allow_html=True)
    pcls = "up" if total_pl >= 0 else "down"
    pct = (total_pl / total_modal * 100) if total_modal else 0
    c3.markdown(kpi_card(L("total_pl"), fmt_rp(total_pl), f'<span class="{pcls}">{pct:+.2f}%</span>'), unsafe_allow_html=True)
    st.write("")
    st.dataframe(pd.DataFrame(out), use_container_width=True, hide_index=True)


# ==============================================================================
# 8) MAIN
# ==============================================================================
def main():
    init_state()
    inject_css(st.session_state["theme"])

    # Kontrol global (selalu tersedia, termasuk di gerbang)
    with st.sidebar:
        render_brand()
        st.markdown("---")
        st.caption(L("settings"))
        lang_en = st.toggle("🌐 English", value=(st.session_state["lang"] == "en"), key="tg_lang")
        st.session_state["lang"] = "en" if lang_en else "id"
        dark = st.toggle(f"🌙 {L('dark_mode')}", value=(st.session_state["theme"] == "dark"), key="tg_theme")
        st.session_state["theme"] = "dark" if dark else "light"
        st.markdown("---")

    if not disclaimer_gate():
        st.stop()

    conn = get_conn()
    auth_ok, username, name = auth_gate(conn)
    if not auth_ok:
        st.stop()

    with st.sidebar:
        if st.session_state.get("is_guest"):
            st.caption(L("guest_badge"))
        else:
            st.caption(f"👤 {name}")
        if st.button(L("logout"), use_container_width=True):
            for k in ("is_guest", "auth_user", "auth_name"):
                st.session_state.pop(k, None)
            st.rerun()
        st.markdown("---")
        nav_items = [L("nav_dashboard"), L("nav_engine"), L("nav_fundamental"),
                     L("nav_radar"), L("nav_news"), L("nav_portfolio")]
        page = st.radio("nav", nav_items, label_visibility="collapsed")
        st.markdown("---")
        ticker_input = st.text_input(L("stock_code"), value="BMRI").strip().upper()
        ticker = to_jk(ticker_input)
        st.caption(L("jk_hint"))
        st.markdown("---")
        st.caption(L("not_advice"))

    if page == L("nav_dashboard"):
        page_dashboard()
    elif page == L("nav_engine"):
        page_engine(ticker)
    elif page == L("nav_fundamental"):
        page_fundamental(ticker)
    elif page == L("nav_radar"):
        page_radar(conn, ticker)
    elif page == L("nav_news"):
        page_news(ticker)
    else:
        page_portfolio(conn, username, ticker)


if __name__ == "__main__":
    main()
