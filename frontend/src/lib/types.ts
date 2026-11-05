// Tipos espelhando os schemas da API (GET /openapi.json do back-end).

export type NivelPrioridade = "NENHUMA" | "BAIXA" | "MEDIA" | "ALTA";
export type StatusAgendamento =
  | "AGENDADO"
  | "AGUARDANDO_RESPOSTA"
  | "CONFIRMADO"
  | "NAO_CONFIRMADO"
  | "CANCELADO"
  | "REMARCACAO_SOLICITADA"
  | "SEM_RESPOSTA"
  | "REALIZADO"
  | "FALTA";
export type StatusOferta = "RESERVADA" | "ACEITA" | "RECUSADA" | "EXPIRADA" | "CANCELADA" | "FALHA_CONTATO";
export type StatusVaga = "DISPONIVEL" | "EM_OFERTA" | "PREENCHIDA" | "SEM_ELEGIVEIS" | "ENCERRADA";
export type StatusRemarcacao = "PENDENTE" | "REMARCADA" | "MANTIDA" | "CANCELADA";
export type StatusRequisicao = "ABERTA" | "RESOLVIDA" | "RESOLVIDA_COM_RESTRICAO" | "INDEFERIDA";
export type TipoRequisicaoTitular = "CONFIRMACAO_TRATAMENTO" | "ACESSO" | "CORRECAO" | "ELIMINACAO";
export type TipoBloqueio = "FERIADO" | "INDISPONIBILIDADE" | "OUTRO";
export type Periodo = "MANHA" | "TARDE" | "NOITE" | "QUALQUER";
export type CategoriaDado =
  | "MENSAGENS"
  | "RESPOSTAS"
  | "TENTATIVAS_INVALIDAS"
  | "FILA_ESPERA_ENCERRADA"
  | "PACIENTES_INATIVOS";
export type AcaoRetencao = "ELIMINAR" | "ANONIMIZAR";
export type Perfil = "ADMINISTRADOR" | "GESTOR" | "RECEPCIONISTA" | "PROFISSIONAL";

export interface Pagina<T> {
  itens: T[];
  total: number;
  page: number;
  size: number;
}

export interface ErroApi {
  codigo: string;
  mensagem: string;
  campos: { campo: string; erro: string }[];
}

