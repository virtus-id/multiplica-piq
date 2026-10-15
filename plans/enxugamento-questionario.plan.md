# Plano: enxugamento do questionário do PIQ

Derivado de `specs/enxugamento-questionario.spec.md`. Cada item rastreia para um requisito (RQ) ou questão em aberto (OQ) da spec.

## 0. Andamento (2026-10-14)

| Etapa | Situação | Tarefas |
|---|---|---|
| 2. Fim da coleta dirigida e do acompanhamento | **Concluída.** Fluxo desligado, Blocos 7, 8 e 10 e 11 de 12 perguntas removidos, código e telas apagados. Ficou `B11.01` (dúvida) | T-387, T-388, T-390 |
| 1. Remoção sem efeito (Blocos 1 a 5) | **Concluída em 87 de 89.** Faltam `B3.S03` e `B5.I01`, que perguntas que ficam usam | T-389 |
| 3. Reduzir o motor | **Parcial.** Feita a pergunta única de custo da dívida (T-393) e a regra de normalização da taxa no motor. As 24 perguntas do motor seguem à espera da aprovação das regras substitutas | T-393 (feita), T-392 (pendente) |
| 4. Ligar ao motor | **Não iniciada.** Depende das regras do especialista | a criar |

Questionário: 267 perguntas, depois 180 (T-389), 125 (T-390), 118 (T-391), 117 (T-396) e **113** com a pergunta única de custo da dívida (T-393). Versão **`1.2.0`**.

## 1. Estratégia

Entregar em quatro etapas, da mais segura para a que muda o cálculo. As etapas 1 e 2 não alteram nenhum plano de aluno; as etapas 3 e 4 sim.

| Etapa | O que entra | Muda o plano do aluno? | Bloqueada por |
|---|---|---|---|
| 1. Remoção sem efeito | 93 perguntas dos Blocos 1 a 5 (RF-402) | Não | Nada, só a aprovação da nova versão da spec |
| 2. Fim da coleta dirigida e do acompanhamento | Blocos 7, 8, 10 e 11 (RF-401) | Não para o primeiro plano | Destino do código (parte final da OQ-1) |
| 3. Reduzir o motor | 24 perguntas que o motor usa (RF-403) | **Sim** | Aprovar as regras substitutas da seção 4 (as questões foram respondidas em 2026-10-14) |
| 4. Ligar ao motor | 32 perguntas (RF-404) e pedidos da observação (RF-406) | **Sim** | OQ-5 (regras do especialista) e os conflitos pai/filha restantes |

## 2. Etapa 1 — remoção sem efeito (RF-402)

1. **Spec canônica §11:** nova versão sem as 93 perguntas. Rastreia: RF-402.
2. **Registros** `collection/registros/bloco-01` a `bloco-05.yaml`: remover as perguntas e subir o `QUESTIONARIO_VERSION` (versão menor). IDs não são reaproveitados.
3. **Condições órfãs:** conferir que nenhuma `condicao_exibicao`, `validacao_cruzada` ou `interpolacao` das perguntas que ficam cita uma removida (OQ-6 lista os 8 conflitos).
4. **Ajustes de código por dependência (32 perguntas removidas têm dependência fora do motor):**

