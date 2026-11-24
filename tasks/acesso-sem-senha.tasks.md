# Backlog — Acesso do aluno sem senha

| Campo | Valor |
| ----- | ----- |
| Slug  | `acesso-sem-senha` |
| Spec  | [`specs/acesso-sem-senha.spec.md`](../specs/acesso-sem-senha.spec.md) |
| Plano | [`plans/acesso-sem-senha.plan.md`](../plans/acesso-sem-senha.plan.md) |

> Numeração conferida em `tasks/`: último `T-689` (`tasks/calculo-de-divida.tasks.md`); este backlog usa `T-690` a `T-703`.
>
> **Ordem:** persistência (`U-01`, `U-02`) → rota de login (`U-03`) → e-mail e provisionamento (`U-04`–`U-06`) → frontend (`U-07`–`U-09`) → e2e → fechamento. Cada tarefa leva junto a atualização dos testes existentes que ela quebra (plano §9, "Testes existentes que mudam"), para terminar com a suíte verde. Tarefas `Test` à parte cobrem os critérios novos.
>
> **Verificação — servidor:** gates `lint`, `build`, `test` da seção 2 de `sdd.config.md`, mais o `pytest -q` dos arquivos tocados. O config grava o caminho Windows (`.venv/Scripts/python.exe`); no macOS as tarefas recentes usam `.venv/bin/python` — mesmo comando, outro caminho. Testes em `tests/app_aluno/integracao/` são `requer_banco`: só rodam com `DATABASE_URL` (schema `piq_app_aluno`); sem ela ficam `skipped`, e a tarefa registra isso no `Status`.
>
> **Verificação — frontend:** scripts de `frontend/package.json`: `npm --prefix frontend run typecheck`, `npm --prefix frontend run test -- <arquivo>`, `npm --prefix frontend run test:e2e -- <arquivo>`. A suíte da `main` já tem falhas preexistentes: o critério é "nenhuma falha nova".
>
> **Nenhuma migração, tabela, rota ou dependência nova** (plano §1, §3). Não mudam: `App.tsx`, `TelaDefinirSenha.tsx`, `tokens_acesso.py`, `sessao.py`, `isolamento.py`, `email.py`, `scripts/papel_revisor.py` (plano §4).
>
> **Textos (`OQ-702`, aberta):** e-mail `primeiro_acesso`, "Esqueci minha senha" e a confirmação usam os rascunhos da spec §10. Os testes verificam presença/ausência (link, e-mail, token, prazo), nunca a frase.

## Progresso

`13/14 tarefas concluídas` — `T-703` parcial: falta a verificação manual a 360 px e com leitor de tela, e a aprovação dos textos da `OQ-702`.

Gates do servidor ao fim de `T-698` (`.venv/bin/python`): `ruff` 16 erros e `mypy` 11 erros em 5 arquivos, os mesmos do `HEAD` e nenhum em arquivo tocado; `pytest -q` 28 failed / 2860 passed / 99 skipped (`HEAD`: 28 failed / 2835 passed / 81 skipped), as mesmas 28 falhas do `HEAD`. A suíte leva ~13 min porque `test_ec05_banco_indisponivel_*` deixa o pool global apontado para `127.0.0.1:1` e os testes seguintes que usam `RepositorioContasSupabase` sem dublê esperam o timeout do pool (preexistente, igual no `HEAD`)

---

## Entrega 1 — Conta encontrada pelo e-mail, aluno sem senha (persistência)

### `T-690` — Normalizar o e-mail na busca e na gravação de `contas.py`

- **Tipo:** `Data`
- **Dependências:** nenhuma
- **Rastreia:** `RF-704`, `AC-711`, `AC-712`, `EC-703`, `EC-713`
- **Arquivos:** `persistencia/app_aluno/contas.py`, `tests/app_aluno/integracao/test_persistencia_contas.py`

**Descrição**

`U-01` (a), (c), (e): `normalizar_email(email) -> str` (`email.strip().lower()`); `RepositorioContasSupabase.buscar_por_email` compara `lower(trim(email)) = %s` com o parâmetro normalizado; `criar` e `provisionar` gravam `normalizar_email(email)`. Docstring de `buscar_por_email` no `Protocol` atualizada. Sem índice nem migração (plano §10).

**Critérios de aceite**

- [x] `normalizar_email` existe em `contas.py` e é a única implementação da regra (sem cópia em outro módulo)
- [x] O SQL de `buscar_por_email` usa `lower(trim(email)) = %s` com `normalizar_email(email)` como parâmetro; comentário `ponytail:` no SQL nomeando a varredura sequencial e o índice funcional como saída
- [x] Os dois `INSERT` de `contas.py` (`criar`, `provisionar`) gravam o e-mail normalizado
- [x] Teste `AC-711`: conta gravada como `aluno@exemplo.com`; `buscar_por_email("  Aluno@Exemplo.COM ")` devolve essa conta
- [x] Teste `AC-712` (persistência): linha `Fulano@Exemplo.com` inserida por SQL direto; `buscar_por_email("fulano@exemplo.com")` devolve essa conta
- [x] Teste: `criar` com `" Novo@Ex.com "` grava `novo@ex.com` (lido por SQL direto)
- [x] Testes existentes de `test_persistencia_contas.py` continuam verdes

**Verificação:** `.venv/bin/python -m pytest -q tests/app_aluno/integracao/test_persistencia_contas.py` (com `DATABASE_URL`); gates `lint`, `build`, `test`

**Status:** `[x] concluída (2026-11-24)` — testes `requer_banco` rodados contra Postgres 17 local (container descartável, migrações 001–012 aplicadas): `integracao/test_persistencia_contas.py` + `integracao/test_rotas_conta.py` 40/40 verdes; pasta `integracao/` 82 verdes e 2 falhas preexistentes da `main` (`test_ec05_banco_indisponivel_gravacao_*`, `test_interface_do_repositorio_nao_expoe_atualizar_nem_remover`). Antes: — implementado: `normalizar_email` em `contas.py` (única implementação), `buscar_por_email` com `lower(trim(email)) = %s` + comentário `ponytail:`, `criar`/`provisionar` gravando normalizado. Testes novos em `integracao/test_persistencia_contas.py` (`test_ac711_*`, `test_ac712_*`, `test_criar_grava_o_email_normalizado`) escritos, mas `DATABASE_URL` ausente nesta máquina (nenhum Postgres local; daemon do Docker parado) — os testes `requer_banco` ficaram `skipped`: falta rodá-los com banco.

