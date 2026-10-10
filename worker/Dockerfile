# Worker de geração de imagem para RunPod Serverless.
# Os pesos NÃO ficam na imagem: configure o campo "Model" do endpoint com o
# mesmo MODEL_ID para a RunPod usar o cache de modelos dela.
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py test_input.json ./
CMD ["python", "-u", "handler.py"]
