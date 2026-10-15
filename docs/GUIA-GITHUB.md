# Organização do Confirma Aí no GitHub

Este guia transforma as seções 9–13 do documento em uma proposta de cadastro. Nomes de etiquetas, convenções de branches e representação dos épicos como issues agrupadoras são sugestões operacionais. Códigos, títulos, prioridades, estimativas e sprints dos PB foram preservados.

## 1. O que significa subir os épicos

Criar 11 issues agrupadoras, uma por épico E1–E11; criar os 38 itens PB01–PB38 como issues; vincular cada PB ao seu épico como sub-issue; adicionar as issues ao GitHub Projects. Isso resulta em 49 issues se o grupo adotar issues para os épicos. São 38 itens estimados do produto, não 49 funcionalidades. Os números automáticos do GitHub não substituem os códigos PB e E.

Os arquivos em issues/epicos e issues/backlog fornecem o título na primeira linha e o corpo nas linhas seguintes. Copiar o título sem o símbolo #. As checklists dos épicos devem receber os links reais das issues após o cadastro; apenas escrever PB01 não cria vínculo no GitHub.

## 2. Repositório

- Nome definido no documento: `confirma-ai`.
- Descrição sugerida: “Sistema web de confirmação de consultas e recuperação de vagas, com fila de espera priorizada, mensageria e gestão de agendas. Projeto acadêmico do Grupo 2.”
- Titular: conta ou organização escolhida pelo grupo.
- Visibilidade: decidir conforme a orientação da disciplina e do grupo; o documento não fixa essa opção.
- Branch principal sugerida: `main`.
- Adicionar os quatro integrantes como colaboradores pelos respectivos usuários do GitHub.
- Não escolher uma licença de uso sem uma decisão do grupo.

Criar o repositório pela opção de novo repositório no GitHub, inicializá-lo com README e depois adicionar os arquivos. Este pacote documenta o planejamento; não apresenta a aplicação como implementada.

Estrutura de implementação prevista na seção 11.9:

```text
confirma-ai/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   └── modules/
│   │       ├── acesso/
│   │       ├── cadastros/
│   │       ├── agenda/
│   │       ├── confirmacao/
│   │       ├── fila/
│   │       ├── recuperacao/
│   │       ├── parametros/
│   │       ├── lgpd/
│   │       ├── notificacao/
│   │       ├── auditoria/
│   │       └── indicadores/
│   ├── alembic/versions/
│   ├── tests/
│   └── pyproject.toml
├── frontend/src/
│   ├── app/
│   ├── components/
│   ├── services/api.ts
│   ├── contexts/
│   ├── interfaces/
│   └── utils/
├── docs/
├── docker-compose.yml
└── .github/workflows/ci.yml
```

Esses caminhos são a estrutura a implementar, não arquivos executáveis fornecidos por este pacote. Para versionar diretórios provisoriamente vazios, pode-se usar `.gitkeep`. Não criar CI que apenas simule sucesso: PB01 exige compilação e testes reais quando os projetos estiverem configurados. O README final deverá incluir comandos de instalação e execução validados.

## 3. Etiquetas sugeridas

- Tipo: `tipo:epico`, `tipo:backlog`.
- Épico: `epico:E1` até `epico:E11`.
- Prioridade: `prioridade:must`, `prioridade:should`, `prioridade:could`.
- Frente: `frente:frontend`, `frente:backend`, `frente:ambos`.
- Apoio: `impedimento`, `refinamento`.

Exemplo: PB05 recebe `tipo:backlog`, `epico:E3`, `prioridade:must` e `frente:ambos`. E3 recebe `tipo:epico` e `epico:E3`. Não atribuir ao épico uma prioridade única quando seus itens tiverem prioridades distintas.

## 4. GitHub Projects

Nome sugerido: `Confirma Aí | Grupo 2`. Vincular o repositório e adicionar as issues. Usar uma visualização de quadro agrupada pelo campo Status com os nomes exatos da seção 9.4:

1. Backlog do produto.
2. Pronto para a sprint.
3. A fazer.
4. Em andamento.
5. Em revisão.
6. Pronto.

Limites do documento: até 2 itens em andamento por pessoa e até 3 itens em revisão no total. Tratar esses limites como política da equipe, acompanhada na Daily; a criação das colunas não garante bloqueio automático por WIP.

Campos sugeridos: Status; Épico (seleção E1–E11); Prioridade (Must, Should, Could); Frente (Front, Back, F + B); SP (número); Sprint prevista (S1–S8 e Futuro); responsável (Assignees). Usar os requisitos no corpo da issue. Datas não foram definidas para S1–S8, portanto começar com seleção simples de sprint; configurar iterações após a equipe aprovar o calendário.

Criar vistas: Backlog ordenado pelo código PB; Sprint atual; Épicos; Futuro. Na vista operacional e na soma dos pontos, filtrar `tipo:backlog`, evitando contar issues agrupadoras e tarefas técnicas duas vezes. Manter PB01–PB38 nessa ordem inicial, sem reorganizar por épico a prioridade global do produto.

## 5. Sequência de cadastro

