# erenML — Motor de Análise e Perfil do Investidor

Serviço Python do projeto **Eren** (TCC — Engenharia de Software, UCB). Contém o
motor de análise que o back-end Java consome via HTTP: classificação de perfil,
score de ações e, futuramente, pipeline de dados e camada de notícias.

> ⚠️ Ferramenta educacional de apoio à decisão. Não constitui recomendação de
> investimento. Rentabilidade passada não garante resultados futuros.

## O que já funciona (v0.1)

**US03 — Definir perfil de investidor**, completo e testado:

- Questionário de 12 perguntas baseado em suitability (ANBIMA/corretoras)
- Pontuação de risco 0–40 → classe conservador / moderado / arrojado
- Travas de segurança: sem reserva de emergência limita a conservador; horizonte
  < 1 ano bloqueia sugestões de compra
- Detecção de divergência entre objetivo declarado e capacidade de risco
- **Vetor de pesos das 5 dimensões** do motor de score (valor, qualidade,
  dividendos, estabilidade, momentum) — o mecanismo que resolve o dilema
  "a mesma ação é boa para um investidor e ruim para outro"
- API REST (FastAPI) + página de demonstração
- 13 testes automatizados

## Como rodar

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pytest -q                              # 13 passed
uvicorn api.main:app --reload          # http://127.0.0.1:8000
```

| URL | O que é |
|---|---|
| `http://127.0.0.1:8000/` | Página de demonstração (questionário → perfil → ranking) |
| `http://127.0.0.1:8000/docs` | Swagger gerado automaticamente |
| `GET /api/questionnaire` | Perguntas e opções (consumido pelo app React Native) |
| `POST /api/profile` | Respostas → perfil + vetor de pesos + ranking |

## Motor de score das ações (v0.2-dev) — funcionando com dados reais

Cada ação do universo (~50 das mais líquidas da B3) recebe **5 notas de 0 a 100**,
calculadas por **percentil** (comparação com as demais ações, não limiares fixos):

| Dimensão | Réguas ativas nesta versão | Comparação | Base acadêmica |
|---|---|---|---|
| Valor | L/P, P/VP, EV/EBITDA | setor | Basu (1977); Fama & French (1992) |
| Qualidade | ROE, ROIC, margem líquida, dívida líq./patrimônio | setor | Piotroski (2000); Novy-Marx (2013) |
| Dividendos | DY médio 5 anos, consistência, payout saudável, tendência do DPA | universo | Lintner (1956) |
| Estabilidade | volatilidade 12m, queda máxima 3a, beta, porte | universo | Ang et al. (2006); Baker et al. (2011) |
| Momentum | retorno 12−1, 6−1, proximidade da máxima 52s | universo | Jegadeesh & Titman (1993); Carhart (1997) |

Antes da pontuação, **filtros eliminatórios** retiram a ação do ranking:
liquidez < R$ 1 mi/dia (E1), patrimônio líquido negativo (E2), < 2 anos de histórico (E6).

O **score final** de cada ação para um investidor = média ponderada das 5 notas com o
vetor de pesos do perfil — a mesma ação recebe scores diferentes para perfis diferentes.

**Réguas pendentes** (F-Score, FCF yield, consistência do ROE, cobertura por caixa) e os
filtros E3/E4/E5 dependem das demonstrações históricas da CVM — próxima etapa. Até lá,
seus pesos são redistribuídos dentro da dimensão e a API sinaliza isso em `/api/scores/meta`.

### Fontes de dados (provisórias)
- **Fundamentus** — múltiplos e rentabilidade de todas as ações (1 requisição)
- **Yahoo Finance** — histórico diário de 5 anos com preço ajustado e proventos

### Atualizar os dados
```bash
python -m eren_ml.pipeline.run            # coleta tudo de novo e recalcula (~1 min)
python -m eren_ml.pipeline.run --offline  # recalcula com os dados salvos em data/raw
```

### Endpoints do motor
| Endpoint | O que faz |
|---|---|
| `GET /api/rankings?vector=renda&limit=10` | Ranking por estratégia (renda, crescimento, equilibrio, preservacao) |
| `POST /api/rankings` | Ranking para um vetor de pesos qualquer (o app envia o vetor do perfil) |
| `GET /api/assets/{ticker}` | Scores, cada régua com valor, percentil e grupo de comparação |
| `GET /api/scores/meta` | Data dos dados, ações eliminadas, réguas pendentes |

Código: `eren_ml/scoring/` (regras, indicadores, motor, ranking) e `eren_ml/pipeline/` (coleta).

## Estrutura

```
erenML/
├── eren_ml/
│   └── profile/
│       ├── questionnaire.py   # 12 perguntas e pontuação (fonte única da verdade)
│       ├── classifier.py      # classificação + travas de segurança
│       ├── weights.py         # vetores de peso por perfil-objetivo + score_asset()
│       └── demo_assets.py     # scores ILUSTRATIVOS (temporário)
├── api/
│   ├── main.py                # FastAPI
│   ├── persistence.py         # gravação opcional em app.investor_profiles
│   └── static/index.html      # página de demonstração
└── tests/test_profile.py
```

O pacote `eren_ml` é puro (sem I/O, sem framework): é importado pela API, pelos
testes e pelos notebooks de backtest — garantindo que a regra validada
historicamente é exatamente a que roda em produção.

## Base acadêmica do motor de score

| Dimensão | Referência |
|---|---|
| Valor | Basu (1977); Fama & French (1992, 1993) |
| Qualidade | Piotroski (2000) — F-Score; Novy-Marx (2013); Asness, Frazzini & Pedersen (2019) |
| Dividendos | Lintner (1956) e literatura de sinalização |
| Estabilidade | Ang et al. (2006); Baker, Bradley & Wurgler (2011) |
| Momentum | Jegadeesh & Titman (1993); Carhart (1997) |

## Persistência (opcional)

Com `DATABASE_URL` no `.env` (Supabase → Connect → Session pooler), enviar
`{"persist": true}` no `POST /api/profile` grava o perfil em
`app.investor_profiles` respeitando a regra de perfil vigente único.

## Próximos passos

1. Seed do universo IBRX-100 em `market.assets`
2. Backfill de preços (yfinance) e job diário (brapi)
3. Fundamentos da CVM (DFP/ITR) → `market.fundamentals_quarterly`
4. Motor de score real → `market.scores_daily` (substitui `demo_assets.py`)
5. Backtest walk-forward 2015–2026 para validar as regras
