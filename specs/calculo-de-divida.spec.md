# Spec — cálculo de dívida (saldo, parcela, taxa e prazo)

| Campo  | Valor |
| ------ | ----- |
| Slug   | `calculo-de-divida` |
| Status | `rascunho` |
| Autor  | Spec Agent |
| Data   | `2026-11-03` |
| Origem | `specs/calculo-de-divida.discovery.md` (pedido do especialista Marcelo Brasília e 3 rodadas de respostas, todas de 2026-11-03). Cada requisito cita a decisão do discovery (`D1` a `D15`, seção 7) ou o risco (seção 6) de que nasce. |

> Numeração global, continuando as specs existentes: último `RF-513`, `AC-516`, `EC-61`, `OQ-72`, `US-405`. Esta spec usa `RF-514` a `RF-540`, `AC-517` a `AC-553`, `EC-62` a `EC-77`, `OQ-73` a `OQ-88`, `US-406` a `US-411`. Os `OQ-D1` a `OQ-D4` do discovery são `OQ-73` a `OQ-76`.

## 1. Overview

Hoje a ficha de dívida pede saldo (`B5.B03`), parcela (`B5.C02`) e taxa (`B5.D06`) como três números independentes, e o motor deriva o prazo. Nada garante que sejam coerentes entre si; a única conferência é o aviso `PARCELA_MAIOR_QUE_O_SALDO` (`RF-479`). O aluno também trava quando não sabe um dado (a taxa é o caso mais comum) e quem tem cartão rotativo ou cheque especial não tem prazo nem parcela contratual, mas o PIQ precisa de uma base de quitação para ordenar e planejar a dívida.

O objetivo é que o PIQ **calcule qualquer uma das quatro informações (saldo, parcela, taxa, prazo) a partir das outras três**, confira a coerência dos quatro valores quando o aluno os informa todos, deixe "não sei" ser resposta válida sem virar zero, e dê uma base de quitação explícita e marcada como estimativa às dívidas sem prazo. Para o aluno do SSD que preenche o diagnóstico, para o revisor que homologa e para o especialista que garante que o PIQ não contradiz o curso. **Nada em `engine/` muda** (hashes do `AC-44` intactos).

### Fases

| Fase | Entrega | Requisitos |
| ---- | ------- | ---------- |
| 1 | Calculadora das quatro variáveis, conferência, "não sei" e marcas | `RF-514` a `RF-531` |
| 2 | Parcela estimada de 24 meses para dívida sem parcela nem prazo | `RF-532` a `RF-537` |
| 3 | Cenário conservador para quatro valores incompatíveis | `RF-538` a `RF-540` |

Cada fase é entregável sozinha. A Fase 2 depende da Fase 1 (marcas, "não sei"); a Fase 3 depende da Fase 1 (incompatibilidade) e do mapeamento da Fase 2 (`RF-537`).

### Revogações (explícitas)

- **`RF-510`**, parte "só quando `TIPO_DIVIDA = FIN_IMOBILIARIO`": revogada por `RF-523`. `AC-510` e `T-465` ficam substituídos (a pergunta `B5.C02A` aparece em toda dívida).
- **`RF-513`**, trecho "Dívida sem parcela responde R$ 0,00" e "`B5.D06` não aceita vazio" (`AC-516`): superado por `RF-526` (a ficha aceita "não sei", que nunca é zero). Resposta `R$ 0,00` digitada continua sendo um pagamento zero válido.
- **`T-411`** (saldo sem "não sei"): superado por `RF-526`.
- **`RF-479`**: preservado (um valor mensal por dívida; aviso `PARCELA_MAIOR_QUE_O_SALDO` sem bloquear). A Fase 2 acrescenta o pagamento mínimo sem revogar a parcela declarada.

## 2. Functional Requirements

### Fase 1 — Calculadora das quatro variáveis