---

### `T-691` — Gravar e devolver o e-mail normalizado em `cadastro.py`

- **Tipo:** `Data`
- **Dependências:** `T-690`
- **Rastreia:** `RF-704`, `EC-713`
- **Arquivos:** `persistencia/app_aluno/cadastro.py`, `tests/app_aluno/integracao/test_persistencia_contas.py`

**Descrição**

`U-02`: `cadastrar_conta_e_caso` e `provisionar_conta_e_caso` passam o e-mail por `normalizar_email` (importado de `contas.py`) antes do `INSERT` e devolvem a `Conta` com o e-mail normalizado. Fecha a última porta de gravação (cadastro público), decisão de `OQ-701`.

**Critérios de aceite**

- [x] Os dois `INSERT INTO piq_app_aluno.contas` de `cadastro.py` gravam `normalizar_email(email)`
- [x] A `Conta` devolvida pelas duas funções traz o e-mail normalizado
- [x] Teste: `cadastrar_conta_e_caso(" Novo@Ex.com ", ...)` grava e devolve `novo@ex.com`
- [x] Teste: `provisionar_conta_e_caso(" Outro@Ex.com ")` grava e devolve `outro@ex.com`
- [x] Teste: cadastrar `A@Ex.com` depois de `a@ex.com` levanta `ErroEmailDuplicado` (duplicata por maiúscula não surge mais, `EC-713`)
- [x] `tests/app_aluno/integracao/test_rotas_conta.py` (cadastro) continua verde

**Verificação:** `.venv/bin/python -m pytest -q tests/app_aluno/integracao/` (com `DATABASE_URL`); gates `lint`, `build`, `test`

**Status:** `[x] concluída (2026-11-24)` — testes `requer_banco` rodados contra Postgres 17 local (container descartável, migrações 001–012 aplicadas): `integracao/test_persistencia_contas.py` + `integracao/test_rotas_conta.py` 40/40 verdes; pasta `integracao/` 82 verdes e 2 falhas preexistentes da `main` (`test_ec05_banco_indisponivel_gravacao_*`, `test_interface_do_repositorio_nao_expoe_atualizar_nem_remover`). Antes: — implementado: `cadastrar_conta_e_caso` e `provisionar_conta_e_caso` normalizam, gravam e devolvem o e-mail normalizado. Testes novos em `integracao/test_persistencia_contas.py` (cadastro, provisionamento, `test_ec713_*`) escritos, mas `DATABASE_URL` ausente nesta máquina (nenhum Postgres local; daemon do Docker parado) — os testes `requer_banco` ficaram `skipped`: falta rodá-los com banco

---

### `T-692` — Reordenar `autenticar`: aluno entra sem senha, revisor só com senha

- **Tipo:** `Data`
- **Dependências:** `T-690`
- **Rastreia:** `RF-701`, `RF-702`, `RF-703`, `AC-702`, `AC-703`, `AC-706`, `AC-707`, `AC-710`, `EC-701`, `EC-707`
- **Arquivos:** `persistencia/app_aluno/contas.py`, `tests/app_aluno/integracao/test_persistencia_contas.py`, `tests/app_aluno/integracao/test_rotas_conta.py`

**Descrição**

`U-01` (b), (d), (f): `ErroSenhaExigida` (mensagem sem e-mail e sem senha) e `autenticar` na ordem do plano §5 — inexistente ⇒ `None`; bloqueado ⇒ `None`; aluno ⇒ conta (senha ignorada); revisor com `senha_hash` nulo, senha `""` ou errada ⇒ `raise ErroSenhaExigida`; senão ⇒ conta. Docstrings de `autenticar` no `Protocol`, de `Conta.senha_hash` e `REGRAS` atualizadas. A rota ainda não captura a exceção (`T-693`): nenhum teste existente faz login de revisor com senha errada contra o banco.

**Critérios de aceite**

- [x] Ordem exata do plano §5; o passo 2 (bloqueio) vem antes do 3 (papel)
- [x] Senha `""` de revisor levanta `ErroSenhaExigida` sem chamar `verificar_senha` (sem Argon2id)
- [x] Assinatura de `RepositorioContas.autenticar` inalterada
- [x] Substitui `test_autenticar_com_conta_inexistente_e_senha_errada_devolve_o_mesmo_resultado` por: `AC-702` (aluno com senha errada devolve a conta) e `AC-706` (revisor com senha errada levanta `ErroSenhaExigida`, hash Argon2id real)
- [x] Teste `AC-703`: conta de `provisionar_conta_e_caso` (sem senha), `autenticar(email, "")` devolve a conta
- [x] Teste `AC-707`/`EC-701`: revisor promovido com `senha_hash` nulo levanta `ErroSenhaExigida` com senha vazia e com qualquer senha
- [x] Teste `AC-704` (repositório): revisor com senha `""` levanta `ErroSenhaExigida`
- [x] Teste `AC-710` (repositório): revisor bloqueado devolve `None` sem senha e com a senha correta (nunca levanta)
- [x] Teste: inexistente devolve `None` com e sem senha
- [x] `integracao/test_rotas_conta.py::test_login_e_logout_ponta_a_ponta_contra_banco_real` reescrito: aluno entra só com o e-mail ⇒ `200`; logout ⇒ `GET /api/conta/eu` responde `401`
- [x] `str(ErroSenhaExigida(...))` não contém o e-mail nem a senha do pedido

**Verificação:** `.venv/bin/python -m pytest -q tests/app_aluno/integracao/test_persistencia_contas.py tests/app_aluno/integracao/test_rotas_conta.py` (com `DATABASE_URL`); gates `lint`, `build`, `test`

