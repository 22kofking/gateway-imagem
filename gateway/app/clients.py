"""Cliente HTTP compartilhado. Os testes trocam `http` por um transporte simulado."""

import httpx

http = httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0))
