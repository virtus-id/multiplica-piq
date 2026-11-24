# Plano: acesso do aluno sem senha

Rastreia a spec [`specs/acesso-sem-senha.spec.md`](../specs/acesso-sem-senha.spec.md).

| Campo  | Valor |
| ------ | ----- |
| Slug   | `acesso-sem-senha` |
| Status | `rascunho` |
| Data   | 2026-11-24 |

## 1. Estratégia

Mudança mínima sobre o que já existe: **nenhuma migração, nenhuma tabela, nenhuma rota nova**.
Três fatias, nesta ordem:

- **(A) Persistência:** a regra "aluno entra sem senha, revisor só com senha" vive em
  `RepositorioContasSupabase.autenticar`; a comparação de e-mail sem maiúsculas/espaços vive em
  `buscar_por_email`; a gravação de conta normaliza o e-mail. Todos os chamadores (login,
  recuperação, webhook de compra e de reembolso) passam por esses dois pontos, então a correção
  é feita uma vez (`RF-701`–`RF-704`).
- **(B) Rotas e e-mail:** o login devolve `exige_senha`; a recuperação só age para revisor; o
  webhook para de emitir token; `primeiro_acesso` vira orientações sem token (`RF-702`,
  `RF-708`–`RF-710`).
- **(C) Tela de entrada:** `TelaLogin` em duas etapas, com "Esqueci minha senha" só na de senha
  (`RF-705`–`RF-707`). `TelaDefinirSenha`, `POST /api/provisionamento/senha` e o texto
  `recuperacao_de_senha` não mudam (`RF-711`).

**OQ-701 resolvida** (2026-11-24, ver spec §10). **Correção (2026-11-24):** a consulta foi feita no projeto Supabase `virtus-id`, que NÃO é o banco de produção (produção é `zbvkvxgjayzmtrpjluhs`, `plans/migracao-supabase-brasil.plan.md`, inacessível por esta sessão). A ausência de duplicata em produção não está verificada; o código falha fechado nesse caso (`buscar_por_email` devolve `None` com e-mail ambíguo), então o pior efeito é a conta ambígua não entrar — nunca entrar na conta errada. Verificar em produção antes do deploy. Não há migração de dados; a busca compara
normalizado e toda gravação nova grava normalizado. **OQ-702** segue aberta e não bloqueia: a
redação vive em `app/notificacao/textos/emails.yaml` e `frontend/src/telas/textosDaEntrada.ts`, e
os testes verificam presença/ausência (link, e-mail, token, prazo), nunca a frase.

## 2. Architecture

```text
TelaLogin (etapa e-mail | etapa senha)
  ├─ entrar(email, senha='')        → POST /api/conta/login ─→ RepositorioContas.autenticar
  │                                                            └─ buscar_por_email (lower(trim))
  └─ pedirRecuperacao(email)        → POST /api/provisionamento/recuperacao
                                         └─ buscar_por_email → se e_revisor: tokens.emitir + e-mail
Hotmart → POST /api/provisionamento/hotmart → provisionar_conta_e_caso (e-mail normalizado)
                                            → primeiro_acesso(email)  (sem token)
n8n     → POST /api/provisionamento/conta   → idem, ainda emite e devolve token (AC-729)
```

A sessão (`iniciar_sessao_conta`, cookie `Secure`+`HttpOnly`, só `conta_id`) e a autorização
(`exigir_papel_revisor`, papel lido do banco a cada requisição) não mudam. `App.tsx` continua
decidindo o destino por `e_revisor` após `GET /api/conta/eu` — sem mudança.

## 3. Tech Stack

Mantida a stack existente, sem dependência nova: FastAPI/Starlette + psycopg (Postgres/Supabase) +
Argon2id (`argon2-cffi`, só no caminho do revisor); React/TypeScript, vitest + happy-dom +
Testing Library, Playwright com `page.route`. A comparação normalizada usa `lower()`/`trim()` do
Postgres e `str.strip().lower()` da stdlib (`RF-704`); a etapa de senha usa estado local do React
(`RF-705`).

