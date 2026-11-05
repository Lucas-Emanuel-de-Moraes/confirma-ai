"use client";

import { useState } from "react";
import { useAcao, useConsulta } from "@/hooks/useApi";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/permissoes";
import { api } from "@/lib/api";
import { dataHora, opcoes, rotulo } from "@/lib/formato";
import type { Pagina, Politica, Referencia, Requisicao, TipoRequisicaoTitular } from "@/lib/types";
import { ExigePermissao } from "@/components/AppShell";
import { Abas, Alerta, AreaTexto, BarraFiltros, Botao, CabecalhoPagina, Caixa, Cartao, Entrada, Selecao } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { Paginacao, Tabela } from "@/components/ui/Tabela";
import { useAvisos } from "@/components/ui/Aviso";
import { SeloRequisicao } from "@/components/Status";
import { SeletorPaciente } from "@/components/SeletorPaciente";

export default function LgpdPage() {
  return (
    <ExigePermissao permissao={P.TITULAR_GERENCIAR}>
      <Conteudo />
    </ExigePermissao>
  );
}

function Conteudo() {
  const { pode } = useAuth();
  const [aba, setAba] = useState<"titular" | "retencao">("titular");
  return (
    <>
      <CabecalhoPagina titulo="LGPD" descricao="Requisições do titular de dados (UC11) e política de retenção com eliminação ou anonimização (UC12)." />
      {pode(P.RETENCAO_GERENCIAR) && (
        <Abas
          abas={[
            { id: "titular", rotulo: "Requisições do titular" },
            { id: "retencao", rotulo: "Retenção de dados" },
          ]}
          ativa={aba}
          onChange={setAba}
        />
      )}
      {aba === "titular" ? <Requisicoes /> : <Retencao />}
    </>
  );
}

/* ------------------------------------------------------------------ Requisições do titular */
function Requisicoes() {
  const [status, setStatus] = useState("ABERTA");
  const [page, setPage] = useState(1);
  const lista = useConsulta<Pagina<Requisicao>>("/requisicoes-titular", { status, page, size: 20 });
  const [nova, setNova] = useState(false);
  const [alvo, setAlvo] = useState<Requisicao | null>(null);

  return (
    <>
      <BarraFiltros>
        <Selecao rotulo="Situação" vazio="Todas" value={status} onChange={(e) => (setStatus(e.target.value), setPage(1))} opcoes={opcoes("statusRequisicao")} />
        <div className="flex items-end lg:col-start-4 lg:justify-end">
          <Botao onClick={() => setNova(true)}>Registrar requisição</Botao>
        </div>
      </BarraFiltros>
      {lista.erro && <Alerta>{lista.erro}</Alerta>}
      <Cartao>
        <Tabela
          itens={lista.dados?.itens}
          carregando={lista.carregando}
          chave={(r) => r.id}
          onLinha={setAlvo}
          vazio="Nenhuma requisição nesta situação."
          colunas={[
            { titulo: "Data", render: (r) => dataHora(r.data_solicitacao) },
            { titulo: "Paciente", render: (r) => `#${r.paciente_id}` },
            { titulo: "Tipo", render: (r) => rotulo("tipoRequisicao", r.tipo) },
            { titulo: "Canal", render: (r) => r.canal },
            { titulo: "Situação", render: (r) => <SeloRequisicao status={r.status} /> },
            { titulo: "Desfecho", render: (r) => <span className="text-xs">{r.desfecho ?? "—"}</span> },
          ]}
        />
        {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
      </Cartao>
      <NovaRequisicao
        aberto={nova}
        onFechar={() => setNova(false)}
        onSalvo={() => {
          setNova(false);
          void lista.recarregar();
        }}
      />
      <ResolverRequisicao requisicao={alvo} onFechar={() => setAlvo(null)} onSalvo={() => void lista.recarregar()} />
    </>
  );
}

function NovaRequisicao({ aberto, onFechar, onSalvo }: { aberto: boolean; onFechar: () => void; onSalvo: () => void }) {
  const avisar = useAvisos();
  const [paciente, setPaciente] = useState<Referencia | null>(null);
  const [form, setForm] = useState({ tipo: "ACESSO" as TipoRequisicaoTitular, canal: "presencial", nome: "", telefone: "" });
  const salvar = useAcao(async () => {
    if (!paciente) throw new Error("Selecione o paciente.");
    await api.post("/requisicoes-titular", {
      paciente_id: paciente.id,
      tipo: form.tipo,
      canal: form.canal,
      dados_correcao: form.tipo === "CORRECAO" ? { nome: form.nome || null, telefone: form.telefone || null } : null,
    });
    avisar("Requisição registrada.");
    setPaciente(null);
    onSalvo();
  });
  return (
    <Modal
      aberto={aberto}
      titulo="Registrar requisição do titular"
      onFechar={onFechar}
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-requisicao" carregando={salvar.executando}>
            Registrar
          </Botao>
        </>
      }
    >
      {salvar.erro && <Alerta onFechar={salvar.limparErro}>{salvar.erro}</Alerta>}
      <form id="form-requisicao" className="space-y-4" onSubmit={(e) => (e.preventDefault(), void salvar.executar())}>
        <SeletorPaciente valor={paciente} onChange={setPaciente} rotulo="Titular (paciente)" />
        <Selecao rotulo="Tipo" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value as TipoRequisicaoTitular })} opcoes={opcoes("tipoRequisicao")} />
        <Selecao
          rotulo="Canal"
          value={form.canal}
          onChange={(e) => setForm({ ...form, canal: e.target.value })}
          opcoes={[
            { value: "presencial", label: "Presencial" },
            { value: "telefone", label: "Telefone" },
            { value: "email", label: "E-mail" },
            { value: "mensageria", label: "Mensageria" },
          ]}
        />
        {form.tipo === "CORRECAO" && (
          <div className="grid gap-4 rounded-lg border border-slate-200 p-3 sm:grid-cols-2">
            <Entrada rotulo="Nome correto" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
            <Entrada rotulo="Telefone correto" value={form.telefone} onChange={(e) => setForm({ ...form, telefone: e.target.value })} />
          </div>
        )}
      </form>
    </Modal>
  );
}

