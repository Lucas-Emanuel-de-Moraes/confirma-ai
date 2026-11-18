"""Demonstração do fluxo principal do Confirma Aí contra a API rodando (seção 2.3 do documento).

Pré-requisitos: API no ar (uvicorn ou docker compose) e dados de demonstração
(python -m app.seed --demo). Uso:

    python scripts/demo_fluxo.py                       # http://localhost:8000
    python scripts/demo_fluxo.py --url http://localhost:8000

Roteiro: Maria tem consulta amanhã -> recebe o lembrete -> responde NÃO -> a vaga é liberada ->
Helena (prioridade ALTA) recebe a oferta e recusa -> João recebe a oferta e aceita ->
novo agendamento criado sem dupla marcação -> histórico e indicadores.
"""

import argparse
import sys
from datetime import date, datetime, time, timedelta

import httpx

MARIA, JOAO, HELENA, CARLOS = "5565999990001", "5565999990002", "5565999990003", "5565999990004"
VERDE, VERMELHO, NEGRITO, FIM = "\033[32m", "\033[31m", "\033[1m", "\033[0m"


def passo(n, texto):
    print(f"\n{NEGRITO}[{n}] {texto}{FIM}")


def ok(texto):
    print(f"   {VERDE}✔{FIM} {texto}")


def falhou(texto):
    print(f"   {VERMELHO}✘ {texto}{FIM}")
    sys.exit(1)


class Api:
    def __init__(self, url):
        self.c = httpx.Client(base_url=url, timeout=15)
        self.h = {}

    def login(self, usuario, senha):
        r = self.c.post("/api/v1/auth/login", data={"username": usuario, "password": senha})
        if r.status_code != 200:
            falhou(f"login de {usuario} falhou: {r.text}. Rodou 'python -m app.seed --demo'?")
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def get(self, rota, h, **params):
        r = self.c.get(f"/api/v1{rota}", headers=h, params=params)
        r.raise_for_status()
        return r.json()

    def post(self, rota, h=None, **kw):
        return self.c.post(f"/api/v1{rota}", headers=h or {}, **kw)


def ultima(api, telefone):
    msgs = api.get("/simulador/mensagens", {}, telefone=telefone, limite=1)
    return msgs[0] if msgs else None


