"use client";

import { useSyncExternalStore } from "react";
import { hojeISO } from "@/lib/formato";

const semAssinatura = () => () => {};

/**
 * Data de hoje ("AAAA-MM-DD") lida só no navegador.
 * No pré-render do Next devolve `null`, então a data nunca fica "congelada" no HTML estático
 * (evita o erro blocking-prerender-current-time-client).
 */
export function useHoje(): string | null {
  return useSyncExternalStore(semAssinatura, hojeISO, () => null);
}
