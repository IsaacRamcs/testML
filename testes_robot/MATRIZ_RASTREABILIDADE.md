# Matriz de rastreabilidade — requisitos × testes

Legenda: **UT** = unitário (pytest, `tests/unit/`); **INT** = integração (Robot); **FUN** = funcional (Robot);
**DES** = desempenho (Robot). Os IDs `TC-ML-UT-NN` estão nas docstrings dos testes pytest. ⚠ indica teste
que detecta defeito conhecido (ver `DEFEITOS.md`).

| Requisito | Descrição | Testes |
|---|---|---|
| **RN-003** | Recomendações personalizadas por perfil; mesma ação com score diferente por perfil | UT-06, UT-26, UT-31 · INT-04, INT-11, INT-16 · FUN-01, FUN-02, FUN-03, FUN-10, FUN-11, FUN-13, FUN-14 |
| **RN-011** | Perfil definido antes das recomendações; horizonte < 1 ano bloqueia sugestões de compra | UT-08, UT-09, UT-10, UT-15, UT-16, UT-17 · INT-05, INT-06, INT-07, INT-08, INT-09 · FUN-07, ⚠FUN-08 (DEF-01) · OBS-02 |
| **RN-012** | Recomendações não contradizem o perfil de risco | UT-11, UT-13, UT-14 · FUN-06, FUN-09, FUN-15, FUN-16 |
| **RNF-002** | Consultas em até 1,5 s no P95 (20 repetições por endpoint) | DES-01 a DES-06 · INT-01 (pré-condição) |
| **RNF-011** | Cobertura ≥ 70% sobre `eren_ml/` | Execução do pytest com `--cov=eren_ml` (resultado em `RELATORIO_EXECUCAO.md` e `htmlcov/`) |
| README — escala 0 a 40 | Pontuação mínima e máxima | UT-03, UT-04 (OBS-01), UT-05 · INT-02, INT-04 |
| README — fronteira 13/14 | Conservador × moderado | UT-01, UT-02 · FUN-04 |
| README — fronteira 26/27 | Moderado × arrojado | UT-01, UT-02 · FUN-05 |
| README — sem reserva de emergência | Limita o perfil a conservador | UT-07, UT-09 · FUN-06 |
| README — divergência objetivo × capacidade | Objetivo de crescimento sem capacidade de risco | UT-11, UT-12 · FUN-09, FUN-16 |
| README — pesos somam 1 | Vetores das 5 dimensões somam 1 | UT-22, ⚠UT-40 (DEF-03), ⚠UT-41 (DEF-02) · INT-04, INT-11, ⚠INT-20, ⚠INT-21 (DEF-02), ⚠INT-22 (DEF-03) · FUN-12 |
| README — score 0 a 100 | Score final de cada ação entre 0 e 100, inclusive com dimensão ausente | UT-23, UT-24, UT-25, UT-36 · INT-11, INT-16, ⚠INT-22 · FUN-12 |
| README — filtro E1 | Liquidez < R$ 1 mi/dia elimina | UT-33 |
| README — filtro E2 | Patrimônio líquido negativo elimina | UT-34 · INT-18 · FUN-17 |
| README — filtro E6 | Menos de 2 anos de histórico elimina | UT-35 |
| README — eliminadas fora do ranking | Ação eliminada nunca entra no ranking | UT-28, UT-37 · INT-18 · FUN-17 |
| README — ranking | Ordenado, respeita `limit` e `sector_cap` | UT-27, UT-29, UT-30 · INT-11, INT-12, ⚠INT-13, ⚠INT-14 (DEF-04), INT-15 |
| README — réguas pendentes / meta | `/api/scores/meta` traz a data e as réguas e regras pendentes | UT-39 (snapshot) · INT-19 |
| Determinismo | Mesma entrada, mesma saída | UT-21, UT-32, UT-38, UT-39 |
| INTEGRACAO.md — questionário sem pontos | `/api/questionnaire` não expõe a pontuação | UT-18 · INT-02, INT-03 |
| INTEGRACAO.md — contrato do perfil e erros 422 | Estrutura da resposta e validação | UT-20 · INT-04 a INT-09 |
| INTEGRACAO.md — disclaimer obrigatório | Aviso educacional em toda recomendação | INT-04 · FUN-11, FUN-18 |
| Infra — health | Serviço no ar, com scores carregados | INT-01 (e pré-condição de todas as suítes Robot) |

## Onde está cada teste unitário

| IDs | Arquivo |
|---|---|
| UT-01 a UT-21 | `tests/unit/test_perfil_unit.py` (`test_ut_per_NN`, com o mesmo NN) |
| UT-22 a UT-32, UT-40, UT-41 | `tests/unit/test_pesos_ranking_unit.py` |
| UT-33 a UT-39 | `tests/unit/test_motor_unit.py` |
| (sem ID de requisito) | `tests/unit/test_pipeline_unit.py`: funções puras do pipeline (cobertura) |