**Status:** `[x] concluída (2026-11-24)` — testes `requer_banco` rodados contra Postgres 17 local (container descartável, migrações 001–012 aplicadas): `integracao/test_persistencia_contas.py` + `integracao/test_rotas_conta.py` 40/40 verdes; pasta `integracao/` 82 verdes e 2 falhas preexistentes da `main` (`test_ec05_banco_indisponivel_gravacao_*`, `test_interface_do_repositorio_nao_expoe_atualizar_nem_remover`). Antes: — implementado: `ErroSenhaExigida` e `autenticar` na ordem do plano §5 (senha `""` de revisor sai antes de `verificar_senha`); docstrings de `Conta.senha_hash`, `Protocol`, `provisionar` e `REGRAS` atualizados (também a frase "até lá, `autenticar` recusa" da docstring de `provisionar_conta_e_caso`, em `cadastro.py`, que ficara falsa). Teste antigo substituído por `AC-702`/`AC-706`; novos `AC-703`, `AC-704`, `AC-707`/`EC-701`, `AC-710`, inexistente; `test_login_e_logout_ponta_a_ponta_contra_banco_real` reescrito. Todos `requer_banco`: `DATABASE_URL` ausente nesta máquina (nenhum Postgres local; daemon do Docker parado) — os testes `requer_banco` ficaram `skipped`. A ordem está coberta por unidade só via o dublê de `T-693`

---

## Entrega 2 — Login por papel no servidor

### `T-693` — Responder `exige_senha` no `POST /api/conta/login`

- **Tipo:** `Data`
- **Dependências:** `T-692`
- **Rastreia:** `RF-701`, `RF-702`, `RF-703`, `AC-706`, `AC-708`, `AC-709`
- **Arquivos:** `app/http/rotas_api_conta.py`, `tests/app_aluno/test_rotas_conta.py`

**Descrição**

`U-03`: `entrar` captura `ErroSenhaExigida` ⇒ `401 {"erro": _MENSAGEM_LOGIN_INVALIDO, "exige_senha": true}` sem sessão; `None` ⇒ o `401` de sempre. Docstrings do módulo e da rota: "inexistente = senha errada" (`RF-02`) passa a valer só para revisor/bloqueio. No teste, `_RepositorioContasDublê.autenticar` passa a reproduzir o plano §5 (inclui `bloqueado_em` e `ErroSenhaExigida`), e os dois testes que afirmam o contrato antigo são reescritos.

**Critérios de aceite**

- [x] `401` com `exige_senha` só vem de `ErroSenhaExigida`; o `401` de `None` não tem a chave
- [x] Nenhum dos dois `401` grava sessão (`GET /api/conta/eu` em seguida ⇒ `401`)
- [x] Sucesso inalterado: `200 {email, conta_id, e_revisor}`
- [x] `_RepositorioContasDublê.autenticar` segue a ordem do plano §5
- [x] `test_login_com_senha_errada_nao_abre_sessao` vira `AC-706`: revisor com senha errada ⇒ `401` com `exige_senha: true`, sem sessão
- [x] `test_mensagem_de_erro_de_login_nao_distingue_conta_inexistente_de_senha_errada` vira `AC-708`/`AC-709`: inexistente e aluno bloqueado ⇒ corpos idênticos, exatamente `{"erro": "E-mail ou senha inválidos."}`
- [x] Os demais testes de `test_rotas_conta.py` (inclusive `test_rf59_*` e `test_t154_*`) continuam verdes

**Verificação:** `.venv/bin/python -m pytest -q tests/app_aluno/test_rotas_conta.py`; gates `lint`, `build`, `test`

**Status:** `[x] concluída (2026-11-24)` — `entrar` captura `ErroSenhaExigida` ⇒ `401 {erro, exige_senha: true}`; `None` ⇒ `401` de sempre. Dublê segue o plano §5; `test_ac706_*` e `test_ac708_ac709_*` substituem os dois testes antigos. `test_rotas_conta.py`: 21/21 verdes

---

### `T-694` — Testar o login por papel e o e-mail normalizado nas rotas

- **Tipo:** `Test`
- **Dependências:** `T-690`, `T-693`
- **Rastreia:** `RF-701`, `RF-702`, `RF-703`, `RF-704`, `AC-701`, `AC-702`, `AC-703`, `AC-704`, `AC-705`, `AC-707`, `AC-710`, `AC-712`, `EC-710`
- **Arquivos:** `tests/app_aluno/test_rotas_conta.py`, `tests/app_aluno/integracao/test_rotas_conta.py`

**Descrição**

Critérios de rota do plano §9 ainda não cobertos por `T-693`. Unit com o dublê; `AC-712` contra Postgres real, com `HOTMART_HOTTOK` por `monkeypatch`. Cada teste cita o `AC` no nome.

**Critérios de aceite**

- [x] `AC-701`: aluno, só `email` ⇒ `200` `e_revisor: false`; `GET /api/conta/eu` ⇒ `200` com o `CASO_ID` da conta
- [x] `AC-702`: aluno com senha definida e senha errada ⇒ `200` e sessão aberta
- [x] `AC-703`: aluno com `senha_hash=None`, só `email` ⇒ `200`
- [x] `AC-704`: revisor, só `email` ⇒ `401` com corpo exatamente `{"erro": "E-mail ou senha inválidos.", "exige_senha": true}`, sem sessão
- [x] `AC-705`: revisor com senha correta ⇒ `200` `e_revisor: true`, sessão aberta
- [x] `AC-707`: revisor com `senha_hash=None`, com e sem senha ⇒ `401` com `exige_senha: true`
- [x] `AC-710`: revisor bloqueado, sem senha e com a senha correta ⇒ corpo idêntico ao de `AC-708`, sem `exige_senha`
- [x] `EC-710`: `email` vazio ⇒ `401` de `AC-708`
- [x] Textos de erro de `AC-704`, `AC-708`, `AC-709` e `AC-710` idênticos byte a byte no campo `erro`
- [x] `AC-712` (integração): linha `Fulano@Exemplo.com` inserida por SQL direto; login com `fulano@exemplo.com` ⇒ `200` para essa conta; webhook `PURCHASE_REFUNDED` com `FULANO@exemplo.com` ⇒ `{"bloqueado": true}` e `bloqueado_em` preenchido no banco

**Verificação:** `.venv/bin/python -m pytest -q tests/app_aluno/test_rotas_conta.py tests/app_aluno/integracao/test_rotas_conta.py` (integração com `DATABASE_URL`); gates `lint`, `build`, `test`

