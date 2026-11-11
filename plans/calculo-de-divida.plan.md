# Plano Técnico — cálculo de dívida (saldo, parcela, taxa e prazo)

| Campo  | Valor |
| ------ | ----- |
| Slug   | `calculo-de-divida` |
| Spec   | [`specs/calculo-de-divida.spec.md`](../specs/calculo-de-divida.spec.md) (e [`discovery`](../specs/calculo-de-divida.discovery.md)) |
| Status | `rascunho` |
| Escopo | Fase 1 detalhada (`RF-514` a `RF-531`); Fases 2 e 3 em nível de arquitetura (`RF-532` a `RF-540`) |

> Numeração global: este plano abre `PD-01` a `PD-16` (decisões técnicas) e propõe `OQ-89` a `OQ-93` (seção 0.3), a continuar a da spec (último `OQ-88`). `engine/` não muda em nenhuma fase (`RF-531`, `AC-44`); a estratégia inteira existe para isso.

## 0. Decisões e questões resolvidas

### 0.1 Decisões técnicas

| # | Decisão | Por quê (requisito) |
| - | ------- | ------------------- |
| PD-01 | A calculadora é um módulo **puro** novo, `app/montagem/calculo_divida.py`: `Decimal` sob `engine.precisao.CONTEXTO_MOTOR`, `ln` e potência pelos métodos do próprio `Decimal` (`Decimal.ln`, `**`), sem `float`, sem I/O. Precedente: `app/montagem/entrada.py` ("agregação de entrada, nunca cálculo do motor refeito", Rodada 9) | `RF-514`, `RF-516`, `RF-531`, NFR Precisão. `engine/` é congelado; `engine/taxa.py` só converte ano→mês (reaproveitado, ver PD-04) |
| PD-02 | Toda constante `Decimal` do módulo (0, 1, centavo, teto, tolerâncias) nasce de `converter_para_dinheiro`/`converter_para_taxa` (padrão de `estado.py::_ZERO` e `entrada.py::_UM`). O módulo **não** chama `Decimal(...)` nem `dinheiro(...)`; `float` nunca | `RF-13` herdado; `tests/app_aluno/estatica/test_fronteira_decimal_unica.py` continua verde sem exceção nova |
| PD-03 | O **prazo** não sai só da fórmula fechada: ela apenas **semeia** o candidato; o valor final é confirmado pela mesma recorrência do motor (saldo × (1 + taxa) − min(pagamento, saldo + juros), precisão integral, sem tolerância de resíduo). Assim o prazo da tela é, por construção, o que o plano projeta | `RF-517`, `AC-526`, Risco 2 da spec |
| PD-04 | A taxa entra no cálculo sempre **normalizada ao mês** por `engine.taxa.derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA` (§16.1, já na allowlist de `app/`). A conversão inversa (mês→ano, só para devolver na periodicidade do aluno) é `(1 + i)^12 − 1` no módulo novo, sob o mesmo contexto com 10 dígitos de guarda que `engine/taxa.py` usa | `RF-522`, `EC-66` |
| PD-05 | Taxa incógnita: **Price** por bisseção (limite superior inicial `0,01` que dobra até envolver a solução); **SAC** por fórmula fechada (`i = P1/S − 1/n`, linear em `i`). Limites numéricos em 0.2 | `RF-516`, `AC-524`, `AC-525` |
| PD-06 | **Derivar, não armazenar.** As marcas `calculado`/`estimado`/`hipótese`/`pendente` e os valores calculados **não são gravados**: saem de uma função pura `resolver_divida(respostas, DIVIDA_ID)` em `app/montagem/premissas.py`, a cada leitura (mesmo princípio de `app/revisao/comprovacao.py`: "derivados a cada leitura, para que não exista segunda fonte que envelheça"). A resposta do aluno fica intacta (`NAO_SEI` onde ele não soube); o valor calculado existe só no estado entregue ao motor e nas telas | `RF-520`, `RF-526`, `RF-528`, `EC-70`, `EC-71` (invalidação gratuita: nada para apagar) |
| PD-07 | Única costura com o motor: `app/montagem/estado.py::montar_divida` passa a ler saldo, parcela e taxa de `resolver_divida`, em vez de ler as respostas cruas. Chega ao motor o que chega hoje: saldo, parcela (nos dois campos), taxa mensal normalizada e sistema; **nada de prazo** | `RF-531`, `AC-542` |
| PD-08 | A pergunta composta é **uma pergunta nova do registro**, `B5.CALC01`, com tipo novo `CALCULO_DIVIDA` (décimo `TipoResposta`), `OPT`+`REP`, primeira da ficha de dívida depois de `B5.A02`. Ela grava, por endpoint próprio, as **mesmas variáveis** que as perguntas individuais gravam. `B5.B03`, `B5.C02`, `B5.D06`, `B5.C02A` ficam como estão no registro (ID e variável estáveis), **sem virar condicionais** (justificativa em 0.4) | `RF-514`, `RF-523`, `RF-526`; "questionário é gerado, não codificado" (`sdd.config.md` §6) |
| PD-09 | Pré-visualização **sem estado**: `POST /caso/{CASO_ID}/calculadora/previa` não grava nada e sempre responde o resultado completo (ou o erro) para o conjunto de campos enviado; o servidor recalcula tudo, o front só exibe | Lei nº 3, `RF-519` (nada calculado é salvo em erro), `AC-529` |
| PD-10 | Dívida **pendente** (não resolvida por `resolver_divida`) **não entra** em `EstadoFinanceiro.dividas`; a montagem passa `INVENTARIO_COMPLETO = False` (leitura, não regra financeira), e o motor rebaixa sozinho a `ORDEM_STATUS = PROVISORIA` (`engine/ordem.py`). O "plano parcial" é uma marca de apresentação derivada da mesma lista | `RF-527`, `OQ-86`, `RF-465` |
| PD-11 | `pendencias_de_homologacao` ganha o conjunto `resolvidas` (campos que a calculadora resolveu): "não sei" em campo **calculado** não é `AUSENTE` | `RF-526`, `AC-538`; evita bloquear a liberação por dado que o sistema calculou |
| PD-12 | Todo texto ao aluno (erros, incompatibilidade, escolha de recalcular, pendente, parcial, perguntas novas) mora em YAML: `app/montagem/textos/calculadora.yaml` (calculadora) e `report/templates/plano/textos-canonicos.yaml` (relatório). Só a frase do `RF-519` está aprovada; o resto é **proposta a aprovar** | `AC-37`, spec §7 |
| PD-13 | **Sem migração de esquema e sem tabela nova** na Fase 1: tudo cabe em `respostas` (variáveis novas) e em derivação. `QUESTIONARIO_VERSION` sobe de `1.3.0` para `1.4.0` nos oito arquivos de `collection/registros/` | spec §5 Versionamento; migração só entra se `OQ-90` for decidida em contrário |
| PD-14 | O revisor recebe **apenas a marca** (`calculado`/`estimado`) por campo da dívida, dentro de `estado_inputs.dividas[].campos`; fórmula, total de juros e intermediários existem **só** na resposta da prévia | `RF-529`, `AC-540` |
| PD-15 | Observabilidade: três eventos nomeados, **sem valor algum do aluno** (`CALCULADORA_SEM_CONVERGENCIA`, `CALCULADORA_TETO_DE_TAXA`, `CALCULADORA_NAO_REDUZ_SALDO`), via `logging` estruturado; teste prova que o registro não carrega número | spec §5 Observabilidade e Segurança/LGPD |
| PD-16 | ~~Passagens do motor para achar a prioritária~~ **Revogada em 2026-11-06**: toda dívida estimável recebe a parcela de 24 meses, então não há prioritária a eleger e o motor roda uma vez só. `app/montagem/prioridade.py`, `avaliar_passagem` e `planejar_com_limite_async` foram removidos | `RF-534`, `RF-537`, `OQ-83` |
| PD-17 | **Mapeamento nos dois campos de pagamento: opção (A) da spec, decidido pelo especialista em 2026-11-06.** `PARCELA_CONTRATUAL` = habitual declarado (`0` quando ausente, com aviso; ressalva (a) aprovada); `PAGAMENTO_MENSAL_EFETIVO` = parcela estimada em toda dívida sem prazo e sem pagamento, habitual quando existe. Ressalva (b) **recusada**: o valor extra declarado é usado como está e o plano avisa quando passa da sobra (`avisos.ataque_acima_da_sobra`). (c) e (d) aprovadas. Não muda `engine/` | `RF-535`, `RF-537`, `RF-540`, `OQ-83`; seção 11.2 |

### 0.2 Limites numéricos (resolvem `OQ-79`; propostas para o especialista aprovar)

| Constante | Valor proposto | Justificativa |
| --------- | -------------- | ------------- |
| `LIMITE_INICIAL_TAXA` | `0,01` (1% ao mês) | Dado pela spec (`RF-516`). Dobra a cada passo até envolver a raiz |
| `TETO_TAXA_MENSAL` | `1,00` (100% ao mês) | Mais do que dobrar o saldo por mês é, na prática, erro de digitação do prazo ou da parcela; cobre o rotativo e o cheque especial sem recusar dado real. Vale como **validação de entrada** (`RF-518`, taxa já normalizada ao mês) e como **limite do resultado** (`RF-516`). O limite superior que dobra para em `min(2×, TETO)`; se ainda não envolver a raiz, é o erro do `RF-519` |
| `PRAZO_MAXIMO_MESES` | `480` (40 anos) | Cobre o financiamento imobiliário mais longo com folga; acima disso o prazo calculado quase sempre é a parcela raspando os juros (`EC-63`). Vale na entrada (prazo informado) e no resultado (prazo calculado) |
| `MAXIMO_ITERACOES_TAXA` | `100` bisseções (+ no máximo `7` dobras, `0,01 → 1,28`) | 100 passos reduzem o intervalo em `2^-100`, além do que `prec = 34` distingue; o custo é fixo e pequeno |
| `TOLERANCIA_TAXA` | largura do intervalo `≤ 1E-12` (fração) ou `|f(i)| ≤ 1E-9` R$ | Convergência bem abaixo da casa guardada (`1E-6` de fração) |
| `RESIDUO_DE_ARREDONDAMENTO` | `1E-9` R$ | Evita que `100,0000000000000000000000001` vire `100,01` no arredondamento para cima da parcela |

