import base64
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import clients, db, storage
from app.config import AppKey, settings
from app.main import app

AUTH = {"Authorization": "Bearer chave-teste"}
PNG = b"\x89PNG fake"


class FakeProviders:
    """Simula RunPod e fal. Cada teste ajusta o comportamento pelos atributos."""

    def __init__(self):
        self.calls: list[tuple[str, str, dict | None]] = []
        self.own_endpoint_fails = False
        self.public_fails = False
        self.status = "COMPLETED"

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, url, body))

        # Seu endpoint Serverless
        if url == "https://api.runpod.ai/v2/meu-endpoint/run":
            return httpx.Response(500) if self.own_endpoint_fails else httpx.Response(200, json={"id": "rp-1"})
        if url == "https://api.runpod.ai/v2/meu-endpoint/status/rp-1":
            output = {"images": [{"base64": base64.b64encode(PNG).decode(), "content_type": "image/png"}]}
            return httpx.Response(200, json={"status": self.status, "output": output})

        # Public Endpoints da RunPod
        if url.startswith("https://api.runpod.ai/v2/") and url.endswith("/run"):
            return httpx.Response(503) if self.public_fails else httpx.Response(200, json={"id": "pub-1"})
        if "/status/pub-1" in url:
            # Formato real visto em 2026-10-10 (z-image-turbo)
            output = {"result": "https://runpod.cdn/img.png", "cost": 0.005}
            return httpx.Response(200, json={"status": self.status, "output": output})

        # fal.ai
        if url.startswith("https://queue.fal.run/") and request.method == "POST":
            return httpx.Response(200, json={"request_id": "fal-1"})
        if url.endswith("/requests/fal-1/status"):
            return httpx.Response(200, json={"status": "COMPLETED" if self.status == "COMPLETED" else "IN_PROGRESS"})
        if url.endswith("/requests/fal-1"):
            return httpx.Response(200, json={"images": [{"url": "https://fal.media/img.png"}]})

        # Download de imagem (storage)
        if url in ("https://runpod.cdn/img.png", "https://fal.media/img.png"):
            return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
        return httpx.Response(404)


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = (Body, ContentType)


@pytest.fixture
def fake(monkeypatch, tmp_path):
    fake = FakeProviders()
    monkeypatch.setattr(clients, "http", httpx.Client(transport=httpx.MockTransport(fake)))
    monkeypatch.setattr(settings, "runpod_api_key", "rp-key")
    monkeypatch.setattr(settings, "fal_key", "fal-key")
    monkeypatch.setattr(settings, "apps", [AppKey("chave-teste", "site", 3), AppKey("outra", "bot", None)])
    monkeypatch.setattr(settings, "sync_wait_seconds", 2)
    monkeypatch.setattr(settings, "s3_bucket", "")
    monkeypatch.setenv("RUNPOD_ENDPOINT_RAPIDO", "meu-endpoint")
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "test.db"))
    db.reset()
    yield fake
    db.reset()


@pytest.fixture
def s3(monkeypatch):
    s3 = FakeS3()
    monkeypatch.setattr(settings, "s3_bucket", "imagens")
    monkeypatch.setattr(settings, "s3_public_base_url", "https://img.exemplo.com")
    monkeypatch.setattr(storage, "_s3", s3)
    return s3


@pytest.fixture
def client(fake):
    return TestClient(app)