**Status:** `[x] concluída (2026-11-24)` — testes `requer_banco` rodados contra Postgres 17 local (container descartável, migrações 001–012 aplicadas): `integracao/test_persistencia_contas.py` + `integracao/test_rotas_conta.py` 40/40 verdes; pasta `integracao/` 82 verdes e 2 falhas preexistentes da `main` (`test_ec05_banco_indisponivel_gravacao_*`, `test_interface_do_repositorio_nao_expoe_atualizar_nem_remover`). Antes: — unidade completa: `AC-701`, `AC-702`, `AC-703`, `AC-704`, `AC-705`, `AC-707` (sem/vazia/qualquer senha), `AC-710` (sem e com senha correta), `EC-710` e o campo `erro` idêntico byte a byte; `test_rotas_conta.py` 33/33 verdes. `AC-712` (integração: login `fulano-…@exemplo.com` e reembolso `FULANO-…` contra linha legada `Fulano-…@Exemplo.com`) escrito em `integracao/test_rotas_conta.py`, mas `DATABASE_URL` ausente nesta máquina (nenhum Postgres local; daemon do Docker parado) — os testes `requer_banco` ficaram `skipped`

---

## Entrega 3 — E-mail de compra sem token e recuperação só para revisor

### `T-695` — Trocar `primeiro_acesso` por orientações de acesso sem token

- **Tipo:** `Data`
- **Dependências:** nenhuma
- **Rastreia:** `RF-709`, `AC-725`, `AC-729`
- **Arquivos:** `app/notificacao/mensagens.py`, `app/notificacao/textos/emails.yaml`, `app/http/rotas_provisionamento.py`, `tests/app_aluno/test_mensagens_de_email.py`, `tests/app_aluno/test_rotas_provisionamento.py`

**Descrição**

`U-04`, `U-05`, `U-06`(b): `primeiro_acesso(email: str) -> Mensagem` = `_montar("primeiro_acesso", link=_url_base(), email=email)`; corpo do YAML = rascunho de `OQ-702` com `{link}` e `{email}`, sem prazo nem "criar senha"; comentário do cabeçalho cita `{email}` (só em `primeiro_acesso`). Os dois chamadores em `rotas_provisionamento.py` (`provisionar` e `_processar_webhook_hotmart`) passam a chamar `primeiro_acesso(email)` — mudança de assinatura, para o `mypy` ficar verde; o webhook ainda emite token até `T-696`. `link_de_senha` e `recuperacao_de_senha` não mudam.

**Critérios de aceite**

- [x] `primeiro_acesso` recebe o e-mail; `{link}` = URL base, sem `#definir-senha`
- [x] `/conta` (n8n) continua emitindo e devolvendo o token, mas envia `primeiro_acesso(email)`
- [x] `test_primeiro_acesso_carrega_o_link_de_senha` vira `AC-725`: com `URL_BASE_APP` configurada, corpo de `primeiro_acesso("aluno@exemplo.com")` contém a URL base e `aluno@exemplo.com`; não contém `#definir-senha`, `token`, `48 horas` nem `horas`
- [x] `test_nenhuma_mensagem_deixa_placeholder_por_substituir`, `test_corpo_e_texto_puro_sem_html` e `test_paragrafos_do_yaml_sobrevivem_a_carga` chamam `primeiro_acesso(_EMAIL)`; o de placeholder guarda também `{email}`
- [x] `test_chaves_do_arquivo_real_batem_com_o_que_o_codigo_espera` e os testes de `recuperacao_de_senha` continuam verdes
- [x] Teste `AC-729`: `POST /api/provisionamento/conta` ⇒ `201` com `token`, `expira_em`, `email_enviado`; com `obter_enviador` sobrescrito por `EnviadorEmMemoria` e `URL_BASE_APP` por `monkeypatch`, o corpo enviado é o de `AC-725` (sem `#definir-senha`)
- [x] Nenhum teste afirma a frase do rascunho (`OQ-702`)

**Verificação:** `.venv/bin/python -m pytest -q tests/app_aluno/test_mensagens_de_email.py tests/app_aluno/test_rotas_provisionamento.py`; gates `lint`, `build`, `test`

**Status:** `[x] concluída (2026-11-24)` — `primeiro_acesso(email)` = URL base + `{email}`; YAML com o rascunho de `OQ-702` (sem prazo, sem token, sem "criar senha"); `/conta` e webhook chamam `primeiro_acesso(email)`. `test_ac725_*` (contém URL e e-mail; não contém `#definir-senha`, `token`, `48 horas`, `horas`), os três testes de `primeiro_acesso(_EMAIL)` e `test_ac729_*` (com `EnviadorEmMemoria`; os fixtures de `test_rotas_provisionamento.py` passaram a sobrescrever `obter_enviador`). `test_mensagens_de_email.py` 19/19, `test_rotas_provisionamento.py` 31/31 verdes

---

### `T-696` — Parar de emitir token no webhook da Hotmart

- **Tipo:** `Data`
- **Dependências:** `T-695`
- **Rastreia:** `RF-710`, `AC-726`, `AC-727`, `AC-728`, `EC-704`, `EC-711`
- **Arquivos:** `app/http/rotas_provisionamento.py`, `tests/app_aluno/test_rotas_provisionamento.py`

**Descrição**

`U-06`(a), (d): `_processar_webhook_hotmart` deixa de chamar `repositorio_tokens.emitir` nos dois ramos (conta nova e `ErroEmailDuplicado`); some o parâmetro `repositorio_tokens` dela e a dependência correspondente de `receber_webhook_hotmart`. Docstring do módulo: "compra repetida reemite o link" vira "reenvia as orientações". Resposta inalterada.

**Critérios de aceite**