## 4. Project Structure — unidades de mudança

Nenhum arquivo novo de produção. `U-NN` são as unidades que o `sdd-task` transforma em tarefas.

| Unidade | Arquivo | Mudança | RF |
| ------- | ------- | ------- | -- |
| `U-01` | `persistencia/app_aluno/contas.py` | (a) `normalizar_email(email) -> str` (`strip().lower()`); (b) `ErroSenhaExigida`; (c) `buscar_por_email` compara `lower(trim(email)) = %s` com o parâmetro normalizado; (d) `autenticar` reordenado (ver §5); (e) `criar` e `provisionar` gravam `normalizar_email(email)`; (f) docstrings do `Protocol` (`autenticar`, `buscar_por_email`), de `Conta.senha_hash` e `REGRAS` atualizados | 701–704 |
| `U-02` | `persistencia/app_aluno/cadastro.py` | `cadastrar_conta_e_caso` e `provisionar_conta_e_caso` gravam **e devolvem** `normalizar_email(email)` (importado de `contas.py`, que este módulo já importa) | 704 |
| `U-03` | `app/http/rotas_api_conta.py` | `entrar` captura `ErroSenhaExigida` ⇒ `401 {"erro": _MENSAGEM_LOGIN_INVALIDO, "exige_senha": true}`; `None` ⇒ `401` de sempre; docstring do módulo e da rota (o `RF-02` "inexistente = senha errada" passa a valer só para o revisor/bloqueio) | 701–703 |
| `U-04` | `app/notificacao/mensagens.py` | `primeiro_acesso(email: str) -> Mensagem` = `_montar("primeiro_acesso", link=_url_base(), email=email)`. `link_de_senha` e `recuperacao_de_senha` não mudam | 709 |
| `U-05` | `app/notificacao/textos/emails.yaml` | corpo de `primeiro_acesso` = rascunho de `OQ-702` com `{link}` e `{email}`, sem prazo nem "criar senha"; comentário do cabeçalho passa a citar `{email}` como segunda interpolação (só em `primeiro_acesso`) | 709 |
| `U-06` | `app/http/rotas_provisionamento.py` | (a) `_processar_webhook_hotmart`: remove `repositorio_tokens.emitir`, envia `primeiro_acesso(email)`; remove o parâmetro `repositorio_tokens` dela e a dependência correspondente de `receber_webhook_hotmart`; (b) `provisionar` (`/conta`): continua emitindo e devolvendo o token, mas envia `primeiro_acesso(email)`; (c) `pedir_recuperacao`: emite/envia só se `conta is not None and conta.e_revisor`; (d) docstring do módulo ("compra repetida reemite o link" vira "reenvia as orientações") | 708–710 |
| `U-07` | `frontend/src/services/api.ts` | `entrar(email: string, senha = '')`; nova `pedirRecuperacao(email: string): Promise<Response>` (`POST /api/provisionamento/recuperacao`, `form-urlencoded`, mesmo molde de `definirSenha`) | 705–707 |
| `U-08` | `frontend/src/telas/textosDaEntrada.ts` | `FORMULARIO.esqueciSenha` e `RECUPERACAO.enviada(email)` (rascunhos de `OQ-702`); `rotuloSenha`, `ERROS` sem mudança (`D-06`, Assumption 2) | 705, 707 |
| `U-09` | `frontend/src/telas/TelaLogin.tsx` | duas etapas (ver §7); "Esqueci minha senha" só na etapa de senha; confirmação anunciada | 705–707 |
| `U-10` | testes de servidor | ver §9 | — |
| `U-11` | testes de frontend (unit + e2e) | ver §9 | — |

