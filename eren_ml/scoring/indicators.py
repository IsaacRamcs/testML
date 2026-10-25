"""Montagem da tabela de indicadores a partir das fontes brutas.

Entrada: linhas do Fundamentus (múltiplos e rentabilidade) + estatísticas de
preço/proventos calculadas a partir do histórico diário (Yahoo Finance).
Saída: um dicionário ticker -> indicadores padronizados, que é exatamente o
que o motor de score consome. Nenhuma regra de pontuação mora aqui.
"""
from __future__ import annotations

import math
from typing import Any

from .universe import UNIVERSE

FUND_COLS = ["ticker", "nome", "pl", "pvp", "dy", "ev_ebitda", "mrg_liq", "liq_corr",
             "roic", "roe", "liq_2m", "patrim", "dl_pl", "cresc_rec_5a"]
PRICE_COLS = ["ticker", "n_days", "last_close", "vol_252", "beta", "mdd_3y", "mom_12_1",
              "mom_6_1", "dist_52w_high", "dy_5y_avg", "anos_com_div", "anos_obs",
              "dpa_recente", "dpa_anterior", "dy_12m"]

#: Valor usado para EV/EBITDA quando o EBITDA é negativo (pior posição no ranking).
EV_EBITDA_NEGATIVE = 999.0


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def payout_score(payout: float | None) -> float | None:
    """Faixas da especificação: 30–80% = 100; 10–30% ou 80–100% = 50; resto = 0."""
    if payout is None:
        return None
    if 0.30 <= payout <= 0.80:
        return 100.0
    if 0.10 <= payout < 0.30 or 0.80 < payout <= 1.00:
        return 50.0
    return 0.0


def build_indicators(fund_rows: list[list], price_rows: list[list]) -> dict[str, dict]:
    fund = {r[0]: dict(zip(FUND_COLS, r)) for r in fund_rows}
    price = {r[0]: dict(zip(PRICE_COLS, r)) for r in price_rows}

    out: dict[str, dict] = {}
    for ticker, asset in UNIVERSE.items():
        f = fund.get(ticker)
        p = price.get(ticker)
        if f is None and p is None:
            continue  # sem nenhum dado: fica fora do snapshot
        f = f or {}
        p = p or {}
        fin = asset.is_financial

        pl = _num(f.get("pl"))
        pvp = _num(f.get("pvp"))
        patrim = _num(f.get("patrim"))
        dy12 = _num(f.get("dy"))
        ev = _num(f.get("ev_ebitda"))

        # Fundamentus devolve 0 quando o indicador não se aplica (bancos/seguradoras)
        def nz(v):
            v = _num(v)
            return None if (v is None or (fin and v == 0)) else v

        ev_ebitda = None
        if not fin and ev not in (None, 0):
            ev_ebitda = ev if ev > 0 else EV_EBITDA_NEGATIVE

        payout = dy12 * pl if (dy12 is not None and pl is not None and pl > 0) else (
            None if dy12 is None else (0.0 if dy12 == 0 else 9.99))  # paga sem lucro -> fora da faixa

        anos_obs = _num(p.get("anos_obs")) or 0
        anos_div = _num(p.get("anos_com_div"))
        dpa_r, dpa_a = _num(p.get("dpa_recente")), _num(p.get("dpa_anterior"))
        dpa_trend = None
        if dpa_r is not None and dpa_a is not None:
            dpa_trend = 0.0 if (dpa_r == 0 and dpa_a == 0) else (100.0 if dpa_r >= dpa_a else 0.0)

        out[ticker] = {
            "ticker": ticker,
            "name": asset.name,
            "sector": asset.sector,
            "type": asset.type,
            "price": _num(p.get("last_close")),
            "history_days": _num(p.get("n_days")),
            # valor
            "pl": pl,
            "earnings_yield": (1.0 / pl) if pl not in (None, 0) else None,
            "pvp": pvp if (pvp is not None and pvp > 0) else None,
            "ev_ebitda": ev_ebitda,
            "fcf_yield": None,
            # qualidade
            "roe": _num(f.get("roe")),
            "roic": nz(f.get("roic")),
            "net_margin": nz(f.get("mrg_liq")),
            "leverage": None if fin else _num(f.get("dl_pl")),
            "f_score": None,
            "roe_stability": None,
            "profit_trend": None,
            # dividendos
            "dy_12m": dy12,
            "dy_5y_avg": _num(p.get("dy_5y_avg")),
            "div_consistency": (anos_div / anos_obs) if (anos_div is not None and anos_obs) else None,
            "div_consistency_score": (100.0 * anos_div / anos_obs) if (anos_div is not None and anos_obs) else None,
            "payout": payout,
            "payout_score": payout_score(payout),
            "cash_coverage": None,
            "dpa_trend_score": dpa_trend,
            "anos_com_div": anos_div,
            "anos_obs": anos_obs or None,
            "dpa_recente": dpa_r,
            "dpa_anterior": dpa_a,
            # estabilidade
            "vol_252": _num(p.get("vol_252")),
            "mdd_3y": _num(p.get("mdd_3y")),
            "beta": _num(p.get("beta")),
            "market_cap": (patrim * pvp) if (patrim and pvp and patrim > 0 and pvp > 0) else None,
            # momentum
            "mom_12_1": _num(p.get("mom_12_1")),
            "mom_6_1": _num(p.get("mom_6_1")),
            "dist_52w_high": _num(p.get("dist_52w_high")),
            # filtros
            "liquidity_brl": _num(f.get("liq_2m")),
            "equity": patrim,
            "revenue_growth_5y": _num(f.get("cresc_rec_5a")),
        }
    return out
