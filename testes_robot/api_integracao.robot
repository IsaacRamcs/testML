*** Settings ***
Documentation       Testes de INTEGRAÇÃO da API HTTP do erenML (contrato, códigos de status, validação).
...                 Resultados esperados: README.md, docs/INTEGRACAO.md e requisitos do Documento de Visão.
...                 Testes com a tag "defeito-conhecido" falham por defeito real do sistema (ver DEFEITOS.md).
Resource            resources/api.resource
Suite Setup         Verificar Servidor No Ar
Suite Teardown      Encerrar Sessoes
Test Tags           integracao    regressao


*** Test Cases ***
TC-ML-INT-01 Health responde 200 com scores disponíveis
    [Documentation]    Infra / RNF-002 (pré-condição): GET /api/health responde 200, status "ok" e scores carregados.
    [Tags]    smoke
    ${resp}=    GET On Session    ${SESSAO}    /api/health    expected_status=200
    Should Be Equal    ${resp.json()}[status]    ok
    Should Be True    ${resp.json()}[scores_available]
    Should Not Be Empty    ${resp.json()}[scores_as_of]

TC-ML-INT-02 Questionário tem 12 perguntas e versão
    [Documentation]    README (US03): questionário de 12 perguntas, com version e max_points = 40.
    [Tags]    smoke
    ${resp}=    GET On Session    ${SESSAO}    /api/questionnaire    expected_status=200
    ${q}=    Set Variable    ${resp.json()}
    Length Should Be    ${q}[questions]    12
    Should Not Be Empty    ${q}[version]
    Should Be Equal As Integers    ${q}[max_points]    40
    FOR    ${p}    IN    @{q}[questions]
        Dictionary Should Contain Key    ${p}    id
        Dictionary Should Contain Key    ${p}    text
        Should Not Be Empty    ${p}[options]
    END

TC-ML-INT-03 Questionário não expõe a pontuação das opções
    [Documentation]    docs/INTEGRACAO.md: "Devolve as 12 perguntas sem os pontos (a pontuação é segredo da regra)".
    ${resp}=    GET On Session    ${SESSAO}    /api/questionnaire    expected_status=200
    FOR    ${p}    IN    @{resp.json()}[questions]
        FOR    ${o}    IN    @{p}[options]
            ${chaves}=    Get Dictionary Keys    ${o}
            Lists Should Be Equal    ${chaves}    ${{["label", "value"]}}
        END
    END
    Should Not Contain    ${resp.text}    "points"

TC-ML-INT-04 Perfil com respostas válidas retorna a estrutura do contrato
    [Documentation]    docs/INTEGRACAO.md (POST /api/profile, Response 200) e RN-003: perfil, vetor de pesos, ranking e disclaimer.
    [Tags]    smoke
    ${resp}=    Enviar Perfil    ${RESPOSTAS_MODERADO}
    ${corpo}=    Set Variable    ${resp.json()}
    FOR    ${chave}    IN    profile    ranking    disclaimer
        Dictionary Should Contain Key    ${corpo}    ${chave}
    END
    Should Be Equal    ${corpo}[persisted]    ${False}
    ${perfil}=    Set Variable    ${corpo}[profile]
    FOR    ${chave}    IN    risk_score    max_score    risk_class    risk_class_label    objective
    ...    horizon    weight_vector_key    weight_vector_label    weight_vector    safety_flags
    ...    objective_divergence    can_receive_recommendations    questionnaire_version
    ...    rules_version    breakdown
        Dictionary Should Contain Key    ${perfil}    ${chave}
    END
    Should Be True    0 <= ${perfil}[risk_score] <= 40
    Should Be Equal As Integers    ${perfil}[max_score]    40
    Pesos Devem Somar Um    ${perfil}[weight_vector]
    Dictionary Should Contain Key    ${corpo}[ranking]    assets
    Dictionary Should Contain Key    ${corpo}[ranking]    is_demo_data
    Should Not Be Empty    ${corpo}[disclaimer]

TC-ML-INT-05 Perfil com resposta faltando é rejeitado com 422
    [Documentation]    docs/INTEGRACAO.md: Response 422 — resposta faltando, detail cita a pergunta. Pré-requisito de RN-011.
    ${respostas}=    Copy Dictionary    ${RESPOSTAS_MODERADO}
    Remove From Dictionary    ${respostas}    q5_reacao_queda
    ${resp}=    Enviar Perfil    ${respostas}    status=422
    Should Contain    ${resp.json()}[detail]    q5_reacao_queda

