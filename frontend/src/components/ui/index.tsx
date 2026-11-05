"use client";

import { forwardRef, useId } from "react";

export function cx(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ Botões */
type Variante = "primario" | "secundario" | "perigo" | "fantasma";
const VARIANTES: Record<Variante, string> = {
  primario: "bg-marca-600 text-white hover:bg-marca-700 disabled:bg-marca-600/50",
  secundario: "bg-white text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:text-slate-400",
  perigo: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-600/50",
  fantasma: "text-marca-700 hover:bg-marca-50 disabled:text-slate-400",
};

interface BotaoProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  tamanho?: "sm" | "md";
  carregando?: boolean;
}

export function Botao({ variante = "primario", tamanho = "md", carregando, className, children, disabled, ...rest }: BotaoProps) {
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled || carregando}
      aria-busy={carregando || undefined}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed",
        tamanho === "sm" ? "px-2.5 py-1.5 text-xs" : "px-4 py-2 text-sm",
        VARIANTES[variante],
        className,
      )}
    >
      {carregando && <Spinner />}
      {children}
    </button>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cx("inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent", className)}
    />
  );
}

/* ------------------------------------------------------------------ Campos */
const BASE_CAMPO =
  "block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-marca-500 focus:outline-none focus:ring-2 focus:ring-marca-500/30 disabled:bg-slate-100";

interface CampoProps {
  rotulo: string;
  ajuda?: string;
  obrigatorio?: boolean;
  className?: string;
}

export const Entrada = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement> & CampoProps>(
  function Entrada({ rotulo, ajuda, obrigatorio, className, id, ...rest }, ref) {
    const auto = useId();
    const idCampo = id ?? auto;
    return (
      <div className={className}>
        <Rotulo htmlFor={idCampo} obrigatorio={obrigatorio ?? rest.required}>
          {rotulo}
        </Rotulo>
        <input ref={ref} id={idCampo} {...rest} aria-describedby={ajuda ? `${idCampo}-ajuda` : undefined} className={BASE_CAMPO} />
        {ajuda && (
          <p id={`${idCampo}-ajuda`} className="mt-1 text-xs text-slate-500">
            {ajuda}
          </p>
        )}
      </div>
    );
  },
);

export function AreaTexto({ rotulo, ajuda, className, id, ...rest }: React.TextareaHTMLAttributes<HTMLTextAreaElement> & CampoProps) {
  const auto = useId();
  const idCampo = id ?? auto;
  return (
    <div className={className}>
      <Rotulo htmlFor={idCampo} obrigatorio={rest.required}>
        {rotulo}
      </Rotulo>
      <textarea id={idCampo} rows={3} {...rest} className={BASE_CAMPO} />
      {ajuda && <p className="mt-1 text-xs text-slate-500">{ajuda}</p>}
    </div>
  );
}

interface SelecaoProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "children">, CampoProps {
  opcoes: { value: string | number; label: string }[];
  vazio?: string;
}

