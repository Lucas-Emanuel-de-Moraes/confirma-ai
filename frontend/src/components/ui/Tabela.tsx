"use client";

import { Botao, Carregando, Vazio, cx } from "./index";

export interface Coluna<T> {
  titulo: string;
  render: (item: T) => React.ReactNode;
  className?: string;
}

interface TabelaProps<T> {
  colunas: Coluna<T>[];
  itens: T[] | undefined;
  chave: (item: T) => string | number;
  carregando?: boolean;
  vazio?: string;
  onLinha?: (item: T) => void;
  rotulo?: string;
}

export function Tabela<T>({ colunas, itens, chave, carregando, vazio = "Nenhum registro encontrado.", onLinha, rotulo }: TabelaProps<T>) {
  if (carregando && !itens?.length) return <Carregando />;
  if (!itens?.length) return <Vazio>{vazio}</Vazio>;
  return (
    <div className={cx("overflow-x-auto", carregando && "opacity-60")}>
      <table className="min-w-full divide-y divide-slate-200 text-sm" aria-label={rotulo}>
        <thead>
          <tr>
            {colunas.map((c) => (
              <th key={c.titulo} scope="col" className={cx("whitespace-nowrap px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500", c.className)}>
                {c.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {itens.map((item) => (
            <tr
              key={chave(item)}
              onClick={onLinha ? () => onLinha(item) : undefined}
              className={cx(onLinha && "cursor-pointer hover:bg-marca-50/60")}
            >
              {colunas.map((c) => (
                <td key={c.titulo} className={cx("px-3 py-2.5 align-middle text-slate-700", c.className)}>
                  {c.render(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Paginacao({ page, size, total, onPage }: { page: number; size: number; total: number; onPage: (p: number) => void }) {
  const paginas = Math.max(1, Math.ceil(total / size));
  if (total <= size) return total > 0 ? <p className="mt-3 text-xs text-slate-500">{total} registro(s)</p> : null;
  return (
    <nav aria-label="Paginação" className="mt-3 flex items-center justify-between text-xs text-slate-600">
      <span>
        {total} registro(s) · página {page} de {paginas}
      </span>
      <div className="flex gap-2">
        <Botao variante="secundario" tamanho="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Anterior
        </Botao>
        <Botao variante="secundario" tamanho="sm" disabled={page >= paginas} onClick={() => onPage(page + 1)}>
          Próxima
        </Botao>
      </div>
    </nav>
  );
}
