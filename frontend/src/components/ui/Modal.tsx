"use client";

import { useEffect, useRef } from "react";
import { cx } from "./index";

interface ModalProps {
  aberto: boolean;
  titulo: string;
  onFechar: () => void;
  children: React.ReactNode;
  rodape?: React.ReactNode;
  largura?: "md" | "lg" | "xl";
}

/** Diálogo acessível usando o elemento nativo <dialog> (foco preso e Esc para fechar). */
export function Modal({ aberto, titulo, onFechar, children, rodape, largura = "md" }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (aberto && !d.open) d.showModal();
    if (!aberto && d.open) d.close();
  }, [aberto]);

  return (
    <dialog
      ref={ref}
      onClose={onFechar}
      onCancel={(e) => {
        e.preventDefault();
        onFechar();
      }}
      aria-labelledby="titulo-modal"
      className={cx(
        "m-auto w-[calc(100%-2rem)] rounded-xl bg-white p-0 shadow-2xl backdrop:bg-slate-900/40",
        { md: "max-w-lg", lg: "max-w-2xl", xl: "max-w-4xl" }[largura],
      )}
    >
      {aberto && (
        <div className="flex max-h-[85vh] flex-col">
          <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h2 id="titulo-modal" className="text-base font-semibold text-slate-900">
              {titulo}
            </h2>
            <button onClick={onFechar} aria-label="Fechar" className="rounded p-1 text-xl leading-none text-slate-400 hover:text-slate-700">
              ×
            </button>
          </header>
          <div className="overflow-y-auto px-5 py-4">{children}</div>
          {rodape && <footer className="flex justify-end gap-2 border-t border-slate-100 px-5 py-3">{rodape}</footer>}
        </div>
      )}
    </dialog>
  );
}
