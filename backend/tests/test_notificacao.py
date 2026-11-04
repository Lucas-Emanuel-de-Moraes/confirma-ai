"""PB13, PB17: outbox, retentativas, falha definitiva, idempotência e consentimento no envio (RN16, RNF12)."""

from conftest import mensagens_para, responder, rodar

from app.core import relogio
from app.core.database import SessionLocal
from app.modules.cadastros.models import Paciente
from app.modules.notificacao import service as notificacao
from app.modules.notificacao.models import Mensagem, OutboxEvento, StatusOutbox, TipoMensagem


def test_enfileirar_e_idempotente(cenario):
    p = cenario.paciente("Maria", "65999990001")
    with SessionLocal() as db:
        pac = db.get(Paciente, p["id"])
        m1 = notificacao.enfileirar(db, tipo=TipoMensagem.AVISO, paciente=pac, conteudo="oi", chave_idempotencia="k1")
        m2 = notificacao.enfileirar(db, tipo=TipoMensagem.AVISO, paciente=pac, conteudo="oi", chave_idempotencia="k1")
        db.commit()
        assert m1.id == m2.id and db.query(OutboxEvento).count() == 1
    rodar("outbox")
    rodar("outbox")
    assert len(mensagens_para(p["tel"])) == 1


def test_revogacao_cancela_mensagem_ja_na_fila(client, cenario):
    maria = cenario.paciente("Maria", "65999990001")
    cenario.agendar(maria)
    rodar("lembretes")  # lembrete gravado no outbox, ainda não enviado
    r = client.delete(f"/api/v1/pacientes/{maria['id']}/autorizacao", headers=cenario.h)
    assert r.status_code == 200 and r.json()["contato_autorizado"] is False
    rodar("outbox")
    assert mensagens_para(maria["tel"]) == []  # RN16: efeito imediato


def test_retentativa_e_falha_definitiva_de_oferta(client, cenario):
    falha = cenario.paciente("Falha", "65999999999")  # o simulador falha para final 9999
    joao = cenario.paciente("Joao", "65999990002")
    cenario.fila(falha, prioridade="ALTA")
    cenario.fila(joao)
    maria = cenario.paciente("Maria", "65999990001")
    cenario.agendar(maria)
    rodar("lembretes")
    rodar("outbox")
    responder(client, maria["tel"], "NAO")
    assert cenario.get("/ofertas")["itens"][0]["paciente"]["id"] == falha["id"]

    assert rodar("outbox") == {"falha": 1}
    assert rodar("outbox") == {}  # próxima tentativa só depois do intervalo (30 s)
    relogio.avancar(seconds=31)
    assert rodar("outbox") == {"falha": 1}
    relogio.avancar(seconds=61)
    assert rodar("outbox") == {"falha": 1}  # 3ª tentativa = falha definitiva (padrão: 3)
    with SessionLocal() as db:
        ev = db.query(OutboxEvento).join(Mensagem).filter(Mensagem.paciente_id == falha["id"]).one()
        assert ev.status == StatusOutbox.FALHA_DEFINITIVA and ev.tentativas == 3
    ofertas = {o["paciente"]["id"]: o["status"] for o in cenario.get("/ofertas")["itens"]}
    assert ofertas == {falha["id"]: "FALHA_CONTATO", joao["id"]: "RESERVADA"}  # RF16: reoferta
    rodar("outbox")
    assert mensagens_para(joao["tel"])[0]["tipo"] == "OFERTA_ENCAIXE"


def test_paciente_sai_pelo_whatsapp(client, cenario, com_lembrete_enviado):
    maria, ag = com_lembrete_enviado
    r = responder(client, maria["tel"], "SAIR", identificador="")
    assert r["valida"] and r["tipo"] == "SAIR"
    assert cenario.get(f"/pacientes/{maria['id']}")["contato_autorizado"] is False
    # a resposta posterior ao lembrete deixa de valer: contato não autorizado (RN20)
    assert responder(client, maria["tel"], "SIM")["motivo"] == "CONTATO_NAO_AUTORIZADO"
