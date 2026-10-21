# Plano — migração do Supabase (EUA → Brasil)

Plano operacional, não é feature de produto: não há `RF-NN`. Motivo: reduzir a latência do
`piq-api` (servidor no Brasil) para o banco, hoje em `us-east-1`.

## Situação

| | Origem (atual) | Destino (novo) |
|---|---|---|
| Região | `us-east-1` | `sa-east-1` |
| Projeto | `fhhrwcxbzyboftgapgis` | `zbvkvxgjayzmtrpjluhs` |
| Estado | em uso pelo PIQ | **vazio** |
| Postgres | 17.6, 13 MB | a confirmar (precisa ser ≥ 17) |

Conteúdo da origem (levantado só com leitura):

- `app_aluno`: 8 tabelas · `motor_calculo`: 2 tabelas · `public`: nenhuma.
- Extensões: `pgcrypto`, `uuid-ossp`, `supabase_vault`, `plpgsql`, `pg_stat_statements`.
- Sem roles próprios do app.
- **Sem alunos reais** → não há perda de cadastro durante a troca; a janela de manutenção
  pode ser de minutos.

Fora do escopo: Auth, Storage e Edge Functions do Supabase. O PIQ usa só o Postgres
(`DATABASE_URL`).

## Decisões

1. **`pg_dump` + `psql`, e não as migrações `001`–`010`.** O dump leva schema e dados juntos e
   elimina divergência entre as migrações e o banco real (inclusive `motor_calculo.parametros`,
   que o cálculo exige com `PARAMETROS_VERSION_VIGENTE=1.0.1`).
2. **Rodar no servidor, em container** (`postgres:17-alpine`): o Mac não tem `psql`, e o servidor
   já tem Docker. Quem fala com os dois bancos é o servidor.
3. **Session pooler (porta 5432) nos dois lados**, nunca a conexão direta
   (`db.<ref>.supabase.co` é só IPv6 e o container não a alcança).
4. **Senha do destino só no `segredos.enc.env`**, como `DATABASE_URL_DESTINO`. Não vai a chat,
   a arquivo em claro nem a argumento de linha de comando.
5. **O banco antigo não é apagado** até a validação e alguns dias de uso.

## Pré-requisitos

- [ ] String do **Session pooler** do destino, da forma
  `postgresql://postgres.zbvkvxgjayzmtrpjluhs:<senha>@aws-?-sa-east-1.pooler.supabase.com:5432/postgres`
  (Supabase → **Connect** → Session pooler; o prefixo `aws-0`/`aws-1` varia, copie do painel).
- [ ] Senha do banco novo com caracteres especiais está **codificada na URL** (`%`→`%25` etc.).
- [ ] Adicionada ao `segredos.enc.env` como `DATABASE_URL_DESTINO` (`sops segredos.enc.env`).
- [ ] Extensões no destino: `pgcrypto`, `uuid-ossp` (o dump as cria; `supabase_vault` já vem
  no projeto Supabase).

## Passos

| # | Passo | Verificação |
|---|---|---|
| 1 | **Backup da origem**: `pg_dump` completo para arquivo fora do repositório (`~/backups/`, fora do git) | arquivo > 0 e legível com `pg_restore -l` |
| 2 | **Teste de conexão** com os dois bancos a partir do servidor | `select 1` nos dois |
| 3 | **Ensaio** (piq-api ainda apontando para a origem): `pg_dump` dos schemas `app_aluno` e `motor_calculo` → restauração no destino | sem erro na restauração |
| 4 | **Conferir**: mesma lista de tabelas, colunas e contagem de linhas por tabela, origem × destino; `motor_calculo.parametros` com `1.0.1` | contagens idênticas |
| 5 | **Janela**: `docker stop piq-api piq-web` | `/saude` fora do ar |
| 6 | **Dump final** e restauração limpa no destino (`--clean --if-exists`), repetindo a conferência do passo 4 | contagens idênticas |
| 7 | **Trocar** `DATABASE_URL` pelo valor do destino no `segredos.enc.env`; commit e push | `git status` limpo |
| 8 | **Subir**: `git pull` no servidor e `sops exec-env segredos.enc.env 'docker compose up -d'` | `piq-api` healthy |
| 9 | **Validar**: `/saude/banco` = 200; login com a conta de teste; gerar um plano (exercita `motor_calculo`) | os três ok |
| 10 | **Limpar**: remover `DATABASE_URL_DESTINO` do arquivo de segredos (passa a ser `DATABASE_URL`) | só uma URL no arquivo |

Janela estimada (passos 5–9): poucos minutos, dado o tamanho de 13 MB.

## Reversão

Antes do passo 10, voltar é restaurar a `DATABASE_URL` antiga no `segredos.enc.env`
(`git revert` do commit do passo 7) e rodar o passo 8. O banco antigo não foi alterado em
nenhum momento: o dump só lê.

Depois da troca, dados novos gravados no destino **não** voltam sozinhos para a origem. Por
isso a reversão só é segura enquanto o PIQ não tiver alunos reais, ou nos primeiros minutos.

## Riscos

| Risco | Mitigação |
|---|---|
| Versão do `pg_dump` menor que a do servidor | usar a imagem `postgres:17-alpine` |
| Senha com caractere especial na URL | codificar; testar no passo 2 |
| Autenticação falhando em loop bloqueia o IP (`ECIRCUITBREAKER`) | testar com **uma** tentativa antes; não deixar o `piq-api` reiniciar em loop com URL errada |
| Dados e referências a usuários do schema `auth` | o PIQ tem os próprios `app_aluno.contas`; confirmar no passo 3 que não há FK para `auth.*` |
| Parâmetros do cálculo ausentes no destino | passo 4 confere `PARAMETROS_VERSION`; reserva: `scripts/semear_parametros.py` |
| Esquecer o banco antigo ligado e pagando | desativar o projeto da origem só após alguns dias de uso estável |

## Segredos

A senha do destino é informada **só por `sops segredos.enc.env`**, no terminal do usuário.
A execução lê o valor via `sops exec-env` e nunca o imprime.
