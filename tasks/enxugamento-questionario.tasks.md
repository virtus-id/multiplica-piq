# Backlog — Enxugamento do questionário e plano definitivo

| Campo | Valor                                                              |
| ----- | ------------------------------------------------------------------ |
| Slug  | `enxugamento-questionario`                                         |
| Spec  | [`specs/enxugamento-questionario.spec.md`](../specs/enxugamento-questionario.spec.md) |
| Plano | [`plans/enxugamento-questionario.plan.md`](../plans/enxugamento-questionario.plan.md) |

> Numeração contínua com o backlog `app-aluno` (última tarefa: `T-386`).
> Esta primeira fatia só **desliga** o que vem depois da entrega do plano (`RF-401`, `RF-409`). Remoção de perguntas e mudanças no motor têm tarefas próprias, depois de fechadas as questões em aberto da spec.

## Progresso

`13/17 tarefas concluídas` (T-387 a T-403), mais `T-399` concluída em parte e `T-394` e `T-395` em parte. Pendentes: `T-392`, e o que falta de `T-394`, `T-395`.

| Situação | Tarefas |
| --- | --- |
| Concluídas (12) | T-387, T-388, T-389, T-390, T-391, T-393, T-396, T-397, T-398, T-400, T-401, T-402 |
| Concluída em parte (1) | T-399 |
| Parciais (2) | T-394, T-395 |
| Pendentes (2) | T-392, T-403 |

### `T-387` — Plano entregue é definitivo: desligar acompanhamento e "refazer plano" (backend)

- **Tipo:** `CHANGE` · **Dependências:** nenhuma · **Rastreia:** `RF-401`, `RF-409`
- [x] `app/casos/maquina.py`: remover da `TABELA_TRANSICOES` as saídas de `PLANO_LIBERADO` para `COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE` e `ACOMPANHAMENTO` (gatilhos `abre_blocos_7_8`, `abre_bloco_10`, `abre_bloco_11`) e as duas transições `aluno_refaz_plano` (`PLANO_LIBERADO → COLETA_INICIAL` e `ACOMPANHAMENTO → COLETA_INICIAL`). Os estados e as demais transições ficam
- [x] `app/http/rotas_etapas.py`: as rotas de abertura das etapas pós-plano deixam de existir ou recusam com `409`; `GET .../etapas` devolve tudo `false`
- [x] `app/http/rotas_respostas.py` e `rotas_inicio.py`: `pode_refazer_plano` sempre `false` (`ESTADOS_COM_PLANO_LIBERADO` vazio) e a rota `refazer-plano` recusa com `409`
- [x] `app/casos/fases.py` e `rotas_inicio.py`: um caso em `PLANO_LIBERADO` está sempre na fase do plano, nunca em coleta dirigida, confirmação ou acompanhamento
- [x] Testes: `tests/app_aluno/test_maquina_de_estados.py`, `test_refazer_plano.py`, `test_rotas_inicio.py` e `tests/invariantes/test_propriedades.py` atualizados; novo teste prova que, de `PLANO_LIBERADO`, nenhuma transição é aceita
- [x] `ruff`, `mypy` e `pytest` passam; nenhum teste fora do escopo foi alterado para passar

**Status:** `[x] concluída` — 2026-10-14

### `T-388` — Plano entregue é definitivo: esconder acompanhamento e "refazer plano" (frontend)

- **Tipo:** `CHANGE` · **Dependências:** `T-387` · **Rastreia:** `RF-401`, `RF-409`
- [x] `frontend/src`: remover da tela do plano o botão de refazer o plano, a trilha de acompanhamento e qualquer chamada às etapas pós-plano (`navegacao.ts`, `TelaInicio.tsx`, `TrilhaDaJornada.tsx`, `TelaRecalculo.tsx`, `services/api.ts`)
- [x] O que o aluno vê depois de receber o plano é o plano e nada mais; antes da entrega a tela continua igual
- [x] Testes do frontend (vitest) atualizados e passando; build sem erro

**Status:** `[x] concluída` — 2026-10-14

### `T-389` — Etapa 1: remover do questionário as perguntas confirmadas que o motor não usa (Blocos 1 a 5)

- **Tipo:** `CHANGE` · **Dependências:** `T-387` · **Rastreia:** `RF-402`, `RF-405`
- [x] Remover dos registros `collection/registros/bloco-01` a `bloco-05.yaml` as 89 perguntas abaixo (decisão do especialista, `sai`; nenhuma é lida pelo motor, comprovado em 4 casos reais). Subir o `QUESTIONARIO_VERSION` (versão menor) de cada arquivo alterado. IDs removidos nunca são reaproveitados
- [x] **Não remover** (pendentes ou decididos em contrário): `B3.C02` (pai de B3.C02A e B3.C02B, que ele quer ligar ao motor (conflito aberto)), `B5.D03` (substituída pela pergunta única de CET ou taxa (RF-407), que muda o motor), `B5.D03A` (idem), `B4.04` (o responsável do produto decidiu manter). Também não mexer em nenhuma pergunta em dúvida nem nas que o especialista mandou **ligar ao motor** (`liga`)
- [x] Conferir que nenhuma `condicao_exibicao`, `validacao_cruzada` ou `interpolacao` das perguntas que ficam cita uma pergunta removida (se citar, parar e reportar, sem inventar saída)
- [x] Ajustar o código que depende de cada pergunta removida (telas de coleta, inventário de dívidas, conferência do mês, tela do revisor, `app/montagem/entrada.py`, etc.), sem mudar o cálculo do motor
- [x] Respostas já gravadas: manter as linhas e não lê-las (nada é apagado do banco)
- [x] Testes: ajustar os que citam perguntas removidas; novo teste de regressão prova que o `EstadoFinanceiro` dos casos de prova do repositório é idêntico com e sem as perguntas removidas; GAB-A/B/C e GAB-01 a GAB-05 passam
- [x] `ruff`, `mypy` e `pytest` (arquivos afetados) passam

