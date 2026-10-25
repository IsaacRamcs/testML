"""Universo de ações analisadas pelo motor de score.

Recorte inicial: ~50 ações entre as mais líquidas da B3 (base IBRX-100),
cobrindo todos os setores relevantes. O setor define o grupo de comparação
das dimensões Valor e Qualidade; o tipo define quais réguas se aplicam
(bancos e seguradoras usam réguas adaptadas).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:
    ticker: str
    name: str
    sector: str
    type: str  # acao | banco | seguradora

    @property
    def is_financial(self) -> bool:
        return self.type in ("banco", "seguradora")


_U = [
    # Financeiro
    ("ITUB4", "Itaú Unibanco", "Financeiro", "banco"),
    ("BBDC4", "Bradesco", "Financeiro", "banco"),
    ("BBAS3", "Banco do Brasil", "Financeiro", "banco"),
    ("SANB11", "Santander Brasil", "Financeiro", "banco"),
    ("BPAC11", "BTG Pactual", "Financeiro", "banco"),
    ("BBSE3", "BB Seguridade", "Financeiro", "seguradora"),
    ("CXSE3", "Caixa Seguridade", "Financeiro", "seguradora"),
    ("PSSA3", "Porto Seguro", "Financeiro", "seguradora"),
    ("B3SA3", "B3", "Serviços Financeiros", "acao"),
    # Petróleo, gás e combustíveis
    ("PETR4", "Petrobras", "Petróleo e Gás", "acao"),
    ("PRIO3", "PRIO", "Petróleo e Gás", "acao"),
    ("RECV3", "PetroReconcavo", "Petróleo e Gás", "acao"),
    ("UGPA3", "Ultrapar", "Petróleo e Gás", "acao"),
    ("VBBR3", "Vibra Energia", "Petróleo e Gás", "acao"),
    # Mineração e siderurgia
    ("VALE3", "Vale", "Mineração e Siderurgia", "acao"),
    ("GGBR4", "Gerdau", "Mineração e Siderurgia", "acao"),
    ("GOAU4", "Metalúrgica Gerdau", "Mineração e Siderurgia", "acao"),
    ("CSNA3", "CSN", "Mineração e Siderurgia", "acao"),
    ("USIM5", "Usiminas", "Mineração e Siderurgia", "acao"),
    # Papel, celulose e química
    ("SUZB3", "Suzano", "Papel, Celulose e Química", "acao"),
    ("KLBN11", "Klabin", "Papel, Celulose e Química", "acao"),
    ("BRKM5", "Braskem", "Papel, Celulose e Química", "acao"),
    # Energia elétrica
    ("TAEE11", "Taesa", "Energia Elétrica", "acao"),
    ("EGIE3", "Engie Brasil", "Energia Elétrica", "acao"),
    ("CMIG4", "Cemig", "Energia Elétrica", "acao"),
    ("EQTL3", "Equatorial", "Energia Elétrica", "acao"),
    ("ENGI11", "Energisa", "Energia Elétrica", "acao"),
    ("CPFE3", "CPFL Energia", "Energia Elétrica", "acao"),
    # Saneamento
    ("SBSP3", "Sabesp", "Saneamento", "acao"),
    ("CSMG3", "Copasa", "Saneamento", "acao"),
    ("SAPR11", "Sanepar", "Saneamento", "acao"),
    # Bens industriais e logística
    ("WEGE3", "WEG", "Bens Industriais", "acao"),
    ("RAIL3", "Rumo", "Bens Industriais", "acao"),
    # Varejo
    ("LREN3", "Lojas Renner", "Varejo", "acao"),
    ("MGLU3", "Magazine Luiza", "Varejo", "acao"),
    ("ASAI3", "Assaí", "Varejo", "acao"),
    # Saúde
    ("RADL3", "Raia Drogasil", "Saúde", "acao"),
    ("RDOR3", "Rede D'Or", "Saúde", "acao"),
    ("HAPV3", "Hapvida", "Saúde", "acao"),
    ("FLRY3", "Fleury", "Saúde", "acao"),
    # Alimentos e bebidas
    ("ABEV3", "Ambev", "Alimentos e Bebidas", "acao"),
    ("SMTO3", "São Martinho", "Alimentos e Bebidas", "acao"),
    # Telecom e tecnologia
    ("VIVT3", "Vivo (Telefônica)", "Telecom e Tecnologia", "acao"),
    ("TIMS3", "TIM", "Telecom e Tecnologia", "acao"),
    ("TOTS3", "Totvs", "Telecom e Tecnologia", "acao"),
    # Imobiliário
    ("CYRE3", "Cyrela", "Imobiliário", "acao"),
    ("MRVE3", "MRV", "Imobiliário", "acao"),
    ("MULT3", "Multiplan", "Imobiliário", "acao"),
    # Educação
    ("YDUQ3", "Yduqs", "Educação", "acao"),
    ("COGN3", "Cogna", "Educação", "acao"),
]

UNIVERSE: dict[str, Asset] = {t: Asset(t, n, s, ty) for t, n, s, ty in _U}

#: Índice de referência para beta.
BENCHMARK = "^BVSP"
