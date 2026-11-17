"use client";

import { useState } from "react";
import { useAcao, useConsulta, useDebounce } from "@/hooks/useApi";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/permissoes";
import { api, lerErro } from "@/lib/api";
import { dataHora, opcoes, telefone } from "@/lib/formato";
import type { Agendamento, Consentimento, NivelPrioridade, Pagina, Paciente } from "@/lib/types";
import { ExigePermissao } from "@/components/AppShell";
import { Alerta, BarraFiltros, Botao, CabecalhoPagina, Caixa, Cartao, Entrada, ItemDefinicao, Selecao, Selo } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { Paginacao, Tabela } from "@/components/ui/Tabela";
import { useAvisos } from "@/components/ui/Aviso";
import { SeloAgendamento, SeloAtivo, SeloPrioridade } from "@/components/Status";

export default function PacientesPage() {
  return (
    <ExigePermissao permissao={P.PACIENTES_LER}>
      <Conteudo />
    </ExigePermissao>
  );
}

function Conteudo() {
  const { pode } = useAuth();
  const [busca, setBusca] = useState("");
  const [ativo, setAtivo] = useState("true");
  const [page, setPage] = useState(1);
  const buscaD = useDebounce(busca);
  const lista = useConsulta<Pagina<Paciente>>("/pacientes", { busca: buscaD, ativo, page, size: 20 });
  const [editando, setEditando] = useState<Paciente | "novo" | null>(null);
  const [detalhe, setDetalhe] = useState<Paciente | null>(null);

  return (
    <>
      <CabecalhoPagina
        titulo="Pacientes"
        descricao="Cadastro, consulta e inativação de pacientes (HU01), com autorização de contato (LGPD)."
        acoes={pode(P.PACIENTES_ESCREVER) && <Botao onClick={() => setEditando("novo")}>Novo paciente</Botao>}
      />
      <BarraFiltros>
        <Entrada
          rotulo="Buscar"
          placeholder="Nome ou telefone"
          className="sm:col-span-2"
          value={busca}
          onChange={(e) => {
            setBusca(e.target.value);
            setPage(1);
          }}
        />
        <Selecao
          rotulo="Situação"
          value={ativo}
          onChange={(e) => {
            setAtivo(e.target.value);
            setPage(1);
          }}
          vazio="Todos"
          opcoes={[
            { value: "true", label: "Ativos" },
            { value: "false", label: "Inativos" },
          ]}
        />
      </BarraFiltros>
      {lista.erro && <Alerta>{lista.erro}</Alerta>}
      <Cartao>
        <Tabela
          rotulo="Pacientes"
          itens={lista.dados?.itens}
          carregando={lista.carregando}
          chave={(p) => p.id}
          onLinha={setDetalhe}
          colunas={[
            { titulo: "Nome", render: (p) => <span className="font-medium text-slate-900">{p.nome}</span> },
            { titulo: "Telefone", render: (p) => telefone(p.telefone) },
            { titulo: "Prioridade", render: (p) => <SeloPrioridade nivel={p.prioridade_assistencial} /> },
            {
              titulo: "Contato",
              render: (p) => <Selo cor={p.contato_autorizado ? "verde" : "amarelo"}>{p.contato_autorizado ? "Autorizado" : "Não autorizado"}</Selo>,
            },
            { titulo: "Situação", render: (p) => <SeloAtivo ativo={p.ativo} /> },
          ]}
        />
        {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
      </Cartao>

      <FormPaciente
        alvo={editando}
        onFechar={() => setEditando(null)}
        onSalvo={() => {
          setEditando(null);
          void lista.recarregar();
        }}
      />
      <DetalhePaciente
        paciente={detalhe}
        onFechar={() => setDetalhe(null)}
        onEditar={(p) => {
          setDetalhe(null);
          setEditando(p);
        }}
        onAlterado={(p) => {
          setDetalhe(p);
          void lista.recarregar();
        }}
      />
    </>
  );
}

function FormPaciente({ alvo, onFechar, onSalvo }: { alvo: Paciente | "novo" | null; onFechar: () => void; onSalvo: () => void }) {
  const avisar = useAvisos();
  const novo = alvo === "novo";
  const p = alvo && alvo !== "novo" ? alvo : null;
  const [form, setForm] = useState({ nome: "", telefone: "", prioridade_assistencial: "NENHUMA" as NivelPrioridade, autorizar_contato: true });
  const [aviso, setAviso] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [chave, setChave] = useState<unknown>(null);

  if (alvo !== chave) {
    setChave(alvo);
    setAviso(null);
    setErro(null);
    setForm({
      nome: p?.nome ?? "",
      telefone: p?.telefone ?? "",
      prioridade_assistencial: p?.prioridade_assistencial ?? "NENHUMA",
      autorizar_contato: true,
    });
  }

  async function salvar(ignorarDuplicidade = false) {
    setEnviando(true);
    setErro(null);
    try {
      if (novo) {
        await api.post("/pacientes", { ...form, ignorar_aviso_duplicidade: ignorarDuplicidade });
        avisar("Paciente cadastrado.");
      } else if (p) {
        await api.put(`/pacientes/${p.id}`, {
          nome: form.nome,
          telefone: form.telefone,
          prioridade_assistencial: form.prioridade_assistencial,
          ignorar_aviso_duplicidade: ignorarDuplicidade,
        });
        avisar("Paciente atualizado.");
      }
      onSalvo();
    } catch (e) {
      const err = lerErro(e);
      if (err.codigo === "TELEFONE_DUPLICADO")
        setAviso("Já existe paciente ativo com este telefone. Confira na busca se não é o mesmo paciente ou salve mesmo assim.");
      else setErro(err.campos.length ? `${err.mensagem} ${err.campos.map((c) => c.erro).join("; ")}` : err.mensagem);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Modal
      aberto={alvo !== null}
      titulo={novo ? "Novo paciente" : "Editar paciente"}
      onFechar={onFechar}
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar}>
            Cancelar
          </Botao>
          {aviso ? (
            <Botao variante="perigo" carregando={enviando} onClick={() => salvar(true)}>
              Salvar mesmo assim
            </Botao>
          ) : (
            <Botao type="submit" form="form-paciente" carregando={enviando}>
              Salvar
            </Botao>
          )}
        </>
      }
    >
      {erro && <Alerta>{erro}</Alerta>}
      {aviso && <Alerta tipo="aviso">{aviso}</Alerta>}
      <form
        id="form-paciente"
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void salvar();
        }}
      >
        <Entrada rotulo="Nome completo" required minLength={3} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        <Entrada
          rotulo="Telefone / WhatsApp"
          required
          placeholder="(65) 99999-1234"
          ajuda="Com DDD. Usado para lembretes e ofertas de encaixe."
          value={form.telefone}
          onChange={(e) => {
            setForm({ ...form, telefone: e.target.value });
            setAviso(null);
          }}
        />
        <Selecao
          rotulo="Prioridade assistencial"
          value={form.prioridade_assistencial}
          onChange={(e) => setForm({ ...form, prioridade_assistencial: e.target.value as NivelPrioridade })}
          opcoes={opcoes("prioridade")}
        />
        {novo && (
          <Caixa
            rotulo="Paciente autoriza contato por mensagem"
            ajuda="Registro de consentimento (LGPD). Pode ser revogado a qualquer momento."
            checked={form.autorizar_contato}
            onChange={(e) => setForm({ ...form, autorizar_contato: e.target.checked })}
          />
        )}
      </form>
    </Modal>
  );
}

