# Suíte de testes do erenML — como executar

Três camadas:

| Camada | Ferramenta | Onde | O que testa |
|---|---|---|---|
| Unitário | pytest (+ pytest-cov) | `tests/unit/` (marcador `unit`) e `tests/test_profile.py` (já existente) | Funções puras de `eren_ml/` |
| Integração | Robot Framework + RequestsLibrary | `testes_robot/api_integracao.robot` | Contrato HTTP: status, estrutura do JSON, validações |
| Funcional | Robot Framework | `testes_robot/api_funcional.robot` | Cenários de negócio (RN-003, RN-011, RN-012, regras do README) vistos pela API |
| Desempenho | Robot Framework | `testes_robot/api_desempenho.robot` | RNF-002: P95 ≤ 1,5 s em 20 repetições por endpoint |

Documentos: `MATRIZ_RASTREABILIDADE.md`, `DEFEITOS.md` e `RELATORIO_EXECUCAO.md` (nesta pasta).

## Regras de segurança da suíte

- Nenhum teste envia `"persist": true` (nada é gravado em banco). Não defina `DATABASE_URL`.
- Nenhum teste roda `python -m eren_ml.pipeline.run` nem acessa a internet. Os testes do pipeline simulam as respostas HTTP.
- Nenhum teste escreve em `data/`. O snapshot é reconstruído **em memória** a partir de `data/raw/`.

## 1. Preparar o ambiente (PowerShell, na pasta `erenML`)

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install robotframework robotframework-requests pytest-cov
```

> **Se o Robot quebrar com `LookupError: unknown encoding: utf-8:surrogateescape`**, o terminal
> tem a variável `PYTHONIOENCODING` com um valor que o Robot não aceita. Corrija só para a sessão:
> `$env:PYTHONIOENCODING = 'utf-8'`

## 2. Testes unitários com cobertura (RNF-011)

```powershell
python -m pytest -q -rxX --cov=eren_ml --cov-report=term --cov-report=html --junitxml=resultados/pytest_junit.xml
```

- Relatório de cobertura: abra `htmlcov\index.html`.
- Só a camada unitária nova: `python -m pytest -m unit`.
- Testes marcados com `xfail` são **defeitos conhecidos** (ver `DEFEITOS.md`). Aparecem como `x` e não quebram a execução. Se o defeito for corrigido, eles passam a falhar como `XPASS(strict)`, avisando que é hora de remover a marcação.

## 3. Subir a API (necessário para o Robot)

Em um terminal separado:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Ou em segundo plano, no mesmo terminal:

```powershell
$srv = Start-Process .\.venv\Scripts\python.exe -ArgumentList "-m","uvicorn","api.main:app","--host","127.0.0.1","--port","8000" -WindowStyle Hidden -PassThru
# ... rodar os testes ...
Stop-Process -Id $srv.Id
```

## 4. Suíte Robot (integração, funcional e desempenho)

```powershell
robot --outputdir resultados testes_robot
```

Variações úteis:

```powershell
robot --outputdir resultados --include smoke testes_robot              # só o smoke
robot --outputdir resultados --include integracao testes_robot
robot --outputdir resultados --include funcional testes_robot
robot --outputdir resultados --include desempenho testes_robot
robot --outputdir resultados --exclude defeito-conhecido testes_robot  # sem os defeitos conhecidos
robot --outputdir resultados --variable BASE_URL:http://192.168.0.10:8000 testes_robot
```

Saídas em `resultados\`: `report.html` (resumo), `log.html` (passo a passo) e `desempenho_p95.csv` (P95 por endpoint).

- Toda suíte começa chamando `/api/health`. Se o servidor não estiver no ar, todos os casos falham com a mensagem
  `SERVIDOR FORA DO AR: ... Suba o servidor com: ...`.
- Casos com a tag `defeito-conhecido` **falham de propósito**: verificam o comportamento exigido pelo requisito,
  e o sistema ainda não o cumpre. Eles não foram ajustados para passar.

## Tags

| Tag | Significado |
|---|---|
| `integracao` | Contrato HTTP da API |
| `funcional` | Cenário de negócio |
| `desempenho` | Tempo de resposta (RNF-002) |
| `smoke` | Verificação rápida de que o serviço está saudável |
| `regressao` | Entra na regressão completa |
| `defeito-conhecido` | Falha por defeito real registrado em `DEFEITOS.md` |
