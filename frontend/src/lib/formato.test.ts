import { describe, expect, it } from "vitest";
import { data, dataHora, hora, paraApiDataHora, paraInputDataHora, percentual, rotulo, somarDias, telefone } from "./formato";

describe("datas da API (horário local da clínica, sem fuso)", () => {
  it("formata data e hora", () => {
    expect(dataHora("2026-11-10T09:05:00")).toBe("10/11/2026 09:05");
    expect(data("2026-11-10T09:05:00")).toBe("10/11/2026");
    expect(hora("2026-11-10T09:05:00")).toBe("09:05");
  });

  it("mostra traço quando não há valor", () => {
    expect(dataHora(null)).toBe("—");
    expect(hora(undefined)).toBe("—");
  });

  it("converte entre o input datetime-local e a API", () => {
    expect(paraApiDataHora("2026-11-10T09:00")).toBe("2026-11-10T09:00:00");
    expect(paraInputDataHora("2026-11-10T09:00:00")).toBe("2026-11-10T09:00");
  });

  it("soma dias atravessando o fim do mês", () => {
    expect(somarDias("2026-11-30", 1)).toBe("2026-12-01");
    expect(somarDias("2026-03-01", -1)).toBe("2026-02-28");
  });
});

describe("outros formatos", () => {
  it("percentual a partir de fração", () => {
    expect(percentual(0.85)).toBe("85%");
    expect(percentual(null)).toBe("—");
  });

  it("telefone com e sem DDI", () => {
    expect(telefone("5565999990001")).toBe("(65) 99999-0001");
    expect(telefone("6533334444")).toBe("(65) 3333-4444");
  });

  it("status sempre em texto (RNF10), com o código como alternativa", () => {
    expect(rotulo("statusAgendamento", "NAO_CONFIRMADO")).toBe("Não confirmado");
    expect(rotulo("statusOferta", "FALHA_CONTATO")).toBe("Falha de contato");
    expect(rotulo("statusAgendamento", "DESCONHECIDO")).toBe("DESCONHECIDO");
  });
});
