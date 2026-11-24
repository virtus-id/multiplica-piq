# Spec — Acesso do aluno sem senha

| Campo    | Valor                                                                                     |
| -------- | ----------------------------------------------------------------------------------------- |
| Slug     | `acesso-sem-senha`                                                                        |
| Status   | `rascunho`                                                                                |
| Autor    | `sdd-spec`, a partir das decisões do dono do produto                                      |
| Data     | 2026-11-24                                                                                |
| Fonte    | Decisões do dono do produto de 2026-11-24 (`D-01` a `D-06`, abaixo) — **fechadas, não se reabrem nesta spec** |
| Substitui | Para o **aluno**, `RF-02` e `OQ-05` de [`specs/app-aluno.spec.md`](app-aluno.spec.md) (login com senha). Para o **revisor**, `RF-02` continua valendo |

> **Sem stack e sem implementação.** Rotas, campos de resposta e nomes de tela
> aparecem aqui porque são o **contrato observável** que já existe e que os
> testes verificam; como mudar o código é trabalho de
> `plans/acesso-sem-senha.plan.md`.

### Decisões que esta spec registra (2026-11-24)

| ID     | Decisão |
| ------ | ------- |
| `D-01` | **Aluno** (conta com `e_revisor = false`) entra **só com o e-mail**, sem senha. Conta existente e não bloqueada (`bloqueado_em` nulo) ⇒ a sessão abre. Risco aceito explicitamente pelo dono do produto (ver `RSK-701`) |
| `D-02` | **Revisor** (`e_revisor = true`) entra com e-mail **e** senha, em **duas etapas** na tela: primeiro o e-mail; se a conta for de revisor, o login responde `401 {"erro": ..., "exige_senha": true}` e a tela mostra o campo de senha. O aluno nunca vê campo de senha |
| `D-03` | O e-mail de compra (`primeiro_acesso`) vira **orientações de acesso**: link para a URL base do app (`URL_BASE_APP`) e o e-mail de login, **sem token e sem prazo**. O webhook da Hotmart deixa de emitir token de primeiro acesso nos dois ramos (conta nova e compra repetida) |
| `D-04` | "Esqueci minha senha" aparece **só na etapa de senha** (só revisor) e chama `POST /api/provisionamento/recuperacao`. A rota passa a emitir token e enviar e-mail **só se a conta for de revisor**; a resposta continua sempre `200 {"pedido_registrado": true}`. O link leva à tela existente `#definir-senha/{token}`, que não muda. Revisor promovido sem senha usa o mesmo caminho para criar a primeira |
| `D-05` | A comparação de e-mail no login ignora maiúsculas/minúsculas e espaços nas pontas. Causa raiz: a busca de conta por e-mail diferencia maiúsculas |
| `D-06` | Conta inexistente ou bloqueada ⇒ `401` com a mensagem genérica de sempre |

---

## 1. Overview

**Problema.** A compra na Hotmart cria a conta do aluno sem senha e envia um e-mail
com link de criar senha que vale 48 horas. Passado o prazo, o aluno fica preso: a
recuperação de senha existe no servidor, mas nenhuma tela a oferece. Além disso,
quem digita o e-mail com uma maiúscula não entra, porque o login diferencia
maiúsculas e a compra grava o e-mail em minúsculas.

**Objetivo.** O aluno entra no PIQ informando apenas o e-mail da compra, a qualquer
momento, sem prazo e sem senha. O revisor continua protegido por senha, com uma
etapa extra na mesma tela e um caminho de "Esqueci minha senha" que também serve
para criar a primeira senha. **Para quem:** o aluno comprador do upsell do curso
Servidor Sem Dívidas (persona principal) e a equipe de revisão.

## 2. Functional Requirements

