# Contrato de integração — Serviço de Análise (erenML)

Documento para a equipe do app (`eren-app`, Expo/React Native).

## Onde este serviço fica na arquitetura

```
App Expo (React Native)
   ├── Supabase Auth ........... login/cadastro
   ├── Supabase Postgres ....... schemas app.* e market.*
   ├── Supabase Edge Functions . proxy da brapi, WhatsApp
   └── erenML (FastAPI) ........ questionário, perfil, score  ← este serviço
```

O app fala **direto** com o serviço de análise por HTTP. Não há backend Java
no caminho: o "módulo de IA" previsto no Documento de Arquitetura é este
serviço, e o adaptador equivalente ao `IaClient` é o `lib/profileApi.ts`.

## Por que a regra não fica no app

A classificação de perfil e (depois) o score das ações vivem no pacote Python
`eren_ml`, que é **puro** — sem banco, sem framework. O mesmo módulo é usado
pela API, pelos testes automatizados e pelos notebooks de backtest. Isso
garante que a regra validada historicamente é exatamente a que roda em
produção, e permite alterar o questionário sem publicar nova versão do app.

## Como rodar

```bash
cd erenML
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                                        # 13 passed
uvicorn api.main:app --reload --host 0.0.0.0     # ouve na rede local
```

`--host 0.0.0.0` é obrigatório para o celular alcançar o serviço: sem isso o
uvicorn só aceita conexões da própria máquina.

Descubra o IP da máquina na rede (macOS): `ipconfig getifaddr en0`.
Configure no `.env` do app:

```
EXPO_PUBLIC_ML_API_URL=http://192.168.0.10:8000
```

| URL | O que é |
|---|---|
| `/` | Página de demonstração (questionário → perfil → ranking) |
| `/docs` | Swagger — contrato sempre atualizado, gerado do código |
| `GET /api/questionnaire` | Perguntas e opções |
| `POST /api/profile` | Respostas → perfil + vetor de pesos |
| `GET /api/health` | Diagnóstico |

CORS está liberado (`*`) para desenvolvimento.

---

## `GET /api/questionnaire`

Devolve as 12 perguntas **sem os pontos** (a pontuação é segredo da regra).
O app renderiza dinamicamente a partir desta resposta.

```json
{
  "version": "1.0",
  "max_points": 40,
  "questions": [
    {
      "id": "q1_idade",
      "text": "Qual a sua idade?",
      "help_text": "Quanto maior o tempo até a aposentadoria, maior a capacidade de absorver oscilações.",
      "scores": true,
      "options": [
        { "value": "ate_30", "label": "Até 30 anos" },
        { "value": "31_45", "label": "Entre 31 e 45 anos" }
      ]
    }
  ]
}
```

Ícones e emojis **não** vêm da API — ficam em
`constants/perfilQuestions.ts` (`visualDaOpcao`), mapeados por
`pergunta_id` + `opcao.value`. Opção não mapeada cai num ícone neutro.

## `POST /api/profile`

Request — as 12 respostas no formato `pergunta_id: opcao_value`:

```json
{
  "answers": {
    "q1_idade": "31_45",
    "q2_percentual_renda": "15_30",
    "q3_reserva": "3_6m",
    "q4_horizonte": "mais_10a",
    "q5_reacao_queda": "compro_mais",
    "q6_experiencia": "acoes",
    "q7_conhecimento": "intermediario",
    "q8_fatia_patrimonio": "30_60",
    "q9_preferencia": "maximo_retorno",
    "q10_dependentes": "nenhuma",
    "q11_estabilidade_renda": "estavel",
    "q12_objetivo": "renda"
  }
}
```

Response 200 (campos principais):

```json
{
  "profile": {
    "risk_score": 33,
    "max_score": 40,
    "risk_class": "arrojado",
    "risk_class_label": "Arrojado",
    "risk_class_description": "Você tem capacidade e disposição para...",
    "objective": "renda",
    "horizon": "mais_10a",
    "weight_vector_key": "renda",
    "weight_vector_label": "Renda / dividendos",
    "weight_vector": {
      "valor": 0.15, "qualidade": 0.25, "dividendos": 0.40,
      "estabilidade": 0.15, "momentum": 0.05
    },
    "safety_flags": [],
    "objective_divergence": false,
    "can_receive_recommendations": true,
    "questionnaire_version": "1.0",
    "rules_version": "0.1-dev",
    "breakdown": { "q1_idade": 3 }
  },
  "ranking": { "is_demo_data": true, "note": "...", "assets": [] },
  "disclaimer": "Ferramenta educacional de apoio à decisão..."
}
```

Response 422 — resposta faltando ou opção inválida:
`{ "detail": "Respostas faltando: q5_reacao_queda" }`

---

## O que o app grava em `app.investor_profiles`

Feito pelo `contexts/PerfilContext.tsx` (o perfil anterior vira
`is_current = false` na mesma operação — o índice `uq_profiles_current`
garante um único vigente por usuário):

| Coluna | Origem |
|---|---|
| `answers` | o objeto de respostas enviado |
| `risk_score` | `profile.risk_score` |
| `risk_class` | `profile.risk_class` |
| `objective` | `profile.objective` |
| `horizon` | `profile.horizon` |
| `weight_vector` | `profile.weight_vector` |
| `safety_flags` | códigos de `profile.safety_flags` |
| `questionnaire_version` / `rules_version` | rastreabilidade |

## Regras que o app DEVE respeitar

1. `can_receive_recommendations = false` → não exibir nem gerar sugestões de
   compra; mostrar o conteúdo educacional da trava correspondente (RN-011).
2. Cada item de `safety_flags` vira um aviso na tela de resultado.
   `blocks_recommendations = true` é bloqueio funcional, não só aviso.
3. `disclaimer` é obrigatório em toda tela de recomendação e em toda mensagem
   de WhatsApp — é o que sustenta o enquadramento como ferramenta educacional.
4. `rules_version` acompanha todo perfil, recomendação e alerta gravado.

## Estabilidade do contrato

Campos existentes não serão removidos nem renomeados sem aviso; novos podem
ser adicionados (o cliente ignora desconhecidos). `questionnaire_version` e
`rules_version` sinalizam mudanças de regra.

O bloco `ranking` hoje usa **dados ilustrativos** (`is_demo_data: true`).
Quando o motor de score entrar, só os números mudam — o formato permanece,
então a integração pode ser feita desde já.

## Próximos endpoints

| Endpoint | Status |
|---|---|
| `GET /api/questionnaire` | ✅ pronto |
| `POST /api/profile` | ✅ pronto |
| `GET /api/rankings` — ranking real do perfil | 🔜 após o motor de score |
| `GET /api/assets/{ticker}` — detalhe + breakdown + notícias | 🔜 |
| `POST /api/invest/allocate` — plano de aporte | 🔜 |
| `GET /api/portfolio/analysis` | 🔜 |