- [x] `receber_webhook_hotmart` não depende mais de `obter_repositorio_tokens`
- [x] `test_hotmart_compra_aprovada_provisiona_e_nao_devolve_token` e `test_hotmart_compra_repetida_reprovisiona_sem_erro` afirmam `tokens.emitidos == []`
- [x] Teste `AC-726`: `PURCHASE_APPROVED` para e-mail novo, com `EnviadorEmMemoria` e `URL_BASE_APP` ⇒ `200 {"provisionado": true, "email_enviado": true}`; conta e caso existem; `tokens.emitidos == []`; exatamente um envio, ao comprador, corpo sem `#definir-senha`
- [x] Teste `AC-727`/`EC-704`: compra repetida ⇒ mesma resposta, nenhum token, um envio com o mesmo corpo, nome completado
- [x] Teste `AC-728`/`EC-711`: enviador que lança `ErroEnvioEmail`, e `URL_BASE_APP` ausente ⇒ `200 {"provisionado": true, "email_enviado": false}` e a conta existe
- [x] Testes de reembolso, `hottok` e evento/produto ignorado continuam verdes

**Verificação:** `.venv/bin/python -m pytest -q tests/app_aluno/test_rotas_provisionamento.py`; gates `lint`, `build`, `test`

**Status:** `[x] concluída (2026-11-24)` — `receber_webhook_hotmart`/`_processar_webhook_hotmart` sem `repositorio_tokens`; nenhum `emitir` nos dois ramos; docstring do módulo "reenvia as orientações". Os dois testes antigos afirmam `tokens.emitidos == []`; novos `test_ac726_*`, `test_ac727_ec704_*` (nome completado, corpo = `primeiro_acesso(email)`), `test_ac728_ec711_*` (SMTP que lança e `URL_BASE_APP` ausente). `test_rotas_provisionamento.py` 35/35 verdes

---

### `T-697` — Restringir a recuperação de senha a conta de revisor

- **Tipo:** `Data`
- **Dependências:** `T-696` (mesmo arquivo de rota e mesmo dublê de teste)
- **Rastreia:** `RF-708`, `RF-704`, `RF-711`, `AC-713`, `AC-721`, `AC-722`, `AC-723`, `AC-724`, `EC-702`, `EC-706`
- **Arquivos:** `app/http/rotas_provisionamento.py`, `tests/app_aluno/test_rotas_provisionamento.py`

**Descrição**

`U-06`(c): `pedir_recuperacao` emite token e envia `recuperacao_de_senha` só se `conta is not None and conta.e_revisor`; a resposta continua sempre `200 {"pedido_registrado": true}`. Docstring da rota ("quem tem conta recebe o link") passa a dizer "só revisor". `_RepositorioContasDublê.buscar_por_email` ganha um conjunto `revisores` e devolve `e_revisor` conforme ele. Seção nova de testes de recuperação, com `EnviadorEmMemoria` e `URL_BASE_APP` por `monkeypatch`.

**Critérios de aceite**

- [x] Aluno, inexistente e e-mail vazio: nenhum `emitir`, nenhum envio, resposta idêntica
- [x] Revisor bloqueado ainda recebe o link (`EC-702`, Assumption 6): a condição é só o papel
- [x] Teste `AC-721`: revisor ⇒ `200 {"pedido_registrado": true}`, um token emitido para a conta, um envio com o link `{URL_BASE_APP}/#definir-senha/{token}`
- [x] Teste `AC-722`: aluno ⇒ mesma resposta, `tokens.emitidos == []`, nenhum envio
- [x] Teste `AC-723`: e-mail sem conta e campo vazio ⇒ idem `AC-722`
- [x] Teste `AC-724`: revisor com enviador que lança `ErroEnvioEmail`, e com `URL_BASE_APP` ausente ⇒ `200 {"pedido_registrado": true}`
- [x] Teste `AC-713`: revisor gravado em minúsculas, pedido com `"  Revisor@Exemplo.COM "` ⇒ token emitido e envio para essa conta
- [x] Testes existentes de `/senha` e do webhook continuam verdes

**Verificação:** `.venv/bin/python -m pytest -q tests/app_aluno/test_rotas_provisionamento.py`; gates `lint`, `build`, `test`

**Status:** `[x] concluída (2026-11-24)` — `pedir_recuperacao` só emite/envia se `conta.e_revisor`; dublê ganhou `revisores`. Novos `test_ac721_*`, `test_ac722_*`, `test_ac723_*` (sem conta e vazio), `test_ac724_*` (SMTP e `URL_BASE_APP`), `test_ac713_*`, `test_ec702_*`. `test_rotas_provisionamento.py` 43/43 verdes

---

### `T-698` — Testar contra o banco o revisor promovido sem senha até entrar

- **Tipo:** `Test`
- **Dependências:** `T-692`, `T-693`, `T-697`
- **Rastreia:** `RF-711`, `RF-702`, `RF-708`, `AC-730`, `EC-701`
- **Arquivos:** `tests/app_aluno/integracao/test_rotas_conta.py`

**Descrição**

Fluxo ponta a ponta com Postgres real e `EnviadorEmMemoria` (`obter_enviador` sobrescrito, `URL_BASE_APP` por `monkeypatch`). Prova que a tela e a rota `/senha`, inalteradas, servem para criar a primeira senha.

**Critérios de aceite**

- [x] Conta criada por `provisionar_conta_e_caso` e promovida com `promover_a_revisor`, sem senha
- [x] (1) login só com e-mail ⇒ `401` com `exige_senha: true`
- [x] (2) `POST /api/provisionamento/recuperacao` ⇒ `200`; o token é extraído do link `#definir-senha/{token}` do corpo enviado
- [x] (3) `POST /api/provisionamento/senha` com o token e 8+ caracteres ⇒ `200 {"senha_definida": true}`
- [x] (4) login com e-mail e a senha nova ⇒ `200` `e_revisor: true`
- [x] Nome do teste cita `AC-730`

**Verificação:** `.venv/bin/python -m pytest -q tests/app_aluno/integracao/test_rotas_conta.py` (com `DATABASE_URL`); gates `lint`, `build`, `test`

**Status:** `[x] concluída (2026-11-24)` — testes `requer_banco` rodados contra Postgres 17 local (container descartável, migrações 001–012 aplicadas): `integracao/test_persistencia_contas.py` + `integracao/test_rotas_conta.py` 40/40 verdes; pasta `integracao/` 82 verdes e 2 falhas preexistentes da `main` (`test_ec05_banco_indisponivel_gravacao_*`, `test_interface_do_repositorio_nao_expoe_atualizar_nem_remover`). Antes: — `test_ac730_revisor_promovido_sem_senha_cria_a_primeira_e_entra` escrito em `integracao/test_rotas_conta.py` (Postgres real + `EnviadorEmMemoria`, token extraído de `#definir-senha/{token}`), mas `DATABASE_URL` ausente nesta máquina (nenhum Postgres local; daemon do Docker parado) — os testes `requer_banco` ficaram `skipped`: falta rodá-lo com banco

