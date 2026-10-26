"""Testes unitários do perfil do investidor (US03).

Requisitos cobertos: RN-003, RN-011, RN-012 e as regras do README
(pontuação 0–40, fronteiras 13/14 e 26/27, travas de segurança, divergência).
"""
import pytest

from apoio_unit import (ARROJADO, CONSERVADOR, FRONTEIRA_13, FRONTEIRA_14, FRONTEIRA_26,
                        FRONTEIRA_27, MAXIMO, MINIMO, MODERADO)
from eren_ml.profile import (MAX_POINTS, QUESTIONS, classify, classify_risk,
                             compute_risk_score, to_dict)
from eren_ml.profile.classifier import InvalidAnswersError
from eren_ml.profile.weights import PROFILE_MATRIX, WEIGHT_VECTORS

pytestmark = pytest.mark.unit


# --- Fronteiras de classify_risk (README: 13/14 e 26/27) -------------------------

@pytest.mark.parametrize("pontos, esperado", [
    (0, "conservador"), (1, "conservador"), (12, "conservador"), (13, "conservador"),
    (14, "moderado"), (15, "moderado"), (25, "moderado"), (26, "moderado"),
    (27, "arrojado"), (28, "arrojado"), (40, "arrojado"),
])
def test_ut_per_01_classify_risk_bordas(pontos, esperado):
    """TC-ML-UT-01 — README: 0–13 conservador, 14–26 moderado, 27–40 arrojado."""
    assert classify_risk(pontos) == esperado


@pytest.mark.parametrize("respostas, pontos, classe", [
    (FRONTEIRA_13, 13, "conservador"),
    (FRONTEIRA_14, 14, "moderado"),
    (FRONTEIRA_26, 26, "moderado"),
    (FRONTEIRA_27, 27, "arrojado"),
])
def test_ut_per_02_fronteiras_pelo_questionario(respostas, pontos, classe):
    """TC-ML-UT-02 — as fronteiras valem também quando a pontuação vem das respostas."""
    r = classify(respostas)
    assert r.risk_score == pontos
    assert r.risk_class == classe


# --- Pontuação mínima e máxima (README: 0 a 40) ----------------------------------

def test_ut_per_03_pontuacao_maxima_e_40():
    """TC-ML-UT-03 — maior opção em todas as perguntas = 40 pontos, arrojado."""
    assert MAX_POINTS == 40
    total, _ = compute_risk_score(MAXIMO)
    assert total == 40
    assert classify(MAXIMO).risk_class == "arrojado"


def test_ut_per_04_pontuacao_minima_dentro_da_escala():
    """TC-ML-UT-04 — menor opção em todas as perguntas fica na escala 0–40 e é conservador.

    Observação OBS-01 (DEFEITOS.md): q1, q2 e q8 não têm opção de 0 ponto, então a
    menor pontuação alcançável é 3. A escala 0–40 do README é respeitada.
    """
    total, breakdown = compute_risk_score(MINIMO)
    assert 0 <= total <= 40
    minimo_teorico = sum(min(o.points for o in q.options) for q in QUESTIONS if q.scores)
    assert total == minimo_teorico
    assert all(v >= 0 for v in breakdown.values())
    assert classify(MINIMO).risk_class == "conservador"
    assert classify_risk(0) == "conservador"


def test_ut_per_05_breakdown_soma_total_e_objetivo_nao_pontua():
    """TC-ML-UT-05 — detalhamento por pergunta soma o total; q12 (objetivo) não pontua."""
    for respostas in (CONSERVADOR, MODERADO, ARROJADO, MAXIMO, MINIMO):
        total, breakdown = compute_risk_score(respostas)
        assert total == sum(breakdown.values())
        assert "q12_objetivo" not in breakdown
        assert len(breakdown) == 11


# --- Perfis típicos (RN-003) -------------------------------------------------------

@pytest.mark.parametrize("respostas, classe", [
    (CONSERVADOR, "conservador"), (MODERADO, "moderado"), (ARROJADO, "arrojado"),
])
def test_ut_per_06_perfis_tipicos(respostas, classe):
    """TC-ML-UT-06 — RN-003: respostas típicas geram a classe esperada."""
    r = classify(respostas)
    assert r.risk_class == classe
    assert r.can_receive_recommendations is True
    assert r.safety_flags == []


# --- Travas de segurança (README / RN-011) -----------------------------------------

def test_ut_per_07_trava_sem_reserva_isolada():
    """TC-ML-UT-07 — sem reserva de emergência limita a conservador (não bloqueia)."""
    r = classify({**ARROJADO, "q3_reserva": "nao", "q12_objetivo": "renda"})
    assert r.risk_class == "conservador"
    codigos = [f.code for f in r.safety_flags]
    assert codigos == ["sem_reserva_emergencia"]
    assert r.can_receive_recommendations is True


def test_ut_per_08_trava_horizonte_curto_isolada():
    """TC-ML-UT-08 — RN-011: horizonte < 1 ano bloqueia sugestões de compra."""
    r = classify({**ARROJADO, "q4_horizonte": "menos_1a", "q12_objetivo": "renda"})
    assert r.can_receive_recommendations is False
    bloqueios = [f for f in r.safety_flags if f.blocks_recommendations]
    assert [f.code for f in bloqueios] == ["horizonte_curto"]