| ID | Fase | Requisito | Origem | Prioridade |
| -- | ---- | --------- | ------ | ---------- |
| `RF-514` | 1 | O sistema calcula **qualquer uma** das quatro informações da dívida (saldo, parcela, taxa, prazo) a partir das outras três, em **Price** (parcela fixa) e **SAC** (a parcela informada é a 1ª; as seguintes decrescem). Saldo é o de hoje e prazo é o restante, em meses. | D1 | essencial |
| `RF-515` | 1 | **Taxa zero** é válida como entrada e como resultado. Com taxa zero, Price e SAC coincidem: parcela = saldo ÷ prazo; prazo = saldo ÷ parcela (para cima); saldo = parcela × prazo. | D1, D15 | essencial |
| `RF-516` | 1 | Quando a taxa é a incógnita, o sistema a resolve numericamente: busca entre 0 e um limite superior inicial de 0,01 (1% ao mês) que **dobra** até envolver a solução, com **número máximo de iterações** e **teto de taxa**. Não convergir, ou resultado acima do teto, é erro tratado (`RF-519`), nunca taxa inválida salva. Os cálculos com logaritmo e potência (`ln(1+i)`) usam precisão decimal, nunca ponto flutuante (fronteira em `app/montagem/conversao.py`). | D1, Risco 5 | essencial |
| `RF-517` | 1 | O prazo calculado é em **meses inteiros**. Quando o resultado é fracionário, arredonda-se **para cima** e o **último pagamento é ajustado** (menor que a parcela e maior que zero) para zerar o saldo. O prazo exibido na tela é o mesmo que o plano projeta. | D2, D15, Risco 2 | essencial |
| `RF-518` | 1 | Validações de entrada, com mensagem que diz o que corrigir: saldo > 0; parcela > 0; taxa ≥ 0 e abaixo do teto (`OQ-79`); prazo inteiro ≥ 1 e abaixo do máximo (`OQ-79`). Valor inválido não dispara cálculo e não é salvo como calculado. | D1, Risco 5 | essencial |
| `RF-519` | 1 | Quando a parcela **não reduz o saldo** (parcela ≤ juros do primeiro mês: saldo × taxa), ou quando o cálculo falha (`RF-516`), o sistema mostra exatamente: "Nas condições informadas, essa parcela não reduz o saldo devedor. Revise os dados ou simule outra condição." e **apaga o resultado calculado** que estivesse na tela, sem deixar valor antigo. Nada calculado é salvo em erro. | D15 | essencial |
| `RF-520` | 1 | A **parcela calculada** é arredondada **para cima** ao centavo. Valor que veio do contrato (digitado pelo aluno) **nunca é alterado** pelo sistema. | D2 | essencial |
| `RF-521` | 1 | Em SAC, o sistema **confere a sequência**: a soma das amortizações é igual ao saldo; as parcelas decrescem (taxa > 0) ou são iguais (taxa 0); o **último pagamento é calculado** (amortização restante + juros do saldo restante), não copiado. Divergência de centavos da divisão da amortização cai na última parcela. | D15 | essencial |
| `RF-522` | 1 | A taxa tem **4 casas decimais só no cálculo interno**; o aluno **não digita nem vê** 4 casas. A taxa continua sendo informada e exibida em **mensal ou anual** (CET mensal ou anual, como já existe em `B5.D06`); a taxa calculada volta na periodicidade que o aluno escolheu. A conversão anual → mensal é a do motor (`§16.1`), sem alteração. | D3, D5 | essencial |
| `RF-523` | 1 | **Price e SAC valem para todas as modalidades de dívida.** Price é o padrão pré-selecionado; a escolha do aluno é preservada ao reabrir a ficha. A simulação nunca é apresentada como condição do credor. A pergunta `B5.C02A` (`SISTEMA_AMORTIZACAO`) deixa de depender de `TIPO_DIVIDA = FIN_IMOBILIARIO`. **Revoga** a restrição de `RF-510`/`T-465`. | D4 | essencial |
| `RF-524` | 1 | Com os **quatro valores informados**, o sistema confere se são compatíveis, usando o **intervalo de arredondamento das entradas** (cada valor digitado representa uma faixa; compatível se a faixa do valor teórico encontra a faixa do digitado). Compatíveis: nada a sinalizar. **Incompatíveis**: os valores **originais são salvos**, o valor teórico é mostrado, e a incompatibilidade é sinalizada ao aluno e ao revisor. | D6, D7 | essencial |
| `RF-525` | 1 | Na incompatibilidade, o aluno **escolhe qual informação recalcular** (saldo, parcela, taxa ou prazo); as outras três ficam intactas e a escolhida passa a valer como calculada, com a marca de `RF-528`. Sem escolha, os originais permanecem e a sinalização continua (e, na Fase 3, vale o cenário conservador). | D6, D15 | essencial |
| `RF-526` | 1 | **"Não sei"** é resposta permitida em saldo, parcela, taxa e prazo e **nunca vira zero**; vira informação pendente. Com **uma** das quatro desconhecida e as outras três informadas, o sistema a calcula. Com duas ou mais desconhecidas, não calcula e as pendentes ficam marcadas. "Não sei" não bloqueia o avanço (`RF-11`, `pendencias_obrigatorias`), mas aparece como pendência real do relatório (`RF-461`). | D13, Risco 3 | essencial |
| `RF-527` | 1 | **Dívida pendente** (sem as três informações mínimas para fechar a conta) fica **fora do plano**, com aviso que a nomeia e diz o que falta. O plano das demais dívidas continua e é **marcado como parcial**. | D13 | essencial |
| `RF-528` | 1 | Todo valor de dívida carrega uma **marca**: `calculado` (saiu da calculadora a partir de três informados), `estimado` (valor em R$ obtido por hipótese, Fase 2), `hipótese` (premissa sob a qual o valor foi estimado, como "24 meses" ou "cenário conservador") e `pendente` (desconhecido). Valor digitado pelo aluno não tem marca de cálculo. A marca persiste com a resposta e sobrevive ao snapshot. | D14, LGPD | essencial |
| `RF-529` | 1 | O **total de juros em R$** aparece **só na tela do cálculo**. O **revisor vê apenas as marcas** `calculado` e `estimado` (não vê fórmulas, total de juros nem valores intermediários). | D14 | importante |
| `RF-530` | 1 | Valores monetários e taxas usam **formato brasileiro com separador de milhar** (`1.234.567,89`). Taxa `0,00` é aceita como resultado e como entrada. | D15 | importante |
| `RF-531` | 1 | **`engine/` não muda.** `Divida` não ganha campo de prazo. Ao motor chegam saldo, parcela (nos dois campos de pagamento), taxa mensal normalizada e sistema de amortização; o prazo calculado é só de apresentação e conferência. O motor segue derivando o prazo (`RF-509`). | Restrições, Risco 1 | essencial |

### Fase 2 — Parcela estimada de 24 meses

