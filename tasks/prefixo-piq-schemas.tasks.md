# Backlog — prefixo `piq_` nos schemas

| Campo | Valor |
| ----- | ----- |
| Slug  | `prefixo-piq-schemas` |
| Spec  | [`specs/prefixo-piq-schemas.spec.md`](../specs/prefixo-piq-schemas.spec.md) |
| Plano | [`plans/prefixo-piq-schemas.plan.md`](../plans/prefixo-piq-schemas.plan.md) |

> Numeração contínua (última da feature anterior: `T-440`).

### `T-441` — Migração 012
- **Rastreia:** `RF-455`, `RF-456`, `RF-457`, `RF-458`, `RF-459`
- [x] `persistencia/supabase/migracoes/012_prefixo_piq_nos_schemas.sql`: renomeia os dois schemas (idempotente) e recria as duas funções de gatilho com a mensagem nova. 001–011 intactas.

### `T-442` — Código
- **Rastreia:** `RF-455`, `RF-460` · **Dependências:** `T-441`
- [x] 10 constantes `_SCHEMA` e o `schema.tabela` dos SQLs em `persistencia/`, `app/`, `scripts/`, `collection/`, `report/`. Sem tocar em imports `persistencia.app_aluno.*`. Atualizar só as 3 entradas de hash de `persistencia/supabase/` em `hashes_congelados.json`.

### `T-443` — Testes
- **Rastreia:** `RF-457`, `RF-458`, `RF-459`, `RF-460` · **Dependências:** `T-442`
- [x] Trocar o schema nos testes existentes e nas asserções de texto de erro; teste de migração 001→012 com reaplicação; teste estático dos nomes antigos.

### `T-444` — Documentos
- **Rastreia:** `RF-460`
- [x] `docs/banco-local.md` (inclui a contagem: são 8 tabelas em `app_aluno`, o doc diz 7), `README.md`, `plans/` e `tasks/` anteriores onde o nome aparece como schema.

### `T-445` — Virada em produção
- **Rastreia:** `RF-455`, `RF-456` · **Dependências:** `T-441` a `T-444`, `OQ-1`, `OQ-2`
- [ ] Executar o roteiro do plano. **Não feito sem autorização explícita.**
