# Backlog — cálculo de dívida (saldo, parcela, taxa e prazo)

| Campo | Valor |
| ----- | ----- |
| Slug  | `calculo-de-divida` |
| Spec  | [`specs/calculo-de-divida.spec.md`](../specs/calculo-de-divida.spec.md) |
| Plano | [`plans/calculo-de-divida.plan.md`](../plans/calculo-de-divida.plan.md) |

> Numeração contínua. O último `T-` existente nos backlogs é `T-471` (`tasks/aluno-deficitario.tasks.md`); `T-472` é a orientação da dívida que cresce (`tasks/pendencias-do-relatorio.tasks.md`, concluída). Esta feature começa em `T-473`. IDs estáveis, nunca renumerados.

## Progresso

`57/66 tarefas concluídas` — Fase 1: 50 tarefas (`T-473` a `T-522`) · Fase 2: 11 (`T-523` a `T-533`) · Fase 3: 5 (`T-534` a `T-538`). Pendentes (9): `T-507`, `T-508`, `T-509`, `T-518`, `T-520`, `T-521`, `T-522`, `T-532`, `T-537`.

## Convenções deste backlog

- **Verificação Python (`VPY`)** = os três comandos de `sdd.config.md` §2, nesta ordem, mais o teste da tarefa:
  `.venv/Scripts/python.exe -m ruff check .` · `.venv/Scripts/python.exe -m mypy engine persistencia collection app report tests` · `.venv/Scripts/python.exe -m pytest -q <arquivo da tarefa>` (e, ao fechar uma entrega, o `pytest -q` completo do config).
- **Verificação front (`VFRONT`)**: `sdd.config.md` não define comandos de front; usa-se `npm --prefix frontend run typecheck` e `npm --prefix frontend run test` (scripts do `frontend/package.json`). Vale lembrar ao especialista: acrescentar ao config via `/sdd:config`.
- `engine/` **não é tocado por nenhuma tarefa** (`RF-531`, `AC-44`); toda tarefa que mexe em `app/`/`collection/`/`report/` roda também `tests/app_aluno/estatica/` (hashes, fronteira de import, fronteira decimal).
- Constantes `Decimal` nascem de `converter_para_dinheiro`/`converter_para_taxa` (PD-02); `float` nunca.
- **Pré-condição da Fase 1 (sem tarefa própria):** `OQ-77` (arredondar para cima, `R$ 528,72`), `OQ-79` (tabela 0.2 do plano) e `OQ-91` (saldo e taxa para baixo) devem estar aprovados pelo especialista antes de `T-475` a `T-478`. Se divergirem, só as constantes e os valores esperados dos testes mudam.
- Tarefa **BLOQUEADA** não é iniciada; o motivo está no campo `Bloqueada por`.

---

# FASE 1 — Calculadora das quatro variáveis (`RF-514` a `RF-531`)

## Entrega 1 — Módulo puro `calculo_divida.py`

### `T-473` — Criar o esqueleto do módulo e a validação de entrada
- **Tipo:** `Data`
- **Dependências:** `nenhuma`
- **Rastreia:** `RF-516`, `RF-518`, `RF-530`, `EC-69`, `AC-527`, `AC-541`
- **Arquivos:** `app/montagem/calculo_divida.py`, `app/montagem/conversao.py` (só se a leitura de prazo exigir)

**Descrição**
`CAMPO_DA_DIVIDA`, `CODIGO_ERRO_DE_ENTRADA`, `CODIGO_ERRO_DE_CALCULO`, `ErroDeEntrada`, `ErroDeCalculo`, `EntradaDaDivida`, as constantes da tabela 0.2 e `validar_entrada` (texto brasileiro para tipos via `conversao.py`; taxa anual normalizada por `engine.taxa.derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA`, PD-04). Sem fórmulas ainda.

**Critérios de aceite**
- [x] Recusa, com código próprio: saldo `<= 0`, parcela `<= 0`, taxa negativa, taxa acima do teto (100% ao mês, já normalizada), prazo não inteiro, prazo `<= 0`, prazo `> 480`, texto ilegível
- [x] `1.234,50` lê como `1234,50`; `1234.56` e `1.234,5` são lidos pelo formato brasileiro ou recusados, nunca zero (`EC-69`)
- [x] Campo ausente (`None`/`""`) é "desconhecido", não erro
- [x] Nenhum `float` e nenhum `Decimal(...)` literal no módulo; imports só de `engine.precisao`, `engine.tipos`, `engine.taxa`, `conversao.py`

**Verificação:** `VPY` com `tests/app_aluno/test_calculo_divida_entrada.py` e `tests/app_aluno/estatica/`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-474` — Implementar a conversão de taxa mensal e anual (cálculo e volta)
- **Tipo:** `Data`
- **Dependências:** `T-473`
- **Rastreia:** `RF-522`, `EC-66`, `AC-532`
- **Arquivos:** `app/montagem/calculo_divida.py`

**Descrição**
Mês para ano por `(1 + i)^12 − 1` sob contexto com 10 dígitos de guarda (mesma técnica de `engine/taxa.py`); ano para mês reaproveita o motor. Arredondamento da taxa calculada: para baixo, 6 casas da fração (4 do percentual); exibição com 2 casas fica no formatador existente.

**Critérios de aceite**
- [x] `26,82% ao ano` ida e volta com `2,00% ao mês` dentro da grade da taxa (±0,005 pp)
- [x] Taxa calculada nunca sai com mais de 2 casas na exibição (`2,00`, nunca `2,0000`)
- [x] Taxa `0` converte para `0` nos dois sentidos

**Verificação:** `VPY` com `tests/app_aluno/test_calculo_divida_taxa_periodo.py`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-475` — Implementar `calcular_parcela` (Price e SAC)
- **Tipo:** `Data`
- **Dependências:** `T-473`
- **Rastreia:** `RF-514`, `RF-515`, `RF-520`, `EC-64`, `AC-517`, `AC-521`, `AC-523`
- **Arquivos:** `app/montagem/calculo_divida.py`

**Descrição**
Price: anuidade (taxa 0 ⇒ `S/n`). SAC: `S/n + S·i` (a de hoje, `OQ-88`). Arredonda a `RESIDUO_DE_ARREDONDAMENTO` e depois **para cima** ao centavo.

**Critérios de aceite**
- [x] `10.000`, 2% a.m., 24, Price ⇒ `528,72` (exato ≈ 528,7111)
- [x] `12.000`, 1%, 12, SAC ⇒ `1.120,00`
- [x] Taxa 0: `1.200` em 12 ⇒ `100,00` em Price e em SAC
- [x] Prazo 1: parcela = `saldo × (1 + taxa)` para cima
- [x] Resíduo `…0000001` acima de um centavo exato não sobe um centavo

**Verificação:** `VPY` com `tests/app_aluno/test_calculo_divida_formulas.py -k parcela`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-476` — Implementar `calcular_saldo` (Price e SAC)
- **Tipo:** `Data`
- **Dependências:** `T-473`
- **Rastreia:** `RF-514`, `RF-515`, `AC-518`, `AC-523`
- **Arquivos:** `app/montagem/calculo_divida.py`

**Descrição**
Price: valor presente das parcelas (taxa 0 ⇒ `P·n`). SAC: `P1 / (1/n + i)`. Arredonda **para baixo** ao centavo (`OQ-80`/`OQ-91`) para o plano não passar de `n` para `n + 1`.

**Critérios de aceite**
- [x] `1.000`, 2%, 12, Price ⇒ `10.575,34` (tolerância `0,01`)
- [x] `100`, taxa 0, 12 ⇒ `1.200,00` em Price e SAC
- [x] SAC com `P1 = 1.120`, 1%, 12 ⇒ `12.000,00`

**Verificação:** `VPY` com `tests/app_aluno/test_calculo_divida_formulas.py -k saldo`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-477` — Implementar `calcular_taxa` (Price por bisseção, SAC fechada)
- **Tipo:** `Data`
- **Dependências:** `T-473`, `T-474`
- **Rastreia:** `RF-514`, `RF-515`, `RF-516`, `AC-519`, `AC-523`, `AC-524`, `AC-525`, `EC-68`
- **Arquivos:** `app/montagem/calculo_divida.py`

**Descrição**
Price: limite superior inicial `0,01` que dobra até `min(2×, TETO)`, máximo 100 bisseções, tolerância da tabela 0.2; `S/n` dentro de meio centavo de `P` ⇒ taxa `0`. SAC: `i = P1/S − 1/n`, negativa ⇒ erro. Não convergir ou passar do teto ⇒ `ErroDeCalculo`, nada devolvido.

**Critérios de aceite**
- [x] `10.000`, `528,72`, 24, Price ⇒ `2,00%` (±0,01 pp)
- [x] `1.000`, `400`, 3, Price ⇒ `9,70%` (±0,05 pp) e um contador/gancho de teste prova que o limite **dobrou** além de 1%
- [x] Taxa 0 é resultado válido (não erro, não vazio)
- [x] Entrada que estoura as iterações ou o teto levanta `ErroDeCalculo`
- [x] SAC com resultado negativo levanta `ErroDeCalculo`

**Verificação:** `VPY` com `tests/app_aluno/test_calculo_divida_formulas.py -k taxa`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-478` — Implementar `calcular_prazo` confirmado pela recorrência
- **Tipo:** `Data`
- **Dependências:** `T-473`, `T-474`
- **Rastreia:** `RF-514`, `RF-515`, `RF-517`, `RF-519`, `EC-63`, `EC-65`, `AC-520`, `AC-522`, `AC-528`, `AC-526`
- **Arquivos:** `app/montagem/calculo_divida.py`

**Descrição**
Price: `−ln(1 − S·i/P)/ln(1+i)` apenas **semeia**; o prazo final vem da recorrência do motor (`saldo × (1+i) − min(pagamento, saldo + juros)`, precisão integral, sem tolerância de resíduo), PD-03. SAC: `a = P1 − S·i`, `n = ⌈S/a⌉`. `P <= S·i` ⇒ `NAO_REDUZ_SALDO`; `> 480` ⇒ `PRAZO_ACIMA_DO_MAXIMO`. Parcela maior que o saldo ⇒ prazo 1.

**Critérios de aceite**
- [x] `10.000`, 2%, parcela `600`, Price ⇒ `21` (fracionário 20,47 sobe)
- [x] `12.000`, 1%, `1.120`, SAC ⇒ `12`
- [x] Parcela `200` e `150` com `10.000` a 2% ⇒ `NAO_REDUZ_SALDO`
- [x] Parcela R$ 0,01 acima dos juros com prazo gigante ⇒ `PRAZO_ACIMA_DO_MAXIMO`; abaixo de 480 calcula
- [x] Taxa 0 ⇒ `⌈S/P⌉`

**Verificação:** `VPY` com `tests/app_aluno/test_calculo_divida_formulas.py -k prazo`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-479` — Implementar `cronograma` e `total_de_juros`
- **Tipo:** `Data`
- **Dependências:** `T-475`, `T-478`
- **Rastreia:** `RF-517`, `RF-521`, `RF-529`, `EC-67`, `AC-520`, `AC-521`, `AC-531`
- **Arquivos:** `app/montagem/calculo_divida.py`

