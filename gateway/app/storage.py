"""Guarda as imagens num bucket S3/R2 nosso, para as URLs não expirarem.

Sem bucket configurado: URLs dos provedores passam direto e imagens em bytes
viram data URI (serve para testes, não para produção).
"""

import base64
import mimetypes

from app import clients
from app.config import settings
from app.providers import GeneratedImage

_s3 = None


def _client():
    global _s3
    if _s3 is None:
        import boto3  # só é necessário quando o storage está ligado

        _s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key or None,
            aws_secret_access_key=settings.s3_secret_key or None,
        )
    return _s3


def persist(app: str, job_id: str, images: list[GeneratedImage]) -> list[str]:
    if not settings.storage_enabled:
        return [img.url or _data_uri(img) for img in images]

    urls = []
    for i, img in enumerate(images):
        data, content_type = img.data, img.content_type
        if data is None:
            r = clients.http.get(img.url)
            r.raise_for_status()
            data = r.content
            content_type = r.headers.get("content-type", content_type).split(";")[0]
        ext = mimetypes.guess_extension(content_type) or ".png"
        key = f"{app}/{job_id}/{i}{ext}"
        _client().put_object(Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type)
        urls.append(f"{settings.s3_public_base_url}/{key}")
    return urls


def _data_uri(img: GeneratedImage) -> str:
    return f"data:{img.content_type};base64,{base64.b64encode(img.data or b'').decode()}"