def responder(api, telefone, resposta, identificador):
    r = api.post("/simulador/responder", json={"telefone": telefone, "identificador": identificador,
                                                 "resposta": resposta})
    return r.json()["resultados"][0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    api = Api(parser.parse_args().url)

    passo(1, "Saúde da API")
    try:
        saude = api.c.get("/api/health").json()
    except httpx.ConnectError:
        falhou("API fora do ar. Suba com: uvicorn app.main:app --reload")
    if saude.get("mensageria") != "simulador":
        falhou("Este roteiro usa o simulador (MENSAGERIA_PROVEDOR=simulador).")
    ok(f"status={saude['status']} banco={saude['banco']} mensageria={saude['mensageria']}")

    passo(2, "Login da recepção e do administrador (JWT)")
    recep, admin = api.login("recepcao", "Senha@123"), api.login("admin", "Admin@123")
    ok("tokens obtidos")

    unidade = api.get("/unidades", recep, busca="Clínica Central")["itens"][0]
    cardio = api.get("/especialidades", recep, busca="Cardiologia")["itens"][0]
    ana = api.get("/profissionais", recep, busca="Ana Souza")["itens"][0]
    pacientes = {p["telefone"]: p for p in api.get("/pacientes", recep, size=100)["itens"]}
    for tel in (JOAO, HELENA):  # garante João e Helena na fila (o roteiro pode ser repetido)
        api.post("/fila-espera", recep, json={"paciente_id": pacientes[tel]["id"], "especialidade_id": cardio["id"],
                                               "preferencias": [{"unidade_id": unidade["id"]}]})

    passo(3, "Recepção agenda a Maria para amanhã (UC02)")
    corpo = {"paciente_id": pacientes[MARIA]["id"], "unidade_id": unidade["id"],
             "especialidade_id": cardio["id"], "profissional_id": ana["id"]}
    dia = date.today() + timedelta(days=1)
    for minutos in range(8 * 60, 21 * 60, 30):
        corpo["data_hora"] = datetime.combine(dia, time(minutos // 60, minutos % 60)).isoformat()
        r = api.post("/agendamentos", recep, json=corpo)
        if r.status_code == 201:
            break
    else:
        falhou("não encontrei horário livre amanhã")
    ag = r.json()
    ok(f"agendamento {ag['numero_agendamento']} em {ag['data_hora']} – {ag['status_descricao']}")

    passo(4, "Tentativa de dupla marcação no mesmo horário (RF17)")
    r = api.post("/agendamentos", recep, json={**corpo, "paciente_id": pacientes[CARLOS]["id"]})
    ok(f"HTTP {r.status_code} {r.json()['codigo']}") if r.status_code == 409 else falhou(r.text)

    passo(5, "Sistema envia o lembrete (tarefas: lembretes + outbox)")
    api.post("/tarefas/ciclo", admin)
    msg = ultima(api, MARIA)
    if not msg or msg["tipo"] != "LEMBRETE_CONFIRMACAO":
        falhou("lembrete não encontrado no simulador")
    ok(f"WhatsApp simulado para Maria: “{msg['texto']}”")

    passo(6, "Resposta forjada (outro telefone com o identificador da Maria) – UC13")
    r = responder(api, "5565911112222", "SIM", msg["identificador"])
    ok(f"descartada: {r['motivo']}") if not r["valida"] else falhou("resposta forjada foi aceita!")

    passo(7, "Maria responde NÃO – a vaga é liberada e oferecida à fila")
    r = responder(api, MARIA, "NÃO", msg["identificador"])
    ok(f"agendamento agora: {r['status']}")
    api.post("/tarefas/outbox", admin)
    oferta = ultima(api, HELENA)
    if not oferta or oferta["tipo"] != "OFERTA_ENCAIXE":
        falhou("Helena (prioridade ALTA) deveria ter recebido a oferta primeiro")
    ok(f"Helena recebeu a oferta (prioridade ALTA, RN09): “{oferta['texto']}”")

    passo(8, "Recepção tenta usar o horário reservado (RN02)")
    r = api.post("/agendamentos", recep, json={**corpo, "paciente_id": pacientes[CARLOS]["id"]})
    ok(f"HTTP {r.status_code} {r.json()['codigo']}") if r.status_code == 409 else falhou(r.text)

    passo(9, "Helena recusa – a vaga vai para o próximo (RF16)")
    responder(api, HELENA, "RECUSAR", oferta["identificador"])
    api.post("/tarefas/outbox", admin)
    oferta_joao = ultima(api, JOAO)
    ok("João recebeu a oferta") if oferta_joao and oferta_joao["tipo"] == "OFERTA_ENCAIXE" else falhou("sem oferta p/ João")

    passo(10, "João aceita – confirmação atômica (RN13)")
    r = responder(api, JOAO, "ACEITAR", oferta_joao["identificador"])
    novo = api.get(f"/agendamentos/{r['agendamento_id']}", recep)
    ok(f"novo agendamento {novo['numero_agendamento']} para {novo['paciente']['nome']} em {novo['data_hora']}")
    r = responder(api, JOAO, "ACEITAR", oferta_joao["identificador"])
    ok(f"aceite repetido descartado: {r['motivo']}")

    passo(11, "Linha do tempo do agendamento original (RF07)")
    for e in api.get(f"/agendamentos/{ag['id']}/historico", recep):
        print(f"     {e['data_hora'][11:19]}  {e['tipo']:<10} {e['descricao']}")

    passo(12, "Indicadores do gestor (RF19)")
    gestor = api.login("gestor", "Senha@123")
    ind = api.get("/indicadores", gestor, unidade_id=unidade["id"])
    ok(f"vagas liberadas={ind['vagas']['liberadas']} recuperadas={ind['vagas']['recuperadas']} "
       f"taxa_recuperacao={ind['taxas']['taxa_recuperacao']}")
    print(f"\n{VERDE}{NEGRITO}Fluxo principal concluído com sucesso!{FIM} Veja tudo em {str(api.c.base_url).rstrip('/')}/docs\n")


if __name__ == "__main__":
    main()
