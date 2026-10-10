"""Worker RunPod Serverless: gera imagens com um modelo do Hugging Face.

A RunPod liga uma GPU, executa este arquivo e chama `handler` a cada pedido.
O modelo é carregado uma vez, fora do handler.

Modelo: variável MODEL_ID (padrão FLUX.2 klein 4B, Apache 2.0). Configure o
mesmo repositório no campo "Model" do endpoint para a RunPod deixá-lo em cache
na máquina (cold start rápido e download não cobrado).

Entrada: {"input": {"prompt": "...", "width": 1024, "height": 1024, "seed": 42}}
Saída:   {"images": [{"base64": "...", "content_type": "image/webp"}], "seed": 42}

Teste local (precisa de GPU): python handler.py --test_input '{"input": {"prompt": "um gato"}}'
"""

import base64
import io
import os
import random

# Cache de modelos da RunPod: precisa ser definido antes de importar diffusers.
RUNPOD_HF_CACHE = "/runpod-volume/huggingface-cache/hub"
if os.path.isdir(RUNPOD_HF_CACHE):
    os.environ.setdefault("HF_HUB_CACHE", RUNPOD_HF_CACHE)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

import runpod  # noqa: E402
import torch  # noqa: E402
from diffusers import DiffusionPipeline  # noqa: E402

MODEL_ID = os.getenv("MODEL_ID", "black-forest-labs/FLUX.2-klein-4B")
STEPS = int(os.getenv("STEPS", "4"))
GUIDANCE = os.getenv("GUIDANCE")  # alguns modelos destilados ignoram; deixe vazio se não souber
OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "WEBP")
MAX_SIDE = 1536

pipe = DiffusionPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16).to("cuda")


def handler(job):
    params = job["input"]
    prompt = params.get("prompt")
    if not prompt:
        return {"error": "prompt é obrigatório"}

    width = int(params.get("width", 1024))
    height = int(params.get("height", 1024))
    if not (256 <= width <= MAX_SIDE and 256 <= height <= MAX_SIDE):
        return {"error": f"largura e altura devem ficar entre 256 e {MAX_SIDE}"}

    seed = params.get("seed")
    seed = random.randint(0, 2**31 - 1) if seed is None else int(seed)

    kwargs = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "num_inference_steps": int(params.get("steps", STEPS)),
        "generator": torch.Generator("cuda").manual_seed(seed),
    }
    if GUIDANCE:
        kwargs["guidance_scale"] = float(GUIDANCE)

    image = pipe(**kwargs).images[0]

    buf = io.BytesIO()
    image.save(buf, format=OUTPUT_FORMAT, quality=90)
    return {
        "images": [
            {
                "base64": base64.b64encode(buf.getvalue()).decode(),
                "content_type": f"image/{OUTPUT_FORMAT.lower()}",
            }
        ],
        "seed": seed,
    }


runpod.serverless.start({"handler": handler})
