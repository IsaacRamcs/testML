"""Pipeline diário do motor de score.

Uso (na raiz do erenML, com o .venv ativo):

    python -m eren_ml.pipeline.run              # coleta, calcula e salva o snapshot
    python -m eren_ml.pipeline.run --offline    # recalcula com os últimos dados brutos salvos

Etapas: Fundamentus (1 requisição) -> Yahoo (1 por ação + Ibovespa) ->
indicadores -> filtros eliminatórios -> 5 dimensões por percentil ->
data/snapshots/scores_latest.json (lido pela API).
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import date

from ..scoring import rules
from ..scoring.indicators import FUND_COLS, PRICE_COLS
from ..scoring.snapshot import RAW_DIR, build_snapshot, latest_raw, save
from ..scoring.universe import BENCHMARK, UNIVERSE
from . import price_stats, sources


def collect() -> tuple[dict, dict]:
    today = date.today().isoformat()
    print("1/3  Fundamentus (múltiplos e rentabilidade)...", flush=True)
    fund_rows = sources.fetch_fundamentus()
    fund = {"source": sources.FUNDAMENTUS_URL, "fetched_at": today,
            "columns": FUND_COLS, "rows": [r for r in fund_rows if r[0] in UNIVERSE]}
    print(f"     {len(fund['rows'])} ações do universo encontradas")

    print(f"2/3  Histórico de preços e proventos (Yahoo) — {len(UNIVERSE) + 1} séries...", flush=True)
    bench = sources.fetch_yahoo_chart(BENCHMARK)
    rows, missing = [], []
    for i, t in enumerate(UNIVERSE, 1):
        chart = sources.fetch_yahoo_chart(t)
        st = price_stats.compute(chart, bench) if chart else None
        if st is None:
            missing.append(t)
        else:
            rows.append([t] + [st[c] for c in PRICE_COLS[1:]])
        print(f"     {i:>2}/{len(UNIVERSE)} {t:<7} {'ok' if st else 'sem dados'}", flush=True)
        time.sleep(0.3)
    price = {"source": "Yahoo Finance chart API (5 anos, diário, com proventos)",
             "as_of": today, "columns": PRICE_COLS, "rows": rows}
    if missing:
        print(f"     sem histórico: {', '.join(missing)}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"fundamentus_{today}.json").write_text(json.dumps(fund, ensure_ascii=False), encoding="utf-8")
    (RAW_DIR / f"price_stats_{today}.json").write_text(json.dumps(price, ensure_ascii=False), encoding="utf-8")
    return fund, price


def main() -> None:
    ap = argparse.ArgumentParser(description="Pipeline do motor de score Eren")
    ap.add_argument("--offline", action="store_true", help="usa os últimos dados brutos salvos")
    args = ap.parse_args()

    if args.offline:
        fp, pp = latest_raw("fundamentus"), latest_raw("price_stats")
        if not fp or not pp:
            raise SystemExit("Nenhum dado bruto salvo em data/raw/. Rode sem --offline.")
        fund = json.loads(fp.read_text(encoding="utf-8"))
        price = json.loads(pp.read_text(encoding="utf-8"))
        print(f"Usando dados salvos: {fp.name}, {pp.name}")
    else:
        fund, price = collect()

    print("3/3  Motor de score (regras %s)..." % rules.RULE_VERSION, flush=True)
    snap = build_snapshot(fund, price)
    path = save(snap)
    print(f"\nPronto: {snap['eligible']} ações pontuadas de {snap['universe_size']} "
          f"| eliminadas: {', '.join(e['ticker'] for e in snap['eliminated']) or 'nenhuma'}")
    print(f"Snapshot: {path}")


if __name__ == "__main__":
    main()
