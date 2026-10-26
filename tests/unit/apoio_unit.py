"""Dados de apoio compartilhados pelos testes unitários.

As pontuações indicadas nos comentários foram somadas a partir da tabela de
pontos de eren_ml/profile/questionnaire.py (fonte única da verdade do
questionário), não do resultado do classificador.
"""

# Perfil tipicamente conservador — 6 pontos.
CONSERVADOR = {
    "q1_idade": "mais_60", "q2_percentual_renda": "menos_5", "q3_reserva": "menos_3m",
    "q4_horizonte": "1_3a", "q5_reacao_queda": "vendo_tudo", "q6_experiencia": "nenhuma",
    "q7_conhecimento": "nenhum", "q8_fatia_patrimonio": "menos_10",
    "q9_preferencia": "preservar", "q10_dependentes": "varias",
    "q11_estabilidade_renda": "instavel", "q12_objetivo": "preservacao",
}

# Perfil tipicamente moderado — 22 pontos.
MODERADO = {
    "q1_idade": "46_60", "q2_percentual_renda": "5_15", "q3_reserva": "3_6m",
    "q4_horizonte": "3_10a", "q5_reacao_queda": "mantenho", "q6_experiencia": "fundos_etf",
    "q7_conhecimento": "basico", "q8_fatia_patrimonio": "10_30",
    "q9_preferencia": "equilibrio", "q10_dependentes": "uma",
    "q11_estabilidade_renda": "media", "q12_objetivo": "equilibrio",
}

# Perfil tipicamente arrojado — 37 pontos.
ARROJADO = {
    "q1_idade": "ate_30", "q2_percentual_renda": "mais_30", "q3_reserva": "mais_6m",
    "q4_horizonte": "mais_10a", "q5_reacao_queda": "compro_mais", "q6_experiencia": "acoes",
    "q7_conhecimento": "avancado", "q8_fatia_patrimonio": "30_60",
    "q9_preferencia": "maximo_retorno", "q10_dependentes": "nenhuma",
    "q11_estabilidade_renda": "estavel", "q12_objetivo": "crescimento",
}

# Fronteiras do README: 13 = conservador, 14 = moderado, 26 = moderado, 27 = arrojado.
FRONTEIRA_13 = {**CONSERVADOR, "q4_horizonte": "3_10a", "q5_reacao_queda": "mantenho",
                "q6_experiencia": "fundos_etf", "q7_conhecimento": "basico"}
FRONTEIRA_14 = {**FRONTEIRA_13, "q10_dependentes": "uma"}
FRONTEIRA_26 = {
    "q1_idade": "31_45", "q2_percentual_renda": "15_30", "q3_reserva": "3_6m",
    "q4_horizonte": "3_10a", "q5_reacao_queda": "mantenho", "q6_experiencia": "fundos_etf",
    "q7_conhecimento": "intermediario", "q8_fatia_patrimonio": "10_30",
    "q9_preferencia": "equilibrio", "q10_dependentes": "uma",
    "q11_estabilidade_renda": "estavel", "q12_objetivo": "equilibrio",
}
FRONTEIRA_27 = {**FRONTEIRA_26, "q10_dependentes": "nenhuma"}

# Maior opção de cada pergunta — 40 pontos (máximo do README).
MAXIMO = {
    "q1_idade": "ate_30", "q2_percentual_renda": "mais_30", "q3_reserva": "mais_6m",
    "q4_horizonte": "mais_10a", "q5_reacao_queda": "compro_mais",
    "q6_experiencia": "derivativos", "q7_conhecimento": "avancado",
    "q8_fatia_patrimonio": "mais_60", "q9_preferencia": "maximo_retorno",
    "q10_dependentes": "nenhuma", "q11_estabilidade_renda": "muito_estavel",
    "q12_objetivo": "crescimento",
}

# Menor opção de cada pergunta (aciona as duas travas de segurança).
MINIMO = {**CONSERVADOR, "q3_reserva": "nao", "q4_horizonte": "menos_1a"}

DIMENSOES = ("valor", "qualidade", "dividendos", "estabilidade", "momentum")


def ativo(ticker, setor="Setor A", eliminado=False, **scores):
    """Ativo no formato do snapshot (o mínimo que rank() consome)."""
    base = {d: 50.0 for d in DIMENSOES}
    base.update(scores)
    return {"ticker": ticker, "name": ticker, "sector": setor, "price": 10.0,
            "eliminated": eliminado, "scores": base, "warnings": []}
