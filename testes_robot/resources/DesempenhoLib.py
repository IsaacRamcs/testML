"""Biblioteca Robot para medir tempo de resposta (RNF-002).

P95 pelo método do posto mais próximo (nearest-rank): ordena as N medições e
toma a de posição ceil(0,95 × N). Com N = 20, é a 19ª medição.

Uma requisição de aquecimento é feita antes das medições e descartada, para
não contar o carregamento inicial do snapshot em memória.
"""
import csv
import math
import os
import time

import requests
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn


def _p95(amostras):
    ordenadas = sorted(amostras)
    return ordenadas[math.ceil(0.95 * len(ordenadas)) - 1]


def medir_tempo_de_resposta(metodo, url, repeticoes=20, corpo=None):
    """Executa `repeticoes` chamadas e devolve um dicionário com p95, média, mínimo e máximo (s).

    Falha se alguma resposta não for 2xx (tempo de erro não vale como medição).
    """
    repeticoes = int(repeticoes)
    metodo = metodo.upper()
    sessao = requests.Session()
    sessao.request(metodo, url, json=corpo, timeout=30)  # aquecimento (descartado)
    tempos = []
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        r = sessao.request(metodo, url, json=corpo, timeout=30)
        tempos.append(time.perf_counter() - inicio)
        if not 200 <= r.status_code < 300:
            raise AssertionError(f"{metodo} {url} respondeu {r.status_code}: {r.text[:200]}")
    resultado = {
        "p95": round(_p95(tempos), 4),
        "media": round(sum(tempos) / len(tempos), 4),
        "minimo": round(min(tempos), 4),
        "maximo": round(max(tempos), 4),
        "n": repeticoes,
    }
    logger.info(f"{metodo} {url} — {resultado}")
    _registrar_csv(metodo, url, resultado)
    return resultado


_csv_iniciado = False


def _registrar_csv(metodo, url, r):
    """Grava desempenho_p95.csv na pasta de saída do Robot (recriado a cada execução)."""
    global _csv_iniciado
    try:
        pasta = BuiltIn().get_variable_value("${OUTPUT DIR}") or "."
    except Exception:
        pasta = "."
    arquivo = os.path.join(pasta, "desempenho_p95.csv")
    modo = "a" if _csv_iniciado else "w"
    with open(arquivo, modo, newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if not _csv_iniciado:
            _csv_iniciado = True
            w.writerow(["metodo", "url", "n", "p95_s", "media_s", "minimo_s", "maximo_s"])
        w.writerow([metodo, url, r["n"], r["p95"], r["media"], r["minimo"], r["maximo"]])
