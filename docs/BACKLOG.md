# Backlog do Confirma Aí

Transcrição estruturada da seção 10.3 do PDF. Estimativas ainda sujeitas à validação da equipe.

| ID | Épico | Item | Prioridade | SP | Frente | Sprint |
|---|---|---|---|---:|---|---|
| PB01 | E1 | Configurar repositório, quadro Kanban, padrão de branches e integração contínua | Must | 3 | F + B | S1 |
| PB02 | E1 | Estruturar o back-end modular em camadas, com health check e documentação OpenAPI | Must | 3 | Back | S1 |
| PB03 | E1 | Criar o banco PostgreSQL com migrations iniciais (pacientes, contatos, unidades, especialidades, profissionais, usuários, perfis) | Must | 3 | Back | S1 |
| PB04 | E1 | Estruturar o front-end com layout base, rotas, guia visual acessível e cliente HTTP | Must | 3 | Front | S1 |
| PB05 | E3 | HU01 – Cadastrar, consultar, alterar e inativar paciente | Must | 5 | F + B | S1 |
| PB06 | E2 | Autenticação individual (login, senha com hash, token JWT) | Must | 5 | F + B | S2 |
| PB07 | E2 | UC08 – Administrar usuários, perfis e permissões | Must | 5 | F + B | S2 |
| PB08 | E3 | UC01 – Cadastrar unidades, especialidades, profissionais, horários e bloqueios | Must | 5 | F + B | S2 |
| PB09 | E10 | Módulo de auditoria: registrar eventos com data, hora e origem | Must | 3 | Back | S2 |
| PB10 | E4 | UC02 – Registrar agendamento validando disponibilidade | Must | 5 | F + B | S3 |
| PB11 | E4 | UC02 – Visualizar agenda com filtros e status textual | Must | 5 | F + B | S3 |
| PB12 | E9 | HU04 – Registrar e revogar autorização e preferências de contato | Must | 3 | F + B | S3 |
| PB13 | E5 | Adaptador de mensageria (interface única, simulador local e WhatsApp Cloud API) | Must | 8 | Back | S3 |
| PB14 | E5 | UC03 – Enviar lembrete automático com antecedência configurável | Must | 5 | Back | S4 |
| PB15 | E5 | UC13 – Gerar identificador único e validar o vínculo da resposta | Must | 5 | Back | S4 |
| PB16 | E5 | UC04 – Processar resposta SIM, NÃO ou REMARCAR e atualizar o status | Must | 5 | F + B | S4 |
| PB17 | E5 | Retentativas controladas e envio idempotente (fila de eventos) | Must | 3 | Back | S4 |
| PB18 | E10 | Histórico do agendamento (linha do tempo de mensagens e status) | Must | 3 | F + B | S4 |
| PB19 | E6 | HU02 – Solicitar remarcação e painel de pendências da recepção | Must | 3 | F + B | S5 |
| PB20 | E6 | Cadastrar paciente na fila de espera com preferências | Must | 5 | F + B | S5 |
| PB21 | E6 | HU03 – Informar disponibilidade para encaixe (locais e períodos) | Must | 3 | F + B | S5 |
| PB22 | E8 | UC10 – Configurar parâmetros operacionais versionados | Must | 3 | F + B | S5 |
| PB23 | E7 | UC05 – Identificar vaga liberada dentro da janela configurada | Must | 5 | Back | S5 |
| PB24 | E7 | UC05 – Aplicar regras de elegibilidade | Must | 8 | Back | S6 |
| PB25 | E7 | Priorizar elegíveis com desempate determinístico | Must | 5 | Back | S6 |
| PB26 | E7 | UC06 – Enviar oferta de encaixe com reserva temporária | Must | 5 | F + B | S6 |
| PB27 | E7 | UC07 – Confirmar aceite de forma atômica e impedir dupla marcação | Must | 5 | Back | S6 |
| PB28 | E7 | UC06 – Liberar reserva por recusa, expiração ou falha e reofertar | Must | 5 | Back | S7 |
| PB29 | E7 | Painel de vagas e ofertas com tratamento manual | Should | 3 | Front | S7 |
| PB30 | E10 | UC09 – Consultar indicadores de absenteísmo e recuperação | Should | 8 | F + B | S7 |
| PB31 | E10 | Métricas de observabilidade (envio, falha, confirmação, recuperação) | Should | 3 | Back | S7 |
| PB32 | E9 | UC11 – Atender requisições do titular de dados | Should | 5 | F + B | S8 |
| PB33 | E9 | UC12 – Configurar retenção e executar eliminação ou anonimização | Should | 8 | Back | S8 |
| PB34 | E11 | Revisão de acessibilidade e linguagem clara das telas e mensagens | Should | 3 | Front | S8 |
| PB35 | E11 | Rotina de backup e teste de restauração | Should | 2 | Back | S8 |
| PB36 | E11 | Teste de desempenho com 10.000 agendamentos ativos | Could | 3 | Back | S8 |
| PB37 | E2 | Autenticação multifator para perfis administrativos | Could | 5 | F + B | Futuro |
| PB38 | E4 | Importar ou sincronizar agendamentos de sistema externo autorizado | Could | 8 | Back | Futuro |

Total: 172 SP; Must: 124 SP; S1–S8: 159 SP; Futuro: 13 SP. Não somar pontos dos épicos novamente.