Pior caso de custo: `7 + 100` avaliações de `(1 + i)^-n` com `n ≤ 480` inteiro, em `prec = 44`: bem abaixo da meta de 500 ms no p95 (NFR), mesmo com a serialização.

### 0.3 Questões resolvidas e novas

| OQ | Resolução no plano | Onde |
| -- | ------------------ | ---- |
| `OQ-78` | **Grade fixa por campo, independente de quantas casas o aluno digitou**: dinheiro `± R$ 0,005`; taxa `± 0,005` ponto percentual (a máscara do front já limita a taxa a 2 casas, `mascaras.ts::formatarTaxa`); prazo **exato** (inteiro). Um "2" digitado vale `2,00 ± 0,005`, não `2 ± 0,5` | 4.3, 5.3 |
| `OQ-79` | Tabela 0.2 | 0.2 **Resolvida: limites aprovados pelo especialista (2026-11-06).** |
| `OQ-80` | Parcela: **para cima** ao centavo (`RF-520`). Prazo: para cima, inteiro. **Saldo calculado: para baixo** ao centavo (diverge da hipótese "mais próximo"): o centavo a mais faria sobrar resíduo e o plano passar de `n` para `n + 1` meses, o que contradiz `RF-517`/`AC-526`. `AC-518` (tolerância R$ 0,01) segue valendo. Ver `OQ-91` | 4.3 |
| `OQ-81` | A taxa calculada é guardada com **4 casas do percentual** (6 casas da fração), arredondada **para baixo** pelo mesmo motivo do saldo; exibida com 2 casas. Na periodicidade que o aluno escolheu (`RF-522`) | 4.3 |
| `OQ-86` | Pendente fora do estado do motor; `INVENTARIO_COMPLETO = False`; `PROVISORIA` pelo motor; **pode ir ao revisor**; a **liberação** ao aluno segue a guarda `RF-93` (ver `OQ-89`) | PD-10, 5.4, 10 |
| `OQ-77` | Hipótese da spec: arredondar para cima, `R$ 528,72` | PD-04, 9 **Resolvida: aprovado pelo especialista (2026-11-06): R$ 528,72.** |
| `OQ-82` | Hipótese da spec: cascata; candidatos = conjunto digitado + os quatro teóricos; entra quando não houve escolha do `RF-525`; empate pela ordem da ficha | 1.3 |
| `OQ-84` | Hipótese da spec: pendente e fora do plano, nunca zero | 1.2 **Resolvida (2026-11-06): entra no relatório com a parcela de 24 meses (não há mais exclusão por falta de mínimo)** |
| `OQ-85` | Hipótese da spec: habitual = `B5.C02` (variável `PARCELA_CONTRATUAL`); prazo e mínimo são perguntas novas; textos a aprovar | 3.1, 1.2 |
| `OQ-87` | Hipótese da spec: o revisor vê `calculado` e `estimado`; `hipótese` aparece como `estimado`; pendência segue `RF-461` | PD-14 |
| `OQ-88` | Hipótese da spec: a parcela SAC informada é sempre a de hoje (a maior); o texto de `B5.C02A` já diz isso | 4.3 |
| `OQ-73` a `OQ-76` | Hipóteses da spec (Fase 2) | 1.2 |
| `OQ-83` | **Spike**, primeira tarefa da Fase 2 | 1.2 |
| **`OQ-89` (nova)** | A guarda `RF-93` faz "não sei" em saldo, parcela ou taxa contar como `AUSENTE` e **bloquear a liberação** (`ErroHomologacaoBloqueada`). Com dívida pendente o plano parcial é calculado e vai ao revisor, mas **não é liberado ao aluno** enquanto a pendência existir. Isso esvazia parte de `US-408` ("sabendo que a dívida fica de fora do plano"). Hipótese adotada: manter `RF-93` (conservador, reversível com um predicado). Decidir antes de publicar a Fase 1 | 10 **Resolvida (especialista, 2026-11-06): o plano parcial é liberado ao aluno e aponta a pendência.** `campos_dispensados` inclui os campos que faltam na dívida pendente; `T-520` |
| **`OQ-90` (nova)** | `SnapshotOrdem` é do motor (congelado): marca e valor original **não cabem no snapshot** (NFR "entram no snapshot"). Hipótese: derivar das respostas atuais. Se o revisor precisar do histórico por versão, cria-se a tabela `premissas_do_plano` (append-only, migração `013`) | 10 **Decisão técnica da equipe (2026-11-06): mantém a derivação das respostas atuais** |
| **`OQ-91` (nova)** | Confirmar com o especialista: saldo e taxa calculados **para baixo** (justificativa em `OQ-80`) | 4.3 **Resolvida: aprovado pelo especialista (2026-11-06).** |
| **`OQ-92` (nova)** | `RF-513` diz que `R$ 0,00` digitado em `B5.C02` é pagamento zero válido; `RF-518`/`AC-527` recusam parcela `≤ 0` **na calculadora**. Hipótese: `0,00` continua resposta válida (dívida completa para o motor), mas **não entra no cálculo**; com os quatro informados e parcela `0,00`, a conferência acusa incompatível | 5.3 **Resolvida: aprovado pelo especialista (2026-11-06).** |
| **`OQ-95` (nova)** | Teto de R$ 1.000.000.000,00 para saldo e parcela na calculadora (`SALDO_ACIMA_DO_MAXIMO`/`PARCELA_ACIMA_DO_MAXIMO`, texto `[PROVISORIO T-507]`) e texto de até 64 caracteres por campo no corpo. Hipótese adotada para não devolver "não reduz o saldo" a valor absurdo; a confirmar com o especialista | 4.1 **Resolvida: aprovado pelo especialista (2026-11-06).** |
| **`OQ-93` (nova)** | `B5.C02A` deixa de ser `COND` e `indispensavel` para virar `OPT` (senão todo caso antigo trava). Perde a trava "sem sistema o motor adivinharia" do financiamento imobiliário. Hipótese: aceitável, porque `Price` é o padrão declarado (`RF-523`) e a pergunta composta sempre grava o sistema | 4.1 **Revertida (especialista, 2026-11-06): `B5.C02A` é obrigatória (`OBR`), padrão Price.** Caso antigo sem a resposta passa a ter uma pendência obrigatória |
| **`OQ-94` (nova)** | A spec (`AC-527`) lista só 0, negativo e prazo `2,5`; a tabela do plano (9.1) e `EC-69` acrescentam `1234.56` e `1.234,5` (`EC-69`: "lida pelo formato brasileiro ou recusada"). Hipótese adotada (a mais segura, sem regra nova): ponto sem vírgula só vale como **milhar** (`1.234`); `1234.56`, `12.5` e `1.5` (ponto decimal, que não é grafia brasileira) são recusados com `VALOR_ILEGIVEL`. `1.234,5` é grafia brasileira válida (milhar + vírgula) e continua **lido** como 1234,5. Confirmar com o especialista; se `1.234,5` também deve ser recusado, é uma linha em `_ponto_decimal` | 4.3 **Resolvida: aprovado pelo especialista (2026-11-06).** |

### 0.4 Por que `B5.B03`, `B5.C02` e `B5.D06` **não** viram condicionais (contra o pedido)

Uma `condicao_exibicao` falsa também fecha a pergunta para `_aberta()` em `app/revisao/comprovacao.py` e para `_e_exigivel_agora` em `app/casos/progresso.py`. Com a pergunta fechada, o "não sei" do aluno **deixaria de ser pendência** e a dívida pendente sumiria de "O que falta informar" (`RF-526`, `RF-461`). Em vez de esconder, as perguntas ficam abertas e a pergunta composta **responde por elas**: ao confirmar, grava `NAO_SEI` ou o valor em cada variável, e o fluxo (`proxima_pergunta_nao_respondida`) pula o que já tem resposta. Quem quiser corrigir um campo vai direto à pergunta individual ("Responder agora", `RF-464`).

## 1. Architecture Overview

### 1.1 Fase 1 — camadas

```text
 ficha da dívida (React)                                  servidor (FastAPI)
┌──────────────────────────┐   POST .../calculadora/previa     ┌────────────────────────────┐
│ CalculadoraDaDivida.tsx  │ ───────────────────────────────▶ │ app/http/rotas_calculadora │
│  4 campos + "não sei"    │ ◀─────────────────────────────── │  (valida, não grava)       │
│  + Price/SAC + escolha   │   resultado já formatado          └──────────────┬─────────────┘
│  de recálculo (RF-525)   │                                                  │ chama
│                          │   POST .../divida/{item}/         ┌──────────────▼─────────────┐
│  só exibe (Lei nº 3)     │        calculadora/confirmar      │ app/montagem/              │
│                          │ ───────────────────────────────▶ │  calculo_divida.py (puro)  │
└──────────────────────────┘   grava respostas + CONFERÊNCIA   │  conversao.py (fronteira)  │
                                                               └──────────────┬─────────────┘
 respostas (piq_app_aluno.respostas) ◀──────── grava ─────────────────────────┘
        │ lê (a cada leitura)
        ▼
 app/montagem/premissas.py::resolver_divida  ──▶ valores + marcas + situação (COMPLETA | PENDENTE | INCOMPATÍVEL)
        │                       │                          │
        ▼                       ▼                          ▼
 estado.py::montar_divida   report/plano.py           rotas de revisão
 (saldo, parcela, taxa,     (vocabulário: pendentes,   (marcas por campo,
  sistema → motor)           plano parcial, avisos)     sem fórmula)
        │
        ▼
 engine/ (inalterado)  →  ORDEM_STATUS = PROVISORIA se houver pendente (INVENTARIO_COMPLETO = False)
```

Regra de dependência (herdada de `sdd.config.md` §3): `calculo_divida.py` e `premissas.py` importam só de `engine.precisao`, `engine.tipos`, `engine.taxa` (já permitidos) e de `app/montagem/conversao.py`; nada em `engine/` importa deles.

### 1.2 Fase 2 — arquitetura (parcela estimada de 24 meses)