function DetalhePaciente({
  paciente,
  onFechar,
  onEditar,
  onAlterado,
}: {
  paciente: Paciente | null;
  onFechar: () => void;
  onEditar: (p: Paciente) => void;
  onAlterado: (p: Paciente) => void;
}) {
  const { pode } = useAuth();
  const avisar = useAvisos();
  const id = paciente?.id;
  const consentimento = useConsulta<Consentimento>(id ? `/pacientes/${id}/consentimento` : null);
  const agenda = useConsulta<Pagina<Agendamento>>(id && pode(P.AGENDA_LER) ? "/agendamentos" : null, { paciente_id: id, size: 10 });
  const acao = useAcao(async (tipo: "inativar" | "reativar" | "autorizar" | "revogar") => {
    if (!paciente) return;
    let r;
    if (tipo === "inativar") r = await api.patch<Paciente>(`/pacientes/${paciente.id}/inativar`);
    else if (tipo === "reativar") r = await api.patch<Paciente>(`/pacientes/${paciente.id}/reativar`);
    else if (tipo === "autorizar") r = await api.post<Paciente>(`/pacientes/${paciente.id}/autorizacao`, { origem: "recepcao" });
    else r = await api.delete<Paciente>(`/pacientes/${paciente.id}/autorizacao`, { params: { motivo: "Solicitado pelo paciente" } });
    avisar(
      { inativar: "Paciente inativado.", reativar: "Paciente reativado.", autorizar: "Autorização registrada.", revogar: "Autorização revogada." }[tipo],
    );
    onAlterado(r.data);
    void consentimento.recarregar();
  });
  const escrever = pode(P.PACIENTES_ESCREVER);

  return (
    <Modal aberto={paciente !== null} titulo={paciente?.nome ?? ""} onFechar={onFechar} largura="lg">
      {paciente && (
        <div className="space-y-6">
          {acao.erro && <Alerta onFechar={acao.limparErro}>{acao.erro}</Alerta>}
          {paciente.uso_restrito && <Alerta tipo="aviso">Uso restrito: dados com tratamento limitado por requisição do titular.</Alerta>}
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <ItemDefinicao termo="Telefone">{telefone(paciente.telefone)}</ItemDefinicao>
            <ItemDefinicao termo="Prioridade">
              <SeloPrioridade nivel={paciente.prioridade_assistencial} />
            </ItemDefinicao>
            <ItemDefinicao termo="Situação">
              <SeloAtivo ativo={paciente.ativo} />
            </ItemDefinicao>
            <ItemDefinicao termo="Cadastrado em">{dataHora(paciente.data_cadastro)}</ItemDefinicao>
            <ItemDefinicao termo="Código">#{paciente.id}</ItemDefinicao>
          </dl>
          {escrever && (
            <div className="flex flex-wrap gap-2">
              <Botao variante="secundario" tamanho="sm" onClick={() => onEditar(paciente)} disabled={paciente.anonimizado}>
                Editar
              </Botao>
              {paciente.ativo ? (
                <Botao variante="secundario" tamanho="sm" carregando={acao.executando} onClick={() => acao.executar("inativar")}>
                  Inativar
                </Botao>
              ) : (
                <Botao variante="secundario" tamanho="sm" carregando={acao.executando} onClick={() => acao.executar("reativar")}>
                  Reativar
                </Botao>
              )}
            </div>
          )}

          <section>
            <h3 className="mb-2 text-sm font-semibold text-slate-800">Autorização de contato (LGPD)</h3>
            <div className="rounded-lg border border-slate-200 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Selo cor={paciente.contato_autorizado ? "verde" : "amarelo"}>
                  {paciente.contato_autorizado ? "Contato autorizado" : "Sem autorização de contato"}
                </Selo>
                {escrever &&
                  (paciente.contato_autorizado ? (
                    <Botao variante="perigo" tamanho="sm" carregando={acao.executando} onClick={() => acao.executar("revogar")}>
                      Revogar autorização
                    </Botao>
                  ) : (
                    <Botao tamanho="sm" carregando={acao.executando} onClick={() => acao.executar("autorizar")}>
                      Registrar autorização
                    </Botao>
                  ))}
              </div>
              {consentimento.dados?.historico.length ? (
                <ul className="mt-3 space-y-1 text-xs text-slate-600">
                  {consentimento.dados.historico.map((h) => (
                    <li key={h.id}>
                      {dataHora(h.data_hora)} — {h.acao.toLowerCase()} (origem: {h.origem})
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </section>

          {pode(P.AGENDA_LER) && (
            <section>
              <h3 className="mb-2 text-sm font-semibold text-slate-800">Agendamentos recentes</h3>
              <Tabela
                itens={agenda.dados?.itens}
                carregando={agenda.carregando}
                chave={(a) => a.id}
                vazio="Nenhum agendamento."
                colunas={[
                  { titulo: "Data", render: (a) => dataHora(a.data_hora) },
                  { titulo: "Especialidade", render: (a) => a.especialidade.nome },
                  { titulo: "Status", render: (a) => <SeloAgendamento status={a.status} descricao={a.status_descricao} /> },
                ]}
              />
            </section>
          )}
        </div>
      )}
    </Modal>
  );
}
