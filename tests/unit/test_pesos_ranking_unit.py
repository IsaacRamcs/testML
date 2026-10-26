"""Testes unitários dos vetores de peso, do score personalizado e do ranking.

Requisitos cobertos: RN-003 (mesma ação, scores diferentes por perfil),
regra do README "pesos das 5 dimensões somam 1", score 0–100, ranking
ordenado com limit e sector_cap, ações eliminadas fora do ranking.
"""
import random

import pytest

from apoio_unit import DIMENSOES, ativo
from eren_ml.profile.demo_assets import DEMO_ASSETS, rank_demo_assets
from eren_ml.profile.weights import WEIGHT_VECTORS, resolve_weight_vector, score_asset
from eren_ml.scoring.ranking import contributions, explain, rank

pytestmark = pytest.mark.unit


# --- Vetores de peso -----------------------------------------------------------------

@pytest.mark.parametrize("chave", sorted(WEIGHT_VECTORS))
def test_ut_pes_01_vetor_soma_um_e_tem_as_5_dimensoes(chave):
    """TC-ML-UT-22 — README: os pesos das 5 dimensões somam 1."""
    vetor = WEIGHT_VECTORS[chave]
    assert set(vetor) == set(DIMENSOES)
    assert sum(vetor.values()) == pytest.approx(1.0, abs=1e-9)
    assert all(0 <= p <= 1 for p in vetor.values())


def test_ut_pes_02_resolve_devolve_copia():
    """Alterar o vetor devolvido não pode corromper a tabela global de pesos."""
    _, pesos, _ = resolve_weight_vector("moderado", "renda")
    pesos["valor"] = 99
    assert WEIGHT_VECTORS["renda"]["valor"] == 0.15


# --- score_asset ----------------------------------------------------------------------

def test_ut_pes_03_score_extremos():
    """TC-ML-UT-23 — notas todas 0 dão 0; todas 100 dão 100, em qualquer vetor."""
    for pesos in WEIGHT_VECTORS.values():
        assert score_asset({d: 0 for d in DIMENSOES}, pesos) == 0
        assert score_asset({d: 100 for d in DIMENSOES}, pesos) == 100


def test_ut_pes_04_score_sempre_entre_0_e_100():
    """TC-ML-UT-24 — 2.000 vetores de notas aleatórias (semente fixa): sempre em 0..100."""
    rnd = random.Random(20261026)
    for _ in range(500):
        notas = {d: rnd.uniform(0, 100) for d in DIMENSOES}
        for pesos in WEIGHT_VECTORS.values():
            assert 0 <= score_asset(notas, pesos) <= 100


def test_ut_pes_05_dimensao_ausente_redistribui_peso():
    """TC-ML-UT-25 — dimensão ausente (None) tem o peso redistribuído entre as demais."""
    notas = {"valor": 80, "qualidade": 60, "dividendos": None, "estabilidade": 40, "momentum": 20}
    pesos = WEIGHT_VECTORS["renda"]
    presentes = {d: n for d, n in notas.items() if n is not None}
    esperado = sum(n * pesos[d] for d, n in presentes.items()) / sum(pesos[d] for d in presentes)
    obtido = score_asset(notas, pesos)
    assert obtido == pytest.approx(esperado, abs=0.01)
    assert 0 <= obtido <= 100


def test_ut_pes_06_dimensao_ausente_por_chave_faltando():
    notas = {"valor": 70, "qualidade": 70}
    assert score_asset(notas, WEIGHT_VECTORS["equilibrio"]) == 70


def test_ut_pes_07_todas_ausentes_gera_erro():
    with pytest.raises(ValueError):
        score_asset({d: None for d in DIMENSOES}, WEIGHT_VECTORS["renda"])