TC-ML-INT-06 Perfil com opção inválida é rejeitado com 422
    [Documentation]    docs/INTEGRACAO.md: Response 422 — opção inválida.
    ${respostas}=    Copy Dictionary    ${RESPOSTAS_MODERADO}
    Set To Dictionary    ${respostas}    q1_idade=opcao_inexistente
    ${resp}=    Enviar Perfil    ${respostas}    status=422
    Should Contain    ${resp.json()}[detail]    opcao_inexistente

TC-ML-INT-07 Perfil com pergunta desconhecida é rejeitado com 422
    [Documentation]    Validação de entrada do POST /api/profile (pergunta fora do questionário).
    ${respostas}=    Copy Dictionary    ${RESPOSTAS_MODERADO}
    Set To Dictionary    ${respostas}    q99_inexistente=x
    ${resp}=    Enviar Perfil    ${respostas}    status=422
    Should Contain    ${resp.json()}[detail]    q99_inexistente

TC-ML-INT-08 Perfil com corpo vazio é rejeitado com 422
    [Documentation]    Validação do FastAPI/Pydantic: corpo {} sem "answers" -> 422.
    ${vazio}=    Create Dictionary
    ${resp}=    Enviar Corpo Bruto Para Perfil    ${vazio}    status=422
    Should Be Equal    ${resp.json()}[detail][0][loc][-1]    answers

TC-ML-INT-09 Perfil com tipo errado é rejeitado com 422
    [Documentation]    Validação do FastAPI/Pydantic: "answers" como lista e resposta numérica -> 422.
    ${corpo}=    Create Dictionary    answers=${{[1, 2]}}
    Enviar Corpo Bruto Para Perfil    ${corpo}    status=422
    ${respostas}=    Copy Dictionary    ${RESPOSTAS_MODERADO}
    Set To Dictionary    ${respostas}    q1_idade=${3}
    Enviar Perfil    ${respostas}    status=422

TC-ML-INT-10 Ranking com estratégia inválida é rejeitado com 422
    [Documentation]    README: estratégias válidas são renda, crescimento, equilibrio e preservacao.
    ${resp}=    Obter Ranking Por Estrategia    especulacao    status=422
    Should Contain    ${resp.json()}[detail]    renda

TC-ML-INT-11 Ranking responde para as 4 estratégias com pesos que somam 1
    [Documentation]    README: pesos das 5 dimensões somam 1; ranking ordenado com scores 0–100 (RN-003).
    [Tags]    smoke
    FOR    ${vetor}    IN    @{VETORES}
        ${resp}=    Obter Ranking Por Estrategia    ${vetor}    limit=10
        Should Be Equal    ${resp.json()}[vector]    ${vetor}
        Pesos Devem Somar Um    ${resp.json()}[weights]
        Length Should Be    ${resp.json()}[assets]    10
        Ranking Deve Estar Ordenado    ${resp.json()}[assets]
        Scores Finais Devem Estar Entre 0 E 100    ${resp.json()}[assets]
    END

TC-ML-INT-12 Ranking com limit muito grande devolve no máximo as ações elegíveis
    [Documentation]    Limite extremo superior: limit=100000 não pode passar do número de ações elegíveis.
    ${resp}=    Obter Ranking Por Estrategia    equilibrio    limit=100000
    ${n}=    Get Length    ${resp.json()}[assets]
    Should Be True    0 < ${n} <= ${resp.json()}[eligible]

TC-ML-INT-13 Ranking com limit negativo é rejeitado
    [Documentation]    Limite extremo inferior: limit=-1 é entrada inválida e deveria ser rejeitado (4xx).
    ...    Obtido: 200 com 48 ações (fatiamento Python [:-1]). Ver DEF-04.
    [Tags]    defeito-conhecido
    ${resp}=    Obter Ranking Por Estrategia    equilibrio    limit=-1    status=any
    Should Be True    400 <= ${resp.status_code} < 500
    ...    msg=limit=-1 respondeu ${resp.status_code} com ${{len($resp.json().get("assets", []))}} ações (esperado 4xx)

TC-ML-INT-14 Ranking com limit zero não devolve o universo inteiro
    [Documentation]    Limite extremo: limit=0 deveria ser rejeitado (4xx) ou devolver lista vazia.
    ...    Obtido: 200 com todas as ações elegíveis. Ver DEF-04.
    [Tags]    defeito-conhecido
    ${resp}=    Obter Ranking Por Estrategia    equilibrio    limit=0    status=any
    IF    ${resp.status_code} == 200
        Should Be Empty    ${resp.json()}[assets]    msg=limit=0 devolveu ${{len($resp.json()["assets"])}} ações
    ELSE
        Should Be True    400 <= ${resp.status_code} < 500
    END

TC-ML-INT-15 Ranking com limit não numérico é rejeitado com 422
    [Documentation]    Validação de tipo do parâmetro limit.
    Obter Ranking Por Estrategia    equilibrio    limit=abc    status=422

