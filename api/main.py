"""API do serviço de análise Eren (FastAPI).

Endpoints desta versão (US03 — Definir perfil de investidor):

    GET  /api/questionnaire   -> perguntas e opções (consumido pelo app RN)
    POST /api/profile         -> respostas -> perfil + vetor de pesos + ranking demo
    GET  /api/health          -> status do serviço
    GET  /                    -> página de demonstração

Rodar:  uvicorn api.main:app --reload
Docs:   http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from eren_ml import __version__
from eren_ml.profile import InvalidAnswersError, classify, to_dict
from eren_ml.profile.demo_assets import IS_DEMO_DATA, rank_demo_assets

DISCLAIMER = (
    "Ferramenta educacional de apoio à decisão. As informações apresentadas não "
    "constituem recomendação de investimento. Rentabilidade passada não garante "
    "resultados futuros."
)

app = FastAPI(
    title="Eren — Serviço de Análise",
    description="Motor de perfil do investidor e score de ações. " + DISCLAIMER,
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TCC/dev; restringir na fase de produção
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnswersPayload(BaseModel):
    answers: dict[str, str] = Field(
        ...,
        description="Mapa pergunta_id -> opção escolhida",
        json_schema_extra={"example": {
            "q1_idade": "31_45", "q2_percentual_renda": "15_30", "q3_reserva": "3_6m",
            "q4_horizonte": "mais_10a", "q5_reacao_queda": "compro_mais",
            "q6_experiencia": "acoes", "q7_conhecimento": "intermediario",
            "q8_fatia_patrimonio": "30_60", "q9_preferencia": "maximo_retorno",
            "q10_dependentes": "nenhuma", "q11_estabilidade_renda": "estavel",
            "q12_objetivo": "renda",
        }},
    )
    persist: bool = Field(False, description="Se true, salva o perfil no banco (requer DATABASE_URL)")


@app.get("/api/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok", "version": __version__, "database_configured": bool(os.getenv("DATABASE_URL"))}


@app.get("/api/questionnaire", tags=["perfil"])
def get_questionnaire() -> dict:
    """Perguntas do questionário de perfil (US03)."""
    return to_dict()


@app.post("/api/profile", tags=["perfil"])
def post_profile(payload: AnswersPayload) -> dict:
    """Classifica o perfil e devolve o vetor de pesos + ranking ilustrativo."""
    try:
        result = classify(payload.answers)
    except InvalidAnswersError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    response = {
        "profile": result.to_dict(),
        "ranking": {
            "is_demo_data": IS_DEMO_DATA,
            "note": (
                "Scores ilustrativos — serão substituídos pela tabela market.scores_daily "
                "quando o pipeline e o motor de score estiverem prontos."
            ),
            "assets": rank_demo_assets(result.weight_vector),
        },
        "disclaimer": DISCLAIMER,
        "persisted": False,
    }

    if payload.persist:
        try:
            from api.persistence import save_profile  # import tardio: opcional
            response["persisted"] = True
            response["profile_id"] = save_profile(result, payload.answers)
        except Exception as exc:  # nunca derruba a demonstração
            response["persist_error"] = f"{type(exc).__name__}: {exc}"

    return response


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def demo_page() -> str:
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