| ID       | Requisito | Origem | Prioridade |
| -------- | --------- | ------ | ---------- |
| `RF-701` | O login (`POST /api/conta/login`) abre a sessão de uma conta de **aluno** existente e não bloqueada **só com o e-mail**. Uma senha enviada junto é ignorada; ter ou não ter senha definida não muda o resultado. A resposta de sucesso é a de hoje (`200`, `{email, conta_id, e_revisor}`) | `D-01` | essencial |
| `RF-702` | Para uma conta de **revisor** não bloqueada, o login só abre a sessão com a senha correta. Sem senha, com senha errada ou com a conta ainda sem senha definida, responde `401` com a mensagem genérica e `"exige_senha": true`, sem abrir sessão | `D-02` | essencial |
| `RF-703` | Conta inexistente ou bloqueada, de qualquer papel, responde `401` com a mensagem genérica de sempre, **sem** `exige_senha`, sem abrir sessão — com ou sem senha no pedido | `D-06` | essencial |
| `RF-704` | Toda busca de conta por e-mail (login, recuperação de senha, webhook de compra e de reembolso) ignora maiúsculas/minúsculas e espaços nas pontas, tanto no e-mail informado quanto no gravado | `D-05` | essencial |
| `RF-705` | A tela de entrada começa **só com o campo de e-mail**. Sucesso ⇒ entra. `401` com `exige_senha` ⇒ mostra a etapa de senha, sem mensagem de erro. `401` sem `exige_senha` ⇒ mostra a mensagem genérica e continua na etapa de e-mail. O aluno nunca vê campo de senha | `D-01`, `D-02` | essencial |
| `RF-706` | Na etapa de senha, a tela envia e-mail e senha. Recusa ⇒ mensagem genérica, continua na etapa de senha. Sucesso ⇒ entra como revisor | `D-02` | essencial |
| `RF-707` | Na etapa de senha (e só nela) a tela oferece "Esqueci minha senha", que envia o e-mail informado a `POST /api/provisionamento/recuperacao` e mostra uma confirmação | `D-04` | essencial |
| `RF-708` | `POST /api/provisionamento/recuperacao` emite token e envia o e-mail `recuperacao_de_senha` **só** quando o e-mail é de uma conta de revisor. Para aluno, conta inexistente ou e-mail vazio, nada é emitido nem enviado. A resposta é sempre `200 {"pedido_registrado": true}`, inclusive quando o envio falha | `D-04` | essencial |
| `RF-709` | O e-mail de compra (`primeiro_acesso`) passa a conter as orientações de acesso: o link para `URL_BASE_APP` (sem `#definir-senha`) e o e-mail de login do destinatário. Não contém token, link de criar senha nem prazo de validade | `D-03` | essencial |
| `RF-710` | O webhook `POST /api/provisionamento/hotmart` (`PURCHASE_APPROVED`) deixa de emitir token de primeiro acesso, tanto para conta nova quanto para compra repetida. Continua criando conta e caso, completando o nome, enviando o e-mail de `RF-709` e respondendo como hoje (`200 {"provisionado": true, "email_enviado": <bool>}`) | `D-03` | essencial |
| `RF-711` | O link do e-mail de recuperação leva à tela existente `#definir-senha/{token}`, sem mudança. É também o caminho pelo qual um revisor promovido sem senha cria a primeira | `D-04` | importante |

## 3. User Stories

### `US-701` — Entrar só com o meu e-mail

> Como **aluno**, quero **entrar informando só o e-mail da compra** para **voltar ao meu
> caso a qualquer momento, sem depender de um link que vence nem de uma senha que esqueci**.

Atende: `RF-701`, `RF-703`, `RF-704`, `RF-705`

### `US-702` — Saber como entrar logo depois de comprar

> Como **aluno que acabou de comprar**, quero **um e-mail que diga onde entrar e com qual
> e-mail** para **começar sem prazo e sem criar senha**.

Atende: `RF-709`, `RF-710`

### `US-703` — Entrar como revisor com senha

> Como **revisor**, quero **informar o e-mail e, em seguida, a senha** para **acessar a
> fila e os casos de todos os alunos com uma proteção a mais que a do aluno**.