- **Spike primeiro (`OQ-83`).** Antes de qualquer pergunta nova ou mudança de montagem, um teste de caracterização monta um estado com duas dívidas (uma com habitual informado, uma sem parcela nem prazo) e observa, **sem tocar `engine/`**, como os dois campos de pagamento se propagam. O que a leitura do código já mostra e o spike precisa **confirmar ou refutar**:
  - `PARCELA_CONTRATUAL` alimenta `FALTA_DE_JUROS`, `RESULTADO_MENSAL_ATUAL` e, por ele, `CAPACIDADE_ATAQUE_*` e `MODO_ESTABILIZACAO` (`engine/diagnostico.py`). Dívida com `PARCELA_CONTRATUAL = DESCONHECIDO` é **pulada** em `calcular_faltas_de_juros` e fica de fora (parcial) das somas.
  - `PAGAMENTO_MENSAL_EFETIVO` alimenta `RESULTADO_CAIXA_OBSERVADO` (a tela do revisor rotula esse campo como "Resultado do mês"), o pagamento mensal da simulação (`ciclo_mensal._pagamento_normal_efetivo`), o fluxo liberado (`bola_de_neve`, `hibrido`) e a ordem (`ordem.py`). Com `DESCONHECIDO` a simulação "nem pode começar" (`beneficio_marginal`).
  - **Hipótese de problema (a medir):** com o mapeamento da spec (`RF-537`), a parcela de 24 meses na prioritária entra em `PAGAMENTO_MENSAL_EFETIVO` e a simulação a paga **além** da capacidade de ataque calculada sobre o devido; o fluxo de caixa simulado passa a exceder o orçamento declarado, e `RESULTADO_CAIXA_OBSERVADO` muda sem aviso (contradiz `RF-540`). Saída possível: `PAGAMENTO_MENSAL_EFETIVO` = mínimo (ou habitual) em todas e a parcela de 24 meses vira **referência de apresentação e de ordenação**, com o excesso saindo pelo ataque do próprio motor (que já é "mínimo em todas, extra concentrado em uma").
  - **Pergunta do spike para `RF-535`:** habitual **ausente** não pode ser `DESCONHECIDO` no campo devido (o motor pula a dívida no alerta de crescimento) nem `0` (viraria zero silencioso). O spike decide se o alerta de crescimento precisa de um valor derivado na montagem ou de uma decisão sobre `engine/`.
  - Resultado do spike: relatório curto em `plans/` (ou seção 11 deste plano) com a tabela caso × campo × resultado do mês × alerta, e a **escolha do mapeamento**: (A) o da spec; (B) o alternativo acima; (C) parar e pedir decisão sobre `engine/` (`OQ-83`).
- **Montagem.** `resolver_divida` ganha a hipótese: saldo e taxa conhecidos, sem parcela e sem prazo (ou habitual `0`/ausente e sem prazo) ⇒ `parcela_estimada` = calculadora com `n = 24` e o sistema da dívida (marca `estimado`, hipótese `PRAZO_24_MESES`); prazo contratual ou habitual `> 0` prevalecem (`OQ-73`). `PRAZO_BASE_ESTIMATIVA_MESES = 24` fica numa constante nomeada.
- **Prioritária (`PD-16`).** Passo 1: monta o estado com todas as estimáveis pagando o mínimo e roda `engine.motor.calcular_plano` em processo, sem gravar snapshot, só para ler a dívida-alvo (`DIVIDA_ALVO` / primeira da `ORDEM_QUITACAO`). Passo 2: fixa a parcela de 24 meses nessa dívida, os mínimos nas outras e roda o cálculo definitivo. Se a alvo mudar no passo 2 (empate em `H-04` nível 3, que lê o fluxo liberado), repete até 3 passagens; sem estabilizar, fica no passo 1 e marca a dívida `hipótese`. O executor deixa de ser "uma única chamada" (`app/motor/executor.py`), o que pede ajustar a barra de progresso (`TelaCalculando`).
- **Perguntas novas.** `B5.C02C` (pagamento mínimo, `MOEDA`, "não sei" permitido, variável `PAGAMENTO_MINIMO_DIVIDA`) em toda dívida; `B5.C02` (habitual, `PARCELA_CONTRATUAL`) ganha redação nova (`OQ-85`, a aprovar). Sobe a versão do questionário (`1.5.0`).
- **Exibição.** A parcela estimada vai em **linha separada e marcada** na prévia e na tabela do revisor, nunca no campo digitado (`RF-533`, `AC-545`). O texto não cita 24 meses quando há prazo contratual ou habitual `> 0` (`RF-536`).
- **Pendência (`OQ-84`).** Dívida não prioritária sem mínimo e sem habitual: `PENDENTE`, fora do plano (`PD-10`).

### 1.3 Fase 3 — arquitetura (cenário conservador)

- Módulo puro novo `app/montagem/cenario_conservador.py`, chamado só por `resolver_divida` quando a situação é `INCOMPATIVEL` **e** não há escolha válida do `RF-525`.
- **Candidatos (`OQ-82`):** o conjunto digitado e quatro "teóricos" (cada um recalcula um dos quatro campos a partir dos outros três pela própria `calculo_divida`). Candidato que falha no cálculo (teto, não converge) é descartado.
- **Escolha:** ordenação lexicográfica por parcela, saldo, taxa, prazo, custo total (soma dos pagamentos do cronograma de `calculo_divida.cronograma`), tudo "maior primeiro"; empate total vale o primeiro na ordem da ficha (`EC-76`): digitado, saldo, parcela, taxa, prazo.
- **Injeção no motor (`RF-539`, `RF-540`):** só `SALDO_DEVEDOR_ATUAL` e `TAXA_EFETIVA_MENSAL_NORMALIZADA` do cenário. Os dois campos de pagamento seguem com o que o aluno declarou. As marcas do saldo e da taxa viram `hipótese` (`CENARIO_CONSERVADOR`); o revisor as vê como `estimado` (`OQ-87`).
- **Cuidado com `test_sem_aritmetica_sobre_snapshot`:** o detector reage ao nome de variável `cenario`/`cenario_recomendado`; no módulo novo os candidatos se chamam `candidato`/`hipotese`.

## 2. Tech Stack

Nenhuma dependência nova. Cada linha ancora a escolha em um requisito.

| Escolha | Uso | Justificativa (e alternativa descartada) |
| ------- | --- | --------------------------------------- |
| Python 3 + `decimal` da stdlib (`Decimal.ln`, `**`, `localcontext`, `Context`) | Calculadora, bisseção, logaritmo, potência | `RF-514`, `RF-516`, NFR Precisão. `ln` e potência já existem no `Decimal` com precisão controlada pelo contexto; descartado `math.log`/`math.pow` (devolvem `float`, proibido por `RF-13`) e descartado biblioteca de terceiros (`mpmath`): dependência nova sem necessidade |
| `engine.precisao.CONTEXTO_MOTOR` (+ contexto de guarda de `prec + 10`) | Contexto único | `RF-516`; mesma técnica de `engine/taxa.py` para `(1+i)^(1/12) − 1` |
| `engine.taxa.derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA` | Taxa anual → mensal | `RF-522` ("a conversão é a do motor, sem alteração"); já na allowlist de `test_fronteira_import_engine.py`, sem exceção nova |
| FastAPI (já em uso) | `rotas_calculadora.py`: prévia e confirmar | `RF-519`, `AC-529`. Rota síncrona (`def`), no pool de threads, como as demais rotas de ficha |
| Pydantic (já traz o FastAPI) | Corpo JSON da prévia (campos que aceitam `null`) | `RF-518`. As rotas atuais usam `_ler_formulario` (texto plano); aqui há ausência significativa (`null` = "não sei"), por isso corpo tipado |
| PyYAML (já em uso) | Textos novos, registro novo | `AC-37` (texto é dado); mesmo mecanismo de `app/montagem/textos/avisos.yaml` |
| React + TypeScript + Vite (já em uso) | `CalculadoraDaDivida.tsx` | `RF-519`, `RF-525`; Lei nº 3: o componente só exibe. Descartado biblioteca de formulário (o componente tem 5 campos) |
| `pytest` + `hypothesis` (já em `pyproject.toml`) | Fórmulas, propriedades (ida e volta, tela = motor) | `RF-517`, `AC-526`; propriedade vale mais que 30 casos fixos |
| `vitest` + Testing Library (já em uso) | Componente | `AC-529`, `RF-519` |
| `ruff`, `mypy --strict` | Qualidade | `sdd.config.md` §2 |

> Mantida a stack existente: a feature é calculadora + derivação + um componente. Trocar qualquer peça criaria risco sem requisito que o peça.

## 3. Project Structure

### 3.1 Fase 1

