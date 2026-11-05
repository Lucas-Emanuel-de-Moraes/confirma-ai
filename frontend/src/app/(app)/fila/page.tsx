"use client";

import { useState } from "react";
import { useAcao, useConsulta, useDebounce } from "@/hooks/useApi";
import { useCadastros } from "@/hooks/useCadastros";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/permissoes";
import { api } from "@/lib/api";
import { data, dataHora, opcoes, rotulo } from "@/lib/formato";
import type { FilaItem, NivelPrioridade, Pagina, Periodo, Preferencia, Referencia } from "@/lib/types";
import { ExigePermissao } from "@/components/AppShell";
import { Alerta, AreaTexto, BarraFiltros, Botao, CabecalhoPagina, Caixa, Cartao, Entrada, Selecao, Selo } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { Paginacao, Tabela } from "@/components/ui/Tabela";
import { useAvisos } from "@/components/ui/Aviso";
import { SeloPrioridade } from "@/components/Status";
import { SeletorPaciente } from "@/components/SeletorPaciente";

export default function FilaPage() {
  return (
    <ExigePermissao permissao={P.FILA_LER}>
      <Conteudo />
    </ExigePermissao>
  );
}

function Conteudo() {
  const { pode } = useAuth();
  const cad = useCadastros();
  const [f, setF] = useState({ especialidade_id: "", unidade_id: "", ativo: "true", disponivel: "", busca: "" });
  const [page, setPage] = useState(1);
  const buscaD = useDebounce(f.busca);
  const lista = useConsulta<Pagina<FilaItem>>("/fila-espera", { ...f, busca: buscaD, page, size: 20 });
  const [novo, setNovo] = useState(false);
  const [prefs, setPrefs] = useState<FilaItem | null>(null);
  const [remover, setRemover] = useState<FilaItem | null>(null);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setF({ ...f, [k]: e.target.value });
    setPage(1);
  };
  const escrever = pode(P.FILA_ESCREVER);

  return (
    <>
      <CabecalhoPagina
        titulo="Fila de espera"
        descricao="Pacientes aguardando vaga, com preferências de local e período para encaixe (RF09, RF10, HU03)."
        acoes={escrever && <Botao onClick={() => setNovo(true)}>Incluir na fila</Botao>}
      />
      <BarraFiltros>
        <Selecao rotulo="Especialidade" vazio="Todas" value={f.especialidade_id} onChange={set("especialidade_id")} opcoes={cad.especialidades.map((e) => ({ value: e.id, label: e.nome }))} />
        <Selecao rotulo="Unidade preferida" vazio="Todas" value={f.unidade_id} onChange={set("unidade_id")} opcoes={cad.unidades.map((u) => ({ value: u.id, label: u.nome }))} />
        <Selecao
          rotulo="Situação"
          vazio="Todas"
          value={f.ativo}
          onChange={set("ativo")}
          opcoes={[
            { value: "true", label: "Na fila" },
            { value: "false", label: "Fora da fila" },
          ]}
        />
        <Selecao
          rotulo="Encaixe"
          vazio="Todos"
          value={f.disponivel}
          onChange={set("disponivel")}
          opcoes={[
            { value: "true", label: "Disponível para encaixe" },
            { value: "false", label: "Indisponível" },
          ]}
        />
        <Entrada rotulo="Buscar paciente" value={f.busca} onChange={set("busca")} className="sm:col-span-2" />
      </BarraFiltros>

      {lista.erro && <Alerta>{lista.erro}</Alerta>}
      <Cartao>
        <Tabela
          itens={lista.dados?.itens}
          carregando={lista.carregando}
          chave={(i) => i.id}
          vazio="Fila vazia com esses filtros."
          colunas={[
            { titulo: "Entrada", render: (i) => dataHora(i.data_entrada) },
            { titulo: "Paciente", render: (i) => <span className="font-medium">{i.paciente.nome}</span> },
            { titulo: "Especialidade", render: (i) => i.especialidade.nome + (i.profissional ? ` · ${i.profissional.nome}` : "") },
            { titulo: "Prioridade", render: (i) => <SeloPrioridade nivel={i.prioridade} /> },
            {
              titulo: "Preferências",
              render: (i) =>
                i.disponivel_para_encaixe ? (
                  <ul className="space-y-0.5 text-xs">
                    {i.preferencias.map((p) => (
                      <li key={p.id}>
                        {cad.nomeUnidade(p.unidade_id) === "—" ? "Qualquer unidade" : cad.nomeUnidade(p.unidade_id)} · {rotulo("periodo", p.periodo)}
                        {p.data_desejada ? ` · ${data(p.data_desejada)}` : ""}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Selo cor="cinza">Indisponível para encaixe</Selo>
                ),
            },
            {
              titulo: "Situação",
              render: (i) => (i.ativo ? <Selo cor="verde">Na fila</Selo> : <Selo title={i.motivo_saida ?? ""}>Saiu {data(i.data_saida)}</Selo>),
            },
            {
              titulo: "",
              className: "text-right",
              render: (i) =>
                escrever && i.ativo ? (
                  <div className="flex justify-end gap-1">
                    <Botao variante="fantasma" tamanho="sm" onClick={() => setPrefs(i)}>
                      Preferências
                    </Botao>
                    <Botao variante="fantasma" tamanho="sm" onClick={() => setRemover(i)}>
                      Retirar
                    </Botao>
                  </div>
                ) : null,
            },
          ]}
        />
        {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
      </Cartao>

      <NovoItem
        aberto={novo}
        cad={cad}
        onFechar={() => setNovo(false)}
        onSalvo={() => {
          setNovo(false);
          void lista.recarregar();
        }}
      />
      <EditarPreferencias
        item={prefs}
        cad={cad}
        onFechar={() => setPrefs(null)}
        onSalvo={() => {
          setPrefs(null);
          void lista.recarregar();
        }}
      />
      <RemoverItem
        item={remover}
        onFechar={() => setRemover(null)}
        onSalvo={() => {
          setRemover(null);
          void lista.recarregar();
        }}
      />
    </>
  );
}

type Cad = ReturnType<typeof useCadastros>;

function EditorPreferencias({ valor, onChange, cad }: { valor: Preferencia[]; onChange: (v: Preferencia[]) => void; cad: Cad }) {
  const atualizar = (i: number, p: Partial<Preferencia>) => onChange(valor.map((v, j) => (j === i ? { ...v, ...p } : v)));
  return (
    <fieldset className="space-y-2">
      <legend className="mb-1 text-sm font-medium text-slate-700">Preferências para encaixe</legend>
      {valor.map((p, i) => (
        <div key={i} className="grid grid-cols-[1fr_1fr_1fr_auto] items-end gap-2 rounded-lg border border-slate-200 p-2">
          <Selecao
            rotulo="Unidade"
            vazio="Qualquer"
            value={p.unidade_id ?? ""}
            onChange={(e) => atualizar(i, { unidade_id: e.target.value ? Number(e.target.value) : null })}
            opcoes={cad.unidades.map((u) => ({ value: u.id, label: u.nome }))}
          />
          <Selecao rotulo="Período" value={p.periodo ?? "QUALQUER"} onChange={(e) => atualizar(i, { periodo: e.target.value as Periodo })} opcoes={opcoes("periodo")} />
          <Entrada rotulo="Data (opcional)" type="date" value={p.data_desejada ?? ""} onChange={(e) => atualizar(i, { data_desejada: e.target.value || null })} />
          <Botao variante="fantasma" tamanho="sm" aria-label="Remover preferência" onClick={() => onChange(valor.filter((_, j) => j !== i))}>
            ×
          </Botao>
        </div>
      ))}
      <Botao variante="secundario" tamanho="sm" onClick={() => onChange([...valor, { unidade_id: null, periodo: "QUALQUER", data_desejada: null }])}>
        + Adicionar preferência
      </Botao>
    </fieldset>
  );
}

const semId = (ps: Preferencia[]) => ps.map((p) => ({ unidade_id: p.unidade_id ?? null, periodo: p.periodo ?? "QUALQUER", data_desejada: p.data_desejada || null }));

function NovoItem({ aberto, cad, onFechar, onSalvo }: { aberto: boolean; cad: Cad; onFechar: () => void; onSalvo: () => void }) {
  const avisar = useAvisos();
  const [paciente, setPaciente] = useState<Referencia | null>(null);
  const [form, setForm] = useState({ especialidade_id: "", profissional_id: "", prioridade: "", disponivel_para_encaixe: true, observacao: "" });
  const [prefs, setPrefs] = useState<Preferencia[]>([{ unidade_id: null, periodo: "QUALQUER", data_desejada: null }]);
  const salvar = useAcao(async () => {
    if (!paciente) throw new Error("Selecione o paciente.");
    await api.post("/fila-espera", {
      paciente_id: paciente.id,
      especialidade_id: Number(form.especialidade_id),
      profissional_id: form.profissional_id ? Number(form.profissional_id) : null,
      prioridade: (form.prioridade || null) as NivelPrioridade | null,
      disponivel_para_encaixe: form.disponivel_para_encaixe,
      observacao: form.observacao || null,
      preferencias: form.disponivel_para_encaixe ? semId(prefs) : [],
    });
    avisar("Paciente incluído na fila de espera.");
    setPaciente(null);
    onSalvo();
  });
  const profs = cad.profissionais.filter((p) => !form.especialidade_id || p.especialidades.some((e) => String(e.id) === form.especialidade_id));

  return (
    <Modal
      aberto={aberto}
      titulo="Incluir na fila de espera"
      onFechar={onFechar}
      largura="lg"
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-fila" carregando={salvar.executando}>
            Incluir
          </Botao>
        </>
      }
    >
      {salvar.erro && <Alerta onFechar={salvar.limparErro}>{salvar.erro}</Alerta>}
      <form
        id="form-fila"
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void salvar.executar();
        }}
      >
        <SeletorPaciente valor={paciente} onChange={setPaciente} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Selecao
            rotulo="Especialidade"
            required
            vazio="Selecione…"
            value={form.especialidade_id}
            onChange={(e) => setForm({ ...form, especialidade_id: e.target.value, profissional_id: "" })}
            opcoes={cad.especialidades.map((e) => ({ value: e.id, label: e.nome }))}
          />
          <Selecao
            rotulo="Profissional desejado"
            vazio="Qualquer"
            value={form.profissional_id}
            onChange={(e) => setForm({ ...form, profissional_id: e.target.value })}
            opcoes={profs.map((p) => ({ value: p.id, label: p.nome }))}
          />
          <Selecao
            rotulo="Prioridade"
            vazio="Usar a do cadastro do paciente"
            value={form.prioridade}
            onChange={(e) => setForm({ ...form, prioridade: e.target.value })}
            opcoes={opcoes("prioridade")}
          />
        </div>
        <Caixa
          rotulo="Disponível para encaixe"
          ajuda="Se marcado, o paciente pode receber ofertas de vagas liberadas."
          checked={form.disponivel_para_encaixe}
          onChange={(e) => setForm({ ...form, disponivel_para_encaixe: e.target.checked })}
        />
        {form.disponivel_para_encaixe && <EditorPreferencias valor={prefs} onChange={setPrefs} cad={cad} />}
        <AreaTexto rotulo="Observação" maxLength={200} value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} />
      </form>
    </Modal>
  );
}

