# Gateway de Imagem

Uma API única para qualquer app gerar imagens com modelos abertos, rodando em GPU de terceiros (RunPod, com fal.ai de reserva).

```
App ──► gateway/ (FastAPI, servidor comum) ──► 1. seu endpoint RunPod Serverless (worker/)
                                            ├─► 2. modelo pronto da RunPod (Public Endpoint)
                                            └─► 3. fal.ai
                    └─► bucket S3/R2 (guarda as imagens)
```

## Pastas

| Pasta | O que tem |
|---|---|
| `gateway/` | A API que os apps chamam |
| `gateway/app/main.py` | Rotas: `/v1/images`, `/v1/jobs/{id}`, `/v1/models`, `/v1/usage`, `/health` |
| `gateway/app/jobs.py` | Escolhe a rota, envia, consulta e finaliza os pedidos |
| `gateway/app/providers/` | Um arquivo por provedor (`runpod.py`, `fal.py`) |
| `gateway/app/storage.py` | Copia as imagens para o seu bucket (as URLs da RunPod expiram em 7 dias) |
| `gateway/app/db.py` | Banco de pedidos e uso (SQLite) |
| `gateway/modelos.toml` | **Catálogo**: nomes públicos dos modelos e a ordem dos provedores |
| `gateway/tests/` | Testes com os provedores simulados |
| `worker/` | Container que roda o modelo na GPU da RunPod |
| `docs/` | Guia de publicação e uso da API |

## Rodar o gateway na sua máquina

```bash
cd gateway
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # preencha RUNPOD_API_KEY e GATEWAY_APP_KEYS
set -a && source .env && set +a
uvicorn app.main:app --reload --port 8000
```

Abra http://localhost:8000/docs para testar pelo navegador. **Só com a chave da RunPod já funciona**, usando os modelos prontos dela; o seu endpoint próprio e a fal são opcionais.

Testes: `pytest` (dentro de `gateway/`).

## Usar de qualquer app

```bash
curl -X POST http://localhost:8000/v1/images \
  -H "Authorization: Bearer SUA_CHAVE_DE_APP" \
  -H "Content-Type: application/json" \
  -d '{"model": "rapido", "prompt": "um gato astronauta, fotografia", "wait": true}'
```

Resposta:

```json
{"id": "img_…", "model": "rapido", "status": "succeeded", "images": ["https://…"], "error": null, ...}
```

Detalhes da API em [docs/api.md](docs/api.md). Como publicar o worker e o gateway em [docs/publicar.md](docs/publicar.md).

## Modelos

| Nome na API | O que usa | Licença |
|---|---|---|
| `rapido` | Seu endpoint com FLUX.2 klein 4B → Z-Image Turbo da RunPod → Z-Image Turbo da fal | Apache 2.0 |
| `texto` | Qwen-Image da RunPod → Qwen-Image da fal | Apache 2.0 |

Para adicionar ou reordenar, edite `gateway/modelos.toml`; os apps não percebem a troca.
