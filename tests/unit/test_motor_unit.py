"""Testes unitários do motor de score (filtros eliminatórios, percentis, snapshot).

Requisitos cobertos (README): filtros eliminatórios E1 (liquidez < R$ 1 mi/dia),
E2 (patrimônio líquido negativo), E6 (< 2 anos de histórico); notas por
dimensão de 0 a 100; determinismo do cálculo.

Nenhum teste escreve em data/: o snapshot é reconstruído em memória a partir
dos arquivos brutos já salvos em data/raw/ (somente leitura).
"""
import json

import pytest

from eren_ml.scoring import engine, rules
from eren_ml.scoring.engine import eliminations, percentile_detail, percentile_score, score_universe, warnings
from eren_ml.scoring.indicators import build_indicators, payout_score
from eren_ml.scoring.snapshot import LATEST, build_snapshot, latest_raw, load_latest, save

pytestmark = pytest.mark.unit

ELEGIVEL = {"liquidity_brl": 50_000_000, "equity": 1_000_000_000, "history_days": 1200}


# --- Filtros eliminatórios ----------------------------------------------------------

def _codigos(ind):
    return [e["code"] for e in eliminations(ind)]


def test_ut_mot_01_elegivel_nao_e_eliminada():
    assert _codigos(ELEGIVEL) == []


@pytest.mark.parametrize("liquidez, eliminada", [
    (0, True), (999_999.99, True), (1_000_000, False), (1_000_001, False),
])
def test_ut_mot_02_filtro_e1_liquidez(liquidez, eliminada):
    """TC-ML-UT-33 — E1: liquidez média diária menor que R$ 1 milhão elimina."""
    assert ("E1" in _codigos({**ELEGIVEL, "liquidity_brl": liquidez})) is eliminada


@pytest.mark.parametrize("patrimonio, eliminada", [(-1, True), (-1e9, True), (0, False), (1, False)])
def test_ut_mot_03_filtro_e2_patrimonio_negativo(patrimonio, eliminada):
    """TC-ML-UT-34 — E2: patrimônio líquido negativo elimina."""
    assert ("E2" in _codigos({**ELEGIVEL, "equity": patrimonio})) is eliminada


@pytest.mark.parametrize("pregoes, eliminada", [(0, True), (252, True), (503, True), (504, False), (1248, False)])
def test_ut_mot_04_filtro_e6_historico(pregoes, eliminada):
    """TC-ML-UT-35 — E6: menos de 2 anos de histórico (2 × 252 = 504 pregões) elimina."""
    assert ("E6" in _codigos({**ELEGIVEL, "history_days": pregoes})) is eliminada


def test_ut_mot_05_filtros_combinados():
    ind = {"liquidity_brl": 10, "equity": -5, "history_days": 10}
    assert _codigos(ind) == ["E1", "E2", "E6"]


def test_ut_mot_06_limiares_documentados():
    assert rules.MIN_LIQUIDITY_BRL == 1_000_000
    assert rules.MIN_HISTORY_DAYS == 504


def test_ut_mot_07_alertas():
    w = warnings({"pl": -3, "payout": 1.5, "leverage": 3.0, "mdd_3y": 0.7})
    assert len(w) == 4
    assert warnings({"pl": 10, "payout": 0.5, "leverage": 1.0, "mdd_3y": 0.2}) == []


# --- Percentil -----------------------------------------------------------------------

def test_ut_mot_08_percentil_direcoes():
    pop = [1, 2, 3, 4, 5]
    assert percentile_score(5, pop, "higher") == 100
    assert percentile_score(1, pop, "higher") == 0
    assert percentile_score(1, pop, "lower") == 100
    assert percentile_score(3, pop, "higher") == 50


def test_ut_mot_09_percentil_empates_e_populacao_unitaria():
    assert percentile_score(2, [2, 2, 2, 2], "higher") == 50
    assert percentile_detail(7, [7], "higher")["score"] == 50.0
    assert percentile_detail(7, [], "higher")["score"] == 50.0


def test_ut_mot_10_percentil_fora_da_populacao_fica_no_extremo():
    assert percentile_score(1000, [1, 2, 3], "higher") == 100
    assert percentile_score(-1000, [1, 2, 3], "higher") == 0


# --- Indicadores ---------------------------------------------------------------------

@pytest.mark.parametrize("payout, nota", [
    (None, None), (0.05, 0.0), (0.10, 50.0), (0.30, 100.0), (0.80, 100.0),
    (0.90, 50.0), (1.00, 50.0), (1.01, 0.0),
])
def test_ut_mot_11_payout_faixas(payout, nota):
    assert payout_score(payout) == nota


# --- Motor sobre um universo sintético ----------------------------------------------