| Caminho | Responsabilidade | Novo? |
| ------- | ---------------- | ----- |
| `app/montagem/calculo_divida.py` | Fórmulas Price/SAC das quatro incógnitas, bisseção, cronograma, arredondamentos, validações, conferência de compatibilidade. Puro | sim |
| `app/montagem/premissas.py` | `resolver_divida`: valores, marcas, situação, faltas, escolha de recálculo. Puro | sim |
| `app/montagem/textos/calculadora.yaml` | Mensagens (erros por código, incompatibilidade, escolha, rótulos de marca, perguntas novas) | sim |
| `app/montagem/estado.py` | `montar_divida` lê de `resolver_divida`; `montar_estado_financeiro` recebe `dividas_pendentes`; `_inventario_completo` | não |
| `app/montagem/conversao.py` | Sem mudança de contrato; as constantes novas passam por ele. Eventual `converter_para_inteiro`/`converter_para_prazo` só se a leitura de "prazo" pedir (preferir reusar `converter_para_dinheiro` e checar inteiro) | não |
| `app/http/rotas_calculadora.py` | `POST /caso/{CASO_ID}/calculadora/previa` e `POST /caso/{CASO_ID}/divida/{item_id}/calculadora/confirmar` | sim |
| `app/http/aplicacao.py` | Registra o roteador | não |
| `app/http/rotas_calculo.py` | `_montar_dividas_do_caso` omite pendentes; recusa quando todas pendentes (`EC-74`); passa `dividas_pendentes` | não |
| `app/http/rotas_coleta.py` | Recusa `POST /resposta` para tipo `CALCULO_DIVIDA` (só o endpoint da calculadora grava) | não |
| `app/http/serializacao.py` | Serializa a pergunta `CALCULO_DIVIDA` (enunciado, apoio, `sistema` padrão) | não |
| `app/revisao/comprovacao.py` | `pendencias_de_homologacao(..., resolvidas)` (PD-11) | não |
| `app/http/rotas_revisao.py`, `rotas_inicio.py`, `app/revisao/fila.py` | Passam `resolvidas`; revisão leva as marcas por dívida | não |
| `app/http/serializacao_plano.py` | `vocabulario_do_caso` leva pendentes e plano parcial; `serializar_estado_inputs` leva as marcas | não |
| `report/plano.py` | `VocabularioDoCaso`: `dividas_pendentes`, `plano_parcial`; `_avisos_gerais` e `_pendencias` listam a dívida pendente e o dado que falta | não |
| `report/templates/plano/textos-canonicos.yaml` | Chaves novas: dívida pendente, plano parcial | não |
| `collection/registros/bloco-05.yaml` | `B5.CALC01` (nova), `B5.C02B` (nova), ajustes em `B5.B03`, `B5.C02`, `B5.D06`, `B5.C02A`; versão `1.4.0` | não |
| `collection/registros/bloco-0{1,2,3,4,9,12-*}.yaml` | Só o `QUESTIONARIO_VERSION` | não |
| `collection/registro.py`, `collection/carga.py` | `TipoResposta.CALCULO_DIVIDA`; validação de carga do tipo novo | não |
| `frontend/src/componentes/CalculadoraDaDivida.tsx` | A tela do cálculo | sim |
| `frontend/src/telas/TelaPergunta.tsx` | Ramo para `tipo === 'CALCULO_DIVIDA'` | não |
| `frontend/src/tipos.ts`, `frontend/src/services/api.ts` | `TipoResposta`, tipos da prévia, `preverCalculadora`, `confirmarCalculadora` | não |
| `frontend/src/componentes/revisao/PartesDaConferencia.tsx` | `Celula` ganha a marca (chip "calculado"/"estimado") | não |
| `tests/app_aluno/test_calculo_divida_*.py`, `test_premissas_da_divida.py`, `test_rotas_calculadora.py`, `test_montagem_divida_calculada.py` | Testes por AC (seção 9) | sim |
| `tests/app_aluno/test_remocao_sem_efeito.py`, `test_sac_imobiliario.py`, `test_pendencias_do_relatorio.py`, `test_custo_da_divida.py`, `test_ficha_enxuta.py`, `test_carga.py` e os que citam `1.3.0` | Atualizados pelas revogações (`RF-510`/`T-465`, `T-411`, `RF-513`) | não |

### 3.2 Fases 2 e 3 (a criar)

| Caminho | Fase | Responsabilidade |
| ------- | ---- | ---------------- |
| `tests/app_aluno/test_spike_pagamentos_da_divida.py` | 2 | Spike `OQ-83` (`AC-549`) |
| `app/montagem/prioridade.py` | 2 | Passagens do motor para a dívida prioritária (`PD-16`) |
| `app/motor/executor.py`, `app/http/rotas_calculo.py` | 2 | Executor com mais de uma passagem; progresso |
| `app/montagem/cenario_conservador.py` | 3 | Candidatos e cascata (`OQ-82`) |
| `collection/registros/bloco-05.yaml` | 2 | `B5.C02C` |

## 4. Data Model

### 4.1 Registro (Fase 1)

| Pergunta | Mudança | `VARIAVEL_GRAVADA` | Obrigatoriedade | "Não sei" |
| -------- | ------- | ------------------ | --------------- | --------- |
| `B5.CALC01` **(nova)** | Tipo `CALCULO_DIVIDA`, escopo `DIVIDA_ID`, ordem logo após `B5.A02`. Enunciado, apoio e rótulos em texto a aprovar | `CONFERENCIA_DA_DIVIDA` (`CONFIRMADA`) | `OPT`, `REP` | não se aplica (cada campo tem o seu) |
| `B5.B03` | `admite_nao_sei: true`; sai a nota "sem não sei (T-411)" | `SALDO_DEVEDOR_ATUAL` | `OBR`, `REP`; `indispensavel` mantido (`OQ-89`) | sim |
| `B5.C02` | `admite_nao_sei: true`. Passa a ser o **pagamento habitual** (`OQ-85`); enunciado na Fase 2 | `PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)` | `OBR`, `REP`; `indispensavel` mantido | sim |
| `B5.C02A` | Sai a `condicao_exibicao` (`RF-523`); texto sem "financiamento" nem afirmar que é o do credor | `SISTEMA_AMORTIZACAO` | `OPT`, `REP`; `indispensavel: false` (`OQ-93`) | não |
| `B5.C02B` **(nova)** | Prazo restante em meses, `NUMERO` | `PRAZO_RESTANTE_MESES` | `OPT`, `REP` | sim |
| `B5.D06` | Terceira opção "Não sei a taxa" (`valor_interno: DESCONHECIDA`, `admite_nao_sei: true`), mesmo precedente de `T-283` | `PERIODICIDADE_TAXA_DIVIDA` + `TAXA_DIVIDA` | `OBR`, `REP`; `indispensavel` mantido | sim, pela opção |

Por que `OPT` na pergunta composta e no prazo: casos antigos não têm essas respostas; `OBR` os travaria em `pendencias_obrigatorias`. `OPT` entra na retomada (`_e_pergunta_aberta`), então a pergunta aparece no fluxo do aluno novo sem bloquear `calcular` nem o envio. Variáveis novas: `CONFERENCIA_DA_DIVIDA`, `PRAZO_RESTANTE_MESES`, `INFORMACAO_A_RECALCULAR`. Nenhum ID reaproveitado (`B5.C03` a `B5.C07A` são histórico; `B5.CALC01` e `B5.C02B` nunca existiram).

### 4.2 Respostas gravadas (`piq_app_aluno.respostas`, sem mudança de esquema)

Uma linha por `(CASO_ID, ID_PERGUNTA, item_id)`, como hoje. A confirmação grava, por dívida: `SALDO_DEVEDOR_ATUAL`, `PARCELA_CONTRATUAL (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)`, `PERIODICIDADE_TAXA_DIVIDA`, `TAXA_DIVIDA`, `PRAZO_RESTANTE_MESES`, `SISTEMA_AMORTIZACAO`, `INFORMACAO_A_RECALCULAR` e, por último, `CONFERENCIA_DA_DIVIDA = CONFIRMADA`. Campo que o aluno não informou (ou que ele deixou a calculadora resolver) grava `NAO_SEI`, nunca `0`. `INFORMACAO_A_RECALCULAR` guarda `"<CAMPO>|<impressão>"`, em que a impressão é um resumo curto (hash) dos quatro valores digitados e do sistema: a escolha só vale enquanto esses valores forem os mesmos (`EC-70` sem hook de invalidação). Sem escolha, grava `NENHUMA`.

### 4.3 Contratos do módulo de cálculo (assinaturas, não implementação)

```python
# app/montagem/calculo_divida.py
class CAMPO_DA_DIVIDA(Enum):          # SALDO, PARCELA, TAXA, PRAZO

class CODIGO_ERRO_DE_CALCULO(Enum):   # NAO_REDUZ_SALDO, SEM_CONVERGENCIA,
                                      # TAXA_ACIMA_DO_TETO, PRAZO_ACIMA_DO_MAXIMO

class CODIGO_ERRO_DE_ENTRADA(Enum):   # VALOR_ILEGIVEL, SALDO_NAO_POSITIVO,
                                      # PARCELA_NAO_POSITIVA, TAXA_NEGATIVA,
                                      # TAXA_ACIMA_DO_TETO, PRAZO_NAO_INTEIRO,
                                      # PRAZO_NAO_POSITIVO, PRAZO_ACIMA_DO_MAXIMO

class ErroDeEntrada(Exception):  campo: CAMPO_DA_DIVIDA; codigo: CODIGO_ERRO_DE_ENTRADA
class ErroDeCalculo(Exception):  codigo: CODIGO_ERRO_DE_CALCULO

@dataclass(frozen=True, slots=True)
class EntradaDaDivida:                 # tudo já Decimal, taxa já MENSAL normalizada
    saldo: Dinheiro | None
    parcela: Dinheiro | None
    taxa_mensal: Taxa | None
    prazo: int | None
    sistema: SISTEMA_AMORTIZACAO

def validar_entrada(...) -> EntradaDaDivida            # RF-518; texto brasileiro -> tipos (via conversao.py)
def calcular_parcela(saldo, taxa_mensal, prazo, sistema) -> Dinheiro      # cima ao centavo, RF-520
def calcular_saldo(parcela, taxa_mensal, prazo, sistema) -> Dinheiro      # baixo ao centavo, OQ-80
def calcular_taxa(saldo, parcela, prazo, sistema) -> Taxa                 # 6 casas da fração, baixo, OQ-81
def calcular_prazo(saldo, parcela, taxa_mensal, sistema) -> int           # RF-517, confirmado pela recorrência

@dataclass(frozen=True, slots=True)
class LinhaDoCronograma:  mes: int; amortizacao: Dinheiro; juros: Dinheiro; pagamento: Dinheiro; saldo_final: Dinheiro
def cronograma(saldo, parcela, taxa_mensal, prazo, sistema) -> tuple[LinhaDoCronograma, ...]
    # RF-517/RF-521: último pagamento calculado; SAC confere soma das amortizações = saldo
def total_de_juros(cronograma) -> Dinheiro        # só para a prévia (RF-529)

class COMPATIBILIDADE(Enum):  COMPATIVEL, INCOMPATIVEL
def conferir_compatibilidade(entrada, taxa_digitada, periodicidade) -> tuple[COMPATIBILIDADE, Dinheiro]
    # devolve também a parcela teórica; grade de OQ-78; compara na eixo da parcela
```

Regras de arredondamento e precisão (resolvem `OQ-80`/`OQ-81`):

| Valor | Regra | Por quê |
| ----- | ----- | ------- |
| Parcela calculada | para cima ao centavo, depois de arredondar a `RESIDUO_DE_ARREDONDAMENTO` | `RF-520` |
| Saldo calculado | para baixo ao centavo | `RF-517`, `AC-526` (ver `OQ-91`) |
| Taxa calculada | para baixo, 6 casas da fração (4 do percentual); exibe 2 | `RF-522`; mesmo motivo do saldo |
| Prazo calculado | meses inteiros, para cima, confirmado pela recorrência | `RF-517`, PD-03 |
| Cronograma exibido | em centavos; o resíduo da divisão da amortização cai na última parcela | `AC-531`. O valor interno do motor segue em precisão integral |
| Valor calculado exibido = valor usado no motor | princípio: a tela nunca mostra um valor diferente do que entra no plano | `RF-517`, `AC-526` |

