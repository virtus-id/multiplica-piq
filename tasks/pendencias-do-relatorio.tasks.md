# Backlog — pendências e redação do relatório

| Campo | Valor |
| ----- | ----- |
| Slug  | `pendencias-do-relatorio` |
| Spec  | [`specs/pendencias-do-relatorio.spec.md`](../specs/pendencias-do-relatorio.spec.md) |
| Plano | [`plans/pendencias-do-relatorio.plan.md`](../plans/pendencias-do-relatorio.plan.md) |

> Numeração contínua (última: `T-445`).

### `T-446` — Pendências só do que o aluno pode informar
- **Rastreia:** `RF-461`, `RF-462`, `RF-463`, `RF-464`
- [x] `VALOR_QUITACAO_HOJE` fora de `_CAMPOS_MATERIAIS_DA_DIVIDA`; `PARCELA_CONTRATUAL` ignorada quando a dívida não tem parcela definida (`VocabularioDoCaso.dividas_sem_parcela_definida`, lido em `vocabulario_do_caso`); `_pendencias` devolve `None` sem pendência real; `pergunta_do_campo`, `onde_achar` e `rotulos_de_pendencia` sem o campo removido; teste estático do mapa de perguntas.

### `T-447` — Plano provisório não é "definitivo"
- **Rastreia:** `RF-465`
- [x] `corpo_provisorio` e `duvidas_provisorio` no YAML; escolha em `montar_contexto_plano`; `duvidas` em `ContextoPlano`, no template, no PDF e na serialização.

### `T-448` — Rótulo do resultado antes das parcelas
- **Rastreia:** `RF-466`
- [x] Novo rótulo no YAML e na spec `RF-412`.

### `T-449` — Regressão da guarda de envio
- **Rastreia:** `RF-467`
- [x] Teste: pergunta `indispensavel` exigível sem resposta impede o envio.

> Verificado em 2026-10-29: `pytest` completo com as mesmas 28 falhas do `HEAD` (nenhuma nova), `mypy` limpo, `ruff` sem erro novo, `vitest` com as mesmas 8 falhas do `HEAD`. Testes novos em `tests/app_aluno/test_pendencias_do_relatorio.py` e `frontend/tests/unit/componentes/PlanoDoDeficitario.test.tsx`.

### `T-462` — Dívida que cresce no relatório (limite de 24 meses, aviso e último mês)
- **Rastreia:** `RF-480`
- **Bloqueada por:** aprovação da spec (`OQ-55` do `motor-calculo`).
- [ ] Contexto e templates: aviso por dívida, mural e fichas mensais limitados, nota de limite, "Fim da projeção" no último mês, totais do prognóstico, dívidas fora da ordem
- [ ] Mesmo comportamento na tela do aluno (`PlanoDoAluno.tsx`)
- [ ] Testes: último mês com saldo não diz "todas quitadas"; parcela < juros gera o aviso e o limite; plano sem dívida que cresce inalterado

**Status:** `[ ] pendente — aguardando aprovação da spec`