**Descrição**
`LinhaDoCronograma` e `cronograma(...)`: exibição em centavos, resíduo da amortização na última parcela; último pagamento **calculado** (amortização restante + juros do saldo restante), nunca copiado. `total_de_juros` só para a prévia.

**Critérios de aceite**
- [x] SAC `12.000`, 1%, 12: parcelas 1.120 / 1.110 / … / 1.010; total de juros `780,00`
- [x] SAC `10.000`, 3, 1%: amortizações `3.333,33 / 3.333,33 / 3.333,34`, soma `10.000,00`, parcelas decrescentes
- [x] Price prazo 21 (`AC-520`): 20 pagamentos de `600` e o 21º com `0 < x < 600`, saldo final `0`
- [x] SAC com taxa 0: todas as parcelas iguais

**Verificação:** `VPY` com `tests/app_aluno/test_calculo_divida_cronograma.py`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-480` — Implementar `conferir_compatibilidade` (quatro valores)
- **Tipo:** `Data`
- **Dependências:** `T-475`, `T-474`
- **Rastreia:** `RF-524`, `AC-534`, `AC-535`
- **Arquivos:** `app/montagem/calculo_divida.py`

**Descrição**
Grade fixa de `OQ-78` (dinheiro ±`0,005`; taxa ±`0,005` pp na periodicidade digitada e renormalizada; prazo exato). Intervalo teórico `[P(S−δS, i−δi, n), P(S+δS, i+δi, n)]` encontra `[parcela ± 0,005]`. Devolve também a parcela teórica.

**Critérios de aceite**
- [x] `10.000`, 2%, 24, parcela `400` ⇒ `INCOMPATIVEL`, teórica `528,72`
- [x] Mesmos dados com parcela `528,71` ⇒ `COMPATIVEL`
- [x] "2" digitado vale `2,00 ± 0,005`, não `2 ± 0,5`
- [x] Parcela `0,00` com os quatro informados ⇒ `INCOMPATIVEL` (`OQ-92`)

**Verificação:** `VPY` com `tests/app_aluno/test_calculo_divida_compatibilidade.py`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-481` — Testar os ACs numéricos por variável e por sistema (Price e SAC)
- **Tipo:** `Test`
- **Dependências:** `T-475`, `T-476`, `T-477`, `T-478`, `T-479`
- **Rastreia:** `RF-514`, `RF-515`, `RF-517`, `RF-520`, `RF-521`, `AC-517`, `AC-518`, `AC-519`, `AC-520`, `AC-521`, `AC-522`, `AC-523`, `AC-524`, `AC-531`
- **Arquivos:** `tests/app_aluno/test_calculo_divida_formulas.py`, `tests/app_aluno/test_calculo_divida_cronograma.py`

**Descrição**
Tabela parametrizada: cada incógnita (parcela, saldo, taxa, prazo) × {Price, SAC} × {taxa positiva, taxa 0, prazo 1}. Cada caso cita seu `AC-NN`. Inclui os quatro valores usados em cada sentido (os mesmos três dados reproduzem o quarto).

**Critérios de aceite**
- [x] Todo `AC-517` a `AC-524` e `AC-531` tem ao menos um caso nomeado
- [x] Taxa 0 nos três sentidos, Price e SAC iguais
- [x] Parcela ≤ juros ⇒ `NAO_REDUZ_SALDO` em Price e SAC
- [x] Prazo fracionário (20,47) ⇒ 21
- [x] Os quatro valores do `AC-517` a `AC-520` fecham entre si (ida e volta)

**Verificação:** `VPY` com os dois arquivos

**Status:** `[x] implementada (2026-11-04)`

---

### `T-482` — Testar erros, entradas inválidas e valor digitado intocado
- **Tipo:** `Test`
- **Dependências:** `T-473`, `T-477`, `T-478`
- **Rastreia:** `RF-516`, `RF-518`, `RF-519`, `RF-520`, `RF-530`, `EC-63`, `EC-68`, `EC-69`, `AC-525`, `AC-527`, `AC-528`, `AC-530`, `AC-541`
- **Arquivos:** `tests/app_aluno/test_calculo_divida_entrada.py`, `tests/app_aluno/test_calculo_divida_erros.py`

**Descrição**
Tabela de entradas inválidas (0, negativo, `2,5`, vazio, `1234.56`, `1.234,5`, teto, prazo 481); estouro de iterações e de teto; a frase do `RF-519` comparada caractere por caractere com o YAML (depende do arquivo criado em `T-502`, portanto a asserção da frase fica em `T-506`).

**Critérios de aceite**
- [x] Cada entrada inválida produz o código previsto e nada é devolvido como calculado
- [x] Parcela digitada `528,71` com saldo `10.000` e prazo 24: calcular a taxa não altera a parcela
- [x] `1234567.89` formata `1.234.567,89` (formatador existente)
- [x] Falha de convergência e teto levantam `ErroDeCalculo`, sem valor parcial

**Verificação:** `VPY` com os dois arquivos

**Status:** `[x] implementada (2026-11-04)`

---

### `T-483` — Testar as propriedades (hypothesis)
- **Tipo:** `Test`
- **Dependências:** `T-475`, `T-476`, `T-477`, `T-478`
- **Rastreia:** `RF-514`, `RF-516`, `RF-517`, `AC-526`
- **Arquivos:** `tests/app_aluno/test_calculo_divida_propriedades.py`

**Descrição**
Ida e volta `prazo(calcular_parcela(S,i,n)) == n` (Price e SAC); `calcular_parcela(calcular_saldo(P,i,n)) ≈ P`; recorrência sem resíduo positivo após `prazo` meses; monotonia da taxa; domínio gerado respeita os limites 0.2 (inclui taxa 0 e prazo 1).

**Critérios de aceite**
- [x] As quatro propriedades passam com `hypothesis` (≥ 200 exemplos cada)
- [x] Nenhum exemplo falha por `float` ou por exceção não tratada
- [x] Pior caso (bisseção no máximo) roda abaixo de 500 ms

**Verificação:** `VPY` com `tests/app_aluno/test_calculo_divida_propriedades.py`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-484` — Testar a equivalência prazo da calculadora = mês de quitação do motor
- **Tipo:** `Test`
- **Dependências:** `T-478`
- **Rastreia:** `RF-517`, `RF-531`, `AC-526`
- **Arquivos:** `tests/app_aluno/test_calculo_divida_equivalencia_motor.py`

**Descrição**
Para um conjunto de dívidas isoladas (sem ataque), o prazo da calculadora é o mês de quitação projetado por `engine.motor.calcular_plano`. O teste pode importar o motor; o módulo de produção, não.

**Critérios de aceite**
- [x] `10.000`, 2%, parcela exibida `528,72`, Price ⇒ quita em 24, não em 25
- [x] Conjunto parametrizado em Price e SAC, saldo e taxa variados, prazo calculado = prazo do motor
- [x] `tests/app_aluno/estatica/test_fronteira_import_engine.py` segue verde sem exceção nova

**Verificação:** `VPY` com o arquivo e `tests/app_aluno/estatica/`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-485` — Testar a conferência dos quatro valores e o valor teórico
- **Tipo:** `Test`
- **Dependências:** `T-480`
- **Rastreia:** `RF-524`, `AC-534`, `AC-535`
- **Arquivos:** `tests/app_aluno/test_calculo_divida_compatibilidade.py`

**Descrição**
Casos de borda da grade de `OQ-78`: fronteira de meio centavo, taxa digitada com 1 e 2 casas, taxa anual, prazo exato, Price e SAC; valor teórico devolvido.

**Critérios de aceite**
- [x] `528,71` compatível, `400` incompatível, `528,72` compatível (`R$ 10.000`, 2%, 24)
- [x] Fronteira ±`0,005` testada dos dois lados
- [x] Prazo diferente em 1 mês ⇒ incompatível

**Verificação:** `VPY` com o arquivo

**Status:** `[x] implementada (2026-11-04)`

---

## Entrega 2 — `premissas.py` e `resolver_divida`

### `T-486` — Implementar `resolver_divida` (valores, marcas e situação)
- **Tipo:** `Data`
- **Dependências:** `T-475`, `T-476`, `T-477`, `T-478`
- **Rastreia:** `RF-526`, `RF-527`, `RF-528`, `RF-531`, `OQ-92`
- **Arquivos:** `app/montagem/premissas.py`

**Descrição**
`MARCA_DO_VALOR`, `SITUACAO_DA_DIVIDA`, `ValorDaDivida`, `PremissasDaDivida` e `resolver_divida(respostas, DIVIDA_ID)` pela tabela-verdade da seção 4.4 (derivar, não armazenar, PD-06). `NAO_SEI` fica intacto na resposta; o calculado existe só na saída. Parcela `0,00` é resposta válida e fica fora do cálculo.

**Critérios de aceite**
- [x] Um desconhecido entre S/P/T ⇒ `COMPLETA`, campo `CALCULADO`; só N desconhecido ⇒ `COMPLETA`, N `CALCULADO` e fora do motor
- [x] Dois ou mais desconhecidos de S/P/T, ou N mais um deles ⇒ `PENDENTE`, `faltas` nomeia S/P/T
- [x] Nenhum `0` é produzido para "não sei"
- [x] Quatro informados incompatíveis ⇒ `INCOMPATIVEL` com `parcela_teorica`; originais intactos
- [x] `taxa_mensal_normalizada` e `taxa_na_periodicidade` preenchidas conforme a periodicidade gravada
- [x] Módulo sem I/O; imports só de `engine.*` permitidos e `conversao.py`