Perguntas (IDs): B1.03 B1.03A B1.04 B1.06 B1.06A B1.06B B1.06C B1.08 B1.11 B1.12 B2.05A B2.08 B3.02B B3.03A B3.03AO B3.03C B3.05AO B3.06 B3.06A B3.06B B3.DF03 B3.DF04 B3.NM02A B3.NM02AO B3.NM02C B3.NM02CO B3.S02 B3.S03 B3.S04 B3.S04L B3.S05 B3.S05C B3.S06A B3.S06AO B3.S06B B3.S06C B3.S06D B3.S06E B3.S07 B3.S07A B3.S07B B3.S08 B4.02B B4.04A B4.06A B4.06B B4.I02 B4.I03 B4.I06 B4.I07 B4.I08 B4.I09 B4.V02 B4.V03 B4.V04 B4.V04A B4.V05 B4.V06 B4.V07 B4.V08 B4.V08A B4.V08B B4.V08C B4.V09 B4.O01 B4.O02 B4.O03 B4.O04 B4.O04A B4.O05 B4.O06 B4.O07 B4.O08 B4.O09 B4.F01 B5.00A B5.A03 B5.A05 B5.A05A B5.B01 B5.B02 B5.B04 B5.C04 B5.C07A B5.D02 B5.G02 B5.G03 B5.H02 B5.I01

**Status:** `[x] concluída` — 2026-10-14

**Notas da execução:** removidas **87** das 89 perguntas listadas. `B3.S03` (`origem_opcoes` de `B5.A02V`) e `B5.I01` (`nivel_comprovacao_se` de `B5.I02`) **ficam**, porque pergunta que permanece depende delas; decisão do especialista pendente. `QUESTIONARIO_VERSION` de todos os registros: `1.0.3` → `1.1.0` (`collection/carga.py` exige versão idêntica em todos os arquivos). Lista, origem e prova de que o estado não muda: `tests/app_aluno/test_remocao_sem_efeito.py`.

### `T-390` — Etapa 2: remover os Blocos 7, 8, 10 e 11 (coleta dirigida, confirmação do ataque e acompanhamento)

- **Tipo:** `CHANGE` · **Dependências:** `T-387`, `T-388`, `T-389` · **Rastreia:** `RF-401`, `RF-409`
- [x] Remover dos registros os Blocos 7, 8 e 10 por inteiro e, do Bloco 11, as 11 perguntas abaixo. **Fica** `B11.01` (em dúvida; confirmar com o especialista)
- [x] Remover o código que só existia para esses blocos e já está desligado desde `T-387`/`T-388`: `app/casos/coleta_dirigida.py`, `confirmacao_ataque.py`, `acompanhamento.py`, `reabertura.py`, `app/http/rotas_coleta_dirigida.py`, `rotas_bloco10.py`, `rotas_bloco11.py`, `rotas_acoes.py`, `rotas_etapas.py` (e seus registros no aplicativo), `app/motor/acoes.py` e o que mais só eles usarem; no frontend, as telas órfãs (`TelaBloco10`, `TelaColetaDirigida`, `TelaAcoes`, `TelaAcao`, `TelaRecalculo`) e as funções de `services/api.ts` que só elas usam. Antes de apagar qualquer arquivo, confirmar com busca que nada fora do escopo o importa
- [x] Máquina de estados: remover os estados `COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE`, `ACOMPANHAMENTO` e as transições que sobrarem deles, **somente se** isso não exigir migração de dados; caso exija, manter os estados e reportar
- [x] Não mexer no motor (`engine/`) nem nos parâmetros. Se algo do motor só existir para esses blocos (por exemplo `ORDEM_ACOES` e o ataque imediato), **deixar** e reportar como sugestão de tarefa
- [x] Testes (Python e vitest) dos blocos removidos saem junto; o que cobre comportamento que continua existindo fica; E2E do Playwright desatualizados são atualizados ou removidos conforme o que testam
- [x] `ruff`, `mypy`, `pytest` (arquivos afetados) e, no frontend, `tsc -b --noEmit`, `npm run build` e `npx vitest run` passam

Perguntas (IDs): B7.04 B7.04A B7.05 B7.06 B7.07V B7.07 B7.08 B7.09 B7.10 B7.11 B7.12 B7.13 B7.13A B7.13B B7.13C B7.13D B7.13E B7.14 B7.15 B7.16 B8.01 B8.02 B8.03 B8.04 B8.05 B8.05A B8.06 B8.07 B8.08 B8.09 B8.10 B8.11 B8.12 B8.12A B8.12B B8.12V B8.12P B8.13 B8.13A B8.13B B8.14 B8.15 B10.C01 B10.C01A B11.03-INF B11.03-REN B11.03-TRO B11.03-ECO B11.Q01 B11.Q02 B11.Q03 B11.Q04 B11.Q04A B11.Q05 B11.Q06

**Status:** `[x] concluída` — 2026-10-14

