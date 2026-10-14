# Backlog — Enxugamento do questionário e plano definitivo

| Campo | Valor                                                              |
| ----- | ------------------------------------------------------------------ |
| Slug  | `enxugamento-questionario`                                         |
| Spec  | [`specs/enxugamento-questionario.spec.md`](../specs/enxugamento-questionario.spec.md) |
| Plano | [`plans/enxugamento-questionario.plan.md`](../plans/enxugamento-questionario.plan.md) |

> Numeração contínua com o backlog `app-aluno` (última tarefa: `T-386`).
> Esta primeira fatia só **desliga** o que vem depois da entrega do plano (`RF-401`, `RF-409`). Remoção de perguntas e mudanças no motor têm tarefas próprias, depois de fechadas as questões em aberto da spec.

## Progresso

`5/9 tarefas concluídas`

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
- [ ] Uma pergunta obrigatória, sem "não sei", com valor e periodicidade, e texto de ajuda dizendo que o número pode aparecer como CET ou taxa; substitui `B5.D01`, `B5.D01A`, `B5.D01B`, `B5.D03` e `B5.D03A`
- [ ] A montagem lê a resposta composta, o motor converte ao mês, e dívida sem o valor bloqueia o cálculo

**Status:** `[ ] pendente`

### `T-394` — Perguntas de valor pedem o valor exato

- **Tipo:** `CHANGE` · **Dependências:** `T-389` · **Rastreia:** `RF-408`
- [ ] Reescrever as perguntas que ficam e pedem valor, conforme a tabela da spec (seção 6); verificar o impacto nos testes que comparam textos com a spec canônica

**Status:** `[ ] pendente`

### `T-395` — Etapa 4: ligar ao motor as perguntas decididas pelo especialista

- **Tipo:** `FEATURE` · **Dependências:** `T-392` · **Rastreia:** `RF-404`, `RF-406`
- [ ] Para cada pergunta ligada: variável no estado, leitura na montagem, regra no motor com ID normativo e teste com critério de aceite; as regras vêm da segunda rodada com o especialista
- [ ] Pedidos novos: campo de resultado mensal e textos de orientação ao aluno

**Status:** `[ ] pendente`
