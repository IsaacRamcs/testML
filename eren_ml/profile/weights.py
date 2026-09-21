"""Vetores de peso por perfil-objetivo (seção 6.7 da especificação).

O motor de score produz, para cada ação, um vetor objetivo de 5 dimensões
(valor, qualidade, dividendos, estabilidade, momentum). A personalização
acontece aqui: o score final do usuário é a média ponderada dessas dimensões
com os pesos abaixo.

É este mecanismo que resolve o dilema "a mesma ação é boa para um investidor
e ruim para outro" sem precisar de um modelo por perfil.
"""
from __future__ import annotations

DIMENSIONS = ("valor", "qualidade", "dividendos", "estabilidade", "momentum")

#: Vetores base. Cada um soma 1.0.
WEIGHT_VECTORS: dict[str, dict[str, float]] = {
    "preservacao": {
        "valor": 0.10, "qualidade": 0.25, "dividendos": 0.25,
        "estabilidade": 0.35, "momentum": 0.05,
    },
    "equilibrio": {
        "valor": 0.20, "qualidade": 0.25, "dividendos": 0.20,
        "estabilidade": 0.20, "momentum": 0.15,
    },
    "crescimento": {
        "valor": 0.25, "qualidade": 0.30, "dividendos": 0.05,
        "estabilidade": 0.10, "momentum": 0.30,
    },
    "renda": {
        "valor": 0.15, "qualidade": 0.25, "dividendos": 0.40,
        "estabilidade": 0.15, "momentum": 0.05,
    },
}

WEIGHT_VECTOR_LABELS: dict[str, str] = {
    "preservacao": "Preservação de capital",
    "equilibrio": "Equilíbrio",
    "crescimento": "Crescimento",
    "renda": "Renda / dividendos",
}

#: Matriz classe de risco × objetivo -> vetor de pesos aplicado.
#: Onde o objetivo declarado é mais agressivo do que a classe de risco suporta,
#: o sistema aplica o vetor mais conservador e registra uma divergência.
PROFILE_MATRIX: dict[tuple[str, str], str] = {
    # Conservador: nunca recebe o vetor de crescimento.
    ("conservador", "preservacao"): "preservacao",
    ("conservador", "equilibrio"): "preservacao",
    ("conservador", "renda"): "renda",
    ("conservador", "crescimento"): "equilibrio",
    # Moderado
    ("moderado", "preservacao"): "preservacao",
    ("moderado", "equilibrio"): "equilibrio",
    ("moderado", "renda"): "renda",
    ("moderado", "crescimento"): "equilibrio",
    # Arrojado
    ("arrojado", "preservacao"): "preservacao",
    ("arrojado", "equilibrio"): "equilibrio",
    ("arrojado", "renda"): "renda",
    ("arrojado", "crescimento"): "crescimento",
}

#: Combinações em que o objetivo foi "rebaixado" por incompatibilidade com o risco.
DIVERGENT_COMBINATIONS: set[tuple[str, str]] = {
    ("conservador", "crescimento"),
    ("moderado", "crescimento"),
}


def resolve_weight_vector(risk_class: str, objective: str) -> tuple[str, dict[str, float], bool]:
    """Retorna (chave_do_vetor, pesos, houve_divergencia)."""
    key = PROFILE_MATRIX[(risk_class, objective)]
    divergent = (risk_class, objective) in DIVERGENT_COMBINATIONS
    return key, dict(WEIGHT_VECTORS[key]), divergent


def score_asset(dimension_scores: dict[str, float], weights: dict[str, float]) -> float:
    """Aplica o vetor de pesos ao vetor de scores de uma ação (0-100).

    Dimensões ausentes têm seu peso redistribuído proporcionalmente entre as
    presentes, conforme a mecânica transversal da especificação.
    """
    present = {d: s for d, s in dimension_scores.items() if s is not None and d in weights}
    if not present:
        raise ValueError("Nenhuma dimensão disponível para pontuar o ativo.")
    total_weight = sum(weights[d] for d in present)
    return round(sum(present[d] * weights[d] for d in present) / total_weight, 2)
