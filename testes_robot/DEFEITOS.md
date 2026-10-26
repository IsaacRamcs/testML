# Defeitos encontrados — erenML

Execução de 26/10/2026, sobre o snapshot de dados de 25/10/2026 (`data/snapshots/scores_latest.json`).
Todos os defeitos foram reproduzidos com o servidor local (`uvicorn api.main:app`). Os testes que os detectam
**foram mantidos** e estão marcados com a tag `defeito-conhecido` (Robot) ou `@pytest.mark.xfail(strict=True)` (pytest).

| ID | Requisito | Esperado | Obtido | Gravidade | Evidência (teste) |
|---|---|---|---|---|---|
| DEF-01 | RN-011: horizonte < 1 ano bloqueia sugestões de compra | `POST /api/profile` com `q4_horizonte = "menos_1a"` não devolve sugestões de compra (`ranking.assets` vazio) | A resposta traz `can_receive_recommendations: false` **e**, no mesmo corpo, 8 ações em `ranking.assets` | **Alta**: viola regra de negócio de proteção ao investidor. Hoje depende só do app obedecer à flag | `TC-ML-FUN-08` → "RN-011 violada: perfil bloqueado recebeu 8 sugestões de compra" |
| DEF-02 | README: pesos das 5 dimensões somam 1 (entrada inválida deve ser rejeitada) | `POST /api/rankings` com pesos todos 0, com `{}` ou só com dimensão desconhecida → 422 (erro do cliente) | **500 Internal Server Error** (`ZeroDivisionError` ou `ValueError` não tratado em `score_asset`) | **Média**: falha não tratada, exposta pela API | `TC-ML-INT-20`, `TC-ML-INT-21` → "500 != 422"; unitário `test_ut_pes_11` (xfail) |
| DEF-03 | README: score final é média ponderada de notas 0–100 (logo 0–100); pesos somam 1 | `POST /api/rankings` com peso negativo → 422, ou scores dentro de 0–100 | 200 com `final_score = 156.7` (CXSE3) | **Média**: score fora da escala chega ao usuário | `TC-ML-INT-22` → "CXSE3 com final_score=156.7, fora da faixa 0–100"; unitário `test_ut_pes_10` (xfail) |
| DEF-04 | Validação do parâmetro `limit` em `GET /api/rankings` | `limit=-1` → 4xx; `limit=0` → 4xx ou lista vazia | `limit=-1` → 200 com 48 ações (fatia `[:-1]` do Python); `limit=0` → 200 com as 49 ações | **Baixa**: resultado inesperado, sem risco ao investidor | `TC-ML-INT-13` → "limit=-1 respondeu 200 com 48 ações"; `TC-ML-INT-14` → "limit=0 devolveu 49 ações" |

## Observações (não classificadas como defeito)

| ID | Assunto | Detalhe |
|---|---|---|
| OBS-01 | Pontuação mínima alcançável | O README define a escala 0–40. As perguntas q1, q2 e q8 não têm opção que valha 0 ponto, então a menor pontuação possível é **3**. A escala é respeitada (`TC-ML-UT-04`), mas 0 é inalcançável. Vale confirmar com a equipe se é intencional. |
| OBS-02 | RN-011 "perfil definido antes de liberar recomendações" | `GET /api/rankings` e `POST /api/rankings` respondem sem nenhum perfil associado (a API não tem usuário/sessão). Pelo `docs/INTEGRACAO.md`, o controle fica no app. Não é testável só pela API e foi registrado como risco. |
| OBS-03 | DEF-01 × contrato | O `docs/INTEGRACAO.md` transfere ao app a obrigação de não exibir sugestões quando `can_receive_recommendations = false`. Mesmo assim, o requisito RN-011 diz que o *sistema* não gera as sugestões. Por isso DEF-01 foi mantido como defeito. A equipe pode reclassificá-lo como decisão de projeto, desde que atualize o requisito. |
| OBS-04 | Vetor de pesos que não soma 1 | `POST /api/rankings` aceita, por exemplo, todos os pesos = 5. Como `score_asset` normaliza pela soma, os scores continuam em 0–100 (`TC-ML-FUN-12` passa). Não é defeito, mas a API não valida a regra "pesos somam 1". |
| OBS-05 | Ambiente | Com `PYTHONIOENCODING=utf-8:surrogateescape` no terminal, o Robot Framework 7.5 quebra antes de executar. Solução: `$env:PYTHONIOENCODING='utf-8'`. É um problema de ambiente, não do erenML. |