Atende: `RF-702`, `RF-705`, `RF-706`

### `US-704` — Criar ou recuperar a senha de revisor

> Como **revisor**, quero **pedir um link de nova senha na própria tela de entrada** para
> **recuperar o acesso, ou criar a primeira senha depois de ser promovido**.

Atende: `RF-707`, `RF-708`, `RF-711`

## 4. Acceptance Criteria

"Mensagem genérica" = a de hoje: no corpo do servidor, `"E-mail ou senha inválidos."`;
na tela, `"E-mail ou senha não conferem."`. "Sem sessão" = `GET /api/conta/eu` em
seguida responde `401`.

| ID       | Story    | Critério (verificável) |
| -------- | -------- | ---------------------- |
| `AC-701` | `US-701` | Dada uma conta de aluno existente e não bloqueada, quando `POST /api/conta/login` recebe só `email`, então responde `200` com `{"email", "conta_id", "e_revisor": false}` e `GET /api/conta/eu` em seguida responde `200` com o `CASO_ID` da conta (`RF-701`) |
| `AC-702` | `US-701` | Dada uma conta de aluno **com** senha definida, quando o login recebe `email` e uma senha **errada**, então responde `200` e abre a sessão — a senha é ignorada (`RF-701`) |
| `AC-703` | `US-701` | Dada uma conta de aluno criada pela compra e **sem** senha definida, quando o login recebe só `email`, então responde `200` e abre a sessão (`RF-701`) |
| `AC-704` | `US-703` | Dada uma conta de revisor não bloqueada, quando o login recebe só `email`, então responde `401` com corpo `{"erro": "E-mail ou senha inválidos.", "exige_senha": true}`, sem sessão (`RF-702`) |
| `AC-705` | `US-703` | Dada uma conta de revisor não bloqueada, quando o login recebe `email` e a senha correta, então responde `200` com `"e_revisor": true` e abre a sessão (`RF-702`) |
| `AC-706` | `US-703` | Dada uma conta de revisor não bloqueada, quando o login recebe `email` e senha errada, então responde `401` com `"exige_senha": true`, sem sessão (`RF-702`) |
| `AC-707` | `US-703` | Dada uma conta de revisor **sem senha definida**, quando o login recebe `email` com qualquer senha, ou sem senha, então responde `401` com `"exige_senha": true`, sem sessão (`RF-702`) |
| `AC-708` | `US-701` | Dado um e-mail sem conta, quando o login é chamado com ou sem senha, então responde `401` com corpo exatamente `{"erro": "E-mail ou senha inválidos."}` (sem a chave `exige_senha`), sem sessão (`RF-703`) |
| `AC-709` | `US-701` | Dada uma conta de aluno bloqueada (`bloqueado_em` preenchido), quando o login recebe o e-mail, então a resposta é idêntica à de `AC-708` (`RF-703`) |
| `AC-710` | `US-703` | Dada uma conta de revisor bloqueada, quando o login recebe o e-mail sem senha **ou** com a senha correta, então a resposta é idêntica à de `AC-708` — sem `exige_senha` (`RF-703`) |
| `AC-711` | `US-701` | Dada uma conta de aluno gravada como `aluno@exemplo.com`, quando o login recebe `"  Aluno@Exemplo.COM "`, então responde `200` para essa conta (`RF-704`) |
| `AC-712` | `US-701` | Dada uma conta gravada com maiúsculas (ex.: `Fulano@Exemplo.com`, vinda do cadastro público), sendo de aluno, quando o login recebe `fulano@exemplo.com`, então responde `200` para essa conta; e o webhook de reembolso com `FULANO@exemplo.com` bloqueia essa conta (`{"bloqueado": true}`) (`RF-704`) |
| `AC-713` | `US-704` | Dada uma conta de revisor gravada em minúsculas, quando a recuperação recebe o e-mail com maiúsculas e espaços nas pontas, então um token é emitido e o e-mail de recuperação é enviado a essa conta (`RF-704`, `RF-708`) |
| `AC-714` | `US-701` | Dada a tela de entrada recém-aberta, então ela mostra o campo "Seu e-mail" e o botão "Entrar", e **não** existe campo de senha nem "Esqueci minha senha" na página (`RF-705`) |
| `AC-715` | `US-701` | Dada a tela de entrada, quando o servidor responde `200` ao e-mail, então a tela entra no app e em nenhum momento um campo de senha foi exibido (`RF-705`) |
| `AC-716` | `US-703` | Dada a tela de entrada, quando o servidor responde `401` com `exige_senha: true`, então aparecem o campo "Sua senha" (com foco) e "Esqueci minha senha", o e-mail digitado continua no campo e **nenhuma** mensagem de erro é exibida (`RF-705`) |
| `AC-717` | `US-701` | Dada a tela de entrada, quando o servidor responde `401` sem `exige_senha`, então aparece a mensagem genérica com `role="alert"` e a tela continua sem campo de senha (`RF-705`) |
| `AC-718` | `US-703` | Dada a etapa de senha, quando o e-mail é alterado, então o campo de senha e "Esqueci minha senha" somem e a tela volta à etapa de e-mail (`RF-705`, ver Assumptions) |
| `AC-719` | `US-703` | Dada a etapa de senha, quando o envio com senha recebe `401`, então aparece a mensagem genérica com `role="alert"` e o campo de senha continua visível; quando recebe `200`, a tela entra no app com o papel de revisor (`RF-706`) |
| `AC-720` | `US-704` | Dada a etapa de senha, quando "Esqueci minha senha" é acionado, então a tela chama `POST /api/provisionamento/recuperacao` com o e-mail digitado, mostra a confirmação e não abre sessão (`RF-707`) |
| `AC-721` | `US-704` | Dado um e-mail de revisor, quando `POST /api/provisionamento/recuperacao` é chamado, então responde `200 {"pedido_registrado": true}`, emite um token para a conta e envia o e-mail `recuperacao_de_senha` com o link `{URL_BASE_APP}/#definir-senha/{token}` (`RF-708`, `RF-711`) |
| `AC-722` | `US-704` | Dado um e-mail de aluno, quando a recuperação é chamada, então responde `200 {"pedido_registrado": true}`, nenhum token é emitido e nenhum e-mail é enviado (`RF-708`) |
| `AC-723` | `US-704` | Dado um e-mail sem conta, ou o campo vazio, quando a recuperação é chamada, então a resposta é idêntica à de `AC-722`, sem token e sem e-mail (`RF-708`) |
| `AC-724` | `US-704` | Dado um e-mail de revisor e falha no envio (servidor de e-mail indisponível ou `URL_BASE_APP` ausente), quando a recuperação é chamada, então a resposta continua `200 {"pedido_registrado": true}` (`RF-708`) |
| `AC-725` | `US-702` | Dada `URL_BASE_APP` configurada, quando o e-mail `primeiro_acesso` é montado para `aluno@exemplo.com`, então o corpo contém a URL base, contém `aluno@exemplo.com` e **não** contém `#definir-senha`, token, "48 horas" nem outro prazo (`RF-709`) |
| `AC-726` | `US-702` | Dado um `PURCHASE_APPROVED` válido para um e-mail novo, quando o webhook o processa, então responde `200 {"provisionado": true, "email_enviado": true}`, a conta e o caso existem, **nenhum** token de acesso foi emitido e um único e-mail (o de `AC-725`) foi enviado ao comprador (`RF-710`) |
| `AC-727` | `US-702` | Dado um `PURCHASE_APPROVED` para um e-mail que já tem conta (compra repetida), quando o webhook o processa, então a resposta é a mesma de `AC-726`, nenhum token é emitido, o e-mail de `AC-725` é enviado e o nome é completado como hoje (`RF-710`) |
| `AC-728` | `US-702` | Dado um `PURCHASE_APPROVED` válido com falha de envio (servidor de e-mail ou `URL_BASE_APP` ausente), quando o webhook o processa, então responde `200 {"provisionado": true, "email_enviado": false}` e a conta existe — e o aluno entra só com o e-mail (`AC-701`) mesmo sem ter recebido nada (`RF-710`) |
| `AC-729` | `US-702` | Dado `POST /api/provisionamento/conta` (n8n) válido, então continua respondendo `201` com `token`, `expira_em` e `email_enviado`, e o e-mail enviado é o mesmo de `AC-725` (`RF-709`, ver Assumptions) |
| `AC-730` | `US-704` | Dado um revisor promovido sem senha, quando ele (1) informa o e-mail ⇒ `401` com `exige_senha`; (2) pede recuperação ⇒ recebe o link; (3) define a senha em `POST /api/provisionamento/senha` com o token e 8+ caracteres ⇒ `200 {"senha_definida": true}`; (4) entra com e-mail e senha ⇒ `200` com `"e_revisor": true` (`RF-711`) |

