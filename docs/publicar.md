# Como publicar

## 0. Contas e chaves (você)

1. **RunPod**: criar conta, colocar crédito e gerar uma API key (Settings → API Keys). Ela vai em `RUNPOD_API_KEY`.
2. *(Opcional)* **fal.ai**: conta, crédito e chave → `FAL_KEY`.
3. *(Opcional, recomendado)* **Cloudflare R2**: criar um bucket público e uma chave de acesso → variáveis `S3_*`.

Com só o passo 1 o gateway já gera imagens pelos modelos prontos da RunPod (~US$ 0,005 por imagem).

## 1. Worker na RunPod (seu próprio modelo, ~US$ 0,001 por imagem)

Caminho recomendado: **integração com GitHub** (a RunPod constrói o Docker, você não precisa instalar nada).

1. Colocar este projeto num repositório GitHub.
2. Na RunPod: Settings → Connections → conectar o GitHub.
3. Serverless → New Endpoint → GitHub Repo → escolher o repositório, branch `main`, **Dockerfile path `worker/Dockerfile`**, **build context `worker`**.
4. Configuração do endpoint:

| Campo | Valor |
|---|---|
| Endpoint type | Queue |
| GPUs (em ordem) | 24 GB: RTX 4090 → L4 → A5000 |
| Active workers | 0 |
| Max workers | 3 |
| Idle timeout | 5 s |
| FlashBoot | ligado |
| **Model** | `black-forest-labs/FLUX.2-klein-4B` (cache de modelo) |
| Variáveis | `MODEL_ID=black-forest-labs/FLUX.2-klein-4B`, `STEPS=4` |

5. Testar na aba Requests do endpoint com o conteúdo de `worker/test_input.json`.
6. Copiar o id do endpoint para `RUNPOD_ENDPOINT_RAPIDO` no gateway.

Atualizações: a RunPod reconstrói ao criar uma **release** no GitHub.

Para trocar de modelo (ex.: Z-Image Turbo), mude `MODEL_ID` e o campo Model para `Tongyi-MAI/Z-Image-Turbo` e ajuste `STEPS` (8 para o Z-Image).

**Atenção:** endpoint sem nenhum pedido por 7 dias tem o máximo de workers zerado pela RunPod. Se isso acontecer, o gateway passa a usar o modelo pronto da RunPod automaticamente, mas você precisa subir o Max workers de novo.

## 2. Gateway

Qualquer serviço que rode um container serve. Opções baratas:

- **Fly.io / Railway / Render**: apontar para a pasta `gateway/` (tem `Dockerfile`), configurar as variáveis do `.env.example` como segredos.
- **VPS** (ex.: US$ 5/mês): `docker build -t gateway gateway/ && docker run -d --env-file gateway/.env -p 8000:8000 -v $PWD/dados:/dados -e GATEWAY_DB=/dados/gateway.db gateway`, com HTTPS via Caddy ou Cloudflare.

O banco SQLite precisa ficar num volume persistente. Com mais de uma instância do gateway, trocar por Postgres.

## Pendências conhecidas

- O worker não foi executado numa GPU ainda; o primeiro deploy é o teste real.
- O gateway foi testado só com provedores simulados (`gateway/tests/`).
- Webhooks (RunPod e fal avisarem quando terminar) ainda não estão implementados; hoje o gateway consulta o provedor quando o app pergunta.
