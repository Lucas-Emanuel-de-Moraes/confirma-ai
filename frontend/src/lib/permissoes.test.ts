import { describe, expect, it } from "vitest";
import { P, temPermissao } from "./permissoes";

describe("permissões por perfil (menor privilégio)", () => {
  it("administrador pode tudo", () => {
    expect(temPermissao(["ADMINISTRADOR"], P.AUDITORIA_LER)).toBe(true);
  });

  it("recepcionista agenda, mas não vê auditoria nem indicadores", () => {
    expect(temPermissao(["RECEPCIONISTA"], P.AGENDA_ESCREVER)).toBe(true);
    expect(temPermissao(["RECEPCIONISTA"], P.AUDITORIA_LER)).toBe(false);
    expect(temPermissao(["RECEPCIONISTA"], P.INDICADORES_LER)).toBe(false);
  });

  it("profissional só lê agenda e estrutura", () => {
    expect(temPermissao(["PROFISSIONAL"], P.AGENDA_LER)).toBe(true);
    expect(temPermissao(["PROFISSIONAL"], P.PACIENTES_LER)).toBe(false);
  });

  it("vários perfis somam permissões; sem perfil não pode nada", () => {
    expect(temPermissao(["PROFISSIONAL", "GESTOR"], P.INDICADORES_LER)).toBe(true);
    expect(temPermissao(undefined, P.AGENDA_LER)).toBe(false);
  });
});