**Notas da execução:** removidos `bloco-07.yaml`, `bloco-08.yaml` e `bloco-10.yaml` (a carga aceita a ausência) e, de `bloco-11.yaml`, as 11 perguntas (fica `B11.01`); `QUESTIONARIO_VERSION` segue `1.1.0`. Removido o código dos Blocos 7, 8, 10 e 11 (`app/casos/{coleta_dirigida,confirmacao_ataque,acompanhamento,reabertura}.py`, `app/http/rotas_{coleta_dirigida,bloco10,bloco11,acoes,etapas}.py`, `app/motor/acoes.py`, `app/eventos/`, `app/http/atualizacoes.py`, `fase_do_plano_liberado`) e as telas órfãs do frontend. **Estados `COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE` e `ACOMPANHAMENTO` mantidos no enum, sem nenhuma transição** (a coluna `casos.estado` é texto e a leitura faz `ESTADO_CASO(valor)`; remover exige migração de dados, não criada). `ERRO_DE_CALCULO` só volta a `COLETA_INICIAL`; a tabela tem 10 transições.

### `T-391` — Seguro da dívida fora do questionário e fora do cálculo

- **Tipo:** `CHANGE` · **Dependências:** `T-389` · **Rastreia:** `RF-410`
- [x] Remover dos registros `collection/registros/bloco-05.yaml` as 7 perguntas `B5.D05`, `B5.D05A`, `B5.D05B`, `B5.D05S`, `B5.D05V`, `B5.D05P` e `B5.D05R` (mesma versão `1.1.0` de todos os arquivos; se a carga exigir mudança de versão, subir de modo consistente)
- [x] `app/montagem/estado.py`: `montar_divida` entrega `SEGURO_INCLUIDO_PARCELA=False` e `CUSTO_SEGURO=DESCONHECIDO` fixos; remover `_custo_seguro_cobrado_a_parte`, `_seguros_mensais_a_parte` e o que mais só existia para o seguro, **sem mudar nenhum número do motor** (`engine/` e `parameters/` ficam intocados)
- [x] Onde o seguro era usado fora do motor (conferência do mês em `app/montagem/entrada.py`, divergências e rateio da tela do revisor em `app/http/rotas_revisao.py`, frontend, pendências do PDF em `report/plano.py` e `report/templates/plano/textos-canonicos.yaml`): remover. O custo do seguro **não** pode aparecer como "informação pendente" para o aluno
- [x] Testes que cobrem só o seguro saem; os que cobrem comportamento que continua são ajustados; novo teste prova que o `EstadoFinanceiro` e o `SnapshotOrdem` são idênticos com e sem as respostas do seguro
- [x] `ruff`, `mypy`, `pytest` (arquivo por arquivo) e, no frontend, `tsc -b --noEmit`, `npm run build` e `npx vitest run` passam

**Status:** `[x] concluída` — 2026-10-14

**Notas da execução:** removidas as 7 perguntas `B5.D05*` (125 → 118 registros; `QUESTIONARIO_VERSION` segue `1.1.0`) e, com elas, o que só existia para o seguro: a ficha de restituição que criava item `EXT` (`rotas_coleta.py`), o aviso `RESTITUICAO_SEGURO_EXTRAORDINARIO`, as condições `ORIGEM_RECURSO_EXTRAORDINARIO = B5.D05R` do `bloco-03.yaml`, o rateio e o seguro "não informado" da tela do revisor, a orientação de seguro do plano e o `CUSTO_SEGURO` das pendências do aluno. `montar_divida` entrega `SEGURO_INCLUIDO_PARCELA=False` e `CUSTO_SEGURO=DESCONHECIDO`; o seguro cobrado à parte deixa de somar em `DESPESAS_OPERACIONAIS_ATUAIS`. `engine/` e `parameters/` intocados.

### `T-392` — Etapa 3: remover do questionário e do motor as perguntas que o motor usa

- **Tipo:** `CHANGE` · **Dependências:** `T-389`, `T-393` · **Rastreia:** `RF-403`
- [ ] Depende de aprovar as regras substitutas (spec, seção 6): nível de controle só com `B2.06` e `B2.12`, tipo de renda fixo, sinais de recaída e abandono como desconhecidos, reserva mobilizável, despesa não mensal sem exclusão de dupla contagem
- [ ] Regra normativa nova na spec do motor, ajuste do `EstadoFinanceiro`, da montagem, dos gabaritos e dos casos reais, com o diff de snapshot registrado

**Status:** `[ ] pendente`

### `T-393` — Pergunta única de custo da dívida (CET ou taxa)