**Verificação:** `VPY` com `tests/app_aluno/test_premissas_da_divida.py` e `tests/app_aluno/estatica/`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-487` — Implementar a escolha de recálculo com impressão dos valores
- **Tipo:** `Data`
- **Dependências:** `T-486`
- **Rastreia:** `RF-525`, `EC-70`, `EC-71`, `AC-536`
- **Arquivos:** `app/montagem/premissas.py`

**Descrição**
Lê `INFORMACAO_A_RECALCULAR = "<CAMPO>|<impressão>"` (hash curto dos quatro valores e do sistema). Escolha vale só se a impressão confere; o campo escolhido vira o teórico, `CALCULADO`, e os outros três permanecem. `NENHUMA` ou impressão velha ⇒ originais e sinalização.

**Critérios de aceite**
- [x] Escolher "parcela" no caso do `AC-534` ⇒ parcela `528,72` `CALCULADO`; saldo, taxa e prazo como digitados
- [x] Escolher "taxa" ⇒ taxa calculada e os outros três intactos
- [x] Alterar qualquer um dos quatro valores ou o sistema invalida a escolha sem escrita alguma
- [x] `recalcular_escolhido` reflete a escolha válida

**Verificação:** `VPY` com `tests/app_aluno/test_premissas_da_divida.py -k recalcular`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-488` — Implementar `dividas_pendentes` e `campos_resolvidos`
- **Tipo:** `Data`
- **Dependências:** `T-486`
- **Rastreia:** `RF-526`, `RF-527`, `EC-62`, `EC-74`
- **Arquivos:** `app/montagem/premissas.py`

**Descrição**
`dividas_pendentes(respostas, itens_por_escopo)` lista as `PENDENTE`; `campos_resolvidos(...)` devolve `frozenset[(item_id, VARIAVEL_GRAVADA)]` dos campos que a calculadora resolveu (PD-11).

**Critérios de aceite**
- [x] Quatro "não sei" ⇒ dívida pendente (`EC-62`)
- [x] Campo calculado aparece em `campos_resolvidos`; campo pendente não
- [x] Ordem das dívidas pendentes segue a ordem da ficha

**Verificação:** `VPY` com `tests/app_aluno/test_premissas_da_divida.py -k pendentes`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-489` — Testar a tabela-verdade completa (2⁴ × Price/SAC)
- **Tipo:** `Test`
- **Dependências:** `T-486`, `T-488`
- **Rastreia:** `RF-526`, `RF-527`, `RF-528`, `AC-537`, `AC-538`, `AC-539`
- **Arquivos:** `tests/app_aluno/test_premissas_da_divida.py`

**Descrição**
As 16 combinações de desconhecidos × dois sistemas, mais parcela `0,00` e dívida sem nenhuma resposta; compara situação, marca de cada campo, `faltas` e ausência de qualquer `0` gravado.

**Critérios de aceite**
- [x] 32 combinações cobertas e nomeadas
- [x] "Não sei" em saldo ⇒ `PENDENTE`, nenhuma resposta `0` produzida
- [x] Saldo, taxa e prazo informados + "não sei" na parcela ⇒ parcela `CALCULADO`; duas "não sei" ⇒ ambos `PENDENTE`

**Verificação:** `VPY` com o arquivo

**Status:** `[x] implementada (2026-11-04)`

---

### `T-490` — Testar recálculo, invalidação e troca de sistema
- **Tipo:** `Test`
- **Dependências:** `T-487`
- **Rastreia:** `RF-525`, `EC-70`, `EC-71`, `AC-536`
- **Arquivos:** `tests/app_aluno/test_premissas_da_divida.py`

**Descrição**
Escolha de recálculo, impressão que deixa de valer ao mudar um valor, troca Price para SAC sem resíduo do resultado anterior.

**Critérios de aceite**
- [x] `AC-536` completo: parcela, taxa e "sem escolha"
- [x] Mudar um dos quatro valores remove o `CALCULADO` do dependente sem escrever nada
- [x] Trocar o sistema recalcula com o novo sistema

**Verificação:** `VPY` com o arquivo

**Status:** `[x] implementada (2026-11-04)`

---

## Entrega 3 — Registro `bloco-05.yaml` e versão `1.4.0`

### `T-491` — Criar o tipo de resposta `CALCULO_DIVIDA` no registro e na carga
- **Tipo:** `Data`
- **Dependências:** `nenhuma`
- **Rastreia:** `RF-514`, `RF-523`
- **Arquivos:** `collection/registro.py`, `collection/carga.py`, `tests/app_aluno/test_carga.py`

**Descrição**
Décimo `TipoResposta`; a carga valida o tipo novo (escopo `DIVIDA_ID`, variável `CONFERENCIA_DA_DIVIDA`).

**Critérios de aceite**
- [ ] Carga aceita pergunta `CALCULO_DIVIDA` bem formada e recusa mal formada
- [ ] Nenhum outro tipo muda de comportamento

**Verificação:** `VPY` com `tests/app_aluno/test_carga.py`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-492` — Registrar `B5.CALC01` e `B5.C02B` em `bloco-05.yaml`
- **Tipo:** `Data`
- **Dependências:** `T-491`
- **Rastreia:** `RF-514`, `RF-523`, `RF-526`
- **Arquivos:** `collection/registros/bloco-05.yaml`

**Descrição**
`B5.CALC01` (tipo `CALCULO_DIVIDA`, escopo `DIVIDA_ID`, logo após `B5.A02`, `OPT`, `REP`, variável `CONFERENCIA_DA_DIVIDA`) e `B5.C02B` (`NUMERO`, `OPT`, `REP`, "não sei", variável `PRAZO_RESTANTE_MESES`). IDs nunca existiram antes. Enunciados provisórios; a redação final é `T-509`.

**Critérios de aceite**
- [ ] Ambas aparecem na ficha de toda dívida, nessa ordem
- [ ] `B5.C03` a `B5.C07A` seguem como histórico, sem reaproveitamento
- [ ] Perguntas existentes continuam com ID e variável idênticos

**Verificação:** `VPY` com `tests/app_aluno/test_carga.py tests/app_aluno/test_ficha_enxuta.py`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-493` — Ajustar `B5.B03`, `B5.C02`, `B5.D06` e `B5.C02A`
- **Tipo:** `Data`
- **Dependências:** `T-492`
- **Rastreia:** `RF-523`, `RF-526`, `OQ-93`, `AC-533`, `AC-537`
- **Arquivos:** `collection/registros/bloco-05.yaml`

**Descrição**
`B5.B03` e `B5.C02` com `admite_nao_sei: true` (sai a nota "sem não sei (T-411)"; `indispensavel` mantido). `B5.D06` ganha a opção "Não sei a taxa" (`DESCONHECIDA`, mesmo precedente de `T-283`). `B5.C02A` perde a `condicao_exibicao`, vira `OPT` e `indispensavel: false`, texto sem "financiamento" nem "do credor"; Price pré-selecionado. As perguntas não viram condicionais (0.4).

**Critérios de aceite**
- [ ] `B5.C02A` presente em `CARTAO_ROTATIVO`, `PESSOAL` e `CONSIGNADO`, Price pré-selecionado
- [ ] "Não sei" aceito em saldo, parcela e taxa e nunca gravado como `0`
- [ ] Enunciado de `B5.C02A` não afirma que a modalidade é a do credor

**Verificação:** `VPY` com `tests/app_aluno/test_carga.py tests/app_aluno/test_ficha_enxuta.py`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-494` — Subir `QUESTIONARIO_VERSION` para `1.4.0` nos oito arquivos
- **Tipo:** `Data`
- **Dependências:** `T-493`
- **Rastreia:** `RF-523`, `RF-526`
- **Arquivos:** `collection/registros/bloco-01.yaml`, `bloco-02.yaml`, `bloco-03.yaml`, `bloco-04.yaml`, `bloco-05.yaml`, `bloco-09.yaml`, `bloco-12-*.yaml`

**Descrição**
Mesma versão em todos os arquivos de `collection/registros/` (PD-13). Sem migração de esquema e sem tabela nova.

**Critérios de aceite**
- [ ] Nenhuma ocorrência de `1.3.0` em `collection/registros/`
- [ ] Teste de consistência de versão entre arquivos passa

**Verificação:** `VPY` com `tests/app_aluno/test_carga.py`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-495` — Atualizar os testes legados das revogações e da versão
- **Tipo:** `Test`
- **Dependências:** `T-493`, `T-494`
- **Rastreia:** `RF-513`, `RF-523`, `RF-526`, `AC-533`
- **Arquivos:** `tests/app_aluno/test_remocao_sem_efeito.py`, `test_sac_imobiliario.py`, `test_pendencias_do_relatorio.py`, `test_custo_da_divida.py`, `test_ficha_enxuta.py`, `test_carga.py` e todo teste que cite `1.3.0`, `AC-510`/`T-465`, `T-411` ou `saldo.admite_nao_sei is False`

**Descrição**
Encontrar por busca (`1.3.0`, `T-465`, `T-411`, `admite_nao_sei`) e atualizar cada asserção para o novo contrato, com comentário citando a revogação (`RF-523`, `RF-526`). Não apagar teste: reescrever o esperado.

**Critérios de aceite**
- [ ] `pytest -q` completo sem falha nova em relação ao `HEAD` (28 falhas preexistentes conhecidas, nenhuma a mais)
- [ ] `grep` de `1.3.0` em `tests/` só sobra em contexto histórico comentado
- [ ] Lista dos arquivos alterados registrada no corpo do commit

**Verificação:** `VPY` completo (`pytest -q` do `sdd.config.md`)

**Status:** `[x] implementada (2026-11-04)`

---

### `T-496` — Recusar `POST /resposta` para `CALCULO_DIVIDA` e serializar a pergunta
- **Tipo:** `Infra`
- **Dependências:** `T-491`, `T-492`
- **Rastreia:** `RF-514`, `RF-523`
- **Arquivos:** `app/http/rotas_coleta.py`, `app/http/serializacao.py`

**Descrição**
Só o endpoint da calculadora grava `CONFERENCIA_DA_DIVIDA`. A serialização leva enunciado, apoio e o `sistema` padrão (`PRICE`) da pergunta composta.

**Critérios de aceite**
- [ ] `POST /resposta` com `ID_PERGUNTA = B5.CALC01` ⇒ `422`, nada gravado
- [ ] `GET` da pergunta devolve `tipo: CALCULO_DIVIDA` e `sistema` padrão `PRICE`
- [ ] `proxima_pergunta_nao_respondida` pula perguntas que a composta já respondeu

**Verificação:** `VPY` com `tests/app_aluno/test_rotas_calculadora.py -k coleta`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-497` — Testar o registro e o "não sei" pela API de coleta
- **Tipo:** `Test`
- **Dependências:** `T-493`, `T-496`
- **Rastreia:** `RF-523`, `RF-526`, `AC-533`, `AC-537`
- **Arquivos:** `tests/app_aluno/test_registro_calculo_divida.py`