export function Selecao({ rotulo, ajuda, opcoes, vazio, className, id, ...rest }: SelecaoProps) {
  const auto = useId();
  const idCampo = id ?? auto;
  return (
    <div className={className}>
      <Rotulo htmlFor={idCampo} obrigatorio={rest.required}>
        {rotulo}
      </Rotulo>
      <select id={idCampo} {...rest} className={BASE_CAMPO}>
        {vazio !== undefined && <option value="">{vazio}</option>}
        {opcoes.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {ajuda && <p className="mt-1 text-xs text-slate-500">{ajuda}</p>}
    </div>
  );
}

export function Caixa({ rotulo, ajuda, className, ...rest }: React.InputHTMLAttributes<HTMLInputElement> & { rotulo: string; ajuda?: string }) {
  return (
    <label className={cx("flex items-start gap-2 text-sm text-slate-700", className)}>
      <input type="checkbox" {...rest} className="mt-0.5 h-4 w-4 rounded border-slate-300 accent-marca-600" />
      <span>
        {rotulo}
        {ajuda && <span className="block text-xs text-slate-500">{ajuda}</span>}
      </span>
    </label>
  );
}

/** Lista de caixas de seleção múltipla (ex.: especialidades de uma unidade). */
export function MultiSelecao({
  rotulo,
  opcoes,
  valor,
  onChange,
}: {
  rotulo: string;
  opcoes: { value: number; label: string }[];
  valor: number[];
  onChange: (v: number[]) => void;
}) {
  return (
    <fieldset>
      <legend className="mb-1 text-sm font-medium text-slate-700">{rotulo}</legend>
      <div className="flex max-h-40 flex-wrap gap-2 overflow-y-auto rounded-lg border border-slate-200 p-2">
        {opcoes.length === 0 && <span className="text-xs text-slate-500">Nenhuma opção cadastrada.</span>}
        {opcoes.map((o) => {
          const marcado = valor.includes(o.value);
          return (
            <label
              key={o.value}
              className={cx(
                "cursor-pointer rounded-full px-3 py-1 text-xs ring-1 ring-inset",
                marcado ? "bg-marca-600 text-white ring-marca-600" : "bg-white text-slate-700 ring-slate-300 hover:bg-slate-50",
              )}
            >
              <input
                type="checkbox"
                className="sr-only"
                checked={marcado}
                onChange={() => onChange(marcado ? valor.filter((v) => v !== o.value) : [...valor, o.value])}
              />
              {o.label}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function Rotulo({ htmlFor, obrigatorio, children }: { htmlFor: string; obrigatorio?: boolean; children: React.ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium text-slate-700">
      {children}
      {obrigatorio && (
        <span className="text-red-600" aria-hidden>
          {" "}
          *
        </span>
      )}
    </label>
  );
}

/* ------------------------------------------------------------------ Estrutura */
export function Cartao({ titulo, acoes, children, className }: { titulo?: string; acoes?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={cx("rounded-xl border border-slate-200 bg-white shadow-sm", className)}>
      {(titulo || acoes) && (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
          {titulo && <h2 className="text-sm font-semibold text-slate-800">{titulo}</h2>}
          {acoes}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function CabecalhoPagina({ titulo, descricao, acoes }: { titulo: string; descricao?: string; acoes?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{titulo}</h1>
        {descricao && <p className="mt-1 max-w-3xl text-sm text-slate-600">{descricao}</p>}
      </div>
      {acoes && <div className="flex flex-wrap gap-2">{acoes}</div>}
    </div>
  );
}

export function BarraFiltros({ children }: { children: React.ReactNode }) {
  return <div className="mb-4 grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">{children}</div>;
}

export function Abas<T extends string>({ abas, ativa, onChange }: { abas: { id: T; rotulo: string }[]; ativa: T; onChange: (a: T) => void }) {
  return (
    <div role="tablist" className="mb-4 flex gap-1 overflow-x-auto border-b border-slate-200">
      {abas.map((a) => (
        <button
          key={a.id}
          role="tab"
          aria-selected={ativa === a.id}
          onClick={() => onChange(a.id)}
          className={cx(
            "-mb-px whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium",
            ativa === a.id ? "border-marca-600 text-marca-700" : "border-transparent text-slate-500 hover:text-slate-800",
          )}
        >
          {a.rotulo}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ Feedback */
export function Alerta({ tipo = "erro", children, onFechar }: { tipo?: "erro" | "sucesso" | "info" | "aviso"; children: React.ReactNode; onFechar?: () => void }) {
  const estilos = {
    erro: "border-red-200 bg-red-50 text-red-800",
    sucesso: "border-emerald-200 bg-emerald-50 text-emerald-800",
    info: "border-sky-200 bg-sky-50 text-sky-800",
    aviso: "border-amber-200 bg-amber-50 text-amber-900",
  }[tipo];
  return (
    <div role={tipo === "erro" ? "alert" : "status"} className={cx("mb-4 flex items-start justify-between gap-3 rounded-lg border px-4 py-3 text-sm", estilos)}>
      <div>{children}</div>
      {onFechar && (
        <button onClick={onFechar} className="text-lg leading-none opacity-60 hover:opacity-100" aria-label="Fechar aviso">
          ×
        </button>
      )}
    </div>
  );
}

const CORES_SELO = {
  cinza: "bg-slate-100 text-slate-700 ring-slate-200",
  verde: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  vermelho: "bg-red-50 text-red-700 ring-red-200",
  amarelo: "bg-amber-50 text-amber-800 ring-amber-200",
  azul: "bg-sky-50 text-sky-700 ring-sky-200",
  roxo: "bg-violet-50 text-violet-700 ring-violet-200",
};
export type CorSelo = keyof typeof CORES_SELO;

export function Selo({ cor = "cinza", children, title }: { cor?: CorSelo; children: React.ReactNode; title?: string }) {
  return (
    <span title={title} className={cx("inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset", CORES_SELO[cor])}>
      {children}
    </span>
  );
}

export function Carregando({ texto = "Carregando…" }: { texto?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-8 text-sm text-slate-500">
      <Spinner /> {texto}
    </div>
  );
}

export function Vazio({ children }: { children: React.ReactNode }) {
  return <p className="py-8 text-center text-sm text-slate-500">{children}</p>;
}

export function ItemDefinicao({ termo, children }: { termo: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{termo}</dt>
      <dd className="mt-0.5 text-sm text-slate-900">{children}</dd>
    </div>
  );
}
