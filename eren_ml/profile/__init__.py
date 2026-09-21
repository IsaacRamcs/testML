"""Módulo de perfil do investidor (US03)."""
from .classifier import (
    InvalidAnswersError,
    ProfileResult,
    RULES_VERSION,
    classify,
    classify_risk,
    compute_risk_score,
)
from .questionnaire import MAX_POINTS, QUESTIONNAIRE_VERSION, QUESTIONS, to_dict
from .weights import DIMENSIONS, WEIGHT_VECTORS, resolve_weight_vector, score_asset

__all__ = [
    "InvalidAnswersError",
    "ProfileResult",
    "RULES_VERSION",
    "classify",
    "classify_risk",
    "compute_risk_score",
    "MAX_POINTS",
    "QUESTIONNAIRE_VERSION",
    "QUESTIONS",
    "to_dict",
    "DIMENSIONS",
    "WEIGHT_VECTORS",
    "resolve_weight_vector",
    "score_asset",
]
