"""Formatos de entrada e saída da API pública."""

from typing import Literal

from pydantic import BaseModel, Field

SIZES = ("1024x1024", "1024x768", "768x1024", "1280x720", "720x1280")


class ImageRequest(BaseModel):
    model: str = "rapido"
    prompt: str = Field(min_length=1, max_length=2000)
    size: Literal[SIZES] = "1024x1024"  # type: ignore[valid-type]
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    wait: bool = Field(default=False, description="Esperar a imagem ficar pronta (até o limite do gateway)")

    @property
    def width(self) -> int:
        return int(self.size.split("x")[0])

    @property
    def height(self) -> int:
        return int(self.size.split("x")[1])


JobStatus = Literal["running", "succeeded", "failed"]


class JobResponse(BaseModel):
    id: str
    model: str
    status: JobStatus
    images: list[str] = []
    error: str | None = None
    cost_usd: float | None = Field(default=None, description="Custo informado pelo provedor, quando ele informa")
    created_at: float
    finished_at: float | None = None


class ModelInfo(BaseModel):
    name: str
    description: str
    available: bool
