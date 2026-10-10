import base64

from tests.conftest import AUTH, PNG


def test_health_sem_chave(client):
    assert client.get("/health").json() == {"ok": True}


def test_sem_chave_da_401(client):
    assert client.post("/v1/images", json={"prompt": "gato"}).status_code == 401
    assert client.post("/v1/images", json={"prompt": "gato"}, headers={"Authorization": "Bearer errada"}).status_code == 401


def test_validacao(client):
    assert client.post("/v1/images", json={"prompt": ""}, headers=AUTH).status_code == 422
    assert client.post("/v1/images", json={"prompt": "gato", "size": "999x999"}, headers=AUTH).status_code == 422
    r = client.post("/v1/images", json={"prompt": "gato", "model": "nao-existe"}, headers=AUTH)
    assert r.status_code == 400


def test_lista_modelos(client):
    names = {m["name"]: m["available"] for m in client.get("/v1/models", headers=AUTH).json()}
    assert names == {"rapido": True, "texto": True}


def test_endpoint_proprio_async(client, fake):
    fake.status = "IN_PROGRESS"
    r = client.post("/v1/images", json={"prompt": "gato", "seed": 7}, headers=AUTH)
    assert r.status_code == 202
    job = r.json()
    assert job["status"] == "running"
    assert fake.calls[0][1] == "https://api.runpod.ai/v2/meu-endpoint/run"
    assert fake.calls[0][2] == {"input": {"prompt": "gato", "width": 1024, "height": 1024, "seed": 7}}

    fake.status = "COMPLETED"
    done = client.get(f"/v1/jobs/{job['id']}", headers=AUTH).json()
    assert done["status"] == "succeeded"
    assert done["images"] == ["data:image/png;base64," + base64.b64encode(PNG).decode()]


def test_wait_devolve_imagem_pronta(client):
    r = client.post("/v1/images", json={"prompt": "gato", "wait": True}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["status"] == "succeeded"


def test_fallback_para_public_endpoint(client, fake):
    fake.own_endpoint_fails = True
    r = client.post("/v1/images", json={"prompt": "gato", "size": "1280x720", "wait": True}, headers=AUTH)
    assert r.json()["images"] == ["https://runpod.cdn/img.png"]
    public_call = fake.calls[1]
    assert public_call[1] == "https://api.runpod.ai/v2/z-image-turbo/run"
    assert public_call[2] == {"input": {"prompt": "gato", "size": "1280*720", "seed": -1}}


def test_fallback_ate_fal(client, fake):
    fake.own_endpoint_fails = True
    fake.public_fails = True
    r = client.post("/v1/images", json={"prompt": "gato", "wait": True}, headers=AUTH)
    assert r.json()["images"] == ["https://fal.media/img.png"]
    assert fake.calls[2][1] == "https://queue.fal.run/fal-ai/z-image/turbo"


def test_sem_endpoint_proprio_pula_direto_para_publico(client, fake, monkeypatch):
    monkeypatch.delenv("RUNPOD_ENDPOINT_RAPIDO")
    client.post("/v1/images", json={"prompt": "gato"}, headers=AUTH)
    assert fake.calls[0][1] == "https://api.runpod.ai/v2/z-image-turbo/run"


def test_todos_falham_da_503(client, fake, monkeypatch):
    from app.config import settings

    fake.own_endpoint_fails = True
    fake.public_fails = True
    monkeypatch.setattr(settings, "fal_key", "")
    r = client.post("/v1/images", json={"prompt": "gato"}, headers=AUTH)
    assert r.status_code == 503


def test_job_de_outro_app_nao_aparece(client):
    job_id = client.post("/v1/images", json={"prompt": "gato"}, headers=AUTH).json()["id"]
    assert client.get(f"/v1/jobs/{job_id}", headers={"Authorization": "Bearer outra"}).status_code == 404


def test_limite_diario(client):
    for _ in range(3):
        assert client.post("/v1/images", json={"prompt": "gato"}, headers=AUTH).status_code in (200, 202)
    assert client.post("/v1/images", json={"prompt": "gato"}, headers=AUTH).status_code == 429


def test_uso_e_custo(client, fake):
    fake.own_endpoint_fails = True
    client.post("/v1/images", json={"prompt": "gato", "wait": True}, headers=AUTH)
    usage = client.get("/v1/usage", headers=AUTH).json()
    assert usage["hoje"] == 1
    assert usage["por_modelo"] == [{"model": "rapido", "provider": "runpod_publico", "imagens": 1, "custo_usd": 0.005}]


def test_storage_copia_imagens_para_o_bucket(client, fake, s3):
    fake.own_endpoint_fails = True
    job = client.post("/v1/images", json={"prompt": "gato", "wait": True}, headers=AUTH).json()
    assert job["images"] == [f"https://img.exemplo.com/site/{job['id']}/0.png"]
    assert s3.objects[("imagens", f"site/{job['id']}/0.png")] == (PNG, "image/png")


def test_storage_com_imagem_em_bytes(client, s3):
    job = client.post("/v1/images", json={"prompt": "gato", "wait": True}, headers=AUTH).json()
    assert job["images"] == [f"https://img.exemplo.com/site/{job['id']}/0.png"]
