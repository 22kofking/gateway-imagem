"""Configuração do gateway: variáveis de ambiente e catálogo de modelos."""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CATALOG_PATH = Path(os.getenv("GATEWAY_CATALOG", Path(__file__).parent.parent / "modelos.toml"))


@dataclass(frozen=True)
class AppKey:
    """Um app cliente: a chave que ele usa e quantas imagens pode gerar por dia."""

    key: str
    name: str
    daily_limit: int | None


@dataclass
class Settings:
    runpod_api_key: str = ""
    fal_key: str = ""
    db_path: str = "gateway.db"
    apps: list[AppKey] = field(default_factory=list)
    sync_wait_seconds: int = 60

    # Storage S3/R2 (opcional). Sem isso, as URLs dos provedores são devolvidas
    # direto (as da RunPod expiram em 7 dias).
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_public_base_url: str = ""

    @property
    def storage_enabled(self) -> bool:
        return bool(self.s3_bucket and self.s3_public_base_url)


def parse_app_keys(raw: str) -> list[AppKey]:
    """Lê "chave:app[:limite_dia],chave2:app2" ."""
    apps = []
    for item in filter(None, (part.strip() for part in raw.split(","))):
        parts = item.split(":")
        if len(parts) < 2:
            continue
        limit = int(parts[2]) if len(parts) > 2 and parts[2] else None
        apps.append(AppKey(key=parts[0], name=parts[1], daily_limit=limit))
    return apps


def load_settings() -> Settings:
    return Settings(
        runpod_api_key=os.getenv("RUNPOD_API_KEY", ""),
        fal_key=os.getenv("FAL_KEY", ""),
        db_path=os.getenv("GATEWAY_DB", "gateway.db"),
        apps=parse_app_keys(os.getenv("GATEWAY_APP_KEYS", "")),
        sync_wait_seconds=int(os.getenv("GATEWAY_SYNC_WAIT", "60")),
        s3_bucket=os.getenv("S3_BUCKET", ""),
        s3_endpoint_url=os.getenv("S3_ENDPOINT_URL", ""),
        s3_access_key=os.getenv("S3_ACCESS_KEY_ID", ""),
        s3_secret_key=os.getenv("S3_SECRET_ACCESS_KEY", ""),
        s3_public_base_url=os.getenv("S3_PUBLIC_BASE_URL", "").rstrip("/"),
    )


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, dict]:
    """Catálogo: nome público do modelo -> descrição e rotas em ordem de preferência."""
    with open(path, "rb") as f:
        return tomllib.load(f)["modelos"]


settings = load_settings()
catalog = load_catalog()
