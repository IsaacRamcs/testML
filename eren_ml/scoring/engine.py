"""Motor de score multidimensional.

Para cada ação: aplica os filtros eliminatórios e calcula 5 notas de 0 a 100
(valor, qualidade, dividendos, estabilidade, momentum). Cada nota é a média
ponderada de réguas pontuadas por PERCENTIL — a ação é comparada com as
demais, não com limiares fixos. Valor e qualidade comparam dentro do setor;
as demais dimensões, no universo inteiro.

Módulo puro: recebe indicadores, devolve scores e o detalhamento de cada
régua (explicabilidade). Sem rede, sem banco.
"""
from __future__ import annotations

from collections import defaultdict

from . import rules
from .rules import DIMENSIONS, Dimension, Regua


def percentile_detail(value: float, population: list[float], direction: str) -> dict:
    """Percentil por posto médio (empates dividem a posição), em 0..100.

    Por ser baseado em posição, é imune a outliers — a winsorização prevista na
    especificação fica implícita. Devolve também os termos da conta, para que o
    app mostre exatamente como a nota foi obtida.
    """
    n = len(population)
    below = sum(1 for x in population if x < value)
    equal = sum(1 for x in population if x == value)
    if n <= 1:
        return {"score": 50.0, "n": n, "below": below, "equal": equal, "rank": None, "percentile": None}
    rank = below + (equal + 1) / 2          # posto médio, 1..n
    pct = (rank - 1) / (n - 1) * 100
    pct = min(100.0, max(0.0, pct))  # ação fora da população (ex.: eliminada) fica nos extremos
    return {
        "score": round(100 - pct if direction == "lower" else pct, 1),
        "n": n, "below": below, "equal": equal,
        "rank": rank, "percentile": round(pct, 1),
    }


def percentile_score(value: float, population: list[float], direction: str) -> float:
    return percentile_detail(value, population, direction)["score"]


def eliminations(ind: dict) -> list[dict]:
    out = []
    liq = ind.get("liquidity_brl")
    if liq is not None and liq < rules.MIN_LIQUIDITY_BRL:
        out.append({"code": "E1", "reason": rules.ELIMINATION_RULES["E1"]})
    eq = ind.get("equity")
    if eq is not None and eq < 0:
        out.append({"code": "E2", "reason": rules.ELIMINATION_RULES["E2"]})
    days = ind.get("history_days")
    if days is not None and days < rules.MIN_HISTORY_DAYS:
        out.append({"code": "E6", "reason": rules.ELIMINATION_RULES["E6"]})
    return out


def warnings(ind: dict) -> list[str]:
    w = []
    if ind.get("pl") is not None and ind["pl"] < 0:
        w.append("Prejuízo nos últimos 12 meses")
    if ind.get("payout") is not None and ind["payout"] > 1.0:
        w.append("Distribui mais proventos do que lucra (payout acima de 100%)")
    if ind.get("leverage") is not None and ind["leverage"] > 2.5:
        w.append("Endividamento elevado em relação ao patrimônio")
    if ind.get("mdd_3y") is not None and ind["mdd_3y"] > 0.6:
        w.append("Queda superior a 60% em relação ao pico dos últimos 3 anos")
    return w


def _reguas_for(dim: Dimension, ind: dict) -> tuple[Regua, ...]:
    if dim.reguas_financeiro and ind["type"] in ("banco", "seguradora"):
        return dim.reguas_financeiro
    return dim.reguas


def score_universe(indicators: dict[str, dict]) -> dict[str, dict]:
    elim = {t: eliminations(i) for t, i in indicators.items()}
    eligible = {t: i for t, i in indicators.items() if not elim[t]}

    results: dict[str, dict] = {
        t: {
            "ticker": t,
            "eliminated": bool(elim[t]),
            "eliminations": elim[t],
            "warnings": warnings(i),
            "scores": {},
            "breakdown": {},
        }
        for t, i in indicators.items()
    }

    for dim in DIMENSIONS:
        # populações por régua (só ações elegíveis), no universo e por setor
        universe_pop: dict[str, list[float]] = defaultdict(list)
        sector_pop: dict[tuple[str, str], list[float]] = defaultdict(list)
        users_of: dict[str, int] = defaultdict(int)
        for t, ind in eligible.items():
            for r in _reguas_for(dim, ind):
                users_of[r.key] += 1
                v = ind.get(r.key)
                if v is not None:
                    universe_pop[r.key].append(v)
                    sector_pop[(ind["sector"], r.key)].append(v)

        def regua_available(r: Regua) -> bool:
            if not r.available:
                return False
            n_users = users_of.get(r.key, 0)
            return n_users > 0 and len(universe_pop[r.key]) / n_users >= rules.MIN_COVERAGE

        for t, ind in indicators.items():
            reguas = _reguas_for(dim, ind)
            avail = [r for r in reguas if regua_available(r)]
            entries = []
            present = 0
            for r in reguas:
                entry = {"key": r.key, "label": r.label, "weight": r.weight, "fmt": r.fmt,
                         "value": ind.get(r.key), "score": None, "status": "ok", "peer": None,
                         "direction": r.direction, "what": r.what, "formula": r.formula}
                if r not in avail:
                    entry["status"] = "indisponivel"
                    entry["note"] = r.note or "Cobertura de dados insuficiente"
                    entries.append(entry)
                    continue
                v = ind.get(r.key)
                if v is None:
                    entry["status"] = "sem_dado"
                    entry["score"] = 50.0
                elif r.direction == "absolute":
                    entry["score"] = round(float(v), 1)
                    entry["peer"] = "absoluto"
                    present += 1
                else:
                    pop = universe_pop[r.key]
                    peer = "universo"
                    if dim.peer == "sector":
                        sp = sector_pop.get((ind["sector"], r.key), [])
                        if len(sp) >= rules.MIN_PEER_GROUP:
                            pop, peer = sp, f"setor: {ind['sector']}"
                    det = percentile_detail(v, pop, r.direction)
                    entry["score"] = det["score"]
                    entry["peer"] = peer
                    entry["calc"] = {k: det[k] for k in ("n", "below", "equal", "rank", "percentile")}
                    present += 1
                entries.append(entry)

            total_w = sum(r.weight for r in avail)
            if avail and present > len(avail) / 2:
                s = sum(e["score"] * e["weight"] for e in entries if e["status"] in ("ok", "sem_dado")) / total_w
                score = round(s, 1)
            else:
                score = None
            for e in entries:  # peso efetivo após redistribuição
                e["weight_effective"] = round(e["weight"] / total_w, 3) if (e["status"] != "indisponivel" and total_w) else 0.0
            results[t]["scores"][dim.key] = score
            results[t]["breakdown"][dim.key] = {
                "label": dim.label,
                "what": dim.what,
                "score": score,
                "peer_basis": "setor" if dim.peer == "sector" else "universo",
                "reference": dim.reference,
                "reguas": entries,
            }
    return results