| Pergunta | ID | Depende dele |
|---|---|---|
| Qual é a sua renda líquida nesse vínculo? | B3.S04L | conferências de entrada (aviso ao aluno) |
| Qual é o valor total disponível para essa modalidade? | B3.S06B | telas de coleta do aluno |
| Quanto está atualmente utilizado? | B3.S06C | telas de coleta do aluno |
| Para ajudar a lembrar, quais destes tipos você possui ou acredita possuir… | B5.00A | tela de inventário de dívidas; telas de coleta do aluno |
| Você sabe quanto foi originalmente contratado ou devido nessa operação? | B5.B01 | telas de coleta do aluno |
| Você já consultou a possibilidade de levar ou substituir esta dívida por uma… | B5.G03 | telas de coleta do aluno |
| A proposta é para pagar à vista, parcelado ou existem as duas opções? | B7.04A | coleta dirigida e reabertura |
| O que essa proposta oferece ou pretende fazer? | B7.05 | coleta dirigida e reabertura |
| Qual é o valor para quitar esta dívida à vista, nessa proposta? | B7.07V | coleta dirigida e reabertura |
| O credor diz que existe desconto nessa proposta? | B7.13 | é pai de B7.13A, B7.13B, B7.13C, B7.13D, B7.13E, que precisam continuar existindo |
| Foi informado algum valor de desconto? | B7.13A | conferências de entrada (aviso ao aluno) |
| Qual é o valor atual para quitar esta dívida, antes do desconto? | B7.13B | coleta dirigida e reabertura; conferências de entrada (aviso ao aluno) |
| Qual é o valor do desconto, em reais? | B7.13C | conferências de entrada (aviso ao aluno) |
| Qual é o percentual do desconto? | B7.13D | conferências de entrada (aviso ao aluno) |
| O credor informou o valor final para quitar, já com o desconto? | B7.13E | conferências de entrada (aviso ao aluno); coleta dirigida e reabertura |
| Você possui essa proposta registrada em algum documento ou canal do credor? | B7.16 | homologação: a fonte do dado define o nível de comprovação e pode travar a liberação do plano (regra de liberação do app-aluno/97); coleta dirigida e reabertura |
| Qual destas opções descreve melhor a proposta recebida? | B8.01 | coleta dirigida e reabertura |
| A nova operação inclui algum seguro? | B8.12 | é pai de B8.12A, que precisa continuar existindo |
| Qual é o custo desse seguro? | B8.12A | tela do revisor |
| Qual é o valor desse seguro? | B8.12V | tela do revisor |
| Por quantos meses esse seguro é cobrado? (No total: o período de cobertura;… | B8.12P | tela do revisor |
| De onde vieram as condições desta proposta? | B8.15 | homologação: a fonte do dado define o nível de comprovação e pode travar a liberação do plano (regra de liberação do app-aluno/97); coleta dirigida e reabertura |
| Quanto desse valor recomendado você realmente confirma que pretende utilizar… | B10.C01 | confirmação do ataque (pós-plano) |
| Qual valor você confirma? | B10.C01A | confirmação do ataque (pós-plano) |
| Você conseguiu obter a informação solicitada? | B11.03-INF | acompanhamento pós-plano; coleta dirigida e reabertura |
| Você recebeu uma proposta? | B11.03-REN | coleta dirigida e reabertura; acompanhamento pós-plano |
| Você recebeu uma proposta concreta de troca/portabilidade? | B11.03-TRO | acompanhamento pós-plano |
| A redução de gasto foi realmente implementada? | B11.03-ECO | acompanhamento pós-plano |
| Em que data a dívida foi quitada? | B11.Q02 | acompanhamento pós-plano |
| Quanto foi efetivamente pago no pagamento final/quitação? | B11.Q03 | acompanhamento pós-plano |
| Você possui comprovante ou confirmação da quitação? | B11.Q05 | acompanhamento pós-plano |
| Depois da quitação, quanto realmente deixou de sair do seu orçamento todos os… | B11.Q06 | acompanhamento pós-plano |

5. **Respostas já gravadas** (OQ-10): decidir manter sem ler ou limpar.
6. **Testes:** (a) estado do motor idêntico com e sem as perguntas, nos 4 casos reais (o script de prova já existe em `scratchpad`, a levar para `tests/`); (b) GAB-A/B/C e GAB-01 a GAB-05; (c) carga dos registros sem pergunta órfã.

## 3. Etapa 2 — Blocos 7, 8, 10 e 11 (RF-401)

1. **OQ-1 está respondida: não há acompanhamento.** Falta decidir o destino do código. Duas opções: (a) remover as rotas, os estados e o gatilho de recálculo; (b) deixar o código e apenas desligar a coleta.
2. **Registros:** remover `bloco-07`, `bloco-08`, `bloco-10`, `bloco-11` (menos `B11.01`, em dúvida).
3. **Máquina de estados** (`app/casos/maquina.py`): `COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE`, `ACOMPANHAMENTO` ficam inalcançáveis. Os gates 3 e 4 já estão fixos em neutro na montagem, então o motor não muda.
4. **Homologação:** `B7.16` e `B8.15` (fontes) saem junto; `B5.I02` fica (RF-405).
5. **Testes:** o primeiro plano é idêntico; um caso nunca entra nos estados removidos.

## 4. Etapa 3 — reduzir o motor (RF-403)

As questões OQ-2, OQ-3, OQ-4, OQ-7 e OQ-8 foram respondidas pelo responsável do produto em 2026-10-14 (spec, seção 6). Falta aprovar a regra substituta de cada uma. Para cada pergunta removida, o plano é: regra nova na spec do motor com ID normativo, ajuste no `EstadoFinanceiro` (`engine/estado.py`), leitura em `app/montagem/estado.py`, gabarito atualizado, recálculo dos 4 casos reais com comparação de snapshot (a diferença esperada é registrada, não escondida).

Decisões já tomadas que entram no plano (spec, seção 6):
- **Taxa e CET (RF-407):** um único valor obrigatório, CET como preferência e taxa de juros se não souber, com periodicidade na mesma resposta e texto de ajuda dizendo que o número pode estar escrito como CET ou taxa. Sem marca de qual foi informado (OQ-12). Cinco perguntas por dívida viram uma. A montagem passa a ler a resposta composta, o motor converte ao ano para o mês, e dívida sem o valor bloqueia o cálculo. É a decisão que mais **acrescenta** trabalho de motor.
- **Hábitos de controle:** remoção aceita; nível de controle e confiabilidade passam a derivar só de `B2.06` e `B2.12` (proposta a aprovar).
- **Sinais de recaída e abandono:** remoção aceita; os sinais viram desconhecidos no estado.
- **Tipo de renda:** assumir renda fixa. **Reserva mobilizável:** zero (contradiz a observação do especialista em `B4.02`; confirmar com ele).
- **Investimentos:** `B4.04` fica e `B4.04B` vira "Qual o valor?".

Pontos críticos, em ordem de risco:
1. **Taxa e ranking (RF-407):** é o ponto que mais exige cuidado. A pergunta de taxa e CET é obrigatória, e o cálculo depende dela.
2. **Perfil de controle (OQ-3):** 6 das 8 variáveis; define `NIVEL_CONTROLE` e `CONFIABILIDADE_DADOS`.
3. **Sinais de risco (OQ-4):** recaída, abandono e uso contínuo de limite.
4. **Tipo de renda (OQ-7)** e **reserva mobilizável (OQ-8)**.
5. **Despesa não mensal sem exclusão de dupla contagem** (`B3.NM02D`).

## 5. Etapa 4 — ligar ao motor (RF-404, RF-406)

Antes de qualquer código, escrever a regra de cada ligação (OQ-5). Por pergunta ligada: variável no estado, leitura na montagem, regra no motor com ID normativo e teste com critério de aceite. Sugestão de ordem, do maior efeito para quem está em déficit para o menor: atraso e negativação (`B5.E01` a `B5.E03`), garantia (`B5.F01` a `B5.F03`), despesa fixa ou variável (`B3.DF02`), contribuição familiar e renda variável, e por último patrimônio (imóvel e investimento), que depende das questões abertas OQ-26 e OQ-27 do motor.

Pedidos novos (RF-406): campo de resultado mensal, reescrita da pergunta de taxa/CET e notas orientativas. Cada um vira tarefa própria depois de especificado.

Valores exatos (RF-408): reescrever as 16 perguntas de valor da spec, seção 6, nos YAML da etapa 1 (texto, sem mudança de cálculo). Duas dependem de decisão de engenharia: `B5.C06A` passa a coletar 3 meses (a média vira agregação de entrada) e `B3.02A` fica em suspenso. As validações cruzadas e a lista de perguntas sem "não sei" (OQ-11) entram na mesma etapa.

## 6. Verificação de cada etapa

- Comandos de `sdd.config.md` §2 (lint, mypy, pytest) passando.
- Teste de sensibilidade: etapas 1 e 2 deixam o estado do motor idêntico; etapas 3 e 4 mudam exatamente como a spec define.
- Recalcular os 4 casos reais (Guilherme e os outros) e anexar o diff de snapshot ao relatório de revisão.
- As 6 perguntas indispensáveis seguem presentes; o revisor consegue liberar um plano de ponta a ponta.

## 7. Riscos

- **Reduzir o motor (24 perguntas) pode degradar a qualidade do plano** (confiabilidade, risco, ranking). É a parte que mais pede cuidado.
- **Ligar 32 perguntas amplia o escopo do motor** enquanto o objetivo declarado é reduzir. Vale priorizar por impacto (seção 5).
- Os casos reais já têm respostas ao questionário antigo (OQ-10).

## 7.1 O que já está confirmado e o que falta

| Confirmado (2026-10-14) | Em aberto |
|---|---|
| Pergunta única de CET ou taxa, obrigatória (RF-407) e OQ-12 | OQ-1, só na parte do código: remover os estados e rotas de acompanhamento ou apenas desligar a coleta |
| Sem acompanhamento: plano único (OQ-1) | |
| Hábitos de controle, sinais de recaída e abandono, tipo de renda e reserva: remoção aceita (OQ-3, OQ-4, OQ-7, OQ-8) | OQ-5: regras de uso das 32 perguntas "Liga ao motor" |
| `B4.04` fica; `B4.04B` vira "Qual o valor?" | Conflitos pai e filha restantes (`B3.02`, `B3.05A`, `B3.C02`) |
| Perguntas de valor pedem valor exato e a fonte (RF-408, redações a aprovar) | As 14 dúvidas (você confirma com o especialista) |
| | Reserva: contradição com a observação do especialista em `B4.02` |
| | OQ-11: perguntas que não admitem "não sei" |

## 8. Próximo passo no fluxo SDD

Fechar com o especialista a OQ-1, a OQ-5 (regras de uso das 32 perguntas), os conflitos pai/filha restantes, as 14 dúvidas e a reserva; depois `/sdd:tasks enxugamento-questionario` para quebrar as etapas 1 e 2 em tarefas.

## 9. Architecture

Sem componente novo. A mudança remove partes da aplicação (rotas e telas de coleta dirigida, confirmação do ataque e acompanhamento) e perguntas do registro. O desenho em camadas continua: `collection/` (registros) → `app/montagem/` (estado) → `engine/` (motor) → `report/` (PDF), com `app/http/` e o frontend por cima.

## 10. Tech Stack

Sem mudança: Python 3 com FastAPI, Postgres no Supabase, React com Vite no frontend, `pytest` e `vitest` para testes, `ruff` e `mypy` para qualidade. Nenhuma dependência nova.

## 11. Data Model

Registros YAML em `collection/registros/` (versão `1.2.0`, 113 perguntas após a T-393). Respostas em `app_aluno.respostas` seguem a chave `(caso, variável, item)`; as de perguntas removidas ficam órfãs. A coluna `casos.estado` é texto sem restrição, por isso os três estados removidos do fluxo continuam no enum.

## 12. Data Flow

Coleta → cálculo (Bloco 6) → revisão → plano entregue (`PLANO_LIBERADO`, terminal). Antes da entrega o aluno pode retirar o plano da conferência para editar e o revisor pode devolver o caso. Depois da entrega não há saída.

## 13. Error Handling

Etapas pós-plano antigas respondem com recusa clara. Dívida sem CET e sem taxa bloqueia o cálculo (RF-407). Respostas órfãs não quebram `montar_estado_financeiro` nem a leitura.

## 14. Testing Strategy

Teste de sensibilidade (estado e snapshot idênticos com e sem as respostas removidas), gabaritos `GAB-A/B/C` e `GAB-01` a `GAB-05`, testes por arquivo (a suíte inteira trava neste ambiente), `vitest` no frontend e os e2e do navegador (exigem o pacote `playwright`).

## 15. Traceability

| Requisito | Etapa | Tarefas |
|---|---|---|
| RF-401, RF-409 | 2 | T-387, T-388, T-390 |
| RF-402, RF-405 | 1 | T-389 |
| RF-410 | 1 (extra) | T-391 |
| RF-403 | 3 | T-392 |
| RF-407 | 3 | T-393 |
| RF-408 | 1 (textos) | T-394 |
| RF-404, RF-406 | 4 | T-395 |
