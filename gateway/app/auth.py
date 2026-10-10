"""Autenticação dos apps clientes por chave (Authorization: Bearer <chave>)."""

import secrets

from fastapi import Header, HTTPException

from app.config import AppKey, settings


def current_app(authorization: str = Header(default="")) -> AppKey:
    token = authorization.removeprefix("Bearer ").strip()
    if token:
        for app in settings.apps:
            if secrets.compare_digest(token, app.key):
                return app
    raise HTTPException(status_code=401, detail="Chave de API inválida")