function ResolverRequisicao({ requisicao, onFechar, onSalvo }: { requisicao: Requisicao | null; onFechar: () => void; onSalvo: () => void }) {
  const avisar = useAvisos();
  const [desfecho, setDesfecho] = useState("");
  const [resultado, setResultado] = useState<Requisicao | null>(null);
  const [chave, setChave] = useState<Requisicao | null>(null);
  if (requisicao !== chave) {
    setChave(requisicao);
    setDesfecho("");
    setResultado(null);
  }
  const salvar = useAcao(async (acao: "RESOLVER" | "INDEFERIR") => {
    if (!requisicao) return;
    const { data } = await api.patch<Requisicao>(`/requisicoes-titular/${requisicao.id}`, { acao, desfecho: desfecho || null });
    avisar(acao === "RESOLVER" ? "Requisição atendida." : "Requisição indeferida.");
    setResultado(data);
    onSalvo();
  });
  const r = resultado ?? requisicao;
  return (
    <Modal aberto={requisicao !== null} titulo={r ? `Requisição #${r.id} · ${rotulo("tipoRequisicao", r.tipo)}` : ""} onFechar={onFechar} largura="lg">
      {r && (
        <div className="space-y-4">
          {salvar.erro && <Alerta onFechar={salvar.limparErro}>{salvar.erro}</Alerta>}
          <div className="flex items-center gap-2 text-sm">
            Situação: <SeloRequisicao status={r.status} />
          </div>
          {r.dados_correcao && <p className="text-sm text-slate-600">Correção solicitada: {JSON.stringify(r.dados_correcao)}</p>}
          {r.status === "ABERTA" ? (
            <>
              <AreaTexto rotulo="Desfecho / resposta ao titular" value={desfecho} onChange={(e) => setDesfecho(e.target.value)} />
              {r.tipo === "ELIMINACAO" && (
                <Alerta tipo="aviso">Atender uma eliminação anonimiza os dados pessoais do paciente. Registros obrigatórios são mantidos com restrição.</Alerta>
              )}
              <div className="flex gap-2">
                <Botao carregando={salvar.executando} onClick={() => salvar.executar("RESOLVER")}>
                  Atender
                </Botao>
                <Botao variante="secundario" carregando={salvar.executando} onClick={() => salvar.executar("INDEFERIR")}>
                  Indeferir
                </Botao>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-700">Desfecho: {r.desfecho ?? "—"}</p>
          )}
          {resultado?.dados && (
            <section>
              <h3 className="mb-1 text-sm font-semibold">Dados para entregar ao titular</h3>
              <pre className="max-h-72 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(resultado.dados, null, 2)}</pre>
            </section>
          )}
        </div>
      )}
    </Modal>
  );
}

