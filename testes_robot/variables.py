"""Variáveis da suíte Robot do erenML.

BASE_URL pode ser sobrescrita na linha de comando, por exemplo:
    robot --variable BASE_URL:http://192.168.0.10:8000 --outputdir resultados testes_robot

Os conjuntos de respostas abaixo tiveram a pontuação somada a partir da
tabela de pontos de eren_ml/profile/questionnaire.py.
"""

BASE_URL = "http://127.0.0.1:8000"

#: RNF-002 — limite do percentil 95 em segundos e número de repetições.
LIMITE_P95_SEGUNDOS = 1.5
REPETICOES_DESEMPENHO = 20

#: Universo atual (data/snapshots/scores_latest.json): 50 ações, 49 elegíveis.
TICKER_EXISTENTE = "TAEE11"
TICKER_INEXISTENTE = "XXXX9"
TICKER_ELIMINADO = "BRKM5"

DIMENSOES = ["valor", "qualidade", "dividendos", "estabilidade", "momentum"]
VETORES = ["renda", "crescimento", "equilibrio", "preservacao"]

# Perfil tipicamente conservador — 6 pontos.
RESPOSTAS_CONSERVADOR = {
    "q1_idade": "mais_60", "q2_percentual_renda": "menos_5", "q3_reserva": "menos_3m",
    "q4_horizonte": "1_3a", "q5_reacao_queda": "vendo_tudo", "q6_experiencia": "nenhuma",
    "q7_conhecimento": "nenhum", "q8_fatia_patrimonio": "menos_10",
    "q9_preferencia": "preservar", "q10_dependentes": "varias",
    "q11_estabilidade_renda": "instavel", "q12_objetivo": "preservacao",
}

# Perfil tipicamente moderado — 22 pontos.
RESPOSTAS_MODERADO = {
    "q1_idade": "46_60", "q2_percentual_renda": "5_15", "q3_reserva": "3_6m",
    "q4_horizonte": "3_10a", "q5_reacao_queda": "mantenho", "q6_experiencia": "fundos_etf",
    "q7_conhecimento": "basico", "q8_fatia_patrimonio": "10_30",
    "q9_preferencia": "equilibrio", "q10_dependentes": "uma",
    "q11_estabilidade_renda": "media", "q12_objetivo": "equilibrio",
}

# Perfil tipicamente arrojado — 37 pontos.
RESPOSTAS_ARROJADO = {
    "q1_idade": "ate_30", "q2_percentual_renda": "mais_30", "q3_reserva": "mais_6m",
    "q4_horizonte": "mais_10a", "q5_reacao_queda": "compro_mais", "q6_experiencia": "acoes",
    "q7_conhecimento": "avancado", "q8_fatia_patrimonio": "30_60",
    "q9_preferencia": "maximo_retorno", "q10_dependentes": "nenhuma",
    "q11_estabilidade_renda": "estavel", "q12_objetivo": "crescimento",
}

# Fronteiras do README.
RESPOSTAS_13_PONTOS = {**RESPOSTAS_CONSERVADOR, "q4_horizonte": "3_10a",
                       "q5_reacao_queda": "mantenho", "q6_experiencia": "fundos_etf",
                       "q7_conhecimento": "basico"}
RESPOSTAS_14_PONTOS = {**RESPOSTAS_13_PONTOS, "q10_dependentes": "uma"}
RESPOSTAS_26_PONTOS = {
    "q1_idade": "31_45", "q2_percentual_renda": "15_30", "q3_reserva": "3_6m",
    "q4_horizonte": "3_10a", "q5_reacao_queda": "mantenho", "q6_experiencia": "fundos_etf",
    "q7_conhecimento": "intermediario", "q8_fatia_patrimonio": "10_30",
    "q9_preferencia": "equilibrio", "q10_dependentes": "uma",
    "q11_estabilidade_renda": "estavel", "q12_objetivo": "equilibrio",
}
RESPOSTAS_27_PONTOS = {**RESPOSTAS_26_PONTOS, "q10_dependentes": "nenhuma"}

# Cenários com travas de segurança (partem do arrojado, objetivo renda).
RESPOSTAS_SEM_RESERVA = {**RESPOSTAS_ARROJADO, "q3_reserva": "nao", "q12_objetivo": "renda"}
RESPOSTAS_HORIZONTE_CURTO = {**RESPOSTAS_ARROJADO, "q4_horizonte": "menos_1a", "q12_objetivo": "renda"}

# Divergência: perfil moderado declarando objetivo de crescimento.
RESPOSTAS_MODERADO_QUER_CRESCIMENTO = {**RESPOSTAS_MODERADO, "q12_objetivo": "crescimento"}

# Vetores customizados para POST /api/rankings.
PESOS_SO_DIVIDENDOS = {"valor": 0.0, "qualidade": 0.0, "dividendos": 1.0,
                       "estabilidade": 0.0, "momentum": 0.0}
PESOS_NAO_SOMAM_UM = {"valor": 5, "qualidade": 5, "dividendos": 5, "estabilidade": 5, "momentum": 5}
PESOS_ZERADOS = {"valor": 0, "qualidade": 0, "dividendos": 0, "estabilidade": 0, "momentum": 0}
PESOS_NEGATIVOS = {"valor": -1, "qualidade": 0.5, "dividendos": 0.5, "estabilidade": 0.5, "momentum": 0.5}
PESOS_DIMENSAO_DESCONHECIDA = {"dimensao_inexistente": 1}