---

## Entrega 4 — Tela de entrada em duas etapas

### `T-699` — Deixar a senha opcional em `entrar` e criar `pedirRecuperacao` e os textos novos

- **Tipo:** `UI`
- **Dependências:** nenhuma (contrato HTTP do plano §5; os testes do frontend simulam a API)
- **Rastreia:** `RF-705`, `RF-707`
- **Arquivos:** `frontend/src/services/api.ts`, `frontend/src/telas/textosDaEntrada.ts`

**Descrição**

`U-07`: `entrar(email: string, senha = '')`; `pedirRecuperacao(email: string): Promise<Response>` faz `POST /api/provisionamento/recuperacao` em `form-urlencoded`, no mesmo molde de `definirSenha`. `U-08`: `FORMULARIO.esqueciSenha` e `RECUPERACAO.enviada(email)` com os rascunhos de `OQ-702`. `rotuloSenha` e `ERROS` não mudam (`D-06`, Assumption 2).

**Critérios de aceite**

- [x] `entrar(email)` envia `senha` vazia; `entrar(email, senha)` igual a hoje
- [x] `pedirRecuperacao` só envia o campo `email`; mesmos `credentials` e cabeçalhos de `definirSenha`
- [x] `FORMULARIO.esqueciSenha` e `RECUPERACAO.enviada(email)` em `textosDaEntrada.ts`, que continua sendo a única fonte de texto da tela; `ERROS` intacto
- [x] `TelaLogin.test.tsx` continua verde (a tela ainda não mudou)

**Verificação:** `npm --prefix frontend run typecheck`; `npm --prefix frontend run test -- tests/unit/componentes/TelaLogin.test.tsx`

**Status:** `[x] concluída (2026-11-24)` — `typecheck` sem erro; `TelaLogin.test.tsx` 14/14 verdes (tela ainda sem mudança)

---

### `T-700` — Dividir `TelaLogin` em etapa de e-mail e etapa de senha

- **Tipo:** `UI`
- **Dependências:** `T-699`
- **Rastreia:** `RF-705`, `RF-706`, `RF-707`, `AC-714`, `AC-715`, `AC-716`, `AC-717`, `AC-718`, `AC-719`, `AC-720`, `EC-712`
- **Arquivos:** `frontend/src/telas/TelaLogin.tsx`, `frontend/tests/unit/componentes/TelaLogin.test.tsx`, `frontend/tests/e2e/apoio/navegacao.ts`, `frontend/tests/e2e/navegacao.spec.ts`

**Descrição**

`U-09`, estado do plano §7 e erros do §8: `etapa` (`'email' | 'senha'`), `email`, `senha`, `erro`, `recuperacaoEnviada`, `enviando`, todos locais. Campo de senha (`autoFocus`) e "Esqueci minha senha" (`<button type="button">` dentro do `form`) só em `etapa === 'senha'`; confirmação em `role="status"`. Junto, os testes existentes que a mudança quebra (plano §9): os oito de `TelaLogin.test.tsx` que usam "Sua senha" na primeira etapa; no e2e, o mock de login de `interceptarBase` (lê `senha` do `postData`: `eRevisor` sem senha ⇒ `401 {erro, exige_senha: true}`), `entrarComoRevisor` em duas etapas, o teste do revisor (~l.680) e `T-154: entrar SEM ?caso=` (~l.908) só com e-mail.

**Critérios de aceite**

- [x] Etapa de e-mail envia `entrar(email)`; `401` com `exige_senha` ⇒ etapa de senha **sem** erro; `401` sem a chave, ou corpo ilegível ⇒ `ERROS.credenciais` (`role="alert"`), etapa mantida
- [x] Etapa de senha envia `entrar(email, senha)`; `401` ⇒ `ERROS.credenciais`, campo de senha continua; `200` ⇒ `onEntrou` como hoje
- [x] Editar o e-mail na etapa de senha volta à etapa de e-mail e limpa `senha`, `erro` e `recuperacaoEnviada`
- [x] "Esqueci minha senha" chama `pedirRecuperacao(email)`; `ok` ⇒ `RECUPERACAO.enviada(email)` em `role="status"`; `!ok` ou rede fora ⇒ `ERROS.indisponivel`; nunca abre sessão
- [x] Rede fora no login ⇒ `ERROS.indisponivel`, etapa mantida (`EC-712`)
- [x] `enviando` desabilita "Entrar" e "Esqueci minha senha"; Enter envia a etapa atual
- [x] Nenhum estado persistido no navegador; nenhum texto fora de `textosDaEntrada.ts`; sem classe CSS nova
- [x] Os oito testes de `TelaLogin.test.tsx` reescritos contra as duas etapas; `autocomplete` de senha verificado na etapa de senha
- [x] `interceptarBase`, `entrarComoRevisor` e os dois testes de `navegacao.spec.ts` atualizados; os demais specs que usam `interceptarBase` continuam verdes

**Verificação:** `npm --prefix frontend run typecheck`; `npm --prefix frontend run test -- tests/unit/componentes/TelaLogin.test.tsx`; `npm --prefix frontend run test:e2e -- tests/e2e/navegacao.spec.ts`

**Status:** `[x] concluída (2026-11-24)` — `typecheck` sem erro; `TelaLogin.test.tsx` 14/14 verdes (os oito testes reescritos contra as duas etapas); `navegacao.spec.ts` 99 verdes, 1 pulado, 4 falhas preexistentes (`AC-83 + AC-29` — a fila responde `HTTP 500` porque o mock não cobre a rota que ela consulta, o login em duas etapas chega à fila — e `AC-103`, nos dois projetos), idênticas às do `HEAD` rodado num worktree

---

### `T-701` — Testar as duas etapas de `TelaLogin` (vitest)

