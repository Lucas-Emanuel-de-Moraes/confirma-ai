"use client";

import { createContext, useCallback, useContext, useState } from "react";
import { cx } from "./index";

type Tipo = "sucesso" | "erro" | "info";
interface Item {
  id: number;
  tipo: Tipo;
  texto: string;
}

const Ctx = createContext<(texto: string, tipo?: Tipo) => void>(() => {});

/** Notificações rápidas ("toasts") após ações bem-sucedidas ou com erro. */
export function AvisosProvider({ children }: { children: React.ReactNode }) {
  const [itens, setItens] = useState<Item[]>([]);

  const avisar = useCallback((texto: string, tipo: Tipo = "sucesso") => {
    const id = Date.now() + Math.random();
    setItens((l) => [...l, { id, tipo, texto }]);
    setTimeout(() => setItens((l) => l.filter((i) => i.id !== id)), 5000);
  }, []);

  return (
    <Ctx.Provider value={avisar}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2">
        {itens.map((i) => (
          <div
            key={i.id}
            className={cx(
              "pointer-events-auto rounded-lg px-4 py-3 text-sm text-white shadow-lg",
              i.tipo === "sucesso" && "bg-emerald-600",
              i.tipo === "erro" && "bg-red-600",
              i.tipo === "info" && "bg-slate-800",
            )}
          >
            {i.texto}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useAvisos() {
  return useContext(Ctx);
}
