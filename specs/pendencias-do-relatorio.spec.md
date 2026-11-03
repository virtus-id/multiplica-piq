# Spec — pendências e redação do relatório do aluno

| Campo | Valor |
| ----- | ----- |
| Slug  | `pendencias-do-relatorio` |
| Origem | Pedido do produto de 2026-10-29, a partir da prévia do caso de teste do Guilherme (aluno deficitário). |

## Problema

O relatório lista, em "O que falta informar", dados que o aluno não tem como informar: quanto pagar para quitar hoje (campo que o questionário já não pergunta desde a `T-408`, e o motor usa o saldo no lugar) e o valor da parcela de uma dívida que o próprio aluno declarou não ter parcela definida. O banner e a pergunta frequente dizem "este plano é definitivo" mesmo quando o plano é provisório. Uma linha da tabela "Seu ponto de partida" tem o rótulo de um total que é, na verdade, o resultado antes das parcelas.

## Requisitos

- **`RF-461`** — "O que falta informar" só lista dado que o aluno pode informar. `VALOR_QUITACAO_HOJE` não é auditado como pendência.
- **`RF-462`** — *(revogado por `RF-513`: `B5.C01` saiu e a parcela é sempre perguntada)* `PARCELA_CONTRATUAL` desconhecida não é pendência quando o aluno respondeu que a dívida não tem parcela definida (`POSSUI_PARCELA_DEFINIDA = NAO`): a ausência é estrutural.
- **`RF-463`** — Sem pendência real, o relatório (PDF e tela) não traz a seção "O que falta informar" nem o aviso "ainda é provisório porque faltam informações". Inventário incompleto continua sendo pendência real.
- **`RF-464`** — O botão "Responder agora" de uma pendência sempre aponta para uma pergunta que existe no questionário.
- **`RF-465`** — Plano provisório (`ORDEM_STATUS = PROVISORIA` ou modo estabilização) não é chamado de "definitivo" no banner nem na pergunta "Quando o meu plano muda?". Plano definitivo mantém o texto atual.
- **`RF-466`** — A linha que soma renda − despesas, antes das parcelas de dívida, tem o rótulo "Resultado do mês antes das parcelas de dívida (renda − despesas)". Substitui o texto da `RF-412` (`B3.DF02`).
- **`RF-467`** — Nenhuma pergunta que o aluno responde deixa de ser exigida: a guarda de envio continua recusando toda pergunta `indispensavel` exigível sem resposta.

### RF-480. Dívida que cresce: a estabilização com mensagem própria
Quando o motor devolve `MODO_ESTABILIZACAO` com `MOTIVO_ESTABILIZACAO = DIVIDA_QUE_CRESCE` (a sobra do mês é maior ou igual a zero, mas menor que a soma das faltas de juros; `RF-79`), o aluno **não é deficitário** e segue o **mesmo caminho do deficitário**: sem prazo, custo nem fichas mensais, com a ordem provisória (`RF-447`, `RF-450`, `RF-473`). A mensagem é **própria** e não reaproveita "seus pagamentos superam sua renda". Ela traz só fatos já no snapshot: o valor livre do mês, cada dívida que cresce com a parcela, os juros do mês e a falta, e a soma das faltas contra a sobra. **Texto proposto, a aprovar pelo produto** (chaves novas em `textos-canonicos.yaml`):

- Título: "Seu mês fecha positivo, mas suas dívidas estão crescendo".
- Corpo: "Depois de pagar tudo, ficam {valor} livres por mês. Só que as dívidas listadas abaixo crescem {falta_total} por mês, juntas, porque a parcela de cada uma não cobre os juros. O valor livre não é suficiente para estancar esse crescimento, e por isso o plano abaixo é provisório." (a palavra "sobra" não é usada em estabilização, `GAB-04`)
- Por dívida: "{credor}: parcela de R$ {parcela}, juros de R$ {juros} por mês, o saldo aumenta R$ {falta} por mês."

**Orientação ao aluno (`OQ-71`, respondida em 2026-11-03):** o caso é parecido com pagar só o mínimo do cartão ou do cheque especial. O aluno recebe a **mesma** orientação em todos os casos, **nesta ordem**: (1) reduzir gastos, e a lista dos maiores gastos aparece junto; (2) renegociar a dívida que mais cresce. Os textos e as aulas vêm só do curso (aulas 5, 10, 11 e 14; `docs/curso-ssd/`) e não o contradizem: a aula 10.1 usa o corte como caixa para negociar e alerta para acordos que só alongam o prazo. Só lê e formata números do motor (`AC-42`). O aviso antes do envio (`RF-453`) segue só para resultado negativo. Plano sem dívida que cresce, ou em que a sobra cobre as faltas: sem mudança, e o último mês nunca escreve "todas quitadas" se restar saldo ("Fim da projeção em {mês}: ainda restam R$ Z").

### RF-481. Dívida que não quita no horizonte aparece na ordem, com o fato
A tabela da ordem de quitação (PDF e tela) e o cartão da dívida mostram **todas** as dívidas de `ORDEM_QUITACAO` (`RF-512`). Para a que não tem mês de quitação no cronograma, no lugar do mês aparece o texto "Não será quitada com os valores de hoje" (chave nova em `textos-canonicos.yaml`, **a aprovar pelo produto**), sem prazo, sem custo e sem inventar mês. O plano continua provisório quando o motor está em estabilização (`RF-465`). Só lê e formata números do motor (`AC-42`). Plano em que todas as dívidas têm mês de quitação: sem mudança.

| ID | Critério |
| -- | -------- |
| `AC-514` | Dado o `aluno.teste3` (4 dívidas, 2 delas sem quitação no horizonte), então a tabela da ordem do PDF e da tela tem 4 linhas, e as duas últimas trazem "Não será quitada com os valores de hoje" e nenhum mês (`RF-481`) |

## Fora do escopo

Mudar o motor, o questionário ou a regra que rebaixa a ordem a `PROVISORIA` (`engine/ordem.py`). A apresentação do aluno deficitário está em [`specs/aluno-deficitario.spec.md`](aluno-deficitario.spec.md).

## Open Questions

| ID | Pergunta | Status |
| -- | -------- | ------ |
| `OQ-71` | Qual orientação o aluno recebe quando a sobra não cobre o crescimento das dívidas (renegociar, cortar gasto, outra)? | `respondida (2026-11-03, especialista)` — os dois, nesta ordem: reduzir gastos e depois renegociar; a mesma orientação em todos os casos (`T-472`) |

As demais redações foram aprovadas pelo produto em 2026-10-29; o texto do `RF-480` e os dois passos da `OQ-71` (`T-472`) foram aprovados pelo produto em 2026-11-03.