def test_ut_pes_08_mesma_acao_score_diferente_por_perfil():
    """TC-ML-UT-26 — RN-003: a mesma ação recebe scores diferentes conforme o perfil."""
    pagadora = {"valor": 50, "qualidade": 70, "dividendos": 95, "estabilidade": 85, "momentum": 20}
    crescimento = {"valor": 40, "qualidade": 90, "dividendos": 10, "estabilidade": 40, "momentum": 95}
    s_renda = score_asset(pagadora, WEIGHT_VECTORS["renda"])
    s_cresc = score_asset(pagadora, WEIGHT_VECTORS["crescimento"])
    assert s_renda != s_cresc
    assert s_renda > s_cresc
    assert score_asset(crescimento, WEIGHT_VECTORS["crescimento"]) > \
        score_asset(crescimento, WEIGHT_VECTORS["renda"])


@pytest.mark.xfail(strict=True, reason="DEF-03: score_asset aceita peso negativo e devolve score fora de 0–100")
def test_ut_pes_10_peso_negativo_nao_gera_score_fora_da_faixa():
    """TC-ML-UT-40 — README (score 0–100, pesos somam 1): vetor com peso negativo deve ser
    rejeitado (ValueError) ou, no mínimo, não produzir score fora de 0–100."""
    notas = {"valor": 0, "qualidade": 100, "dividendos": 100, "estabilidade": 100, "momentum": 100}
    pesos = {"valor": -1, "qualidade": 0.5, "dividendos": 0.5, "estabilidade": 0.5, "momentum": 0.5}
    try:
        s = score_asset(notas, pesos)
    except ValueError:
        return
    assert 0 <= s <= 100, f"score={s}"


@pytest.mark.xfail(strict=True, raises=ZeroDivisionError,
                   reason="DEF-02: vetor de pesos todo zero causa ZeroDivisionError (HTTP 500 na API)")
def test_ut_pes_11_pesos_zerados_sao_rejeitados_com_erro_de_validacao():
    """TC-ML-UT-41 — README (pesos somam 1): vetor todo zero é inválido e deve gerar ValueError
    (mesmo tratamento de "nenhuma dimensão disponível"), não um erro aritmético."""
    with pytest.raises(ValueError):
        score_asset({d: 50 for d in DIMENSOES}, {d: 0 for d in DIMENSOES})


def test_ut_pes_09_determinismo_score():
    notas = {"valor": 33.3, "qualidade": 66.6, "dividendos": 12.1, "estabilidade": 90, "momentum": 45}
    resultados = {score_asset(dict(notas), WEIGHT_VECTORS["equilibrio"]) for _ in range(100)}
    assert len(resultados) == 1


# --- Ranking --------------------------------------------------------------------------

def _universo():
    return [
        ativo("AAA3", "Energia", dividendos=95, estabilidade=90, momentum=10),
        ativo("BBB3", "Energia", dividendos=90, estabilidade=85, momentum=15),
        ativo("CCC3", "Energia", dividendos=85, estabilidade=80, momentum=20),
        ativo("DDD3", "Tecnologia", dividendos=10, estabilidade=30, momentum=95, qualidade=90),
        ativo("EEE3", "Tecnologia", dividendos=15, estabilidade=35, momentum=90, qualidade=85),
        ativo("FFF3", "Varejo", dividendos=40, estabilidade=40, momentum=40),
        ativo("ZZZ3", "Varejo", eliminado=True, valor=100, qualidade=100, dividendos=100,
              estabilidade=100, momentum=100),
    ]


def test_ut_rank_01_ordenado_decrescente_e_posicoes():
    """TC-ML-UT-27 — ranking ordenado pelo score final, com posição 1..n."""
    r = rank(_universo(), WEIGHT_VECTORS["renda"], limit=None)
    finais = [a["final_score"] for a in r]
    assert finais == sorted(finais, reverse=True)
    assert [a["position"] for a in r] == list(range(1, len(r) + 1))


def test_ut_rank_02_eliminada_nunca_entra():
    """TC-ML-UT-28 — ação eliminada não entra no ranking, mesmo com notas máximas."""
    r = rank(_universo(), WEIGHT_VECTORS["equilibrio"], limit=None)
    assert "ZZZ3" not in [a["ticker"] for a in r]
    assert len(r) == 6