**Não mudam:** `App.tsx`, `TelaDefinirSenha.tsx`, `persistencia/app_aluno/tokens_acesso.py`,
`app/http/sessao.py`, `app/http/isolamento.py`, `app/notificacao/email.py`, `scripts/papel_revisor.py`
(fora de escopo, spec §9), dublês de `RepositorioContas` que não exercitam login
(`test_guarda_papel_revisor.py`, `e2e/test_rotas_operador.py`) e o de
`e2e/test_ciclo_completo.py` (mais estrito que o novo contrato, mas os fluxos dele enviam a senha
correta — continua passando).

## 5. Data Model — contratos

Sem tabela, coluna nem índice novo. Contratos:

```python
# persistencia/app_aluno/contas.py
def normalizar_email(email: str) -> str: ...          # email.strip().lower()

class ErroSenhaExigida(Exception):
    """Conta de revisor ativa e a senha do pedido está vazia, errada, ou a conta
    ainda não tem senha. Mensagem sem e-mail e sem senha."""

class RepositorioContas(Protocol):                     # assinaturas inalteradas
    def buscar_por_email(self, email: str) -> Conta | None: ...
        # WHERE lower(trim(email)) = %s  ← normalizar_email(email)
    def autenticar(self, email: str, senha: str) -> Conta | None: ...
        # 1. buscar_por_email(email) is None          → None
        # 2. conta.bloqueado_em is not None           → None          (qualquer papel, RF-703)
        # 3. not conta.e_revisor                      → conta         (senha ignorada, RF-701)
        # 4. senha_hash None | senha == "" | verificar_senha falso
        #                                             → raise ErroSenhaExigida (RF-702)
        # 5.                                          → conta
```

A ordem 2 → 3 é o que garante `AC-710` (revisor bloqueado nunca vê `exige_senha`) e `AC-703`
(aluno com `senha_hash = NULL` entra). O passo 4 com `senha == ""` evita computar Argon2id na
primeira etapa do revisor.

```python
# app/notificacao/mensagens.py
def primeiro_acesso(email: str) -> Mensagem: ...       # {link} = _url_base(), {email} = email
```

Contrato HTTP (o único campo novo é `exige_senha`):

| Rota | Resposta |
| ---- | -------- |
| `POST /api/conta/login` | `200 {email, conta_id, e_revisor}` · `401 {"erro": "E-mail ou senha inválidos."}` · `401 {"erro": "E-mail ou senha inválidos.", "exige_senha": true}` |
| `POST /api/provisionamento/recuperacao` | sempre `200 {"pedido_registrado": true}` (inalterado) |
| `POST /api/provisionamento/hotmart` | inalterado: `200 {"provisionado": true, "email_enviado": bool}` |
| `POST /api/provisionamento/conta` | inalterado: `201 {token, expira_em, email_enviado}` |

```ts
// frontend/src/services/api.ts
export function entrar(email: string, senha?: string): Promise<Response>   // senha default ''
export function pedirRecuperacao(email: string): Promise<Response>
// frontend/src/telas/textosDaEntrada.ts
FORMULARIO.esqueciSenha: string
export const RECUPERACAO: { enviada: (email: string) => string }
```

## 6. Data Flow

**Login (aluno).** E-mail → `entrar(email, '')` → rota → `autenticar` → `buscar_por_email`
normalizado → aluno ativo ⇒ `Conta` ⇒ `iniciar_sessao_conta` ⇒ `200` → `onEntrou` → `App` consulta
`/api/conta/eu` → Início. Inexistente/bloqueado ⇒ `401` sem `exige_senha` → mensagem genérica.

**Login (revisor).** Etapa 1 envia `senha=''` ⇒ `ErroSenhaExigida` ⇒ `401` com `exige_senha` → a
tela abre a etapa de senha sem erro. Etapa 2 envia a senha ⇒ `200` (entra, `App` leva à fila) ou
`401` com `exige_senha` → mensagem genérica, continua na etapa de senha (a tela distingue as duas
pelo que enviou, Assumption 3).

