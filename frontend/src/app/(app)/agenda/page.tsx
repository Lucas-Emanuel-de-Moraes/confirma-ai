"use client";

import { useState } from "react";
import { useAcao, useConsulta, useDebounce } from "@/hooks/useApi";
import { useCadastros } from "@/hooks/useCadastros";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/permissoes";
import { api } from "@/lib/api";
import { dataHora, opcoes, paraApiDataHora } from "@/lib/formato";
import { useHoje } from "@/hooks/useHoje";
import type { Agendamento, EventoHistorico, Pagina, Referencia } from "@/lib/types";
import { ExigePermissao } from "@/components/AppShell";
import { Alerta, AreaTexto, BarraFiltros, Botao, CabecalhoPagina, Cartao, Entrada, ItemDefinicao, Selecao } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { Paginacao, Tabela } from "@/components/ui/Tabela";
import { useAvisos } from "@/components/ui/Aviso";
import { SeloAgendamento } from "@/components/Status";
import { SeletorPaciente } from "@/components/SeletorPaciente";

export default function AgendaPage() {
  return (
    <ExigePermissao permissao={P.AGENDA_LER}>
      <ComData />
    </ExigePermissao>
  );
}

/** Só monta a página quando a data do navegador está disponível (não no pré-render). */
function ComData() {
  const hoje = useHoje();
  return hoje ? <Conteudo hoje={hoje} /> : null;
}

function Conteudo({ hoje }: { hoje: string }) {
  const { pode } = useAuth();
  const cad = useCadastros();
  const [f, setF] = useState({ data: hoje, unidade_id: "", especialidade_id: "", profissional_id: "", status: "", busca: "" });
  const [page, setPage] = useState(1);
  const buscaD = useDebounce(f.busca);
  const lista = useConsulta<Pagina<Agendamento>>("/agendamentos", { ...f, busca: buscaD, page, size: 25 });
  const [novo, setNovo] = useState(false);
  const [detalhe, setDetalhe] = useState<Agendamento | null>(null);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setF({ ...f, [k]: e.target.value });
    setPage(1);
  };

  return (
    <>
      <CabecalhoPagina
        titulo="Agenda"
        descricao="Consultas com status textual de confirmação (RF04). Clique em uma linha para ver o histórico e registrar ações."
        acoes={pode(P.AGENDA_ESCREVER) && <Botao onClick={() => setNovo(true)}>Novo agendamento</Botao>}
      />
      <BarraFiltros>
        <Entrada rotulo="Dia" type="date" value={f.data} onChange={set("data")} ajuda="Deixe vazio para todos os dias" />
        <Selecao rotulo="Unidade" vazio="Todas" value={f.unidade_id} onChange={set("unidade_id")} opcoes={cad.unidades.map((u) => ({ value: u.id, label: u.nome }))} />
        <Selecao
          rotulo="Especialidade"
          vazio="Todas"
          value={f.especialidade_id}
          onChange={set("especialidade_id")}
          opcoes={cad.especialidades.map((e) => ({ value: e.id, label: e.nome }))}
        />
        <Selecao
          rotulo="Profissional"
          vazio="Todos"
          value={f.profissional_id}
          onChange={set("profissional_id")}
          opcoes={cad.profissionais.map((p) => ({ value: p.id, label: p.nome }))}
        />
        <Selecao rotulo="Status" vazio="Todos" value={f.status} onChange={set("status")} opcoes={opcoes("statusAgendamento")} />
        <Entrada rotulo="Buscar" placeholder="Paciente ou nº do agendamento" value={f.busca} onChange={set("busca")} className="sm:col-span-2" />
      </BarraFiltros>

      {lista.erro && <Alerta>{lista.erro}</Alerta>}
      <Cartao>
        <Tabela
          rotulo="Agendamentos"
          itens={lista.dados?.itens}
          carregando={lista.carregando}
          chave={(a) => a.id}
          onLinha={setDetalhe}
          vazio="Nenhum agendamento com esses filtros."
          colunas={[
            { titulo: "Data e hora", render: (a) => <span className="font-medium tabular-nums">{dataHora(a.data_hora)}</span> },
            { titulo: "Paciente", render: (a) => a.paciente.nome },
            { titulo: "Especialidade", render: (a) => a.especialidade.nome },
            { titulo: "Profissional", render: (a) => a.profissional.nome },
            { titulo: "Unidade", render: (a) => a.unidade.nome },
            {
              titulo: "Status",
              render: (a) => (
                <div>
                  <SeloAgendamento status={a.status} />
                  <p className="mt-0.5 text-xs text-slate-500">{a.status_descricao}</p>
                </div>
              ),
            },
          ]}
        />
        {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
      </Cartao>

      <NovoAgendamento
        aberto={novo}
        cad={cad}
        onFechar={() => setNovo(false)}
        onSalvo={() => {
          setNovo(false);
          void lista.recarregar();
        }}
      />
      <DetalheAgendamento
        hoje={hoje}
        agendamento={detalhe}
        onFechar={() => setDetalhe(null)}
        onAlterado={(a) => {
          setDetalhe(a);
          void lista.recarregar();
        }}
      />
    </>
  );
}