| ID | Fase | Requisito | Origem | Prioridade |
| -- | ---- | --------- | ------ | ---------- |
| `RF-532` | 2 | Dívida com **saldo e taxa conhecidos, sem parcela e sem prazo**, recebe a **hipótese de 24 meses**, em **todas as modalidades** (inclui cartão rotativo, cheque especial e dívida de parcela fixa). A parcela estimada é calculada como em `RF-514` com prazo de 24 e o sistema da dívida (Price se não escolhido). O **prazo contratual** ou o **pagamento informado pelo aluno** (habitual > 0) **prevalecem**: a informação do aluno é soberana. Pagamento atual zero ou ausente também usa os 24 meses (`OQ-73`). | D9, OQ-D1, OQ-D4 | essencial |
| `RF-533` | 2 | O questionário coleta, em **toda dívida**, o **pagamento mínimo** ao lado do **pagamento habitual** (o que o aluno de fato paga, hoje a parcela de `B5.C02`; `OQ-85`). A **parcela estimada** é sempre exibida **separada** dos valores informados e **marcada** (`RF-528`). | D8 | essencial |
| `RF-534` | 2 | **Toda** dívida sem prazo e sem pagamento recebe a parcela de 24 meses: o plano precisa de horizonte temporal (especialista, 2026-11-06; substitui "só a prioritária, as demais no mínimo" de 2026-11-03). O mínimo informado fica só registrado. | D10, OQ-D3 | essencial |
| `RF-535` | 2 | O **alerta de dívida que cresce** (`RF-79`) compara os juros do mês com o pagamento **habitual**, nunca com a parcela estimada de 24 meses (que, por construção, sempre cobre os juros e esconderia o crescimento). Habitual zero ou ausente: a falta é igual aos juros. | D11 | essencial |
| `RF-536` | 2 | Pagamento que **inviabiliza o plano** (`OQ-74`): o plano avisa a inviabilidade e **nunca troca o pagamento do aluno**. Com pagamento informado pelo aluno, o texto não fala em hipótese de 24 meses. | D12, OQ-D2 | essencial |
| `RF-537` | 2 | **Mapeamento nos dois campos de pagamento do motor**, adotado como **hipótese a validar por teste antes de fechar o plano** (spike), sem tocar em `engine/`: `PARCELA_CONTRATUAL` recebe o pagamento **habitual** declarado (devido; alimenta `FALTA_DE_JUROS`); `PAGAMENTO_MENSAL_EFETIVO` recebe o que o plano paga (parcela estimada em toda dívida sem informação do aluno; o declarado quando existe). O teste usa dívida de exemplo e prova que o alerta de crescimento não some e que o resultado do mês não muda sem aviso (`OQ-83`). | Risco 1, D11 | essencial |

### Fase 3 — Cenário conservador

| ID | Fase | Requisito | Origem | Prioridade |
| -- | ---- | --------- | ------ | ---------- |
| `RF-538` | 3 | Quando os quatro valores são incompatíveis e o aluno não escolheu recalcular (`RF-525`), o plano usa o **cenário conservador**, escolhido pela ordem: **maior parcela**, **maior saldo**, **maior taxa**, **maior prazo**, **maior custo total** (`OQ-82`). O cenário é marcado `hipótese` e o aluno e o revisor o veem sinalizado. | D6 | importante |
| `RF-539` | 3 | **Só o saldo e a taxa do cenário chegam ao motor.** Parcela e prazo do cenário **não governam o plano**. O texto ao aluno diz isso de forma explícita. | D6, Risco 4 | essencial |
| `RF-540` | 3 | O **resultado do mês usa o pagamento que o aluno declara**, em qualquer cenário. Trocar de cenário não muda o resultado do mês. | D6 | essencial |

## 3. User Stories

### `US-406` — Calcular o que não sei
> Como **aluno do SSD**, quero informar três dos quatro dados da dívida (saldo, parcela, taxa, prazo) para que o PIQ calcule o quarto, sem eu chutar.

Atende: `RF-514`, `RF-515`, `RF-516`, `RF-517`, `RF-520`, `RF-522`, `RF-523`

### `US-407` — Entender quando a conta não fecha
> Como **aluno do SSD**, quero ser avisado, com mensagem clara, quando a parcela não reduz o saldo ou os quatro valores não batem, e escolher o que recalcular, para corrigir meus dados.

Atende: `RF-518`, `RF-519`, `RF-521`, `RF-524`, `RF-525`

### `US-408` — Seguir sem saber tudo
> Como **aluno do SSD**, quero responder "não sei" em um dado da dívida e continuar preenchendo, para não travar a ficha, sabendo que a dívida sem dados suficientes fica de fora do plano com aviso.

Atende: `RF-526`, `RF-527`, `RF-528`

### `US-409` — Dívida sem prazo entra no plano
> Como **aluno do SSD** com cartão rotativo ou cheque especial, quero que o PIQ use uma base de quitação de 24 meses, marcada como estimativa, para que a dívida seja ordenada e planejada sem eu inventar uma parcela.

Atende: `RF-532`, `RF-533`, `RF-534`, `RF-535`, `RF-536`, `RF-537`

### `US-410` — Distinguir informado, calculado e estimado
> Como **revisor**, quero ver quais valores foram calculados ou estimados, para decidir se os dados do aluno são confiáveis antes de homologar.

Atende: `RF-524`, `RF-528`, `RF-529`, `RF-538`

### `US-411` — Não contradizer o curso
> Como **especialista do método**, quero que o plano use a regra "mínimo em todas, extra concentrado em uma" e nunca troque o pagamento que o aluno declara, para que o PIQ não contradiga o curso SSD.

Atende: `RF-534`, `RF-536`, `RF-539`, `RF-540`

## 4. Acceptance Criteria

Exemplos numéricos usam `R$` com formato brasileiro. "Tolerância" abaixo é de arredondamento da conta, não folga de regra.

### Fase 1