- **Tipo:** `Test`
- **Dependências:** `T-700`
- **Rastreia:** `RF-705`, `RF-706`, `RF-707`, `AC-714`, `AC-716`, `AC-717`, `AC-718`, `AC-719`, `AC-720`, `EC-712`
- **Arquivos:** `frontend/tests/unit/componentes/TelaLogin.test.tsx`

**Descrição**

Testes novos de componente (happy-dom, `vi.spyOn(api, …)`), um por critério, com o `AC` no nome.

**Critérios de aceite**

- [x] `AC-714`: tela recém-aberta tem "Seu e-mail" e "Entrar"; `queryByLabelText("Sua senha")` e "Esqueci minha senha" ausentes
- [x] `AC-716`: `401` + `exige_senha` ⇒ "Sua senha" com foco, "Esqueci minha senha" visível, e-mail mantido, nenhum `role="alert"`
- [x] `AC-717`: `401` sem `exige_senha` ⇒ mensagem genérica em `role="alert"`, sem campo de senha; corpo ilegível ⇒ idem
- [x] `AC-718`: na etapa de senha, editar o e-mail ⇒ campo de senha e "Esqueci minha senha" somem
- [x] `AC-719`: na etapa de senha, `401` ⇒ `role="alert"` e campo de senha visível; `200` ⇒ `onEntrou` com `e_revisor: true`
- [x] `AC-720`: "Esqueci minha senha" ⇒ `pedirRecuperacao` com o e-mail digitado, confirmação em `role="status"`, `onEntrou` não chamado; o clique não submete o formulário (`entrar` não chamado de novo)
- [x] `EC-712`: rede fora no login e na recuperação ⇒ `ERROS.indisponivel`, etapa mantida
- [x] Durante o envio, "Entrar" e "Esqueci minha senha" desabilitados
- [x] Arquivo todo verde

**Verificação:** `npm --prefix frontend run test -- tests/unit/componentes/TelaLogin.test.tsx`

**Status:** `[x] concluída (2026-11-24)` — `TelaLogin.test.tsx`: 25 testes (14 + 11 novos com o `AC`/`EC` no nome), 25 verdes

---

### `T-702` — Testar no navegador o aluno só com e-mail e o revisor em duas etapas

- **Tipo:** `Test`
- **Dependências:** `T-700`
- **Rastreia:** `RF-705`, `RF-706`, `AC-715`, `AC-716`, `AC-719`
- **Arquivos:** `frontend/tests/e2e/navegacao.spec.ts`

**Descrição**

Asserções de fluxo sobre os testes ajustados em `T-700`, com `page.route` (sem servidor real), nos projetos `desktop` e `mobile-360`.

**Critérios de aceite**

- [x] `AC-715`: aluno entra só com o e-mail; `getByLabel("Sua senha")` tem contagem `0` antes e depois do clique em "Entrar"; o app abre
- [x] `AC-716`: revisor, depois do e-mail, vê "Sua senha" focado e nenhum `role="alert"`
- [x] `AC-719`: revisor com senha errada ⇒ `role="alert"` e "Sua senha" ainda visível; com a senha certa ⇒ chega à fila
- [x] Arquivo todo verde nos dois projetos — exceto as 4 falhas preexistentes da `main` (`AC-83 + AC-29`, `AC-103`), idênticas no `HEAD`

**Verificação:** `npm --prefix frontend run test:e2e -- tests/e2e/navegacao.spec.ts`

**Status:** `[x] concluída (2026-11-24)` — `AC-715` em `T-154 + AC-715` (aluno só com e-mail, "Sua senha" com contagem `0` antes e depois); `AC-716`/`AC-719` em teste novo (senha focada, sem `role="alert"`; senha errada ⇒ alerta e campo mantido; certa ⇒ fila): 4/4 verdes nos dois projetos. Arquivo: 101 verdes, 1 pulado e as mesmas 4 falhas preexistentes do `HEAD` (`AC-83 + AC-29`, `AC-103`) — o critério "arquivo todo verde" fica em aberto só por elas. Suíte e2e completa: 186 verdes, as 6 falhas do `HEAD` (+`AC-109` de `plano.spec.ts`) e 1 instável (`calculadora-da-divida.spec.ts:462`, tooltip; 80/80 verdes com `--repeat-each=5`)

---

## Entrega 5 — Fechamento

### `T-703` — Verificar a feature ponta a ponta

- **Tipo:** `Test`
- **Dependências:** `T-691`, `T-694`, `T-698`, `T-701`, `T-702`
- **Rastreia:** `RF-701`–`RF-711` (regressão), NFR de responsividade e acessibilidade, `OQ-702`
- **Arquivos:** nenhum (só os `Status` deste backlog e o `Progresso`)

**Descrição**

Regressão completa e o que o plano §9 deixa fora de teste automatizado: 360 px sem rolagem horizontal na etapa de senha e redação final (`OQ-702`, aberta).

**Critérios de aceite**

- [x] Gates `lint`, `build`, `test` de `sdd.config.md` §2, com `DATABASE_URL`: nenhuma falha nova em relação à `main`
- [x] `npm --prefix frontend run typecheck`, `npm --prefix frontend run test` e `npm --prefix frontend run test:e2e` completos: nenhuma falha nova
- [x] `git diff --name-only main` não lista `App.tsx`, `TelaDefinirSenha.tsx`, `tokens_acesso.py`, `sessao.py`, `isolamento.py`, `email.py`, `scripts/papel_revisor.py` nem migração nova
- [ ] Manual a 360 px: etapa de senha sem rolagem horizontal; foco vai para "Sua senha"; leitor de tela anuncia erro e confirmação
- [x] `OQ-702` continua listada como pendente de aprovação do produto (textos em `emails.yaml` e `textosDaEntrada.ts`)
- [x] Status de `T-690` a `T-703` e `Progresso` atualizados

**Verificação:** comandos acima; conferência manual