function EditarPreferencias({ item, cad, onFechar, onSalvo }: { item: FilaItem | null; cad: Cad; onFechar: () => void; onSalvo: () => void }) {
  const avisar = useAvisos();
  const [disp, setDisp] = useState(true);
  const [prefs, setPrefs] = useState<Preferencia[]>([]);
  const [chave, setChave] = useState<FilaItem | null>(null);
  if (item !== chave) {
    setChave(item);
    setDisp(item?.disponivel_para_encaixe ?? true);
    setPrefs(item?.preferencias ?? []);
  }
  const salvar = useAcao(async () => {
    if (!item) return;
    await api.put(`/fila-espera/${item.id}/preferencias`, { disponivel_para_encaixe: disp, preferencias: disp ? semId(prefs) : [] });
    avisar("Preferências atualizadas.");
    onSalvo();
  });
  return (
    <Modal
      aberto={item !== null}
      titulo={`Preferências de ${item?.paciente.nome ?? ""}`}
      onFechar={onFechar}
      largura="lg"
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar}>
            Cancelar
          </Botao>
          <Botao carregando={salvar.executando} onClick={() => salvar.executar()}>
            Salvar
          </Botao>
        </>
      }
    >
      {salvar.erro && <Alerta onFechar={salvar.limparErro}>{salvar.erro}</Alerta>}
      <div className="space-y-4">
        <Caixa rotulo="Disponível para encaixe" checked={disp} onChange={(e) => setDisp(e.target.checked)} />
        {disp && <EditorPreferencias valor={prefs} onChange={setPrefs} cad={cad} />}
      </div>
    </Modal>
  );
}

function RemoverItem({ item, onFechar, onSalvo }: { item: FilaItem | null; onFechar: () => void; onSalvo: () => void }) {
  const avisar = useAvisos();
  const [motivo, setMotivo] = useState("");
  const salvar = useAcao(async () => {
    if (!item) return;
    await api.patch(`/fila-espera/${item.id}/remover`, null, { params: { motivo } });
    avisar("Paciente retirado da fila.");
    setMotivo("");
    onSalvo();
  });
  return (
    <Modal
      aberto={item !== null}
      titulo="Retirar da fila de espera"
      onFechar={onFechar}
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar}>
            Cancelar
          </Botao>
          <Botao variante="perigo" carregando={salvar.executando} onClick={() => salvar.executar()}>
            Retirar
          </Botao>
        </>
      }
    >
      {salvar.erro && <Alerta onFechar={salvar.limparErro}>{salvar.erro}</Alerta>}
      <p className="mb-3 text-sm text-slate-600">
        Retirar <strong>{item?.paciente.nome}</strong> da fila de {item?.especialidade.nome}?
      </p>
      <Entrada rotulo="Motivo" placeholder="Ex.: consulta já realizada" maxLength={80} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
    </Modal>
  );
}