| ID | Story | Critério (verificável) |
| -- | ----- | ---------------------- |
| `AC-517` | `US-406` | Dado saldo R$ 10.000,00, taxa 2,00% ao mês, prazo 24 meses, Price, quando a parcela é calculada, então o valor exato é aproximadamente R$ 528,7111 e a parcela exibida é **R$ 528,72** (arredondada para cima ao centavo, `RF-520`). Ver `OQ-77`: o exemplo do pedido cita R$ 528,71, que é o arredondamento ao mais próximo e contradiz a decisão 2 (`RF-514`, `RF-520`) |
| `AC-518` | `US-406` | Dado parcela R$ 1.000,00, taxa 2,00% ao mês, prazo 12 meses, Price, quando o saldo é calculado, então o saldo é R$ 10.575,34 (tolerância de R$ 0,01) (`RF-514`) |
| `AC-519` | `US-406` | Dado saldo R$ 10.000,00, parcela R$ 528,72, prazo 24 meses, Price, quando a taxa é calculada, então a taxa é 2,00% ao mês (exibida com 2 casas, tolerância de 0,01 ponto percentual) (`RF-514`, `RF-516`) |
| `AC-520` | `US-406` | Dado saldo R$ 10.000,00, taxa 2,00% ao mês, parcela R$ 600,00, Price, quando o prazo é calculado, então o prazo é **21 meses**: 20 pagamentos de R$ 600,00 e o 21º menor que R$ 600,00 e maior que zero, de modo que o saldo final é zero (prazo fracionário 20,47 arredondado para cima) (`RF-514`, `RF-517`) |
| `AC-521` | `US-406` | Dado saldo R$ 12.000,00, taxa 1,00% ao mês, prazo 12 meses, SAC, quando a 1ª parcela é calculada, então a amortização é R$ 1.000,00, a 1ª parcela é R$ 1.120,00, a 2ª é R$ 1.110,00 e a 12ª é R$ 1.010,00; o total de juros na tela do cálculo é R$ 780,00 (`RF-514`, `RF-521`, `RF-529`) |
| `AC-522` | `US-406` | Dado saldo R$ 12.000,00, taxa 1,00% ao mês, 1ª parcela R$ 1.120,00, SAC, quando o prazo é calculado, então o prazo é 12 meses (`RF-514`) |
| `AC-523` | `US-406` | Dado saldo R$ 1.200,00 e prazo 12 meses com taxa 0,00%, então a parcela calculada é R$ 100,00 em Price e em SAC; dado saldo R$ 1.200,00, parcela R$ 100,00 e prazo 12, então a taxa calculada é 0,00% e é aceita e salva (não é erro nem campo vazio); dado parcela R$ 100,00, taxa 0,00% e prazo 12, então o saldo calculado é R$ 1.200,00 (`RF-515`, `RF-530`) |
| `AC-524` | `US-406` | Dado saldo R$ 1.000,00, parcela R$ 400,00 e prazo 3 meses, Price, quando a taxa é calculada, então o resultado é 9,70% ao mês (tolerância de 0,05 ponto percentual), acima do limite inicial de 1%, o que prova que o limite superior dobra até envolver a solução (`RF-516`) |
| `AC-525` | `US-407` | Dada uma entrada em que a bisseção atinge o máximo de iterações sem convergir ou o resultado passa do teto de taxa, quando o cálculo roda, então a mensagem do `RF-519` aparece, nenhum valor calculado é salvo e o campo de resultado fica vazio (`RF-516`, `RF-519`) |
| `AC-526` | `US-406` | Dado um aluno cuja dívida tem prazo calculado de 24 meses (saldo R$ 10.000,00, 2,00% ao mês, parcela exibida R$ 528,72, Price), quando o plano é gerado sem pagamento extra para essa dívida isolada, então ela quita em 24 meses, não em 25 (`RF-517`, `RF-520`) |
| `AC-527` | `US-407` | Dado saldo 0, saldo negativo, parcela 0 ou negativa, taxa negativa, prazo 0 ou prazo não inteiro (2,5), quando o aluno tenta calcular, então o valor é recusado com mensagem que diz o que corrigir e nada é salvo como calculado (`RF-518`) |
| `AC-528` | `US-407` | Dado saldo R$ 10.000,00 e taxa 2,00% ao mês (juros do mês R$ 200,00), quando a parcela informada é R$ 200,00 ou R$ 150,00 e o prazo é pedido, então aparece exatamente "Nas condições informadas, essa parcela não reduz o saldo devedor. Revise os dados ou simule outra condição." (`RF-519`) |
| `AC-529` | `US-407` | Dado um prazo calculado de 24 meses na tela, quando o aluno troca a parcela para um valor que gera o erro do `RF-519`, então o campo do prazo fica vazio (sem o 24 antigo), a mensagem aparece e nada é gravado como calculado (`RF-519`) |
| `AC-530` | `US-406` | Dado que o aluno informou parcela R$ 528,71 (do contrato) com saldo R$ 10.000,00 e prazo 24, quando o sistema calcula a taxa, então a parcela salva continua R$ 528,71, sem virar R$ 528,72 (`RF-520`) |
| `AC-531` | `US-407` | Dado saldo R$ 10.000,00, prazo 3 meses, taxa 1,00% ao mês, SAC, então as amortizações são R$ 3.333,33, R$ 3.333,33 e R$ 3.333,34, a soma é R$ 10.000,00, as parcelas decrescem, e a última parcela é a amortização restante mais os juros do saldo restante (`RF-521`) |
| `AC-532` | `US-406` | Dada uma taxa calculada de 2,00% ao mês, então a tela e o relatório mostram no máximo 2 casas decimais (nunca "2,0000"), e a mesma taxa informada ao ano (ex.: 26,82% ao ano) volta ao ano quando o aluno escolheu "ao ano" (`RF-522`) |
| `AC-533` | `US-406` | Dadas dívidas de tipos `CARTAO_ROTATIVO`, `PESSOAL` e `CONSIGNADO`, então a pergunta Price ou SAC (`B5.C02A`) aparece em todas, com Price pré-selecionado; escolhido SAC e reaberta a ficha, SAC continua; o texto não afirma que a modalidade é a do credor (`RF-523`) |
| `AC-534` | `US-407` | Dado saldo R$ 10.000,00, taxa 2,00% ao mês, prazo 24 e parcela R$ 400,00, então os quatro valores são incompatíveis, a tela mostra o valor teórico R$ 528,72, os quatro originais são salvos e a ficha fica sinalizada para o aluno e para o revisor (`RF-524`) |
| `AC-535` | `US-407` | Dado saldo R$ 10.000,00, taxa 2,00% ao mês, prazo 24 e parcela R$ 528,71 (digitada), então os quatro valores são compatíveis pelo intervalo de arredondamento e nenhuma sinalização aparece (`RF-524`) |
| `AC-536` | `US-407` | Dado o `AC-534`, quando o aluno escolhe recalcular "parcela", então a parcela passa a R$ 528,72 com a marca `calculado` e saldo, taxa e prazo permanecem como digitados; quando escolhe "taxa", a taxa passa a ser a calculada e os outros três permanecem; sem escolha, os originais e a sinalização permanecem (`RF-525`) |
| `AC-537` | `US-408` | Dado "não sei" no saldo de uma dívida, então nenhuma resposta `0` é gravada para o saldo, o valor fica `pendente`, a pergunta não bloqueia o avanço e a pendência aparece em "O que falta informar" (`RF-526`) |
| `AC-538` | `US-408` | Dadas saldo, taxa e prazo informados e "não sei" na parcela, então a parcela é calculada e marcada `calculado`; dadas duas respostas "não sei", então nada é calculado e as duas ficam `pendente` (`RF-526`) |
| `AC-539` | `US-408` | Dadas três dívidas, uma delas pendente, então o plano é gerado com as outras duas, a pendente não aparece na ordem de quitação, o aviso cita a dívida e o dado que falta, e o plano é marcado como parcial no relatório e na tela (`RF-527`) |
| `AC-540` | `US-410` | Dado um valor calculado e outro estimado, então o aluno vê as marcas `calculado`/`estimado`/`hipótese`/`pendente` conforme `RF-528`; o revisor vê `calculado` e `estimado` e não vê fórmula, total de juros nem valores intermediários (`RF-528`, `RF-529`) |
| `AC-541` | `US-406` | Dado o valor 1234567.89, então ele é exibido `1.234.567,89`; dada a entrada `1.234,50`, então é lida como 1234,50 (`RF-530`) |
| `AC-542` | `US-406` | Dada uma dívida com prazo informado ou calculado, então o estado entregue ao motor traz saldo, parcela (nos dois campos de pagamento), taxa mensal normalizada e sistema, sem campo de prazo, e os hashes de `tests/app_aluno/estatica/hashes_congelados.json` não mudam (`RF-531`) |