**Descrição**
`AC-533` (Price/SAC em três modalidades, SAC persiste ao reabrir, texto sem "do credor"); `AC-537` (`POST /resposta` com `NAO_SEI` em `B5.B03`: coleta avança, linha sem valor, pendência em "O que falta informar").

**Critérios de aceite**
- [ ] `avanco_permitido` verdadeiro com `NAO_SEI` em saldo
- [ ] Nenhuma linha `0` gravada; pendência listada em "O que falta informar"
- [ ] SAC escolhido continua SAC ao reabrir

**Verificação:** `VPY` com o arquivo

**Status:** `[x] implementada (2026-11-04)`

---

## Entrega 4 — Costura com o motor e dívida pendente

### `T-498` — Fazer `montar_divida` ler de `resolver_divida`
- **Tipo:** `Data`
- **Dependências:** `T-486`, `T-494`
- **Rastreia:** `RF-531`, `RF-517`, `AC-542`
- **Arquivos:** `app/montagem/estado.py`

**Descrição**
Única costura com o motor (PD-07): saldo, parcela (nos dois campos de pagamento), taxa mensal normalizada e sistema vêm de `resolver_divida`. **Nenhum campo de prazo** chega ao motor.

**Critérios de aceite**
- [x] Dívida com campo calculado entrega o valor calculado ao motor
- [x] `Divida` não ganha campo; `engine/` sem diff
- [x] Dívida só com respostas antigas (sem `CALC01`) monta como antes

**Verificação:** `VPY` com `tests/app_aluno/test_montagem_divida_calculada.py`, `tests/app_aluno/estatica/test_engine_congelado.py`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-499` — Manter a dívida pendente fora do estado e marcar o inventário incompleto
- **Tipo:** `Data`
- **Dependências:** `T-488`, `T-498`
- **Rastreia:** `RF-527`, `EC-74`, `AC-539`, `OQ-86`
- **Arquivos:** `app/montagem/estado.py`, `app/http/rotas_calculo.py`

**Descrição**
`_montar_dividas_do_caso` omite pendentes; `montar_estado_financeiro(..., dividas_pendentes=...)` força `INVENTARIO_COMPLETO = False` (PD-10); o motor rebaixa sozinho a `PROVISORIA`. Todas pendentes: `_preparar_calculo` recusa o Bloco 6 com `422` e `pendencias`, sem chamar o motor.

**Critérios de aceite**
- [x] Três dívidas, uma pendente ⇒ estado com duas, `INVENTARIO_COMPLETO = False`, `ORDEM_STATUS = PROVISORIA`
- [x] Pendente ausente de `ORDEM_QUITACAO`
- [x] Todas pendentes ⇒ `422` com `pendencias` e motor não chamado

**Verificação:** `VPY` com `tests/app_aluno/test_montagem_divida_calculada.py -k pendente`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-500` — Passar `resolvidas` a `pendencias_de_homologacao` e às três chamadas
- **Tipo:** `Data`
- **Dependências:** `T-488`
- **Rastreia:** `RF-526`, `AC-538`, `PD-11`
- **Arquivos:** `app/revisao/comprovacao.py`, `app/http/rotas_revisao.py`, `app/http/rotas_inicio.py`, `app/revisao/fila.py`

**Descrição**
"Não sei" em campo **calculado** deixa de contar `AUSENTE`; em campo pendente continua contando (guarda `RF-93` mantida, `OQ-89`).

**Critérios de aceite**
- [x] Campo calculado não é `AUSENTE`; campo pendente é `AUSENTE`
- [x] Os três pontos de chamada passam `resolvidas`; sem esquecer nenhum (busca por todos os chamadores)
- [x] Comportamento de casos sem calculadora inalterado

**Verificação:** `VPY` com `tests/app_aluno/test_premissas_da_divida.py -k homologacao`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-501` — Testar a costura de montagem, hashes congelados e `RF-479`
- **Tipo:** `Test`
- **Dependências:** `T-498`, `T-499`, `T-500`
- **Rastreia:** `RF-479`, `RF-531`, `RF-527`, `AC-539`, `AC-542`, `EC-74`
- **Arquivos:** `tests/app_aluno/test_montagem_divida_calculada.py`, `tests/app_aluno/estatica/test_engine_congelado.py` (sem edição)

**Descrição**
Estado entregue ao motor com respostas calculadas (dois campos de pagamento iguais, sem prazo); caracterização do comportamento de pendente (congela o que o risco da tabela 10 descreve); regressão de `PARCELA_MAIOR_QUE_O_SALDO` sem bloqueio e dos gabaritos `GAB-A/B/C` e `GAB-01` a `GAB-05`.

**Critérios de aceite**
- [x] Hashes de `hashes_congelados.json` não mudam
- [x] `PARCELA_MAIOR_QUE_O_SALDO` segue aviso sem bloqueio
- [x] GAB-A/B/C e GAB-01 a 05 verdes

**Verificação:** `VPY` completo

**Status:** `[x] implementada (2026-11-04)`

---

## Entrega 5 — Endpoints da calculadora

### `T-502` — Criar `calculadora.yaml` com a estrutura e a frase aprovada do `RF-519`
- **Tipo:** `Docs`
- **Dependências:** `nenhuma`
- **Rastreia:** `RF-519`, `RF-518`, `AC-528`
- **Arquivos:** `app/montagem/textos/calculadora.yaml`, `tests/app_aluno/estatica/` (teste de conteúdo no código)

**Descrição**
Estrutura de chaves por código de erro, estado, rótulo de marca. **Só** a frase do `RF-519` está aprovada ("Nas condições informadas, essa parcela não reduz o saldo devedor. Revise os dados ou simule outra condição."); as demais chaves nascem com marcador de texto provisório a aprovar em `T-507`.

**Critérios de aceite**
- [x] A frase do `RF-519` idêntica à da spec, caractere por caractere
- [x] Cada `CODIGO_ERRO_DE_ENTRADA`/`CODIGO_ERRO_DE_CALCULO` tem chave
- [x] `test_sem_conteudo_de_questionario_no_codigo` verde (mensagem só em YAML)

**Verificação:** `VPY` com `tests/app_aluno/estatica/`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-503` — Implementar `POST /caso/{CASO_ID}/calculadora/previa`
- **Tipo:** `Infra`
- **Dependências:** `T-486`, `T-487`, `T-479`, `T-502`
- **Rastreia:** `RF-519`, `RF-524`, `RF-525`, `RF-529`, `RF-530`, `AC-529`, `EC-77`
- **Arquivos:** `app/http/rotas_calculadora.py`, `app/http/aplicacao.py`

**Descrição**
Corpo Pydantic (`CorpoDaCalculadora`; `null`/`""` = desconhecido). Sem estado e sem gravação (PD-09). Servidor formata com `formatar_dinheiro_br`/`formatar_taxa_br`. Erro de negócio é `200` com `estado: ERRO` e `valores` vazio. Rota síncrona, `exigir_caso_da_sessao`. Resumo (prazo, 1ª parcela, último pagamento, total de juros) só aqui.

**Critérios de aceite**
- [x] `400` corpo malformado, `401/403` sessão/isolamento, `503` falha interna
- [x] Sucesso seguido de erro devolve `valores` vazio e a frase do `RF-519`
- [x] Nenhuma linha gravada em `respostas` (contagem antes = depois)
- [x] Total de juros e cronograma ausentes de qualquer outra rota
- [x] Quatro valores incompatíveis ⇒ `INCOMPATIVEL` com `teorico` e `alternativas`

**Verificação:** `VPY` com `tests/app_aluno/test_rotas_calculadora.py -k previa`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-504` — Implementar `POST /caso/{CASO_ID}/divida/{item_id}/calculadora/confirmar`
- **Tipo:** `Infra`
- **Dependências:** `T-503`, `T-496`, `T-494`
- **Rastreia:** `RF-518`, `RF-520`, `RF-523`, `RF-525`, `RF-526`, `AC-530`, `EC-77`
- **Arquivos:** `app/http/rotas_calculadora.py`

**Descrição**
Valida tudo antes de gravar; grava `SALDO_DEVEDOR_ATUAL`, `PARCELA_CONTRATUAL`, `PERIODICIDADE_TAXA_DIVIDA`, `TAXA_DIVIDA`, `PRAZO_RESTANTE_MESES`, `SISTEMA_AMORTIZACAO`, `INFORMACAO_A_RECALCULAR` e, por último, `CONFERENCIA_DA_DIVIDA = CONFIRMADA`. Desconhecido ou "a calcular" grava `NAO_SEI`, nunca `0`; valor digitado nunca é alterado. Devolve `{ID_PERGUNTA, proxima, avisos}`.

**Critérios de aceite**
- [x] `422` com entrada inválida e **nada** gravado; `409` coleta não editável; `404` item inexistente; `503` com `_MENSAGEM_FALHA_SALVAR`
- [x] Parcela digitada `528,71` continua `528,71` após confirmar
- [x] Repetir a confirmação é idempotente
- [x] Falha no meio não deixa `CONFERENCIA_DA_DIVIDA` gravada
- [x] Campo escolhido em `recalcular` grava `NAO_SEI` na variável e a escolha em `INFORMACAO_A_RECALCULAR`

**Verificação:** `VPY` com `tests/app_aluno/test_rotas_calculadora.py -k confirmar`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-505` — Registrar os três eventos de observabilidade sem dado do aluno
- **Tipo:** `Infra`
- **Dependências:** `T-503`
- **Rastreia:** `RF-516`, `RF-519`, NFR Observabilidade e LGPD (PD-15)
- **Arquivos:** `app/http/rotas_calculadora.py` ou `app/montagem/calculo_divida.py` (só a emissão pelo chamador, módulo continua puro)

**Descrição**
`CALCULADORA_SEM_CONVERGENCIA`, `CALCULADORA_TETO_DE_TAXA`, `CALCULADORA_NAO_REDUZ_SALDO` via `logging` estruturado.

**Critérios de aceite**
- [x] Cada falha emite exatamente o evento correspondente
- [x] `caplog` prova que nenhum registro contém saldo, parcela, taxa, prazo ou `CASO_ID`

**Verificação:** `VPY` com `tests/app_aluno/test_rotas_calculadora.py -k eventos`

**Status:** `[x] implementada (2026-11-04)`

---

