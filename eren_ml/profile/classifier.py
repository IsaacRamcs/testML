"""Classificador de perfil do investidor.

Recebe as respostas do questionário e devolve:
  - pontuação de risco e classe (conservador / moderado / arrojado)
  - objetivo declarado
  - vetor de pesos das 5 dimensões do motor de score
  - travas de segurança acionadas (reserva de emergência, horizonte curto)

Módulo puro: sem I/O, sem banco, sem framework. É importado tanto pela API
quanto pelos testes e pelos notebooks de pesquisa.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from .questionnaire import MAX_POINTS, QUESTIONS, QUESTIONS_BY_ID, QUESTIONNAIRE_VERSION
from .weights import WEIGHT_VECTOR_LABELS, resolve_weight_vector

RULES_VERSION = "0.1-dev"

#: Faixas de classificação sobre a pontuação de risco (0..MAX_POINTS).
THRESHOLD_CONSERVADOR = 13   # 0..13
THRESHOLD_MODERADO = 26      # 14..26 ; 27+ = arrojado

RISK_CLASS_LABELS = {
    "conservador": "Conservador",
    "moderado": "Moderado",
    "arrojado": "Arrojado",
}

RISK_CLASS_DESCRIPTIONS = {
    "conservador": (
        "Você prioriza segurança e tem menor capacidade ou disposição para "
        "conviver com oscilações. A carteira sugerida privilegia empresas "
        "estáveis, lucrativas e pagadoras consistentes."
    ),
    "moderado": (
        "Você aceita alguma oscilação em busca de retorno maior, mas ainda "
        "preza por estabilidade. A carteira sugerida equilibra as cinco "
        "dimensões de análise."
    ),
    "arrojado": (
        "Você tem capacidade e disposição para assumir mais risco em busca de "
        "retornos maiores. A carteira sugerida dá mais peso a valorização e "
        "qualidade, aceitando maior oscilação."
    ),
}


class InvalidAnswersError(ValueError):
    """Respostas ausentes ou com opção inexistente."""


@dataclass
class SafetyFlag:
    code: str
    title: str
    message: str
    blocks_recommendations: bool = False


@dataclass
class ProfileResult:
    risk_score: int
    max_score: int
    risk_class: str
    risk_class_label: str
    risk_class_description: str
    objective: str
    horizon: str
    weight_vector_key: str
    weight_vector_label: str
    weight_vector: dict[str, float]
    safety_flags: list[SafetyFlag] = field(default_factory=list)
    objective_divergence: bool = False
    can_receive_recommendations: bool = True
    questionnaire_version: str = QUESTIONNAIRE_VERSION
    rules_version: str = RULES_VERSION
    breakdown: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["safety_flags"] = [asdict(f) for f in self.safety_flags]
        return data


def validate_answers(answers: dict[str, str]) -> None:
    missing = [q.id for q in QUESTIONS if q.id not in answers]
    if missing:
        raise InvalidAnswersError(f"Respostas faltando: {', '.join(missing)}")
    for qid, value in answers.items():
        question = QUESTIONS_BY_ID.get(qid)
        if question is None:
            raise InvalidAnswersError(f"Pergunta desconhecida: {qid}")
        if value not in {o.value for o in question.options}:
            raise InvalidAnswersError(f"Opção inválida '{value}' para a pergunta {qid}")


def compute_risk_score(answers: dict[str, str]) -> tuple[int, dict[str, int]]:
    """Soma os pontos de risco e devolve também o detalhamento por pergunta."""
    breakdown: dict[str, int] = {}
    for question in QUESTIONS:
        if not question.scores:
            continue
        chosen = answers[question.id]
        points = next(o.points for o in question.options if o.value == chosen)
        breakdown[question.id] = points
    return sum(breakdown.values()), breakdown


def classify_risk(risk_score: int) -> str:
    if risk_score <= THRESHOLD_CONSERVADOR:
        return "conservador"
    if risk_score <= THRESHOLD_MODERADO:
        return "moderado"
    return "arrojado"


def _safety_flags(answers: dict[str, str], risk_class: str) -> tuple[list[SafetyFlag], str, bool]:
    """Travas de segurança. Retorna (flags, classe_ajustada, pode_receber_recomendacoes)."""
    flags: list[SafetyFlag] = []
    adjusted = risk_class
    can_recommend = True

    if answers["q3_reserva"] == "nao":
        flags.append(SafetyFlag(
            code="sem_reserva_emergencia",
            title="Monte sua reserva de emergência primeiro",
            message=(
                "Você indicou não ter reserva de emergência. Investir em ações sem "
                "reserva costuma forçar vendas no pior momento. Seu perfil foi limitado "
                "a Conservador — recomendamos formar de 3 a 6 meses de custo de vida em "
                "aplicações de liquidez diária antes de aumentar a exposição."
            ),
        ))
        adjusted = "conservador"

    if answers["q4_horizonte"] == "menos_1a":
        flags.append(SafetyFlag(
            code="horizonte_curto",
            title="Horizonte muito curto para renda variável",
            message=(
                "Para prazos abaixo de 1 ano, o risco de precisar vender em queda é alto. "
                "O sistema não gera sugestões de compra de ações neste cenário — o conteúdo "
                "exibido é apenas educacional."
            ),
            blocks_recommendations=True,
        ))
        adjusted = "conservador"
        can_recommend = False

    return flags, adjusted, can_recommend


def classify(answers: dict[str, str]) -> ProfileResult:
    """Ponto de entrada: respostas -> perfil completo."""
    validate_answers(answers)

    risk_score, breakdown = compute_risk_score(answers)
    raw_class = classify_risk(risk_score)
    flags, risk_class, can_recommend = _safety_flags(answers, raw_class)

    objective = answers["q12_objetivo"]
    horizon = answers["q4_horizonte"]

    vector_key, weights, divergent = resolve_weight_vector(risk_class, objective)
    if divergent:
        flags.append(SafetyFlag(
            code="objetivo_divergente",
            title="Objetivo ajustado ao seu perfil de risco",
            message=(
                "Você declarou buscar crescimento máximo, mas suas respostas indicam "
                f"perfil {RISK_CLASS_LABELS[risk_class]}. Para sua proteção, o sistema "
                "aplicou uma estratégia equilibrada em vez da agressiva."
            ),
        ))

    return ProfileResult(
        risk_score=risk_score,
        max_score=MAX_POINTS,
        risk_class=risk_class,
        risk_class_label=RISK_CLASS_LABELS[risk_class],
        risk_class_description=RISK_CLASS_DESCRIPTIONS[risk_class],
        objective=objective,
        horizon=horizon,
        weight_vector_key=vector_key,
        weight_vector_label=WEIGHT_VECTOR_LABELS[vector_key],
        weight_vector=weights,
        safety_flags=flags,
        objective_divergence=divergent,
        can_receive_recommendations=can_recommend,
        breakdown=breakdown,
    )
