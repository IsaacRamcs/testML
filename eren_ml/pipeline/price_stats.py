"""Indicadores de preço e proventos a partir do histórico diário.

Mesmas fórmulas usadas na coleta via banco (SQL), para que as duas rotas
produzam números idênticos:
  - volatilidade: desvio-padrão dos retornos diários (252 pregões) x raiz(252)
  - beta: inclinação da regressão dos retornos da ação contra o Ibovespa (252 pregões)
  - queda máxima: maior distância pico-a-vale nos últimos 756 pregões (~3 anos)
  - momentum 12-1 e 6-1: retorno até 21 pregões atrás (exclui o último mês)
  - dividend yield por ano: proventos do ano / preço médio de fechamento do ano
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone


def _series(chart: dict) -> list[tuple[date, float, float]]:
    ts = chart.get("timestamp") or []
    q = (chart.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    a = (chart.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose") or []
    out = []
    for i, t in enumerate(ts):
        c = q[i] if i < len(q) else None
        adj = a[i] if i < len(a) else None
        if c is None or adj is None or adj <= 0:
            continue
        out.append((datetime.fromtimestamp(t, tz=timezone.utc).date(), float(c), float(adj)))
    out.sort(key=lambda x: x[0])
    return out


def _returns(series):
    return {series[i][0]: series[i][2] / series[i - 1][2] - 1 for i in range(1, len(series))}


def _stdev(xs):
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def compute(chart: dict, benchmark: dict | None, today: date | None = None) -> dict | None:
    s = _series(chart)
    n = len(s)
    if n < 30:
        return None
    today = today or s[-1][0]
    adj = [x[2] for x in s]
    rets = _returns(s)
    last252 = s[-252:]

    def back(k):  # valor ajustado k pregões atrás (k=0 é o último)
        return adj[-1 - k] if n > k else None

    vol = _stdev([rets[d] for d, _, _ in last252 if d in rets])
    beta = None
    if benchmark:
        brets = _returns(_series(benchmark))
        pairs = [(rets[d], brets[d]) for d, _, _ in last252 if d in rets and d in brets]
        if len(pairs) > 30:
            mx = sum(b for _, b in pairs) / len(pairs)
            my = sum(y for y, _ in pairs) / len(pairs)
            var = sum((b - mx) ** 2 for _, b in pairs)
            beta = sum((y - my) * (b - mx) for y, b in pairs) / var if var else None

    runmax, mdd = 0.0, 0.0
    for _, _, a in s[-756:]:
        runmax = max(runmax, a)
        mdd = max(mdd, 1 - a / runmax)

    a21, a126, a252 = back(21), back(126), back(252)
    max52 = max(x[2] for x in last252)

    # proventos
    divs = []
    for ev in (chart.get("events", {}).get("dividends") or {}).values():
        divs.append((datetime.fromtimestamp(ev["date"], tz=timezone.utc).date(), float(ev["amount"])))
    years = list(range(today.year - 5, today.year))
    avg_close = {}
    for y in years:
        cl = [c for d, c, _ in s if d.year == y]
        if cl:
            avg_close[y] = sum(cl) / len(cl)
    div_year = {y: sum(v for d, v in divs if d.year == y) for y in years}
    obs = [y for y in years if y in avg_close]
    dy5 = (sum(div_year[y] / avg_close[y] for y in obs) / len(obs)) if obs else None
    recent = sum(div_year[y] for y in years[-2:]) / 2
    previous = sum(div_year[y] for y in years[-4:-2]) / 2
    div12 = sum(v for d, v in divs if d > today - timedelta(days=365))

    return {
        "n_days": n,
        "last_close": s[-1][1],
        "vol_252": vol * math.sqrt(252) if vol is not None else None,
        "beta": beta,
        "mdd_3y": mdd,
        "mom_12_1": (a21 / a252 - 1) if (a21 and a252) else None,
        "mom_6_1": (a21 / a126 - 1) if (a21 and a126) else None,
        "dist_52w_high": adj[-1] / max52 if max52 else None,
        "dy_5y_avg": dy5,
        "anos_com_div": sum(1 for y in obs if div_year[y] > 0),
        "anos_obs": len(obs),
        "dpa_recente": recent,
        "dpa_anterior": previous,
        "dy_12m": div12 / s[-1][1] if s[-1][1] else None,
    }
