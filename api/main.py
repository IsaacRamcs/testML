"""API do serviço de análise Eren (FastAPI).

Perfil do investidor (US03):
    GET  /api/questionnaire        -> perguntas e opções (consumido pelo app RN)
    POST /api/profile              -> respostas -> perfil + vetor de pesos + ranking

Motor de score das ações (US07):
    GET  /api/rankings             -> ranking por estratégia (?vector=renda)
    POST /api/rankings             -> ranking para um vetor de pesos qualquer
    GET  /api/assets/{ticker}      -> scores, detalhamento por régua e indicadores
    GET  /api/assets/{ticker}/history -> cotação atual + histórico de fechamento (?range=1a)
    GET  /api/scores/meta          -> data, fontes, cobertura e regras pendentes

Infra:
    GET  /api/health               -> status do serviço
    GET  /                         -> página de demonstração

Rodar:  uvicorn api.main:app --reload --host 0.0.0.0
Docs:   http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from eren_ml import __version__
from eren_ml.profile import InvalidAnswersError, classify, to_dict
from eren_ml.profile.demo_assets import rank_demo_assets
from eren_ml.profile.weights import WEIGHT_VECTOR_LABELS, WEIGHT_VECTORS
from eren_ml.scoring.ranking import rank
from eren_ml.scoring.rules import MIN_HISTORY_DAYS, MIN_LIQUIDITY_BRL
from eren_ml.scoring.snapshot import load_latest

DISCLAIMER = (
    "Ferramenta educacional de apoio à decisão. As informações apresentadas não "
    "constituem recomendação de investimento. Rentabilidade passada não garante "
    "resultados futuros."
)

app = FastAPI(
    title="Eren — Serviço de Análise",
    description="Motor de perfil do investidor e score de ações. " + DISCLAIMER,
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TCC/dev; restringir na fase de produção
    allow_methods=["*"],
    allow_headers=["*"],
)


def _snapshot_or_404() -> dict:
    snap = load_latest()
    if snap is None:
        raise HTTPException(
            status_code=503,
            detail="Ainda não há scores calculados. Rode: python -m eren_ml.pipeline.run",
        )
    return snap


def _meta(snap: dict) -> dict:
    return {
        "as_of": snap.get("as_of"),
        "generated_at": snap.get("generated_at"),
        "rule_version": snap.get("rule_version"),
        "universe_size": snap.get("universe_size"),
        "eligible": snap.get("eligible"),
    }


class AnswersPayload(BaseModel):
    answers: dict[str, str] = Field(
        ...,
        description="Mapa pergunta_id -> opção escolhida",
        json_schema_extra={"example": {
            "q1_idade": "31_45", "q2_percentual_renda": "15_30", "q3_reserva": "3_6m",
            "q4_horizonte": "mais_10a", "q5_reacao_queda": "compro_mais",
            "q6_experiencia": "acoes", "q7_conhecimento": "intermediario",
            "q8_fatia_patrimonio": "30_60", "q9_preferencia": "maximo_retorno",
            "q10_dependentes": "nenhuma", "q11_estabilidade_renda": "estavel",
            "q12_objetivo": "renda",
        }},
    )
    persist: bool = Field(False, description="Se true, salva o perfil no banco (requer DATABASE_URL)")


class ScoresPayload(BaseModel):
    tickers: list[str] = Field(..., json_schema_extra={"example": ["PETR4", "BBAS3"]})
    weights: dict[str, float] = Field(..., json_schema_extra={"example": WEIGHT_VECTORS["renda"]})


class SearchPayload(BaseModel):
    q: str = Field("", description="Código ou nome da empresa (vazio = todas)")
    weights: dict[str, float] = Field(..., json_schema_extra={"example": WEIGHT_VECTORS["renda"]})
    limit: int = 20


def _norm(t: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def _score_one(asset: dict, weights: dict[str, float]) -> dict:
    """Score de UMA ação para um vetor de pesos (inclui eliminadas, com motivo)."""
    base = {
        "ticker": asset["ticker"], "name": asset["name"], "sector": asset["sector"],
        "price": asset.get("price"), "in_universe": True,
        "eliminated": asset["eliminated"],
        "eliminations": [e["reason"] for e in asset["eliminations"]],
        "scores": asset["scores"], "warnings": asset.get("warnings", []),
        "final_score": None, "reasons": {"strengths": [], "weaknesses": []}, "calc": [],
    }
    if not asset["eliminated"]:
        r = rank([asset], weights, limit=1)
        if r:
            base["final_score"] = r[0]["final_score"]
            base["reasons"] = r[0]["reasons"]
            base["calc"] = r[0]["calc"]
    return base


class RankingPayload(BaseModel):
    weights: dict[str, float] = Field(
        ..., description="Pesos das 5 dimensões (valor, qualidade, dividendos, estabilidade, momentum)",
        json_schema_extra={"example": WEIGHT_VECTORS["renda"]},
    )
    limit: int = 10
    sector_cap: int | None = Field(2, description="Máximo de ações do mesmo setor (diversificação)")


@app.get("/api/health", tags=["infra"])
def health() -> dict:
    snap = load_latest()
    return {
        "status": "ok",
        "version": __version__,
        "database_configured": bool(os.getenv("DATABASE_URL")),
        "scores_available": snap is not None,
        "scores_as_of": snap.get("as_of") if snap else None,
    }


# --- Perfil -------------------------------------------------------------------

@app.get("/api/questionnaire", tags=["perfil"])
def get_questionnaire() -> dict:
    """Perguntas do questionário de perfil (US03)."""
    return to_dict()


@app.post("/api/profile", tags=["perfil"])
def post_profile(payload: AnswersPayload) -> dict:
    """Classifica o perfil e devolve o vetor de pesos + as ações mais aderentes."""
    try:
        result = classify(payload.answers)
    except InvalidAnswersError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    snap = load_latest()
    if snap is not None:
        ranking = {
            "is_demo_data": False,
            "note": f"Scores calculados com dados de mercado de {snap.get('as_of')} "
                    f"(regras {snap.get('rule_version')}).",
            **_meta(snap),
            "assets": rank(snap["assets"], result.weight_vector, limit=8, sector_cap=2),
        }
    else:
        ranking = {
            "is_demo_data": True,
            "note": "Scores ilustrativos — rode o pipeline para gerar scores reais.",
            "assets": rank_demo_assets(result.weight_vector),
        }

    response = {
        "profile": result.to_dict(),
        "ranking": ranking,
        "disclaimer": DISCLAIMER,
        "persisted": False,
    }

    if payload.persist:
        try:
            from api.persistence import save_profile  # import tardio: opcional
            response["profile_id"] = save_profile(result, payload.answers)
            response["persisted"] = True
        except Exception as exc:  # nunca derruba a demonstração
            response["persist_error"] = f"{type(exc).__name__}: {exc}"

    return response


# --- Motor de score -------------------------------------------------------------

@app.get("/api/rankings", tags=["score"])
def get_rankings(vector: str = "equilibrio", limit: int = 10, sector_cap: int | None = None) -> dict:
    """Ranking das ações para uma das estratégias: renda, crescimento, equilibrio, preservacao."""
    if vector not in WEIGHT_VECTORS:
        raise HTTPException(422, f"Estratégia inválida. Use: {', '.join(WEIGHT_VECTORS)}")
    snap = _snapshot_or_404()
    weights = WEIGHT_VECTORS[vector]
    return {
        **_meta(snap),
        "vector": vector,
        "vector_label": WEIGHT_VECTOR_LABELS[vector],
        "weights": weights,
        "assets": rank(snap["assets"], weights, limit=limit, sector_cap=sector_cap),
        "disclaimer": DISCLAIMER,
    }


@app.post("/api/rankings", tags=["score"])
def post_rankings(payload: RankingPayload) -> dict:
    """Ranking para um vetor de pesos qualquer — o app envia o vetor salvo do perfil."""
    snap = _snapshot_or_404()
    return {
        **_meta(snap),
        "weights": payload.weights,
        "assets": rank(snap["assets"], payload.weights, limit=payload.limit,
                       sector_cap=payload.sector_cap),
        "disclaimer": DISCLAIMER,
    }


@app.post("/api/scores", tags=["score"])
def post_scores(payload: ScoresPayload) -> dict:
    """Score de ações específicas (ex.: as da carteira) para o vetor de pesos do usuário."""
    snap = _snapshot_or_404()
    by_ticker = {a["ticker"]: a for a in snap["assets"]}
    items = {}
    for t in payload.tickers:
        t = t.upper().strip()
        a = by_ticker.get(t)
        items[t] = _score_one(a, payload.weights) if a else {"ticker": t, "in_universe": False}
    return {**_meta(snap), "items": items, "disclaimer": DISCLAIMER}


@app.post("/api/search", tags=["score"])
def post_search(payload: SearchPayload) -> dict:
    """Pesquisa ações do universo por código ou nome, já com o score para o perfil."""
    snap = _snapshot_or_404()
    q = _norm(payload.q.strip())
    found = []
    for a in snap["assets"]:
        hay = _norm(a["ticker"] + " " + a["name"] + " " + a["sector"])
        if not q or q in hay:
            starts = _norm(a["ticker"]).startswith(q) or _norm(a["name"]).startswith(q)
            found.append((0 if starts else 1, a))
    found.sort(key=lambda x: (x[0], x[1]["ticker"]))
    results = [_score_one(a, payload.weights) for _, a in (found if not q else found[: payload.limit])]
    if not q:  # sem busca: lista o universo pelo score do perfil
        results.sort(key=lambda r: (r["final_score"] is None, -(r["final_score"] or 0)))
        results = results[: payload.limit]
    return {**_meta(snap), "query": payload.q, "results": results, "disclaimer": DISCLAIMER}


@app.get("/api/assets/{ticker}", tags=["score"])
def get_asset(ticker: str) -> dict:
    """Detalhe da ação: 5 scores, cada régua com valor, percentil e grupo de comparação."""
    snap = _snapshot_or_404()
    t = ticker.upper()
    asset = next((a for a in snap["assets"] if a["ticker"] == t), None)
    if asset is None:
        raise HTTPException(404, f"{t} não está no universo analisado.")
    ranked = {k: (rank([asset], w, limit=1) or [None])[0] if not asset["eliminated"] else None
              for k, w in WEIGHT_VECTORS.items()}
    return {**_meta(snap), "asset": asset,
            "strategy_scores": {k: r["final_score"] if r else None for k, r in ranked.items()},
            "strategy_calc": {k: r["calc"] if r else [] for k, r in ranked.items()},
            "strategy_weights": WEIGHT_VECTORS,
            "strategy_labels": WEIGHT_VECTOR_LABELS,
            "elimination_rules": {
                "E1": "Liquidez média diária (2 meses, Fundamentus) abaixo de R$ "
                      + f"{MIN_LIQUIDITY_BRL:,.0f}".replace(",", "."),
                "E2": "Patrimônio líquido negativo (Fundamentus)",
                "E6": f"Menos de {MIN_HISTORY_DAYS} pregões (~2 anos) de histórico de preços",
            },
            "disclaimer": DISCLAIMER}


# --- Histórico de preços ---------------------------------------------------------

#: Janela (em dias corridos) de cada período do gráfico.
HISTORY_RANGES = {"1m": 31, "3m": 92, "6m": 183, "1a": 366, "5a": 1830}
HISTORY_MAX_POINTS = 260
_HISTORY_TTL = 600  # segundos
_history_cache: dict[str, tuple[float, dict]] = {}


def _yahoo_chart_cached(ticker: str) -> dict | None:
    import time
    from eren_ml.pipeline.sources import fetch_yahoo_chart

    hit = _history_cache.get(ticker)
    if hit and time.time() - hit[0] < _HISTORY_TTL:
        return hit[1]
    chart = fetch_yahoo_chart(ticker, timeout=15, retries=1)
    if chart:
        _history_cache[ticker] = (time.time(), chart)
    return chart


@app.get("/api/assets/{ticker}/history", tags=["score"])
def get_asset_history(ticker: str, range: str = "1a") -> dict:
    """Cotação atual e histórico de fechamento (Yahoo Finance, 5 anos diários, cache de 10 min)."""
    from datetime import datetime, timedelta, timezone

    if range not in HISTORY_RANGES:
        raise HTTPException(422, f"Período inválido. Use: {', '.join(HISTORY_RANGES)}")
    t = ticker.upper()
    chart = _yahoo_chart_cached(t)
    if not chart:
        raise HTTPException(502, f"Não foi possível obter o histórico de {t} no Yahoo Finance agora.")

    meta = chart.get("meta", {})
    closes = (chart.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    serie = [
        (datetime.fromtimestamp(ts, tz=timezone.utc).date(), float(c))
        for ts, c in zip(chart.get("timestamp") or [], closes) if c is not None
    ]
    if len(serie) < 2:
        raise HTTPException(404, f"Sem histórico de preços para {t}.")

    price = meta.get("regularMarketPrice") or serie[-1][1]
    market_time = meta.get("regularMarketTime")
    market_date = (datetime.fromtimestamp(market_time, tz=timezone.utc).date()
                   if market_time else serie[-1][0])
    # fechamento anterior = último pregão antes do pregão da cotação atual
    previous = next((c for d, c in reversed(serie) if d < market_date), serie[-2][1])

    inicio = serie[-1][0] - timedelta(days=HISTORY_RANGES[range])
    janela = [(d, c) for d, c in serie if d >= inicio]
    passo = max(1, -(-len(janela) // HISTORY_MAX_POINTS))  # divisão para cima
    pontos = janela[::passo]
    if pontos[-1] != janela[-1]:
        pontos.append(janela[-1])

    return {
        "ticker": t,
        "range": range,
        "currency": meta.get("currency", "BRL"),
        "price": price,
        "previous_close": previous,
        "change": price - previous,
        "change_pct": (price / previous - 1) * 100 if previous else None,
        "market_time": datetime.fromtimestamp(market_time, tz=timezone.utc).isoformat() if market_time else None,
        "source": "Yahoo Finance (cotação com atraso de até 15 minutos)",
        "points": [{"date": d.isoformat(), "close": round(c, 4)} for d, c in pontos],
    }


@app.get("/api/scores/meta", tags=["score"])
def get_scores_meta() -> dict:
    """Data de referência, fontes, ações eliminadas e réguas ainda indisponíveis."""
    snap = _snapshot_or_404()
    return {**_meta(snap), "sources": snap.get("sources"),
            "eliminated": snap.get("eliminated"), "data_quality": snap.get("data_quality")}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def demo_page() -> str:
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
