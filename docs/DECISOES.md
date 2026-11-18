# Registro de decisões técnicas

O GUIA-GITHUB (seção 9) pede que nenhum framework novo seja adotado sem registro.
Cada decisão traz o contexto, o que foi decidido e o que ainda falta validar com o grupo e o PO.

| # | Decisão | Situação |
|---|---|---|
| D1 | Front-end em **Next.js 16 + React 19** (o documento cita React 18) | Em uso — validar com o grupo |
| D2 | **Tailwind CSS 4** para estilos (não citado no documento) | Em uso — validar com o grupo |
| D3 | Testes do front com **Vitest** | Em uso |
| D4 | Sprint 1 redefinida pelo professor como o **Problema 3** | Registrado |
| D5 | Previsão de falta e FHIR (Problema 3) ainda fora deste código | Pendente |

## D1 – Next.js 16 e React 19

**Contexto.** A seção 11 do documento define React 18 + Next.js com App Router. As versões atuais
do Next.js (15 em diante) exigem React 19, e o código do front-end foi criado já nessa versão.

**Decisão.** Manter Next.js 16 e React 19. App Router, TypeScript e Axios continuam como no documento.

**Consequência.** Atualizar a seção 11 do documento de requisitos (de "React 18" para "React 19").

## D2 – Tailwind CSS

**Contexto.** O documento não define biblioteca de estilos. O front-end usa Tailwind CSS 4, sem
outras bibliotecas de componentes.

**Decisão.** Manter o Tailwind. As regras de acessibilidade (RNF16) continuam valendo: rótulos nos
campos, foco visível, contraste e status em texto.

## D3 – Vitest nos testes do front-end

**Contexto.** O documento se contradiz: a seção 11.4 cita `node:test` e a tarefa T04 cita Vitest.

**Decisão.** Vitest (`npm test`). Ele entende TypeScript e o atalho `@/` sem configuração extra.
O CI roda lint, tipos, testes e build do front a cada pull request.

## D4 – Sprint 1 = Problema 3

**Contexto.** O backlog prevê S1 = PB01–PB05 (fundação + cadastro de paciente). O professor redefine
o escopo a cada semana e definiu a Sprint 1 como a entrega do Problema 3 (protótipo com FHIR e uma
funcionalidade inteligente).

**Decisão.** As sprints S2–S8 do backlog servem de referência de prioridade, não de calendário fixo.

## D5 – Pendência: previsão de falta e FHIR

O que foi apresentado no Problema 3 (previsão de falta explicável e o agendamento exportado como
HL7 FHIR R4 `Appointment`) ainda não está neste código nem em nenhum PB do backlog.

**Próximo passo.** Criar um requisito (ex.: RF25 – estimar o risco de falta de um agendamento) e um
item PB para cada parte, e só então implementar, conforme a regra 10.1(c) do backlog.
