"""Snapshot diário do motor de score.

O pipeline gera um arquivo JSON com indicadores, scores e detalhamento de
todas as ações. A API lê esse arquivo (e, quando configurado, o banco).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import rules
from .engine import score_universe
from .indicators import build_indicators

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
SNAPSHOT_DIR = ROOT / "data" / "snapshots"
LATEST = SNAPSHOT_DIR / "scores_latest.json"


def build_snapshot(fund: dict, price: dict) -> dict:
    indicators = build_indicators(fund["rows"], price["rows"])
    scored = score_universe(indicators)

    assets = []
    for t, ind in indicators.items():
        s = scored[t]
        assets.append({
            "ticker": t,
            "name": ind["name"],
            "sector": ind["sector"],
            "type": ind["type"],
            "price": ind["price"],
            "eliminated": s["eliminated"],
            "eliminations": s["eliminations"],
            "warnings": s["warnings"],
            "scores": s["scores"],
            "breakdown": s["breakdown"],
            "indicators": {k: v for k, v in ind.items()
                           if k not in ("ticker", "name", "sector", "type")},
        })
    assets.sort(key=lambda a: a["ticker"])

    unavailable = sorted({
        f'{d.label}: {r.label}'
        for d in rules.DIMENSIONS
        for r in (d.reguas + (d.reguas_financeiro or ()))
        if not r.available
    })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of": price.get("as_of"),
        "rule_version": rules.RULE_VERSION,
        "sources": {
            "fundamentals": fund.get("source"),
            "fundamentals_fetched_at": fund.get("fetched_at"),
            "prices": price.get("source"),
        },
        "universe_size": len(assets),
        "eligible": sum(1 for a in assets if not a["eliminated"]),
        "eliminated": [
            {"ticker": a["ticker"], "reasons": [e["reason"] for e in a["eliminations"]]}
            for a in assets if a["eliminated"]
        ],
        "data_quality": {
            "unavailable_reguas": unavailable,
            "pending_rules": rules.PENDING_RULES,
            "note": ("Réguas indisponíveis dependem das demonstrações históricas da CVM "
                     "(próxima etapa do pipeline). Seus pesos são redistribuídos entre "
                     "as réguas presentes da mesma dimensão."),
        },
        "assets": assets,
    }


def save(snapshot: dict, path: Path = LATEST) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


_cache: dict = {"mtime": None, "data": None}


def load_latest(path: Path = LATEST) -> dict | None:
    """Lê o snapshot mais recente (com cache por data de modificação)."""
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    if _cache["mtime"] != mtime:
        _cache["data"] = json.loads(path.read_text(encoding="utf-8"))
        _cache["mtime"] = mtime
    return _cache["data"]


def latest_raw(prefix: str) -> Path | None:
    files = sorted(RAW_DIR.glob(f"{prefix}_*.json"))
    return files[-1] if files else None