**Recuperação.** "Esqueci minha senha" → `pedirRecuperacao(email)` → rota normaliza e busca → só
revisor: `tokens.emitir` + `recuperacao_de_senha(token)` → `{URL_BASE_APP}/#definir-senha/{token}`
→ `TelaDefinirSenha` (inalterada) → `POST /api/provisionamento/senha` → login em duas etapas
(`AC-730`). Resposta sempre igual; falha de envio é engolida como hoje.

**Compra.** Webhook → e-mail normalizado → `provisionar_conta_e_caso` (grava normalizado) ou, se
`ErroEmailDuplicado`, `buscar_por_email` + `completar_nome` → `primeiro_acesso(email)` → envio.
Nenhum token. Falha de envio ⇒ `email_enviado: false`, conta existe e o aluno entra só com o
e-mail.

## 7. State Management (tela de entrada)

Estado local de `TelaLogin`, nada global, nada persistido no navegador:

| Estado | Tipo | Regra |
| ------ | ---- | ----- |
| `etapa` | `'email' \| 'senha'` | nasce `'email'`; vira `'senha'` só com `401` + `exige_senha` **na etapa de e-mail**; volta a `'email'` quando o e-mail é editado (`AC-718`) |
| `email`, `senha` | `string` | editar o e-mail na etapa de senha limpa `senha` |
| `erro` | `string \| null` | `ERROS.credenciais` ou `ERROS.indisponivel`; limpo a cada envio e ao editar o e-mail |
| `recuperacaoEnviada` | `boolean` | `true` após `pedirRecuperacao` responder `ok`; limpo ao editar o e-mail |
| `enviando` | `boolean` | desabilita "Entrar" e "Esqueci minha senha" durante qualquer requisição |

Campo de senha e "Esqueci minha senha" só são renderizados em `etapa === 'senha'`; o campo de senha
ganha foco ao aparecer (`autoFocus`, `NFR` de acessibilidade). "Esqueci minha senha" é
`<button type="button">` dentro do formulário, para o Enter continuar enviando a etapa atual. A
confirmação usa `role="status"`; erros seguem `role="alert"` como hoje. `textosDaEntrada.ts`
continua sendo a única fonte de texto da tela.

## 8. Error Handling

| Situação | Detecção | Resposta | Recuperação |
| -------- | -------- | -------- | ----------- |
| envio em curso | `enviando` | botão em "Entrando…", botões desabilitados | — |
| `401` sem `exige_senha` | corpo JSON sem a chave | `ERROS.credenciais` (`role="alert"`), etapa mantida | corrigir e-mail |
| `401` com `exige_senha`, etapa e-mail | corpo JSON | abre etapa de senha, **sem** erro | — |
| `401`, etapa senha | `!ok` | `ERROS.credenciais`, campo de senha continua | nova senha ou "Esqueci minha senha" |
| corpo `401` ilegível | `json()` lança | tratado como `401` sem `exige_senha` (lado seguro: não revela etapa) | — |
| rede fora (login ou recuperação) | `fetch` rejeita | `ERROS.indisponivel`, etapa mantida (`EC-712`) | tentar de novo |
| recuperação `!ok` | `!ok` | `ERROS.indisponivel` (a rota sempre responde `200`; só proxy/infra chega aqui) | tentar de novo |
| servidor: falha de SMTP ou `URL_BASE_APP` | `ErroConfiguracaoEmail`/`ErroEnvioEmail`/`ErroUrlBaseAusente` | recuperação: `200` igual; webhook: `email_enviado: false` | inalterado |
| servidor: falha de banco | exceção do driver | `500` como hoje — não é resultado de autenticação | inalterado |

## 9. Testing Strategy

Servidor com dublês via `app.dependency_overrides` (unit) e Postgres real (`requer_banco`,
pulado sem `DATABASE_URL`) onde só o SQL real prova o critério. Frontend com vitest + happy-dom
(componente) e Playwright com `page.route` (fluxo). Todo teste novo cita o `AC-7NN`.

