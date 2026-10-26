*** Settings ***
Documentation       Testes FUNCIONAIS: cenários de negócio do erenML vistos de fora, pela API HTTP.
...                 Cada cenário verifica uma regra de negócio (RN), um requisito não funcional (RNF) ou uma regra do README.
...                 Testes com a tag "defeito-conhecido" falham por defeito real do sistema (ver DEFEITOS.md).
Resource            resources/api.resource
Suite Setup         Verificar Servidor No Ar
Suite Teardown      Encerrar Sessoes
Test Tags           funcional    regressao


*** Test Cases ***
TC-ML-FUN-01 Investidor com respostas típicas de conservador recebe perfil conservador
    [Documentation]    RN-003 / README (0–13 = conservador): idoso, sem experiência, vende tudo na queda -> conservador, vetor de preservação.
    ${perfil}=    Obter Perfil    ${RESPOSTAS_CONSERVADOR}
    Should Be Equal    ${perfil}[risk_class]    conservador
    Should Be True    ${perfil}[risk_score] <= 13
    Should Be Equal    ${perfil}[weight_vector_key]    preservacao
    Should Be True    ${perfil}[can_receive_recommendations]

TC-ML-FUN-02 Investidor com respostas típicas de moderado recebe perfil moderado
    [Documentation]    RN-003 / README (14–26 = moderado): mantém na queda, horizonte 3–10 anos -> moderado, vetor de equilíbrio.
    ${perfil}=    Obter Perfil    ${RESPOSTAS_MODERADO}
    Should Be Equal    ${perfil}[risk_class]    moderado
    Should Be True    14 <= ${perfil}[risk_score] <= 26
    Should Be Equal    ${perfil}[weight_vector_key]    equilibrio

TC-ML-FUN-03 Investidor com respostas típicas de arrojado recebe perfil arrojado
    [Documentation]    RN-003 / README (27–40 = arrojado): jovem, experiente, compra mais na queda -> arrojado, vetor de crescimento.
    ${perfil}=    Obter Perfil    ${RESPOSTAS_ARROJADO}
    Should Be Equal    ${perfil}[risk_class]    arrojado
    Should Be True    ${perfil}[risk_score] >= 27
    Should Be Equal    ${perfil}[weight_vector_key]    crescimento
    Should Not Be True    ${perfil}[objective_divergence]

TC-ML-FUN-04 Fronteira 13/14 separa conservador de moderado
    [Documentation]    README: fronteira conservador/moderado em 13/14 pontos.
    Perfil Deve Ter Classe E Pontos    ${RESPOSTAS_13_PONTOS}    conservador    13
    Perfil Deve Ter Classe E Pontos    ${RESPOSTAS_14_PONTOS}    moderado    14

TC-ML-FUN-05 Fronteira 26/27 separa moderado de arrojado
    [Documentation]    README: fronteira moderado/arrojado em 26/27 pontos.
    Perfil Deve Ter Classe E Pontos    ${RESPOSTAS_26_PONTOS}    moderado    26
    Perfil Deve Ter Classe E Pontos    ${RESPOSTAS_27_PONTOS}    arrojado    27

TC-ML-FUN-06 Investidor sem reserva de emergência é limitado a conservador
    [Documentation]    README (trava de segurança) / RN-012: sem reserva de emergência limita o perfil a conservador,
    ...    mesmo com todas as outras respostas arrojadas.
    ${perfil}=    Obter Perfil    ${RESPOSTAS_SEM_RESERVA}
    Should Be True    ${perfil}[risk_score] >= 27    msg=Pré-condição: pontuação bruta de arrojado
    Should Be Equal    ${perfil}[risk_class]    conservador
    Perfil Deve Conter Trava    ${perfil}    sem_reserva_emergencia

TC-ML-FUN-07 Horizonte menor que 1 ano marca o perfil como bloqueado para recomendações
    [Documentation]    RN-011: horizonte < 1 ano bloqueia sugestões de compra (can_receive_recommendations = false).
    ${perfil}=    Obter Perfil    ${RESPOSTAS_HORIZONTE_CURTO}
    Should Not Be True    ${perfil}[can_receive_recommendations]
    Perfil Deve Conter Trava    ${perfil}    horizonte_curto
    ${bloqueia}=    Evaluate    any(f["blocks_recommendations"] for f in $perfil["safety_flags"])
    Should Be True    ${bloqueia}

