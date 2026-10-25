"""Ranking personalizado: aplica o vetor de pesos do perfil aos scores.

O score de cada ação é objetivo e único; o que muda entre investidores é o
peso de cada dimensão. Ações eliminadas nunca entram no ranking.
"""
from __future__ import annotations

from ..profile.weights import DIMENSIONS, score_asset

DIM_LABEL = {
    "valor": "Valor",
    "qualidade": "Qualidade",
    "dividendos": "Dividendos",
    "estabilidade": "Estabilidade",
    "momentum": "Momentum",
}

STRENGTH = {
    "valor": "Preço atrativo em relação ao que a empresa entrega",
    "qualidade": "Empresa rentável e bem gerida",
    "dividendos": "Histórico consistente de proventos",
    "estabilidade": "Oscila menos que a média do mercado",
    "momentum": "Tendência de alta nos últimos meses",
}

WEAKNESS = {
    "valor": "Preço esticado em relação aos pares",
    "qualidade": "Rentabilidade abaixo dos pares do setor",
    "dividendos": "Proventos baixos ou irregulares",
    "estabilidade": "Oscilação acima da média",
    "momentum": "Tendência de queda recente",
}


#: Critérios dos motivos exibidos ao usuário.
STRENGTH_MIN_SCORE, STRENGTH_MIN_WEIGHT = 60, 0.10
WEAKNESS_MAX_SCORE, WEAKNESS_MIN_WEIGHT = 35, 0.15

CRITERIA = {
    "strength": (f"Ponto forte: dimensão com nota de {STRENGTH_MIN_SCORE} pontos ou mais e peso de "
                 f"pelo menos {STRENGTH_MIN_WEIGHT:.0%} no seu perfil (no máximo 2, as que mais contribuem)."),
    "weakness": (f"Ponto de atenção: dimensão com nota abaixo de {WEAKNESS_MAX_SCORE} pontos e peso de "
                 f"pelo menos {WEAKNESS_MIN_WEIGHT:.0%} no seu perfil."),
}


def explain(scores: dict[str, float | None], weights: dict[str, float]) -> dict:
    """Motivos legíveis: pontos fortes que mais pesam para ESTE perfil e alertas."""
    contrib = sorted(
        ((d, s * weights.get(d, 0)) for d, s in scores.items() if s is not None),
        key=lambda x: x[1], reverse=True,
    )
    strengths = [
        {"dimension": d, "score": scores[d], "text": STRENGTH[d]}
        for d, _ in contrib if scores[d] >= STRENGTH_MIN_SCORE and weights.get(d, 0) >= STRENGTH_MIN_WEIGHT
    ][:2]
    weaknesses = [
        {"dimension": d, "score": scores[d], "text": WEAKNESS[d]}
        for d in DIMENSIONS
        if scores.get(d) is not None and scores[d] < WEAKNESS_MAX_SCORE and weights.get(d, 0) >= WEAKNESS_MIN_WEIGHT
    ]
    return {"strengths": strengths, "weaknesses": weaknesses, "criteria": CRITERIA}


def contributions(scores: dict[str, float | None], weights: dict[str, float]) -> list[dict]:
    """Decomposição do score final: nota × peso efetivo de cada dimensão.

    É a mesma conta de score_asset: dimensões sem nota saem e o peso delas é
    redistribuído proporcionalmente entre as demais (peso efetivo).
    """
    present = [d for d in DIMENSIONS if scores.get(d) is not None and d in weights]
    total = sum(weights[d] for d in present)
    out = []
    for d in DIMENSIONS:
        s, w = scores.get(d), weights.get(d, 0.0)
        eff = (w / total) if (s is not None and total) else 0.0
        out.append({
            "dimension": d, "label": DIM_LABEL[d], "score": s, "weight": w,
            "weight_effective": round(eff, 4),
            "contribution": round(s * eff, 2) if s is not None else None,
        })
    return out


def rank(assets: list[dict], weights: dict[str, float], limit: int | None = 10,
         sector_cap: int | None = None) -> list[dict]:
    ranked = []
    for a in assets:
        if a.get("eliminated"):
            continue
        scores = a["scores"]
        if all(scores.get(d) is None for d in DIMENSIONS):
            continue
        final = score_asset({d: scores.get(d) for d in DIMENSIONS}, weights)
        ranked.append({
            "ticker": a["ticker"],
            "name": a["name"],
            "sector": a["sector"],
            "price": a.get("price"),
            "scores": {d: scores.get(d) for d in DIMENSIONS},
            "final_score": final,
            "reasons": explain(scores, weights),
            "calc": contributions(scores, weights),
            "warnings": a.get("warnings", []),
        })
    ranked.sort(key=lambda x: x["final_score"], reverse=True)

    if sector_cap:  # diversificação: no máximo N por setor no topo
        out, per_sector = [], {}
        for r in ranked:
            if per_sector.get(r["sector"], 0) < sector_cap:
                out.append(r)
                per_sector[r["sector"]] = per_sector.get(r["sector"], 0) + 1
        ranked = out

    for i, r in enumerate(ranked, 1):
        r["position"] = i
    return ranked[:limit] if limit else ranked
