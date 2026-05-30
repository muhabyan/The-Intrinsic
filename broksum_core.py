"""
================================================================================
broksum_core — Logika inti Broker Summary (dipakai bersama)
================================================================================

Modul murni (tanpa dependensi Streamlit / Supabase / FastAPI) yang berisi
klasifikasi akumulasi/distribusi broker. Diimpor oleh:
    - app.py  (mesin rekomendasi Streamlit)
    - api.py  (layanan FastAPI broksum)

Tujuan: satu sumber kebenaran untuk skor broksum, supaya hasil di Streamlit
dan di API selalu konsisten.
================================================================================
"""

from typing import Iterable, Dict

# Ambang nilai net (Rupiah) untuk klasifikasi kualitatif ukuran arus dana.
BIG_THRESHOLD = 10_000_000_000      # >= 10 miliar  -> "Big"
MEDIUM_THRESHOLD = 1_000_000_000    # >= 1 miliar   -> "Medium"


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def classify_nets(nets: Iterable) -> Dict:
    """
    Klasifikasikan daftar net value broker menjadi skor & label.

    Args:
        nets: iterable berisi net value per broker (Rupiah).
              Positif = net beli (akumulasi), negatif = net jual (distribusi).

    Returns:
        dict dengan kunci:
          - score      : float -1..+1 (rasio net terhadap gross)
          - label      : str, mis. "Big Acc", "Medium Dist", "Neutral"
          - total_net  : int, total net value (Rupiah)
          - size       : "Big" | "Medium" | "Small"
          - direction  : "Acc" | "Dist" | "Neutral"
          - count      : jumlah baris broker yang dihitung
    """
    cleaned = [float(n or 0) for n in nets]
    total_net = sum(cleaned)
    gross = sum(abs(n) for n in cleaned) or 1.0
    ratio = _clip(total_net / gross)

    abs_net = abs(total_net)
    if abs_net >= BIG_THRESHOLD:
        size = "Big"
    elif abs_net >= MEDIUM_THRESHOLD:
        size = "Medium"
    else:
        size = "Small"

    if total_net > 0:
        direction = "Acc"
    elif total_net < 0:
        direction = "Dist"
    else:
        direction = "Neutral"

    label = f"{size} {direction}" if direction != "Neutral" else "Neutral"

    return {
        "score": float(ratio),
        "label": label,
        "total_net": int(total_net),
        "size": size,
        "direction": direction,
        "count": len(cleaned),
    }