### Fase 2

| ID | Story | Critério (verificável) |
| -- | ----- | ---------------------- |
| `AC-543` | `US-409` | Dado cartão rotativo com saldo R$ 10.000,00, taxa 2,00% ao mês, sem parcela e sem prazo, então a parcela estimada é R$ 528,72 (24 meses, mesma conta do `AC-517`), marcada `estimado` com a hipótese "24 meses"; vale igual para as demais modalidades (`RF-532`) |
| `AC-544` | `US-409` | Dado o `AC-543` com prazo contratual de 36 meses informado, então a base é 36 meses e o texto não cita 24; dado pagamento habitual R$ 600,00, então a base é R$ 600,00; dado pagamento habitual R$ 0,00 ou vazio, então a base volta a ser 24 meses (`RF-532`, `OQ-73`) |
| `AC-545` | `US-409` | Dado o questionário, então toda dívida pergunta o pagamento mínimo e o pagamento habitual; a parcela estimada aparece em linha separada e marcada, nunca no campo digitado (`RF-533`) |
| `AC-546` | `US-411` | Dadas duas dívidas sem parcela e sem prazo, então as duas têm como pagamento a sua parcela de 24 meses, mesmo com mínimo informado (`RF-534`) |
| `AC-547` | `US-409` | Dada dívida com saldo R$ 10.000,00, taxa 2,00% ao mês (juros R$ 200,00) e pagamento habitual R$ 150,00, então o alerta de dívida que cresce aparece com falta de R$ 50,00 mesmo havendo parcela estimada de R$ 528,72; com habitual R$ 0,00, a falta é R$ 200,00 (`RF-535`) |
| `AC-548` | `US-411` | Dado pagamento habitual informado menor ou igual aos juros do mês, ou resultado do mês negativo, então o plano avisa a inviabilidade, o pagamento do aluno permanece o declarado e o texto não menciona hipótese de 24 meses (`RF-536`, `OQ-74`) |
| `AC-549` | `US-409` | Dado um caso de exemplo com duas dívidas (uma com habitual informado, uma sem parcela nem prazo), então um teste automatizado, rodado sem alterar `engine/`, mostra que `FALTA_DE_JUROS` usa o habitual, que o alerta de crescimento não some e que o resultado do mês é igual ao calculado com o pagamento declarado (`RF-537`, `OQ-83`) |

### Fase 3

| ID | Story | Critério (verificável) |
| -- | ----- | ---------------------- |
| `AC-550` | `US-410` | Dados dois cenários candidatos que diferem só na parcela, então vale o de maior parcela; que empatam em parcela e diferem no saldo, o de maior saldo; depois, nesta ordem, maior taxa, maior prazo e maior custo total (`RF-538`, `OQ-82`) |
| `AC-551` | `US-411` | Dado o cenário conservador escolhido, então o motor recebe o saldo e a taxa do cenário, a parcela e o prazo do cenário não alteram o plano, e o texto ao aluno diz que só saldo e taxa foram usados (`RF-539`) |
| `AC-552` | `US-411` | Dado o mesmo caso em dois cenários diferentes, então o resultado do mês (renda − despesas − pagamentos declarados) é o mesmo nos dois (`RF-540`) |
| `AC-553` | `US-410` | Dado cenário conservador em uso, então a ficha e o relatório o marcam como `hipótese` para o aluno e o revisor o vê sinalizado (`RF-538`) |

