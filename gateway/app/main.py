"""API pública do gateway de geração de imagem.

Rodar: uvicorn app.main:app --port 8000   (dentro da pasta gateway/)
Docs interativas: http://localhost:8000/docs
"""

import logging
import time

from fastapi import Depends, FastAPI, HTTPException, Response

from app import db, jobs
from app.auth import current_app
from app.config import AppKey, catalog, settings
from app.schemas import ImageRequest, JobResponse, ModelInfo

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Gateway de Imagem", version="0.1.0")


def start_of_day() -> float:
    now = time.time()
    return now - (now % 86400)  # meia-noite UTC


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/v1/models", response_model=list[ModelInfo])
def list_models(_: AppKey = Depends(current_app)):
    return [
        ModelInfo(name=name, description=cfg.get("descricao", ""), available=bool(jobs.available_routes(name)))
        for name, cfg in catalog.items()
    ]


@app.post("/v1/images", response_model=JobResponse, status_code=202)
def create_image(req: ImageRequest, response: Response, client: AppKey = Depends(current_app)):
    if req.model not in catalog:
        raise HTTPException(400, f"Modelo desconhecido. Use um de: {sorted(catalog)}")
    if client.daily_limit is not None and db.count_since(client.name, start_of_day()) >= client.daily_limit:
        raise HTTPException(429, f"Limite diário de {client.daily_limit} imagens atingido")

    try:
        job_id = jobs.create(client.name, req)
    except jobs.NoRouteAvailable as e:
        raise HTTPException(503, f"Nenhum provedor disponível: {e}") from e

    if req.wait:
        job = jobs.wait(job_id, client.name, settings.sync_wait_seconds)
    else:
        job = jobs.get(job_id, client.name)
    if job.status != "running":
        response.status_code = 200
    return job


@app.get("/v1/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, client: AppKey = Depends(current_app)):
    job = jobs.get(job_id, client.name)
    if job is None:
        raise HTTPException(404, "Job não encontrado")
    return job


@app.get("/v1/usage")
def usage(days: int = 30, client: AppKey = Depends(current_app)):
    since = start_of_day() - (days - 1) * 86400
    return {
        "app": client.name,
        "dias": days,
        "hoje": db.count_since(client.name, start_of_day()),
        "limite_diario": client.daily_limit,
        "por_modelo": db.usage(client.name, since),
    }