def _ind(ticker, setor="S1", tipo="acao", **extra):
    base = {
        "ticker": ticker, "name": ticker, "sector": setor, "type": tipo,
        "liquidity_brl": 5e7, "equity": 1e9, "history_days": 1000,
        "earnings_yield": 0.1, "pvp": 1.5, "ev_ebitda": 5.0, "roe": 0.15, "roic": 0.12,
        "net_margin": 0.1, "leverage": 0.5, "dy_5y_avg": 0.05, "div_consistency_score": 100.0,
        "payout_score": 100.0, "dpa_trend_score": 100.0, "vol_252": 0.3, "mdd_3y": 0.3,
        "beta": 1.0, "market_cap": 1e10, "mom_12_1": 0.1, "mom_6_1": 0.05, "dist_52w_high": 0.9,
    }
    base.update(extra)
    return base


def _universo_sintetico():
    u = {}
    for i in range(8):
        u[f"A{i}"] = _ind(f"A{i}", setor="S1" if i < 5 else "S2", tipo="banco" if i == 7 else "acao",
                          earnings_yield=0.02 * (i + 1), vol_252=0.1 * (i + 1),
                          mom_12_1=-0.2 + 0.05 * i, dy_5y_avg=0.01 * i)
    u["ELIM"] = _ind("ELIM", liquidity_brl=10, earnings_yield=10.0)  # eliminada (E1)
    return u


def test_ut_mot_12_notas_entre_0_e_100():
    """TC-ML-UT-36 — toda nota de dimensão fica em 0..100 (ou None)."""
    res = score_universe(_universo_sintetico())
    for r in res.values():
        for nota in r["scores"].values():
            assert nota is None or 0 <= nota <= 100


def test_ut_mot_13_eliminada_marcada_e_fora_da_populacao():
    """TC-ML-UT-37 — a ação eliminada não altera a régua das elegíveis."""
    u = _universo_sintetico()
    com = score_universe(u)
    sem = score_universe({k: v for k, v in u.items() if k != "ELIM"})
    assert com["ELIM"]["eliminated"] is True
    assert com["ELIM"]["eliminations"][0]["code"] == "E1"
    for t in sem:
        assert com[t]["scores"] == sem[t]["scores"]


def test_ut_mot_14_regua_indisponivel_e_sem_dado():
    res = score_universe(_universo_sintetico())
    valor = res["A0"]["breakdown"]["valor"]["reguas"]
    status = {r["key"]: r["status"] for r in valor}
    assert status["fcf_yield"] == "indisponivel"
    u = _universo_sintetico()
    u["A1"]["pvp"] = None
    r2 = score_universe(u)
    st = {r["key"]: r["status"] for r in r2["A1"]["breakdown"]["valor"]["reguas"]}
    assert st["pvp"] == "sem_dado"


def test_ut_mot_15_determinismo_motor():
    """TC-ML-UT-38 — mesma entrada, mesmas notas."""
    assert score_universe(_universo_sintetico()) == score_universe(_universo_sintetico())


# --- Snapshot com os dados reais de data/raw (somente leitura) ----------------------

def _brutos():
    fp, pp = latest_raw("fundamentus"), latest_raw("price_stats")
    if not fp or not pp:
        pytest.skip("Sem dados brutos em data/raw/")
    return (json.loads(fp.read_text(encoding="utf-8")),
            json.loads(pp.read_text(encoding="utf-8")))


def test_ut_mot_16_indicadores_a_partir_dos_brutos():
    fund, price = _brutos()
    ind = build_indicators(fund["rows"], price["rows"])
    assert len(ind) >= 40
    for i in ind.values():
        assert {"liquidity_brl", "equity", "history_days", "sector", "type"} <= set(i)


def test_ut_mot_17_snapshot_reconstruido_bate_com_o_salvo():
    """TC-ML-UT-39 — determinismo: reprocessar os brutos reproduz as notas do snapshot salvo."""
    fund, price = _brutos()
    salvo = load_latest()
    if salvo is None or salvo.get("as_of") != price.get("as_of"):
        pytest.skip("Snapshot salvo não corresponde aos últimos dados brutos")
    novo = build_snapshot(fund, price)
    assert novo["universe_size"] == salvo["universe_size"]
    assert novo["eligible"] == salvo["eligible"]
    assert {a["ticker"]: a["scores"] for a in novo["assets"]} == \
        {a["ticker"]: a["scores"] for a in salvo["assets"]}


def test_ut_mot_18_snapshot_filtros_e_pendencias():
    fund, price = _brutos()
    snap = build_snapshot(fund, price)
    for a in snap["assets"]:
        assert a["eliminated"] == bool(a["eliminations"])
    assert snap["data_quality"]["unavailable_reguas"]
    assert set(snap["data_quality"]["pending_rules"]) == {"E3", "E4", "E5"}


def test_ut_mot_19_save_e_load_em_pasta_temporaria(tmp_path):
    """save/load usando pasta temporária (nunca data/)."""
    destino = tmp_path / "snap.json"
    assert load_latest(destino) is None
    save({"as_of": "2000-01-01", "assets": []}, destino)
    assert load_latest(destino)["as_of"] == "2000-01-01"
    assert destino != LATEST


def test_ut_mot_20_reexporta_api_do_pacote():
    import eren_ml.scoring as s
    assert s.rank and s.score_universe and s.percentile_score and engine