Caminhos de cálculo (resumo para o implementador, não a fórmula completa):

| Incógnita | Price | SAC (parcela informada = a de hoje, `OQ-88`) |
| --------- | ----- | --------------------------------------------- |
| Parcela | anuidade; taxa 0 ⇒ `S/n` | `S/n + S·i` |
| Saldo | valor presente das parcelas; taxa 0 ⇒ `P·n` | `P1 / (1/n + i)` |
| Taxa | bisseção (0.2); `S/n` dentro de meio centavo de `P` ⇒ taxa `0` | `P1/S − 1/n`; negativa ⇒ erro do `RF-519` |
| Prazo | `−ln(1 − S·i/P) / ln(1+i)` semeia; recorrência confirma; `P ≤ S·i` ⇒ `NAO_REDUZ_SALDO`; `> 480` ⇒ `PRAZO_ACIMA_DO_MAXIMO` | `a = P1 − S·i`; `a ≤ 0` ⇒ `NAO_REDUZ_SALDO`; `n = ⌈S/a⌉` |

Conferência de compatibilidade (`RF-524`, `OQ-78`): a parcela é monótona crescente em saldo e em taxa, então o intervalo teórico é `[P(S−δS, i−δi, n), P(S+δS, i+δi, n)]`, com `δS = 0,005`, `δi = 0,005 ponto percentual` (aplicado na periodicidade digitada e renormalizado), prazo exato. Compatível quando esse intervalo encontra `[parcela ± 0,005]`. Exemplo: `R$ 10.000`, 2% a.m., 24 meses ⇒ a taxa sozinha move a parcela em cerca de `± R$ 0,30`, por isso `R$ 528,71` é compatível (`AC-535`) e `R$ 400,00` não (`AC-534`).

### 4.4 Contratos de derivação

```python
# app/montagem/premissas.py
class MARCA_DO_VALOR(Enum):       # INFORMADO, CALCULADO, ESTIMADO, HIPOTESE, PENDENTE
class SITUACAO_DA_DIVIDA(Enum):   # COMPLETA, PENDENTE, INCOMPATIVEL

@dataclass(frozen=True, slots=True)
class ValorDaDivida:
    campo: CAMPO_DA_DIVIDA
    valor: Dinheiro | int | None        # None só quando PENDENTE
    marca: MARCA_DO_VALOR
    original: Dinheiro | int | None     # o que o aluno digitou, quando difere de `valor`

@dataclass(frozen=True, slots=True)
class PremissasDaDivida:
    DIVIDA_ID: str
    sistema: SISTEMA_AMORTIZACAO
    valores: Mapping[CAMPO_DA_DIVIDA, ValorDaDivida]
    taxa_mensal_normalizada: Taxa | None      # o que vai ao motor
    taxa_na_periodicidade: Taxa | None        # o que o aluno vê/escolheu
    situacao: SITUACAO_DA_DIVIDA
    faltas: tuple[CAMPO_DA_DIVIDA, ...]       # campos pendentes que impedem o motor
    parcela_teorica: Dinheiro | None          # só INCOMPATIVEL
    recalcular_escolhido: CAMPO_DA_DIVIDA | None

def resolver_divida(respostas: RespostasCaso, DIVIDA_ID: str) -> PremissasDaDivida
def dividas_pendentes(respostas, itens_por_escopo) -> tuple[PremissasDaDivida, ...]
def campos_resolvidos(...) -> frozenset[tuple[str, str]]       # (item_id, VARIAVEL_GRAVADA), PD-11
```

**Tabela-verdade da situação** (Fase 1; os quatro campos são saldo S, parcela P, taxa T, prazo N; "ok" = informado e válido):

| Desconhecidos | Resultado | Marca do que faltava |
| ------------- | --------- | -------------------- |
| nenhum (4 ok) | `COMPLETA` se compatível; `INCOMPATIVEL` se não. Com escolha válida do `RF-525`, o campo escolhido vira o teórico | `CALCULADO` só no escolhido |
| só N | `COMPLETA` (N não vai ao motor); a prévia mostra o prazo calculado | N: `CALCULADO` |
| só S, P ou T | `COMPLETA` | o campo: `CALCULADO` |
| N e mais um de S/P/T, ou dois ou mais de S/P/T | `PENDENTE` (`faltas` lista os de S/P/T) | `PENDENTE` |
| P informado `0,00` e S, T ok | `COMPLETA` (pagamento zero é resposta válida, `OQ-92`); N não é calculado | — |

A tabela é testada inteira (2⁴ combinações × Price/SAC, seção 9). Fase 2 estreita a linha "N e mais um": saldo e taxa ok sem P e sem N deixam de ser `PENDENTE`.

### 4.5 Contratos HTTP e tipos do front

```ts
// frontend/src/tipos.ts (acréscimos)
type TipoResposta = ... | 'CALCULO_DIVIDA'
type CampoDaDivida = 'SALDO' | 'PARCELA' | 'TAXA' | 'PRAZO'
type MarcaDoValor = 'INFORMADO' | 'CALCULADO' | 'PENDENTE'     // F2/F3: + 'ESTIMADO' | 'HIPOTESE'
interface CorpoDaCalculadora {
  sistema: 'PRICE' | 'SAC'
  periodicidade: 'MENSAL' | 'ANUAL'
  saldo: string | null; parcela: string | null; taxa: string | null; prazo: string | null
  recalcular: CampoDaDivida | null
}
interface ValorCalculado { texto: string; entrada: string; marca: MarcaDoValor }  // texto formatado e texto para o input
interface RespostaDaPrevia {
  estado: 'CALCULADO' | 'CONFERIDO' | 'INCOMPATIVEL' | 'PENDENTE' | 'SEM_CALCULO' | 'ERRO'
  campo_calculado: CampoDaDivida | null
  valores: Partial<Record<CampoDaDivida, ValorCalculado>>
  teorico: { campo: CampoDaDivida; texto: string } | null
  alternativas: CampoDaDivida[]            // só INCOMPATIVEL
  resumo: { prazo: number; primeira_parcela: string; ultimo_pagamento: string; total_de_juros: string } | null
  erros: { campo: CampoDaDivida; codigo: string; mensagem: string }[]
  mensagem: string | null                  // a frase do RF-519 em ERRO de cálculo
}
```

Contratos de rota:

| Rota | Entrada | Saída | Efeito |
| ---- | ------- | ----- | ------ |
| `POST /caso/{CASO_ID}/calculadora/previa` | `CorpoDaCalculadora` (JSON). Texto na grafia brasileira (`"10.000,00"`, `"2,00"`, `"24"`); `null` ou `""` = desconhecido | `200` com `RespostaDaPrevia` (erro de **negócio** também é `200`, com `estado: ERRO`/`erros`); `400` corpo malformado; `401/403` sessão e isolamento (`exigir_caso_da_sessao`); `503` falha interna (`EC-77`) com `{"erro": ...}` | **Nenhum** (`AC-529`) |
| `POST /caso/{CASO_ID}/divida/{item_id}/calculadora/confirmar` | mesmo corpo | `200` `{ID_PERGUNTA, proxima, avisos}` (mesma forma de `POST /resposta`); `409` coleta não editável (`exigir_coleta_editavel`); `422` entrada inválida, **nada gravado**; `404` item inexistente | Grava as respostas da seção 4.2, validando tudo antes e a marca `CONFERENCIA_DA_DIVIDA` por último |

Códigos de erro: `VALOR_ILEGIVEL` (`EC-69`), `SALDO_NAO_POSITIVO`, `PARCELA_NAO_POSITIVA`, `TAXA_NEGATIVA`, `TAXA_ACIMA_DO_TETO`, `PRAZO_NAO_INTEIRO`, `PRAZO_NAO_POSITIVO`, `PRAZO_ACIMA_DO_MAXIMO`; e, de cálculo, `NAO_REDUZ_SALDO`, `SEM_CONVERGENCIA`. Os de cálculo usam todos a mensagem do `RF-519`. Total de juros, cronograma e valor teórico existem **só** nesta resposta.

## 5. Data Flow

### 5.1 Digitação → prévia (nada é gravado)

1. O aluno digita em `CalculadoraDaDivida`. A cada mudança o componente **limpa o resultado atual na hora** (nunca deixa o 24 antigo, `AC-529`) e agenda a chamada (espera de ~400 ms; `AbortController` cancela a anterior, e resposta fora de ordem é descartada).
2. Servidor: texto brasileiro → tipos por `conversao.py` (`EC-69`, `AC-541`) → `validar_entrada` (`RF-518`) → conta de desconhecidos → ramo da tabela-verdade.
3. Com um desconhecido: `calcular_*` do campo; com os quatro: `conferir_compatibilidade`; com `recalcular`, o campo escolhido é tratado como incógnita.
4. Saída formatada por `report.plano.formatar_dinheiro_br` e `formatar_taxa_br` (o servidor formata; o front não faz conta).
5. Falha em qualquer etapa de cálculo: `estado: ERRO`, `valores` vazio, `mensagem` do `RF-519`; evento sem dado pessoal (PD-15).

### 5.2 Confirmação → resposta

`validar` tudo ⇒ gravar variáveis (4.2) ⇒ gravar `CONFERENCIA_DA_DIVIDA` ⇒ devolver `proxima` pela mesma função de `POST /resposta`. Falha no meio: a marca final não foi gravada, o fluxo reabre a pergunta composta e a confirmação é idempotente (o `INSERT ... ON CONFLICT` substitui a linha, sem merge, `EC-10`).

### 5.3 Leitura para o motor, o relatório e o revisor

`respostas → resolver_divida → (montar_divida | vocabulario_do_caso | marcas do revisor)`. Uma função, uma verdade. Pontos de atenção:

- A taxa que o motor lê é `taxa_mensal_normalizada`, derivada da taxa **gravada** na periodicidade gravada. A calculadora usa a mesma derivação, então prazo na tela = prazo no plano (`AC-526`).
- Parcela `0,00` digitada: resposta válida, fora do cálculo (`OQ-92`).
- Conferência com pendente: `faltas` alimenta o aviso nominal ("Dívida X: falta informar saldo").