| Critério | Arquivo |
| -------- | ------- |
| `AC-701`, `AC-702`, `AC-703` | `tests/app_aluno/test_rotas_conta.py` (login só com e-mail → `200` + `/api/conta/eu` com `CASO_ID`; aluno com senha errada → `200`; aluno com `senha_hash=None` → `200`) · `tests/app_aluno/integracao/test_persistencia_contas.py` (`autenticar` real: aluno com senha errada e conta de `provisionar_conta_e_caso` com `senha=""` devolvem a conta) |
| `AC-704`–`AC-707` | `test_rotas_conta.py` (corpo exato com `exige_senha`, sem sessão; senha correta → `200` `e_revisor: true`) · `integracao/test_persistencia_contas.py` (`ErroSenhaExigida` com hash Argon2id real: sem senha, senha errada, `senha_hash` nulo) |
| `AC-708`–`AC-710` | `test_rotas_conta.py` (`resposta.json() == {"erro": "E-mail ou senha inválidos."}` para inexistente, aluno bloqueado, revisor bloqueado com e sem senha correta; textos idênticos byte a byte) |
| `AC-711`, `AC-712` | `integracao/test_persistencia_contas.py` (`buscar_por_email` com `"  Aluno@Exemplo.COM "`; linha `Fulano@Exemplo.com` inserida por SQL direto, pois a gravação agora normaliza) · `integracao/test_rotas_conta.py` (login `fulano@exemplo.com` → `200`; webhook `PURCHASE_REFUNDED` com `FULANO@exemplo.com` → `{"bloqueado": true}`, com `HOTMART_HOTTOK` por `monkeypatch`) · gravação normalizada: `integracao/test_persistencia_contas.py` (`criar`/`cadastrar_conta_e_caso` com `" Novo@Ex.com "` gravam `novo@ex.com`) |
| `AC-713` | `tests/app_aluno/test_rotas_provisionamento.py` (recuperação com e-mail em maiúsculas e espaços → token emitido para a conta do revisor) |
| `AC-714`–`AC-720` | `frontend/tests/unit/componentes/TelaLogin.test.tsx` |
| `AC-715`, `AC-716`, `AC-719` (fluxo) | `frontend/tests/e2e/navegacao.spec.ts` (aluno entra sem nunca ver "Sua senha"; revisor em duas etapas até a fila) via `frontend/tests/e2e/apoio/navegacao.ts` |
| `AC-721`–`AC-724` | `test_rotas_provisionamento.py`, seção nova de recuperação (`obter_enviador` sobrescrito por `EnviadorEmMemoria`; `URL_BASE_APP` por `monkeypatch`; falha = enviador que lança `ErroEnvioEmail` e `URL_BASE_APP` ausente) |
| `AC-725` | `tests/app_aluno/test_mensagens_de_email.py` (corpo contém URL base e o e-mail; não contém `#definir-senha`, `token`, `48 horas`, `horas`) |
| `AC-726`–`AC-728` | `test_rotas_provisionamento.py` (webhook com `EnviadorEmMemoria`: `tokens.emitidos == []`, um envio ao comprador, corpo sem `#definir-senha`; compra repetida idem + nome completado; falha de envio → `email_enviado: false`). A segunda metade de `AC-728` (entra só com o e-mail) é a mesma regra de `AC-703` |
| `AC-729` | `test_rotas_provisionamento.py` (`/conta` → `201` com `token`, `expira_em`, `email_enviado`; corpo enviado = o de `AC-725`) |
| `AC-730` | `integracao/test_rotas_conta.py` (Postgres real + `EnviadorEmMemoria`: conta promovida com `promover_a_revisor`, sem senha → `exige_senha` → recuperação → token extraído do link → `/senha` → login com senha `200 e_revisor: true`) |