> Todo `RF-NN` acima tem ao menos um `AC-NN`: `RF-514` (517, 518, 519, 520, 521, 522), `RF-515` (523), `RF-516` (519, 524, 525), `RF-517` (520, 526), `RF-518` (527), `RF-519` (525, 528, 529), `RF-520` (517, 530), `RF-521` (521, 531), `RF-522` (532), `RF-523` (533), `RF-524` (534, 535), `RF-525` (536), `RF-526` (537, 538), `RF-527` (539), `RF-528` (540), `RF-529` (521, 540), `RF-530` (523, 541), `RF-531` (542), `RF-532` (543, 544), `RF-533` (545), `RF-534` (546), `RF-535` (547), `RF-536` (548), `RF-537` (549), `RF-538` (550, 553), `RF-539` (551), `RF-540` (552).

## 5. Non-Functional Requirements

- **Precisão:** todo cálculo da calculadora usa `Decimal` com o contexto do motor (`engine.precisao.CONTEXTO_MOTOR`); `float` proibido fora do motor. A fronteira de conversão é `app/montagem/conversao.py`. Arredondamento só na camada de exibição, exceto o da parcela calculada (para cima, `RF-520`) e o da taxa interna (4 casas, `RF-522`).
- **Lei nº 3:** o front não faz conta. A tela chama o servidor e exibe o que volta.
- **Performance:** a calculadora responde em menos de 500 ms no p95, incluindo o pior caso da bisseção (máximo de iterações). *(Meta adotada por esta spec; ver `OQ-79`.)*
- **Acessibilidade:** a mensagem do `RF-519` e a sinalização de incompatibilidade são texto, lidas por leitor de tela, e não dependem só de cor; a escolha do `RF-525` é navegável por teclado. Mesmo padrão das telas existentes.
- **Responsividade:** a tela do cálculo segue os mesmos breakpoints da ficha de dívida atual; **novo visual não faz parte do escopo**.
- **Segurança e LGPD:** saldo, parcela e taxa são dados pessoais do aluno. Valor calculado ou estimado é **rastreável e distinguível** do informado (`RF-528`). Logs de erro do cálculo não gravam os valores do aluno.
- **Observabilidade:** falha de convergência, resultado acima do teto e parcela que não reduz o saldo são registrados como evento (sem dados pessoais), para medir quantas fichas caem nessas mensagens.
- **Versionamento:** perguntas novas (prazo, pagamento mínimo, pagamento habitual) e a mudança em `B5.B03`, `B5.C02`, `B5.D06`, `B5.C02A` sobem `QUESTIONARIO_VERSION`; IDs de pergunta são estáveis e nunca reaproveitados (`sdd.config.md` §6).
- **Imutabilidade:** snapshots não são sobrescritos (`V-01`); marca e valor original entram no snapshot.

## 6. Edge Cases

| ID | Situação | Comportamento esperado |
| -- | -------- | ---------------------- |
| `EC-62` | Nenhuma das quatro informações conhecida ("não sei" em todas) | Nada é calculado; dívida `pendente` e fora do plano com aviso (`RF-526`, `RF-527`) |
| `EC-63` | Parcela apenas R$ 0,01 acima dos juros do mês, prazo resultante gigantesco | Acima do prazo máximo (`OQ-79`) o resultado é recusado com a mensagem do `RF-519`; abaixo, é calculado normalmente |
| `EC-64` | Prazo de 1 mês | Parcela = saldo × (1 + taxa), arredondada para cima; taxa = parcela ÷ saldo − 1; prazo 1 em SAC e Price coincidem |
| `EC-65` | Parcela maior que o saldo | Segue o `RF-479`: aviso `PARCELA_MAIOR_QUE_O_SALDO`, sem bloquear; a calculadora trata como prazo 1 mês quando a conta pede |
| `EC-66` | Taxa informada ao ano | Convertida como em `§16.1` do motor; a taxa calculada volta ao ano (`RF-522`) |
| `EC-67` | SAC com taxa 0 | Todas as parcelas iguais, sequência estritamente igual (`RF-515`, `RF-521`) |
| `EC-68` | Bisseção atinge o máximo de iterações | Erro tratado do `RF-519`; nada salvo; resultado apagado (`RF-516`) |
| `EC-69` | Entrada vazia, texto, `1234.56` ou `1.234,5` | Lida pelo formato brasileiro ou recusada com mensagem; nunca interpretada como zero (`RF-518`, `RF-530`) |
| `EC-70` | Aluno reabre a ficha e altera um dos quatro valores depois de um cálculo | A marca `calculado` do valor dependente cai, o resultado antigo é apagado e a calculadora oferece recalcular |
| `EC-71` | Troca de Price para SAC (ou o contrário) depois de um resultado | Resultado calculado anterior é apagado; recalcula-se com o novo sistema |
| `EC-72` | Cartão rotativo ou cheque especial: saldo e taxa, sem prazo nem parcela | Hipótese de 24 meses, parcela estimada marcada (`RF-532`) |
| `EC-73` | Pagamento habitual R$ 0,00 em dívida que cresce | Base de 24 meses; alerta de crescimento com falta igual aos juros (`RF-532`, `RF-535`) |
| `EC-74` | Todas as dívidas pendentes | Nenhum plano é gerado; aviso diz que não há dívida com dados suficientes (`RF-527`) |
| `EC-75` | Alterar dados muda qual é a dívida prioritária | Sem efeito: toda dívida sem prazo e sem pagamento recebe a parcela de 24 meses (`RF-534`, 2026-11-06) |
| `EC-76` | Empate total entre candidatos do cenário conservador | Vale o primeiro na ordem de entrada da ficha, determinístico (`OQ-82`) |
| `EC-77` | Falha ou timeout do cálculo no servidor | Erro tratado, resultado apagado, nada salvo; o aluno pode tentar de novo ou informar "não sei" |

