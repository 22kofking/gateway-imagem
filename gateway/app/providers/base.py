"""Interface comum dos provedores de GPU."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.schemas import ImageRequest


class ProviderError(Exception):
    """O provedor recusou ou não respondeu ao pedido."""


@dataclass
class GeneratedImage:
    """Uma imagem pronta: ou já tem URL, ou veio em bytes (base64 do worker)."""

    url: str | None = None
    data: bytes | None = None
    content_type: str = "image/png"


@dataclass
class PollResult:
    status: Literal["running", "succeeded", "failed"]
    images: list[GeneratedImage] = field(default_factory=list)
    error: str | None = None
    cost_usd: float | None = None


class Provider(Protocol):
    name: str

    def configured(self, route: dict) -> bool:
        """A rota tem chave e endpoint para ser usada?"""

    def submit(self, route: dict, req: ImageRequest) -> str:
        """Envia o pedido e devolve o id do job no provedor."""

    def poll(self, route: dict, job_id: str) -> PollResult:
        """Consulta o job no provedor."""