**Testes existentes que mudam** (regressão esperada — o comportamento mudou de propósito):

| Arquivo | Teste / peça | Por quê | Vira |
| ------- | ------------ | ------- | ---- |
| `tests/app_aluno/test_rotas_conta.py` | `_RepositorioContasDublê.autenticar` | reproduz o contrato antigo | reproduz §5 (inclui `ErroSenhaExigida` e `bloqueado_em`) |
| idem | `test_login_com_senha_errada_nao_abre_sessao` | aluno com senha errada agora entra | `AC-706` (revisor) |
| idem | `test_mensagem_de_erro_de_login_nao_distingue_conta_inexistente_de_senha_errada` | idem; e o revisor agora traz `exige_senha` | `AC-708`/`AC-709` (inexistente ≡ bloqueado) |
| `tests/app_aluno/integracao/test_persistencia_contas.py` | `test_autenticar_com_conta_inexistente_e_senha_errada_devolve_o_mesmo_resultado` | aluno com senha errada devolve a conta | `AC-702` + `AC-706` no repositório |
| `tests/app_aluno/integracao/test_rotas_conta.py` | `test_login_e_logout_ponta_a_ponta_contra_banco_real` | afirma `401` para aluno com senha errada | login só com e-mail → `200`, logout → sem sessão |
| `tests/app_aluno/test_rotas_provisionamento.py` | `test_hotmart_compra_aprovada_provisiona_e_nao_devolve_token`, `test_hotmart_compra_repetida_reprovisiona_sem_erro` | afirmam `tokens.emitidos == ["CONTA_1", ...]` | `tokens.emitidos == []` (`AC-726`, `AC-727`) |
| idem | `_RepositorioContasDublê.buscar_por_email` | não sabe de `e_revisor` | aceita um conjunto `revisores` para os testes de recuperação |
| `tests/app_aluno/test_mensagens_de_email.py` | `test_primeiro_acesso_carrega_o_link_de_senha` | o link de senha sai do e-mail de compra | `AC-725` |
| idem | `test_nenhuma_mensagem_deixa_placeholder_por_substituir`, `test_corpo_e_texto_puro_sem_html`, `test_paragrafos_do_yaml_sobrevivem_a_carga` | chamam `primeiro_acesso(_TOKEN)` | `primeiro_acesso(_EMAIL)` — o placeholder test passa a guardar também `{email}` |
| `frontend/tests/unit/componentes/TelaLogin.test.tsx` | os oito testes que digitam em "Sua senha" na primeira etapa | o campo não existe mais na etapa de e-mail | reescritos contra as duas etapas; `autocomplete` de senha verificado na etapa de senha |
| `frontend/tests/e2e/apoio/navegacao.ts` | `interceptarBase` (mock do login) e `entrarComoRevisor` | revisor precisa de duas etapas | mock lê `senha` do `postData`: `eRevisor` sem senha → `401 {erro, exige_senha: true}`; helper preenche e-mail, clica, preenche senha, clica |
| `frontend/tests/e2e/navegacao.spec.ts` | teste do revisor (~l.635–683) e `T-154: entrar SEM ?caso=` (~l.907) | preenchem "Sua senha" na primeira etapa | revisor em duas etapas; aluno só com e-mail + asserção de que "Sua senha" não existe |

**Fora de teste automatizado:** redação final (`OQ-702`, revisão do produto) e 360 px sem rolagem
horizontal na etapa de senha (a etapa só acrescenta um campo e um botão com as classes existentes;
conferência visual na revisão).

## 10. Risks & Trade-offs

