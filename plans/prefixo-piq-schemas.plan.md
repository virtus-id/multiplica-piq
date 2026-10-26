# Plano — prefixo `piq_` nos schemas do banco

| Campo | Valor |
| ----- | ----- |
| Slug  | `prefixo-piq-schemas` |
| Spec  | [`specs/prefixo-piq-schemas.spec.md`](../specs/prefixo-piq-schemas.spec.md) |

## Tech Stack

Sem tecnologia nova. Postgres (`ALTER SCHEMA ... RENAME TO`), psycopg e SQL já existentes. Uma migração e uma troca textual.

## Decisões

1. **Migração nova `012_prefixo_piq_nos_schemas.sql`; 001–011 intactas** (`RF-455`, `RF-458`). As anteriores já foram aplicadas em produção e a 001 está no conjunto congelado por hash. Instalação nova roda 001→012 em ordem e chega ao mesmo estado.
2. **`ALTER SCHEMA ... RENAME`** (`RF-456`): só metadado. Tabelas, índices, FKs, gatilhos, funções e `REVOKE` acompanham o schema.
3. **Idempotência** (`RF-459`): cada renomeação só roda se o schema antigo existe e o novo não.
4. **Funções de gatilho recriadas** (`RF-457`): o texto do `RAISE EXCEPTION` cita o nome do schema; `CREATE OR REPLACE` na 012 atualiza a mensagem.
5. **Código**: trocar as constantes `_SCHEMA` e o `schema.tabela` dos SQLs. O padrão exige lookbehind `(?<![\w.])` para não atingir `persistencia.app_aluno.contas` (módulo Python) (`RF-460`).
6. **Hashes congelados**: `conexao.py`, `fonte_parametros.py` e `repositorio_snapshots.py` mudam, então só essas três entradas de `tests/app_aluno/estatica/hashes_congelados.json` são atualizadas, uma a uma. `001_inicial.sql` não é tocada.

## Virada em produção

Banco e app trocam juntos. Pré-requisitos: `OQ-1` e `OQ-2` respondidas e imagem nova construída.

1. Conferir que `piq_app_aluno` e `piq_motor_calculo` não existem no banco compartilhado.
2. Parar a API.
3. Se a 011 ainda não foi aplicada, aplicá-la **agora** (cita os nomes antigos), e depois a 012.
4. Subir a imagem nova; conferir `/saude`, login e `GET /api/conta/eu`.
5. Reversão: `ALTER SCHEMA piq_app_aluno RENAME TO app_aluno` (idem motor) e subir a imagem anterior.

## Testes

Derivam dos RF: `RF-455/456/458/459` por um teste de integração que aplica 001→012 em banco limpo, grava dados, reaplica a 012 e confere; `RF-457` pelos testes de append-only já existentes com o texto novo; `RF-460` por um teste estático que varre `persistencia`, `app`, `scripts`, `collection`, `report` e `tests`.