def test_ut_per_09_travas_combinadas():
    """TC-ML-UT-09 — as duas travas juntas: conservador e recomendações bloqueadas."""
    r = classify({**ARROJADO, "q3_reserva": "nao", "q4_horizonte": "menos_1a",
                  "q12_objetivo": "renda"})
    codigos = {f.code for f in r.safety_flags}
    assert {"sem_reserva_emergencia", "horizonte_curto"} <= codigos
    assert r.risk_class == "conservador"
    assert r.can_receive_recommendations is False


@pytest.mark.parametrize("horizonte", ["1_3a", "3_10a", "mais_10a"])
def test_ut_per_10_horizonte_a_partir_de_1_ano_nao_bloqueia(horizonte):
    """TC-ML-UT-10 — RN-011 (fronteira): horizonte >= 1 ano não aciona o bloqueio."""
    r = classify({**MODERADO, "q4_horizonte": horizonte})
    assert r.can_receive_recommendations is True
    assert not any(f.blocks_recommendations for f in r.safety_flags)


# --- Divergência de objetivo (README) ----------------------------------------------

@pytest.mark.parametrize("respostas, classe", [(CONSERVADOR, "conservador"), (MODERADO, "moderado")])
def test_ut_per_11_divergencia_crescimento_sem_capacidade(respostas, classe):
    """TC-ML-UT-11 — objetivo crescimento sem capacidade de risco: divergência e vetor rebaixado."""
    r = classify({**respostas, "q12_objetivo": "crescimento"})
    assert r.risk_class == classe
    assert r.objective_divergence is True
    assert r.weight_vector_key != "crescimento"
    assert any(f.code == "objetivo_divergente" for f in r.safety_flags)


def test_ut_per_12_sem_divergencia_quando_arrojado_quer_crescimento():
    """TC-ML-UT-12 — arrojado com objetivo crescimento: sem divergência."""
    r = classify(ARROJADO)
    assert r.objective_divergence is False
    assert r.weight_vector_key == "crescimento"


# --- RN-012: recomendação não contradiz o perfil de risco --------------------------

@pytest.mark.parametrize("objetivo", ["renda", "crescimento", "equilibrio", "preservacao"])
@pytest.mark.parametrize("classe", ["conservador", "moderado"])
def test_ut_per_13_vetor_nunca_mais_agressivo_que_o_perfil(classe, objetivo):
    """TC-ML-UT-13 — RN-012: conservador/moderado nunca recebem o vetor de crescimento,
    e o vetor aplicado nunca pesa momentum acima de estabilidade."""
    chave = PROFILE_MATRIX[(classe, objetivo)]
    assert chave != "crescimento"
    pesos = WEIGHT_VECTORS[chave]
    assert pesos["estabilidade"] >= pesos["momentum"]


def test_ut_per_14_matriz_cobre_todas_as_combinacoes():
    """TC-ML-UT-14 — toda combinação classe × objetivo tem um vetor definido."""
    for classe in ("conservador", "moderado", "arrojado"):
        for objetivo in ("renda", "crescimento", "equilibrio", "preservacao"):
            assert PROFILE_MATRIX[(classe, objetivo)] in WEIGHT_VECTORS


# --- Validação das respostas --------------------------------------------------------

def test_ut_per_15_resposta_faltando():
    """TC-ML-UT-15 — validação: resposta faltando é rejeitada citando a pergunta."""
    a = dict(MODERADO)
    del a["q9_preferencia"]
    with pytest.raises(InvalidAnswersError, match="q9_preferencia"):
        classify(a)


def test_ut_per_16_pergunta_desconhecida():
    """TC-ML-UT-16 — validação: pergunta fora do questionário é rejeitada."""
    with pytest.raises(InvalidAnswersError, match="Pergunta desconhecida"):
        classify({**MODERADO, "q99_inexistente": "x"})


def test_ut_per_17_opcao_invalida():
    """TC-ML-UT-17 — validação: opção inexistente é rejeitada."""
    with pytest.raises(InvalidAnswersError, match="Opção inválida"):
        classify({**MODERADO, "q3_reserva": "talvez"})


# --- Questionário ------------------------------------------------------------------

def test_ut_per_18_questionario_publico_sem_pontos():
    """TC-ML-UT-18 — 12 perguntas, versão presente e nenhuma opção expõe pontos."""
    q = to_dict()
    assert q["version"]
    assert q["max_points"] == 40
    assert len(q["questions"]) == 12
    assert len({p["id"] for p in q["questions"]}) == 12
    for p in q["questions"]:
        for o in p["options"]:
            assert set(o) == {"value", "label"}


def test_ut_per_19_versao_com_pontos_uso_interno():
    """TC-ML-UT-19 — a versão interna (com pontos) existe para documentação do TCC."""
    from eren_ml.profile.questionnaire import to_dict_with_points
    q = to_dict_with_points()
    assert all("points" in o for p in q["questions"] for o in p["options"])


def test_ut_per_20_to_dict_serializa_flags():
    """TC-ML-UT-20 — serialização do perfil: travas como lista e vetor com as 5 dimensões."""
    d = classify({**MODERADO, "q3_reserva": "nao"}).to_dict()
    assert isinstance(d["safety_flags"], list)
    assert d["safety_flags"][0]["code"] == "sem_reserva_emergencia"
    assert set(d["weight_vector"]) == {"valor", "qualidade", "dividendos", "estabilidade", "momentum"}


# --- Determinismo ------------------------------------------------------------------

def test_ut_per_21_determinismo_classificacao():
    """TC-ML-UT-21 — mesma entrada, mesma saída (100 execuções)."""
    primeira = classify(ARROJADO).to_dict()
    for _ in range(100):
        assert classify(dict(ARROJADO)).to_dict() == primeira
