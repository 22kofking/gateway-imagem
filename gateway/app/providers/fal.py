"""fal.ai via API de fila: https://fal.ai/docs/documentation/model-apis/inference/queue.md"""

import httpx

from app import clients
from app.config import settings
from app.providers.base import GeneratedImage, PollResult, ProviderError
from app.schemas import ImageRequest

QUEUE = "https://queue.fal.run"


class Fal:
    name = "fal"

    def configured(self, route: dict) -> bool:
        return bool(settings.fal_key and route.get("modelo"))

    def _headers(self) -> dict:
        return {"Authorization": f"Key {settings.fal_key}"}

    def submit(self, route: dict, req: ImageRequest) -> str:
        body = {"prompt": req.prompt, "image_size": {"width": req.width, "height": req.height}}
        if req.seed is not None:
            body["seed"] = req.seed
        try:
            r = clients.http.post(f"{QUEUE}/{route['modelo']}", headers=self._headers(), json=body)
            r.raise_for_status()
            return r.json()["request_id"]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            raise ProviderError(f"fal: {e}") from e

    def poll(self, route: dict, job_id: str) -> PollResult:
        base = f"{QUEUE}/{route['modelo']}/requests/{job_id}"
        try:
            r = clients.http.get(f"{base}/status", headers=self._headers())
            r.raise_for_status()
            if r.json().get("status") != "COMPLETED":
                return PollResult("running")
            r = clients.http.get(base, headers=self._headers())
        except (httpx.HTTPError, ValueError) as e:
            raise ProviderError(f"fal: {e}") from e

        if r.status_code >= 400:
            return PollResult("failed", error=r.text[:500])
        images = [GeneratedImage(url=img["url"]) for img in r.json().get("images", [])]
        if not images:
            return PollResult("failed", error="fal não devolveu imagens")
        return PollResult("succeeded", images=images)
