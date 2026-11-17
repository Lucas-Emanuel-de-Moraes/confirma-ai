import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// Testes unitários das funções puras do front (formatação, permissões).
export default defineConfig({
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: { include: ["src/**/*.test.ts"], environment: "node" },
});
