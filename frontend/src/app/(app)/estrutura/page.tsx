"use client";

import { useState } from "react";
import { useAcao, useConsulta } from "@/hooks/useApi";
import { useCadastros } from "@/hooks/useCadastros";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/permissoes";
import { api } from "@/lib/api";
import { DIAS_SEMANA, dataHora, hora, opcoes, paraApiDataHora, rotulo } from "@/lib/formato";
import type { Bloqueio, Especialidade, Horario, Pagina, Profissional, Unidade } from "@/lib/types";
import { ExigePermissao } from "@/components/AppShell";
import { Abas, Alerta, Botao, CabecalhoPagina, Caixa, Cartao, Entrada, MultiSelecao, Selecao } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { Paginacao, Tabela } from "@/components/ui/Tabela";
import { useAvisos } from "@/components/ui/Aviso";
import { SeloAtivo } from "@/components/Status";

type Aba = "unidades" | "especialidades" | "profissionais" | "bloqueios";

export default function EstruturaPage() {
  return (
    <ExigePermissao permissao={P.ESTRUTURA_LER}>
      <Conteudo />
    </ExigePermissao>
  );
}

function Conteudo() {
  const [aba, setAba] = useState<Aba>("unidades");
  const cad = useCadastros();
  return (
    <>
      <CabecalhoPagina titulo="Unidades e profissionais" descricao="Estrutura de atendimento: unidades, especialidades, profissionais, horários e bloqueios (UC01)." />
      <Abas
        abas={[
          { id: "unidades", rotulo: "Unidades" },
          { id: "especialidades", rotulo: "Especialidades" },
          { id: "profissionais", rotulo: "Profissionais" },
          { id: "bloqueios", rotulo: "Bloqueios de agenda" },
        ]}
        ativa={aba}
        onChange={setAba}
      />
      {aba === "unidades" && <Unidades cad={cad} />}
      {aba === "especialidades" && <Especialidades onMudou={cad.recarregar} />}
      {aba === "profissionais" && <Profissionais cad={cad} />}
      {aba === "bloqueios" && <Bloqueios cad={cad} />}
    </>
  );
}

type Cad = ReturnType<typeof useCadastros>;