## 7. Assumptions

- Saldo é o de **hoje** e prazo é o **restante**; em SAC a parcela informada é a **1ª parcela do prazo restante** (a maior), coerente com o texto atual de `B5.C02`/`B5.C02A` e com `engine/amortizacao.py` (`amortização = parcela − saldo × taxa`).
- Taxa é **efetiva** (mensal ou anual); a taxa **nominal anual** não existe no PIQ. O valor informado como CET ou como taxa é usado como está (o motor já não distingue, `T-393`).
- Pergunta de prazo restante é nova, em toda dívida e com "não sei" permitido; o prazo nunca é entregue ao motor.
- O arredondamento da parcela para cima é a regra única da parcela calculada; saldo calculado usa o centavo mais próximo e prazo calculado usa meses inteiros para cima (`OQ-80`).
- "Intervalo de arredondamento" é meia unidade da última casa informada (R$ 0,005 em dinheiro, 0,005 ponto percentual em taxa digitada com 2 casas); prazo é exato (`OQ-78`).
- Revisor vê a marca `hipótese` como `estimado` (`OQ-87`).
- Os textos novos citados nesta spec (aviso de dívida pendente, plano parcial, inviabilidade, cenário conservador, perguntas novas) são **propostas a aprovar pelo produto**; só a frase do `RF-519` já foi dada pelo especialista.
- A referência ao curso vem só de `docs/curso-ssd/` (aula 12).

## 8. Risks

| Risco | Impacto | Mitigação |
| ----- | ------- | --------- |
| Mapear parcela estimada, habitual e mínimo nos dois campos de pagamento do motor muda o alerta ou o resultado do mês sem aviso | alto | Spike com dívida de exemplo antes de fechar o plano da Fase 2 (`RF-537`, `AC-549`); `engine/` não muda |
| Prazo do plano diverge 1 mês do prazo da tela por arredondamento | médio | Parcela calculada arredondada para cima (`RF-520`); `AC-526` |
| Permitir "não sei" bloqueia por obrigatória pendente (`app/casos/progresso.py`) ou grava zero | alto | `NAO_SEI` já conta como resposta (`RF-11`); `RF-526` e `AC-537` exigem não gravar zero; revisar `pendencias_obrigatorias` e `AC-08` |
| Cenário conservador injeta só saldo e taxa; expectativa de que prazo e parcela do cenário governem o plano | médio | `RF-539` e texto explícito ao aluno (`AC-551`) |
| Bisseção sem convergência ou resultado absurdo salvo | alto | Máximo de iterações, teto de taxa, erro tratado e nada salvo (`RF-516`, `AC-525`) |
| Liberar SAC para todas as modalidades regride `RF-510`/`T-465` | médio | Revogação explícita (`RF-523`), atualizar testes de `AC-510` |
| Aluno lê a simulação como condição do credor | médio | `RF-523`: texto nunca a apresenta como do credor; marcas `calculado`/`hipótese` |
| Pagamento declarado e pagamento do plano divergem e o resultado do mês muda | alto | `RF-540`, `OQ-83` |
| Dívida pendente fora do plano subestima o endividamento | médio | Aviso nominal e plano marcado como parcial (`RF-527`) |

## 9. Out of Scope

- **Qualquer alteração em `engine/`**, inclusive campo de prazo em `Divida`, tolerância de resíduo e mudança nos dois campos de pagamento (`AC-44`, hashes congelados).
- **Taxa nominal anual** (só efetiva, mensal ou anual).
- **CET como taxa de cálculo própria**: decompor o CET em juros e tarifas, ou usá-lo diferente da taxa. O valor de `B5.D06` entra como está.
- **Novo visual** do PIQ; o HTML de referência só serve de interação.
- Seguros, tarifas e IOF separados da parcela (`OQ-70` do motor); amortização extraordinária na calculadora.
- Total de juros em R$ fora da tela do cálculo, no relatório ou na tela do revisor (`RF-529`).
- Orientação ao aluno sobre o que fazer quando o pagamento é inviável (segue `OQ-71`).
- Trocar o pagamento do aluno por outro, em qualquer cenário.
- Dado de fonte externa ao curso SSD.

## 10. Open Questions

Hipótese adotada entre parênteses; nenhuma bloqueia a spec, e todas devem ser confirmadas antes do plano da fase correspondente.

