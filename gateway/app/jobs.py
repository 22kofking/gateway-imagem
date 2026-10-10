"""Regras do gateway: escolher a rota, enviar, consultar e finalizar jobs."""

import json
import logging
import time
import uuid

from app import db, storage
from app.config import catalog
from app.providers import PROVIDERS, ProviderError
from app.schemas import ImageRequest, JobResponse

log = logging.getLogger("gateway")


class NoRouteAvailable(Exception):
    pass


def available_routes(model: str) -> list[dict]:
    return [r for r in catalog[model]["rotas"] if PROVIDERS[r["provedor"]].configured(r)]


def create(app_name: str, req: ImageRequest) -> str:
    """Tenta as rotas do modelo em ordem até uma aceitar o pedido."""
    errors = []
    for route in available_routes(req.model):
        provider = PROVIDERS[route["provedor"]]
        try:
            provider_job_id = provider.submit(route, req)
        except ProviderError as e:
            log.warning("rota falhou, tentando a próxima: %s", e)
            errors.append(str(e))
            continue
        job_id = "img_" + uuid.uuid4().hex[:20]
        db.insert_job(job_id, app_name, req.model, provider.name, route, provider_job_id)
        return job_id
    raise NoRouteAvailable("; ".join(errors) or "nenhum provedor configurado para este modelo")


def refresh(row) -> None:
    """Consulta o provedor de um job ainda em andamento e grava o resultado."""
    route = json.loads(row["route"])
    try:
        result = PROVIDERS[row["provider"]].poll(route, row["provider_job_id"])
    except ProviderError as e:
        log.warning("falha ao consultar %s: %s", row["id"], e)
        return  # tenta de novo na próxima consulta

    if result.status == "running":
        return
    if result.status == "failed":
        db.finish_job(row["id"], "failed", [], result.error, None)
        return
    try:
        urls = storage.persist(row["app"], row["id"], result.images)
    except Exception as e:  # noqa: BLE001 - qualquer falha de storage vira erro do job
        log.exception("falha ao salvar imagens de %s", row["id"])
        db.finish_job(row["id"], "failed", [], f"falha ao salvar imagem: {e}", result.cost_usd)
        return
    db.finish_job(row["id"], "succeeded", urls, None, result.cost_usd)


def get(job_id: str, app_name: str) -> JobResponse | None:
    row = db.get_job(job_id, app_name)
    if row is None:
        return None
    if row["status"] == "running":
        refresh(row)
        row = db.get_job(job_id, app_name)
    return JobResponse(
        id=row["id"],
        model=row["model"],
        status=row["status"],
        images=json.loads(row["images"]) if row["images"] else [],
        error=row["error"],
        created_at=row["created_at"],
        finished_at=row["finished_at"],
    )


def wait(job_id: str, app_name: str, timeout: float, interval: float = 1.0) -> JobResponse:
    deadline = time.monotonic() + timeout
    while True:
        job = get(job_id, app_name)
        if job.status != "running" or time.monotonic() >= deadline:
            return job
        time.sleep(interval)