> Todo `RF-7NN` tem ao menos um `AC-7NN`: `RF-701` (701–703), `RF-702` (704–707),
> `RF-703` (708–710), `RF-704` (711–713), `RF-705` (714–718), `RF-706` (719),
> `RF-707` (720), `RF-708` (721–724), `RF-709` (725, 729), `RF-710` (726–728),
> `RF-711` (721, 730).

## 5. Non-Functional Requirements

- **Performance:** sem meta nova. O login do aluno deixa de verificar senha, então não
  fica mais lento que hoje.
- **Acessibilidade:** a etapa de senha, ao aparecer, recebe o foco no campo de senha;
  erros e a confirmação de recuperação são anunciados (`role="alert"` / região
  anunciada, como os erros atuais); tudo operável por teclado, Enter envia a etapa atual.
- **Responsividade:** mesma da tela de entrada atual; a etapa de senha não cria rolagem
  horizontal a 360 px.
- **Segurança:**
  - A sessão continua sendo a de hoje (cookie `Secure` + `HttpOnly`, só `conta_id`); o
    papel continua lido do banco a cada requisição.
  - A recuperação nunca revela se o e-mail existe nem qual é o papel (resposta única).
  - O link de recuperação mantém o token no fragmento (`#`), como hoje.
  - Login do aluno sem senha é **risco aceito** (`RSK-701`), não omissão.
