"use client";

import { useState } from "react";
import { useAcao, useConsulta, useDebounce } from "@/hooks/useApi";
import { useCadastros } from "@/hooks/useCadastros";
import { P } from "@/lib/permissoes";
import { api } from "@/lib/api";
import { dataHora, rotulo } from "@/lib/formato";
import type { Pagina, Perfil, PerfilSaida, Usuario } from "@/lib/types";
import { ExigePermissao } from "@/components/AppShell";
import { Alerta, BarraFiltros, Botao, CabecalhoPagina, Cartao, Entrada, Selecao, Selo } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { Paginacao, Tabela } from "@/components/ui/Tabela";
import { useAvisos } from "@/components/ui/Aviso";
import { SeloAtivo } from "@/components/Status";

export default function UsuariosPage() {
  return (
    <ExigePermissao permissao={P.USUARIOS}>
      <Conteudo />
    </ExigePermissao>
  );
}

function Conteudo() {
  const cad = useCadastros();
  const [busca, setBusca] = useState("");
  const [ativo, setAtivo] = useState("true");
  const [page, setPage] = useState(1);
  const buscaD = useDebounce(busca);
  const lista = useConsulta<Pagina<Usuario>>("/usuarios", { busca: buscaD, ativo, page, size: 20 });
  const perfis = useConsulta<PerfilSaida[]>("/usuarios/perfis");
  const [alvo, setAlvo] = useState<Usuario | "novo" | null>(null);

  return (
    <>
      <CabecalhoPagina titulo="Usuários e perfis" descricao="Acesso individual por perfil com menor privilégio (UC08)." acoes={<Botao onClick={() => setAlvo("novo")}>Novo usuário</Botao>} />
      <BarraFiltros>
        <Entrada rotulo="Buscar" placeholder="Nome ou login" value={busca} onChange={(e) => (setBusca(e.target.value), setPage(1))} className="sm:col-span-2" />
        <Selecao
          rotulo="Situação"
          vazio="Todos"
          value={ativo}
          onChange={(e) => (setAtivo(e.target.value), setPage(1))}
          opcoes={[
            { value: "true", label: "Ativos" },
            { value: "false", label: "Inativos" },
          ]}
        />
      </BarraFiltros>
      {lista.erro && <Alerta>{lista.erro}</Alerta>}
      <div className="grid gap-6 lg:grid-cols-3">
        <Cartao className="lg:col-span-2">
          <Tabela
            itens={lista.dados?.itens}
            carregando={lista.carregando}
            chave={(u) => u.id}
            onLinha={setAlvo}
            colunas={[
              { titulo: "Nome", render: (u) => <span className="font-medium">{u.nome}</span> },
              { titulo: "Login", render: (u) => <code className="text-xs">{u.login}</code> },
              {
                titulo: "Perfis",
                render: (u) => (
                  <div className="flex flex-wrap gap-1">
                    {u.perfis.map((p) => (
                      <Selo key={p} cor="azul">
                        {rotulo("perfil", p)}
                      </Selo>
                    ))}
                  </div>
                ),
              },
              { titulo: "Unidade", render: (u) => (u.unidade_id ? cad.nomeUnidade(u.unidade_id) : "Todas") },
              { titulo: "Situação", render: (u) => <SeloAtivo ativo={u.ativo} /> },
            ]}
          />
          {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
        </Cartao>
        <Cartao titulo="Perfis e permissões">
          <ul className="space-y-4 text-sm">
            {perfis.dados?.map((p) => (
              <li key={p.id}>
                <p className="font-medium text-slate-800">{rotulo("perfil", p.nome)}</p>
                <p className="mt-1 text-xs leading-relaxed text-slate-500">{p.permissoes.includes("*") ? "Todas as permissões" : p.permissoes.join(", ")}</p>
              </li>
            ))}
          </ul>
        </Cartao>
      </div>
      <FormUsuario
        alvo={alvo}
        perfis={perfis.dados?.map((p) => p.nome) ?? []}
        cad={cad}
        onFechar={() => setAlvo(null)}
        onSalvo={() => {
          setAlvo(null);
          void lista.recarregar();
        }}
      />
    </>
  );
}

function FormUsuario({
  alvo,
  perfis,
  cad,
  onFechar,
  onSalvo,
}: {
  alvo: Usuario | "novo" | null;
  perfis: Perfil[];
  cad: ReturnType<typeof useCadastros>;
  onFechar: () => void;
  onSalvo: () => void;
}) {
  const avisar = useAvisos();
  const u = alvo && alvo !== "novo" ? alvo : null;
  const [form, setForm] = useState({ nome: "", login: "", senha: "", perfis: [] as Perfil[], unidade_id: "" });
  const [chave, setChave] = useState<unknown>(null);
  if (alvo !== chave) {
    setChave(alvo);
    setForm({ nome: u?.nome ?? "", login: u?.login ?? "", senha: "", perfis: u?.perfis ?? [], unidade_id: u?.unidade_id ? String(u.unidade_id) : "" });
  }
  const salvar = useAcao(async () => {
    if (!form.perfis.length) throw new Error("Selecione ao menos um perfil.");
    const unidade_id = form.unidade_id ? Number(form.unidade_id) : null;
    if (u) {
      await api.put(`/usuarios/${u.id}`, { nome: form.nome, perfis: form.perfis, unidade_id, ...(form.senha ? { senha: form.senha } : {}) });
    } else {
      await api.post("/usuarios", { ...form, unidade_id });
    }
    avisar(u ? "Usuário atualizado." : "Usuário criado.");
    onSalvo();
  });
  const inativar = useAcao(async () => {
    if (!u) return;
    await api.patch(`/usuarios/${u.id}/inativar`);
    avisar("Usuário inativado.");
    onSalvo();
  });

  return (
    <Modal
      aberto={alvo !== null}
      titulo={u ? `Editar ${u.login}` : "Novo usuário"}
      onFechar={onFechar}
      rodape={
        <>
          {u?.ativo && (
            <Botao variante="perigo" className="mr-auto" carregando={inativar.executando} onClick={() => inativar.executar()}>
              Inativar
            </Botao>
          )}
          <Botao variante="secundario" onClick={onFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-usuario" carregando={salvar.executando}>
            Salvar
          </Botao>
        </>
      }
    >
      {(salvar.erro || inativar.erro) && <Alerta onFechar={salvar.limparErro}>{salvar.erro ?? inativar.erro}</Alerta>}
      {u && <p className="mb-3 text-xs text-slate-500">Criado em {dataHora(u.criado_em)}</p>}
      <form id="form-usuario" className="space-y-4" onSubmit={(e) => (e.preventDefault(), void salvar.executar())}>
        <Entrada rotulo="Nome" required minLength={3} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        <Entrada
          rotulo="Login"
          required
          minLength={3}
          pattern="[a-zA-Z0-9._\-]+"
          disabled={!!u}
          value={form.login}
          onChange={(e) => setForm({ ...form, login: e.target.value })}
          ajuda="Letras, números, ponto, hífen ou sublinhado."
        />
        <Entrada
          rotulo={u ? "Nova senha (opcional)" : "Senha"}
          type="password"
          autoComplete="new-password"
          required={!u}
          minLength={8}
          value={form.senha}
          onChange={(e) => setForm({ ...form, senha: e.target.value })}
          ajuda="Mínimo de 8 caracteres, combinando letras e números ou símbolos."
        />
        <fieldset>
          <legend className="mb-1 text-sm font-medium text-slate-700">Perfis</legend>
          <div className="flex flex-wrap gap-3">
            {perfis.map((p) => (
              <label key={p} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-marca-600"
                  checked={form.perfis.includes(p)}
                  onChange={(e) => setForm({ ...form, perfis: e.target.checked ? [...form.perfis, p] : form.perfis.filter((x) => x !== p) })}
                />
                {rotulo("perfil", p)}
              </label>
            ))}
          </div>
        </fieldset>
        <Selecao
          rotulo="Unidade de lotação"
          vazio="Todas (sem restrição)"
          value={form.unidade_id}
          onChange={(e) => setForm({ ...form, unidade_id: e.target.value })}
          opcoes={cad.unidades.map((x) => ({ value: x.id, label: x.nome }))}
          ajuda="Restringe a consulta de agenda e fila à unidade."
        />
      </form>
    </Modal>
  );
}
