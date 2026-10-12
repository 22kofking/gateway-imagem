"""Formatos de entrada e saída da API pública."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MIN_SIDE, MAX_SIDE = 256, 1536  # limites do Z-Image Turbo na RunPod (cada lado)
IMAGE_MAX_CHARS = 12_000_000    # data URI de até ~9 MB


class ImageRequest(BaseModel):
    model: str = "rapido"
    prompt: str = Field(min_length=1, max_length=2000)
    size: str = Field(default="1024x1024", description=f"LARGURAxALTURA, cada lado entre {MIN_SIDE} e {MAX_SIDE}")
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    image: str | None = Field(
        default=None,
        max_length=IMAGE_MAX_CHARS,
        description="Imagem de entrada (image-to-image): link https ou data URI (data:image/png;base64,...)",
    )
    strength: float | None = Field(
        default=None, ge=0, le=1, description="Com `image`: quanto a imagem pode mudar (0 = igual, 1 = do zero)"
    )
    wait: bool = Field(default=False, description="Esperar a imagem ficar pronta (até o limite do gateway)")

    @field_validator("size")
    @classmethod
    def _size(cls, v: str) -> str:
        m = re.fullmatch(r"(\d{3,4})x(\d{3,4})", v)
        if not m or not all(MIN_SIDE <= int(n) <= MAX_SIDE for n in m.groups()):
            raise ValueError(f"use LARGURAxALTURA com cada lado entre {MIN_SIDE} e {MAX_SIDE}, ex.: 1024x448")
        return v

    @field_validator("image")
    @classmethod
    def _image(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("https://", "http://", "data:image/")):
            raise ValueError("image deve ser um link http(s) ou um data URI de imagem")
        return v

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