/* ------------------------------------------------------------------ Unidades */
function Unidades({ cad }: { cad: Cad }) {
  const { pode } = useAuth();
  const [page, setPage] = useState(1);
  const lista = useConsulta<Pagina<Unidade>>("/unidades", { page, size: 20 });
  const [alvo, setAlvo] = useState<Unidade | "nova" | null>(null);
  return (
    <Cartao titulo="Unidades de saúde" acoes={pode(P.ESTRUTURA_ESCREVER) && <Botao tamanho="sm" onClick={() => setAlvo("nova")}>Nova unidade</Botao>}>
      {lista.erro && <Alerta>{lista.erro}</Alerta>}
      <Tabela
        itens={lista.dados?.itens}
        carregando={lista.carregando}
        chave={(u) => u.id}
        onLinha={pode(P.ESTRUTURA_ESCREVER) ? setAlvo : undefined}
        colunas={[
          { titulo: "Nome", render: (u) => <span className="font-medium">{u.nome}</span> },
          { titulo: "Endereço", render: (u) => u.endereco ?? "—" },
          { titulo: "Especialidades", render: (u) => u.especialidades.map((e) => e.nome).join(", ") || "—" },
          { titulo: "Regras", render: (u) => <span className="text-xs">{u.exige_profissional_especifico ? "Exige profissional específico" : u.permite_profissional_equivalente ? "Aceita equivalente" : "—"}</span> },
          { titulo: "Situação", render: (u) => <SeloAtivo ativo={u.ativo} /> },
        ]}
      />
      {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
      <FormUnidade
        alvo={alvo}
        especialidades={cad.especialidades}
        onFechar={() => setAlvo(null)}
        onSalvo={() => {
          setAlvo(null);
          void lista.recarregar();
          void cad.recarregar();
        }}
      />
    </Cartao>
  );
}

function FormUnidade({ alvo, especialidades, onFechar, onSalvo }: { alvo: Unidade | "nova" | null; especialidades: Especialidade[]; onFechar: () => void; onSalvo: () => void }) {
  const avisar = useAvisos();
  const u = alvo && alvo !== "nova" ? alvo : null;
  const vazio = { nome: "", endereco: "", exige_profissional_especifico: false, permite_profissional_equivalente: true, especialidade_ids: [] as number[], ativo: true };
  const [form, setForm] = useState(vazio);
  const [chave, setChave] = useState<unknown>(null);
  if (alvo !== chave) {
    setChave(alvo);
    setForm(
      u
        ? {
            nome: u.nome,
            endereco: u.endereco ?? "",
            exige_profissional_especifico: u.exige_profissional_especifico,
            permite_profissional_equivalente: u.permite_profissional_equivalente,
            especialidade_ids: u.especialidades.map((e) => e.id),
            ativo: u.ativo,
          }
        : vazio,
    );
  }
  const salvar = useAcao(async () => {
    const corpo = { ...form, endereco: form.endereco || null };
    if (u) await api.put(`/unidades/${u.id}`, corpo);
    else await api.post("/unidades", corpo);
    avisar(u ? "Unidade atualizada." : "Unidade cadastrada.");
    onSalvo();
  });
  return (
    <Modal
      aberto={alvo !== null}
      titulo={u ? "Editar unidade" : "Nova unidade"}
      onFechar={onFechar}
      rodape={<Rodape onFechar={onFechar} form="form-unidade" carregando={salvar.executando} />}
    >
      {salvar.erro && <Alerta onFechar={salvar.limparErro}>{salvar.erro}</Alerta>}
      <form id="form-unidade" className="space-y-4" onSubmit={(e) => (e.preventDefault(), void salvar.executar())}>
        <Entrada rotulo="Nome" required minLength={2} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        <Entrada rotulo="Endereço" value={form.endereco} onChange={(e) => setForm({ ...form, endereco: e.target.value })} />
        <MultiSelecao
          rotulo="Especialidades atendidas"
          opcoes={especialidades.map((e) => ({ value: e.id, label: e.nome }))}
          valor={form.especialidade_ids}
          onChange={(v) => setForm({ ...form, especialidade_ids: v })}
        />
        <Caixa
          rotulo="Exige profissional específico no encaixe"
          checked={form.exige_profissional_especifico}
          onChange={(e) => setForm({ ...form, exige_profissional_especifico: e.target.checked })}
        />
        <Caixa
          rotulo="Permite profissional equivalente (mesma especialidade)"
          checked={form.permite_profissional_equivalente}
          onChange={(e) => setForm({ ...form, permite_profissional_equivalente: e.target.checked })}
        />
        {u && <Caixa rotulo="Unidade ativa" checked={form.ativo} onChange={(e) => setForm({ ...form, ativo: e.target.checked })} />}
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------ Especialidades */
function Especialidades({ onMudou }: { onMudou: () => void }) {
  const { pode } = useAuth();
  const avisar = useAvisos();
  const [page, setPage] = useState(1);
  const lista = useConsulta<Pagina<Especialidade>>("/especialidades", { page, size: 20 });
  const [nome, setNome] = useState("");
  const criar = useAcao(async () => {
    await api.post("/especialidades", { nome });
    avisar("Especialidade cadastrada.");
    setNome("");
    void lista.recarregar();
    onMudou();
  });
  const alternar = useAcao(async (e: Especialidade) => {
    await api.put(`/especialidades/${e.id}`, { ativo: !e.ativo });
    void lista.recarregar();
    onMudou();
  });
  const escrever = pode(P.ESTRUTURA_ESCREVER);
  return (
    <Cartao titulo="Especialidades">
      {(criar.erro || alternar.erro) && <Alerta onFechar={() => (criar.limparErro(), alternar.limparErro())}>{criar.erro ?? alternar.erro}</Alerta>}
      {escrever && (
        <form className="mb-4 flex flex-wrap items-end gap-2" onSubmit={(e) => (e.preventDefault(), void criar.executar())}>
          <Entrada rotulo="Nova especialidade" required minLength={2} value={nome} onChange={(e) => setNome(e.target.value)} className="min-w-64 flex-1" />
          <Botao type="submit" carregando={criar.executando}>
            Adicionar
          </Botao>
        </form>
      )}
      <Tabela
        itens={lista.dados?.itens}
        carregando={lista.carregando}
        chave={(e) => e.id}
        colunas={[
          { titulo: "Nome", render: (e) => <span className="font-medium">{e.nome}</span> },
          { titulo: "Situação", render: (e) => <SeloAtivo ativo={e.ativo} /> },
          {
            titulo: "",
            className: "text-right",
            render: (e) =>
              escrever && (
                <Botao variante="fantasma" tamanho="sm" onClick={() => alternar.executar(e)}>
                  {e.ativo ? "Inativar" : "Reativar"}
                </Botao>
              ),
          },
        ]}
      />
      {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
    </Cartao>
  );
}

/* ------------------------------------------------------------------ Profissionais */
function Profissionais({ cad }: { cad: Cad }) {
  const { pode } = useAuth();
  const [page, setPage] = useState(1);
  const lista = useConsulta<Pagina<Profissional>>("/profissionais", { page, size: 20 });
  const [alvo, setAlvo] = useState<Profissional | "novo" | null>(null);
  const [horarios, setHorarios] = useState<Profissional | null>(null);
  const escrever = pode(P.ESTRUTURA_ESCREVER);
  return (
    <Cartao titulo="Profissionais" acoes={escrever && <Botao tamanho="sm" onClick={() => setAlvo("novo")}>Novo profissional</Botao>}>
      {lista.erro && <Alerta>{lista.erro}</Alerta>}
      <Tabela
        itens={lista.dados?.itens}
        carregando={lista.carregando}
        chave={(p) => p.id}
        colunas={[
          { titulo: "Nome", render: (p) => <span className="font-medium">{p.nome}</span> },
          { titulo: "Registro", render: (p) => p.registro_conselho },
          { titulo: "Especialidades", render: (p) => p.especialidades.map((e) => e.nome).join(", ") },
          { titulo: "Unidades", render: (p) => p.unidades.map((u) => u.nome).join(", ") },
          { titulo: "Situação", render: (p) => <SeloAtivo ativo={p.ativo} /> },
          {
            titulo: "",
            className: "text-right",
            render: (p) => (
              <div className="flex justify-end gap-1">
                <Botao variante="fantasma" tamanho="sm" onClick={() => setHorarios(p)}>
                  Horários
                </Botao>
                {escrever && (
                  <Botao variante="fantasma" tamanho="sm" onClick={() => setAlvo(p)}>
                    Editar
                  </Botao>
                )}
              </div>
            ),
          },
        ]}
      />
      {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
      <FormProfissional
        alvo={alvo}
        cad={cad}
        onFechar={() => setAlvo(null)}
        onSalvo={() => {
          setAlvo(null);
          void lista.recarregar();
          void cad.recarregar();
        }}
      />
      <Horarios profissional={horarios} cad={cad} onFechar={() => setHorarios(null)} />
    </Cartao>
  );
}

function FormProfissional({ alvo, cad, onFechar, onSalvo }: { alvo: Profissional | "novo" | null; cad: Cad; onFechar: () => void; onSalvo: () => void }) {
  const avisar = useAvisos();
  const p = alvo && alvo !== "novo" ? alvo : null;
  const vazio = { nome: "", registro_conselho: "", especialidade_ids: [] as number[], unidade_ids: [] as number[] };
  const [form, setForm] = useState(vazio);
  const [chave, setChave] = useState<unknown>(null);
  if (alvo !== chave) {
    setChave(alvo);
    setForm(p ? { nome: p.nome, registro_conselho: p.registro_conselho, especialidade_ids: p.especialidades.map((e) => e.id), unidade_ids: p.unidades.map((u) => u.id) } : vazio);
  }
  const salvar = useAcao(async () => {
    if (!form.especialidade_ids.length || !form.unidade_ids.length) throw new Error("Selecione ao menos uma especialidade e uma unidade.");
    if (p) await api.put(`/profissionais/${p.id}`, form);
    else await api.post("/profissionais", form);
    avisar(p ? "Profissional atualizado." : "Profissional cadastrado.");
    onSalvo();
  });
  const inativar = useAcao(async () => {
    if (!p) return;
    await api.patch(`/profissionais/${p.id}/inativar`);
    avisar("Profissional inativado.");
    onSalvo();
  });
  return (
    <Modal
      aberto={alvo !== null}
      titulo={p ? "Editar profissional" : "Novo profissional"}
      onFechar={onFechar}
      rodape={
        <>
          {p?.ativo && (
            <Botao variante="perigo" className="mr-auto" carregando={inativar.executando} onClick={() => inativar.executar()}>
              Inativar
            </Botao>
          )}
          <Rodape onFechar={onFechar} form="form-profissional" carregando={salvar.executando} />
        </>
      }
    >
      {(salvar.erro || inativar.erro) && <Alerta onFechar={salvar.limparErro}>{salvar.erro ?? inativar.erro}</Alerta>}
      <form id="form-profissional" className="space-y-4" onSubmit={(e) => (e.preventDefault(), void salvar.executar())}>
        <Entrada rotulo="Nome" required minLength={3} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        <Entrada
          rotulo="Registro no conselho"
          required
          minLength={3}
          placeholder="CRM-MT 12345"
          value={form.registro_conselho}
          onChange={(e) => setForm({ ...form, registro_conselho: e.target.value })}
        />
        <MultiSelecao
          rotulo="Especialidades"
          opcoes={cad.especialidades.map((e) => ({ value: e.id, label: e.nome }))}
          valor={form.especialidade_ids}
          onChange={(v) => setForm({ ...form, especialidade_ids: v })}
        />
        <MultiSelecao
          rotulo="Unidades"
          opcoes={cad.unidades.map((u) => ({ value: u.id, label: u.nome }))}
          valor={form.unidade_ids}
          onChange={(v) => setForm({ ...form, unidade_ids: v })}
        />
      </form>
    </Modal>
  );
}

function Horarios({ profissional, cad, onFechar }: { profissional: Profissional | null; cad: Cad; onFechar: () => void }) {
  const { pode } = useAuth();
  const avisar = useAvisos();
  const lista = useConsulta<Horario[]>(profissional ? `/profissionais/${profissional.id}/horarios` : null);
  const [form, setForm] = useState({ unidade_id: "", dia_semana: "0", hora_inicio: "08:00", hora_fim: "12:00", duracao_consulta_min: "30" });
  const criar = useAcao(async () => {
    if (!profissional) return;
    await api.post(`/profissionais/${profissional.id}/horarios`, {
      unidade_id: Number(form.unidade_id),
      dia_semana: Number(form.dia_semana),
      hora_inicio: form.hora_inicio,
      hora_fim: form.hora_fim,
      duracao_consulta_min: Number(form.duracao_consulta_min),
    });
    avisar("Horário adicionado.");
    void lista.recarregar();
  });
  const remover = useAcao(async (h: Horario) => {
    await api.delete(`/horarios/${h.id}`);
    void lista.recarregar();
  });
  const unidades = profissional?.unidades ?? [];
  return (
    <Modal aberto={profissional !== null} titulo={`Horários de ${profissional?.nome ?? ""}`} onFechar={onFechar} largura="lg">
      {(criar.erro || remover.erro) && <Alerta onFechar={() => (criar.limparErro(), remover.limparErro())}>{criar.erro ?? remover.erro}</Alerta>}
      <Tabela
        itens={lista.dados ?? undefined}
        carregando={lista.carregando}
        chave={(h) => h.id}
        vazio="Nenhum horário de atendimento cadastrado."
        colunas={[
          { titulo: "Dia", render: (h) => DIAS_SEMANA[h.dia_semana] },
          { titulo: "Horário", render: (h) => `${hora(h.hora_inicio)} – ${hora(h.hora_fim)}` },
          { titulo: "Duração", render: (h) => `${h.duracao_consulta_min} min` },
          { titulo: "Unidade", render: (h) => cad.nomeUnidade(h.unidade_id) },
          {
            titulo: "",
            className: "text-right",
            render: (h) =>
              pode(P.ESTRUTURA_ESCREVER) && (
                <Botao variante="fantasma" tamanho="sm" onClick={() => remover.executar(h)}>
                  Remover
                </Botao>
              ),
          },
        ]}
      />
      {pode(P.ESTRUTURA_ESCREVER) && (
        <form className="mt-4 grid grid-cols-2 gap-3 rounded-lg border border-slate-200 p-3 sm:grid-cols-3" onSubmit={(e) => (e.preventDefault(), void criar.executar())}>
          <Selecao
            rotulo="Unidade"
            required
            vazio="Selecione…"
            value={form.unidade_id}
            onChange={(e) => setForm({ ...form, unidade_id: e.target.value })}
            opcoes={unidades.map((u) => ({ value: u.id, label: u.nome }))}
          />
          <Selecao rotulo="Dia da semana" value={form.dia_semana} onChange={(e) => setForm({ ...form, dia_semana: e.target.value })} opcoes={DIAS_SEMANA.map((d, i) => ({ value: i, label: d }))} />
          <Entrada rotulo="Duração (min)" type="number" min={5} max={240} value={form.duracao_consulta_min} onChange={(e) => setForm({ ...form, duracao_consulta_min: e.target.value })} />
          <Entrada rotulo="Início" type="time" required value={form.hora_inicio} onChange={(e) => setForm({ ...form, hora_inicio: e.target.value })} />
          <Entrada rotulo="Fim" type="time" required value={form.hora_fim} onChange={(e) => setForm({ ...form, hora_fim: e.target.value })} />
          <div className="flex items-end">
            <Botao type="submit" className="w-full" carregando={criar.executando}>
              Adicionar horário
            </Botao>
          </div>
        </form>
      )}
    </Modal>
  );
}

/* ------------------------------------------------------------------ Bloqueios */
function Bloqueios({ cad }: { cad: Cad }) {
  const { pode } = useAuth();
  const avisar = useAvisos();
  const [page, setPage] = useState(1);
  const lista = useConsulta<Pagina<Bloqueio>>("/bloqueios", { page, size: 20 });
  const [form, setForm] = useState({ unidade_id: "", profissional_id: "", inicio: "", fim: "", tipo: "FERIADO", motivo: "" });
  const criar = useAcao(async () => {
    await api.post("/bloqueios", {
      unidade_id: form.unidade_id ? Number(form.unidade_id) : null,
      profissional_id: form.profissional_id ? Number(form.profissional_id) : null,
      inicio: paraApiDataHora(form.inicio),
      fim: paraApiDataHora(form.fim),
      tipo: form.tipo,
      motivo: form.motivo || null,
    });
    avisar("Bloqueio registrado.");
    setForm({ ...form, inicio: "", fim: "", motivo: "" });
    void lista.recarregar();
  });
  const remover = useAcao(async (b: Bloqueio) => {
    await api.delete(`/bloqueios/${b.id}`);
    void lista.recarregar();
  });
  return (
    <Cartao titulo="Bloqueios de agenda (feriados e indisponibilidades)">
      {(criar.erro || remover.erro) && <Alerta onFechar={() => (criar.limparErro(), remover.limparErro())}>{criar.erro ?? remover.erro}</Alerta>}
      {pode(P.ESTRUTURA_ESCREVER) && (
        <form className="mb-4 grid grid-cols-1 gap-3 rounded-lg border border-slate-200 p-3 sm:grid-cols-3" onSubmit={(e) => (e.preventDefault(), void criar.executar())}>
          <Selecao rotulo="Unidade" vazio="Todas" value={form.unidade_id} onChange={(e) => setForm({ ...form, unidade_id: e.target.value })} opcoes={cad.unidades.map((u) => ({ value: u.id, label: u.nome }))} />
          <Selecao
            rotulo="Profissional"
            vazio="Todos"
            value={form.profissional_id}
            onChange={(e) => setForm({ ...form, profissional_id: e.target.value })}
            opcoes={cad.profissionais.map((p) => ({ value: p.id, label: p.nome }))}
          />
          <Selecao rotulo="Tipo" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })} opcoes={opcoes("tipoBloqueio")} />
          <Entrada rotulo="Início" type="datetime-local" required value={form.inicio} onChange={(e) => setForm({ ...form, inicio: e.target.value })} />
          <Entrada rotulo="Fim" type="datetime-local" required value={form.fim} onChange={(e) => setForm({ ...form, fim: e.target.value })} />
          <Entrada rotulo="Motivo" value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })} />
          <div className="sm:col-span-3">
            <Botao type="submit" carregando={criar.executando}>
              Registrar bloqueio
            </Botao>
          </div>
        </form>
      )}
      <Tabela
        itens={lista.dados?.itens}
        carregando={lista.carregando}
        chave={(b) => b.id}
        vazio="Nenhum bloqueio cadastrado."
        colunas={[
          { titulo: "Período", render: (b) => `${dataHora(b.inicio)} – ${dataHora(b.fim)}` },
          { titulo: "Tipo", render: (b) => rotulo("tipoBloqueio", b.tipo) },
          { titulo: "Unidade", render: (b) => (b.unidade_id ? cad.nomeUnidade(b.unidade_id) : "Todas") },
          { titulo: "Profissional", render: (b) => (b.profissional_id ? cad.nomeProfissional(b.profissional_id) : "Todos") },
          { titulo: "Motivo", render: (b) => b.motivo ?? "—" },
          {
            titulo: "",
            className: "text-right",
            render: (b) =>
              pode(P.ESTRUTURA_ESCREVER) && (
                <Botao variante="fantasma" tamanho="sm" onClick={() => remover.executar(b)}>
                  Remover
                </Botao>
              ),
          },
        ]}
      />
      {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
    </Cartao>
  );
}

function Rodape({ onFechar, form, carregando }: { onFechar: () => void; form: string; carregando: boolean }) {
  return (
    <>
      <Botao variante="secundario" onClick={onFechar}>
        Cancelar
      </Botao>
      <Botao type="submit" form={form} carregando={carregando}>
        Salvar
      </Botao>
    </>
  );
}
