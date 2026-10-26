# Relatório de execução — suíte de testes do erenML

- **Data:** 26/10/2026
- **Ambiente:** Windows 11, Python 3.14.5 (.venv), pytest 9.1.1, pytest-cov 7.1.0, Robot Framework 7.5, RequestsLibrary 0.9.7
- **Dados:** snapshot de 25/10/2026 (50 ações, 49 elegíveis, BRKM5 eliminada por E2). Nenhum dado foi recoletado.
- **Servidor:** `uvicorn api.main:app --host 127.0.0.1 --port 8000`, sem `DATABASE_URL` (`database_configured: false`)

## Resumo

| Camada | Total | Passou | Falhou | Defeito conhecido |
|---|---|---|---|---|
| Unitário (pytest, inclui os 13 originais) | 139 | 137 | 0 | 2 (xfail: DEF-02, DEF-03) |
| Integração (Robot) | 22 | 17 | 5 | 5 (DEF-02, DEF-03, DEF-04) |
| Funcional (Robot) | 18 | 17 | 1 | 1 (DEF-01) |
| Desempenho (Robot) | 6 | 6 | 0 | 0 |
| **Total** | **185** | **177** | **6** | **8 testes → 4 defeitos** |

Toda falha do Robot tem a tag `defeito-conhecido`, conferido pelo `output.xml`: nenhuma falha ficou sem a tag.

## Cobertura (RNF-011: mínimo 70%)

`pytest --cov=eren_ml`: **90%** (607 instruções, 61 não cobertas). **Atende.**

| Módulo | Cobertura |
|---|---|
| profile/* (classifier, questionnaire, weights, demo_assets) | 100% |
| scoring/ranking, rules, snapshot, universe | 100% |
| scoring/engine | 99% |
| scoring/indicators | 93% |
| pipeline/price_stats | 99% |
| pipeline/sources | 97% (rede simulada) |
| pipeline/run | **0%**: não executado por regra (acessa a internet e reescreve `data/`) |

Relatório navegável: `htmlcov/index.html`.

## Desempenho (RNF-002: P95 ≤ 1,5 s, 20 repetições + 1 de aquecimento)

| Endpoint | P95 (s) | Média (s) | Máx. (s) | Resultado |
|---|---|---|---|---|
| GET /api/questionnaire | 0,0015 | 0,0014 | 0,0018 | Atende |
| POST /api/profile | 0,0025 | 0,0023 | 0,0027 | Atende |
| GET /api/rankings?vector=renda&limit=10 | 0,0027 | 0,0023 | 0,0032 | Atende |
| POST /api/rankings | 0,0023 | 0,0022 | 0,0025 | Atende |
| GET /api/assets/TAEE11 | 0,0017 | 0,0016 | 0,0019 | Atende |
| GET /api/scores/meta | 0,0014 | 0,0013 | 0,0014 | Atende |

Ressalva: a medição foi local (cliente e servidor na mesma máquina), sequencial e sem concorrência. Ela não
representa latência de rede nem carga simultânea.

## Defeitos

Quatro defeitos reais (1 alta, 2 média, 1 baixa) e cinco observações. Detalhes em `DEFEITOS.md`.

## Evidências

- `resultados/report.html`, `resultados/log.html`, `resultados/output.xml`: execução Robot
- `resultados/desempenho_p95.csv`: medições de P95
- `resultados/pytest_junit.xml`: execução pytest
- `htmlcov/`: cobertura