### `T-506` — Testar as rotas da calculadora
- **Tipo:** `Test`
- **Dependências:** `T-503`, `T-504`, `T-505`
- **Rastreia:** `RF-519`, `RF-525`, `RF-530`, `AC-525`, `AC-528`, `AC-529`, `AC-530`, `AC-541`, `EC-77`
- **Arquivos:** `tests/app_aluno/test_rotas_calculadora.py`

**Descrição**
Cobre prévia e confirmar ponta a ponta, isolamento entre casos, frase do `RF-519` comparada com o YAML, formato brasileiro na saída e idempotência.

**Critérios de aceite**
- [x] Todos os códigos de resposta da tabela 4.5 exercitados
- [x] Caso de outro aluno ⇒ `403`/`404`
- [x] Frase do `RF-519` literal igual ao YAML

**Verificação:** `VPY` com o arquivo

**Status:** `[x] implementada (2026-11-04)`

---

## Entrega 6 — Textos (BLOQUEADAS até aprovação do produto)

### `T-507` — Preencher os textos da calculadora em `calculadora.yaml`
- **Tipo:** `Docs`
- **Dependências:** `T-502`
- **Rastreia:** `RF-518`, `RF-524`, `RF-525`, `RF-526`, `RF-528`, `AC-37`
- **Arquivos:** `app/montagem/textos/calculadora.yaml`
- **Bloqueada por:** aprovação do produto dos textos (erros por campo, incompatibilidade, escolha de recálculo, rótulos de marca, "Faltam dados para calcular", "Não foi possível calcular agora"). Só a frase do `RF-519` está aprovada.

**Descrição**
Trocar os marcadores provisórios pelo texto aprovado. Sem texto novo escrito por conta própria.

**Critérios de aceite**
- [ ] Todas as chaves com texto aprovado e sem marcador provisório
- [ ] Sinal de incompatibilidade é texto, não só cor

**Verificação:** `VPY` com `tests/app_aluno/estatica/`

**Status:** `[ ] BLOQUEADA`

---

### `T-508` — Preencher os textos canônicos do relatório (dívida pendente, plano parcial)
- **Tipo:** `Docs`
- **Dependências:** `nenhuma`
- **Rastreia:** `RF-527`, `AC-539`, `AC-37`
- **Arquivos:** `report/templates/plano/textos-canonicos.yaml`
- **Bloqueada por:** aprovação do produto dos textos do aviso nominal e da marca "plano parcial".

**Descrição**
Chaves novas com o texto aprovado. Pode nascer com o aviso nominal "Dívida X: falta informar saldo/parcela/taxa".

**Critérios de aceite**
- [ ] Chaves de dívida pendente e plano parcial presentes e aprovadas
- [ ] Nenhum texto fixo no código Python

**Verificação:** `VPY` com `tests/app_aluno/estatica/ tests/app_aluno/test_pendencias_do_relatorio.py`

**Status:** `[ ] BLOQUEADA`

---

### `T-509` — Redigir os enunciados das perguntas novas e alteradas
- **Tipo:** `Docs`
- **Dependências:** `T-492`, `T-493`
- **Rastreia:** `RF-523`, `RF-526`, `OQ-85`, `AC-533`
- **Arquivos:** `collection/registros/bloco-05.yaml`
- **Bloqueada por:** aprovação do produto da redação de `B5.CALC01`, `B5.C02B`, `B5.C02A` (sem "financiamento" nem "do credor") e da opção "Não sei a taxa" de `B5.D06`.

**Descrição**
Substituir os enunciados provisórios de `T-492`/`T-493`. A redação de `B5.C02` como "pagamento habitual" é da Fase 2 (`T-532`).

**Critérios de aceite**
- [ ] Enunciados aprovados; nenhuma referência ao curso fora de `docs/curso-ssd/`
- [ ] `B5.C02A` não afirma que a modalidade é a do credor

**Verificação:** `VPY` com `tests/app_aluno/test_carga.py tests/app_aluno/test_registro_calculo_divida.py`

**Status:** `[ ] BLOQUEADA`

---

## Entrega 7 — Frontend

### `T-510` — Acrescentar tipos e chamadas de API da calculadora
- **Tipo:** `UI`
- **Dependências:** `T-503`, `T-504`
- **Rastreia:** `RF-519`, `RF-525`
- **Arquivos:** `frontend/src/tipos.ts`, `frontend/src/services/api.ts`

**Descrição**
`TipoResposta` + `'CALCULO_DIVIDA'`, `CampoDaDivida`, `MarcaDoValor`, `CorpoDaCalculadora`, `ValorCalculado`, `RespostaDaPrevia`, `preverCalculadora` (aceita `AbortSignal`) e `confirmarCalculadora`.

**Critérios de aceite**
- [ ] Tipos idênticos ao contrato 4.5
- [ ] `typecheck` sem erro; nenhuma conta no front

**Verificação:** `VFRONT`

**Status:** `[x] implementada (2026-11-05)`

---

### `T-511` — Criar `CalculadoraDaDivida.tsx` (campos, "não sei", sistema e prévia)
- **Tipo:** `UI`
- **Dependências:** `T-510`
- **Rastreia:** `RF-514`, `RF-519`, `RF-522`, `RF-523`, `RF-526`, `RF-529`, `RF-530`, `AC-529`, `AC-532`
- **Arquivos:** `frontend/src/componentes/CalculadoraDaDivida.tsx`

**Descrição**
Quatro campos com máscaras existentes (`mascaras.ts`, taxa em 2 casas), "não sei" por campo, Price/SAC (Price pré-selecionado), periodicidade mensal/anual. A cada edição limpa o resultado **na hora**, espera ~400 ms, cancela a requisição anterior (`AbortController`) e descarta resposta fora de ordem. Mostra o que o servidor devolve; campo "a calcular" vai como `null` (risco 9).

**Critérios de aceite**
- [ ] Erro depois de sucesso não deixa o valor antigo na tela
- [ ] Total de juros aparece só no resumo da prévia
- [ ] Mensagem em `role="alert"`, resultado em `role="status"`
- [ ] Rótulos por `<label>`/`<fieldset>`; sem biblioteca de formulário nova

**Verificação:** `VFRONT`

**Status:** `[x] implementada (2026-11-05)`

---

### `T-512` — Implementar a incompatibilidade e a escolha de recálculo no componente
- **Tipo:** `UI`
- **Dependências:** `T-511`
- **Rastreia:** `RF-524`, `RF-525`, `AC-534`, `AC-536`
- **Arquivos:** `frontend/src/componentes/CalculadoraDaDivida.tsx`

**Descrição**
Mostra o valor teórico, sinal de incompatibilidade em texto e a escolha "qual informação recalcular" (grupo de rádio) navegável por teclado, incluindo "manter os originais".

**Critérios de aceite**
- [ ] Escolha operável só com teclado, foco visível
- [ ] Sinalização não depende só de cor
- [ ] Sem escolha, os originais e a sinalização permanecem

**Verificação:** `VFRONT`

**Status:** `[x] implementada (2026-11-05)`

---

### `T-513` — Ligar a calculadora em `TelaPergunta` e tratar a reabertura da ficha
- **Tipo:** `UI`
- **Dependências:** `T-512`, `T-496`
- **Rastreia:** `RF-523`, `RF-526`, `EC-70`, `EC-71`
- **Arquivos:** `frontend/src/telas/TelaPergunta.tsx`

**Descrição**
Ramo para `tipo === 'CALCULO_DIVIDA'`. Ao reabrir, preenche com o que foi gravado (`NAO_SEI` vira campo vazio "não sei"), preserva SAC se escolhido e **nunca reenvia o valor calculado exibido** como se fosse digitado. Troca de sistema ou edição apaga o resultado anterior.

**Critérios de aceite**
- [ ] SAC escolhido continua SAC ao reabrir
- [ ] Campo que o sistema calculou volta como "a calcular", não como digitado
- [ ] Confirmar leva ao `proxima` devolvido pela API

**Verificação:** `VFRONT`

**Status:** `[x] implementada (2026-11-05)`

---

### `T-514` — Mostrar a marca por valor em `PartesDaConferencia`
- **Tipo:** `UI`
- **Dependências:** `T-519`
- **Rastreia:** `RF-528`, `RF-529`, `AC-540`
- **Arquivos:** `frontend/src/componentes/revisao/PartesDaConferencia.tsx`, `frontend/src/tipos.ts`

**Descrição**
`Celula` ganha o chip "calculado"/"estimado" a partir de `estado_inputs.dividas[].campos`. Sem fórmula, juros ou intermediário.

**Critérios de aceite**
- [ ] Célula sem marca renderiza como hoje
- [ ] Chip em texto acessível, não só cor
- [ ] Nenhum campo de fórmula ou total de juros no tipo recebido

**Verificação:** `VFRONT`

**Status:** `[x] implementada (2026-11-05)` — chip por `marca` em `CampoDeEntrada`; contrato confirmado com `T-519`: chave `marca` (`calculado`/`estimado`) presente só no campo marcado

---

### `T-515` — Testar o componente (vitest)
- **Tipo:** `Test`
- **Dependências:** `T-512`, `T-513`, `T-514`
- **Rastreia:** `RF-519`, `RF-525`, `RF-526`, `AC-529`, `AC-536`, `AC-541`
- **Arquivos:** `frontend/tests/unit/componentes/CalculadoraDaDivida.test.tsx`, `frontend/tests/unit/componentes/PartesDaConferencia.test.tsx`

**Descrição**
Limpa o resultado em erro, cancela a requisição anterior, descarta resposta fora de ordem, não calcula nada, `role="status"`/`role="alert"`, escolha de recálculo por teclado, `mascaras` inalterado.

**Critérios de aceite**
- [ ] `AC-529`: 24 antigo some quando a troca gera erro
- [ ] Nenhuma operação aritmética sobre valores no componente (Lei nº 3)
- [ ] Mesmas 8 falhas preexistentes do `vitest`, nenhuma nova

**Verificação:** `VFRONT`

**Status:** `[x] implementada (2026-11-05)` — testes do chip em `PartesDaConferencia.test.tsx` usam o contrato provisório de `T-514`; acrescentado `TelaPerguntaCalculadora.test.tsx` (`T-513`)

---

### `T-516` — Escrever o e2e da ficha com "não sei" e da incompatibilidade
- **Tipo:** `Test`
- **Dependências:** `T-513`, `T-509`
- **Rastreia:** `RF-525`, `RF-526`, `AC-536`, `AC-538`
- **Arquivos:** `frontend/tests/e2e/calculadora-da-divida.spec.ts`

