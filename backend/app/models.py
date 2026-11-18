"""Importa todos os modelos para que o SQLAlchemy e o Alembic conheçam todas as tabelas."""

from app.modules.acesso.models import Perfil, Usuario, usuario_perfil  # noqa: F401
from app.modules.agenda.models import (  # noqa: F401
    Agendamento,
    HistoricoComparecimento,
    HistoricoStatusAgendamento,
)
from app.modules.auditoria.models import LogAuditoria  # noqa: F401
from app.modules.cadastros.models import (  # noqa: F401
    BloqueioAgenda,
    Contato,
    Especialidade,
    HorarioAtendimento,
    Paciente,
    Profissional,
    UnidadeSaude,
)
from app.modules.confirmacao.models import RespostaConfirmacao  # noqa: F401
from app.modules.fila.models import FilaEspera, PreferenciaEncaixe, SolicitacaoRemarcacao  # noqa: F401
from app.modules.lgpd.models import (  # noqa: F401
    HistoricoConsentimento,
    PoliticaRetencao,
    RequisicaoTitular,
)
from app.modules.notificacao.models import Mensagem, OutboxEvento  # noqa: F401
from app.modules.parametros.models import ParametroOperacional, RegraElegibilidade  # noqa: F401
from app.modules.recuperacao.models import OfertaVaga, VagaLiberada  # noqa: F401