export interface Referencia {
  id: number;
  nome: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Usuario {
  id: number;
  nome: string;
  login: string;
  ativo: boolean;
  mfa_habilitado: boolean;
  unidade_id: number | null;
  criado_em: string;
  perfis: Perfil[];
}

export interface PerfilSaida {
  id: number;
  nome: Perfil;
  permissoes: string[];
}

export interface Paciente {
  id: number;
  nome: string;
  telefone: string | null;
  ativo: boolean;
  prioridade_assistencial: NivelPrioridade;
  contato_autorizado: boolean;
  uso_restrito: boolean;
  anonimizado: boolean;
  data_cadastro: string;
}

export interface HistoricoConsentimento {
  id: number;
  contato_id: number;
  acao: "AUTORIZOU" | "REVOGOU" | "PREFERENCIAS";
  data_hora: string;
  origem: string;
  detalhes: Record<string, unknown> | null;
}

export interface Consentimento {
  paciente_id: number;
  autorizado: boolean;
  data_autorizacao: string | null;
  data_revogacao: string | null;
  origem_alteracao: string | null;
  preferencias: Record<string, unknown> | null;
  historico: HistoricoConsentimento[];
}

export interface Especialidade {
  id: number;
  nome: string;
  ativo: boolean;
}

export interface Unidade {
  id: number;
  nome: string;
  endereco: string | null;
  exige_profissional_especifico: boolean;
  permite_profissional_equivalente: boolean;
  ativo: boolean;
  especialidades: Referencia[];
}

export interface Profissional {
  id: number;
  nome: string;
  registro_conselho: string;
  ativo: boolean;
  especialidades: Referencia[];
  unidades: Referencia[];
}

export interface Horario {
  id: number;
  profissional_id: number;
  unidade_id: number;
  dia_semana: number;
  hora_inicio: string;
  hora_fim: string;
  duracao_consulta_min: number;
  ativo: boolean;
}

export interface Bloqueio {
  id: number;
  unidade_id: number | null;
  profissional_id: number | null;
  inicio: string;
  fim: string;
  tipo: TipoBloqueio;
  motivo: string | null;
}

export interface Agendamento {
  id: number;
  numero_agendamento: string;
  data_hora: string;
  status: StatusAgendamento;
  origem: string;
  versao: number;
  data_criacao: string;
  paciente: Referencia;
  unidade: Referencia;
  especialidade: Referencia;
  profissional: Referencia;
  status_descricao: string;
}

export interface EventoHistorico {
  data_hora: string;
  tipo: string;
  descricao: string;
  origem?: string | null;
}

export interface Preferencia {
  id?: number;
  unidade_id?: number | null;
  periodo?: Periodo;
  data_desejada?: string | null;
}

export interface FilaItem {
  id: number;
  paciente: Referencia;
  especialidade: Referencia;
  profissional: Referencia | null;
  data_entrada: string;
  prioridade: NivelPrioridade;
  disponivel_para_encaixe: boolean;
  ativo: boolean;
  observacao: string | null;
  data_saida: string | null;
  motivo_saida: string | null;
  preferencias: Preferencia[];
}

export interface Remarcacao {
  id: number;
  agendamento_id: number;
  data_solicitacao: string;
  origem: string;
  status: StatusRemarcacao;
  data_resolucao: string | null;
  observacao: string | null;
  novo_agendamento_id: number | null;
  agendamento: Agendamento;
}

export interface Vaga {
  id: number;
  agendamento_id: number;
  unidade_id: number;
  profissional_id: number;
  especialidade_id: number;
  data_hora: string;
  status: StatusVaga;
  motivo_liberacao: string;
  observacao: string | null;
  data_liberacao: string;
  data_preenchimento: string | null;
  agendamento_novo_id: number | null;
}

export interface Oferta {
  id: number;
  vaga_id: number;
  paciente: Referencia;
  vaga_data_hora: string;
  status: StatusOferta;
  prazo_resposta: string;
  reserva_ativa: boolean;
  data_criacao: string;
  data_envio: string | null;
  data_resposta: string | null;
  criterio_selecao: string | null;
  motivo: string | null;
  agendamento_gerado_id: number | null;
}

export interface Parametros {
  unidade_id: number;
  versao: number;
  vigente: boolean;
  criado_em: string;
  criado_por_id: number | null;
  antecedencia_lembrete_horas: number;
  prazo_resposta_min: number;
  tentativas_contato: number;
  janela_reserva_min: number;
  antecedencia_minima_oferta_min: number;
  nome_regra: string;
  considera_prioridade_assistencial: boolean;
  exige_profissional_compativel: boolean;
  criterio_desempate: "DATA_ENTRADA" | "ID";
}

export interface Indicadores {
  periodo: { inicio: string; fim: string };
  filtros: { unidade_id: number | null; especialidade_id: number | null; profissional_id: number | null };
  agendamentos: {
    total: number;
    confirmados: number;
    cancelados: number;
    nao_respondidos: number;
    remarcacoes_solicitadas: number;
    pendentes_de_resposta: number;
    realizados: number;
    faltas: number;
    por_status: Record<StatusAgendamento, number>;
  };
  vagas: {
    liberadas: number;
    recuperadas: number;
    em_oferta: number;
    sem_elegiveis: number;
    encerradas: number;
    tempo_medio_recuperacao_min: number | null;
  };
  ofertas: Record<StatusOferta, number>;
  taxas: {
    taxa_confirmacao: number | null;
    taxa_absenteismo: number | null;
    taxa_recuperacao: number | null;
    taxa_ocupacao: number | null;
  };
}

export interface Requisicao {
  id: number;
  paciente_id: number;
  tipo: TipoRequisicaoTitular;
  canal: string;
  status: StatusRequisicao;
  dados_correcao: { nome?: string | null; telefone?: string | null } | null;
  data_solicitacao: string;
  data_resolucao: string | null;
  desfecho: string | null;
  dados?: Record<string, unknown> | null;
}

export interface Politica {
  categoria: CategoriaDado;
  prazo_dias: number;
  acao: AcaoRetencao;
  ativo: boolean;
  versao: number;
  atualizado_em: string;
  ultima_execucao: string | null;
}

export interface LogAuditoria {
  id: number;
  acao: string;
  entidade: string;
  entidade_id: string | null;
  data_hora: string;
  origem: string;
  usuario_id: number | null;
  detalhes: Record<string, unknown> | null;
}

export interface MensagemSimulador {
  destino: string;
  [chave: string]: unknown;
}

export interface Health {
  status: "ok" | "degradado";
  aplicacao: string;
  versao: string;
  banco: string;
  mensageria: string;
  agendador: boolean;
}
