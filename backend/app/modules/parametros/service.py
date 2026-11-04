"""Parâmetros operacionais e regra de elegibilidade versionados por unidade (RF20, UC10, RN11)."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.erros import NaoEncontrado, RegraNegocio
from app.core.relogio import agora
from app.modules.auditoria import service as auditoria
from app.modules.cadastros.models import UnidadeSaude
from app.modules.parametros.models import ParametroOperacional, RegraElegibilidade
from app.modules.parametros.schemas import ParametrosEntrada


@dataclass
class Configuracao:
    parametro: ParametroOperacional
    regra: RegraElegibilidade


def _vigentes(db: Session, unidade_id: int) -> tuple[ParametroOperacional | None, RegraElegibilidade | None]:
    p = db.scalar(
        select(ParametroOperacional).where(
            ParametroOperacional.unidade_id == unidade_id, ParametroOperacional.vigente.is_(True)
        )
    )
    r = db.scalar(
        select(RegraElegibilidade).where(
            RegraElegibilidade.unidade_id == unidade_id, RegraElegibilidade.vigente.is_(True)
        )
    )
    return p, r


def vigente(db: Session, unidade_id: int) -> Configuracao:
    """Devolve a configuração vigente; cria a versão 1 com os valores padrão se não existir."""
    p, r = _vigentes(db, unidade_id)
    if p is None or r is None:
        padrao = ParametrosEntrada()
        p = p or ParametroOperacional(
            unidade_id=unidade_id, versao=1, vigente=True, criado_em=agora(),
            antecedencia_lembrete_horas=padrao.antecedencia_lembrete_horas,
            prazo_resposta_min=padrao.prazo_resposta_min,
            tentativas_contato=padrao.tentativas_contato,
            janela_reserva_min=padrao.janela_reserva_min,
            antecedencia_minima_oferta_min=padrao.antecedencia_minima_oferta_min,
        )
        r = r or RegraElegibilidade(
            unidade_id=unidade_id, versao=p.versao, vigente=True, nome=padrao.nome_regra,
            considera_prioridade_assistencial=padrao.considera_prioridade_assistencial,
            exige_profissional_compativel=padrao.exige_profissional_compativel,
            criterio_desempate=padrao.criterio_desempate,
        )
        db.add_all([p, r])
        db.flush()
    return Configuracao(p, r)


def para_saida(cfg: Configuracao) -> dict:
    p, r = cfg.parametro, cfg.regra
    return {
        "unidade_id": p.unidade_id, "versao": p.versao, "vigente": p.vigente, "criado_em": p.criado_em,
        "criado_por_id": p.criado_por_id,
        "antecedencia_lembrete_horas": p.antecedencia_lembrete_horas,
        "prazo_resposta_min": p.prazo_resposta_min, "tentativas_contato": p.tentativas_contato,
        "janela_reserva_min": p.janela_reserva_min,
        "antecedencia_minima_oferta_min": p.antecedencia_minima_oferta_min,
        "nome_regra": r.nome, "considera_prioridade_assistencial": r.considera_prioridade_assistencial,
        "exige_profissional_compativel": r.exige_profissional_compativel,
        "criterio_desempate": r.criterio_desempate,
    }


def _unidade(db: Session, unidade_id: int) -> UnidadeSaude:
    u = db.get(UnidadeSaude, unidade_id)
    if u is None:
        raise NaoEncontrado("Unidade não encontrada.")
    return u


def obter(db: Session, unidade_id: int) -> dict:
    _unidade(db, unidade_id)
    cfg = vigente(db, unidade_id)
    db.commit()
    return para_saida(cfg)


def atualizar(db: Session, unidade_id: int, dados: ParametrosEntrada, usuario) -> dict:
    """Cria uma nova versão; as anteriores ficam guardadas e os fluxos já iniciados não mudam (UC10)."""
    _unidade(db, unidade_id)
    if dados.prazo_resposta_min >= dados.antecedencia_lembrete_horas * 60:
        raise RegraNegocio(
            "O prazo de resposta deve ser menor que a antecedência do lembrete.",
            campos=[{"campo": "prazo_resposta_min", "erro": "maior ou igual à antecedência do lembrete"}],
        )
    atual = vigente(db, unidade_id)
    nova_versao = atual.parametro.versao + 1
    atual.parametro.vigente = False
    atual.regra.vigente = False
    db.flush()
    p = ParametroOperacional(
        unidade_id=unidade_id, versao=nova_versao, vigente=True, criado_em=agora(), criado_por_id=usuario.id,
        antecedencia_lembrete_horas=dados.antecedencia_lembrete_horas,
        prazo_resposta_min=dados.prazo_resposta_min, tentativas_contato=dados.tentativas_contato,
        janela_reserva_min=dados.janela_reserva_min,
        antecedencia_minima_oferta_min=dados.antecedencia_minima_oferta_min,
    )
    r = RegraElegibilidade(
        unidade_id=unidade_id, versao=nova_versao, vigente=True, nome=dados.nome_regra,
        considera_prioridade_assistencial=dados.considera_prioridade_assistencial,
        exige_profissional_compativel=dados.exige_profissional_compativel,
        criterio_desempate=dados.criterio_desempate,
    )
    db.add_all([p, r])
    auditoria.registrar(
        db, "PARAMETROS_ALTERADOS", "unidade_saude", unidade_id, auditoria.origem_usuario(usuario), usuario.id,
        {"versao": nova_versao, **dados.model_dump()},
    )
    db.commit()
    return para_saida(Configuracao(p, r))


def historico(db: Session, unidade_id: int) -> list[dict]:
    _unidade(db, unidade_id)
    ps = db.scalars(
        select(ParametroOperacional)
        .where(ParametroOperacional.unidade_id == unidade_id)
        .order_by(ParametroOperacional.versao.desc())
    ).all()
    rs = {
        r.versao: r
        for r in db.scalars(select(RegraElegibilidade).where(RegraElegibilidade.unidade_id == unidade_id))
    }
    return [para_saida(Configuracao(p, rs[p.versao])) for p in ps if p.versao in rs]
