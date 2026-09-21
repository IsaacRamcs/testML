"""Persistência opcional do perfil no banco (Supabase/Postgres).

Só é usada quando a requisição pede `persist: true` E a variável DATABASE_URL
está configurada. Mantida isolada para que a demonstração do classificador
nunca dependa do banco.

Grava em app.investor_profiles respeitando a regra de perfil vigente único
por usuário (índice uq_profiles_current).
"""
from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from eren_ml.profile.classifier import ProfileResult

load_dotenv()

DEMO_EMAIL = "demo@eren.app"
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL não configurada no .env")
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def _ensure_demo_user(conn) -> str:
    row = conn.execute(
        text("select id from app.users where email = :email"), {"email": DEMO_EMAIL}
    ).fetchone()
    if row:
        return str(row[0])
    row = conn.execute(
        text(
            "insert into app.users (name, email, password_hash, consent_lgpd_at) "
            "values ('Usuário Demo', :email, 'demo-nao-usar-em-producao', now()) "
            "returning id"
        ),
        {"email": DEMO_EMAIL},
    ).fetchone()
    return str(row[0])


def save_profile(result: ProfileResult, answers: dict[str, str], user_id: str | None = None) -> str:
    """Salva o perfil como vigente e devolve o id gerado."""
    engine = _get_engine()
    with engine.begin() as conn:
        uid = user_id or _ensure_demo_user(conn)

        # Perfil anterior deixa de ser o vigente
        conn.execute(
            text("update app.investor_profiles set is_current = false "
                 "where user_id = :uid and is_current"),
            {"uid": uid},
        )

        row = conn.execute(
            text(
                "insert into app.investor_profiles "
                "(user_id, answers, risk_score, risk_class, objective, horizon, "
                " weight_vector, safety_flags, is_current) "
                "values (:uid, cast(:answers as jsonb), :score, :risk_class, :objective, "
                " :horizon, cast(:weights as jsonb), cast(:flags as jsonb), true) "
                "returning id"
            ),
            {
                "uid": uid,
                "answers": json.dumps(answers),
                "score": result.risk_score,
                "risk_class": result.risk_class,
                "objective": result.objective,
                "horizon": result.horizon,
                "weights": json.dumps(result.weight_vector),
                "flags": json.dumps([f.code for f in result.safety_flags]),
            },
        ).fetchone()
        return str(row[0])
