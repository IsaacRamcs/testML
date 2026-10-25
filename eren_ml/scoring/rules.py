"""Regras do motor de score — versão 0.2-dev.

Tudo que é parâmetro (réguas, pesos, direções, grupos de comparação e
limiares dos filtros) mora aqui, para que cada execução seja rastreável por
RULE_VERSION. As referências acadêmicas de cada dimensão estão na
especificação técnica (seção "Motor de score").

Réguas marcadas como `available=False` fazem parte da especificação, mas
dependem de dados que esta versão da coleta ainda não obtém (ex.: F-Score
exige demonstrações históricas da CVM). Elas são exibidas como
"indisponível" e seu peso é redistribuído entre as réguas presentes.
"""
from __future__ import annotations

from dataclasses import dataclass

RULE_VERSION = "0.2-dev"


@dataclass(frozen=True)
class Regua:
    key: str            # nome do indicador na tabela
    label: str          # nome amigável
    weight: float
    direction: str      # "higher" | "lower" | "absolute" (score já vem 0-100)
    fmt: str = "num"    # num | pct | x
    available: bool = True
    note: str = ""
    what: str = ""      # o que o indicador mede (texto para o usuário)
    formula: str = ""   # como o valor bruto é calculado


@dataclass(frozen=True)
class Dimension:
    key: str
    label: str
    peer: str           # "sector" | "universe"
    reguas: tuple[Regua, ...]
    reguas_financeiro: tuple[Regua, ...] | None = None
    reference: str = ""
    what: str = ""      # o que a dimensão mede (texto para o usuário)


