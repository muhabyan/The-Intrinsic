"""
================================================================================
api.py — Layanan FastAPI Broker Summary untuk The Intrinsic
================================================================================

Peran dalam arsitektur:
    Scraper / feed broksum  --(POST /broksum)-->  Supabase (broker_summary)
                                                        |
    Streamlit (broksum_score) --(GET /broksum/{kode}/score)-->  skor broksum

Mesin rekomendasi di app.py (fungsi broksum_score) memanggil endpoint
GET /broksum/{kode}/score bila [broksum].api_url diisi di secrets.toml.
Dengan begitu data broksum otomatis masuk ke skor komposit. Bila API tidak
dikonfigurasi atau tidak bisa dihubungi, app.py jatuh-balik membaca Supabase
secara langsung.

Logika klasifikasi (akumulasi/distribusi -> skor) memakai modul yang sama,
broksum_core.classify_nets, supaya hasil API == hasil Streamlit.

Menjalankan:
    export SUPABASE_URL="https://xxxx.supabase.co"
    export SUPABASE_KEY="<service_role_key>"   # server-side; aman utk ingest
    uvicorn api:app --reload --port 8000

Konfigurasi di app.py (.streamlit/secrets.toml):
    [broksum]
    api_url = "http://localhost:8000"

Contoh ingest:
    curl -X POST http://localhost:8000/broksum \
      -H "Content-Type: application/json" \
      -d '{"records":[
            {"kode_saham":"BMRI","tanggal":"2026-05-29","kode_broker":"MG","net_value":15000000000},
            {"kode_saham":"BMRI","tanggal":"2026-05-29","kode_broker":"CC","net_value":-4000000000}
          ]}'
================================================================================
"""

import os
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from broksum_core import classify_nets

try:
    from supabase import create_client, Client
except ImportError:  # pragma: no cover
    create_client = None
    Client = None

app = FastAPI(
    title="The Intrinsic — Broksum API",
    description="Ingest & agregasi broker summary, sumber data untuk mesin rekomendasi.",
    version="1.0.0",
)

# Klien Supabase dibuat sekali (lazy) dan dipakai ulang antar request.
_sb_client: Optional["Client"] = None


def get_client() -> "Client":
    """Buat / kembalikan klien Supabase dari environment variable."""
    global _sb_client
    if _sb_client is not None:
        return _sb_client
    if create_client is None:
        raise HTTPException(500, "Paket `supabase` belum terpasang di server.")
    url = os.environ.get("SUPABASE_URL")
    # Di sisi server, service_role boleh dipakai (untuk ingest). Jangan di klien.
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise HTTPException(
            500, "SUPABASE_URL / SUPABASE_KEY belum diset di environment server."
        )
    _sb_client = create_client(url, key)
    return _sb_client


# ------------------------------------------------------------------ schemas ---
class BrokerNet(BaseModel):
    kode_saham: str = Field(..., examples=["BMRI"])
    tanggal: date = Field(..., examples=["2026-05-29"])
    kode_broker: str = Field(..., examples=["MG"])
    net_value: int = Field(
        ..., description="Rupiah; positif = net beli, negatif = net jual"
    )


class IngestRequest(BaseModel):
    records: List[BrokerNet]


class ScoreResponse(BaseModel):
    kode_saham: str
    score: float
    label: str
    total_net: int
    size: str
    direction: str
    count: int


# ----------------------------------------------------------------- endpoints ---
@app.get("/")
def health():
    return {"status": "ok", "service": "intrinsic-broksum", "version": app.version}


@app.post("/broksum")
def ingest(payload: IngestRequest):
    """Upsert baris broker summary ke Supabase (idempotent per kunci unik)."""
    if not payload.records:
        raise HTTPException(400, "Field `records` tidak boleh kosong.")
    sb = get_client()
    rows = [
        {
            "kode_saham": r.kode_saham.strip().upper(),
            "tanggal": r.tanggal.isoformat(),
            "kode_broker": r.kode_broker.strip().upper(),
            "net_value": r.net_value,
        }
        for r in payload.records
    ]
    try:
        # Cocok dengan unique (kode_saham, tanggal, kode_broker) di schema.sql
        sb.table("broker_summary").upsert(
            rows, on_conflict="kode_saham,tanggal,kode_broker"
        ).execute()
    except Exception as exc:
        raise HTTPException(500, f"Gagal menyimpan ke Supabase: {exc}")
    return {"upserted": len(rows)}


def _fetch_rows(sb, kode: str) -> list:
    kode = kode.strip().upper()
    try:
        res = (
            sb.table("broker_summary")
            .select("kode_broker,tanggal,net_value")
            .eq("kode_saham", kode)
            .execute()
        )
        return res.data or []
    except Exception as exc:
        raise HTTPException(500, f"Gagal membaca broker_summary: {exc}")


@app.get("/broksum/{kode}")
def get_broksum(kode: str):
    """Kembalikan baris broker summary mentah untuk satu emiten."""
    sb = get_client()
    rows = _fetch_rows(sb, kode)
    return {"kode_saham": kode.strip().upper(), "count": len(rows), "rows": rows}


@app.get("/broksum/{kode}/score", response_model=ScoreResponse)
def get_score(kode: str):
    """
    Skor broksum teragregasi untuk satu emiten — inilah endpoint yang
    dipanggil mesin rekomendasi Streamlit (broksum_score di app.py).
    """
    sb = get_client()
    rows = _fetch_rows(sb, kode)
    result = classify_nets([r.get("net_value", 0) for r in rows])
    result["kode_saham"] = kode.strip().upper()
    return result