- **Tipo:** `FEATURE` · **Dependências:** `T-389` · **Rastreia:** `RF-407`
- **Aprovada pelo responsável do produto em 2026-10-14.**
- [x] **Spec primeiro.** Acrescentar à `specs/motor-calculo.spec.md` uma seção de definições incorporadas (no mesmo padrão das rodadas 2 e 3) com a regra de normalização da taxa: dado um valor e a periodicidade (`MENSAL` ou `ANUAL`), a taxa efetiva mensal é o próprio valor, ou `(1 + anual)^(1/12) - 1`. Escolher o ID normativo seguindo o padrão do projeto e registrar critérios de aceite. Não criar `RF-NN` novo sem a tarefa correspondente em `tasks/motor-calculo.tasks.md` (o CI exige)
- [x] **Motor:** função pura nova em `engine/` que aplica essa regra com precisão decimal integral (`engine/precisao.py`), sem parâmetro `P_*` e sem mudar o contrato `Divida` (a montagem a chama, como já faz com `derivar_NIVEL_CONTROLE`; `engine/` não importa de `app/`)
- [x] **Registro:** remover `B5.D01`, `B5.D01A`, `B5.D01B`, `B5.D03` e `B5.D03A` e criar uma pergunta nova (ID novo, nunca reaproveitado), obrigatória, sem "não sei", `escopo_repeticao: DIVIDA_ID`, `indispensavel: true`, tipo de campo com valor e periodicidade (ao mês ou ao ano, só essas duas) na mesma resposta. Enunciado: "Qual é o Custo Efetivo Total (CET) desta operação? Se não souber, informe a taxa de juros." Ajuda na tela: "No seu contrato, extrato ou aplicativo do banco, esse número pode aparecer escrito como CET ou como taxa de juros. Informe o que encontrar e diga se é ao mês ou ao ano." (se o esquema não tiver campo de ajuda, no enunciado entre parênteses, como em `B3.NM01`)
- [x] **Montagem:** `montar_divida` lê a resposta composta e preenche `TAXA_EFETIVA_MENSAL_NORMALIZADA` chamando a função do motor; o `CET` do estado segue `DESCONHECIDO` (não há marca de qual foi informado)
- [x] **Bloqueio:** dívida sem o valor impede o cálculo (a pergunta é obrigatória; confirmar que o bloqueio do Bloco 6 a enxerga)
- [x] **PDF e tela:** como `CET` passa a ser sempre desconhecido, retirá-lo da lista de informações pendentes (`report/plano.py`, textos canônicos), como foi feito com o seguro na `T-391`; os textos que explicam onde achar a taxa dizem "CET ou taxa de juros"
- [x] Testes: normalização (mensal passa direto; `26,82% a.a.` dá `2% a.m.`, precisão integral), montagem, bloqueio, ranking de juros com taxa vinda de CET anual, e plano sem a linha de CET como pendência; `GAB-A/B/C` e `GAB-01` a `GAB-05` seguem passando; respostas antigas (`B5.D01*`) não quebram a leitura

**Status:** `[x] concluída` — 2026-10-14

**Notas da execução:** regra `§16.1` na spec do motor (seção 16, Rodada 6): ID pela seção, porque os IDs `LETRA-NN` são a lista fechada da canônica e `tests/estatica/test_toda_regra_citada.py` recusa qualquer outro. Função `engine/taxa.py::derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA` (módulo novo; nenhuma regra existente tocada). Pergunta nova `B5.D06` (`OBR` + `REP`, `indispensavel`, sem "não sei"): `SELECAO_UNICA` "ao mês / ao ano" com `abre_campo: TAXA`, que grava o código em `PERIODICIDADE_TAXA_DIVIDA` e o percentual (fração) em `TAXA_DIVIDA`; o mecanismo `variavel_do_campo` da `T-294` foi estendido de `MOEDA` para `TAXA` (esquema, rota de coleta, revisão de respostas e frontend). Registros 117 → 113. Bloqueio: `B5.D06` é `OBR`, então `pendencias_obrigatorias` a lista e o Bloco 6 recusa. Respostas antigas ficam no banco e não são lidas (variáveis novas). `CET` retirado das pendências do PDF (a tela do revisor segue mostrando `CET` como "Não informado"). Allowlist de `app/` e hash congelado de `engine/taxa.py` acrescentados (só entrada nova).

### `T-394` — Perguntas de valor pedem o valor exato

- **Tipo:** `CHANGE` · **Dependências:** `T-389` · **Rastreia:** `RF-408`
- [ ] Reescrever as perguntas que ficam e pedem valor, conforme a tabela da spec (seção 6); verificar o impacto nos testes que comparam textos com a spec canônica
- [x] Aplicar as sugestões de texto já aprovadas (os quatro itens abaixo feitos; as demais perguntas de valor exato seguem pendentes): `B5.D04` ("Além dos juros, existe alguma tarifa, encargo ou custo sendo cobrado nessa operação?"), `B5.D04A` ("Qual valor?"), `B5.00` ("Quantas dívidas ou operações financeiras diferentes você tem hoje?") e `B4.04B` ("Qual o valor?"). `B3.NM01` entra na T-397

**Status:** `[ ] parcial` — feitos os quatro textos acima (três deles, `B5.D04`, `B5.D04A` e `B4.04B`, saíram depois do questionário na `T-398`) e, na `T-402`, as redações aprovadas de `B3.01`, `B3.03B`, `B3.04A`, `B3.C01`, `B3.C02A`, `B3.C02B`, `B2.10`, `B4.01A`, `B4.02A` e o texto novo de `B5.C06A`. **Falta:** `B5.C06A` em três campos de valor (muda o motor, agregação de entrada a especificar), `B3.02A` (em suspenso, depende de `B3.02`), validações cruzadas e a lista de perguntas sem "não sei" (OQ-11).

### `T-395` — Etapa 4: ligar ao motor as perguntas decididas pelo especialista

- **Tipo:** `FEATURE` · **Dependências:** `T-392` · **Rastreia:** `RF-404`, `RF-406`
- [ ] Para cada pergunta ligada: variável no estado, leitura na montagem, regra no motor com ID normativo e teste com critério de aceite; as regras vêm da segunda rodada com o especialista
- [ ] Pedidos novos: campo de resultado mensal e textos de orientação ao aluno