### 5.4 Pendente até o relatório

`dividas_pendentes` → (a) `_montar_dividas_do_caso` não entrega a dívida ao motor; (b) `montar_estado_financeiro(..., dividas_pendentes=...)` força `INVENTARIO_COMPLETO = False`; (c) o motor devolve `PROVISORIA` e o relatório já lista "inventário incompleto" como pendência real (`RF-463`); (d) `VocabularioDoCaso` leva `dividas_pendentes` (nome do credor + campos que faltam) e `plano_parcial`, e `report/plano.py` acrescenta o aviso nominal e a marca "plano parcial". Todas pendentes (`EC-74`): `_preparar_calculo` recusa o Bloco 6 com `422` e `pendencias` (mesma forma de `_recusar_montagem`), sem chamar o motor. Liberação ao aluno: ver `OQ-89`.

### 5.5 Fases 2 e 3

Fase 2 acrescenta a derivação da parcela estimada e as passagens do motor (1.2). Fase 3 acrescenta o cenário conservador dentro de `resolver_divida` (1.3). Em ambas, o contrato com o motor continua o da seção 4.3 do `RF-531`.

## 6. External Interfaces

Não há serviço externo. Contratos internos:

| Interface | Contrato | Auth | Limites | Falha → |
| --------- | -------- | ---- | ------- | ------- |
| `POST /caso/{CASO_ID}/calculadora/previa` | seção 4.5 | sessão do aluno e isolamento por caso (`exigir_caso_da_sessao`) | corpo ≤ poucos campos; custo fixo `≤ 107` avaliações; p95 `< 500 ms` (NFR) | `200` com `ERRO` (negócio); `503` técnico |
| `POST /caso/{CASO_ID}/divida/{item_id}/calculadora/confirmar` | seção 4.5 | idem, mais `exigir_coleta_editavel` (`RF-114`) e guarda de consentimento do repositório (`RF-30`) | idem | `409`, `422`, `404`, `503` (`_MENSAGEM_FALHA_SALVAR`) |
| `engine.taxa.derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA` | função pura do motor, já na allowlist | — | taxa negativa levanta `ValueError` (a validação de entrada recusa antes) | erro de entrada |
| `engine.motor.calcular_plano` (Fase 2) | duas passagens em processo | — | custo ×2 | cai para uma passagem e marca `hipótese` |

## 7. State Management

| Estado | Dono | Ciclo de vida |
| ------ | ---- | ------------- |
| Valores digitados, "não sei", sistema, escolha de recálculo | `piq_app_aluno.respostas` (servidor) | Gravado só na confirmação ou pela pergunta individual |
| Valor calculado, marca, situação | **Derivados** por `resolver_divida`, a cada leitura | Sem cache e sem cópia; mudou uma resposta, mudou o derivado (`EC-70`, `EC-71`) |
| Resultado da prévia | Estado local do componente `CalculadoraDaDivida` | Apagado a cada edição, a cada erro e ao desmontar; nunca persistido |
| Ordem e estado do motor | `SnapshotOrdem` (inalterado) | Snapshot imutável (`V-01`); as marcas **não** estão nele (`OQ-90`) |

Invalidação: nenhuma explícita. A escolha do `RF-525` carrega a impressão dos quatro valores; se mudarem, a escolha deixa de valer sem escrita nenhuma.

## 8. Error Handling Strategy

| Situação | Detecção | Resposta ao usuário | Recuperação |
| -------- | -------- | ------------------- | ----------- |
| `loading` da prévia | requisição em curso | indicador discreto no painel de resultado; campos continuam editáveis | nova digitação cancela a anterior |
| Entrada inválida (`RF-518`, `EC-69`) | `ErroDeEntrada` | mensagem do campo dizendo o que corrigir (texto do YAML); resultado limpo | o aluno corrige; nada salvo (`AC-527`) |
| Parcela não reduz o saldo, sem convergência, taxa acima do teto, prazo acima do máximo | `ErroDeCalculo` | **exatamente** "Nas condições informadas, essa parcela não reduz o saldo devedor. Revise os dados ou simule outra condição."; campo calculado vazio (`AC-525`, `AC-528`, `AC-529`) | revisar dados ou responder "não sei" |
| Quatro valores incompatíveis | `COMPATIBILIDADE.INCOMPATIVEL` | valor teórico, sinal em texto (não só cor), escolha "qual informação recalcular" navegável por teclado (`RF-525`) | escolher ou manter os originais |
| `vazio` (duas ou mais desconhecidas) | tabela-verdade | "Faltam dados para calcular" com os campos pendentes; nada calculado | informar mais um dado |
| Falha ou timeout (`EC-77`) | `503` / rede | "Não foi possível calcular agora"; resultado apagado; nada salvo | tentar de novo ou "não sei" |
| Dívida pendente no Bloco 6 | `dividas_pendentes` | aviso nominal; plano parcial/provisório | completar a ficha |
| Todas pendentes (`EC-74`) | lista de dívidas válidas vazia | "Não há dívida com dados suficientes para montar o plano" | completar uma ficha |
| Persistência falha na confirmação | `ErroGravacao*` | `_MENSAGEM_FALHA_SALVAR` (`503`) | repetir; idempotente |

Acessibilidade: mensagem do `RF-519` em `role="alert"`, resultado em `role="status"`, sinal de incompatibilidade em texto; rótulos por `<label>`/`<fieldset>` como em `CampoPergunta`.

## 9. Testing Strategy

**Princípio:** todo teste rastreia para um `AC-NN` (`sdd.config.md` §5); comportamento observável, não implementação.

### 9.1 Unitários (pytest, `hypothesis`)

| AC | Teste |
| -- | ----- |
| `AC-517` | `calcular_parcela(10000, 2%, 24, PRICE) == 528,72` (exato ≈ 528,7111, para cima) |
| `AC-518` | saldo `10.575,34` (±0,01) |
| `AC-519` | taxa `2,00%` (±0,01 pp) |
| `AC-520` | prazo 21; 20 pagamentos de 600 e o 21º `0 < x < 600` |
| `AC-521`, `AC-522`, `AC-531` | SAC: 1ª, 2ª e 12ª parcelas, total de juros `780`, prazo 12; amortizações `3333,33/3333,33/3333,34`, soma `10.000`, última calculada |
| `AC-523` | taxa 0 nos três sentidos (Price e SAC); taxa `0,00%` resultado aceito |
| `AC-524` | `9,70%` (±0,05 pp); o teste exige que a bisseção tenha **dobrado** (limite inicial 1%) |
| `AC-525`, `EC-68` | entrada que estoura as iterações / passa do teto ⇒ `ErroDeCalculo`, nada devolvido |
| `AC-527` | tabela de entradas inválidas (0, negativo, 2,5, vazio, `1234.56`, `1.234,5`) |
| `AC-528` | parcela `200` e `150` com `10000` a `2%` ⇒ `NAO_REDUZ_SALDO`; a frase é comparada **caractere por caractere** com o YAML |
| `AC-530` | parcela digitada `528,71` permanece `528,71` (nenhum arredondamento na entrada) |
| `AC-532` | exibição da taxa com 2 casas, nunca `2,0000`; ida e volta mensal/anual |
| `AC-541` | `1234567.89 → 1.234.567,89`; `1.234,50 → 1234,50` |
| `AC-534`, `AC-535` | compatibilidade (grade de `OQ-78`); valor teórico `528,72` |
| `AC-536` | recalcular parcela / taxa; sem escolha os originais ficam |
| `AC-537`, `AC-538` | `premissas`: "não sei" ⇒ nenhuma resposta `0`, `PENDENTE`; um desconhecido ⇒ `CALCULADO`; dois ⇒ ambos `PENDENTE` |
| `AC-539` | três dívidas, uma pendente ⇒ estado do motor com duas, `INVENTARIO_COMPLETO = False` |
| **Propriedades** | (1) ida e volta: `prazo(calcular_parcela(S,i,n)) == n` em Price e SAC; (2) `calcular_parcela(calcular_saldo(P,i,n)) ≈ P`; (3) a recorrência nunca sobra resíduo positivo após `prazo` meses; (4) monotonia da taxa; (5) tabela-verdade completa 2⁴ × {Price, SAC} |
| `AC-526` | **teste de equivalência com o motor:** para um conjunto de dívidas isoladas (sem ataque), o `prazo` da calculadora = o mês de quitação projetado por `engine.motor.calcular_plano` (o teste pode importar o motor; só `app/`, `collection/` e `report/` têm allowlist) |

### 9.2 Integração

| AC | Costura |
| -- | ------- |
| `AC-542` | `montar_divida` com respostas calculadas: saldo, parcela (nos **dois** campos), taxa mensal normalizada e sistema; sem campo de prazo; `test_engine_congelado.py` sem alteração (hashes de `hashes_congelados.json` intactos) |
| `AC-533` | registro: `B5.C02A` presente em `CARTAO_ROTATIVO`, `PESSOAL`, `CONSIGNADO`; Price pré-selecionado; SAC persiste ao reabrir; texto não diz "do credor" |
| `AC-537` | `POST /resposta` com `NAO_SEI` em `B5.B03`: coleta avança (`avanco_permitido`), linha sem valor, pendência em "O que falta informar" |
| `AC-529` | prévia: erro depois de um sucesso devolve `valores` vazio; a rota não gravou |
| `AC-539`, `AC-540` | relatório: dívida pendente fora da ordem, aviso nominal, "plano parcial"; revisor recebe só `calculado`/`estimado` (nenhum campo com fórmula ou juros) |
| `EC-74` | todas pendentes ⇒ `422`, motor não chamado |
| PD-11 | `pendencias_de_homologacao` com `resolvidas`: campo calculado não é `AUSENTE`; campo pendente é |
| PD-15 | `caplog`: os três eventos não carregam número do aluno |
| Estáticos | `test_fronteira_decimal_unica`, `test_fronteira_import_engine` (sem exceção nova), `test_sem_aritmetica_sobre_snapshot`, `test_sem_conteudo_de_questionario_no_codigo` (mensagens só em YAML) |
| Regressão | `RF-479` (`PARCELA_MAIOR_QUE_O_SALDO` segue sem bloquear); GAB-A/B/C e GAB-01 a 05; suites que citam `1.3.0`, `AC-510`/`T-465`, `T-411` atualizadas e nomeadas na tarefa |

