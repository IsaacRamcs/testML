"""Vetores de score ILUSTRATIVOS para demonstração.

ATENÇÃO: estes números NÃO vêm do motor de score — são valores plausíveis,
escritos à mão, para demonstrar como o mesmo conjunto de ações é ranqueado de
formas diferentes conforme o perfil do investidor.

Serão substituídos pela tabela `market.scores_daily` assim que o pipeline de
dados (semanas 1-2) e o motor de score (semanas 4-5) estiverem prontos.
"""
from __future__ import annotations

from .weights import score_asset

IS_DEMO_DATA = True

DEMO_ASSETS: list[dict] = [
    {
        "ticker": "TAEE11", "name": "Taesa", "sector": "Energia Elétrica",
        "scores": {"valor": 55, "qualidade": 78, "dividendos": 92, "estabilidade": 84, "momentum": 41},
    },
    {
        "ticker": "WEGE3", "name": "WEG", "sector": "Bens Industriais",
        "scores": {"valor": 22, "qualidade": 95, "dividendos": 30, "estabilidade": 62, "momentum": 81},
    },
    {
        "ticker": "ITUB4", "name": "Itaú Unibanco", "sector": "Financeiro",
        "scores": {"valor": 68, "qualidade": 82, "dividendos": 74, "estabilidade": 71, "momentum": 66},
    },
    {
        "ticker": "PETR4", "name": "Petrobras", "sector": "Petróleo e Gás",
        "scores": {"valor": 88, "qualidade": 64, "dividendos": 86, "estabilidade": 35, "momentum": 52},
    },
    {
        "ticker": "MGLU3", "name": "Magazine Luiza", "sector": "Varejo",
        "scores": {"valor": 41, "qualidade": 28, "dividendos": 8, "estabilidade": 15, "momentum": 73},
    },
    {
        "ticker": "SBSP3", "name": "Sabesp", "sector": "Saneamento",
        "scores": {"valor": 59, "qualidade": 70, "dividendos": 48, "estabilidade": 76, "momentum": 69},
    },
]


def rank_demo_assets(weights: dict[str, float], limit: int = 6) -> list[dict]:
    """Ranqueia os ativos de demonstração com o vetor de pesos do usuário."""
    ranked = [
        {
            "ticker": a["ticker"],
            "name": a["name"],
            "sector": a["sector"],
            "scores": a["scores"],
            "final_score": score_asset(a["scores"], weights),
        }
        for a in DEMO_ASSETS
    ]
    ranked.sort(key=lambda a: a["final_score"], reverse=True)
    return ranked[:limit]
