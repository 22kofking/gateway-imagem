# API do Gateway de Imagem

Todas as rotas `/v1/*` exigem `Authorization: Bearer <chave do app>`.

## POST /v1/images

Pede uma imagem.

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `prompt` | texto | obrigatório | Até 2000 caracteres |
| `model` | texto | `rapido` | Nome do catálogo (`GET /v1/models`) |
| `size` | texto | `1024x1024` | `LARGURAxALTURA`, cada lado entre 256 e 1536 (ex.: `1024x448`, `512x704`) |
| `seed` | número | aleatório | Mesmo seed + mesmo prompt = mesma imagem (no mesmo provedor) |
| `image` | texto | nenhum | Imagem de entrada (image-to-image): link `https://` ou data URI (`data:image/png;base64,...`), até ~9 MB |
| `strength` | número | 0.8 | Com `image`: quanto a imagem pode mudar, de 0 (igual) a 1 (do zero) |
| `wait` | booleano | `false` | Esperar a imagem ficar pronta (até `GATEWAY_SYNC_WAIT` segundos) |

Respostas:
- `202` com `status: "running"`: consulte `GET /v1/jobs/{id}`.
- `200` com `status: "succeeded"` e `images`: pronto (modo `wait` ou provedor rápido).
- Pedido com `image` só vai para as rotas do catálogo marcadas com `aceita_imagem = true` (hoje, o Z-Image Turbo da RunPod no modelo `rapido`).
- `400` modelo desconhecido · `401` chave inválida · `422` campo inválido · `429` limite diário atingido · `503` nenhum provedor aceitou.

## GET /v1/jobs/{id}

Consulta um pedido. `status` é `running`, `succeeded` ou `failed` (com `error`). `cost_usd` traz o custo da imagem em dólar quando o provedor informa (os modelos prontos da RunPod informam); senão vem `null`. Recomendação: consultar a cada 1 a 2 segundos. Um app só enxerga os próprios pedidos.

## GET /v1/models

Lista os modelos e se cada um tem algum provedor configurado (`available`).

## GET /v1/usage?days=30

Imagens geradas hoje, limite diário e totais por modelo e provedor no período, com custo quando o provedor informa (modelos prontos da RunPod informam).

## GET /health

Sem autenticação. Para monitoramento.

## Exemplo em JavaScript

```js
const r = await fetch("https://seu-gateway/v1/images", {
  method: "POST",
  headers: { Authorization: `Bearer ${CHAVE}`, "Content-Type": "application/json" },
  body: JSON.stringify({ prompt: "um gato astronauta", wait: true }),
});
const job = await r.json();
console.log(job.images[0]);
```

## Exemplo em Python

```python
import httpx, time

h = {"Authorization": f"Bearer {CHAVE}"}
job = httpx.post("https://seu-gateway/v1/images", headers=h, json={"prompt": "um gato astronauta"}).json()
while job["status"] == "running":
    time.sleep(1.5)
    job = httpx.get(f"https://seu-gateway/v1/jobs/{job['id']}", headers=h).json()
print(job["images"])
```