### 9.3 Frontend e E2E

`vitest`: `CalculadoraDaDivida` limpa o resultado em erro (`AC-529`), cancela requisição anterior, não calcula nada, lê a prévia por `role="status"`/`role="alert"`, escolha de recálculo por teclado; `mascaras` inalterado. E2E (`playwright`, já em dependências de dev): ficha de dívida com três dados + "não sei" na taxa até a confirmação; incompatibilidade com escolha.

### 9.4 Fora de teste automatizado

Redação dos textos novos (aprovação do produto); leitura real por leitor de tela (checagem manual com o padrão das telas existentes); conferência de `OQ-79` e `OQ-91` com o especialista.

### 9.5 Fases 2 e 3 (por AC)

`AC-543` a `AC-548`: unitários de `premissas` e de `prioridade` (inclui `EC-75`, troca da prioritária); `AC-549`: o spike como teste automatizado, **sem alterar `engine/`**, que fica no repositório; `AC-550` a `AC-553`: cascata do cenário (ordem e `EC-76`), `AC-551`/`AC-552` com dois cenários e mesmo resultado do mês.

### 9.6 Ordem de implementação da Fase 1 (dependências, não tarefas)

1. `calculo_divida.py` e testes de fórmula/propriedade (`RF-514` a `RF-518`, `RF-520`, `RF-521`): não depende de nada; destrava o resto.
2. Erros e `RF-519` (`AC-525`, `AC-527`, `AC-528`) e conferência (`RF-524`).
3. `premissas.py` e tabela-verdade (`RF-526`, `RF-527`, `RF-528`).
4. Registro, carga e versão `1.4.0`, com a atualização dos testes legados (`RF-523`, `RF-526`, revogações).
5. Montagem: `montar_divida`, `dividas_pendentes`, `INVENTARIO_COMPLETO`, `EC-74` (`RF-531`, `RF-527`, `AC-542`).
6. `comprovacao.py` com `resolvidas` (PD-11) e as três chamadas.
7. Rotas da calculadora, textos em YAML, eventos (`RF-519`, `RF-525`, `RF-530`).
8. Front: tipo novo, componente, `api.ts`.
9. Relatório e revisor: vocabulário, aviso, chips (`RF-527`, `RF-528`, `RF-529`).
10. Regressão completa, e2e e fechamento.

## 10. Risks & Trade-offs

| Decisão | Alternativa descartada | Por quê | Risco assumido |
| ------- | ---------------------- | ------- | -------------- |
| Calculadora em `app/montagem` (puro) | Função nova em `engine/` | `engine/` é congelado (`AC-44`, `RF-531`) | Duplica a recorrência de um mês do motor. Mitiga: o prazo é confirmado pela recorrência e o teste de equivalência com `calcular_plano` (`AC-526`) falha se divergirem. Precedente: `entrada.py` (Rodada 9) |
| Derivar marca e valor calculado | Gravar valor calculado + marca em `respostas` | Sem staleness, sem hook de invalidação, sem apagar linha (o repositório só grava e lista) | Marca fora do snapshot (`OQ-90`): ao rever uma versão antiga, o revisor vê a derivação das respostas **atuais** |
| `NAO_SEI` permanece na resposta mesmo quando calculado | Sobrescrever com o calculado | Valor original nunca alterado (`RF-520`) | `TelaRespostas` (respostas cruas) mostra "não sei" onde o plano usou o valor calculado. Mitiga: a marca e o valor aparecem ao lado |
| Pergunta composta `OPT` | `OBR` | Casos antigos travariam em `pendencias_obrigatorias` | A calculadora é o caminho do aluno novo, não uma trava; ficha antiga mostra "Pendência" até alguém abri-la |
| `B5.C02A` `OPT` sem `indispensavel` (`OQ-93`) | Manter `indispensavel` e condição | Sem condição, `OBR` travaria todo caso antigo | Imobiliário sem resposta cai em `PRICE` em silêncio. Mitiga: a pergunta composta sempre grava o sistema |
| Bisseção só no Price; SAC fechada | Bisseção nos dois | SAC é linear em `i`; menos código, menos erro | Nenhum relevante |
| Saldo e taxa calculados **para baixo** | Mais próximo | Sobrar resíduo de centavo faria o plano durar `n + 1` | Vício sistemático de menos de um centavo / 0,0001 ponto percentual; `OQ-91` |
| Grade de arredondamento fixa (`OQ-78`) | Casas efetivamente digitadas | "2" digitado não pode virar `± 0,5` ponto percentual | A conferência fica permissiva: em R$ 10.000 a 24 meses a taxa move a parcela em `± R$ 0,30`. Escolha deliberada: é a imprecisão real de uma taxa informada com 2 casas |
| Guarda `RF-93` mantida (`OQ-89`) | Exceção para dívida pendente | Não afrouxar uma trava de homologação sem decisão do especialista | **Plano parcial só vai ao revisor, não ao aluno**; reduz o benefício de `US-408` até a decisão |
| Pendente fora do estado do motor + `INVENTARIO_COMPLETO = False` | Entregar a dívida com `DESCONHECIDO` e confiar no Gate 1 | O Gate 1 desvia por `VALOR_RELEVANTE_PARA_QUITACAO` (derivado do saldo); taxa ou parcela desconhecida segue caminhos diferentes em `beneficio_marginal`/`diagnostico` | Perde a ação de informação do motor (`ORDEM_ACOES`) para a dívida; o aviso nominal é do relatório. Um teste de caracterização (seção 9) congela o comportamento |
| Duas passagens do motor (Fase 2) | Eleger a prioritária por heurística na montagem | Prioritária é regra do motor (`OQ-75`); reimplementar a ordem na aplicação viola a Lei nº 3 | Custo ×2 no Bloco 6; empate em `H-04` nível 3 pode oscilar (limite de 3 passagens) |
| Mapeamento de pagamentos decidido por spike | Fixar `RF-537` agora | Risco alto declarado na spec | Pode concluir que o mapeamento da spec dobra o fluxo de caixa simulado (1.2) e exigir decisão sobre `engine/` |

### Riscos novos (além dos 9 da spec)

1. **Liberação bloqueada por `RF-93` com dívida pendente** (`OQ-89`): contraria o valor de `US-408`.
2. **Mapeamento de pagamentos pode dobrar a saída de caixa simulada**: a parcela de 24 meses em `PAGAMENTO_MENSAL_EFETIVO` é paga pela simulação além da capacidade de ataque (calculada sobre o devido); `RESULTADO_CAIXA_OBSERVADO` (o "Resultado do mês" da tela do revisor) varia com ele.
3. **Habitual ausente × alerta de crescimento**: `calcular_faltas_de_juros` pula dívida com `PARCELA_CONTRATUAL = DESCONHECIDO`, e `0` seria zero silencioso; `RF-535` pode ser inalcançável sem decisão (spike).
4. **Prioritária circular**: a ordem do motor depende dos pagamentos que dependem da prioritária (Fase 2).
5. **Marca fora do snapshot** (`OQ-90`).
6. **Arredondamento para baixo de saldo e taxa** diverge da hipótese da spec (`OQ-91`).
7. **Parcela `0,00` × `RF-518`** (`OQ-92`).
8. **`B5.C02A` perde `indispensavel`** (`OQ-93`).
9. **Reabertura da taxa calculada**: a máscara de `TAXA` limita a 2 casas; reabrir a ficha mostra 2 casas e uma nova confirmação grava 2 casas. O servidor deve tratar campo "a calcular" como `null` no corpo (não reenviar o valor exibido).
10. **Teste estático por nome** (`cenario`) pode acusar falso positivo na Fase 3.
11. **Suite legada** que cita `1.3.0`, `AC-510`/`T-465`, `T-411` e `saldo.admite_nao_sei is False`: precisa ser atualizada junto, não depois.
12. **Conferência permissiva** com taxa de 2 casas (acima).

## 11. Traceability

| Requisito | Coberto por (seção do plano) |
| --------- | ---------------------------- |
| `RF-514` | PD-01, PD-05; 4.3; 9.1 (`AC-517` a `AC-522`) |
| `RF-515` | 4.3 (caminhos Price/SAC com taxa 0); 9.1 (`AC-523`) |
| `RF-516` | PD-01, PD-02, PD-05; 0.2; 4.3; 9.1 (`AC-519`, `AC-524`, `AC-525`) |
| `RF-517` | PD-03; 4.3 (arredondamentos); 9.1 (`AC-520`, `AC-526`) |
| `RF-518` | 4.3 (`validar_entrada`); 4.5 (códigos); 8; 9.1 (`AC-527`) |
| `RF-519` | PD-09; 4.5; 5.1; 8; 9.1 (`AC-525`, `AC-528`, `AC-529`) |
| `RF-520` | 4.3 (tabela de arredondamento); 9.1 (`AC-517`, `AC-530`) |
| `RF-521` | 4.3 (`cronograma`); 9.1 (`AC-521`, `AC-531`) |
| `RF-522` | PD-04; 4.3; 5.3; 9.1 (`AC-532`) |
| `RF-523` | PD-08; 4.1 (`B5.C02A`); 9.2 (`AC-533`) |
| `RF-524` | 4.3 (conferência, `OQ-78`); 9.1 (`AC-534`, `AC-535`) |
| `RF-525` | 4.2 (`INFORMACAO_A_RECALCULAR`); 4.4; 4.5; 7; 9.1 (`AC-536`) |
| `RF-526` | PD-06, PD-11; 4.1; 4.4 (tabela-verdade); 5.4; 9 (`AC-537`, `AC-538`) |
| `RF-527` | PD-10; 5.4; 8; 9.2 (`AC-539`) |
| `RF-528` | PD-06, PD-14; 4.4; 7; 9.2 (`AC-540`) |
| `RF-529` | PD-14; 4.5 (total de juros só na prévia); 9.2 (`AC-540`) |
| `RF-530` | 4.5 (texto brasileiro, formatadores existentes); 9.1 (`AC-541`) |
| `RF-531` | PD-01, PD-07; 5.3; 9.2 (`AC-542`) |
| `RF-532` | 1.2; 4.4 (nota Fase 2); 9.5 (`AC-543`, `AC-544`) |
| `RF-533` | 1.2 (`B5.C02C`, exibição separada); 9.5 (`AC-545`) |
| `RF-534` | PD-16; 1.2 (prioritária); 9.5 (`AC-546`) |
| `RF-535` | 1.2 (spike: habitual ausente); 9.5 (`AC-547`) |
| `RF-536` | 1.2 (exibição, textos); 9.5 (`AC-548`) |
| `RF-537` | PD-16; 1.2 (spike); 9.5 (`AC-549`) |
| `RF-538` | 1.3 (candidatos e cascata); 9.5 (`AC-550`, `AC-553`) |
| `RF-539` | 1.3 (injeção só de saldo e taxa); 9.5 (`AC-551`) |
| `RF-540` | 1.3; 1.2 (spike); 9.5 (`AC-552`) |