**Descrição**
Três dados + "não sei" na taxa até a confirmação; quatro valores incompatíveis com escolha de recálculo. Depende dos textos aprovados (`T-509`) para asserções de texto.

**Critérios de aceite**
- [x] Taxa calculada aparece e é confirmada; resposta gravada como `NAO_SEI`, não `0`
- [x] Incompatibilidade: escolher "parcela" mostra `R$ 528,72`

**Verificação:** `npm --prefix frontend run test:e2e`

**Status:** `[x] implementada (2026-11-05)` — `frontend/tests/e2e/calculadora-da-divida.spec.ts`, 3 cenários × desktop e 360px (6 passam, rede interceptada). Não afirma texto de redação (`T-509` segue bloqueada); "gravada como `NAO_SEI`" é provado no servidor (`test_rotas_calculadora.py::test_ac537_*`), o e2e prova que a taxa vai `null`

---

## Entrega 8 — Plano parcial, aviso e revisor

### `T-517` — Levar dívidas pendentes e plano parcial ao vocabulário do caso
- **Tipo:** `Data`
- **Dependências:** `T-499`
- **Rastreia:** `RF-527`, `AC-539`
- **Arquivos:** `report/plano.py`, `app/http/serializacao_plano.py`

**Descrição**
`VocabularioDoCaso` ganha `dividas_pendentes` (credor + campos que faltam) e `plano_parcial`, ambos derivados de `dividas_pendentes`. `_pendencias` lista o dado que falta. Sem aritmética sobre snapshot.

**Critérios de aceite**
- [ ] Caso com pendente ⇒ `plano_parcial = True` e dívida nomeada com o campo faltante
- [ ] Caso sem pendente inalterado
- [ ] `test_sem_aritmetica_sobre_snapshot` verde

**Verificação:** `VPY` com `tests/app_aluno/test_pendencias_do_relatorio.py`

**Status:** `[x] implementada (2026-11-05)` — `VocabularioDoCaso.dividas_pendentes` (DIVIDA_ID, campos do estado) e `plano_parcial` (propriedade), alimentados por `vocabulario_do_caso(..., premissas)`; `_pendencias` lista a dívida pendente pelo credor com o dado que falta. Ligado só na rota do revisor; aluno/PDF ligam em `T-518`. Testes: `test_rotas_revisao_marcas.py`

---

### `T-518` — Exibir o aviso nominal e a marca "plano parcial" no relatório e na tela
- **Tipo:** `UI`
- **Dependências:** `T-517`, `T-508`
- **Rastreia:** `RF-527`, `AC-539`
- **Arquivos:** `report/plano.py`, `report/templates/plano/`, `frontend/src/componentes/PlanoDoAluno.tsx`, `frontend/src/componentes/PlanoDoDeficitario.tsx`

**Descrição**
Aviso "dívida X, falta Y" e a marca de plano parcial no PDF/HTML do relatório e na tela. Usa só as chaves aprovadas de `T-508`.

**Critérios de aceite**
- [ ] Dívida pendente não aparece na tabela da ordem
- [ ] Aviso cita a dívida e o dado que falta; plano marcado como parcial nas duas saídas
- [ ] Todas pendentes (`EC-74`): mensagem "não há dívida com dados suficientes", sem plano

**Verificação:** `VPY` com `tests/app_aluno/test_pendencias_do_relatorio.py` e `VFRONT`

**Status:** `[ ] BLOQUEADA` (por dependência de `T-508`)

---

### `T-519` — Entregar ao revisor só a marca por campo da dívida
- **Tipo:** `Data`
- **Dependências:** `T-486`
- **Rastreia:** `RF-528`, `RF-529`, `OQ-87`, `AC-540`
- **Arquivos:** `app/http/serializacao_plano.py`, `app/http/rotas_revisao.py`

**Descrição**
`serializar_estado_inputs` leva `dividas[].campos` com `calculado`/`estimado` (hipótese aparece como `estimado`). Fórmula, total de juros e intermediários **não** saem (PD-14).

**Critérios de aceite**
- [ ] Marcas presentes por campo; nenhum campo com fórmula, juros ou cronograma no payload
- [ ] Campo digitado sem marca de cálculo

**Verificação:** `VPY` com `tests/app_aluno/test_premissas_da_divida.py -k revisor`

**Status:** `[x] implementada (2026-11-05)` — `ContextoCampo.marca` + `serializar_estado_inputs` (chave só quando há marca); `premissas_da_ficha` em `premissas.py`; arquivos reais: `report/plano.py`, `app/http/serializacao_plano.py`, `app/http/rotas_api_plano.py` (o endpoint do revisor mora lá, não em `rotas_revisao.py`). Prazo não tem marca: `Divida` do motor não o carrega

---

### `T-520` — Liberar ao aluno o plano parcial (exceção à guarda `RF-93`)
- **Tipo:** `Data`
- **Dependências:** `T-500`, `T-517`
- **Rastreia:** `RF-93`, `RF-526`, `RF-527`, `OQ-89`, `US-408`
- **Arquivos:** `app/revisao/comprovacao.py`, `app/casos/` (liberação), testes
- **Bloqueada por:** resposta ao `OQ-89` do plano. Hoje `RF-93` conta "não sei" em saldo, parcela ou taxa como `AUSENTE` e bloqueia a liberação (`ErroHomologacaoBloqueada`); o plano parcial só chega ao revisor, não ao aluno. Decidir: manter (nada a fazer, `US-408` fica parcial) ou abrir exceção por um predicado (dívida pendente com aviso nominal).

**Descrição**
Se o especialista aprovar a exceção, ajustar o predicado de `pendencias_de_homologacao` para não bloquear a liberação por dívida pendente já fora do plano e avisada. Se mantiver `RF-93`, a tarefa fecha como "sem mudança" e registra a decisão aqui.

**Critérios de aceite**
- [ ] Decisão registrada na tarefa (data e quem decidiu)
- [ ] Conforme a decisão: liberação com pendente é permitida e coberta por teste, ou continua bloqueada e coberta por teste
- [ ] Demais campos `AUSENTE` continuam bloqueando

**Verificação:** `VPY` completo

**Status:** `[ ] BLOQUEADA`

---

### `T-521` — Testar relatório, aviso e visão do revisor
- **Tipo:** `Test`
- **Dependências:** `T-518`, `T-519`
- **Rastreia:** `RF-527`, `RF-528`, `RF-529`, `AC-539`, `AC-540`, `EC-74`
- **Arquivos:** `tests/app_aluno/test_pendencias_do_relatorio.py`, `tests/app_aluno/test_rotas_revisao_marcas.py`

**Descrição**
Três dívidas, uma pendente: fora da ordem, aviso nominal, "plano parcial"; revisor recebe apenas `calculado`/`estimado`; todas pendentes ⇒ `422`, motor não chamado.

**Critérios de aceite**
- [ ] `AC-539` e `AC-540` cobertos
- [ ] `EC-74`: `422` e nenhuma chamada ao motor (espionagem)

**Verificação:** `VPY` com os dois arquivos

**Status:** `[ ] pendente` — parcial: `AC-540`/`AC-539` (nível de contexto) e `EC-74` (já em `test_montagem_divida_calculada.py`) cobertos; faltam as asserções do aviso/marca renderizados, que dependem de `T-518`

---

### `T-522` — Fechar a Fase 1 com a regressão completa
- **Tipo:** `Test`
- **Dependências:** `T-481`, `T-482`, `T-483`, `T-484`, `T-485`, `T-489`, `T-490`, `T-495`, `T-497`, `T-501`, `T-506`, `T-515`, `T-516`, `T-521`
- **Rastreia:** `RF-514` a `RF-531`, `AC-542`
- **Arquivos:** `specs/calculo-de-divida.spec.md` e `plans/calculo-de-divida.plan.md` (status), este backlog

**Descrição**
Rodar tudo, comparar com o `HEAD`, atualizar status dos artefatos. `T-507`, `T-508`, `T-509` e `T-520` bloqueadas impedem **liberar** a Fase 1; a regressão técnica pode ser rodada antes, e esta tarefa só fecha quando elas estiverem resolvidas.

**Critérios de aceite**
- [ ] `ruff`, `mypy --strict`, `pytest -q` e `vitest` sem falha nova em relação ao `HEAD`
- [ ] Hashes de `engine/` intactos (`git diff --stat engine/` vazio)
- [ ] Tabela de cobertura abaixo sem requisito órfão

**Verificação:** `VPY` completo e `VFRONT`

**Status:** `[ ] pendente`

---

# FASE 2 — Parcela estimada de 24 meses (`RF-532` a `RF-537`) — nível de arquitetura

> Toda a Fase 2 depende da Fase 1 concluída e do resultado do spike. Antes de detalhar em tarefas pequenas, rever este bloco com o relatório do spike. Premissas a confirmar: `OQ-73` a `OQ-76` e `OQ-84`.

### `T-523` — Executar o spike do `OQ-83` (mapeamento nos dois campos de pagamento)
- **Tipo:** `Test`
- **Dependências:** `T-522`
- **Rastreia:** `RF-537`, `RF-540`, `AC-549`, `OQ-83`
- **Arquivos:** `tests/app_aluno/test_spike_pagamentos_da_divida.py`, relatório curto em `plans/` (seção 11 do plano)
- **Bloqueada por:** decisão do especialista sobre `engine/` e a abertura da Fase 2; e, se o spike refutar o mapeamento da spec (opção C do plano 1.2), a tarefa devolve a decisão ao especialista antes de qualquer outra da fase.

**Descrição**
Teste de caracterização, **sem tocar `engine/`**: estado com duas dívidas (uma com habitual informado, uma sem parcela nem prazo); observa como `PARCELA_CONTRATUAL` e `PAGAMENTO_MENSAL_EFETIVO` se propagam (`FALTA_DE_JUROS`, `RESULTADO_CAIXA_OBSERVADO`, simulação, ordem) e responde à pergunta do `RF-535` (habitual ausente nem `DESCONHECIDO` nem `0`).

**Critérios de aceite**
- [x] Tabela caso × campo × resultado do mês × alerta registrada
- [x] Escolha do mapeamento: (A) o da spec, com ressalvas (plano 11.1)
- [x] Teste fica no repositório e `git diff engine/` vazio

**Verificação:** `VPY` com `tests/app_aluno/test_spike_pagamentos_da_divida.py`

**Status:** `[x] implementada (2026-11-05)` — mapeamento (A) com ressalvas (a) a (d) do plano 11.1, para decisão do especialista na `T-524`

