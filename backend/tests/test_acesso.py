"""PB02, PB06, PB07: health check, autenticação JWT, perfis e auditoria de login."""

from conftest import login


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and r.json()["banco"] == "ok"


def test_openapi_documentado(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "/api/v1/pacientes" in r.json()["paths"]
    assert client.get("/docs").status_code == 200


def test_login_invalido_e_rota_protegida(client):
    r = client.post("/api/v1/auth/login", data={"username": "admin", "password": "errada123"})
    assert r.status_code == 401 and r.json()["codigo"] == "CREDENCIAIS_INVALIDAS"
    r = client.get("/api/v1/pacientes")
    assert r.status_code == 401 and set(r.json()) == {"codigo", "mensagem", "campos"}
    r = client.get("/api/v1/pacientes", headers={"Authorization": "Bearer token-falso"})
    assert r.status_code == 401


def test_perfis_e_permissoes(client, admin):
    corpo = {"nome": "Recepcionista Um", "login": "recep1", "senha": "Senha@123", "perfis": ["RECEPCIONISTA"]}
    r = client.post("/api/v1/usuarios", json=corpo, headers=admin)
    assert r.status_code == 201 and r.json()["perfis"] == ["RECEPCIONISTA"]
    assert client.post("/api/v1/usuarios", json=corpo, headers=admin).status_code == 409

    recep = login(client, "recep1", "Senha@123")
    assert client.get("/api/v1/auth/me", headers=recep).json()["login"] == "recep1"
    assert client.get("/api/v1/pacientes", headers=recep).status_code == 200
    # recepcionista não administra usuários nem vê auditoria (403)
    assert client.get("/api/v1/usuarios", headers=recep).status_code == 403
    assert client.get("/api/v1/auditoria", headers=recep).status_code == 403


def test_senha_fraca_rejeitada(client, admin):
    r = client.post("/api/v1/usuarios", json={"nome": "Fulano", "login": "fulano", "senha": "12345678",
                                              "perfis": ["GESTOR"]}, headers=admin)
    assert r.status_code == 422 and r.json()["campos"][0]["campo"] == "senha"


def test_usuario_inativo_nao_entra(client, admin):
    uid = client.post("/api/v1/usuarios", json={"nome": "Gestor Um", "login": "gestor1", "senha": "Senha@123",
                                                "perfis": ["GESTOR"]}, headers=admin).json()["id"]
    token = login(client, "gestor1", "Senha@123")
    assert client.patch(f"/api/v1/usuarios/{uid}/inativar", headers=admin).status_code == 200
    r = client.post("/api/v1/auth/login", data={"username": "gestor1", "password": "Senha@123"})
    assert r.status_code == 401
    assert client.get("/api/v1/auth/me", headers=token).status_code == 401  # token antigo deixa de valer


def test_login_auditado_sem_senha(client, admin):
    client.post("/api/v1/auth/login", data={"username": "admin", "password": "senhaErrada1"})
    logs = client.get("/api/v1/auditoria", params={"entidade": "usuario"}, headers=admin).json()["itens"]
    acoes = [log["acao"] for log in logs]
    assert "LOGIN_FALHA" in acoes and "LOGIN_SUCESSO" in acoes
    assert all("senhaErrada1" not in str(log["detalhes"]) for log in logs)