**Status:** `[ ] parcial` — a parte com regra clara do especialista foi feita na `T-399` (avisos de `B5.E01`, `B5.F01`, `B5.00`; `B3.C00`; `B3.C02A`/`B3.C02B`; `B3.04A`; `B3.DF02`; campo "Despesas mensais totais"; exibição de `B5.A01`, `B5.A02V`, `B5.I03`). **Falta:** regras de ordem (`B5.E03`, `B5.F02`, `B5.F03`, `B5.H03`, `B5.H04`), `B3.02A`, as notas orientativas ao aluno (imóvel, reserva acima de 6 meses, aula) e a reescrita de regra de qualquer pergunta em dúvida; depende da segunda rodada com o especialista (OQ-5). A dependência de `T-392` segue valendo para o que mexe no motor.

### `T-396` — Remover a pergunta de veículo (`B4.V01`)

- **Tipo:** `CHANGE` · **Dependências:** `T-389` · **Rastreia:** `RF-402`
- [x] Remover `B4.V01` de `collection/registros/bloco-04.yaml` (decisão do responsável do produto em 2026-10-14; todas as perguntas de detalhe do veículo já saíram na T-389), ajustar a contagem de registros nos testes e conferir que nenhuma pergunta que fica depende dela
- [x] Teste de regressão: estado do motor e snapshot idênticos com e sem a resposta

**Status:** `[x] concluída` — 2026-10-14

### `T-397` — Perguntas de existência: Sim ou Não direto, sem "Não sei"

- **Tipo:** `CHANGE` · **Dependências:** `T-389` · **Rastreia:** `RF-411`
- [x] `B5.E05`: texto "Esta dívida tem processo ou cobrança judicial?", só Sim e Não
- [x] `B5.G01`: texto "O credor já fez uma proposta para esta dívida?", só Sim e Não (sai a opção "Recebi uma proposta, mas ela já venceu")
- [x] `B3.NM01`: texto "Você tem Despesas Extraordinárias já previstas?", só Sim e Não, com a ajuda "São despesas que não acontecem todo mês." (se o registro não tiver campo de ajuda, a ajuda vai no próprio enunciado)
- [x] Ajustar o código que tratava "Não sei" nessas três (montagem, telas, conferências) e os testes, sem mudar o motor; `B5.F04` e a extensão a outras perguntas ficam fora desta tarefa

**Status:** `[x] concluída` — 2026-10-14

### `T-398` — Remover mais 15 perguntas dos Blocos 4, 5 e 11

- **Tipo:** `CHANGE` · **Dependências:** `T-389`, `T-390` · **Rastreia:** `RF-402`
- [x] Remover `B4.04B`, `B4.05`, `B4.06`, `B4.I04`, `B4.I04A`, `B4.I05`, `B4.I05A`, `B5.C03`, `B5.C05`, `B5.C05A`, `B5.D04`, `B5.D04A`, `B5.E04`, `B5.F04` e `B11.01` (decisão do produto e do especialista); apagar `bloco-11.yaml` e o filtro de blocos pós-plano (`BLOCOS_POS_PLANO`, `da_coleta_inicial`), que ficaram sem uso
- [x] Ajustar a contagem de registros (113 → 98) e os testes que citavam essas perguntas; estado do motor e snapshot idênticos com e sem as respostas (`test_remocao_sem_efeito.py`)

**Status:** `[x] concluída` — 2026-10-15

### `T-399` — Ligar ao motor as regras já confirmadas pelo especialista

- **Tipo:** `FEATURE` · **Dependências:** `T-389` · **Rastreia:** `RF-412`, `RF-404`
- [x] (parte A) Avisos `B5.E01`, `B5.F01`, `B5.00` no plano/tela, com a frase de responsabilidade do aluno; sem mudar a ordem
- [x] (parte B) `B3.C00` bloqueia e exige indicar quais itens não conferem (`B3.C00A`); `B3.C02A`/`B3.C02B` comparam com o resultado calculado (`B3.C02C`, `engine/percepcao.py`) e o aluno aceita ou revisa
- [x] (parte B) `B3.04A` soma à renda disponível (`_contribuicao_familiar`) e o plano avisa (tela e PDF)
- [x] (parte A) plano mostra fixo × variável (`B3.DF02`) e "Despesas mensais totais"
- [x] (parte A) Credor (já no nome da dívida) e vínculo (`B5.A02V`, fato do cartão) só exibidos; `B5.I03` (só revisor) feita na `T-402`; testes por critério de aceite; fora: regras de ordem, `B3.02A` e dúvidas

**Status:** `[x] concluída em parte` — 2026-10-15 (commits `b17ae78` e `dfb0e11`). Todos os itens acima estão feitos. **Ficou fora, por decisão de RF-412 ("Fora desta entrega"):** regras de ordem `B5.E03`, `B5.F02`, `B5.F03`, `B5.H03`, `B5.H04` (faltam precedência e pesos), `B3.02A` (conflita com `B3.02`) e tudo marcado como dúvida. Por isso a `RF-404` não está inteira; o resto fica na `T-395`. Funções puras novas do motor: `engine/despesas.py` (`B3.DF02`) e `engine/percepcao.py` (`B3.C02C`); regras normativas na spec do motor §16.2 e §16.3.

### `T-400` — Excluir o pós-entrega do plano e fechar pendências técnicas

- **Tipo:** `CHANGE` · **Dependências:** `T-390`, `T-399` · **Rastreia:** `RF-413`, `RF-409`
- [x] Conferir (leitura) que nenhum caso está em `COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE` ou `ACOMPANHAMENTO`
- [x] Apagar os três estados do código, testes, textos e frontend; `PLANO_LIBERADO` continua terminal
- [x] `QUESTIONARIO_VERSION` 1.3.0 em todos os registros; rótulo de `LIQUIDEZ_INVESTIMENTOS`