function NovoAgendamento({ aberto, cad, onFechar, onSalvo }: { aberto: boolean; cad: ReturnType<typeof useCadastros>; onFechar: () => void; onSalvo: () => void }) {
  const avisar = useAvisos();
  const [paciente, setPaciente] = useState<Referencia | null>(null);
  const [form, setForm] = useState({ unidade_id: "", especialidade_id: "", profissional_id: "", data_hora: "" });
  const salvar = useAcao(async () => {
    if (!paciente) throw new Error("Selecione o paciente.");
    await api.post("/agendamentos", {
      paciente_id: paciente.id,
      unidade_id: Number(form.unidade_id),
      especialidade_id: Number(form.especialidade_id),
      profissional_id: Number(form.profissional_id),
      data_hora: paraApiDataHora(form.data_hora),
    });
    avisar("Agendamento registrado.");
    setPaciente(null);
    setForm({ unidade_id: "", especialidade_id: "", profissional_id: "", data_hora: "" });
    onSalvo();
  });

  const unidade = cad.unidades.find((u) => String(u.id) === form.unidade_id);
  const especialidades = unidade ? unidade.especialidades : cad.especialidades;
  const profissionais = cad.profissionais.filter(
    (p) =>
      (!form.unidade_id || p.unidades.some((u) => String(u.id) === form.unidade_id)) &&
      (!form.especialidade_id || p.especialidades.some((e) => String(e.id) === form.especialidade_id)),
  );

  return (
    <Modal
      aberto={aberto}
      titulo="Novo agendamento"
      onFechar={onFechar}
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-agendamento" carregando={salvar.executando}>
            Agendar
          </Botao>
        </>
      }
    >
      {salvar.erro && <Alerta onFechar={salvar.limparErro}>{salvar.erro}</Alerta>}
      <form
        id="form-agendamento"
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void salvar.executar();
        }}
      >
        <SeletorPaciente valor={paciente} onChange={setPaciente} />
        <Selecao
          rotulo="Unidade"
          required
          vazio="Selecione…"
          value={form.unidade_id}
          onChange={(e) => setForm({ ...form, unidade_id: e.target.value, especialidade_id: "", profissional_id: "" })}
          opcoes={cad.unidades.map((u) => ({ value: u.id, label: u.nome }))}
        />
        <Selecao
          rotulo="Especialidade"
          required
          vazio="Selecione…"
          value={form.especialidade_id}
          onChange={(e) => setForm({ ...form, especialidade_id: e.target.value, profissional_id: "" })}
          opcoes={especialidades.map((e) => ({ value: e.id, label: e.nome }))}
        />
        <Selecao
          rotulo="Profissional"
          required
          vazio="Selecione…"
          value={form.profissional_id}
          onChange={(e) => setForm({ ...form, profissional_id: e.target.value })}
          opcoes={profissionais.map((p) => ({ value: p.id, label: p.nome }))}
        />
        <Entrada
          rotulo="Data e hora"
          type="datetime-local"
          required
          value={form.data_hora}
          onChange={(e) => setForm({ ...form, data_hora: e.target.value })}
          ajuda="A API valida o horário de atendimento, bloqueios e conflitos."
        />
      </form>
    </Modal>
  );
}

