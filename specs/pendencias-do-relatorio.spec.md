# Spec — pendências e redação do relatório do aluno

| Campo | Valor |
| ----- | ----- |
| Slug  | `pendencias-do-relatorio` |
| Origem | Pedido do produto de 2026-10-29, a partir da prévia do caso de teste do Guilherme (aluno deficitário). |

## Problema

O relatório lista, em "O que falta informar", dados que o aluno não tem como informar: quanto pagar para quitar hoje (campo que o questionário já não pergunta desde a `T-408`, e o motor usa o saldo no lugar) e o valor da parcela de uma dívida que o próprio aluno declarou não ter parcela definida. O banner e a pergunta frequente dizem "este plano é definitivo" mesmo quando o plano é provisório. Uma linha da tabela "Seu ponto de partida" tem o rótulo de um total que é, na verdade, o resultado antes das parcelas.

## Requisitos

- **`RF-461`** — "O que falta informar" só lista dado que o aluno pode informar. `VALOR_QUITACAO_HOJE` não é auditado como pendência.
- **`RF-462`** — `PARCELA_CONTRATUAL` desconhecida não é pendência quando o aluno respondeu que a dívida não tem parcela definida (`POSSUI_PARCELA_DEFINIDA = NAO`): a ausência é estrutural.
- **`RF-463`** — Sem pendência real, o relatório (PDF e tela) não traz a seção "O que falta informar" nem o aviso "ainda é provisório porque faltam informações". Inventário incompleto continua sendo pendência real.
- **`RF-464`** — O botão "Responder agora" de uma pendência sempre aponta para uma pergunta que existe no questionário.
- **`RF-465`** — Plano provisório (`ORDEM_STATUS = PROVISORIA` ou modo estabilização) não é chamado de "definitivo" no banner nem na pergunta "Quando o meu plano muda?". Plano definitivo mantém o texto atual.
- **`RF-466`** — A linha que soma renda − despesas, antes das parcelas de dívida, tem o rótulo "Resultado do mês antes das parcelas de dívida (renda − despesas)". Substitui o texto da `RF-412` (`B3.DF02`).
- **`RF-467`** — Nenhuma pergunta que o aluno responde deixa de ser exigida: a guarda de envio continua recusando toda pergunta `indispensavel` exigível sem resposta.

## Fora do escopo

Mudar o motor, o questionário ou a regra que rebaixa a ordem a `PROVISORIA` (`engine/ordem.py`). A apresentação do aluno deficitário está em [`specs/aluno-deficitario.spec.md`](aluno-deficitario.spec.md).

## Open Questions

Nenhuma. As redações novas foram aprovadas pelo produto em 2026-10-29.
