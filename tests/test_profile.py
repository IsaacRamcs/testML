"""Testes do classificador de perfil (US03)."""
import pytest

from eren_ml.profile import MAX_POINTS, classify, classify_risk, compute_risk_score
from eren_ml.profile.classifier import InvalidAnswersError
from eren_ml.profile.weights import WEIGHT_VECTORS, score_asset

BASE = {
    "q1_idade": "31_45", "q2_percentual_renda": "15_30", "q3_reserva": "3_6m",
    "q4_horizonte": "3_10a", "q5_reacao_queda": "mantenho",
    "q6_experiencia": "fundos_etf", "q7_conhecimento": "intermediario",
    "q8_fatia_patrimonio": "10_30", "q9_preferencia": "equilibrio",
    "q10_dependentes": "uma", "q11_estabilidade_renda": "estavel",
    "q12_objetivo": "equilibrio",
}


def answers(**over):
    return {**BASE, **over}


# --- pontuação e classificação ------------------------------------------------

def test_max_points_consistente():
    assert MAX_POINTS == 40


def test_perfil_conservador():
    a = answers(
        q1_idade="mais_60", q2_percentual_renda="menos_5", q3_reserva="menos_3m",
        q4_horizonte="1_3a", q5_reacao_queda="vendo_tudo", q6_experiencia="nenhuma",
        q7_conhecimento="nenhum", q8_fatia_patrimonio="menos_10",
        q9_preferencia="preservar", q10_dependentes="varias",
        q11_estabilidade_renda="instavel", q12_objetivo="preservacao",
    )
    r = classify(a)
    assert r.risk_class == "conservador"
    assert r.weight_vector_key == "preservacao"
    assert r.weight_vector["estabilidade"] == 0.35


def test_perfil_arrojado():
    a = answers(
        q1_idade="ate_30", q2_percentual_renda="mais_30", q3_reserva="mais_6m",
        q4_horizonte="mais_10a", q5_reacao_queda="compro_mais",
        q6_experiencia="derivativos", q7_conhecimento="avancado",
        q8_fatia_patrimonio="mais_60", q9_preferencia="maximo_retorno",
        q10_dependentes="nenhuma", q11_estabilidade_renda="muito_estavel",
        q12_objetivo="crescimento",
    )
    r = classify(a)
    assert r.risk_score == MAX_POINTS
    assert r.risk_class == "arrojado"
    assert r.weight_vector_key == "crescimento"
    assert r.weight_vector["momentum"] == 0.30


def test_fronteiras_de_classificacao():
    assert classify_risk(0) == "conservador"
    assert classify_risk(13) == "conservador"
    assert classify_risk(14) == "moderado"
    assert classify_risk(26) == "moderado"
    assert classify_risk(27) == "arrojado"


def test_breakdown_soma_o_total():
    total, breakdown = compute_risk_score(BASE)
    assert total == sum(breakdown.values())
    assert "q12_objetivo" not in breakdown  # objetivo não pontua


# --- travas de segurança ------------------------------------------------------

def test_trava_sem_reserva_limita_a_conservador():
    a = answers(
        q1_idade="ate_30", q3_reserva="nao", q5_reacao_queda="compro_mais",
        q6_experiencia="derivativos", q8_fatia_patrimonio="mais_60",
        q9_preferencia="maximo_retorno", q12_objetivo="crescimento",
    )
    r = classify(a)
    assert r.risk_class == "conservador"
    assert any(f.code == "sem_reserva_emergencia" for f in r.safety_flags)


def test_trava_horizonte_curto_bloqueia_recomendacoes():
    r = classify(answers(q4_horizonte="menos_1a"))
    assert r.can_receive_recommendations is False
    assert any(f.blocks_recommendations for f in r.safety_flags)


def test_divergencia_objetivo_agressivo_com_perfil_moderado():
    r = classify(answers(q12_objetivo="crescimento"))
    assert r.risk_class == "moderado"
    assert r.objective_divergence is True
    assert r.weight_vector_key == "equilibrio"


# --- o dilema do perfil: mesma ação, perfis diferentes ------------------------

def test_mesma_acao_pontua_diferente_por_perfil():
    """TAEE11-like: ótima para renda, mediana para crescimento."""
    acao = {"valor": 55, "qualidade": 78, "dividendos": 92, "estabilidade": 84, "momentum": 41}
    renda = score_asset(acao, WEIGHT_VECTORS["renda"])
    crescimento = score_asset(acao, WEIGHT_VECTORS["crescimento"])
    assert renda > crescimento + 10


def test_pesos_somam_um():
    for key, vector in WEIGHT_VECTORS.items():
        assert round(sum(vector.values()), 6) == 1.0, key


def test_dimensao_ausente_redistribui_peso():
    completo = {"valor": 80, "qualidade": 80, "dividendos": 80, "estabilidade": 80, "momentum": 80}
    parcial = {**completo, "dividendos": None}
    assert score_asset(parcial, WEIGHT_VECTORS["renda"]) == 80.0


# --- validação ----------------------------------------------------------------

def test_resposta_faltando():
    a = answers()
    del a["q5_reacao_queda"]
    with pytest.raises(InvalidAnswersError, match="q5_reacao_queda"):
        classify(a)


def test_opcao_invalida():
    with pytest.raises(InvalidAnswersError, match="Opção inválida"):
        classify(answers(q1_idade="opcao_que_nao_existe"))