function DetalheAgendamento({
  hoje,
  agendamento,
  onFechar,
  onAlterado,
}: {
  hoje: string;
  agendamento: Agendamento | null;
  onFechar: () => void;
  onAlterado: (a: Agendamento) => void;
}) {
  const { pode } = useAuth();
  const avisar = useAvisos();
  const historico = useConsulta<EventoHistorico[]>(agendamento ? `/agendamentos/${agendamento.id}/historico` : null);
  const [motivo, setMotivo] = useState("");
  const [cancelando, setCancelando] = useState(false);

  const acao = useAcao(async (tipo: "cancelar" | "COMPARECEU" | "FALTOU") => {
    if (!agendamento) return;
    const { data } =
      tipo === "cancelar"
        ? await api.post<Agendamento>(`/agendamentos/${agendamento.id}/cancelar`, { motivo })
        : await api.post<Agendamento>(`/agendamentos/${agendamento.id}/comparecimento`, { tipo });
    avisar(tipo === "cancelar" ? "Agendamento cancelado. A vaga foi liberada para encaixe." : "Comparecimento registrado.");
    setCancelando(false);
    setMotivo("");
    onAlterado(data);
    void historico.recarregar();
  });

  const a = agendamento;
  const encerrado = a && ["CANCELADO", "REALIZADO", "FALTA"].includes(a.status);
  // A API só aceita comparecimento/falta a partir do dia da consulta
  const jaChegouODia = a ? a.data_hora.slice(0, 10) <= hoje : false;

  return (
    <Modal aberto={a !== null} titulo={a ? `Agendamento ${a.numero_agendamento}` : ""} onFechar={onFechar} largura="lg">
      {a && (
        <div className="space-y-6">
          {acao.erro && <Alerta onFechar={acao.limparErro}>{acao.erro}</Alerta>}
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <ItemDefinicao termo="Paciente">{a.paciente.nome}</ItemDefinicao>
            <ItemDefinicao termo="Data e hora">{dataHora(a.data_hora)}</ItemDefinicao>
            <ItemDefinicao termo="Status">
              <SeloAgendamento status={a.status} />
            </ItemDefinicao>
            <ItemDefinicao termo="Especialidade">{a.especialidade.nome}</ItemDefinicao>
            <ItemDefinicao termo="Profissional">{a.profissional.nome}</ItemDefinicao>
            <ItemDefinicao termo="Unidade">{a.unidade.nome}</ItemDefinicao>
          </dl>
          <p className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">{a.status_descricao}</p>

          {pode(P.AGENDA_ESCREVER) && !encerrado && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {jaChegouODia && (
                  <>
                    <Botao variante="secundario" tamanho="sm" carregando={acao.executando} onClick={() => acao.executar("COMPARECEU")}>
                      Registrar comparecimento
                    </Botao>
                    <Botao variante="secundario" tamanho="sm" carregando={acao.executando} onClick={() => acao.executar("FALTOU")}>
                      Registrar falta
                    </Botao>
                  </>
                )}
                <Botao variante="perigo" tamanho="sm" onClick={() => setCancelando(!cancelando)}>
                  Cancelar agendamento
                </Botao>
              </div>
              {cancelando && (
                <form
                  className="space-y-2 rounded-lg border border-red-200 bg-red-50/50 p-3"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void acao.executar("cancelar");
                  }}
                >
                  <AreaTexto rotulo="Motivo do cancelamento" required minLength={3} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
                  <Botao type="submit" variante="perigo" tamanho="sm" carregando={acao.executando}>
                    Confirmar cancelamento
                  </Botao>
                </form>
              )}
            </div>
          )}

          <section>
            <h3 className="mb-3 text-sm font-semibold text-slate-800">Linha do tempo</h3>
            {historico.carregando && <p className="text-sm text-slate-500">Carregando…</p>}
            <ol className="relative space-y-4 border-l border-slate-200 pl-5">
              {historico.dados?.map((h, i) => (
                <li key={i} className="relative">
                  <span className="absolute -left-[1.6rem] top-1 h-2.5 w-2.5 rounded-full bg-marca-500 ring-4 ring-white" aria-hidden />
                  <p className="text-xs text-slate-500">
                    {dataHora(h.data_hora)} · {h.tipo}
                    {h.origem ? ` · ${h.origem}` : ""}
                  </p>
                  <p className="text-sm text-slate-800">{h.descricao}</p>
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}
    </Modal>
  );
}
