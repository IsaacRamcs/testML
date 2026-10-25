"""Coleta de dados brutos de mercado.

- Fundamentus (resultado.php): uma página com múltiplos e rentabilidade de
  todas as ações listadas — P/L, P/VP, EV/EBITDA, ROE, ROIC, margens,
  liquidez média e patrimônio líquido.
- Yahoo Finance (API de gráfico): histórico diário de 5 anos com preço
  ajustado e eventos de proventos.

Fontes provisórias do TCC: a especificação prevê a migração dos
fundamentos para as demonstrações oficiais da CVM (DFP/ITR).
"""
from __future__ import annotations

import re
import time

import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

FUNDAMENTUS_URL = "https://www.fundamentus.com.br/resultado.php"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1d&events=div"

# Ordem das colunas da tabela do Fundamentus (após "Papel")
_FCOLS = ["cotacao", "pl", "pvp", "psr", "dy", "p_ativo", "p_cap_giro", "p_ebit",
          "p_ativ_circ_liq", "ev_ebit", "ev_ebitda", "mrg_bruta", "mrg_ebit", "mrg_liq",
          "liq_corr", "roic", "roe", "liq_2m", "patrim", "dl_pl", "cresc_rec_5a"]


def _br_number(v: str) -> float | None:
    v = re.sub(r"\s", "", v)
    if v in ("", "-"):
        return None
    pct = v.endswith("%")
    v = v.rstrip("%").replace(".", "").replace(",", ".")
    try:
        n = float(v)
    except ValueError:
        return None
    return n / 100 if pct else n


def parse_fundamentus(html: str) -> list[list]:
    """Converte a página do Fundamentus em linhas no formato do pipeline."""
    rows = []
    for chunk in html.split("<tr"):
        if "detalhes.php?papel=" not in chunk:
            continue
        m = re.search(r"papel=([A-Z0-9]+)", chunk)
        title = re.search(r'title="([^"]*)"', chunk)
        cells = re.findall(r"<td>([^<]*)</td>", chunk)
        if not m or len(cells) != len(_FCOLS):
            continue
        d = dict(zip(_FCOLS, (_br_number(c) for c in cells)))
        rows.append([m.group(1), (title.group(1).strip() if title else ""),
                     d["pl"], d["pvp"], d["dy"], d["ev_ebitda"], d["mrg_liq"], d["liq_corr"],
                     d["roic"], d["roe"], d["liq_2m"], d["patrim"], d["dl_pl"], d["cresc_rec_5a"]])
    return rows


def fetch_fundamentus(timeout: int = 30) -> list[list]:
    r = requests.get(FUNDAMENTUS_URL, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    rows = parse_fundamentus(r.content.decode("latin-1"))
    if len(rows) < 100:
        raise RuntimeError(f"Fundamentus retornou só {len(rows)} linhas — layout pode ter mudado.")
    return rows


#: O Yahoo às vezes responde 429 para o User-Agent completo de navegador e
#: aceita um genérico; tentamos os dois antes de desistir.
_YAHOO_UAS = (UA, "Mozilla/5.0")


def fetch_yahoo_chart(ticker: str, timeout: int = 30, retries: int = 2) -> dict | None:
    symbol = ticker.replace("^", "%5E") if ticker.startswith("^") else f"{ticker}.SA"
    for attempt in range(retries + 1):
        try:
            for ua in _YAHOO_UAS:
                r = requests.get(YAHOO_URL.format(symbol=symbol), headers={"User-Agent": ua}, timeout=timeout)
                if r.status_code != 429:
                    break
            if r.status_code == 404:
                return None
            r.raise_for_status()
            res = r.json()["chart"]["result"]
            return res[0] if res else None
        except Exception:
            if attempt == retries:
                return None
            time.sleep(1.5 * (attempt + 1))
    return None