**Status:** `[x] concluída` — conferência no banco novo (somente leitura): AGUARDANDO_REVISAO 4, CADASTRADO 7, COLETA_INICIAL 1, nenhum nos três estados. Estados apagados de `ESTADO_CASO`, `fases.py`, `mensagens_de_estado.py`, `textos-canonicos.yaml` e testes; `QUESTIONARIO_VERSION` 1.3.0; rótulos `D0`..`BLOQUEADO` (liquidez do investimento) em `rotulos_de_codigos` (o enum é do motor, em uso, não removido).

### `T-401` — Situação do pagamento (`B5.E01`) sem "Não sei"

- **Tipo:** `CHANGE` · **Dependências:** `T-399` · **Rastreia:** `RF-414`, `RF-411`
- [x] Remover a opção "Não sei" de `B5.E01` em `collection/registros/bloco-05.yaml`; ajustar montagem, telas, conferências e testes que tratavam `NAO_SEI` nessa pergunta, sem mudar o motor
- [x] Teste: estado do motor idêntico para as respostas que continuam válidas

**Status:** `[x] concluída` — commit `559717b`. A pergunta tem `admite_nao_sei: false` e as quatro opções `EM_DIA`, `VENCIDO`, `PARCIAL`, `SEM_PAGAMENTO_REGULAR`. O bloqueio de "fichas faltando" (`B5.00`) foi mantido (`RF-87`) e o aviso foi acrescentado.

### `T-402` — Textos de valor exato aprovados (T-394) e `B5.I03` na tela do revisor

- **Tipo:** `CHANGE` · **Dependências:** `T-399`, `T-401` · **Rastreia:** `RF-415`, `RF-408`
- [x] Aplicar nos registros os textos aprovados das 9 perguntas e o texto novo de `B5.C06A`; ajustar testes que comparam texto com a spec
- [x] `B5.I03` aparece na tela do revisor como informação, sem efeito no cálculo; teste de regressão do estado do motor

**Status:** `[x] concluída`

### `T-403` — Correções do teste de mesa e da revisão final

- **Tipo:** `CHANGE` · **Dependências:** `T-402` · **Rastreia:** `RF-416`, `RF-409`
- [x] Tirar do plano/FAQ/PDF o texto sobre refazer plano, "Gerar um novo plano" e acompanhar
- [x] Investigar e corrigir a diferença de números no plano de quem fecha o mês no negativo
- [x] Sincronizar plano, tarefas e spec; regras normativas das funções novas do motor; limpar restos de texto

**Status:** `[x] concluída` — 2026-10-16 (inclui RF-417)

### `T-404` — Tirar do questionário e do cálculo as perguntas decididas (T-392)

- **Tipo:** `CHANGE` · **Dependências:** `T-403` · **Rastreia:** `RF-418`, `RF-403`
- [ ] Remover as 16 perguntas dos registros (e as que dependem só delas); montagem com valores neutros no lugar das respostas; textos de `B3.NM02A` e `B3.NM02B`; sem alterar `engine/`
- [x] Testes: o plano e o snapshot não quebram sem essas respostas; a mudança de nível de controle, confiabilidade e margem de segurança está provada em teste; ajustar os testes que exigiam as respostas

**Status:** `[x] concluída` — 2026-10-16 (19 perguntas saíram, não 16: também `B3.05BF`, `B3.S03` e `B5.A02V`, que só existiam por causa de `B3.05A` e `B3.S01`. `B3.02B` e `B3.NM02A` já não existiam; o texto novo entrou só em `B3.NM02B`. Fica como débito o código de vínculo que não tem mais origem: `VINCULO_SEM_ITEM`/`CONSIGNADO_SEM_VINCULO` em `app/casos/inventario.py` e a exibição do vínculo em `report/plano.py` e `app/http/serializacao_plano.py`.)

### `T-405` — Textos de reserva, "Sim ou Não direto" e quanto falta cortar

- **Tipo:** `CHANGE` · **Dependências:** `T-404` · **Rastreia:** `RF-418`, `RF-411`
- [x] `B4.03` e `B4.03A` com os textos diretos; sai o "Não sei" de `B4.01`, `B4.04`, `B5.B05`, `B5.FIM02`
- [x] Plano de quem fecha o mês no negativo mostra quanto falta cortar para chegar a zero

**Status:** `[x] concluída`

### `T-406` — Regras de ordem das dívidas

- **Tipo:** `FEATURE` · **Dependências:** `T-404` · **Rastreia:** `RF-418`, `RF-404`
- [x] Spec do motor: regra normativa de ordem (essencial, negativada, peso da garantia 3/2/1, urgência +20%, escolha do aluno com diferença de custo de até 5%) com critérios de aceite
- [x] Perguntas `B5.E03`, `B5.F02`, `B5.F03`, `B5.H03`, `B5.H04` ligadas na montagem e no motor, com hash congelado e testes por critério

**Status:** `[x] concluída`

### `T-407` — Limpeza antes da publicação e resultado do mês no negativo

- **Tipo:** `CHANGE` · **Dependências:** `T-406` · **Rastreia:** `RF-419`
- [x] Resultado do mês no plano de estabilização usa o valor estrutural, com teste de que os números fecham
- [x] Remover código/testes de vínculo sem origem; atualizar os dois testes de banco desatualizados

**Status:** `[x] concluída`

### `T-408` — Remover as 17 perguntas sem uso

