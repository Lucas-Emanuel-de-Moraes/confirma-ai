import { percentual, rotulo } from "@/lib/formato";
import type { Indicadores } from "@/lib/types";
import { cx } from "./ui";

export function CartaoNumero({ titulo, valor, detalhe, destaque }: { titulo: string; valor: React.ReactNode; detalhe?: string; destaque?: boolean }) {
  return (
    <div className={cx("rounded-xl border p-4 shadow-sm", destaque ? "border-marca-200 bg-marca-50" : "border-slate-200 bg-white")}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{titulo}</p>
      <p className={cx("mt-1 text-2xl font-bold", destaque ? "text-marca-700" : "text-slate-900")}>{valor}</p>
      {detalhe && <p className="mt-0.5 text-xs text-slate-500">{detalhe}</p>}
    </div>
  );
}

export function Taxas({ dados }: { dados: Indicadores }) {
  const t = dados.taxas;
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <CartaoNumero destaque titulo="Taxa de confirmação" valor={percentual(t.taxa_confirmacao)} detalhe="Respostas SIM / agendamentos" />
      <CartaoNumero destaque titulo="Absenteísmo" valor={percentual(t.taxa_absenteismo)} detalhe="Faltas / (realizados + faltas)" />
      <CartaoNumero destaque titulo="Recuperação de vagas" valor={percentual(t.taxa_recuperacao)} detalhe="Vagas preenchidas / liberadas" />
      <CartaoNumero destaque titulo="Ocupação" valor={percentual(t.taxa_ocupacao)} detalhe="Horários ocupados ao final" />
    </div>
  );
}

/** Barras horizontais simples em CSS (sem biblioteca de gráficos). */
export function Barras({ titulo, valores, grupo }: { titulo: string; valores: Record<string, number>; grupo: string }) {
  const max = Math.max(1, ...Object.values(valores));
  return (
    <figure>
      <figcaption className="mb-3 text-sm font-semibold text-slate-800">{titulo}</figcaption>
      <ul className="space-y-2">
        {Object.entries(valores).map(([chave, v]) => (
          <li key={chave} className="grid grid-cols-[10rem_1fr_2.5rem] items-center gap-2 text-xs">
            <span className="truncate text-slate-600">{rotulo(grupo, chave)}</span>
            <span className="h-3 overflow-hidden rounded-full bg-slate-100" aria-hidden>
              <span className="block h-full rounded-full bg-marca-500" style={{ width: `${(v / max) * 100}%` }} />
            </span>
            <span className="text-right font-medium tabular-nums text-slate-800">{v}</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}
