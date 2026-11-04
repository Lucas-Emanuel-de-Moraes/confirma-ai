"""Login, usuários e perfis (RF18, UC08, PB06, PB07)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.erros import Conflito, NaoAutorizado, NaoEncontrado, RegraNegocio
from app.core.paginacao import ParamsPaginacao, paginar
from app.core.relogio import agora
from app.core.seguranca import criar_token, hash_senha, verificar_senha
from app.modules.acesso import repository as repo
from app.modules.acesso.models import Perfil, Usuario
from app.modules.acesso.permissoes import PERFIS_PADRAO
from app.modules.acesso.schemas import UsuarioAtualizar, UsuarioCriar
from app.modules.auditoria import service as auditoria
from app.modules.cadastros.models import UnidadeSaude


def autenticar(db: Session, login: str, senha: str, ip: str | None = None) -> tuple[str, int]:
    usuario = repo.por_login(db, login)
    valido = usuario is not None and usuario.ativo and verificar_senha(senha, usuario.senha_hash)
    # Toda tentativa de login é auditada (PB06); a senha nunca é registrada.
    auditoria.registrar(
        db,
        "LOGIN_SUCESSO" if valido else "LOGIN_FALHA",
        "usuario",
        usuario.id if usuario else None,
        origem=f"login:{login}"[:80],
        usuario_id=usuario.id if (usuario and valido) else None,
        detalhes={"ip": ip, "motivo": None if valido else ("inativo" if usuario and not usuario.ativo else "credenciais")},
    )
    db.commit()
    if not valido:
        raise NaoAutorizado("Usuário ou senha inválidos.", codigo="CREDENCIAIS_INVALIDAS")
    return criar_token(usuario.id, usuario.nomes_perfis)


def garantir_perfis_padrao(db: Session) -> None:
    existentes = {p.nome: p for p in db.scalars(select(Perfil))}
    for nome, permissoes in PERFIS_PADRAO.items():
        if nome not in existentes:
            db.add(Perfil(nome=nome, permissoes=permissoes))
        else:
            existentes[nome].permissoes = permissoes
    db.flush()


def _validar_unidade(db: Session, unidade_id: int | None) -> None:
    if unidade_id is not None and db.get(UnidadeSaude, unidade_id) is None:
        raise RegraNegocio("Unidade de lotação inexistente.", campos=[{"campo": "unidade_id", "erro": "inexistente"}])


def criar(db: Session, dados: UsuarioCriar, autor: Usuario | None) -> Usuario:
    if repo.por_login(db, dados.login):
        raise Conflito("Já existe um usuário com este login.", codigo="LOGIN_DUPLICADO")
    _validar_unidade(db, dados.unidade_id)
    usuario = Usuario(
        nome=dados.nome,
        login=dados.login,
        senha_hash=hash_senha(dados.senha),
        unidade_id=dados.unidade_id,
        ativo=True,
        criado_em=agora(),
        perfis=repo.perfis_por_nome(db, dados.perfis),
    )
    db.add(usuario)
    db.flush()
    auditoria.registrar(
        db, "USUARIO_CRIADO", "usuario", usuario.id, auditoria.origem_usuario(autor),
        autor.id if autor else None, {"perfis": dados.perfis},
    )
    db.commit()
    return usuario


def obter(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise NaoEncontrado("Usuário não encontrado.")
    return usuario


def atualizar(db: Session, usuario_id: int, dados: UsuarioAtualizar, autor: Usuario) -> Usuario:
    usuario = obter(db, usuario_id)
    alterados = []
    if dados.nome is not None:
        usuario.nome = dados.nome
        alterados.append("nome")
    if dados.senha is not None:
        usuario.senha_hash = hash_senha(dados.senha)
        alterados.append("senha")
    if dados.perfis is not None:
        if usuario.id == autor.id and "ADMINISTRADOR" not in dados.perfis and usuario.eh_admin:
            raise RegraNegocio("Você não pode remover o seu próprio perfil de administrador.")
        usuario.perfis = repo.perfis_por_nome(db, dados.perfis)
        alterados.append("perfis")
    if "unidade_id" in dados.model_fields_set:
        _validar_unidade(db, dados.unidade_id)
        usuario.unidade_id = dados.unidade_id
        alterados.append("unidade_id")
    auditoria.registrar(
        db, "USUARIO_ALTERADO", "usuario", usuario.id, auditoria.origem_usuario(autor), autor.id,
        {"campos": alterados, "perfis": dados.perfis},
    )
    db.commit()
    return usuario


def inativar(db: Session, usuario_id: int, autor: Usuario) -> Usuario:
    usuario = obter(db, usuario_id)
    if usuario.id == autor.id:
        raise RegraNegocio("Você não pode inativar o próprio usuário.")
    usuario.ativo = False
    auditoria.registrar(db, "USUARIO_INATIVADO", "usuario", usuario.id, auditoria.origem_usuario(autor), autor.id)
    db.commit()
    return usuario


def listar(db: Session, params: ParamsPaginacao, ativo: bool | None, busca: str | None) -> dict:
    return paginar(db, repo.listar_stmt(ativo, busca), params)


def listar_perfis(db: Session) -> list[Perfil]:
    return list(db.scalars(select(Perfil).order_by(Perfil.nome)))