TC-ML-FUN-08 Horizonte menor que 1 ano não recebe sugestões de compra na resposta
    [Documentation]    RN-011: com horizonte < 1 ano o sistema não gera sugestões de compra.
    ...    Obtido: a mesma resposta traz can_receive_recommendations=false E 8 ações em ranking.assets. Ver DEF-01.
    [Tags]    defeito-conhecido
    ${resp}=    Enviar Perfil    ${RESPOSTAS_HORIZONTE_CURTO}
    Should Not Be True    ${resp.json()}[profile][can_receive_recommendations]
    Should Be Empty    ${resp.json()}[ranking][assets]
    ...    msg=RN-011 violada: perfil bloqueado recebeu ${{len($resp.json()["ranking"]["assets"])}} sugestões de compra

TC-ML-FUN-09 Objetivo de crescimento sem capacidade de risco gera divergência
    [Documentation]    README (divergência objetivo × capacidade) / RN-012: moderado que declara crescimento recebe vetor equilibrado e aviso.
    ${perfil}=    Obter Perfil    ${RESPOSTAS_MODERADO_QUER_CRESCIMENTO}
    Should Be Equal    ${perfil}[risk_class]    moderado
    Should Be True    ${perfil}[objective_divergence]
    Should Not Be Equal    ${perfil}[weight_vector_key]    crescimento
    Perfil Deve Conter Trava    ${perfil}    objetivo_divergente

TC-ML-FUN-10 Ranking de renda prioriza dividendos e difere do ranking de crescimento
    [Documentation]    RN-003: recomendações personalizadas. O top 10 de "renda" tem média de dividendos maior que o de
    ...    "crescimento"; o de "crescimento" tem momentum maior; as listas são diferentes.
    ${renda}=    Obter Ranking Por Estrategia    renda    limit=10
    ${cresc}=    Obter Ranking Por Estrategia    crescimento    limit=10
    ${a_renda}=    Set Variable    ${renda.json()}[assets]
    ${a_cresc}=    Set Variable    ${cresc.json()}[assets]
    ${div_renda}=    Media Da Dimensao    ${a_renda}    dividendos
    ${div_cresc}=    Media Da Dimensao    ${a_cresc}    dividendos
    ${mom_renda}=    Media Da Dimensao    ${a_renda}    momentum
    ${mom_cresc}=    Media Da Dimensao    ${a_cresc}    momentum
    Should Be True    ${div_renda} > ${div_cresc}    msg=Dividendos: renda=${div_renda} crescimento=${div_cresc}
    Should Be True    ${mom_cresc} > ${mom_renda}    msg=Momentum: crescimento=${mom_cresc} renda=${mom_renda}
    ${t_renda}=    Tickers Do Ranking    ${a_renda}
    ${t_cresc}=    Tickers Do Ranking    ${a_cresc}
    Should Not Be Equal    ${t_renda}    ${t_cresc}
    Log    Renda: ${t_renda} (div. médio ${div_renda}) | Crescimento: ${t_cresc} (div. médio ${div_cresc})

TC-ML-FUN-11 Ranking com vetor de pesos customizado (100% dividendos)
    [Documentation]    README (POST /api/rankings: ranking para um vetor qualquer) / RN-003: com peso só em dividendos,
    ...    o score final de cada ação é a própria nota de dividendos e o ranking segue essa nota.
    ${resp}=    Obter Ranking Com Pesos    ${PESOS_SO_DIVIDENDOS}    limit=10
    Dictionaries Should Be Equal    ${resp.json()}[weights]    ${PESOS_SO_DIVIDENDOS}
    ${ativos}=    Set Variable    ${resp.json()}[assets]
    Should Not Be Empty    ${ativos}
    FOR    ${a}    IN    @{ativos}
        Should Be Equal As Numbers    ${a}[final_score]    ${a}[scores][dividendos]    precision=2
    END
    Ranking Deve Estar Ordenado    ${ativos}
    Should Not Be Empty    ${resp.json()}[disclaimer]

TC-ML-FUN-12 Vetor customizado que não soma 1 ainda gera scores entre 0 e 100
    [Documentation]    README (pesos somam 1; score 0–100): um vetor fora da escala não pode produzir score fora de 0–100.
    ${resp}=    Obter Ranking Com Pesos    ${PESOS_NAO_SOMAM_UM}    limit=20    status=any
    IF    ${resp.status_code} == 200
        Scores Finais Devem Estar Entre 0 E 100    ${resp.json()}[assets]
    ELSE
        Should Be Equal As Integers    ${resp.status_code}    422
    END