- **Observabilidade:** nenhum log novo com e-mail ou outro dado do aluno (mesma
  disciplina de hoje). O webhook continua informando `email_enviado`.

## 6. Edge Cases

| ID       | Situação | Comportamento esperado |
| -------- | -------- | ---------------------- |
| `EC-701` | Revisor sem senha definida ainda (promovido de uma conta da compra) | Etapa 1 ⇒ `exige_senha`; qualquer senha ⇒ `401` com `exige_senha`; cria a primeira senha por "Esqueci minha senha" (`AC-707`, `AC-730`) |
| `EC-702` | Revisor bloqueado | `401` genérico sem `exige_senha`, com ou sem senha (`AC-710`). A recuperação ainda envia o link (a decisão condiciona só ao papel), mas o login continua recusando |
| `EC-703` | E-mail com maiúsculas e/ou espaços nas pontas, no login, na recuperação ou no webhook | Encontra a mesma conta (`AC-711`–`AC-713`) |
| `EC-704` | Compra repetida do mesmo e-mail | Mesma resposta da compra nova, sem token, com o e-mail de orientações (`AC-727`) |
| `EC-705` | Compra nova de quem foi reembolsado (conta bloqueada) | Como hoje: a conta **continua bloqueada** e o e-mail de orientações é enviado; o login responde `401` genérico. Desbloqueio fora de escopo |
| `EC-706` | Recuperação pedida para e-mail de aluno ou inexistente (chamada direta à rota) | `200 {"pedido_registrado": true}`, sem token e sem e-mail (`AC-722`, `AC-723`) |
| `EC-707` | Aluno que já tinha senha (cadastro público ou primeiro acesso antigo) | A senha passa a ser ignorada; entra só com o e-mail (`AC-702`) |
| `EC-708` | Link antigo de primeiro acesso ainda dentro das 48 h | A tela `#definir-senha` funciona como hoje; a senha definida não muda nada no login do aluno |
| `EC-709` | Revisor que perde o papel (`e_revisor` volta a `false`) | Passa a entrar só com o e-mail, como aluno, na requisição seguinte |
| `EC-710` | Login com e-mail vazio | A tela não envia (campo obrigatório); chamada direta ⇒ `401` genérico de `AC-708` |
| `EC-711` | Falha no envio do e-mail de compra | `email_enviado: false`; o aluno entra mesmo assim só com o e-mail da compra (`AC-728`) |
| `EC-712` | Falha de rede na tela (login ou recuperação) | Mensagem de indisponibilidade atual (`"Não foi possível entrar agora."`); a tela continua na etapa em que estava |
| `EC-713` | Duas contas cujos e-mails diferem só em maiúsculas/espaços | Não verificado em produção (ver `OQ-701`); se existir, a busca falha fechado (`None`). Deixa de poder surgir: toda gravação nova normaliza o e-mail (`OQ-701`, resolvida) |

