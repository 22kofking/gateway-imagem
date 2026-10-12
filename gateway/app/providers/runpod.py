"""RunPod: endpoint Serverless próprio e Public Endpoints (modelos hospedados pela RunPod).

Os dois usam a mesma API: POST /v2/{endpoint}/run e GET /v2/{endpoint}/status/{id}.
Documentação: https://docs.runpod.io/serverless/endpoints/send-requests
"""

import base64
import os

import httpx

from app import clients
from app.config import settings
from app.providers.base import GeneratedImage, PollResult, ProviderError
from app.schemas import ImageRequest

API = "https://api.runpod.ai/v2"
FAILED_STATES = {"FAILED", "CANCELLED", "TIMED_OUT"}


class _RunPodBase:
    name = "runpod"

    def endpoint(self, route: dict) -> str:
        raise NotImplementedError

    def payload(self, req: ImageRequest) -> dict:
        raise NotImplementedError

    def configured(self, route: dict) -> bool:
        return bool(settings.runpod_api_key and self.endpoint(route))

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {settings.runpod_api_key}"}

    def submit(self, route: dict, req: ImageRequest) -> str:
        try:
            r = clients.http.post(
                f"{API}/{self.endpoint(route)}/run",
                headers=self._headers(),
                json={"input": self.payload(req)},
            )
            r.raise_for_status()
            return r.json()["id"]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            raise ProviderError(f"{self.name}: {e}") from e

    def poll(self, route: dict, job_id: str) -> PollResult:
        try:
            r = clients.http.get(f"{API}/{self.endpoint(route)}/status/{job_id}", headers=self._headers())
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise ProviderError(f"{self.name}: {e}") from e

        status = data.get("status")
        if status in FAILED_STATES:
            return PollResult("failed", error=str(data.get("error") or status))
        if status != "COMPLETED":
            return PollResult("running")
        return self.parse_output(data.get("output") or {})

    def parse_output(self, output: dict) -> PollResult:
        raise NotImplementedError


class RunPodServerless(_RunPodBase):
    """Seu worker (pasta worker/). Ele devolve {"images": [{"base64": ..., "content_type": ...}]}."""

    name = "runpod"

    def endpoint(self, route: dict) -> str:
        return os.getenv(route.get("endpoint_env", ""), "") if route.get("endpoint_env") else route.get("endpoint", "")

    def payload(self, req: ImageRequest) -> dict:
        body = {"prompt": req.prompt, "width": req.width, "height": req.height}
        if req.seed is not None:
            body["seed"] = req.seed
        return body

    def parse_output(self, output: dict) -> PollResult:
        if "error" in output:
            return PollResult("failed", error=str(output["error"]))
        images = []
        for img in output.get("images", []):
            if img.get("url"):
                images.append(GeneratedImage(url=img["url"]))
            else:
                images.append(
                    GeneratedImage(
                        data=base64.b64decode(img["base64"]),
                        content_type=img.get("content_type", "image/webp"),
                    )
                )
        if not images:
            return PollResult("failed", error="worker não devolveu imagens")
        return PollResult("succeeded", images=images)


class RunPodPublic(_RunPodBase):
    """Public Endpoints: https://docs.runpod.io/public-endpoints/overview

    Devolvem {"result": <url>, "cost": ...} (alguns modelos usam "image_url").
    A URL expira em 7 dias.
    """

    name = "runpod_publico"

    def endpoint(self, route: dict) -> str:
        return route.get("endpoint", "")

    def payload(self, req: ImageRequest) -> dict:
        return {
            "prompt": req.prompt,
            "size": f"{req.width}*{req.height}",
            "seed": -1 if req.seed is None else req.seed,
        }

    def parse_output(self, output: dict) -> PollResult:
        url = output.get("result") or output.get("image_url")
        if not isinstance(url, str) or not url:
            return PollResult("failed", error=str(output.get("error") or "resposta sem URL da imagem"))
        return PollResult("succeeded", images=[GeneratedImage(url=url)], cost_usd=output.get("cost"))