/* ------------------------------------------------------------------ Retenção */
function Retencao() {
  const avisar = useAvisos();
  const lista = useConsulta<Politica[]>("/retencao/politicas");
  const [edicao, setEdicao] = useState<Record<string, { prazo_dias: number; ativo: boolean }>>({});
  const [resultado, setResultado] = useState<unknown>(null);

  const valor = (p: Politica) => edicao[p.categoria] ?? { prazo_dias: p.prazo_dias, ativo: p.ativo };
  const salvar = useAcao(async () => {
    const corpo = Object.entries(edicao).map(([categoria, v]) => ({ categoria, ...v }));
    if (!corpo.length) return;
    await api.put("/retencao/politicas", corpo);
    setEdicao({});
    avisar("Política de retenção atualizada.");
    void lista.recarregar();
  });
  const executar = useAcao(async () => {
    const { data } = await api.post("/retencao/executar");
    setResultado(data);
    avisar("Rotina de retenção executada.");
    void lista.recarregar();
  });

  return (
    <Cartao
      titulo="Prazos de retenção por categoria"
      acoes={
        <div className="flex gap-2">
          <Botao variante="secundario" tamanho="sm" carregando={executar.executando} onClick={() => executar.executar()}>
            Executar rotina agora
          </Botao>
          <Botao tamanho="sm" disabled={!Object.keys(edicao).length} carregando={salvar.executando} onClick={() => salvar.executar()}>
            Salvar alterações
          </Botao>
        </div>
      }
    >
      {(lista.erro || salvar.erro || executar.erro) && <Alerta>{lista.erro ?? salvar.erro ?? executar.erro}</Alerta>}
      <Tabela
        itens={lista.dados ?? undefined}
        carregando={lista.carregando}
        chave={(p) => p.categoria}
        colunas={[
          { titulo: "Categoria", render: (p) => <span className="font-medium">{rotulo("categoriaDado", p.categoria)}</span> },
          { titulo: "Ação", render: (p) => rotulo("acaoRetencao", p.acao) },
          {
            titulo: "Prazo (dias)",
            render: (p) => (
              <input
                type="number"
                min={1}
                aria-label={`Prazo para ${rotulo("categoriaDado", p.categoria)}`}
                className="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm"
                value={valor(p).prazo_dias}
                onChange={(e) => setEdicao({ ...edicao, [p.categoria]: { ...valor(p), prazo_dias: Number(e.target.value) } })}
              />
            ),
          },
          {
            titulo: "Ativa",
            render: (p) => (
              <Caixa rotulo="" aria-label="Ativa" checked={valor(p).ativo} onChange={(e) => setEdicao({ ...edicao, [p.categoria]: { ...valor(p), ativo: e.target.checked } })} />
            ),
          },
          { titulo: "Versão", render: (p) => `v${p.versao}` },
          { titulo: "Última execução", render: (p) => dataHora(p.ultima_execucao) },
        ]}
      />
      {resultado !== null && (
        <pre className="mt-4 max-h-60 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(resultado, null, 2)}</pre>
      )}
    </Cartao>
  );
}