## 7. Assumptions

1. **Papel** = `e_revisor` lido do banco no momento do login. Não há outro papel.
2. **Mensagem genérica** = a de hoje, sem mudança de texto (`D-06`), inclusive na etapa
   de e-mail do aluno, onde ela ainda cita "senha". Mudar a redação exige aprovação do
   produto e não faz parte desta spec.
3. **Corpo do `401` do revisor** traz o mesmo `erro` genérico e `exige_senha: true` tanto
   sem senha quanto com senha errada. A tela distingue os dois pelo que ela enviou: sem
   senha ⇒ abre a etapa de senha sem erro; com senha ⇒ mostra o erro.
4. **Editar o e-mail na etapa de senha volta à etapa de e-mail** (`AC-718`), para que o
   campo de senha nunca fique na tela ao lado de um e-mail que não foi checado.
5. **Um único texto `primeiro_acesso`.** `POST /api/provisionamento/conta` (n8n) usa a
   mesma mensagem, então também passa a enviar as orientações sem token, embora continue
   devolvendo o token no corpo (`AC-729`).
6. **Recuperação** depende só do papel; o bloqueio é verificado no login (`EC-702`).
7. Os textos `recuperacao_de_senha` e da tela `#definir-senha` não mudam: "criar uma nova
   senha" serve também ao revisor que cria a primeira.
8. Tokens já emitidos não são revogados; vencem sozinhos.
9. Nenhum e-mail **já gravado** no banco é reescrito: a regra de `D-05` vale na comparação.
   Contas **novas** passam a ser gravadas com o e-mail aparado e em minúsculas, venham do
   cadastro público ou da compra (`OQ-701`, resolvida).

## 8. Risks

| ID        | Risco | Impacto | Mitigação |
| --------- | ----- | ------- | --------- |
| `RSK-701` | **Risco aceito pelo dono do produto em 2026-11-24.** Quem souber o e-mail de um aluno entra na conta dele e vê dados financeiros sensíveis (renda, dívidas, contracheque declarado, plano) | alto | **Nenhuma nesta spec — aceito explicitamente** (`D-01`). Rate limiting (`T-184`) reduz tentativa em massa, mas não protege contra quem já conhece o e-mail |
| `RSK-702` | O login passa a revelar se um e-mail é de aluno (`200`), de revisor (`exige_senha`) ou não tem conta (`401`) — enumeração de contas e da equipe | médio | Consequência direta de `D-01`/`D-02`, aceita com elas. A recuperação continua sem revelar nada |
| `RSK-703` | Sem rate limiting, alguém pode testar e-mails em massa, tentar senhas de revisor sem limite e disparar e-mails de recuperação para revisores | médio | `T-184` (`tasks/app-aluno.tasks.md`) fica **mais urgente** com o login só por e-mail |
| `RSK-704` | Aluno usa um e-mail diferente do da compra e recebe `401` | médio | O e-mail de compra informa o e-mail de login (`RF-709`) |
| `RSK-705` | Duas contas que só diferem em maiúsculas tornam a busca ambígua | baixo | `OQ-701` resolvida: base verificada sem duplicata e gravação normalizada daqui em diante |

