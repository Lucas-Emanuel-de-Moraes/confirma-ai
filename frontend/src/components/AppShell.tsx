"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { P, type Permissao } from "@/lib/permissoes";
import { rotulo } from "@/lib/formato";
import { Carregando, cx } from "./ui";

interface ItemMenu {
  href: string;
  rotulo: string;
  permissao?: Permissao;
}

const GRUPOS: { titulo: string; itens: ItemMenu[] }[] = [
  {
    titulo: "Operação",
    itens: [
      { href: "/", rotulo: "Painel" },
      { href: "/agenda", rotulo: "Agenda", permissao: P.AGENDA_LER },
      { href: "/remarcacoes", rotulo: "Remarcações", permissao: P.AGENDA_LER },
      { href: "/fila", rotulo: "Fila de espera", permissao: P.FILA_LER },
      { href: "/vagas", rotulo: "Vagas e ofertas", permissao: P.OFERTAS_LER },
    ],
  },
  {
    titulo: "Cadastros",
    itens: [
      { href: "/pacientes", rotulo: "Pacientes", permissao: P.PACIENTES_LER },
      { href: "/estrutura", rotulo: "Unidades e profissionais", permissao: P.ESTRUTURA_LER },
      { href: "/parametros", rotulo: "Parâmetros", permissao: P.PARAMETROS_LER },
    ],
  },
  {
    titulo: "Gestão",
    itens: [
      { href: "/indicadores", rotulo: "Indicadores", permissao: P.INDICADORES_LER },
      { href: "/lgpd", rotulo: "LGPD", permissao: P.TITULAR_GERENCIAR },
      { href: "/usuarios", rotulo: "Usuários", permissao: P.USUARIOS },
      { href: "/auditoria", rotulo: "Auditoria", permissao: P.AUDITORIA_LER },
      { href: "/simulador", rotulo: "Simulador de mensagens", permissao: P.TAREFAS_EXECUTAR },
    ],
  },
];

/** Layout autenticado: menu lateral filtrado por perfil e guarda de rota. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { usuario, carregando, sair, pode } = useAuth();
  const router = useRouter();
  const caminho = usePathname();
  const [menuAberto, setMenuAberto] = useState(false);

  useEffect(() => {
    if (!carregando && !usuario) router.replace("/login");
  }, [carregando, usuario, router]);

  // Fecha o menu móvel ao navegar (ajuste de estado durante a renderização)
  const [caminhoAnterior, setCaminhoAnterior] = useState(caminho);
  if (caminho !== caminhoAnterior) {
    setCaminhoAnterior(caminho);
    setMenuAberto(false);
  }

  if (carregando || !usuario) {
    // A página continua sendo renderizada (oculta) para o Next validar a navegação instantânea.
    // Sem usuário, `pode()` é falso: ExigePermissao bloqueia o conteúdo e nenhuma consulta autenticada é feita.
    return (
      <>
        <div className="flex min-h-screen items-center justify-center">
          <Carregando texto="Verificando sessão…" />
        </div>
        <div hidden>{children}</div>
      </>
    );
  }

  const ativo = (href: string) => (href === "/" ? caminho === "/" : caminho.startsWith(href));

  const menu = (
    <nav aria-label="Menu principal" className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
      {GRUPOS.map((g) => {
        const itens = g.itens.filter((i) => !i.permissao || pode(i.permissao));
        if (!itens.length) return null;
        return (
          <div key={g.titulo}>
            <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wider text-marca-200/70">{g.titulo}</p>
            <ul className="space-y-0.5">
              {itens.map((i) => (
                <li key={i.href}>
                  <Link
                    href={i.href}
                    aria-current={ativo(i.href) ? "page" : undefined}
                    className={cx(
                      "block rounded-lg px-3 py-2 text-sm",
                      ativo(i.href) ? "bg-white/15 font-medium text-white" : "text-marca-100 hover:bg-white/10 hover:text-white",
                    )}
                  >
                    {i.rotulo}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </nav>
  );

  return (
    <div className="h-screen overflow-hidden lg:flex">
      <a href="#conteudo" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">
        Pular para o conteúdo
      </a>

      <aside
        className={cx(
          "fixed inset-y-0 left-0 z-40 flex h-screen w-64 shrink-0 flex-col bg-marca-900 transition-transform lg:static lg:translate-x-0",
          menuAberto ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center gap-2 px-6">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-marca-500 font-bold text-white">✓</span>
          <span className="text-lg font-bold text-white">Confirma Aí</span>
        </div>
        {menu}
        <div className="border-t border-white/10 p-4 text-sm">
          <p className="truncate font-medium text-white">{usuario.nome}</p>
          <p className="truncate text-xs text-marca-200">{usuario.perfis.map((p) => rotulo("perfil", p)).join(", ")}</p>
          <button onClick={sair} className="mt-3 w-full rounded-lg bg-white/10 px-3 py-1.5 text-sm text-white hover:bg-white/20">
            Sair
          </button>
        </div>
      </aside>

      {menuAberto && <div className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" onClick={() => setMenuAberto(false)} aria-hidden />}

      {/* Coluna de conteúdo: altura máxima da tela, com rolagem própria (a sidebar não rola junto) */}
      <div className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 lg:hidden">
          <button onClick={() => setMenuAberto(true)} aria-label="Abrir menu" className="rounded p-2 text-slate-600 hover:bg-slate-100">
            ☰
          </button>
          <span className="font-semibold text-marca-700">Confirma Aí</span>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <main id="conteudo" tabIndex={-1} className="mx-auto w-full max-w-7xl px-4 py-6 focus:outline-none sm:px-6 lg:px-8">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}

/** Mostra aviso quando o perfil não tem a permissão exigida pela página. */
export function ExigePermissao({ permissao, children }: { permissao: Permissao; children: React.ReactNode }) {
  const { pode } = useAuth();
  if (!pode(permissao)) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
        Seu perfil não tem acesso a esta área. Fale com o administrador se precisar dessa permissão.
      </div>
    );
  }
  return <>{children}</>;
}