DIMENSIONS: tuple[Dimension, ...] = (
    Dimension(
        key="valor",
        what="Se o preço da ação está barato ou caro em relação ao que a empresa entrega (lucro, patrimônio, geração de caixa).",
        label="Valor",
        peer="sector",
        reference="Basu (1977); Fama & French (1992, 1993)",
        reguas=(
            Regua("earnings_yield", "Lucro/Preço (L/P)", 0.30, "higher", "pct",
                  what="Quanto de lucro a empresa gera por real pago na ação. Quanto maior, mais barata.",
                  formula="L/P = 1 ÷ P/L = lucro líquido dos últimos 12 meses ÷ valor de mercado (Fundamentus)"),
            Regua("pvp", "P/VP", 0.25, "lower", "x",
                  what="Quantas vezes o preço da ação vale o patrimônio contábil por ação. Quanto menor, mais barata.",
                  formula="P/VP = preço da ação ÷ (patrimônio líquido ÷ número de ações) (Fundamentus)"),
            Regua("ev_ebitda", "EV/EBITDA", 0.25, "lower", "x",
                  what="Quantos anos de geração de caixa operacional pagariam a empresa inteira, incluindo a dívida. Quanto menor, mais barata.",
                  formula="EV/EBITDA = (valor de mercado + dívida líquida) ÷ EBITDA dos últimos 12 meses (Fundamentus). EBITDA negativo vai para o fim da fila"),
            Regua("fcf_yield", "FCF yield", 0.20, "higher", "pct", available=False,
                  note="Requer fluxo de caixa livre (DFP/CVM)",
                  what="Fluxo de caixa livre gerado por real pago na ação.",
                  formula="FCF yield = fluxo de caixa livre ÷ valor de mercado"),
        ),
        reguas_financeiro=(
            Regua("earnings_yield", "Lucro/Preço (L/P)", 0.55, "higher", "pct",
                  what="Quanto de lucro a empresa gera por real pago na ação. Quanto maior, mais barata.",
                  formula="L/P = 1 ÷ P/L = lucro líquido dos últimos 12 meses ÷ valor de mercado (Fundamentus)"),
            Regua("pvp", "P/VP", 0.45, "lower", "x",
                  what="Quantas vezes o preço da ação vale o patrimônio contábil por ação. Quanto menor, mais barata.",
                  formula="P/VP = preço da ação ÷ (patrimônio líquido ÷ número de ações) (Fundamentus)"),
        ),
    ),
    Dimension(
        key="qualidade",
        what="Se a empresa é rentável, eficiente e pouco endividada.",
        label="Qualidade",
        peer="sector",
        reference="Piotroski (2000); Novy-Marx (2013); Asness, Frazzini & Pedersen (2019)",
        reguas=(
            Regua("f_score", "F-Score de Piotroski", 0.35, "higher", available=False,
                  note="Requer demonstrações de 2 anos consecutivos (DFP/CVM)",
                  what="Nota de 0 a 9 de saúde financeira (9 testes contábeis).",
                  formula="Soma de 9 critérios binários de rentabilidade, alavancagem e eficiência"),
            Regua("roe", "ROE", 0.20, "higher", "pct",
                  what="Retorno sobre o patrimônio: quanto lucro a empresa gera para cada real dos acionistas.",
                  formula="ROE = lucro líquido 12 meses ÷ patrimônio líquido (Fundamentus)"),
            Regua("roic", "ROIC", 0.15, "higher", "pct",
                  what="Retorno sobre todo o capital investido (próprio + dívida).",
                  formula="ROIC = lucro operacional após impostos ÷ capital investido (Fundamentus)"),
            Regua("net_margin", "Margem líquida", 0.10, "higher", "pct",
                  what="Quanto sobra de lucro de cada real vendido.",
                  formula="Margem líquida = lucro líquido 12 meses ÷ receita líquida 12 meses (Fundamentus)"),
            Regua("roe_stability", "Consistência do ROE (5a)", 0.10, "lower", available=False,
                  note="Requer histórico de 5 anos de ROE (DFP/CVM)",
                  what="Quanto o ROE oscila ao longo de 5 anos.",
                  formula="Desvio-padrão do ROE anual em 5 anos"),
            Regua("leverage", "Dívida líquida / Patrimônio", 0.10, "lower", "x",
                  note="Proxy de Dívida líquida/EBITDA nesta versão",
                  what="Tamanho da dívida líquida em relação ao patrimônio. Quanto menor, menos endividada.",
                  formula="Dív. líquida / PL = (dívida bruta − caixa) ÷ patrimônio líquido (Fundamentus)"),
        ),
        reguas_financeiro=(
            Regua("roe", "ROE", 0.40, "higher", "pct",
                  what="Retorno sobre o patrimônio: quanto lucro a empresa gera para cada real dos acionistas.",
                  formula="ROE = lucro líquido 12 meses ÷ patrimônio líquido (Fundamentus)"),
            Regua("roe_stability", "Consistência do ROE (5a)", 0.30, "lower", available=False,
                  note="Requer histórico de 5 anos de ROE (DFP/CVM)",
                  what="Quanto o ROE oscila ao longo de 5 anos.",
                  formula="Desvio-padrão do ROE anual em 5 anos"),
            Regua("profit_trend", "Tendência de lucro (3a)", 0.30, "higher", available=False,
                  note="Requer histórico de lucros (DFP/CVM)",
                  what="Se o lucro vem crescendo nos últimos 3 anos.",
                  formula="Inclinação do lucro líquido anual em 3 anos"),
        ),
    ),
    Dimension(
        key="dividendos",
        what="Se a empresa paga proventos altos, de forma regular e sustentável.",
        label="Dividendos",
        peer="universe",
        reference="Lintner (1956) — sinalização e sustentabilidade de proventos",
        reguas=(
            Regua("dy_5y_avg", "Dividend yield médio (5 anos)", 0.30, "higher", "pct",
                  what="Quanto a ação pagou de proventos por ano, em % do preço, na média dos últimos 5 anos.",
                  formula="Para cada um dos 5 anos fechados: proventos por ação pagos no ano ÷ preço médio de fechamento do ano. Depois, média simples dos anos (Yahoo Finance)"),
            Regua("div_consistency_score", "Consistência de pagamento", 0.25, "absolute",
                  what="Em quantos dos últimos anos a empresa pagou algum provento.",
                  formula="Nota = 100 × (anos com provento ÷ anos observados), nos últimos 5 anos fechados"),
            Regua("payout_score", "Payout saudável", 0.20, "absolute",
                  what="Se a fatia do lucro distribuída é sustentável: nem pouco, nem mais do que a empresa lucra.",
                  formula="Payout = dividend yield 12m × P/L. Faixas fixas: 30% a 80% = 100 pts; 10–30% ou 80–100% = 50 pts; abaixo de 10% ou acima de 100% = 0 pts"),
            Regua("cash_coverage", "Cobertura por caixa", 0.15, "absolute", available=False,
                  note="Requer fluxo de caixa livre (DFP/CVM)",
                  what="Se o caixa gerado cobre os proventos pagos.",
                  formula="Fluxo de caixa livre ÷ proventos pagos"),
            Regua("dpa_trend_score", "Tendência do dividendo por ação", 0.10, "absolute",
                  what="Se o provento por ação está crescendo ou caindo.",
                  formula="Compara a média de proventos por ação dos 2 últimos anos com a dos 2 anos anteriores: igual ou maior = 100 pts; menor = 0 pts"),
        ),
    ),
    Dimension(
        key="estabilidade",
        what="Quanto o preço da ação oscila e cai em momentos ruins.",
        label="Estabilidade",
        peer="universe",
        reference="Ang et al. (2006); Baker, Bradley & Wurgler (2011)",
        reguas=(
            Regua("vol_252", "Volatilidade (12 meses)", 0.40, "lower", "pct",
                  what="Quanto o preço oscila no dia a dia, em termos anuais. Quanto menor, mais estável.",
                  formula="Desvio-padrão dos retornos diários dos últimos 252 pregões × √252 (Yahoo Finance, preço ajustado)"),
            Regua("mdd_3y", "Queda máxima (3 anos)", 0.25, "lower", "pct",
                  what="A maior queda do pico ao fundo nos últimos 3 anos. Quanto menor, melhor.",
                  formula="Maior valor de (1 − preço ÷ maior preço até aquele dia), nos últimos 756 pregões"),
            Regua("beta", "Beta vs Ibovespa", 0.20, "lower", "x",
                  what="Quanto a ação costuma se mover quando o Ibovespa se move 1%. Abaixo de 1 = oscila menos que o mercado.",
                  formula="Inclinação da regressão dos retornos diários da ação contra os do Ibovespa, 252 pregões"),
            Regua("market_cap", "Porte (valor de mercado)", 0.15, "higher", "brl",
                  what="Tamanho da empresa na bolsa. Empresas maiores tendem a ser mais estáveis.",
                  formula="Valor de mercado = patrimônio líquido × P/VP (Fundamentus)"),
        ),
    ),
    Dimension(
        key="momentum",
        what="Se o preço da ação vem em tendência de alta ou de queda.",
        label="Momentum",
        peer="universe",
        reference="Jegadeesh & Titman (1993); Carhart (1997); George & Hwang (2004)",
        reguas=(
            Regua("mom_12_1", "Retorno 12m (exceto último mês)", 0.60, "higher", "pct",
                  what="Quanto a ação subiu ou caiu em 12 meses, ignorando o último mês (que tende a reverter).",
                  formula="Preço ajustado de 21 pregões atrás ÷ preço ajustado de 252 pregões atrás − 1"),
            Regua("mom_6_1", "Retorno 6m (exceto último mês)", 0.25, "higher", "pct",
                  what="Quanto a ação subiu ou caiu em 6 meses, ignorando o último mês.",
                  formula="Preço ajustado de 21 pregões atrás ÷ preço ajustado de 126 pregões atrás − 1"),
            Regua("dist_52w_high", "Proximidade da máxima de 52 semanas", 0.15, "higher", "pct",
                  what="Quão perto o preço está da máxima do último ano. 100% = está na máxima.",
                  formula="Preço ajustado de hoje ÷ maior preço ajustado dos últimos 252 pregões"),
        ),
    ),
)

#: Grupos com menos membros que isto usam o universo inteiro como comparação
#: (percentil em grupo de 2 ou 3 ações é ruído, não informação).
MIN_PEER_GROUP = 4

#: Réguas com cobertura menor que isto no universo são tratadas como indisponíveis.
MIN_COVERAGE = 0.5

# --- Filtros eliminatórios ---------------------------------------------------
MIN_LIQUIDITY_BRL = 1_000_000      # E1 — volume financeiro médio diário
MIN_HISTORY_DAYS = 504             # E6 — ~2 anos de pregões

ELIMINATION_RULES = {
    "E1": "Liquidez média diária abaixo de R$ 1 milhão",
    "E2": "Patrimônio líquido negativo",
    "E6": "Menos de 2 anos de histórico de negociação",
}

#: Regras da especificação que dependem de dados ainda não coletados.
PENDING_RULES = {
    "E3": "Prejuízo em 3 dos últimos 5 anos (requer DFP/CVM)",
    "E4": "Dívida líquida/EBITDA acima do limite setorial (requer DFP/CVM)",
    "E5": "Recuperação judicial (requer camada de notícias/fatos relevantes)",
}