| ID | Pergunta | Por que importa | Status |
| -- | -------- | --------------- | ------ |
| `OQ-73` | *(OQ-D1)* "Pagamento atual informado" é o pagamento habitual maior que zero? Zero ou vazio dispara os 24 meses. **Hipótese adotada: sim.** | Define quando a hipótese de 24 meses se aplica (`RF-532`, `AC-544`) | `aberta` |
| `OQ-74` | *(OQ-D2)* "Inviável" é pagamento menor ou igual aos juros do mês, ou resultado do mês negativo? **Hipótese adotada: qualquer das duas.** | Define quando o aviso aparece e o texto (`RF-536`, `AC-548`) | `aberta` |
| `OQ-75` | *(OQ-D3)* Qual é a dívida prioritária da regra dos 24 meses? **Hipótese adotada: a dívida-alvo da ordem do motor.** | Define em qual dívida a parcela estimada vale; impacto alto (`RF-534`) | `resolvida 2026-11-06`: não há prioritária; toda dívida estimável recebe 24 meses |
| `OQ-76` | *(OQ-D4)* Os 24 meses valem também para dívida de parcela fixa quando o aluno não sabe parcela nem prazo? **Hipótese adotada: sim (decisão 9).** | Pode contrariar o contrato real (`RF-532`) | `aberta` |
| `OQ-77` | O exemplo do pedido (R$ 10.000, 2% ao mês, 24 meses, Price ⇒ R$ 528,71) é o arredondamento ao mais próximo; a decisão 2 manda arredondar **para cima**, o que dá R$ 528,72 (valor exato ≈ 528,7111). Qual vale? **Hipótese adotada: para cima (R$ 528,72).** | Valor de referência de `AC-517` e dos exemplos derivados (`AC-519`, `AC-526`, `AC-534`, `AC-543`) | `aberta` |
| `OQ-78` | Qual é o intervalo de arredondamento exato da compatibilidade dos quatro valores (por tipo de campo, quantas casas)? **Hipótese: meia unidade da última casa informada; prazo exato.** | Define quando `AC-534` e `AC-535` divergem (`RF-524`) | `aberta` |
| `OQ-79` | Quais são os valores de **teto de taxa**, **prazo máximo** e **máximo de iterações**? **Hipótese: o plano os propõe e o especialista aprova; a spec só exige que existam.** | `RF-516`, `RF-518`, `AC-525`, `EC-63`, meta de desempenho | `aberta` |
| `OQ-80` | Como se arredonda o saldo calculado? **Hipótese: centavo mais próximo; prazo para cima; parcela para cima.** | `AC-518` (tolerância de R$ 0,01) | `aberta` |
| `OQ-81` | "4 casas" da taxa são 4 casas do **percentual** (2,0000%)? E a taxa calculada é exibida com quantas casas? **Hipótese: 4 casas do percentual internamente; exibição com 2.** | Define precisão guardada e `AC-532` (`RF-522`) | `aberta` |
| `OQ-82` | A ordem do cenário conservador (parcela, saldo, taxa, prazo, custo total) é **desempate em cascata** entre cenários candidatos? Quais são os candidatos (originais e teóricos)? Quando o cenário entra, se o aluno não recalcula? **Hipótese: cascata; candidatos são o conjunto digitado e os teóricos calculados; entra quando não houve escolha do `RF-525`.** | Define `RF-538`, `AC-550`, `EC-76` | `aberta` |
| `OQ-83` | O resultado do mês do motor soma `PAGAMENTO_MENSAL_EFETIVO`. Se esse campo recebe a parcela estimada ou o mínimo (`RF-537`), o resultado do mês deixa de usar o pagamento declarado (`RF-540`)? **Hipótese: o spike da Fase 2 define o mapeamento; o resultado do mês exibido usa o declarado.** | Risco alto de o resultado mudar sem aviso; pode exigir decisão sobre `engine/` | `resolvida`: spike (plano 11.1); valor declarado não é cortado pela aplicação, com aviso (2026-11-06); o motor usa `MIN(RESULTADO_MENSAL_ATUAL, declarado) × fator`, e o aviso diz o valor usado e só aparece com cronograma (`T-540`, 2026-11-10) |
| `OQ-84` | Dívida não prioritária sem pagamento mínimo informado ("não sei") e sem habitual: o que acontece? **Hipótese: fica pendente e fora do plano (`RF-527`), nunca zero.** | `RF-533`, `RF-534`, `EC-62` | `resolvida 2026-11-06`: entra no relatório com a parcela de 24 meses |
| `OQ-85` | Pagamento **habitual** é a parcela atual de `B5.C02` (renomeada) ou uma pergunta nova ao lado dela? Redação das perguntas de prazo, mínimo e habitual. **Hipótese: habitual = `B5.C02`; mínimo e prazo são perguntas novas; textos a aprovar.** | Compatibilidade com `RF-479`/`RF-513` e `QUESTIONARIO_VERSION` | `aberta` |
| `OQ-86` | Plano parcial e `ORDEM_STATUS`/`INVENTARIO_COMPLETO`: plano parcial é sempre `PROVISORIA`? Pode ser enviado ao revisor? **Hipótese: a dívida pendente fica fora do estado do motor; o plano é marcado parcial e segue a regra de provisório atual (`RF-465`).** | Evita bloqueio por inventário incompleto e a regra "não inventar dado" | `aberta` |
| `OQ-87` | O revisor vê `hipótese` e `pendente`, ou só `calculado` e `estimado`? **Hipótese: só os dois (a `hipótese` aparece como `estimado`); pendência segue o `RF-461`.** | `RF-529`, `AC-540` | `aberta` |
| `OQ-88` | Para o SAC, a calculadora aceita a parcela "de hoje" como 1ª do prazo restante? E se o aluno informar uma parcela do meio do financiamento? **Hipótese: sempre a de hoje (a maior).** | Evita saldo/prazo errados em SAC (`RF-514`, `RF-521`) | `aberta` |
| `OQ-96` | Dívida com parcela estimada de 24 meses (sem prazo e sem pagamento): o "devido" é R$ 0,00 (resposta 2) e o pagamento do plano é a parcela de 24 meses (resposta 1). O plano então diz ao mesmo tempo "seu mês fecha positivo" (sem a parcela) e "seu mês fecha em −R$ X" (com ela). O "devido" deve ser também a parcela de 24 meses? **Hipótese da equipe: sim.** | Mensagens contraditórias ao aluno (caso `aluno.teste3`, 2026-11-10); `RF-535`, `RF-537` | `aberta` (pergunta ao especialista, 2026-11-10; `T-543`) |

## Ao final: o que falta decidir antes do plano

1. **Fase 1:** `OQ-77` (arredondar para cima ou ao mais próximo no exemplo), `OQ-78`, `OQ-79`, `OQ-80`, `OQ-81`, `OQ-85`, `OQ-86`, `OQ-88`, mais aprovação dos textos novos.
2. **Fase 2:** `OQ-73` a `OQ-76`, `OQ-83` (mapeamento e spike) e `OQ-84`.
3. **Fase 3:** `OQ-82` e `OQ-87`.