1. Criar o repositório, adicionar colaboradores e README.
2. Criar etiquetas e o Project com campos e colunas.
3. Criar E1–E11 com os textos de issues/epicos.
4. Criar PB01–PB38 com os textos de issues/backlog.
5. Associar cada PB ao seu épico como sub-issue e inserir os links na checklist do épico.
6. Adicionar ao Project e preencher os campos conforme docs/BACKLOG.md.
7. Manter os itens no Backlog do produto inicialmente. Validar estimativas e critérios antes de movê-los para Pronto para a sprint.
8. Após a Sprint Planning, selecionar PB01–PB05 para S1, atribuir responsáveis e mover o trabalho selecionado para A fazer.
9. Configurar proteção da main e CI quando o código base estiver disponível. Verificar disponibilidade da proteção conforme plano e visibilidade do repositório.

## 6. Padrões de colaboração propostos

Branches: `feat/PB05-cadastro-pacientes`, `fix/PB05-validacao-telefone`, `chore/PB01-configuracao-repositorio`.

Commits: `feat(pacientes): adiciona cadastro [PB05]`.

PR: `[PB05] Cadastro de pacientes`. Descrever alteração e validação e vincular a issue pelo número real. Usar `Closes #NUMERO_REAL` apenas no PR que efetivamente concluir o item; em entregas parciais, usar apenas uma referência para não encerrar a issue antecipadamente.

Proteger main para exigir PR revisado por outro integrante e verificações de CI aprovadas. Não marcar como pronto só porque o PR foi mesclado: falta verificar os demais critérios e o aceite do PO.

Um responsável principal por PB. Para itens F + B, dividir tarefas de cada frente, com responsáveis diferentes, vinculadas ao mesmo PB. Registrar dúvidas de integração na issue. Realizar revisão cruzada entre frentes ao menos uma vez por sprint, conforme seção 13.3.

## 7. Critérios de Preparado e Pronto

Preparado: história ou tarefa técnica com rastreabilidade; critérios verificáveis; estimativa feita pela equipe; dependências resolvidas ou planejadas na mesma sprint; tamanho de até 8 SP.

Pronto: critérios atendidos e demonstrados; código na principal após PR revisado; lint e testes aprovados; novos endpoints documentados no OpenAPI; telas com rótulos, navegação por teclado e status textual; auditoria aplicável registrada; cartão em Pronto e aceite do PO.

PB01–PB09 têm detalhamento no PDF, mas as estimativas ainda precisam de Planning Poker. PB10–PB38 devem ser refinados antes de entrar em sprint; os arquivos deixam essa pendência explícita.

## 8. Sprints preservadas do documento

| Sprint | Itens | SP |
|---|---|---:|
| S1 | PB01–PB05 | 17 |
| S2 | PB06–PB09 | 18 |
| S3 | PB10–PB13 | 21 |
| S4 | PB14–PB18 | 21 |
| S5 | PB19–PB23 | 19 |
| S6 | PB24–PB27 | 23 |
| S7 | PB28–PB31 | 19 |
| S8 | PB32–PB36 | 21 |
| Futuro | PB37–PB38 | 13 |

Total de 172 SP, incluindo Futuro; 159 SP em S1–S8; 124 SP Must. São estimativas, não horas ou entregas concluídas. A Sprint 0 produz o planejamento e não adiciona pontos de produto.

Na Sprint 1, o documento atribui criação do repositório e proteção de branch à Laryssa; quadro e cadastro das 38 issues ao Fabricio; CI ao Lucas. Esses papéis podem ser combinados novamente pelo grupo. Ter os textos prontos não significa que PB01 esteja concluído.

## 9. Pontos para validar no refinamento

- O MVP é anunciado ao final de S6, mas PB28 (recusa, expiração, falha e reoferta) é Must e está em S7. Proposta: antecipar PB28 e recalcular capacidade ou revisar o marco do MVP para S7. O pacote preserva a previsão original.
- RF08/RN05 preservam a consulta ao solicitar remarcação. Não liberar a vaga apenas porque chegou REMARCAR; formalizar a transição que efetivamente torna a vaga disponível antes de PB23 ofertá-la.
- E2 e E4 incluem itens de Futuro (PB37 e PB38). Distinguir conclusão da release e encerramento integral do épico.
- O documento menciona “LGPD completa” em S8. Tratar isso como nome de escopo planejado, não como certificação de conformidade jurídica obtida por terminar issues.
- A seção 11.3 registra que PoliticaRetencao precisa ser acrescentada ao diagrama de classes. Manter essa atualização vinculada à implementação de PB33.
- Preservar a versão React/Next especificada como referência do planejamento, mas definir versões compatíveis ao implementar. Não introduzir outro framework sem registrar a decisão.

## 10. Texto para apresentação

“A organização do Confirma Aí no GitHub será baseada nos 11 épicos e nos 38 itens do backlog definidos no documento de requisitos. Cada épico agrupa uma capacidade do sistema, e cada item PB será registrado como issue com rastreabilidade, prioridade MoSCoW, estimativa, frente e sprint prevista. O GitHub Projects representará o fluxo Scrumban, permitindo acompanhar responsáveis, impedimentos, revisões e entregas. O repositório seguirá a arquitetura de monólito modular, com front-end React/TypeScript, API FastAPI e banco PostgreSQL. A primeira sprint contempla a fundação técnica e o cadastro de pacientes, totalizando 17 pontos estimados.”

## Fontes de operação do GitHub

- [GitHub Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects): quadros, tabelas e visualizações.
- [Campos do Project](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields): campos personalizados e relações pai/sub-issue.
- [Criação de issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue): cadastro de trabalho no repositório.
- [Proteção de branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches): revisões e verificações obrigatórias.
