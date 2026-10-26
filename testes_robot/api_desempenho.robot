*** Settings ***
Documentation       Testes de DESEMPENHO (RNF-002): consultas respondem em até 1,5 s no percentil 95.
...                 Cada endpoint principal recebe 20 requisições sequenciais (mais 1 de aquecimento, descartada).
...                 O P95 de cada caso aparece na mensagem do teste no report.html e em resultados/desempenho_p95.csv.
Resource            resources/api.resource
Suite Setup         Verificar Servidor No Ar
Suite Teardown      Encerrar Sessoes
Test Tags           desempenho    regressao


*** Test Cases ***
TC-ML-DES-01 P95 do GET /api/questionnaire
    [Documentation]    RNF-002: P95 <= 1,5 s em 20 repetições.
    P95 Deve Atender RNF-002    GET    /api/questionnaire

TC-ML-DES-02 P95 do POST /api/profile
    [Documentation]    RNF-002: P95 <= 1,5 s em 20 repetições (sem persistir).
    ${corpo}=    Create Dictionary    answers=${RESPOSTAS_MODERADO}
    P95 Deve Atender RNF-002    POST    /api/profile    ${corpo}

TC-ML-DES-03 P95 do GET /api/rankings
    [Documentation]    RNF-002: P95 <= 1,5 s em 20 repetições.
    P95 Deve Atender RNF-002    GET    /api/rankings?vector=renda&limit=10

TC-ML-DES-04 P95 do POST /api/rankings
    [Documentation]    RNF-002: P95 <= 1,5 s em 20 repetições.
    ${corpo}=    Create Dictionary    weights=${PESOS_SO_DIVIDENDOS}    limit=${10}
    P95 Deve Atender RNF-002    POST    /api/rankings    ${corpo}

TC-ML-DES-05 P95 do GET /api/assets/{ticker}
    [Documentation]    RNF-002: P95 <= 1,5 s em 20 repetições.
    P95 Deve Atender RNF-002    GET    /api/assets/${TICKER_EXISTENTE}

TC-ML-DES-06 P95 do GET /api/scores/meta
    [Documentation]    RNF-002: P95 <= 1,5 s em 20 repetições.
    P95 Deve Atender RNF-002    GET    /api/scores/meta
