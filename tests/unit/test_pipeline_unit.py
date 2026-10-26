"""Testes unitários das funções puras do pipeline de dados.

NÃO acessam a internet: as chamadas HTTP são substituídas (monkeypatch) por
respostas falsas. NÃO executam eren_ml.pipeline.run e não escrevem em data/.
"""
from datetime import datetime, timedelta, timezone

import pytest

from eren_ml.pipeline import price_stats, sources

pytestmark = pytest.mark.unit


def _grafico(precos, inicio=datetime(2020, 1, 2, tzinfo=timezone.utc), dividendos=()):
    ts = [int((inicio + timedelta(days=i)).timestamp()) for i in range(len(precos))]
    eventos = {str(t): {"date": t, "amount": v} for t, v in dividendos}
    return {
        "timestamp": ts,
        "indicators": {"quote": [{"close": list(precos)}], "adjclose": [{"adjclose": list(precos)}]},
        "events": {"dividends": eventos},
    }


# --- price_stats ---------------------------------------------------------------------

def test_ut_pip_01_historico_curto_retorna_none():
    assert price_stats.compute(_grafico([10.0] * 29), None) is None


def test_ut_pip_02_preco_constante():
    st = price_stats.compute(_grafico([10.0] * 600), None)
    assert st["n_days"] == 600
    assert st["vol_252"] == 0
    assert st["mdd_3y"] == 0
    assert st["mom_12_1"] == 0 and st["mom_6_1"] == 0
    assert st["dist_52w_high"] == 1
    assert st["beta"] is None


def test_ut_pip_03_queda_maxima_e_beta():
    precos = [100.0] * 300 + [50.0] * 300
    st = price_stats.compute(_grafico(precos), _grafico(precos))
    assert st["mdd_3y"] == pytest.approx(0.5)
    precos2 = [100 + (i % 7) for i in range(600)]
    st2 = price_stats.compute(_grafico(precos2), _grafico(precos2))
    assert st2["beta"] == pytest.approx(1.0)


def test_ut_pip_04_ignora_pontos_invalidos_e_conta_proventos():
    g = _grafico([10.0] * 2000)
    g["indicators"]["quote"][0]["close"][5] = None
    hoje = datetime(2020, 1, 2, tzinfo=timezone.utc) + timedelta(days=1999)
    t = int((hoje - timedelta(days=30)).timestamp())
    g["events"]["dividends"] = {str(t): {"date": t, "amount": 1.0}}
    st = price_stats.compute(g, None)
    assert st["n_days"] == 1999
    assert st["dy_12m"] == pytest.approx(0.1)


# --- sources (sem rede) --------------------------------------------------------------

@pytest.mark.parametrize("texto, valor", [
    ("1.234,56", 1234.56), ("12,5%", 0.125), ("-", None), ("", None), ("abc", None), ("-3,2", -3.2),
])
def test_ut_pip_05_numero_brasileiro(texto, valor):
    assert sources._br_number(texto) == (pytest.approx(valor) if valor is not None else None)


def _linha_html(papel):
    celulas = "".join("<td>1,0</td>" for _ in sources._FCOLS)
    return f'<tr><td><a href="detalhes.php?papel={papel}" title="EMPRESA {papel}">{papel}</a></td>{celulas}</tr>'


def test_ut_pip_06_parse_fundamentus():
    html = "<table>" + _linha_html("ABCD3") + _linha_html("WXYZ4") + "<tr><td>lixo</td></tr></table>"
    linhas = sources.parse_fundamentus(html)
    assert [l[0] for l in linhas] == ["ABCD3", "WXYZ4"]
    assert linhas[0][1] == "EMPRESA ABCD3"
    assert len(linhas[0]) == 14


class _RespostaFalsa:
    def __init__(self, status=200, corpo=None, conteudo=b""):
        self.status_code, self._corpo, self.content = status, corpo, conteudo

    def json(self):
        return self._corpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def test_ut_pip_07_fetch_yahoo_simulado(monkeypatch):
    chamadas = []
    respostas = iter([_RespostaFalsa(429), _RespostaFalsa(200, {"chart": {"result": [{"ok": 1}]}})])
    monkeypatch.setattr(sources.requests, "get", lambda url, **kw: chamadas.append(url) or next(respostas))
    assert sources.fetch_yahoo_chart("PETR4") == {"ok": 1}
    assert "PETR4.SA" in chamadas[0]


def test_ut_pip_08_fetch_yahoo_404_e_falha(monkeypatch):
    monkeypatch.setattr(sources.requests, "get", lambda url, **kw: _RespostaFalsa(404))
    assert sources.fetch_yahoo_chart("^BVSP") is None
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    monkeypatch.setattr(sources.requests, "get", lambda url, **kw: _RespostaFalsa(500))
    assert sources.fetch_yahoo_chart("XXXX3", retries=1) is None


def test_ut_pip_09_fetch_fundamentus_simulado(monkeypatch):
    poucas = ("<table>" + _linha_html("ABCD3") + "</table>").encode("latin-1")
    monkeypatch.setattr(sources.requests, "get", lambda url, **kw: _RespostaFalsa(200, conteudo=poucas))
    with pytest.raises(RuntimeError, match="layout"):
        sources.fetch_fundamentus()
    muitas = ("<table>" + "".join(_linha_html(f"A{i:03d}3") for i in range(120)) + "</table>").encode("latin-1")
    monkeypatch.setattr(sources.requests, "get", lambda url, **kw: _RespostaFalsa(200, conteudo=muitas))
    assert len(sources.fetch_fundamentus()) == 120