---

### `T-524` — Registrar a decisão do mapeamento e ajustar o plano da Fase 2
- **Tipo:** `Docs`
- **Dependências:** `T-523`
- **Rastreia:** `RF-535`, `RF-537`, `OQ-83`
- **Arquivos:** `plans/calculo-de-divida.plan.md`, este backlog
- **Bloqueada por:** ~~`T-523`~~ e a confirmação do especialista (execução autorizada pelo usuário sobre a hipótese).

**Descrição**
Transformar o resultado do spike em decisão (`PD-17`), detalhar as tarefas `T-525` a `T-533` conforme o mapeamento escolhido e reavaliar `RF-535`.

**Critérios de aceite**
- [x] Decisão registrada com data
- [x] Tarefas seguintes revistas sem renumeração

**Verificação:** revisão do especialista (sem comando)

**Status:** `[x] registrada (2026-11-05)` — **HIPÓTESE ADOTADA, aguardando confirmação do especialista (Marcelo); não é decisão aprovada.** Mapeamento (A) com as ressalvas (a) a (d), plano seção 11.2 e `PD-17`. A ressalva (b) fica isolada em `prioridade.limitar_capacidade_ao_caixa`. Verificação por revisão do especialista continua pendente.

---

### `T-525` — Perguntar o pagamento mínimo (`B5.C02C`) e subir para `1.5.0`
- **Tipo:** `Data`
- **Dependências:** `T-524`
- **Rastreia:** `RF-533`, `OQ-85`, `AC-545`
- **Arquivos:** `collection/registros/bloco-05.yaml` (e demais blocos só na versão), testes de carga
- **Bloqueada por:** `T-524`.

**Descrição**
`B5.C02C` (`MOEDA`, "não sei" permitido, `PAGAMENTO_MINIMO_DIVIDA`) em toda dívida; `QUESTIONARIO_VERSION 1.5.0` nos oito arquivos; suites que citam `1.4.0` atualizadas.

**Critérios de aceite**
- [x] Toda dívida pergunta mínimo e habitual
- [x] Nenhum `1.4.0` residual

**Verificação:** `VPY` completo

**Status:** `[x] implementada (2026-11-05)` — `B5.C02C` depois de `B5.C02B`, versão `1.5.0` nos sete arquivos que declaram versão; enunciado `[PROVISORIO T-532]` — **testes adiados para a fase final** (critérios de teste não marcados; testes já escritos nesta fase ficam onde estão)

---

### `T-526` — Derivar a parcela estimada em `resolver_divida`
- **Tipo:** `Data`
- **Dependências:** `T-524`, `T-486`
- **Rastreia:** `RF-532`, `OQ-73`, `OQ-76`, `AC-543`, `AC-544`
- **Arquivos:** `app/montagem/premissas.py`
- **Bloqueada por:** `T-524`.

**Descrição**
Saldo e taxa conhecidos, sem parcela e sem prazo (ou habitual `0`/ausente e sem prazo) ⇒ `parcela_estimada` com `n = 24` (`PRAZO_BASE_ESTIMATIVA_MESES`) e o sistema da dívida; marca `ESTIMADO`, hipótese `PRAZO_24_MESES`. Prazo contratual e habitual `> 0` prevalecem. Estreita a tabela-verdade (saldo e taxa sem P e sem N deixam de ser `PENDENTE`).

**Critérios de aceite**
- [x] `R$ 10.000`, 2% a.m., sem parcela nem prazo ⇒ `528,72` `ESTIMADO`
- [x] Prazo 36 ⇒ base 36; habitual `600` ⇒ base `600`; habitual `0` ⇒ 24
- [x] Vale igual em todas as modalidades

**Verificação:** `VPY` com `tests/app_aluno/test_premissas_da_divida.py -k estimada`

**Status:** `[x] implementada (2026-11-05)` — testes em `test_premissas_da_divida.py` (`-k estimada`); habitual `0,00` com prazo informado cai na incompatibilidade da Fase 1 (`OQ-92`), sem estimar — **testes adiados para a fase final** (critérios de teste não marcados; testes já escritos nesta fase ficam onde estão)

---

### `T-527` — Eleger a dívida prioritária em duas passagens do motor
- **Tipo:** `Data`
- **Dependências:** `T-524`, `T-526`
- **Rastreia:** `RF-534`, `OQ-75`, `EC-75`, `AC-546`, `PD-16`
- **Arquivos:** `app/montagem/prioridade.py`
- **Bloqueada por:** `T-524`.

**Descrição**
Passo 1: estado com todas as estimáveis no mínimo, `engine.motor.calcular_plano` em processo sem snapshot, lê a dívida-alvo. Passo 2: fixa a parcela de 24 meses nela. Até 3 passagens; sem estabilizar, fica no passo 1 e marca `hipótese`. Dívida não prioritária sem mínimo e sem habitual: `PENDENTE` (`OQ-84`).

**Critérios de aceite**
- [x] Só a dívida-alvo recebe a parcela de 24 meses; as outras pagam o mínimo
- [x] Troca de prioritária migra a parcela e as marcas (`EC-75`)
- [x] Empate oscilante termina em ≤ 3 passagens

**Verificação:** `VPY` com `tests/app_aluno/test_prioridade.py`

**Status:** `[x] implementada (2026-11-05)` — `app/montagem/prioridade.py`; testes em `tests/app_aluno/test_prioridade.py` — **testes adiados para a fase final** (critérios de teste não marcados; testes já escritos nesta fase ficam onde estão)

---

### `T-528` — Adaptar o executor e a barra de progresso a mais de uma passagem
- **Tipo:** `Infra`
- **Dependências:** `T-527`
- **Rastreia:** `RF-534`, `PD-16`
- **Arquivos:** `app/motor/executor.py`, `app/http/rotas_calculo.py`, `frontend/src/telas/TelaCalculando.tsx`
- **Bloqueada por:** `T-524`.

**Critérios de aceite**
- [ ] Progresso coerente com 1 a 3 passagens
- [x] Falha na segunda passagem cai para uma passagem e marca `hipótese`

**Verificação:** `VPY` completo e `VFRONT`

**Status:** `[x] implementada (2026-11-05)` — as passagens rodam em segundo plano com o caso em `CALCULANDO` (o progresso é o mesmo para 1 a 3 passagens); `TelaCalculando` não mudou (spinner sem percentual) — **testes adiados para a fase final** (critérios de teste não marcados; testes já escritos nesta fase ficam onde estão)

---

### `T-529` — Garantir o alerta de dívida que cresce com o habitual (`RF-535`)
- **Tipo:** `Data`
- **Dependências:** `T-524`, `T-526`
- **Rastreia:** `RF-535`, `EC-73`, `AC-547`
- **Arquivos:** `app/montagem/estado.py`, `app/montagem/premissas.py`
- **Bloqueada por:** `T-524` (o spike decide se basta um valor derivado na montagem ou se exige decisão sobre `engine/`).

**Critérios de aceite**
- [x] Juros `200`, habitual `150` ⇒ falta `50` mesmo com parcela estimada `528,72`
- [x] Habitual `0`/ausente ⇒ falta `200`
- [x] `git diff engine/` vazio

**Verificação:** `VPY` com `tests/app_aluno/test_montagem_divida_calculada.py -k crescimento`

**Status:** `[x] implementada (2026-11-05)` — sem tocar `engine/`: habitual ausente vira `0` no devido; testes `-k crescimento` em `test_montagem_divida_calculada.py` e `test_prioridade.py` — **testes adiados para a fase final** (critérios de teste não marcados; testes já escritos nesta fase ficam onde estão)

---

### `T-530` — Avisar a inviabilidade sem trocar o pagamento do aluno
- **Tipo:** `Data`
- **Dependências:** `T-524`, `T-526`
- **Rastreia:** `RF-536`, `OQ-74`, `AC-548`
- **Arquivos:** `app/montagem/premissas.py`, `report/plano.py`
- **Bloqueada por:** `T-524` e texto aprovado (`T-532`).

**Critérios de aceite**
- [x] Habitual ≤ juros ou resultado do mês negativo ⇒ aviso de inviabilidade
- [x] Pagamento declarado permanece; texto não cita 24 meses quando há pagamento informado

**Verificação:** `VPY` com `tests/app_aluno/test_premissas_da_divida.py -k inviavel`

**Status:** `[x] implementada com texto provisório (2026-11-05)` — aviso em `report/plano.py::_avisos_de_pagamento`; testes em `tests/app_aluno/test_avisos_de_pagamento.py` (não em `test_premissas_da_divida.py -k inviavel`); texto segue `[PROVISORIO T-532]` — **testes adiados para a fase final** (critérios de teste não marcados; testes já escritos nesta fase ficam onde estão)

---

### `T-531` — Exibir a parcela estimada em linha separada e marcada
- **Tipo:** `UI`
- **Dependências:** `T-526`, `T-519`
- **Rastreia:** `RF-533`, `RF-528`, `RF-536`, `AC-545`
- **Arquivos:** `frontend/src/componentes/CalculadoraDaDivida.tsx`, `frontend/src/componentes/revisao/PartesDaConferencia.tsx`, `app/http/serializacao_plano.py`
- **Bloqueada por:** `T-524`.

**Critérios de aceite**
- [x] Estimada nunca aparece no campo digitado
- [x] Texto não cita 24 meses com prazo contratual ou habitual `> 0`
- [x] Revisor vê a marca `estimado`

**Verificação:** `VFRONT` e `VPY` com `tests/app_aluno/test_rotas_calculadora.py`

**Status:** `[x] implementada (2026-11-05)` — prévia `parcela_estimada`, linha à parte na calculadora, coluna "Pagamento do plano" com a marca no revisor — **testes adiados para a fase final** (critérios de teste não marcados; testes já escritos nesta fase ficam onde estão)

---

### `T-532` — Aprovar e preencher os textos da Fase 2
- **Tipo:** `Docs`
- **Dependências:** `T-525`
- **Rastreia:** `RF-533`, `RF-536`, `OQ-85`
- **Arquivos:** `app/montagem/textos/calculadora.yaml`, `report/templates/plano/textos-canonicos.yaml`, `collection/registros/bloco-05.yaml`
- **Bloqueada por:** aprovação do produto (redação de mínimo e habitual, hipótese de 24 meses, inviabilidade) e `T-524`.

**Critérios de aceite**
- [ ] Textos aprovados em YAML, nenhum no código

**Verificação:** `VPY` com `tests/app_aluno/estatica/`