TC-ML-INT-16 Detalhe de ação existente
    [Documentation]    README (GET /api/assets/{ticker}): 5 scores 0–100 e score por estratégia (RN-003). Ticker em minúsculas também é aceito.
    [Tags]    smoke
    ${resp}=    GET On Session    ${SESSAO}    /api/assets/${TICKER_EXISTENTE.lower()}    expected_status=200
    ${ativo}=    Set Variable    ${resp.json()}[asset]
    Should Be Equal    ${ativo}[ticker]    ${TICKER_EXISTENTE}
    FOR    ${d}    IN    @{DIMENSOES}
        Should Be True    0 <= ${ativo}[scores][${d}] <= 100
    END
    FOR    ${vetor}    IN    @{VETORES}
        Should Be True    0 <= ${resp.json()}[strategy_scores][${vetor}] <= 100
    END
    Dictionary Should Contain Key    ${ativo}    breakdown

TC-ML-INT-17 Detalhe de ação inexistente responde 404
    [Documentation]    README (GET /api/assets/{ticker}): ticker fora do universo -> 404 com mensagem.
    ${resp}=    GET On Session    ${SESSAO}    /api/assets/${TICKER_INEXISTENTE}    expected_status=404
    Should Contain    ${resp.json()}[detail]    ${TICKER_INEXISTENTE}

TC-ML-INT-18 Ação eliminada aparece marcada e sem score por estratégia
    [Documentation]    README (filtros eliminatórios E2): patrimônio líquido negativo retira a ação do ranking.
    ${resp}=    GET On Session    ${SESSAO}    /api/assets/${TICKER_ELIMINADO}    expected_status=200
    Should Be True    ${resp.json()}[asset][eliminated]
    ${codigos}=    Evaluate    [e["code"] for e in $resp.json()["asset"]["eliminations"]]
    Should Contain    ${codigos}    E2
    FOR    ${vetor}    IN    @{VETORES}
        Should Be Equal    ${resp.json()}[strategy_scores][${vetor}]    ${None}
    END

TC-ML-INT-19 Meta dos scores traz data e réguas pendentes
    [Documentation]    README (GET /api/scores/meta): data dos dados, ações eliminadas e réguas pendentes (E3/E4/E5).
    [Tags]    smoke
    ${resp}=    GET On Session    ${SESSAO}    /api/scores/meta    expected_status=200
    ${m}=    Set Variable    ${resp.json()}
    Should Match Regexp    ${m}[as_of]    ^\\d{4}-\\d{2}-\\d{2}$
    Should Not Be Empty    ${m}[data_quality][unavailable_reguas]
    FOR    ${regra}    IN    E3    E4    E5
        Dictionary Should Contain Key    ${m}[data_quality][pending_rules]    ${regra}
    END
    Should Be Equal As Integers    ${m}[universe_size]    ${{$m["eligible"] + len($m["eliminated"])}}

TC-ML-INT-20 Ranking customizado com pesos zerados é rejeitado com 422
    [Documentation]    README: pesos das 5 dimensões somam 1. Vetor todo zero é entrada inválida -> 422.
    ...    Obtido: 500 Internal Server Error (divisão por zero). Ver DEF-02.
    [Tags]    defeito-conhecido
    ${resp}=    Obter Ranking Com Pesos    ${PESOS_ZERADOS}    status=any
    Should Be Equal As Integers    ${resp.status_code}    422

TC-ML-INT-21 Ranking customizado com dimensão desconhecida é rejeitado com 422
    [Documentation]    README: o vetor de pesos é sobre as 5 dimensões. Vetor sem nenhuma delas -> 422.
    ...    Obtido: 500 Internal Server Error. Ver DEF-02.
    [Tags]    defeito-conhecido
    ${resp}=    Obter Ranking Com Pesos    ${PESOS_DIMENSAO_DESCONHECIDA}    status=any
    Should Be Equal As Integers    ${resp.status_code}    422

TC-ML-INT-22 Ranking customizado com peso negativo não gera score fora de 0 a 100
    [Documentation]    README: score final é média ponderada de notas 0–100, logo também 0–100; pesos somam 1.
    ...    Esperado: 422 ou scores em 0–100. Obtido: 200 com final_score acima de 100. Ver DEF-03.
    [Tags]    defeito-conhecido
    ${resp}=    Obter Ranking Com Pesos    ${PESOS_NEGATIVOS}    status=any
    IF    ${resp.status_code} == 200
        Scores Finais Devem Estar Entre 0 E 100    ${resp.json()}[assets]
    ELSE
        Should Be Equal As Integers    ${resp.status_code}    422
    END