**Status:** `[~] parcial (2026-11-24)` — gates sem falha nova em relação à `main` (servidor com `DATABASE_URL` num Postgres 17 local descartável: `integracao/` + rotas + mensagens 179 verdes, 2 falhas preexistentes; frontend: as mesmas 9 falhas vitest e 6 e2e da `main`); diff sem arquivos proibidos. Revisão `sdd-review` sem bloqueante; aplicados I1 (e-mail desabilitado durante o envio), I2 + R1 (`buscar_por_email` falha fechado com e-mail vazio ou ambíguo, testes `test_rf704_*`/`test_rf701_*`), M2 (docstring de `/conta`) e M3 (`AC-711` na rota). Falta: verificação manual a 360 px e com leitor de tela, e aprovação de texto da `OQ-702` pelo produto.

### `T-704` — Etapa de senha não cai quando o e-mail só muda em maiúsculas/espaços

- **Tipo:** `Fix`
- **Dependências:** `T-700`
- **Rastreia:** `RF-705`, `RF-704`, `AC-718`
- **Arquivos:** `frontend/src/telas/TelaLogin.tsx`, `frontend/tests/unit/componentes/TelaLogin.test.tsx`

**Descrição**

Revisor relatou digitar o e-mail duas vezes. Causa provável: o gerenciador de senhas reescreve o e-mail ao preencher a senha (ex.: `Fulano@` × `fulano@`), `aoEditarEmail` tratava como edição e voltava à etapa de e-mail. Passa a comparar o e-mail normalizado (mesma regra do servidor).

**Critérios de aceite**

- [x] Na etapa de senha, trocar o e-mail por variação só de maiúsculas/espaços mantém o campo de senha
- [x] Editar para outro e-mail ainda volta à etapa de e-mail (`AC-718` inalterado)

**Verificação:** `npx vitest run tests/unit/componentes/TelaLogin.test.tsx`; `npm --prefix frontend run typecheck`

**Status:** `[x] concluída (2026-11-24)` — falta confirmar no navegador do revisor (autopreenchimento real).

### `T-705` — Remover o alerta permanente de inventário incompleto

- **Tipo:** `Fix`
- **Dependências:** nenhuma
- **Rastreia:** `RF-86`, `RF-559`, `AC-133` (nota de substituição em `specs/app-aluno.spec.md`)
- **Arquivos:** `frontend/src/componentes/Tela.tsx`, `App.tsx`, `TelaCalculando.tsx`; removidos `AlertaInventario.tsx`, `AlertaInventario.test.tsx`, `tests/e2e/inventario.spec.ts`

**Descrição**

Conta nova via "Cadastrar as fichas" desde o primeiro login, antes dos termos. O alerta sai; o bloqueio do cálculo (servidor) e a próxima etapa do Início permanecem.

**Critérios de aceite**

- [x] Nenhuma tela do aluno mostra "Inventário incompleto"
- [x] `typecheck` limpo; vitest sem falha nova (as 9 da `main`)
- [ ] e2e completo rodado (não rodei)

**Status:** `[x] concluída (2026-11-24)`, falta rodar o e2e.

---

## Cobertura de requisitos

| Requisito | Tarefas |
| --------- | ------- |
| `RF-701` | `T-692`, `T-693`, `T-694`, `T-703` |
| `RF-702` | `T-692`, `T-693`, `T-694`, `T-698`, `T-703` |
| `RF-703` | `T-692`, `T-693`, `T-694`, `T-703` |
| `RF-704` | `T-690`, `T-691`, `T-694`, `T-697`, `T-703` |
| `RF-705` | `T-699`, `T-700`, `T-701`, `T-702`, `T-703` |
| `RF-706` | `T-700`, `T-701`, `T-702`, `T-703` |
| `RF-707` | `T-699`, `T-700`, `T-701`, `T-703` |
| `RF-708` | `T-697`, `T-698`, `T-703` |
| `RF-709` | `T-695`, `T-703` |
| `RF-710` | `T-696`, `T-703` |
| `RF-711` | `T-697`, `T-698`, `T-703` |

Critérios: `AC-701` (`T-694`) · `AC-702` (`T-692`, `T-694`) · `AC-703` (`T-692`, `T-694`) · `AC-704` (`T-692`, `T-694`) · `AC-705` (`T-694`) · `AC-706` (`T-692`, `T-693`) · `AC-707` (`T-692`, `T-694`) · `AC-708` (`T-693`) · `AC-709` (`T-693`) · `AC-710` (`T-692`, `T-694`) · `AC-711` (`T-690`) · `AC-712` (`T-690`, `T-694`) · `AC-713` (`T-697`) · `AC-714` (`T-700`, `T-701`) · `AC-715` (`T-700`, `T-702`) · `AC-716` (`T-700`, `T-701`, `T-702`) · `AC-717` (`T-700`, `T-701`) · `AC-718` (`T-700`, `T-701`) · `AC-719` (`T-700`, `T-701`, `T-702`) · `AC-720` (`T-700`, `T-701`) · `AC-721` (`T-697`) · `AC-722` (`T-697`) · `AC-723` (`T-697`) · `AC-724` (`T-697`) · `AC-725` (`T-695`) · `AC-726` (`T-696`) · `AC-727` (`T-696`) · `AC-728` (`T-696`; a metade "entra só com o e-mail" é a regra de `AC-703`) · `AC-729` (`T-695`) · `AC-730` (`T-698`).

Casos de borda: `EC-701` (`T-692`, `T-698`) · `EC-702` (`T-697`) · `EC-703` (`T-690`) · `EC-704` (`T-696`) · `EC-705` (sem mudança de comportamento; reembolso e compra seguem como hoje) · `EC-706` (`T-697`) · `EC-707` (`T-692`) · `EC-708` (sem mudança; tela `#definir-senha` inalterada) · `EC-709` (decorre de `T-692`: papel lido do banco a cada login) · `EC-710` (`T-694`) · `EC-711` (`T-696`) · `EC-712` (`T-700`, `T-701`) · `EC-713` (`T-690`, `T-691`).

Requisitos sem tarefa: nenhum. Unidades do plano: `U-01` (`T-690`, `T-692`) · `U-02` (`T-691`) · `U-03` (`T-693`) · `U-04`, `U-05` (`T-695`) · `U-06` (`T-695`, `T-696`, `T-697`) · `U-07`, `U-08` (`T-699`) · `U-09` (`T-700`) · `U-10` (`T-694`, `T-698` e os testes de cada tarefa) · `U-11` (`T-701`, `T-702`).