- **Tipo:** `CHANGE` · **Dependências:** `T-407` · **Rastreia:** `RF-420`, `AC-416`
- [x] Perguntas apagadas dos registros dos Blocos 2 a 5 (84 → 67)
- [x] Montagem com valores neutros; painel de comparação e exigência de `B3.C00A` removidos; campos sem pergunta fora da tela do revisor
- [x] Testes ajustados; estado e snapshot do motor idênticos com e sem as respostas antigas, exceto os campos neutros

**Status:** `[x] concluída (2026-10-22)`; suíte completa: 12 falhas (1 ambiente de acessibilidade, 11 em test_rotas_plano/test_rotas_revisao_decisao que passam isoladas) e 4 e2e que já falhavam antes

### `T-409` — Pergunta da renda curta, com a instrução em destaque menor

- **Tipo:** `CHANGE` · **Dependências:** `T-408` · **Rastreia:** `RF-117`, `AC-180`
- [x] `B3.01`: enunciado "Qual é o seu salário líquido mensal?"; instrução de preenchimento no novo campo opcional `apoio` do registro
- [x] `apoio` chega ao aluno na pergunta e aparece abaixo do enunciado em destaque menor (campo, escalas e seleções)

**Status:** `[x] concluída (2026-10-22)`

### `T-410` — Valores à vista na lista de fichas curtas

- **Tipo:** `CHANGE` · **Dependências:** `T-409` · **Rastreia:** `RF-421`, `AC-417`
- [x] Implementado (2026-10-22)

**Status:** `[x] concluída (2026-10-22)`

### `T-411` — Sem "Não sei" nos campos de valor do cálculo

- **Tipo:** `CHANGE` · **Dependências:** `T-409` · **Rastreia:** `RF-422`, `AC-418`
- [x] Implementado (2026-10-22)

**Status:** `[x] concluída (2026-10-22)`

### `T-412` — Nome da despesa não mensal

- **Tipo:** `CHANGE` · **Dependências:** `T-409` · **Rastreia:** `RF-423`, `AC-419`
- [x] Implementado (2026-10-22)

**Status:** `[x] concluída (2026-10-22)`

### `T-413` — Fotografia do mês com despesas à vista em tabela

- **Tipo:** `CHANGE` · **Dependências:** `T-409` · **Rastreia:** `RF-424`, `AC-420`
- [x] Implementado (2026-10-22)

**Status:** `[x] concluída (2026-10-22)`

### `T-414` — Quantidade de dívidas exata, com "Nenhuma dívida"

- **Tipo:** `CHANGE` · **Dependências:** `T-413` · **Rastreia:** `RF-425`, `AC-421`
- [x] `B5.00` sem "Não sei"; opção "Nenhuma dívida" e quantidade de 1 a 50 validada no servidor
- [x] "Nenhuma dívida": aviso na pergunta, nenhuma ficha aberta e cálculo bloqueado por pendência de inventário

**Status:** `[x] concluída (2026-10-22)`

### `T-415` — Credor em lista de instituições

- **Tipo:** `CHANGE` · **Dependências:** `T-414` · **Rastreia:** `RF-426`, `AC-422`
- [x] `B5.A01` em menu com 10 instituições e "Outra instituição ou pessoa" com campo de nome; `credor_da_ficha` resolve o nome

**Status:** `[x] concluída (2026-10-22)`

### `T-416` — Status da operação direto

- **Tipo:** `CHANGE` · **Dependências:** `T-415` · **Rastreia:** `RF-427`, `AC-423`
- [x] `B5.A04` com a pergunta nova e sem a opção de quitação a confirmar

**Status:** `[x] concluída (2026-10-22)`

### `T-417` — Sim ou Não de verdade, sem palpite

- **Tipo:** `CHANGE` · **Dependências:** `T-416` · **Rastreia:** `RF-428`, `AC-424`
- [x] "Não sei"/"Talvez"/"Não tenho certeza" fora das 13 perguntas de RF-428; fichas do extraordinário só com "Sim"

**Status:** `[x] concluída (2026-10-22)`

### `T-418` — Pagamento "valor total da dívida" sem digitar duas vezes

- **Tipo:** `CHANGE` · **Dependências:** `T-417` · **Rastreia:** `RF-429`, `AC-425`
- [x] Opção `TOTAL` em `B5.C06`; a montagem copia o saldo devedor de `B5.B03`

**Status:** `[x] concluída (2026-10-22)`

### `T-419` — Fim do botão e da tela "Aguardar a conferência"

- **Tipo:** `CHANGE` · **Dependências:** `T-418` · **Rastreia:** `RF-430`, `AC-426`
- [x] Início sem o botão na fase de conferência, com a explicação da espera; `TelaAguardando` e a rota `#aguardando` removidas

**Status:** `[x] concluída (2026-10-22)`

### `T-420` — Redesenho da tela de acompanhamento do plano

- **Tipo:** `CHANGE` · **Dependências:** `T-419` · **Rastreia:** `RF-431`, `AC-427`
- [x] Componente `AcompanhamentoDoPlano` (andamento em três etapas, cartões de status, prazo e respostas) no Início em conferência; ícones de olho e lápis
- [x] Testes unitários e e2e (desktop e 360px)

**Status:** `[x] concluída (2026-10-22)`

### `T-421` — Andamento em três etapas em todas as telas