TC-ML-FUN-13 A mesma ação recebe scores diferentes conforme o perfil
    [Documentation]    RN-003: "a mesma ação deve ter score diferente conforme o perfil" (GET /api/assets/{ticker}).
    ${resp}=    GET On Session    ${SESSAO}    /api/assets/${TICKER_EXISTENTE}    expected_status=200
    ${s}=    Set Variable    ${resp.json()}[strategy_scores]
    Log    ${TICKER_EXISTENTE}: ${s}
    ${distintos}=    Evaluate    len(set($s.values()))
    Should Be True    ${distintos} >= 2    msg=Scores iguais para todos os perfis: ${s}
    Should Not Be Equal As Numbers    ${s}[renda]    ${s}[crescimento]

TC-ML-FUN-14 A mesma ação tem scores diferentes nos rankings de perfis diferentes
    [Documentation]    RN-003: conferência pelo ranking: a mesma ação aparece com final_score diferente em "renda" e "crescimento".
    ${renda}=    Obter Ranking Por Estrategia    renda    limit=100
    ${cresc}=    Obter Ranking Por Estrategia    crescimento    limit=100
    ${s_renda}=    Evaluate    {a["ticker"]: a["final_score"] for a in $renda.json()["assets"]}
    ${s_cresc}=    Evaluate    {a["ticker"]: a["final_score"] for a in $cresc.json()["assets"]}
    Should Not Be Equal As Numbers    ${s_renda}[${TICKER_EXISTENTE}]    ${s_cresc}[${TICKER_EXISTENTE}]
    ${diferentes}=    Evaluate    sum(1 for t in r if t in c and r[t] != c[t])
    ...    namespace=${{{"r": $s_renda, "c": $s_cresc}}}
    Should Be True    ${diferentes} > 0

TC-ML-FUN-15 Recomendações de perfil conservador não contradizem o risco
    [Documentation]    RN-012: o perfil conservador nunca recebe o vetor de crescimento e sua carteira sugerida é,
    ...    em média, mais estável que a do perfil arrojado.
    ${r_cons}=    Enviar Perfil    ${RESPOSTAS_CONSERVADOR}
    ${r_arr}=    Enviar Perfil    ${RESPOSTAS_ARROJADO}
    Should Not Be Equal    ${r_cons.json()}[profile][weight_vector_key]    crescimento
    ${w}=    Set Variable    ${r_cons.json()}[profile][weight_vector]
    Should Be True    ${w}[estabilidade] >= ${w}[momentum]
    ${est_cons}=    Media Da Dimensao    ${r_cons.json()}[ranking][assets]    estabilidade
    ${est_arr}=    Media Da Dimensao    ${r_arr.json()}[ranking][assets]    estabilidade
    Should Be True    ${est_cons} > ${est_arr}    msg=Estabilidade média: conservador=${est_cons} arrojado=${est_arr}

TC-ML-FUN-16 Perfil conservador que declara crescimento não recebe estratégia agressiva
    [Documentation]    RN-012: objetivo agressivo não pode sobrepor a classe de risco conservadora.
    ${respostas}=    Copy Dictionary    ${RESPOSTAS_CONSERVADOR}
    Set To Dictionary    ${respostas}    q12_objetivo=crescimento
    ${perfil}=    Obter Perfil    ${respostas}
    Should Be Equal    ${perfil}[risk_class]    conservador
    Should Not Be Equal    ${perfil}[weight_vector_key]    crescimento
    Should Be True    ${perfil}[objective_divergence]

TC-ML-FUN-17 Ação eliminada nunca aparece em nenhum ranking
    [Documentation]    README (filtros eliminatórios): ação eliminada (BRKM5, patrimônio líquido negativo) não entra no ranking.
    FOR    ${vetor}    IN    @{VETORES}
        ${resp}=    Obter Ranking Por Estrategia    ${vetor}    limit=100
        ${tickers}=    Tickers Do Ranking    ${resp.json()}[assets]
        Should Not Contain    ${tickers}    ${TICKER_ELIMINADO}
    END
    ${meta}=    GET On Session    ${SESSAO}    /api/scores/meta
    ${eliminadas}=    Evaluate    [e["ticker"] for e in $meta.json()["eliminated"]]
    Should Contain    ${eliminadas}    ${TICKER_ELIMINADO}

TC-ML-FUN-18 Toda resposta com recomendação traz o aviso educacional
    [Documentation]    docs/INTEGRACAO.md (regra 3): disclaimer obrigatório em toda resposta de recomendação.
    ${p}=    Enviar Perfil    ${RESPOSTAS_MODERADO}
    ${g}=    Obter Ranking Por Estrategia    renda
    ${c}=    Obter Ranking Com Pesos    ${PESOS_SO_DIVIDENDOS}
    FOR    ${resp}    IN    ${p}    ${g}    ${c}
        Should Contain    ${resp.json()}[disclaimer]    não constituem recomendação de investimento
    END
