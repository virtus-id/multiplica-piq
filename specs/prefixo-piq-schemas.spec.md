# Spec — prefixo `piq_` nos schemas do banco

| Campo | Valor |
| ----- | ----- |
| Slug  | `prefixo-piq-schemas` |
| Origem | Pedido do produto: o Supabase de produção é compartilhado com outros sistemas (`vtr_*`, `core_*`, `trv_*`, `ads_*`) e não se distingue o que é do PIQ. |

## Requisitos

- **`RF-455`** — Os schemas do PIQ passam a se chamar `piq_app_aluno` (era `app_aluno`) e `piq_motor_calculo` (era `motor_calculo`). Os nomes das tabelas **não mudam**.
- **`RF-456`** — Nenhum dado é perdido ou movido: contas, casos, respostas, revisões, snapshots e parâmetros existentes continuam acessíveis após a mudança, com os mesmos valores.
- **`RF-457`** — A restrição de append-only de `snapshots` e `revisoes` (gatilho e `REVOKE`) continua valendo no schema renomeado, e as mensagens de erro citam os nomes novos.
- **`RF-458`** — Uma instalação nova (migrações 001 a 012 em ordem) termina com o mesmo estado de um banco existente migrado.
- **`RF-459`** — A migração é segura de repetir (rodar duas vezes não falha nem altera nada na segunda).
- **`RF-460`** — Nenhum código, teste ou documento do projeto cita os nomes antigos de schema como nome de schema. O pacote Python `persistencia.app_aluno` e a pasta `tests/app_aluno/` **não** são schemas e ficam como estão.

## Fora do escopo

Renomear tabelas, colunas, índices ou o pacote Python; mover tabelas para `public`; habilitar RLS (achado à parte: as 10 tabelas estão sem RLS).

## Open Questions

- **`OQ-1`** — Existe algo fora deste repositório que leia esses schemas pelo nome (n8n, BI, SQL salvo no painel, "Exposed schemas" da API do Supabase)? Precisa ser respondida antes da virada em produção.
- **`OQ-2`** — A migração 011 já foi aplicada em produção? (O `T-435` diz que não.) Ela cita os nomes antigos e **deve** rodar antes da 012.