| Decisão | Alternativa descartada | Por quê | Risco assumido |
| ------- | ---------------------- | ------- | -------------- |
| `autenticar` sinaliza o revisor com `ErroSenhaExigida` | (a) mudar o retorno para um tipo-soma; (b) a rota chamar `buscar_por_email` de novo quando `autenticar` devolve `None` | Assinatura do `Protocol` intacta (nenhum dublê alheio precisa mudar), uma ida ao banco, regra num lugar só. Exceção de controle já é padrão aqui (`ErroEmailDuplicado` no provisionamento) | mypy não obriga o chamador a tratar; `autenticar` só tem um chamador de produção (`entrar`), coberto por teste |
| Busca `lower(trim(email)) = %s` sem índice funcional | índice `lower(email)` em migração | base pequena; a diretriz é não criar migração | varredura sequencial — `ponytail:` comentário no SQL; índice funcional quando a base crescer |
| Normalizar na gravação (4 `INSERT`s em `persistencia/app_aluno/`) | normalizar só nas rotas | as rotas de compra já normalizam; o cadastro público não. Persistência é o ponto por onde todos passam (decisão de `OQ-701`) | `UNIQUE(email)` continua sensível a maiúsculas: um e-mail legado com maiúscula + compra nova em minúscula criaria duplicata. Produção verificada sem legado; gravação normalizada impede o caso novo |
| `/conta` (n8n) continua emitindo token | parar de emitir | spec `AC-729` e §9: contrato da rota mantido | token devolvido no corpo, mas o e-mail não o leva mais — inofensivo ao aluno |
| `.strip().lower()` do Python vs `lower(trim())` do Postgres | só SQL | o parâmetro já chega normalizado; `trim` do SQL só tira espaços, o `strip` também tira tab/quebra | divergência só em caracteres não ASCII, irrelevante para e-mail |

**Riscos de produto aceitos na spec** (não mitigados aqui): `RSK-701` (login só com e-mail),
`RSK-702` (enumeração aluno/revisor/inexistente, inclusive por tempo — Argon2id só no revisor),
`RSK-703` (sem rate limiting: `T-184` fica mais urgente).

**Regressão.** Toda a suíte que assumia "aluno precisa de senha" está listada em §9; os demais
logins de teste que enviam senha correta continuam passando, porque a senha do aluno é ignorada,
não recusada.

**Schema de produção.** O código e os testes de integração usam `piq_app_aluno`. A suspeita de que
produção ainda estaria em `app_aluno` veio do banco errado (`virtus-id`); em produção, `POST /api/conta/login`
com e-mail inexistente respondeu `401` (consulta à tabela de contas funcionou). Este plano não cria nada
que dependa do nome.

## 11. Traceability

| Requisito | Coberto por |
| --------- | ----------- |
| `RF-701` | §5 `autenticar` passo 3; `U-01`, `U-03`; §9 `AC-701`–`AC-703` |
| `RF-702` | §5 passo 4 + contrato `exige_senha`; `U-01`, `U-03`; §9 `AC-704`–`AC-707` |
| `RF-703` | §5 passos 1–2; `U-01`, `U-03`; §9 `AC-708`–`AC-710` |
| `RF-704` | §5 `normalizar_email`/`buscar_por_email`; `U-01`, `U-02`, `U-06`; §9 `AC-711`–`AC-713` |
| `RF-705` | §7; `U-07`, `U-08`, `U-09`; §9 `AC-714`–`AC-718` |
| `RF-706` | §6 login revisor, §7; `U-09`; §9 `AC-719` |
| `RF-707` | §6 recuperação, §7; `U-07`, `U-08`, `U-09`; §9 `AC-720` |
| `RF-708` | §6 recuperação; `U-06`(c); §9 `AC-721`–`AC-724` |
| `RF-709` | §5 `primeiro_acesso`; `U-04`, `U-05`, `U-06`(b); §9 `AC-725`, `AC-729` |
| `RF-710` | §6 compra; `U-06`(a); §9 `AC-726`–`AC-728` |
| `RF-711` | §6 recuperação (tela e rota de senha inalteradas); §9 `AC-721`, `AC-730` |

Nenhum requisito sem cobertura; nenhuma unidade sem requisito.
