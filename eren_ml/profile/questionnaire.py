"""Questionário de perfil do investidor (US03).

Baseado na estrutura dos questionários de suitability do mercado brasileiro
(ANBIMA / corretoras): cada resposta soma pontos de capacidade e tolerância
a risco. A última pergunta não pontua — ela define o OBJETIVO, que junto com
a classe de risco seleciona o vetor de pesos usado no motor de score.

Este módulo é a fonte única da verdade do questionário: a API o expõe ao app
e o classificador o usa para pontuar. Versionado em QUESTIONNAIRE_VERSION.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

QUESTIONNAIRE_VERSION = "1.0"


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    points: int = 0


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    options: tuple[Option, ...]
    scores: bool = True
    help_text: str | None = None

    @property
    def max_points(self) -> int:
        return max(o.points for o in self.options) if self.scores else 0


QUESTIONS: tuple[Question, ...] = (
    Question(
        id="q1_idade",
        text="Qual a sua idade?",
        options=(
            Option("ate_30", "Até 30 anos", 4),
            Option("31_45", "Entre 31 e 45 anos", 3),
            Option("46_60", "Entre 46 e 60 anos", 2),
            Option("mais_60", "Mais de 60 anos", 1),
        ),
        help_text="Quanto maior o tempo até a aposentadoria, maior a capacidade de absorver oscilações.",
    ),
    Question(
        id="q2_percentual_renda",
        text="Quanto da sua renda mensal você consegue investir?",
        options=(
            Option("menos_5", "Menos de 5%", 1),
            Option("5_15", "Entre 5% e 15%", 2),
            Option("15_30", "Entre 15% e 30%", 3),
            Option("mais_30", "Mais de 30%", 4),
        ),
    ),
    Question(
        id="q3_reserva",
        text="Você tem reserva de emergência?",
        options=(
            Option("nao", "Não tenho", 0),
            Option("menos_3m", "Sim, menos de 3 meses de custo de vida", 1),
            Option("3_6m", "Sim, de 3 a 6 meses", 3),
            Option("mais_6m", "Sim, mais de 6 meses", 4),
        ),
        help_text="Reserva de emergência é pré-requisito para investir em renda variável.",
    ),
    Question(
        id="q4_horizonte",
        text="Por quanto tempo pretende deixar o dinheiro investido?",
        options=(
            Option("menos_1a", "Menos de 1 ano", 0),
            Option("1_3a", "De 1 a 3 anos", 2),
            Option("3_10a", "De 3 a 10 anos", 3),
            Option("mais_10a", "Mais de 10 anos", 4),
        ),
    ),
    Question(
        id="q5_reacao_queda",
        text="Sua carteira cai 20% em um mês. O que você faz?",
        options=(
            Option("vendo_tudo", "Vendo tudo para não perder mais", 0),
            Option("vendo_parte", "Vendo parte para reduzir o risco", 1),
            Option("mantenho", "Mantenho e espero a recuperação", 3),
            Option("compro_mais", "Aproveito e compro mais", 4),
        ),
        help_text="Mede tolerância emocional a risco — o fator que mais destrói retorno na prática.",
    ),
    Question(
        id="q6_experiencia",
        text="Qual sua experiência com investimentos?",
        options=(
            Option("nenhuma", "Nenhuma", 0),
            Option("renda_fixa", "Só renda fixa (poupança, CDB, Tesouro)", 1),
            Option("fundos_etf", "Fundos de investimento ou ETFs", 2),
            Option("acoes", "Já invisto em ações", 3),
            Option("derivativos", "Ações e derivativos (opções, futuros)", 4),
        ),
    ),
    Question(
        id="q7_conhecimento",
        text="Como você avalia seu conhecimento sobre o mercado financeiro?",
        options=(
            Option("nenhum", "Nenhum", 0),
            Option("basico", "Básico", 1),
            Option("intermediario", "Intermediário", 2),
            Option("avancado", "Avançado", 3),
        ),
    ),
    Question(
        id="q8_fatia_patrimonio",
        text="Que fatia do seu patrimônio ficará investida em ações?",
        options=(
            Option("menos_10", "Menos de 10%", 1),
            Option("10_30", "Entre 10% e 30%", 2),
            Option("30_60", "Entre 30% e 60%", 3),
            Option("mais_60", "Mais de 60%", 4),
        ),
    ),
    Question(
        id="q9_preferencia",
        text="O que você prefere?",
        options=(
            Option("preservar", "Preservar o valor, mesmo rendendo pouco", 0),
            Option("equilibrio", "Equilíbrio entre segurança e retorno", 2),
            Option("maximo_retorno", "Máximo retorno possível, aceito perdas no caminho", 4),
        ),
    ),
    Question(
        id="q10_dependentes",
        text="Quantas pessoas dependem financeiramente da sua renda?",
        options=(
            Option("varias", "Várias", 0),
            Option("uma", "Uma", 1),
            Option("nenhuma", "Nenhuma", 2),
        ),
    ),
    Question(
        id="q11_estabilidade_renda",
        text="Sua renda é estável?",
        options=(
            Option("instavel", "Instável / autônomo sem previsibilidade", 0),
            Option("media", "Média — varia de mês a mês", 1),
            Option("estavel", "Estável", 2),
            Option("muito_estavel", "Muito estável, com outras fontes de renda", 3),
        ),
    ),
    Question(
        id="q12_objetivo",
        text="Qual é o seu objetivo principal ao investir?",
        options=(
            Option("renda", "Gerar renda passiva / me aposentar com dividendos"),
            Option("crescimento", "Fazer o patrimônio crescer o máximo possível"),
            Option("equilibrio", "Crescer com equilíbrio entre risco e retorno"),
            Option("preservacao", "Preservar o que já tenho, com segurança"),
        ),
        scores=False,
        help_text="Não pontua risco: define o objetivo, que escolhe o vetor de pesos do motor de score.",
    ),
)

QUESTIONS_BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}

#: Pontuação máxima possível no questionário (calculada, não fixa).
MAX_POINTS: int = sum(q.max_points for q in QUESTIONS)


def to_dict() -> dict:
    """Serializa o questionário para a API / app (sem expor a pontuação)."""
    return {
        "version": QUESTIONNAIRE_VERSION,
        "max_points": MAX_POINTS,
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "help_text": q.help_text,
                "scores": q.scores,
                "options": [{"value": o.value, "label": o.label} for o in q.options],
            }
            for q in QUESTIONS
        ],
    }


def to_dict_with_points() -> dict:
    """Versão completa, com pontos — uso interno / documentação do TCC."""
    return {
        "version": QUESTIONNAIRE_VERSION,
        "max_points": MAX_POINTS,
        "questions": [asdict(q) for q in QUESTIONS],
    }