**Status:** `[ ] PENDENTE de aprovação do produto` — textos provisórios marcados `[PROVISORIO T-532]` em `calculadora.yaml` (`estimativa`), `textos-canonicos.yaml` (`avisos`) e `bloco-05.yaml` (`B5.C02C`); nenhum aprovado. Falta também a redação nova de `B5.C02` (habitual, `OQ-85`)

---

### `T-533` — Testar a Fase 2 por AC e fechar
- **Tipo:** `Test`
- **Dependências:** `T-526`, `T-527`, `T-528`, `T-529`, `T-530`, `T-531`
- **Rastreia:** `RF-532` a `RF-537`, `AC-543` a `AC-549`
- **Arquivos:** `tests/app_aluno/test_premissas_da_divida.py`, `tests/app_aluno/test_prioridade.py`, `tests/app_aluno/test_spike_pagamentos_da_divida.py`
- **Bloqueada por:** `T-524` e dependências.

**Critérios de aceite**
- [x] `AC-543` a `AC-549` com teste nomeado; `GAB-A/B/C` e `GAB-01` a `GAB-05` verdes; hashes de `engine/` intactos

**Verificação:** `VPY` completo e `VFRONT`

**Status:** `[x] implementada (2026-11-05)` — lacunas fechadas em `test_prioridade.py` (modalidades, `AC-544`, marca `estimado` só na prioritária), `test_registro_calculo_divida.py` (sem `1.4.0` residual), `test_rotas_calculadora.py` (confirmar não grava a estimada), `test_rotas_revisao_marcas.py` (`AC-540`); o resto já estava em `test_premissas_da_divida.py`, `test_avisos_de_pagamento.py`, `test_spike_pagamentos_da_divida.py`, `test_montagem_divida_calculada.py`. Suíte: 26 falhas, todas fora desta feature

---

# FASE 3 — Cenário conservador (`RF-538` a `RF-540`) — nível de arquitetura

> Depende da Fase 1 (incompatibilidade) e do mapeamento fechado na Fase 2 (`T-524`). Premissas a confirmar: `OQ-82` e `OQ-87`.

### `T-534` — Criar o módulo puro `cenario_conservador.py`
- **Tipo:** `Data`
- **Dependências:** `T-480`, `T-524`
- **Rastreia:** `RF-538`, `OQ-82`, `EC-76`, `AC-550`
- **Arquivos:** `app/montagem/cenario_conservador.py`

**Descrição**
Candidatos = conjunto digitado + os quatro teóricos (cada um recalcula um campo pelos outros três); candidato que falha é descartado. Ordenação lexicográfica "maior primeiro": parcela, saldo, taxa, prazo, custo total (soma do `cronograma`); empate total vale o primeiro da ordem da ficha (digitado, saldo, parcela, taxa, prazo). Variáveis chamam-se `candidato`/`hipotese`, nunca `cenario` (teste estático).

**Critérios de aceite**
- [x] Cascata respeita a ordem e `EC-76`
- [ ] `test_sem_aritmetica_sobre_snapshot` verde

**Verificação:** `VPY` com `tests/app_aluno/test_cenario_conservador.py`

**Status:** `[x] concluída (implementação)` — implementado em `app/montagem/cenario_conservador.py` (cascata e `EC-76`); **testes adiados para a fase final**, critérios de aceite não marcados

---

### `T-535` — Injetar só saldo e taxa do cenário no motor
- **Tipo:** `Data`
- **Dependências:** `T-534`, `T-486`
- **Rastreia:** `RF-539`, `RF-540`, `AC-551`, `AC-552`
- **Arquivos:** `app/montagem/premissas.py`, `app/montagem/estado.py`

**Descrição**
Quando a situação é `INCOMPATIVEL` e não há escolha válida do `RF-525`, `resolver_divida` aplica o cenário: só `SALDO_DEVEDOR_ATUAL` e `TAXA_EFETIVA_MENSAL_NORMALIZADA`; pagamentos seguem o declarado; marcas `HIPOTESE` (`CENARIO_CONSERVADOR`).

**Critérios de aceite**
- [x] Parcela e prazo do cenário não alteram o plano
- [x] Resultado do mês igual em dois cenários diferentes
- [x] `git diff engine/` vazio

**Verificação:** `VPY` com `tests/app_aluno/test_cenario_conservador.py`

**Status:** `[x] concluída (implementação)` — implementado em `app/montagem/premissas.py` (`hipotese_conservadora`, marca `HIPOTESE`; `estado.py` já lê saldo e taxa de `resolver_divida`; `git diff engine/` vazio); **testes adiados para a fase final**, critérios de aceite não marcados

---

### `T-536` — Sinalizar o cenário como `hipótese` ao aluno e ao revisor
- **Tipo:** `UI`
- **Dependências:** `T-535`, `T-519`
- **Rastreia:** `RF-538`, `RF-539`, `OQ-87`, `AC-551`, `AC-553`
- **Arquivos:** `report/plano.py`, `frontend/src/componentes/`, `app/http/serializacao_plano.py`

**Descrição**
Aluno vê `hipótese` na ficha e no relatório com o texto de que só saldo e taxa foram usados; revisor vê `estimado`.

**Critérios de aceite**
- [ ] Texto explícito de que parcela e prazo do cenário não governam o plano
- [x] Revisor vê `estimado`, sem fórmula

**Verificação:** `VPY` completo e `VFRONT`

**Status:** `[x] concluída (implementação)` — implementado (prévia `hipotese_conservadora` + `CalculadoraDaDivida.tsx`, aviso em `report/plano.py`, marca `estimado` ao revisor); textos `[PROVISORIO T-537]`; **testes adiados para a fase final**, critérios de aceite não marcados

---

### `T-537` — Aprovar e preencher os textos da Fase 3
- **Tipo:** `Docs`
- **Dependências:** `T-535`
- **Rastreia:** `RF-539`, `AC-551`
- **Arquivos:** `app/montagem/textos/calculadora.yaml`, `report/templates/plano/textos-canonicos.yaml`
- **Bloqueada por:** aprovação do produto do texto do cenário conservador.

**Critérios de aceite**
- [ ] Texto aprovado em YAML

**Verificação:** `VPY` com `tests/app_aluno/estatica/`

**Status:** `[ ] BLOQUEADA`

---

### `T-538` — Testar a Fase 3 por AC e fechar
- **Tipo:** `Test`
- **Dependências:** `T-534`, `T-535`, `T-536`
- **Rastreia:** `RF-538`, `RF-539`, `RF-540`, `AC-550` a `AC-553`
- **Arquivos:** `tests/app_aluno/test_cenario_conservador.py`

**Critérios de aceite**
- [x] `AC-550` (cada nível da cascata), `AC-551`, `AC-552` (dois cenários, mesmo resultado do mês), `AC-553`
- [x] Regressão completa sem falha nova; hashes de `engine/` intactos

**Verificação:** `VPY` completo e `VFRONT`

**Status:** `[x] implementada (2026-11-05)` — `tests/app_aluno/test_cenario_conservador.py` (18 testes) + bloco `hipotese-conservadora` em `CalculadoraDaDivida.test.tsx`. O nível 5 da cascata (custo total) é função dos quatro primeiros e só aparece no desempate `EC-76` (ver relatório). `T-534` segue com `test_sem_aritmetica_sobre_snapshot` não verde por falha preexistente em `rotas_api_plano.py:164`

---

## Cobertura de requisitos

| Requisito | Tarefas |
| --------- | ------- |
| `RF-514` | `T-473`, `T-475`, `T-476`, `T-477`, `T-478`, `T-481`, `T-483`, `T-491`, `T-492`, `T-496`, `T-511` |
| `RF-515` | `T-475`, `T-476`, `T-477`, `T-478`, `T-481` |
| `RF-516` | `T-473`, `T-477`, `T-482`, `T-483`, `T-505` |
| `RF-517` | `T-474`, `T-478`, `T-479`, `T-481`, `T-483`, `T-484`, `T-498` |
| `RF-518` | `T-473`, `T-482`, `T-502`, `T-504`, `T-507` |
| `RF-519` | `T-478`, `T-482`, `T-502`, `T-503`, `T-505`, `T-506`, `T-510`, `T-511`, `T-515` |
| `RF-520` | `T-475`, `T-481`, `T-482`, `T-504` |
| `RF-521` | `T-479`, `T-481` |
| `RF-522` | `T-474`, `T-511` |
| `RF-523` | `T-491`, `T-492`, `T-493`, `T-494`, `T-495`, `T-496`, `T-497`, `T-504`, `T-509`, `T-513` |
| `RF-524` | `T-480`, `T-485`, `T-503`, `T-507`, `T-512` |
| `RF-525` | `T-487`, `T-490`, `T-503`, `T-504`, `T-507`, `T-510`, `T-512`, `T-515`, `T-516` |
| `RF-526` | `T-486`, `T-488`, `T-489`, `T-493`, `T-495`, `T-497`, `T-500`, `T-504`, `T-507`, `T-509`, `T-511`, `T-513`, `T-515`, `T-516`, `T-520` |
| `RF-527` | `T-486`, `T-488`, `T-499`, `T-501`, `T-508`, `T-517`, `T-518`, `T-520`, `T-521` |
| `RF-528` | `T-486`, `T-507`, `T-514`, `T-519`, `T-521`, `T-531` |
| `RF-529` | `T-479`, `T-503`, `T-511`, `T-514`, `T-519`, `T-521` |
| `RF-530` | `T-473`, `T-482`, `T-503`, `T-506`, `T-511` |
| `RF-531` | `T-484`, `T-486`, `T-498`, `T-501`, `T-522` |
| `RF-532` | `T-526`, `T-533` |
| `RF-533` | `T-525`, `T-531`, `T-532`, `T-533` |
| `RF-534` | `T-527`, `T-528`, `T-533` |
| `RF-535` | `T-523`, `T-524`, `T-529`, `T-533` |
| `RF-536` | `T-530`, `T-531`, `T-532`, `T-533` |
| `RF-537` | `T-523`, `T-524`, `T-533` |
| `RF-538` | `T-534`, `T-536`, `T-538` |
| `RF-539` | `T-535`, `T-536`, `T-537`, `T-538` |
| `RF-540` | `T-523`, `T-535`, `T-538` |

Requisitos sem tarefa: nenhum. Tarefas auxiliares sem `RF` próprio rastreiam para o `RF` que habilitam (`T-495` para `RF-513`/`RF-523`; `T-505` para NFR de observabilidade).

> `RF-93` (guarda de homologação) é herdado e entra só em `T-520`.
