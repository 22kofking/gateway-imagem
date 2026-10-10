"""Autenticação dos apps clientes por chave (Authorization: Bearer <chave>)."""

import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import AppKey, settings

# HTTPBearer também faz aparecer o botão "Authorize" em /docs
bearer = HTTPBearer(auto_error=False, description="Chave do app (GATEWAY_APP_KEYS)")


def current_app(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> AppKey:
    token = credentials.credentials.strip() if credentials else ""
    if token:
        for app in settings.apps:
            if secrets.compare_digest(token, app.key):
                return app
    raise HTTPException(status_code=401, detail="Chave de API inválida")
