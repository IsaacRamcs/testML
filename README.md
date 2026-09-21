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