**Buracos sinalizados.** (1) `NFR` "marca e valor original entram no snapshot" não é atendido literalmente (`OQ-90`). (2) `RF-535` depende do resultado do spike (1.2); sem ele, não há como afirmar que é atingível sem tocar `engine/`. (3) `US-408` fica parcialmente atendida até `OQ-89`. (4) `OQ-77` e `OQ-79` precisam de aprovação do especialista antes da implementação da Fase 1.

> Todo item deste plano rastreia para um `RF-NN`. Itens sem requisito foram cortados (por exemplo: tabela de histórico de premissas, cache de cálculo, serviço assíncrono de prévia).

### 11.1 Relatório do spike `T-523` (`OQ-83`, `AC-549`) — 2026-11-05

Teste: `tests/app_aluno/test_spike_pagamentos_da_divida.py` (10 testes, `engine/` intocado). Cenário: renda 10.000, despesas 7.000 (disponível 3.000); `D1` 10.000 a 2%, habitual 150; `D2` 5.000 a 3%, sem parcela nem prazo, mínimo 80, parcela de 24 meses 295,24.

| Caso (`PARCELA_CONTRATUAL` / `PAGAMENTO_MENSAL_EFETIVO` de `D2`) | Caixa observado | Estrutural (`RESULTADO_MENSAL_ATUAL`) | Saída da simulação no mês 1 | Alerta de crescimento |
| --- | --- | --- | --- | --- |
| Base: 80 / 80 | 2.770,00 | 2.770,00 | 3.000,00 | `D1` 50 + `D2` 70 |
| Spec (`RF-537`): 0 / 295,24 | 2.554,76 | 2.850,00 | **3.295,24** | `D1` 50 + `D2` 150 (preservado) |
| Spec com `DESCONHECIDO` / 295,24 | 2.554,76 | 2.850,00 | 3.295,24 | só `D1` 50 (**`D2` pulada**) |
| Opção B: 0 / 80 | 2.770,00 | 2.850,00 | **3.080,00** | `D1` 50 + `D2` 150 |
| 295,24 / 295,24 (parcela de 24 meses no devido) | 2.554,76 | 2.704,76 | — | só `D1` (`D2` some) |
| Spec com disponível 300 | **-145,24** | 150,00 | 595,24 | preservado; `DEFICIT_MENSAL` = 0 |
| Spec + `CAPACIDADE_ATAQUE_DECLARADA` = caixa (2.554,76) | 2.554,76 | 2.850,00 | **3.000,00** | preservado |

**Respostas.**
1. **Não fecha sozinho.** O ataque vem do estrutural (devido), o pagamento normal vem do efetivo; onde `devido != efetivo` a simulação paga a diferença duas vezes (excesso = efetivo − devido: 295,24 na spec, 80 na opção B). O caixa já mostra a parcela de 24 meses, mas `DEFICIT_MENSAL` e `CAPACIDADE_ATAQUE_ATUAL` ignoram. Sem `engine/`, o excesso some se a montagem limitar `CAPACIDADE_ATAQUE_DECLARADA` ao caixa observado (cai para 3.000,00).
2. **Alerta preservado** com `PARCELA_CONTRATUAL` = 0 (falta = juros, `AC-547`). Parcela de 24 meses no devido esconde a dívida.
3. **Prazo 24** na calculadora e no motor (dívida isolada, sem ataque).
4. **Regra "só a prioritária recebe a parcela de 24 meses" alcançável:** passagem 1 (todas no mínimo) dá `D2`; passagem 2 (`D2` com 295,24) mantém `D2`; dar a parcela à outra também mantém. Duas passagens estabilizam neste caso; o empate em `H-04` nível 3 segue como risco (1.2).
5. **`RF-535` não é inalcançável**, desde que habitual ausente vire **0** (não `DESCONHECIDO`, que o motor pula: falta 50 em vez de 200). Custo do 0: estrutural e capacidade ficam acima do real (2.850 contra 2.554,76).

**Escolha: (A) o mapeamento da spec, com ressalvas. Não exige mudar `engine/`; `git diff engine/` vazio.** Decisões para o especialista antes da `T-524`: (a) habitual ausente = `PARCELA_CONTRATUAL` 0 com o aluno avisado de que não é um "zero declarado"; (b) a montagem limita `CAPACIDADE_ATAQUE_DECLARADA` ao caixa observado (altera um campo declarado, só para baixo, marcado `hipótese`); (c) com orçamento apertado `DEFICIT_MENSAL` fica 0 e só o caixa negativo acusa: a tela deve exibi-lo; (d) a parcela de 24 meses não pode depender do cenário (`RF-540`). Se (b) for recusada, a opção é (C): decisão sobre `engine/`.

### 11.2 Decisão do mapeamento (`T-524`, `PD-17`) — 2026-11-05

> **Atualização 2026-11-06 (respostas do especialista, `docs/perguntas-marcelo-calculo-de-divida.md`):** (a), (c) e (d) aprovadas; (b) recusada e removida (o valor declarado é usado e o plano avisa); a parcela de 24 meses vale para toda dívida estimável, sem passagens do motor. O texto abaixo é o histórico de 2026-11-05.
>
> **Status (2026-11-05): HIPÓTESE ADOTADA, aguardando confirmação do especialista (Marcelo).** A execução da Fase 2 foi autorizada pelo usuário sobre esta hipótese; nada abaixo foi aprovado. Se o especialista recusar a ressalva (b), a saída é a opção (C) da 1.2 (decisão sobre `engine/`), e só `limitar_capacidade_ao_caixa` precisa sair.

**Mapeamento adotado (A) e onde vive cada ressalva**

| Ressalva do spike (11.1) | Como ficou | Onde |
| ------------------------ | ---------- | ---- |
| (a) habitual ausente = `PARCELA_CONTRATUAL` 0, com aviso de que não é "zero declarado" | `montar_divida` põe `0` no devido quando há `parcela_estimada`; `premissas.ParcelaEstimada.habitual_ausente` distingue ausente de zero declarado; o relatório avisa (`avisos.habitual_nao_informado`) | `app/montagem/estado.py`, `premissas.py`, `report/plano.py::_avisos_de_pagamento` |
| (a) **revogada** (2026-11-10, `OQ-96`, `T-543`) | Com parcela estimada, `PARCELA_CONTRATUAL` = `PAGAMENTO_MENSAL_EFETIVO` = estimada; o mês tem uma conta só e o aviso `habitual_nao_informado` saiu | `app/montagem/estado.py`, `serializacao_plano.py`, `report/plano.py` |
| (b) a montagem limita `CAPACIDADE_ATAQUE_DECLARADA` ao caixa observado, só para baixo, como `hipótese` | **Ponto único** `prioridade.limitar_capacidade_ao_caixa` (nunca sobe; caixa negativo vira `0`; `DESCONHECIDO` intacto); o relatório avisa a redução (`avisos.capacidade_limitada`, "(hipótese)") | `app/montagem/prioridade.py` |
| (c) exibir o caixa negativo quando o orçamento aperta | aviso `avisos.caixa_negativo` quando `RESULTADO_CAIXA_OBSERVADO < 0 <= RESULTADO_MENSAL_ATUAL` (só o caixa acusa) | `report/plano.py` |
| (d) a parcela de 24 meses independe do cenário (`RF-540`) | `parcela_estimada` depende só de saldo, taxa e sistema da dívida; o cenário conservador (Fase 3) injeta só saldo e taxa | `premissas.py` |

**Detalhamento das tarefas seguintes (sem renumeração)**

- `T-525`: `B5.C02C` (`PAGAMENTO_MINIMO_DIVIDA`), `OPT`+`REP`, depois de `B5.C02B`; versão `1.5.0` nos sete arquivos de `collection/registros/` que declaram versão.
- `T-526`: estimativa em `resolver_divida` só com prazo desconhecido e habitual ausente ou `0,00`; `valores[PARCELA]` vira `ESTIMADO` quando o habitual é ausente (a situação deixa de ser `PENDENTE`); habitual `0,00` declarado continua `INFORMADO` e a estimativa vai em `parcela_estimada`.
- `T-527`/`T-528`: `planejar_pagamentos` (até 3 passagens do motor em processo, sem snapshot); o executor ganha `avaliar_passagem` e `planejar_com_limite_async`; as passagens rodam em segundo plano com o caso já em `CALCULANDO`, e falha ou estouro de tempo caem no estado provisório (uma passagem, `hipótese`).
- `T-529`/`T-530`: não exigem decisão sobre `engine/` (o spike mostrou `RF-535` alcançável com habitual `0` no devido). A inviabilidade lê `DIVIDAS_QUE_CRESCEM` e `RESULTADO_CAIXA_OBSERVADO` do snapshot, sem conta.
- `T-531`: prévia ganha `parcela_estimada` (linha separada, marcada); o revisor vê a marca `estimado` em `PAGAMENTO_MENSAL_EFETIVO` (nova coluna "Pagamento do plano"), nunca em `PARCELA_CONTRATUAL`.
- `T-532`: textos **provisórios** marcados `[PROVISORIO T-532]`; a tarefa segue pendente de aprovação do produto.

**Riscos que a hipótese deixa em aberto.** A marca `hipótese` da prioritária e o teto de capacidade não entram no snapshot (mesma limitação de `OQ-90`): o relatório os infere das respostas e do estado. A alvo é confirmada no motor sem o teto; se o teto trocar a alvo, a passagem não repete. O empate em `H-04` nível 3 segue como risco da seção 1.2.