def test_ut_rank_03_sem_nenhuma_nota_fica_fora():
    vazio = ativo("VAZ3")
    vazio["scores"] = {d: None for d in DIMENSOES}
    r = rank(_universo() + [vazio], WEIGHT_VECTORS["renda"], limit=None)
    assert "VAZ3" not in [a["ticker"] for a in r]


@pytest.mark.parametrize("limite", [1, 3, 5])
def test_ut_rank_04_respeita_limit(limite):
    """TC-ML-UT-29 — o ranking devolve no máximo `limit` ações."""
    r = rank(_universo(), WEIGHT_VECTORS["renda"], limit=limite)
    assert len(r) == limite


def test_ut_rank_05_limit_maior_que_universo():
    r = rank(_universo(), WEIGHT_VECTORS["renda"], limit=1000)
    assert len(r) == 6


@pytest.mark.parametrize("cap", [1, 2])
def test_ut_rank_06_respeita_sector_cap(cap):
    """TC-ML-UT-30 — no máximo `sector_cap` ações do mesmo setor."""
    r = rank(_universo(), WEIGHT_VECTORS["renda"], limit=None, sector_cap=cap)
    por_setor = {}
    for a in r:
        por_setor[a["sector"]] = por_setor.get(a["sector"], 0) + 1
    assert max(por_setor.values()) <= cap
    assert [a["position"] for a in r] == list(range(1, len(r) + 1))


def test_ut_rank_07_renda_prioriza_dividendos_crescimento_prioriza_momentum():
    """TC-ML-UT-31 — RN-003: os perfis ordenam o mesmo universo de formas diferentes."""
    renda = rank(_universo(), WEIGHT_VECTORS["renda"], limit=None)
    cresc = rank(_universo(), WEIGHT_VECTORS["crescimento"], limit=None)
    assert renda[0]["ticker"] == "AAA3"
    assert cresc[0]["ticker"] in ("DDD3", "EEE3")
    assert [a["ticker"] for a in renda] != [a["ticker"] for a in cresc]


def test_ut_rank_08_contribuicoes_somam_score_final():
    """A decomposição (nota × peso efetivo) reproduz o score final."""
    for a in rank(_universo(), WEIGHT_VECTORS["equilibrio"], limit=None):
        soma = sum(c["contribution"] for c in a["calc"] if c["contribution"] is not None)
        assert soma == pytest.approx(a["final_score"], abs=0.05)


def test_ut_rank_09_contribuicoes_com_dimensao_ausente():
    calc = contributions({"valor": 80, "qualidade": None, "dividendos": 60,
                          "estabilidade": 40, "momentum": 20}, WEIGHT_VECTORS["renda"])
    ausente = next(c for c in calc if c["dimension"] == "qualidade")
    assert ausente["contribution"] is None and ausente["weight_effective"] == 0
    assert sum(c["weight_effective"] for c in calc) == pytest.approx(1.0, abs=1e-3)


def test_ut_rank_10_explicacao_fortes_e_fracos():
    exp = explain({"valor": 10, "qualidade": 90, "dividendos": 95, "estabilidade": 20, "momentum": 50},
                  WEIGHT_VECTORS["renda"])
    assert [s["dimension"] for s in exp["strengths"]] == ["dividendos", "qualidade"]
    assert {w["dimension"] for w in exp["weaknesses"]} == {"valor", "estabilidade"}
    assert len(exp["strengths"]) <= 2


def test_ut_rank_11_determinismo_ranking():
    """TC-ML-UT-32 — mesma entrada, mesmo ranking."""
    a = rank(_universo(), WEIGHT_VECTORS["preservacao"], limit=None, sector_cap=2)
    for _ in range(20):
        assert rank(_universo(), WEIGHT_VECTORS["preservacao"], limit=None, sector_cap=2) == a


def test_ut_rank_12_demo_assets_ordenados():
    r = rank_demo_assets(WEIGHT_VECTORS["renda"])
    assert len(r) == len(DEMO_ASSETS)
    finais = [a["final_score"] for a in r]
    assert finais == sorted(finais, reverse=True)
    assert len(rank_demo_assets(WEIGHT_VECTORS["renda"], limit=2)) == 2