- **Tipo:** `CHANGE` · **Dependências:** `T-420` · **Rastreia:** `RF-432`, `AC-428`
- [x] `AndamentoDoPlano` (três etapas) no Início, no termo e nas telas de coleta; `TrilhaDaJornada` (quatro etapas) removida
- [x] Cinco partes da coleta mantidas como progresso secundário (`LateralDaColeta`); testes unitários e e2e ajustados

**Status:** `[x] concluída (2026-10-22)`

### `T-422` — "Minhas respostas" em uma página só, igual para ver e editar

- **Tipo:** `CHANGE` · **Dependências:** `T-421` · **Rastreia:** `RF-433`, `AC-429`
- [x] Layout compartilhado (`PaginaDeRespostas`, `BannerDeRespostas`, `LinhaDaResposta`): índice fixo com âncoras e seção ativa, busca, seções em sequência
- [x] Modo edição com os campos de sempre, rascunho por linha e "Salvar alterações" pela rota de coleta
- [x] Testes reescritos (unitários e e2e); lint, build e navegador executados

**Status:** `[x] concluída (2026-10-22)`

### `T-423` — Título das fichas pelo tipo

- **Tipo:** `FIX` · **Dependências:** `T-422` · **Rastreia:** `RF-434`, `AC-430`
- [x] `agruparPorItem` usa o prefixo do identificador (`DESP`, `REND`, `EXT`, `NM`, `D`…); teste com tipos misturados

**Status:** `[x] concluída (2026-10-22)`

### `T-424` — Índice com textos curtos

- **Tipo:** `CHANGE` · **Dependências:** `T-423` · **Rastreia:** `RF-435`, `AC-431`
- [x] Textos curtos e espaçamento menor no índice; título completo no nome acessível

**Status:** `[x] concluída (2026-10-22)`

### `T-425` — Unificar progresso em "Minhas respostas" e confirmar o envio

- **Tipo:** `CHANGE` · **Dependências:** `T-424` · **Rastreia:** `RF-436`, `AC-432`
- [x] `TelaProgresso` e a rota `#progresso` removidas; atalhos das fichas em "Minhas respostas" (`AtalhosDasFichas`)
- [x] "Enviar para análise do especialista" com confirmação; destino `progresso` do servidor abre "Minhas respostas"

**Status:** `[x] concluída (2026-10-22)`

### `T-426` — Atalhos das fichas por seção e índice confiável

- **Tipo:** `FIX` · **Dependências:** `T-425` · **Rastreia:** `RF-437`, `AC-433`
- [x] "Gerenciar …" no cabeçalho de cada seção (`AtalhosDaSecao`); índice com rolagem corrigida na chegada

**Status:** `[x] concluída (2026-10-22)`

### `T-427` — Fim de B5.CHECK e B5.FIM01 e edição sem uma requisição por linha

- **Tipo:** `CHANGE` · **Dependências:** `T-426` · **Rastreia:** `RF-438`, `RF-439`, `AC-434`, `AC-435`
- [x] `B5.CHECK` e `B5.FIM01` removidas, com a guarda de salvar a ficha
- [x] `com_campos=1` na lista de respostas; a página usa o campo embutido e cancela a busca por linha ao sair

**Status:** `[x] concluída (2026-10-22)`

### `T-428` — Fim do esforço extra (B3.C01A)

- **Tipo:** `CHANGE` · **Dependências:** `T-427` · **Rastreia:** `RF-440`, `AC-436`
- [x] `B3.C01A` removida; montagem com `CONTRIBUICAO_EXTRA_MENSAL = None`; testes que usavam a pergunta como `OPT` real passam a usar `B3.01` com a obrigatoriedade trocada

**Status:** `[x] concluída (2026-10-22)`


### `T-429` — Mesa de conferência do revisor

- **Tipo:** `CHANGE` · **Dependências:** `T-428` · **Rastreia:** `RF-441`, `AC-437`
- [x] `TelaEquipeCaso` recomposta: resumo executivo, análise e dívidas (colunas 68%/32%), apoio à decisão; só dados já entregues pela API

**Status:** `[x] concluída (2026-10-23)`

### `T-430` — Indicadores e dívidas da conferência

- **Tipo:** `CHANGE` · **Dependências:** `T-429` · **Rastreia:** `RF-441`, `RF-442`, `AC-438`
- [x] Seção "Plano como o aluno vai ver" removida da tela do revisor
- [x] Despesas mensais lidas de `DESPESAS_OPERACIONAIS_ATUAIS`; dívidas fora da ordem listadas e contadas
- [x] "Pode ser homologado" sai da faixa; entram "Total em dívidas" (campo `resumo` aditivo na API) e "Possui reserva"

**Status:** `[x] concluída (2026-10-23)`

### `T-431` — Cenário acelerado pelo questionário

- **Tipo:** `CHANGE` · **Dependências:** `T-430` · **Rastreia:** `RF-443`, `AC-439`
- [x] `B3.C02` e `B3.C02A` no bloco 3; montagem volta a ler `CONTRIBUICAO_EXTRA_MENSAL`
- [x] Títulos do item 5: "Se nada mudar", "Seguindo seu plano", "Potencializando seu plano"; nota do verde diz que é simulação do aluno
- [x] Testes ajustados (contagem 63; `B3.C01A` sai da lista de removidas sem efeito)

**Status:** `[x] concluída (2026-10-23)`

### `T-432` — Acabamento visual do PDF

- **Tipo:** `CHANGE` · **Dependências:** `T-431` · **Rastreia:** `RF-444`
- [x] Bloco de refinamento no CSS de `plano.html`, sem mudar conteúdo nem medidas das fichas

**Status:** `[x] concluída (2026-10-23)`