## 9. Out of Scope

- **Rate limiting** — já é `T-184` em `tasks/app-aluno.tasks.md`, pendente; fica mais
  urgente com esta spec (`RSK-703`), mas não entra aqui.
- **`POST /api/conta/cadastro`** (cadastro público com senha) continua como está, exceto
  que o e-mail passa a ser gravado normalizado (`OQ-701`). Contas criadas por ele com
  `e_revisor = false` são de aluno e seguem `RF-701`.
- **`POST /api/provisionamento/conta`** (n8n) continua emitindo e devolvendo o token,
  que deixa de ser necessário ao aluno (`AC-729`).
- Tela `#definir-senha/{token}`, rota `POST /api/provisionamento/senha` e o texto
  `recuperacao_de_senha` — sem mudança.
- Desbloqueio de conta em compra nova depois de reembolso (`EC-705`).
- Login por link mágico, código por e-mail, segundo fator ou qualquer outra prova de
  posse do e-mail para o aluno.
- Comparação de e-mail nos scripts de promover/revogar revisor e migração dos e-mails já
  gravados.
- Qualquer mudança em autorização (`exigir_papel_revisor`, isolamento de caso), no motor
  ou no esquema do banco além do que `RF-704` exigir.

## 10. Open Questions

| ID       | Pergunta | Por que importa | Status |
| -------- | -------- | --------------- | ------ |
| `OQ-701` | Se existirem duas contas cujos e-mails só diferem em maiúsculas/espaços (possível via cadastro público, que não grava em minúsculas), qual delas o login, a recuperação e o webhook encontram? | Com `RF-704` a busca deixa de distinguir as duas; escolher uma sem regra pode abrir o caso de outra pessoa. **Resolvida em 2026-11-24 (decisão técnica):** base de produção consultada — 7 contas, 0 e-mails fora do padrão minúsculo/sem espaço, 0 grupos duplicados por `lower(trim(email))`. **Correção (2026-11-24):** a consulta foi feita no projeto Supabase `virtus-id`, que NÃO é o banco de produção (produção é `zbvkvxgjayzmtrpjluhs`, `plans/migracao-supabase-brasil.plan.md`, inacessível por esta sessão). A ausência de duplicata em produção não está verificada; o código falha fechado nesse caso (`buscar_por_email` devolve `None` com e-mail ambíguo), então o pior efeito é a conta ambígua não entrar — nunca entrar na conta errada. Verificar em produção antes do deploy. Decisão: a busca por e-mail compara `lower(trim(email))` com o e-mail informado normalizado; não há migração de dados. Para não criar duplicata no futuro, **toda gravação de conta** (cadastro público, compra, criação pelo repositório) passa a gravar o e-mail com `strip().lower()` — a normalização vive na camada de persistência, por onde todos os chamadores passam. Ver `plans/acesso-sem-senha.plan.md` | `resolvida` |
| `OQ-702` | Redação final dos textos novos. Rascunhos propostos — e-mail `primeiro_acesso`: *"Sua compra foi confirmada e o seu acesso ao PIQ já está liberado. Para entrar, acesse {link} e informe o seu e-mail: {email}. Não precisa de senha. Use sempre este mesmo e-mail."*; tela: link *"Esqueci minha senha"* e confirmação *"Enviamos um link para criar uma nova senha. Confira a caixa de entrada de {email}."* | Textos ao aluno e à equipe exigem aprovação do produto. **Não bloqueia o plano**: os critérios verificam a presença do link, do e-mail e a ausência de token/prazo, não a redação exata | `aberta` |
