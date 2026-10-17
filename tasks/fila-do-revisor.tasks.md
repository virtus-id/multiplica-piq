# Backlog — Fila do revisor em tabela

| Campo | Valor |
| ----- | ----- |
| Slug  | `fila-do-revisor` |
| Spec  | [`specs/fila-do-revisor.spec.md`](../specs/fila-do-revisor.spec.md) |
| Plano | [`plans/fila-do-revisor.plan.md`](../plans/fila-do-revisor.plan.md) |

> Numeração contínua com `enxugamento-questionario` (última tarefa: `T-407`).

## Progresso

`1/3 tarefas concluídas`.

### `T-408` — Consulta unificada de casos para o revisor (servidor)

- **Tipo:** `FEATURE` · **Dependências:** nenhuma · **Rastreia:** `RF-501`, `RF-502`, `RF-503`, `RF-504`, `RF-505`, `RF-506`
- [x] `GET /api/revisao/casos` com abas, filtros, ordenação, paginação, contagens, data de chegada, tempo na fila e quem decidiu
- [x] Testes por critério (AC-501 a AC-505, AC-507) e testes estáticos existentes verdes

**Status:** `[x] concluída`

### `T-409` — Tabela, filtros e cartões no celular (front)

- **Tipo:** `FEATURE` · **Dependências:** `T-408` · **Rastreia:** `RF-502`, `RF-504`, `RF-505`, `RF-507`
- [ ] Tabela com abas, filtros, chips, ordenação, paginação, alerta de 5 dias; cartões abaixo de 768px
- [ ] Testes de componente, acessibilidade e 360px; rótulos humanos

**Status:** `[ ] pendente`

### `T-410` — Revisão, PR e deploy

- **Tipo:** `CHORE` · **Dependências:** `T-409` · **Rastreia:** `RF-507`
- [ ] Revisão da branch, PR, merge e deploy no servidor, teste de fumaça da tela

**Status:** `[ ] pendente`
