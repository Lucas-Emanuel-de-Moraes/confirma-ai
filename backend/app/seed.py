"""Carga inicial do banco.

    python -m app.seed           -> perfis padrão + usuário administrador (ADMIN_LOGIN / ADMIN_SENHA)
    python -m app.seed --demo    -> também cria dados FICTÍCIOS para testar o fluxo (RNF08: nunca dados reais)
"""

import argparse
from datetime import time

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.relogio import agora
from app.core.seguranca import hash_senha
from app.modules.acesso import repository as acesso_repo
from app.modules.acesso.models import Usuario
from app.modules.acesso.service import garantir_perfis_padrao
from app.modules.cadastros.models import (
    Contato,
    Especialidade,
    HorarioAtendimento,
    NivelPrioridade,
    Paciente,
    Profissional,
    TipoContato,
    UnidadeSaude,
)
from app.modules.fila.models import FilaEspera, Periodo, PreferenciaEncaixe
from app.modules.lgpd import consentimento
from app.modules.lgpd.service import politicas
from app.modules.parametros import service as parametros

SENHA_DEMO = "Senha@123"


def _usuario(db, login, nome, perfis, senha, unidade_id=None):
    if acesso_repo.por_login(db, login):
        return
    db.add(Usuario(nome=nome, login=login, senha_hash=hash_senha(senha), ativo=True, criado_em=agora(),
                   unidade_id=unidade_id, perfis=acesso_repo.perfis_por_nome(db, perfis)))


def seed_basico(db) -> None:
    garantir_perfis_padrao(db)
    _usuario(db, settings.ADMIN_LOGIN, settings.ADMIN_NOME, ["ADMINISTRADOR"], settings.ADMIN_SENHA)
    politicas(db)
    db.commit()
    print(f"✔ Perfis e usuário administrador prontos (login: {settings.ADMIN_LOGIN}).")


def seed_demo(db) -> None:
    if db.scalar(select(UnidadeSaude).where(UnidadeSaude.nome == "Clínica Central")):
        print("• Dados de demonstração já existem – nada a fazer.")
        return
    cardio, derma, geral = (Especialidade(nome=n, ativo=True) for n in ("Cardiologia", "Dermatologia", "Clínica Geral"))
    central = UnidadeSaude(nome="Clínica Central", endereco="Av. Fictícia, 100 – Centro", ativo=True,
                           especialidades=[cardio, derma, geral])
    norte = UnidadeSaude(nome="Unidade Bairro Norte", endereco="Rua Exemplo, 200 – Norte", ativo=True,
                         especialidades=[geral, cardio])
    db.add_all([cardio, derma, geral, central, norte])
    db.flush()
    for u in (central, norte):
        parametros.vigente(db, u.id)

    ana = Profissional(nome="Dra. Ana Souza", registro_conselho="CRM-MT 1001", ativo=True,
                       especialidades=[cardio], unidades=[central, norte])
    bruno = Profissional(nome="Dr. Bruno Lima", registro_conselho="CRM-MT 1002", ativo=True,
                         especialidades=[cardio, geral], unidades=[central])
    carla = Profissional(nome="Dra. Carla Reis", registro_conselho="CRM-MT 1003", ativo=True,
                         especialidades=[derma], unidades=[central])
    db.add_all([ana, bruno, carla])
    db.flush()
    # Horários amplos (todos os dias, 07h–22h) para facilitar os testes em qualquer momento
    for prof in (ana, bruno, carla):
        for dia in range(7):
            db.add(HorarioAtendimento(profissional_id=prof.id, unidade_id=central.id, dia_semana=dia,
                                      hora_inicio=time(7, 0), hora_fim=time(22, 0), duracao_consulta_min=30, ativo=True))

    pacientes = [
        ("Maria Fictícia Oliveira", "5565999990001", NivelPrioridade.NENHUMA),
        ("João Exemplo Santos", "5565999990002", NivelPrioridade.NENHUMA),
        ("Helena Teste Prioritária", "5565999990003", NivelPrioridade.ALTA),
        ("Carlos Demo Pereira", "5565999990004", NivelPrioridade.NENHUMA),
        ("Paciente Falha Envio", "5565999999999", NivelPrioridade.NENHUMA),  # simula falha do provedor
    ]
    criados = []
    for nome, tel, prio in pacientes:
        p = Paciente(nome=nome, ativo=True, prioridade_assistencial=prio, data_cadastro=agora())
        c = Contato(tipo=TipoContato.WHATSAPP, valor=tel)
        p.contatos.append(c)
        db.add(p)
        db.flush()
        consentimento.autorizar_contato(db, c, "seed-demonstracao")
        criados.append(p)

    # João (entrou primeiro) e Helena (prioridade ALTA) aguardam vaga de Cardiologia
    for p in (criados[1], criados[2]):
        db.add(FilaEspera(paciente_id=p.id, especialidade_id=cardio.id, data_entrada=agora(), prioridade=p.prioridade_assistencial,
                          disponivel_para_encaixe=True, ativo=True,
                          preferencias=[PreferenciaEncaixe(unidade_id=central.id, periodo=Periodo.QUALQUER)]))
        db.flush()

    _usuario(db, "recepcao", "Recepcionista Demo", ["RECEPCIONISTA"], SENHA_DEMO)
    _usuario(db, "gestor", "Gestor Demo", ["GESTOR"], SENHA_DEMO)
    _usuario(db, "profissional", "Profissional Demo", ["PROFISSIONAL"], SENHA_DEMO)
    db.commit()
    print("✔ Dados de demonstração criados:")
    print(f"   Unidade 'Clínica Central' id={central.id} | Cardiologia id={cardio.id} | Dra. Ana Souza id={ana.id}")
    print("   Pacientes: " + ", ".join(f"{p.nome.split()[0]} id={p.id}" for p in criados))
    print(f"   Usuários: recepcao / gestor / profissional (senha {SENHA_DEMO})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga inicial do Confirma Aí")
    parser.add_argument("--demo", action="store_true", help="cria dados fictícios de demonstração")
    args = parser.parse_args()
    with SessionLocal() as db:
        seed_basico(db)
        if args.demo:
            seed_demo(db)


if __name__ == "__main__":
    main()
