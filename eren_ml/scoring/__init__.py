"""Motor de score das ações (5 dimensões, percentis, filtros eliminatórios)."""
from .engine import percentile_score, score_universe
from .ranking import rank
from .rules import RULE_VERSION
from .snapshot import build_snapshot, load_latest

__all__ = ["percentile_score", "score_universe", "rank", "RULE_VERSION",
           "build_snapshot", "load_latest"]
