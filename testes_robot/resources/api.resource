*** Settings ***
Documentation       Keywords reutilizáveis para testar a API HTTP do erenML.
...                 Nenhuma keyword envia "persist": true no POST /api/profile (não grava em banco).
Library             RequestsLibrary
Library             Collections
Library             DesempenhoLib.py
Variables           ../variables.py


*** Variables ***
${SESSAO}           eren


*** Keywords ***
Verificar Servidor No Ar
    [Documentation]    Pré-condição de toda a suíte: o serviço precisa responder em /api/health.
    ...    Se não responder, a suíte inteira falha com instrução de como subir o servidor.
    ${estado}    ${detalhe}=    Run Keyword And Ignore Error
    ...    GET    ${BASE_URL}/api/health    timeout=5    expected_status=200
    IF    '${estado}' != 'PASS'
        Fail    SERVIDOR FORA DO AR: o erenML não respondeu em ${BASE_URL}/api/health (${detalhe}). Suba o servidor com: .\\.venv\\Scripts\\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
    END
    Create Session    ${SESSAO}    ${BASE_URL}    timeout=30

Encerrar Sessoes
    Delete All Sessions

# --- Perfil ---------------------------------------------------------------------

Enviar Perfil
    [Documentation]    POST /api/profile somente com as respostas (persist nunca é enviado).
    [Arguments]    ${respostas}    ${status}=200
    ${corpo}=    Create Dictionary    answers=${respostas}
    ${resp}=    POST On Session    ${SESSAO}    /api/profile    json=${corpo}    expected_status=${status}
    RETURN    ${resp}

Enviar Corpo Bruto Para Perfil
    [Documentation]    POST /api/profile com um corpo arbitrário (para testes de validação).
    [Arguments]    ${corpo}    ${status}=any
    ${resp}=    POST On Session    ${SESSAO}    /api/profile    json=${corpo}    expected_status=${status}
    RETURN    ${resp}

Obter Perfil
    [Documentation]    Envia as respostas e devolve só o bloco "profile" da resposta.
    [Arguments]    ${respostas}
    ${resp}=    Enviar Perfil    ${respostas}
    RETURN    ${resp.json()}[profile]

Perfil Deve Conter Trava
    [Arguments]    ${perfil}    ${codigo}
    ${codigos}=    Evaluate    [f["code"] for f in $perfil["safety_flags"]]
    Should Contain    ${codigos}    ${codigo}    msg=Trava "${codigo}" não encontrada em ${codigos}

Perfil Deve Ter Classe E Pontos
    [Arguments]    ${respostas}    ${classe}    ${pontos}
    ${perfil}=    Obter Perfil    ${respostas}
    Should Be Equal As Integers    ${perfil}[risk_score]    ${pontos}
    Should Be Equal    ${perfil}[risk_class]    ${classe}

# --- Ranking --------------------------------------------------------------------

Obter Ranking Por Estrategia
    [Arguments]    ${vetor}    ${limit}=10    ${status}=200
    ${params}=    Create Dictionary    vector=${vetor}    limit=${limit}
    ${resp}=    GET On Session    ${SESSAO}    /api/rankings    params=${params}    expected_status=${status}
    RETURN    ${resp}

Obter Ranking Com Pesos
    [Arguments]    ${pesos}    ${limit}=10    ${status}=200
    ${corpo}=    Create Dictionary    weights=${pesos}    limit=${limit}
    ${resp}=    POST On Session    ${SESSAO}    /api/rankings    json=${corpo}    expected_status=${status}
    RETURN    ${resp}

Tickers Do Ranking
    [Arguments]    ${ativos}
    ${tickers}=    Evaluate    [a["ticker"] for a in $ativos]
    RETURN    ${tickers}

Media Da Dimensao
    [Arguments]    ${ativos}    ${dimensao}
    ${media}=    Evaluate
    ...    statistics.mean([a["scores"]["${dimensao}"] for a in $ativos if a["scores"]["${dimensao}"] is not None])
    ...    modules=statistics
    RETURN    ${media}

Scores Finais Devem Estar Entre 0 E 100
    [Arguments]    ${ativos}
    FOR    ${a}    IN    @{ativos}
        Should Be True    0 <= ${a}[final_score] <= 100
        ...    msg=${a}[ticker] com final_score=${a}[final_score], fora da faixa 0–100
    END

Ranking Deve Estar Ordenado
    [Arguments]    ${ativos}
    ${finais}=    Evaluate    [a["final_score"] for a in $ativos]
    ${ordenado}=    Evaluate    sorted($finais, reverse=True)
    Lists Should Be Equal    ${finais}    ${ordenado}

Pesos Devem Somar Um
    [Arguments]    ${pesos}
    ${soma}=    Evaluate    round(sum($pesos.values()), 9)
    Should Be Equal As Numbers    ${soma}    1.0

# --- Desempenho -----------------------------------------------------------------

P95 Deve Atender RNF-002
    [Documentation]    Mede ${REPETICOES_DESEMPENHO} chamadas e verifica P95 <= ${LIMITE_P95_SEGUNDOS} s.
    [Arguments]    ${metodo}    ${caminho}    ${corpo}=${None}
    ${r}=    Medir Tempo De Resposta    ${metodo}    ${BASE_URL}${caminho}    ${REPETICOES_DESEMPENHO}    ${corpo}
    Set Test Message    P95=${r}[p95] s | média=${r}[media] s | máx=${r}[maximo] s | n=${r}[n]
    Should Be True    ${r}[p95] <= ${LIMITE_P95_SEGUNDOS}
    ...    msg=RNF-002 violado: P95=${r}[p95] s > ${LIMITE_P95_SEGUNDOS} s em ${metodo} ${caminho}
