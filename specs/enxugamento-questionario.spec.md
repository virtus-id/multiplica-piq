# Spec: enxugamento do questionário do PIQ (rascunho gerado das decisões do especialista)

> Fonte única deste documento: as decisões que o especialista registrou no formulário de revisão
> (https://claude.ai/artifact/UAkEhMLLqjzspsfmggSSav), lidas em 2026-10-14 (229 registros).
> Foram tratadas como **oficiais**, conforme orientação do responsável do produto. Observação em branco
> não é pendência. A situação de cada requisito está na própria seção e no backlog
> (`tasks/enxugamento-questionario.tasks.md`).

## 1. Overview (contexto e objetivo)

O projeto reduz o escopo da primeira entrega. O questionário tinha 267 perguntas no sistema (a spec cita 291) e
a decisão `OQ-02` de `specs/app-aluno.spec.md` fixava **coleta completa, sem recorte mínimo**. Esta spec
**reverte essa decisão** nos pontos abaixo. Isso vale como mudança de metodologia: exige nova versão da spec
canônica (§11) e do `QUESTIONARIO_VERSION` antes de qualquer código (`sdd.config.md` §6).

## 2. Resultado das decisões

| Situação | Perguntas |
|---|---|
| Saem do questionário | **166** (142 que o motor não usava, 24 que o motor usa) |
| Ficam | **87** (15 do motor confirmadas, 39 do motor sem decisão e portanto mantidas, 32 para ligar ao motor, 1 mantida sem efeito) |
| Em dúvida | **14** |
| Total | 267 |

Efeito no caso real do Guilherme: de 710 respostas para 457 (36% a menos).

## 3. Functional Requirements (requisitos)

### RF-401. Fora do escopo: coleta dirigida, confirmação do ataque e acompanhamento

**Situação (2026-10-14):** concluído (T-387, T-388, T-390), exceto `B11.01`, que segue em dúvida.
Saem por completo os Blocos 7 (proposta de renegociação, 18 perguntas) e 8 (proposta de troca, 21),
o Bloco 10 (confirmação do ataque, 2) e o Bloco 11 (acompanhamento, 11 de 12). `B11.01` ficou em dúvida, com a observação:
"Esse bloco só faz sentido se formos acompanhar o plano do aluno."
**Confirmado em 2026-10-14 (OQ-1): não há acompanhamento.** O produto passa a entregar **um plano único**, sem renegociação ou troca
dirigidas pelo motor, sem confirmação do ataque pelo aluno e sem recálculo por quitação confirmada.

### RF-409. O plano entregue é definitivo (confirmado em 2026-10-14)
Depois que o aluno recebe o plano (`PLANO_LIBERADO`), o caso não segue para coleta dirigida, confirmação do ataque nem acompanhamento, e o aluno **não pode pedir plano novo**. O especialista não quer o plano "indo e voltando". Valem as exceções que acontecem **antes** da entrega: o aluno retirar o plano da conferência para editar (`aluno_retoma_edicao`) e o revisor devolver o caso (`devolve_ao_aluno`) continuam como estão.

Decisão de implementação (OQ-1, parte final): em 2026-10-14 o fluxo foi **desligado** e, em seguida, o código das telas e das regras dos Blocos 7, 8, 10 e 11 foi apagado (T-390). Os estados `COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE` e `ACOMPANHAMENTO` ficaram no enum, sem transição, para não quebrar a leitura de casos gravados. **Superado por RF-413 (2026-10-15):** conferido que nenhum caso estava nesses estados, eles foram removidos do código (T-400). `PLANO_LIBERADO` é terminal.

### RF-402. Remover do questionário o que o motor não usa (Blocos 1 a 5)

**Situação (2026-10-14):** 87 das 89 listadas foram removidas (T-389). `B3.S03` e `B5.I01` continuam porque perguntas que ficam dependem delas (decisão pendente com o especialista).
**Situação (2026-10-15):** mais 15 removidas por decisão do produto e do especialista (T-398): `B4.04B`, `B4.05`, `B4.06`, `B4.I04`, `B4.I04A`, `B4.I05`, `B4.I05A`, `B5.C03`, `B5.C05`, `B5.C05A`, `B5.D04`, `B5.D04A`, `B5.E04`, `B5.F04` e `B11.01` (o Bloco 11 deixa de existir). Registros 113 → 98.
Remoção sem efeito no cálculo, comprovada em 4 casos reais (estado do motor idêntico). Lista:

#### Bloco 1 · Compromisso (10)

| Pergunta | ID | 
|---|---|
| Qual é a principal finalidade desse novo crédito? | B1.03 | 
| Qual? | B1.03A | 
| Qual é o valor aproximado desse novo crédito? | B1.04 | 
| Nos próximos 12 meses, você já sabe de alguma despesa relevante que terá de… | B1.06 | 
| Que despesa é essa? | B1.06A | 
| Quanto você estima que precisará pagar? | B1.06B | 
| Quando essa despesa deve acontecer? | B1.06C | 
| Hoje, você considera usar limite ou crédito disponível para alguma destas… | B1.08 | 
| Pensando principalmente nessa nova dívida ou parcelamento, qual foi o motivo… | B1.11 | 
| Existe outra pessoa cuja renda, gastos ou decisões financeiras influenciem… | B1.12 | 

#### Bloco 2 · Hábitos de controle (2)

| Pergunta | ID | 
|---|---|
| Quais formas de pagamento costumam escapar mais do seu controle? | B2.05A | 
| Em um mês típico, quanto você estima que esses gastos ou cobranças que não… | B2.08 | 

#### Bloco 3 · Renda e despesas (31)

| Pergunta | ID | 
|---|---|
| Pensando em um mês mais fraco, qual valor líquido você considera… | B3.02B | 
| Que renda é essa? | B3.03A | 
| Descreva essa renda. | B3.03AO | 
| Esse valor costuma ser: | B3.03C | 
| Descreva a origem do valor. | B3.05AO | 
| Existe alguma forma realista de aumentar sua renda mensal de maneira… | B3.06 | 
| De onde viria essa renda adicional? | B3.06A | 
| Quanto você estima que essa renda poderia acrescentar por mês? | B3.06B | 
| No seu orçamento atual, esse gasto é obrigatório ou não obrigatório? | B3.DF03 | 
| O valor informado foi conferido recentemente ou é uma estimativa? | B3.DF04 | 
| Que despesa é essa? | B3.NM02A | 
| Descreva essa despesa. | B3.NM02AO | 
| Com que frequência ela ocorre? | B3.NM02C | 
| Descreva com que frequência ela ocorre. | B3.NM02CO | 
| Na prática, como seus últimos meses costumam terminar? | B3.C02 | 
| Qual é a sua situação principal? | B3.S02 | 
| Qual é o órgão ou a fonte pagadora desse vínculo? | B3.S03 | 
| Qual é a sua remuneração bruta nesse vínculo? | B3.S04 | 
| Qual é a sua renda líquida nesse vínculo? | B3.S04L | 
| Você consegue consultar atualmente suas margens consignáveis? | B3.S05 | 
| Há algum desconto consignado neste vínculo? | B3.S05C | 
| Qual é o tipo desta margem? | B3.S06A | 
| Descreva essa margem. | B3.S06AO | 
| Qual é o valor total disponível para essa modalidade? | B3.S06B | 
| Quanto está atualmente utilizado? | B3.S06C | 
| Qual é o valor livre informado pelo sistema ou contracheque? | B3.S06D | 
| De quando é essa informação? | B3.S06E | 
| Você sabe se alguma parcela consignada termina nos próximos 12 meses e… | B3.S07 | 
| Qual é o valor da parcela que deixará de ocupar margem? | B3.S07A | 
| Quando isso deve ocorrer? | B3.S07B | 
| Existe algum desconto relacionado a crédito ou consignação no seu… | B3.S08 | 

#### Bloco 4 · Reserva e patrimônio (34)

| Pergunta | ID | 
|---|---|
| Onde esse dinheiro está guardado? | B4.02B | 
| Além dos valores que você já informou como reserva, você possui outros… | B4.04 | 
| Que investimento é esse? | B4.04A | 
| Quanto você estima que perderia ou pagaria para retirar esse investimento? | B4.06A | 
| Você aceitaria considerar o uso desse investimento para reduzir dívidas, caso… | B4.06B | 
| Que imóvel é esse? | B4.I02 | 
| Quanto você estima que esse imóvel vale hoje? | B4.I03 | 
| Além de eventual financiamento, quanto esse imóvel custa para você por mês,… | B4.I06 | 
| Qual é o papel desse imóvel na sua vida hoje? | B4.I07 | 
| Você consideraria vender esse imóvel como parte de uma reorganização… | B4.I08 | 
| Você sabe aproximadamente quais seriam os custos para vender ou transferir… | B4.I09 | 
| Que tipo de veículo é esse? | B4.V02 | 
| Quanto você estima que esse veículo vale hoje? | B4.V03 | 
| Esse veículo possui financiamento ou outra dívida vinculada? | B4.V04 | 
| Qual é aproximadamente o saldo atual? | B4.V04A | 
| Além da parcela de eventual financiamento, quanto esse veículo custa por mês,… | B4.V05 | 
| Esse veículo é essencial para sua rotina atual? | B4.V06 | 
| Você consideraria vender esse veículo como parte de uma reorganização… | B4.V07 | 
| Você consideraria trocar esse veículo por outro de menor valor ou menor custo… | B4.V08 | 
| Se essa troca acontecesse, quanto você imagina gastar aproximadamente no… | B4.V08A | 
| Você estima que essa substituição reduziria seus gastos mensais com o veículo? | B4.V08B | 
| Em quanto aproximadamente por mês? | B4.V08C | 
| Você estima algum custo relevante para vender, transferir ou substituir esse… | B4.V09 | 
| Além de dinheiro, investimentos, imóveis e veículos, você possui algum outro… | B4.O01 | 
| O que é? | B4.O02 | 
| Quanto você estima que vale? | B4.O03 | 
| Existe dívida diretamente vinculada a esse ativo? | B4.O04 | 
| Qual é o saldo aproximado? | B4.O04A | 
| Esse ativo produz renda? | B4.O05 | 
| Esse ativo gera custo recorrente? | B4.O06 | 
| Esse ativo é essencial para sua rotina ou atividade? | B4.O07 | 
| Você consideraria vender ou desmobilizar esse ativo? | B4.O08 | 
| Quais seriam aproximadamente os custos para vendê-lo ou desmobilizá-lo? | B4.O09 | 
| Existe algum recurso ou patrimônio relevante que ainda não apareceu? | B4.F01 | 

#### Bloco 5 · Fichas de dívida (16)

| Pergunta | ID | 
|---|---|
| Para ajudar a lembrar, quais destes tipos você possui ou acredita possuir… | B5.00A | 
| Para que essa dívida foi originalmente feita? | B5.A03 | 
| Esta operação nasceu de uma renegociação ou substituição de uma dívida… | B5.A05 | 
| A dívida anterior ainda continua existindo separadamente? | B5.A05A | 
| Você sabe quanto foi originalmente contratado ou devido nessa operação? | B5.B01 | 
| Você sabe aproximadamente quanto já pagou nessa operação desde o início? | B5.B02 | 
| De quando é essa informação? | B5.B04 | 
| Você sabe quando essa operação termina se seguir normalmente até o fim? | B5.C04 | 
| Quanto aproximadamente você volta a utilizar por mês? | B5.C07A | 
| O documento informa se essa taxa é efetiva ou nominal? | B5.D02 | 
| Você possui o CET — Custo Efetivo Total — desta operação? | B5.D03 | 
| Qual é o CET informado? | B5.D03A | 
| Esta dívida já foi renegociada alguma vez? | B5.G02 | 
| Você já consultou a possibilidade de levar ou substituir esta dívida por uma… | B5.G03 | 
| O que mais faz essa dívida pesar para você? | B5.H02 | 
| Que documentos ou informações você possui hoje sobre esta dívida? | B5.I01 | 

### RF-403. Remover perguntas que o motor usa hoje (24) — **muda o cálculo**

**Situação (2026-10-14):** pendente (T-392). Depende de aprovar as regras substitutas.
Cada uma exige alterar o motor, a montagem e os gabaritos. O especialista não registrou observação; o efeito abaixo é o que o código faz hoje com a resposta.

| Pergunta | ID | Efeito no motor |
|---|---|---|
| Hoje, você já pretende ou considera provável contratar algum novo crédito nos… | B1.02 | Sinal de nova dívida prevista, usado no risco de recaída. |
| Quando você imagina que essa contratação pode acontecer? | B1.05 | Janela da nova dívida, usada no sinal de nova dívida. |
| Nos últimos 12 meses, você assumiu alguma nova dívida ou parcelamento mesmo… | B1.10 | Histórico de recaída, usado no risco de recaída. |
| Hoje, quanto dos seus gastos você costuma registrar ou acompanhar de alguma… | B2.01 | Uma das 8 variáveis do perfil de controle: alimenta o nível de controle e a confiabilidade dos dados do plano. Sem ela a derivação precisa ser redefinida. |
| Com que regularidade você costuma atualizar esse controle? | B2.02 | Uma das 8 variáveis do perfil de controle: alimenta o nível de controle e a confiabilidade dos dados do plano. Sem ela a derivação precisa ser redefinida. |
| Quando você registra um gasto, normalmente faz isso quando? | B2.03 | Uma das 8 variáveis do perfil de controle: alimenta o nível de controle e a confiabilidade dos dados do plano. Sem ela a derivação precisa ser redefinida. |
| E aqueles gastos pequenos — café, lanche, estacionamento, aplicativo,… | B2.04 | Uma das 8 variáveis do perfil de controle: alimenta o nível de controle e a confiabilidade dos dados do plano. Sem ela a derivação precisa ser redefinida. |
| Pensando apenas nas formas de pagamento que você realmente usa, seu controle… | B2.05 | Uma das 8 variáveis do perfil de controle: alimenta o nível de controle e a confiabilidade dos dados do plano. Sem ela a derivação precisa ser redefinida. |
| Quando você olha sua conta ou fatura, com que frequência encontra gastos ou… | B2.07 | Uma das 8 variáveis do perfil de controle: alimenta o nível de controle e a confiabilidade dos dados do plano. Sem ela a derivação precisa ser redefinida. |
| Qual destas opções descreve melhor a sua principal renda? | B3.02 | Tipo de renda (fixa ou variável): campo obrigatório do estado financeiro. |
| Que valor extraordinário é esse? | B3.05A | Tipo do recurso extraordinário: entra no ataque imediato. |
| Esse valor já está sendo reservado ou contabilizado mensalmente em alguma… | B3.NM02D | Evita contar duas vezes a despesa não mensal já incluída em outra despesa. Sem ela, todas somam. |
| Alguma das suas rendas está ligada a vínculo público, aposentadoria ou pensão… | B3.S01 | Só abre as fichas de vínculo público. Sem efeito direto no cálculo. |
| Se a análise mostrar que usar uma parte da reserva pode ser financeiramente… | B4.03 | Disposição de usar a reserva: define a reserva mobilizável. |
| Qual é o valor máximo da sua reserva que você aceitaria colocar em análise… | B4.03A | Valor máximo da reserva em análise: define a reserva mobilizável. Sem as duas a reserva mobilizável fica zero ou desconhecida. |
| Mesmo enquanto paga essa dívida, você continua usando esse limite ou linha de… | B5.C07 | Sinal de risco: continua usando o limite enquanto paga. |
| Essa taxa é: | B5.D01B | Periodicidade da taxa. **Substituída por RF-407**: a periodicidade passa a fazer parte da resposta única de custo da dívida, então não vira perda de dado. |
| Você possui hoje uma proposta concreta do credor para renegociar ou quitar… | B7.04 | Faz parte da proposta de renegociação (Bloco 7). |
| Até quando esta proposta é válida? | B7.15 | Validade da proposta (Bloco 7). |
| Até quando esta proposta de troca é válida? | B8.14 | Validade da proposta de troca (Bloco 8). |
| Nos últimos dois anos, você começou algum plano para organizar as finanças,… | B9.04 | Histórico de abandono: sinal de risco de abandono. |
| A dívida [Dxxx] foi efetivamente quitada? | B11.Q01 | Quitação confirmada: dispara novo plano (Bloco 11). |
| Depois desse pagamento, o credor confirmou que não existe saldo restante? | B11.Q04 | Confirmação de saldo zero (Bloco 11). |
| Qual saldo ainda aparece? | B11.Q04A | Saldo residual após a quitação (Bloco 11). |

### RF-404. Ligar ao motor 32 perguntas
O especialista mandou **manter e fazer o motor usar**. Ele não escreveu a regra de uso para a maioria (ver OQ-5).
6 delas estavam na proposta de ligação do levantamento e 26 foram escolha dele.

#### Bloco 3 · Renda e despesas (7)

| Pergunta | ID | 
|---|---|
| Considerando os últimos meses, qual foi aproximadamente a sua renda líquida… | B3.02A | 
| Outra pessoa contribui regularmente com dinheiro para pagar as despesas que… | B3.04 | 
| Quanto essa pessoa efetivamente coloca, em média, por mês nas despesas deste… | B3.04A | 
| Esse gasto costuma ser fixo ou variável? | B3.DF02 | 
| Essa fotografia de renda e despesas parece representar razoavelmente o seu… | B3.C00 | 
| Quanto costuma sobrar, aproximadamente? | B3.C02A | 
| Quanto costuma faltar, aproximadamente? | B3.C02B | 

#### Bloco 4 · Reserva e patrimônio (7)

| Pergunta | ID | 
|---|---|
| Qual é aproximadamente o valor atual desse investimento? | B4.04B | 
| Se você decidisse resgatar esse investimento, em quanto tempo o dinheiro… | B4.05 | 
| Você sabe se teria algum custo, perda relevante, multa, imposto específico ou… | B4.06 | 
| Esse imóvel possui hoje financiamento ou outra dívida diretamente vinculada a… | B4.I04 | 
| Qual é aproximadamente o saldo devedor atual? | B4.I04A | 
| Esse imóvel gera alguma renda recorrente para você? | B4.I05 | 
| Quanto líquido, aproximadamente, por mês? | B4.I05A | 

#### Bloco 5 · Fichas de dívida (18)

| Pergunta | ID | 
|---|---|
| Quantas dívidas ou operações financeiras diferentes você acredita ter hoje? | B5.00 | 
| Para quem você deve nessa operação? | B5.A01 | 
| Em qual vínculo esta dívida é descontada? | B5.A02V | 
| Quantas parcelas ainda faltam? | B5.C03 | 
| Existe algum pagamento mínimo ou valor mensal formalmente exigido hoje? | B5.C05 | 
| Qual é esse valor mínimo? | B5.C05A | 
| Além dos juros, existe alguma tarifa, encargo ou custo relevante que você… | B5.D04 | 
| Quanto aproximadamente? | B5.D04A | 
| Como está o pagamento desta dívida hoje? | B5.E01 | 
| Há quanto tempo existe valor vencido? | B5.E02 | 
| Esta dívida aparece atualmente em cadastro de inadimplência/negativação? | B5.E03 | 
| Você está recebendo atualmente cobranças relacionadas a essa dívida? | B5.E04 | 
| Esta dívida está vinculada a algum bem ou garantia? | B5.F01 | 
| Qual é a garantia? | B5.F02 | 
| Esse bem é essencial para sua moradia, trabalho, saúde ou rotina familiar? | B5.F03 | 
| Na sua percepção, de 0 a 10, com que urgência esta dívida precisa ser… | B5.H03 | 
| Se você pudesse eliminar apenas uma das suas dívidas primeiro, esta estaria… | B5.H04 | 
| As informações desta dívida foram consultadas ou atualizadas quando? | B5.I03 | 

Das 9 perguntas que o levantamento propôs ligar, ele recusou 3 (mandou sair):
B3.06 (Existe alguma forma realista de aumentar sua…), B3.06B (Quanto você estima que essa renda poderia…), B3.DF03 (No seu orçamento atual, esse gasto é obrigatório…).

### RF-405. Manter
- 15 perguntas do motor confirmadas explicitamente e 39 mantidas por falta de decisão contrária.
- `B5.I02` (de onde vieram as informações) fica **sem efeito no cálculo**, para sustentar o nível de comprovação do revisor (regras de comprovação do app-aluno).
- As 6 perguntas "indispensáveis" para liberar o plano continuam presentes.

### RF-406. Pedidos que o especialista escreveu nas observações (requisitos novos)
- `B3.DF02` (Esse gasto costuma ser fixo ou variável?) [Liga ao motor]: "Colocar um campo com as Despesas Mensais Totais (Receitas Totais - Despesas Totais)"
- `B5.D01` (Você sabe qual é a taxa de juros desta operação?) [sem decisão]: "Qual é o Custo Efetivo Total desta operação? Se não souber, qual é a taxa de juros?"
- `B5.00` (Quantas dívidas ou operações financeiras diferentes…) [Liga ao motor]: "Quantas dívidas ou operações financeiras diferentes você acredita TEM hoje?"
- `B4.V01` (Você possui algum veículo?) [Dúvida]: "Recomendar a aula que possa trazer novos recursos ou reduzir despesas."
- `B3.NM01` (Você tem despesas previsíveis que não acontecem todos…) [Dúvida]: "Despesas Extraordinárias já previstas por mês."
- `B11.01` (Como está esta ação?) [Dúvida]: "Esse bloco só faz sentido se formos acompanhar o plano do aluno."
- `B4.I01` (Você possui algum imóvel, total ou parcialmente?) [Dúvida]: "Colocar como observação: você pode transformar um imóvel em dinheiro para pagar as dívidas, se sim, depois da concretização, volte e inclua o valor liberado."
- `B5.D04` (Além dos juros, existe alguma tarifa, encargo ou custo…) [Liga ao motor]: "Além dos juros, existe alguma tarifa, encargo ou custo sendo cobrado nessa operação?"
- `B5.D05A` (Você sabe quanto esse seguro custa?) [Dúvida]: "Valor?"
- `B5.D03` (Você possui o CET — Custo Efetivo Total — desta…) [Sai]: "Pode sair já que tem a outra pergunta sobre juros."
- `B5.D05S` (Qual é a situação desse seguro hoje?) [Dúvida]: "Não entendi"
- `B4.02` (Você possui hoje alguma reserva financeira separada…) [Fica]: "A reserva de emergência deve permanecer, se for grande demais (mais de 6 meses da despesa, pode ser usada para quitar dívidas)"
- `B5.D04A` (Quanto aproximadamente?) [Liga ao motor]: "Qual valor?"
- `B4.04B` (Qual é aproximadamente o valor atual desse…) [Liga ao motor]: "Qual é o valor?"

Leitura de engenharia, a validar com ele: (a) acrescentar um campo de **resultado mensal total** (receitas totais menos despesas totais); (b) reescrever a pergunta da taxa para pedir o **CET** e, se não souber, a **taxa de juros**; (c) acrescentar notas orientativas ao aluno: usar imóvel para pagar dívida, reserva acima de 6 meses de despesa pode quitar dívida, recomendar aula que traga recursos ou reduza despesas.

## 4. Perguntas em dúvida (14), sem observação

| Pergunta | ID | 
|---|---|
| Você tem despesas previsíveis que não acontecem todos os meses, mas que sabe… | B3.NM01 | 
| Você possui algum imóvel, total ou parcialmente? | B4.I01 | 
| Você possui algum veículo? | B4.V01 | 
| Existe seguro prestamista ou outro seguro associado a esta dívida? | B5.D05 | 
| Você sabe quanto esse seguro custa? | B5.D05A | 
| Esse custo já está incluído no valor da parcela que você informou? | B5.D05B | 
| Qual é a situação desse seguro hoje? | B5.D05S | 
| Qual é o valor desse seguro? | B5.D05V | 
| Por quantos meses esse seguro é cobrado? (No total: o período de cobertura;… | B5.D05P | 
| Qual valor de restituição o credor ou a seguradora já confirmou? | B5.D05R | 
| Você tem conhecimento de algum processo judicial ou cobrança judicial… | B5.E05 | 
| Você sabe de alguma consequência específica que pode ocorrer se esta dívida… | B5.F04 | 
| Existe alguma proposta atual do credor para esta dívida? | B5.G01 | 
| Como está esta ação? | B11.01 | 

## 5. Questões em aberto (nada abaixo foi presumido)

- **OQ-1 (respondida em 2026-10-14: o produto não tem acompanhamento).** O destino do código foi decidido primeiro como desligar (RF-409) e, em 2026-10-15, como **remover** (RF-413): os estados `COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE` e `ACOMPANHAMENTO` e o gatilho de recálculo por quitação (V-01) saíram do código.
- **OQ-2 (respondida em 2026-10-14, ver seção 6, RF-407).** `B5.D01B` (periodicidade da taxa) saiu, e o CET também (`B5.D03`/`B5.D03A`). A montagem só converte a taxa para mensal quando a periodicidade é mensal, e o CET está fixo como desconhecido. **Sem as duas, nenhuma dívida tem juros utilizável e o ranking por juros fica sem dado.** Qual regra substitui? (Opção: pedir a taxa já em "% ao mês".)
- **OQ-3 (respondida: remoção aceita, ver seção 6; falta a regra substituta).** Hábitos de controle: saíram 6 de 8 variáveis do perfil (`B2.01` a `B2.05` e `B2.07`); ficam `B2.06` e `B2.12`. O nível de controle e a confiabilidade dos dados dependem das 8. Qual a nova regra com 2?
- **OQ-4 (respondida: remoção aceita, ver seção 6).** Risco de recaída e abandono: saíram `B1.02`, `B1.05`, `B1.10`, `B9.04` e `B5.C07`. O estado exige os sinais comportamentais completos. Como o risco de recaída é calculado agora?
- **OQ-5 (aberta, depende do especialista; ver plano, seção 5).** As 32 perguntas "Liga ao motor" não têm regra de uso. Para cada uma é preciso definir **como o motor a usa** (variável, fórmula, efeito no plano). Em especial: as de atraso e cobrança (`B5.E01` a `B5.E04`), garantia (`B5.F01` a `B5.F03`), imóvel (`B4.I04` a `B4.I05A`), investimento (`B4.04B`, `B4.05`, `B4.06`), margem mínima (`B5.C05`, `B5.C05A`), renda variável (`B3.02A`) e contribuição familiar (`B3.04`, `B3.04A`).
- **OQ-6 (parcialmente respondida: `B4.04`, ver seção 6; os demais seguem abertos).** Conflitos entre pergunta que abre outra e a que ela abre (8):
  - `B3.02` sai, mas `B3.02A` liga ao motor: Qual destas opções descreve melhor a sua… → Considerando os últimos meses, qual foi…
  - `B3.05A` sai, mas `B3.05B` fica: Que valor extraordinário é esse? → Quanto você espera receber?
  - `B3.05A` sai, mas `B3.05BF` fica: Que valor extraordinário é esse? → Quanto você espera receber só do acréscimo…
  - `B3.C02` sai, mas `B3.C02A` liga ao motor: Na prática, como seus últimos meses costumam… → Quanto costuma sobrar, aproximadamente?
  - `B3.C02` sai, mas `B3.C02B` liga ao motor: Na prática, como seus últimos meses costumam… → Quanto costuma faltar, aproximadamente?
  - `B4.04` sai, mas `B4.04B` liga ao motor: Além dos valores que você já informou como… → Qual é aproximadamente o valor atual desse…
  - `B4.04` sai, mas `B4.05` liga ao motor: Além dos valores que você já informou como… → Se você decidisse resgatar esse…
  - `B4.04` sai, mas `B4.06` liga ao motor: Além dos valores que você já informou como… → Você sabe se teria algum custo, perda…
  Se o pai sai, a filha nunca aparece. Decidir: o pai volta ou a filha sai.
- **OQ-7 (respondida: remoção aceita, ver seção 6).** `B3.02` (tipo de renda) saiu. É campo obrigatório do estado financeiro. Qual o valor assumido (fixa)? Isso afeta `B3.02A` (renda variável), que ele quer ligar.
- **OQ-8 (respondida: remoção aceita, mas contradiz a observação do especialista em `B4.02`; ver seção 6).** Reserva: `B4.03` e `B4.03A` saíram, e a observação de `B4.02` diz que reserva acima de 6 meses de despesa pode quitar dívida. Como o motor define a reserva mobilizável sem a pergunta de disposição?
- **OQ-9 (em espera: o responsável do produto vai confirmar com o especialista).** As 14 dúvidas precisam de resposta (seção 4).
- **OQ-10.** `QUESTIONARIO_VERSION`: os casos em andamento (5 com respostas) têm respostas a perguntas removidas. Manter as linhas sem ler ou limpar?

## 6. Decisões do responsável do produto sobre as questões em aberto (2026-10-14)

Estas decisões **complementam** as do especialista. Os registros do formulário de revisão não foram alterados.

### RF-407. Um único valor de custo da dívida, obrigatório (confirmado em 2026-10-14)
O aluno informa **um só valor** por dívida: o **CET** (preferência) ou, se não souber, a **taxa de juros**. No sistema o valor é tratado como **a taxa da dívida**, com um único nome de variável. **Não se registra qual dos dois foi informado.**

- **Pergunta:** "Qual é o Custo Efetivo Total (CET) desta operação? Se não souber, informe a taxa de juros."
- **Texto de ajuda na tela, abaixo da pergunta:** "No seu contrato, extrato ou aplicativo do banco, esse número pode aparecer escrito como CET ou como taxa de juros. Informe o que encontrar e diga se é ao mês ou ao ano."
- **Resposta:** valor e periodicidade (ao mês ou ao ano), os dois obrigatórios, na mesma resposta. **Sem opção "não sei".** Sem o valor o plano não é gerado.
- **Substitui cinco perguntas por dívida por uma:** `B5.D01` (qualidade da taxa), `B5.D01A` (taxa), `B5.D01B` (periodicidade), `B5.D03` (possui CET) e `B5.D03A` (CET). Nas listas de RF-402 e RF-403, `B5.D03`, `B5.D03A` e `B5.D01B` aparecem como "saem": a decisão correta é **substituídas por esta pergunta**.
- **Periodicidade continua obrigatória** porque "2" pode ser 2% ao mês ou ao ano. Ela faz parte da mesma resposta (campo de taxa com unidade), não é pergunta separada.
- **Consequências de engenharia, a validar:**
  1. Hoje a montagem lê a taxa e a periodicidade como respostas separadas, só aceita a taxa quando a periodicidade é mensal e **ignora o CET** (fixo como desconhecido). Passa a ler uma resposta composta (valor e unidade), com o formato definido no registro da pergunta.
  2. A conversão do ano para o mês é fórmula financeira e pertence ao motor, não à montagem (Lei nº 3). **Hoje o motor não tem essa conversão** (recebe a taxa mensal pronta): será criada uma função pura nova no motor, com regra na spec do motor, e a montagem a chama (T-393, aprovada em 2026-10-14).
  3. Dívida sem esse valor bloqueia o cálculo, como o inventário incompleto (regra do inventário incompleto do app-aluno).
  4. O ranking por juros continua usando a taxa efetiva mensal. O CET como segunda opção (regra de fallback do motor-calculo) deixa de existir como campo à parte.
- **Risco aceito pelo responsável do produto (OQ-12, respondida):** CET e taxa de juros não são a mesma medida (o CET inclui tarifas e seguros). O ranking passa a comparar o CET de umas dívidas com a taxa de outras, sem marcação de qual foi informado.

### RF-407 (complemento). Nomes no sistema
Implementado na T-393: a pergunta única é `B5.D06`, que grava o percentual em `TAXA_DIVIDA` e a periodicidade (`MENSAL` ou `ANUAL`) em `PERIODICIDADE_TAXA_DIVIDA`. Ela substitui `B5.D01`, `B5.D01A`, `B5.D01B`, `B5.D03` e `B5.D03A`. Nos documentos da spec canônica os nomes antigos continuam sendo os de origem. A pergunta única coleta **um valor com a periodicidade** (ao mês ou ao ano), seja CET ou taxa.

### RF-408. Perguntas de valor devem pedir o valor exato (decisão de 2026-10-14)
Regra: "por se tratar de programa de cálculo, o motor precisa dos valores exatos; nada subjetivo". Pergunta que pede valor não pode usar "aproximadamente", "estima", "em média" ou "acredita". Deve pedir o número exato e dizer **onde ele está** (contracheque, extrato, fatura, contrato).

No registro há 66 perguntas com linguagem aproximada ou subjetiva; 41 saem pelas decisões acima. Das **25 que ficam**, **16 pedem valor ou quantidade** e entram nesta regra. As outras 9 medem hábito ou comportamento (por exemplo, "o que você costuma fazer quando o dinheiro não chega") e **não** são valores: ficam como estão.

| ID | Redação atual | Redação proposta (a aprovar) |
|---|---|---|
| B3.01 | "Quanto você recebe por mês, **em média**…" | "Qual é o valor líquido que você recebe por mês, conforme seu contracheque (depois do imposto de renda e da previdência, antes de empréstimos e consignados)?" |
| B3.03B | "Quanto essa renda acrescenta, em média, por mês?" | "Qual é o valor mensal dessa renda adicional, conforme o último comprovante?" |
| B3.04A | "Quanto essa pessoa coloca, em média…" | "Qual valor exato essa pessoa coloca por mês nas despesas deste orçamento?" |
| B3.C01 | "…qual valor adicional você **acredita** conseguir separar…" | "Qual valor exato você se compromete a separar todo mês para pagar dívidas?" |
| B3.C02A | "Quanto costuma sobrar, **aproximadamente**?" | "Qual foi a sobra do último mês fechado, conforme seu extrato?" |
| B3.C02B | "Quanto costuma faltar, **aproximadamente**?" | "Qual foi a falta do último mês fechado, conforme seu extrato?" |
| B2.10 | "Quanto por mês você **estima** que poderia reduzir…" | "Qual é o valor mensal exato desses gastos, conforme sua fatura ou extrato?" |
| B4.01A | "Quanto **aproximadamente**?" | "Qual é o valor exato disponível hoje?" |
| B4.02A | "Qual é o valor total que você **considera** como reserva…" | "Qual é o saldo total da sua reserva hoje, conforme o extrato?" |
| B4.04B | "Qual é **aproximadamente** o valor atual desse investimento?" | "Qual o valor?" (decisão do responsável do produto; sugestão de complemento: "conforme o extrato") |
| B4.I04A | "Qual é **aproximadamente** o saldo devedor…" | "Qual é o saldo devedor atual do financiamento, conforme o contrato ou extrato?" |
| B4.I05A | "Quanto líquido, **aproximadamente**, por mês?" | "Qual é o valor líquido mensal exato que o imóvel gera?" |
| B5.00 | "Quantas dívidas… você **acredita** ter hoje?" | "Quantas dívidas ou operações financeiras diferentes você tem hoje?" (também sugerida pelo especialista) |
| B5.C06A | "Nos últimos 3 meses, qual foi **aproximadamente** a média mensal paga?" | "Qual foi o valor pago nesta dívida em cada um dos últimos 3 meses, conforme o extrato?" (3 campos; o motor passa a calcular a média, o que é agregação de entrada a especificar) |
| B5.D04A | "Quanto **aproximadamente**?" | "Qual é o valor mensal exato dessas tarifas e encargos?" |
| B3.02A | "…qual foi **aproximadamente** a sua renda líquida média mensal?" | Em suspenso: depende de `B3.02` (tipo de renda) ter saído |

**Textos sugeridos pelo especialista nas observações (não são dúvidas).** Duas das observações que ele deixou em perguntas marcadas como dúvida eram sugestões de redação mais clara:
- `B3.NM01`: de "Você tem despesas previsíveis que não acontecem todos os meses, mas que sabe que precisará pagar ao longo do ano?" para "Despesas Extraordinárias já previstas por mês." A pergunta é respondida com Sim, Não ou Não sei, então o texto precisa continuar sendo uma pergunta. Proposta que mantém as palavras dele: "Você tem Despesas Extraordinárias já previstas?", com a ajuda "São despesas que não acontecem todo mês." (a confirmar no formulário da segunda rodada). Com isso `B3.NM01` **sai da lista de dúvidas**.
- `B5.D05A` ("Valor?") e `B5.D05S` ("Não entendi") eram avisos de texto confuso, e as duas perguntas já saíram junto com o seguro (RF-410).
O mesmo estilo curto e direto aparece em outras observações dele: `B4.04B` ("Qual o valor?", confirmado), `B5.D04A` ("Qual valor?") e `B5.00` ("…você **tem** hoje?"). Entram na tarefa T-394.

**Limite a registrar (OQ-11).** Mudar o texto não garante exatidão: o aluno pode inventar um número para seguir. O que protege o cálculo é (a) pedir a **fonte** do valor, (b) validações cruzadas (por exemplo, parcela maior que o saldo, como a `D008` do Guilherme) e (c) a opção "não sei", que hoje deixa o campo como desconhecido e o plano provisório, em vez de inventar um valor (`GAB-03`). Decidir quais perguntas **não** admitem "não sei" além da taxa/CET (RF-407): hoje 12 das 16 admitem.

### RF-410. Seguro da dívida sai do questionário e deixa de ser considerado (decisão de 2026-10-14)

**Situação (2026-10-14):** concluído (T-391).
Decisão do responsável do produto: "o seguro da dívida não precisamos considerar no motor e nem no questionário; o especialista marcou dúvida porque está confuso". Saem as 7 perguntas por dívida: `B5.D05`, `B5.D05A`, `B5.D05B`, `B5.D05S`, `B5.D05V`, `B5.D05P` e `B5.D05R`. Isso resolve 7 das 14 dúvidas.
- O motor já tratava o seguro como informativo (`CUSTO_SEGURO` e `SEGURO_INCLUIDO_PARCELA` nunca entram no cálculo, `GAB-01`). Os dois campos continuam declarados em `engine/estado.py`, sem uso. A remoção deles do motor depende de nova versão da spec do motor e fica como tarefa futura.
- A montagem passa a entregar ao motor valores neutros fixos (custo do seguro desconhecido; seguro incluído na parcela falso). O PDF e a tela do revisor deixam de mencionar seguro; o custo do seguro deixa de aparecer como "informação pendente".

### Demais respostas
| OQ | Decisão do responsável do produto | Efeito |
|---|---|---|
| OQ-3 | Hábitos de controle: "não é tão relevante para a saída do plano". Remoção das 6 perguntas **aceita** | Falta a regra substituta para o nível de controle e a confiabilidade dos dados com `B2.06` e `B2.12`. Proposta de engenharia a aprovar: derivar só dessas 2 |
| OQ-4 | Risco de recaída e abandono: "se for abandono do usuário não tem problema; quero o mínimo que o aluno precisa preencher". Remoção de `B1.02`, `B1.05`, `B1.10`, `B9.04` e `B5.C07` **aceita** | O estado exige os sinais; o motor passa a tratá-los como desconhecidos |
| OQ-7 | Tipo de renda (`B3.02`): **pode tirar** | Assumir renda fixa (servidor público) e documentar. `B3.02A` (renda variável) perde sentido |
| OQ-8 | Reserva (`B4.03`, `B4.03A`): **pode tirar** | A reserva mobilizável fica zero. **Contradiz** a observação do especialista em `B4.02` (reserva acima de 6 meses de despesa pode quitar dívida). Confirmar com ele |
| OQ-6 (parte) | `B4.04` **fica**; `B4.04B` passa a se chamar **"Qual o valor?"** | Resolve 3 dos 8 conflitos (`B4.04B`, `B4.05`, `B4.06`) |
| OQ-1 | Sem acompanhamento: plano único | `B11.01` ("só faz sentido se formos acompanhar o plano") deixa de ter razão de existir; está em dúvida e **não foi alterada**. Confirmar com o especialista |
| OQ-12 | CET ou taxa em um só valor, sem marca de qual foi informado | Ver RF-407 |
| OQ-9 | Das 14 dúvidas, as 7 de **seguro da dívida** foram decididas (RF-410: saem). As outras 7 seguem como estão até o responsável confirmar com o especialista | 6 restantes: `B5.E05`, `B5.F04`, `B5.G01`, `B4.I01`, `B4.V01`, `B11.01` (`B3.NM01` era sugestão de texto, não dúvida) |

### Decisões do responsável do produto no primeiro formulário (2026-10-14)
Lidas do banco do formulário de revisão, onde o responsável do produto alterou 8 registros:
- `B4.V01` (veículo): dúvida → **sai**. A recomendação de aula que o especialista queria junto da pergunta fica sem lugar para aparecer; a tarefa T-396 remove a pergunta.
- `B5.D05`, `B5.D05A`, `B5.D05B`, `B5.D05S` e `B5.D05V` (seguro): dúvida → sai, de acordo com RF-410.
- `B5.D05P` e `B5.D05R` (seguro): dúvida → **fica**. Isso contradiz RF-410, que tira as 7 perguntas de seguro, e as duas já saíram do questionário (T-391). Registro tratado como engano até confirmação.

**Dúvidas que seguem abertas (3):** `B5.F04` (proposta: sai, por ser subjetiva), `B4.I01` (imóvel, o especialista quer um texto de orientação) e `B11.01` (tudo indica sair, pela condição que ele mesmo escreveu). `B5.E05`, `B5.G01` e `B3.NM01` deixaram de ser dúvida com a regra RF-411.

### RF-411. Pergunta de existência: Sim ou Não direto, sem "Não sei" (decisão de 2026-10-14)
O responsável do produto explicou que as dúvidas do especialista vinham de a pergunta estar subjetiva. Regra: pergunta que apenas diz se a coisa existe ("tem" ou "não tem") tem **duas respostas, Sim e Não**. Não existem "Não sei", "Talvez" nem "Recebi, mas já venceu".
- **Aplica já** (as dúvidas que dependem disso): `B5.E05` ("Esta dívida tem processo ou cobrança judicial?"), `B5.G01` ("O credor já fez uma proposta para esta dívida?") e `B3.NM01` ("Você tem Despesas Extraordinárias já previstas?", com a ajuda "São despesas que não acontecem todo mês"). As três ficam como pergunta, e com isso deixam de ser dúvida. `B4.I01` já é Sim ou Não; sua dúvida era o texto de orientação.
- **`B5.F04`** (consequência do não pagamento) é uma lista de consequências e não tem como virar Sim ou Não sem perder o sentido. Proposta: sai (decisão do especialista).
- **Extensão pendente (OQ-11):** hoje 64 das 118 perguntas aceitam "Não sei", e 13 são do tipo Sim, Não ou Talvez (`B3.03`, `B3.04`, `B3.D11`, `B3.NM02D`, `B4.I04`, `B4.I05`, `B5.C01`, `B5.C05`, `B5.D04`, `B5.E03`, `B5.F01`, `B5.H04`). Estender a regra a elas muda como o motor trata a resposta desconhecida (hoje vira `DESCONHECIDO`, sem estimar) e fica para uma segunda tarefa, depois da confirmação.

### Conflitos pai e filha ainda abertos
- `B3.02` (sai) e `B3.02A` (liga): sem o tipo de renda, a renda variável nunca aparece.
- `B3.05A` (sai) e `B3.05B`, `B3.05BF` (ficam).
- `B3.C02` (sai) e `B3.C02A`, `B3.C02B` (ligam).

- **OQ-12 (respondida em 2026-10-14).** Aceitar a mistura entre CET e taxa, sem marcar qual foi informado. Risco registrado em RF-407.

## 7. User Stories

- **US-401.** Como aluno, quero responder só o que o plano precisa, para terminar o questionário em menos tempo. (RF-402, RF-403, RF-410)
- **US-402.** Como aluno, quero receber um plano definitivo, para não ter que voltar e refazê-lo. (RF-401, RF-409)
- **US-403.** Como especialista, quero decidir pergunta a pergunta o que sai, o que fica e o que passa a alimentar o motor, para o questionário refletir o método. (RF-402 a RF-406)
- **US-404.** Como responsável do produto, quero que cada pergunta mantida tenha efeito no plano, para não pedir dado que não muda nada. (RF-404, RF-405)
- **US-405.** Como revisor, quero liberar o plano sem depender de pergunta que saiu do questionário. (RF-402, RF-410)

## 8. Acceptance Criteria

| ID | Rastreia | Critério | Situação |
|---|---|---|---|
| AC-401 | RF-401, RF-409 | Dado um caso em `PLANO_LIBERADO`, quando qualquer transição é pedida, então é recusada; as rotas pós-plano não existem; a tela do aluno não oferece refazer plano nem acompanhamento | verificado (T-387, T-388, T-390) |
| AC-402 | RF-402 | Dado o registro do questionário, quando carregado, então nenhuma das perguntas removidas existe (87 na T-389, `B4.V01` na T-396, 15 na T-398) e a versão (`1.3.0`) é a mesma em todos os arquivos | verificado (T-389, T-396, T-398, T-400) |
| AC-403 | RF-402, RF-410 | Dado um caso de prova, quando as respostas das perguntas removidas são retiradas, então o `EstadoFinanceiro` e o `SnapshotOrdem` são idênticos | verificado (T-389, T-391) |
| AC-404 | RF-410 | Dado um plano, então o PDF e a tela do revisor não mencionam seguro da dívida nem o apontam como informação pendente | verificado (T-391) |
| AC-405 | RF-407 | Dada uma dívida sem CET e sem taxa, quando o cálculo é pedido, então ele é bloqueado; a taxa ao ano é normalizada para o mês pela regra `§16.1` do motor | verificado (T-393) |
| AC-406 | RF-408, RF-415 | Dada qualquer pergunta que continua pedindo valor, então o enunciado não contém "aproximadamente", "estima", "em média" nem "acredita" | parcial: verificado nas perguntas de valor aprovadas (T-402); faltam `B3.02A` (em suspenso) e os três campos de `B5.C06A` (T-394) |
| AC-407 | RF-403, RF-404 | Para cada pergunta removida do motor ou ligada a ele existe regra normativa na spec do motor e teste com critério de aceite | parcial: as regras novas de `B3.DF02` (§16.2) e `B3.C02A`/`B3.C02B` (§16.3) têm critérios e testes (T-399, T-403); o restante depende de T-392 e T-395 |
| AC-408 | RF-405 | As 6 perguntas indispensáveis para liberar o plano continuam no registro | verificado (T-389) |
| AC-409 | RF-411 | Dadas `B5.E05`, `B5.G01` e `B3.NM01`, então cada uma aceita só Sim ou Não | verificado (T-397) |
| AC-410 | RF-413, RF-409 | Dado o enum de estados do caso, então não contém `COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE` nem `ACOMPANHAMENTO`; `PLANO_LIBERADO` não aceita transição | verificado (T-400) |
| AC-411 | RF-412 | Dado um caso com `B5.E01` atrasada, `B5.F01` com garantia ou `B5.00` maior que as fichas, então o plano mostra o aviso com a frase de responsabilidade do aluno, a ordem não muda e o bloqueio por fichas faltando continua | verificado (T-399) |
| AC-412 | RF-412 | Dadas `B3.C02A`/`B3.C02B` e o resultado mensal calculado, então a tela mostra a diferença e o aluno aceita ou revisa; despesas fixas e variáveis e "Despesas mensais totais" aparecem no plano | verificado (T-399; regras §16.2 e §16.3 do motor) |
| AC-413 | RF-414 | Dada `B5.E01`, então não oferece "Não sei" e é obrigatória | verificado (T-401) |
| AC-414 | RF-415 | Dado o revisor, então vê `B5.I03` como informação, sem efeito no cálculo | verificado (T-402) |
| AC-415 | RF-416 | Dado o plano, a FAQ e o anexo, então nenhum menciona refazer o plano, "Gerar um novo plano" nem acompanhamento; os números do plano de quem fecha o mês no negativo fecham entre si | a implementar (T-403) |
| AC-416 | RF-420 | Dado o questionário carregado, então nenhuma das 17 perguntas de RF-420 existe e o estado do motor com ou sem as respostas antigas é o mesmo, exceto os campos neutros | verificado (T-408) |
| AC-417 | RF-421 | Dada a lista de despesas, então cada linha traz o valor em reais e Fixo/Variável ao lado | verificado (T-410) |
| AC-418 | RF-422 | Dado um campo de valor do cálculo, então não há "Não sei" na tela, a requisição com `nao_sei` é recusada e um "não sei" antigo vira pendência | verificado (T-411) |
| AC-419 | RF-423 | Dada a despesa não mensal, então o formulário pede o nome e a lista mostra o nome digitado | verificado (T-412) |
| AC-420 | RF-424 | Dada a `B3.C00`, então as despesas aparecem sem abrir nada, em tabela com "Corrigir" à direita | verificado (T-413) |
| AC-421 | RF-425 | Dado `B5.00`, então não há "Não sei"; "Nenhuma dívida" mostra o aviso, não abre ficha e bloqueia o cálculo; quantidade inválida é recusada | verificado (T-414) |
| AC-422 | RF-426 | Dado `B5.A01`, então o aluno escolhe a instituição num menu, ou "Outra" e digita o nome; nome vazio ou acima de 60 letras é recusado | verificado (T-415) |
| AC-423 | RF-427 | Dado `B5.A04`, então a pergunta é "Qual é o status desta operação hoje?" e não há opção de quitação a confirmar | verificado (T-416) |
| AC-424 | RF-428 | Dadas as perguntas listadas em RF-428, então não oferecem "Não sei"/"Talvez"/"Não tenho certeza"; sim/não mostra só Sim e Não | verificado (T-417) |
| AC-425 | RF-429 | Dada `B5.C06`, quando a pessoa escolhe o valor total, então o pagamento mensal efetivo é igual ao saldo devedor de `B5.B03` | verificado (T-418) |
| AC-426 | RF-430 | Dado um caso em conferência, então o Início não traz o botão "Aguardar a conferência", traz a explicação da espera, e a rota `#aguardando` deixa de existir | verificado (T-419) |
| AC-427 | RF-431 | Dado um caso em conferência, então o Início mostra as três etapas, o prazo e os dois botões; editar só retira o plano da fila depois da confirmação; sem permissão do servidor não há botão de editar | verificado (T-420) |
| AC-428 | RF-432 | Dada qualquer tela do aluno com andamento, então há exatamente três etapas, uma só atual, e a primeira se chama "Preencha as informações" | verificado (T-421) |
| AC-429 | RF-433 | Dada "Minhas respostas", então as cinco partes aparecem na mesma página, o índice fixo leva a cada uma e destaca a visível, a busca encontra pergunta ou resposta, e visualizar e editar têm o mesmo layout (campos editáveis só na edição) | verificado (T-422) |
| AC-430 | RF-434 | Dadas fichas de tipos diferentes, então cada título traz o tipo e o número dentro do tipo, e despesa não aparece como dívida | verificado (T-423) |
| AC-431 | RF-435 | Dado o índice de "Minhas respostas" no computador, então as cinco partes aparecem numa linha, com texto curto e nome acessível completo | verificado (T-424) |
| AC-432 | RF-436 | Dado o Início de um caso com tudo preenchido, então não há "Ver meu progresso", o envio tem confirmação, e as listas de fichas são alcançadas por "Minhas respostas" | verificado (T-425) |
| AC-433 | RF-437 | Dado o modo de edição, então cada botão de gerenciar fichas está na sua seção, e clicar numa parte do índice leva o topo dela para logo abaixo do índice, mesmo com os campos abrindo | verificado (T-426) |
| AC-434 | RF-438 | Dada a ficha de dívida, então ela termina na última pergunta de dados, sem "Essa ficha está correta?" nem "tem mais dívida?" | verificado (T-427) |
| AC-435 | RF-439 | Dada a edição de "Minhas respostas", então a lista traz os campos numa só requisição e a tela não pede uma pergunta por linha | verificado (T-427) |
| AC-436 | RF-440 | Dado o questionário, então `B3.C01A` não existe, e o prognóstico mostra os caminhos vermelho e azul, sem o verde | verificado (T-428) |
| AC-437 | RF-441 | Dado um caso em conferência, então a tela mostra resumo executivo, tabela de dívidas ligada por `DIVIDA_ID`, apoio à decisão e todos os dados de entrada, sem valor inventado e sem mudar a regra de liberação | verificado (T-429) |
| AC-438 | RF-442 | Dado um caso com 3 dívidas cadastradas e 1 na ordem do plano, então o indicador mostra "1 de 3 cadastradas", a tabela lista as 3 e o total em dívidas soma os saldos informados (parcial se faltar saldo) | verificado (T-430) |

### RF-420. Saem as 17 perguntas que o motor não lê (2026-10-22)
Levantamento de uso de todas as perguntas (leitura do motor, da montagem, do plano e do revisor). Saem, por decisão do produto ("o que está sem uso pode remover"), as perguntas sem consumidor no cálculo: `B2.13`; `B2.09`, `B2.10` e `B2.10A`; `B3.C00A`; `B3.C02`, `B3.C02A`, `B3.C02B` e `B3.C02C`; `B4.01` e `B4.01A`; `B4.04` e `B4.I01`; `B5.G01`; `B5.B05`, `B5.B05A` e `B5.B05B`. Questionário de 84 para 67 perguntas na coleta.
- Valores neutros na montagem, motor intocado: `AUTOPERCEPCAO_CONTROLE = DESCONHECIDO`; `ECONOMIA_POTENCIAL_IMEDIATA` = o valor da chamadora (zero); `DINHEIRO_DISPONIVEL = 0`; `QUITACAO_CONSULTADA = NAO`, `VALOR_QUITACAO_HOJE = DESCONHECIDO`, `STATUS_VALIDADE_PROPOSTA = VALIDADE_DESCONHECIDA` (o motor já usava sempre o saldo devedor).
- `B4.04` e `B4.I01` estavam como "manter" em RF-418; a decisão de agora as substitui.
- Saem também o painel de comparação entre sobra/falta informada e calculada, e a exigência de justificar quando a fotografia do mês não confere (parte de RF-412). `B3.C00` segue e continua levando a `B3.D11` ou à correção.
- A tela do revisor deixa de listar os cinco campos que não têm mais pergunta.
- `engine/percepcao.py` e `engine/despesas.py` ficam como estão (o motor não muda sem a spec do motor).
- `QUESTIONARIO_VERSION` segue em `1.3.0`, como em T-398 (sem mudar o formato das respostas guardadas).

### RF-421. Lista de fichas curtas com o que foi preenchido (2026-10-22)
Na lista de despesas (e demais fichas curtas), cada linha mostra ao lado o valor em reais e as escolhas (ex.: Fixo ou Variável) no lugar de "N campos". A dívida segue com a contagem.

### RF-422. Sem "Não sei" nos campos de valor do cálculo (2026-10-22)
Decisão do produto: o valor precisa existir, mesmo estimado. Perdem a opção `B3.03B`, `B3.04A`, `B3.05B`, `B3.DF01`, `B3.DF02`, `B3.NM02B`, `B3.C01`, `B5.B03`, `B5.C02`, `B5.C06` e `B5.C06A`. O servidor recusa "não sei" em pergunta que não o admite, e quem já respondeu "não sei" antes volta a ter pendência. A montagem segue lendo respostas antigas (revisa AC-08 só para estes campos de entrada).

### RF-423. A despesa não mensal tem nome (2026-10-22)
A ficha da despesa não mensal pede um nome (obrigatório para concluir), e a lista, a fotografia e o revisor mostram esse nome em vez do identificador (`NM001`). Vale também para as já cadastradas.

### RF-424. Fotografia do mês com as despesas à vista, em tabela (2026-10-22)
Na `B3.C00` as despesas por item e as não mensais aparecem sempre abertas, em tabela compacta (modelo da fila do revisor) com o botão "Corrigir" à direita e, no monitor, lado a lado; abaixo de 768px viram cartões.

### RF-425. Quantidade de dívidas exata, com "Nenhuma dívida" (2026-10-22)
`B5.00` perde o "Não sei exatamente quantas". A pessoa escolhe "Nenhuma dívida" ou informa a quantidade (inteiro de 1 a 50); valor negativo, decimal ou vazio é recusado. O cálculo exige uma ficha para cada dívida declarada. "Nenhuma dívida" não abre ficha de dívida, mostra na própria pergunta o aviso de que, sem dívidas, não há plano de quitação, e o caso não segue para o cálculo (pendência de inventário `SEM_DIVIDAS`, que leva de volta à `B5.00`).

### RF-426. Credor escolhido em lista de instituições (2026-10-22)
`B5.A01` ("Para quem você deve nessa operação?") deixa de ser texto livre: a pessoa escolhe num menu entre Caixa Econômica Federal, Banco do Brasil, Itaú, Bradesco, Santander, Nubank, Banco Inter, C6 Bank, Sicoob e Sicredi, ou em "Outra instituição ou pessoa", que abre um campo para digitar o nome (1 a 60 letras). O nome mostrado no plano, na lista e na conferência é o do banco ou o digitado; respostas antigas em texto livre seguem como estão.

### RF-427. Status da operação direto, sem palpite de quitação (2026-10-22)
`B5.A04` passa a perguntar "Qual é o status desta operação hoje?" e deixa de oferecer "Acredito que esteja quitada, mas preciso confirmar". O motor mantém o tratamento da situação antiga para respostas já gravadas.

### RF-428. Sem "Não sei", "Talvez" e "Não tenho certeza" nas perguntas de fato (2026-10-22)
Decisão do produto: o cálculo precisa de exatidão, sem adivinhação. Perdem a opção de palpite `B5.C01`, `B5.E02`, `B5.E03`, `B5.F01`, `B5.F02`, `B5.F03`, `B5.H04`, `B5.I03` e `B5.FIM01` ("Não sei"/"Não tenho certeza"), `B4.02A` e `B4.03A` (valor), `B2.11` ("Não consigo avaliar") e `B3.05C` ("Ainda não sei"). `B1.07` e `B3.05` passam a Sim ou Não, sem "Talvez"; as fichas do valor extraordinário abrem só com "Sim". Ficam, por serem escalas de comportamento e não sim/não, `B2.06`, `B4.03` e a opção de pular de `B3.C01A` (opcional); estão no relatório de subjetividade. O motor segue lendo respostas antigas.

### RF-429. Pagamento mensal "valor total da dívida" (2026-10-22)
Em `B5.C06` ("Na prática, quanto você está pagando por mês nesta dívida atualmente?") há a opção "Estou pagando o valor total da dívida." O pagamento passa a ser o saldo devedor que a pessoa já informou em `B5.B03`: copiado, não calculado, para ela não digitar o mesmo valor duas vezes. Se o saldo for corrigido depois, o pagamento acompanha.

### RF-430. Sem botão nem tela de "Aguardar a conferência" (2026-10-22)
Com o plano calculado e em conferência, o Início não oferece mais o botão "Aguardar a conferência" nem leva a uma tela de espera. O próprio Início diz que a equipe confere o plano antes de liberar e que o aviso vem por e-mail (normalmente até 2 dias úteis), e mantém as consultas ("Ver minhas respostas", "Quero editar minhas respostas") e o "Sair".

### RF-431. Tela de acompanhamento do plano em elaboração e análise (2026-10-22)
Com o plano em conferência, o Início vira "Meu plano de quitação": andamento com exatamente três etapas (Informações enviadas — concluída; Elaboração e análise do plano — etapa atual; Plano liberado — pendente), um cartão "Estamos preparando seu plano de quitação", o prazo estimado de até 2 dias úteis com o aviso por e-mail e a orientação de espera, e o cartão "Quer revisar suas informações?" com "Ver minhas respostas" e "Editar minhas respostas". Editar pede confirmação ("Alterar suas informações?", com "Continuar aguardando" e "Editar respostas") antes de retirar o plano da fila, e só existe quando o servidor permite (`pode_retomar_edicao`). A tela nunca diz que o plano está calculado ou pronto, e não traz contagem regressiva, data nem porcentagem. Substitui a explicação de espera de RF-430.

### RF-432. Andamento do plano em três etapas em todas as telas (2026-10-22)
A jornada "Onde você está" passa a ter três etapas em toda tela do aluno — **Preencha as informações**, **Elaboração e análise do plano** e **Plano liberado** — no lugar das quatro de RF-64 (que ficam substituídas, com AC-93/AC-94 revistos para três). A etapa atual vem da fase do caso: coleta → 1; conferência, plano devolvido e fase desconhecida → 2; plano liberado → 3. O andamento aparece no Início, na tela do termo e nas telas de coleta (pergunta, lista de fichas e formulário); nestas, as cinco partes do questionário seguem logo abaixo como progresso secundário. Continua informativo: nenhuma etapa é clicável.

### RF-433. "Minhas respostas" em uma página só, igual para ver e editar (2026-10-22)
A tela deixa de ter menu lateral e de mostrar uma parte por vez. Todas as cinco partes aparecem em sequência numa página, cada uma com número, título, contagem e as perguntas com as respostas. No topo há um índice horizontal fixo que leva a cada parte por rolagem suave e destaca sozinho a parte que está à vista (no celular rola na horizontal), uma busca por pergunta ou resposta que leva ao item e o realça, e uma faixa de status. O layout é o mesmo nos dois modos: na visualização (cálculo, conferência, plano liberado) as respostas só se leem; na edição cada resposta vira o campo de sempre, com as mesmas máscaras, validações e campos condicionais. As alterações ficam em rascunho e o "Salvar alterações" grava cada uma pela rota de sempre, uma por vez, mostrando o erro na própria linha. O modo vem do servidor (`editavel`); a retirada do plano da conferência continua pedindo confirmação.

### RF-434. Título das fichas em "Minhas respostas" pelo tipo (2026-10-22)
Cada ficha ganha o título do seu tipo e o número dentro do tipo: "Dívida 1", "Despesa 1", "Renda adicional 1", "Despesa não mensal 1", "Valor extraordinário 1". A despesa mensal deixa de ser chamada de "Dívida", e a numeração recomeça a cada tipo.

### RF-435. Índice de "Minhas respostas" com textos curtos (2026-10-22)
O índice fixo mostra um texto curto por parte — Compromisso, Controle dos gastos, Entradas e saídas, Salário e margem, Dívidas — para os cinco caberem numa linha no computador. O título completo continua na seção, no nome acessível e na dica do botão. No celular o índice segue rolando na horizontal.

### RF-436. Fim da tela de progresso e envio ao especialista com confirmação (2026-10-22)
O Início deixa de oferecer "Ver meu progresso" e a tela de progresso (`#progresso`) deixa de existir; ela substitui RF-31/AC-40. O que tinha de único, o acesso às listas de fichas (dívidas, despesas, rendas adicionais; RF-53, AC-04), passa para "Minhas respostas", num bloco "Dívidas e despesas cadastradas" só no modo editável. O destino `progresso` que o servidor ainda envia na fase de plano devolvido abre "Minhas respostas". O botão "Montar o seu plano" vira **"Enviar para análise do especialista"** e pede confirmação ("Depois de enviar, suas respostas ficam só para leitura até a conferência") antes de levar ao cálculo; vale também para o reenvio depois de uma devolução.

### RF-437. Atalhos das fichas na seção de cada uma e índice que chega ao destino (2026-10-22)
Os botões de gerenciar fichas deixam de ser um bloco solto acima da página: cada um fica no cabeçalho da seção em que a ficha nasce (despesas, despesas não mensais, rendas adicionais e valores extraordinários na parte 3; dívidas na parte 5), com a redação "Gerenciar …" e só no modo de edição. O índice fixo leva a cada seção com o topo logo abaixo dele e corrige a chegada, porque no modo de edição os campos das linhas abrem durante a rolagem e mudam a altura da página.

### RF-438. Saem "Essa ficha está correta?" e "Você ainda precisa cadastrar alguma outra dívida?" (2026-10-22)
`B5.CHECK` e `B5.FIM01` não mudavam nada no cálculo: a ficha fecha quando a última pergunta é respondida, e "adicionar outra dívida" já é um botão da lista. Saem do questionário (62 perguntas), junto da guarda de "salvar a ficha" que só existia por causa de `B5.CHECK`. `B5.FIM02` (todas as dívidas foram cadastradas?) permanece.

### RF-439. A edição de "Minhas respostas" não faz uma requisição por linha (2026-10-22)
`GET /caso/{id}/respostas?com_campos=1` devolve, em cada resposta, também o campo pronto para editar (mesmo objeto de `GET /pergunta/{ID}`), só quando o caso é editável; sem o parâmetro a resposta é a de sempre. A página usa esse campo e só busca a pergunta de uma linha se ele faltar, cancelando a busca ao sair da tela.

### RF-440. Sai "Se você fizesse um esforço extra…" (B3.C01A) (2026-10-22)
Pergunta opcional, hipotética, que só alimentava o caminho "verde" do prognóstico. Sai do questionário (61 perguntas) e do cálculo: a montagem entrega sem contribuição extra, e o plano mostra os caminhos vermelho e azul. O motor segue sabendo calcular o verde para um snapshot que já o traga, mas o aplicativo não o produz mais.

### RF-441. Mesa de conferência do revisor (2026-10-23)
A tela de conferência vira um painel de análise: faixa de indicadores, análise financeira, dívidas do plano, ponto de partida, mudanças, dados de entrada e, ao lado, apoio à decisão (método, pendências, fontes, registro de homologação, sinais). Só apresentação: mesmas APIs, cálculos e regras de homologação; dado ausente aparece como "não disponível". A seção "Plano como o aluno vai ver" sai da tela: o revisor confere o plano pelo botão "Abrir prévia do aluno" (PDF em nova aba).

### RF-442. Indicadores e dívidas da conferência (2026-10-23)
- **Faixa:** Renda total recorrente, Saídas totais do mês, Resultado do mês, Total de dívidas, Total em dívidas e Possui reserva. "Pode ser homologado" sai da faixa (segue no registro de homologação e no bloqueio de "Liberar").
- **Despesas mensais** lê `DESPESAS_OPERACIONAIS_ATUAIS`. O `despesas_mensais_totais` do ponto de partida é receitas − despesas (a sobra), e por isso saía negativo; não serve de despesa. `DESPESAS_NAO_MENSAIS_NORMALIZADAS` vai como linha de apoio, sem somar.
- **Saídas totais do mês** (renda → saídas → resultado fecham): soma, no servidor (`resumo.saidas_totais`), de `DESPESAS_OPERACIONAIS_ATUAIS` + `DESPESAS_NAO_MENSAIS_NORMALIZADAS` + `PAGAMENTOS_MENSAIS_DEVIDOS_VIGENTES`, as mesmas parcelas que o motor desconta em `RESULTADO_MENSAL_ATUAL` (o "Resultado do mês" do plano). Renda − saídas = resultado. O card traz o detalhe "Despesas + não mensais + dívidas" já formatado; a tela não soma.
- **Dívidas:** a ordem do plano só leva as dívidas elegíveis. O indicador "Total de dívidas" conta as cadastradas (`estado_inputs.dividas`) e a tabela lista também as que estão fora da ordem (ordem "—", mês de quitação "não disponível"), ligadas por `DIVIDA_ID`.
- **Total em dívidas:** soma dos `SALDO_DEVEDOR_ATUAL` informados, feita no servidor (campo aditivo `resumo` em `GET /api/revisao/caso/{id}`; a tela não calcula). Saldo desconhecido não entra e marca o total como parcial.
- **Reserva:** o card "Total em reserva" mostra o `RESERVA_TOTAL` salvo pelo aluno e, embaixo, só "Uso: …" (`DISPOSICAO_USO_RESERVA`). "Aceita usar" só aparece com valor informado. Sem valor, o card vira "Possui reserva" com o `RESERVA_EXISTE`.

## 9. Non-Functional Requirements

- **Determinismo:** o mesmo caso com os mesmos parâmetros produz o mesmo snapshot (`AC-18` do `app-aluno`).
- **Não inventar dado:** valor desconhecido continua `DESCONHECIDO`; nenhuma regra nova estima.
- **Zero parâmetro no código:** limites e prazos novos nascem em `parameters/`.
- **Compatibilidade de dados:** respostas já gravadas de perguntas removidas ficam no banco, sem leitura e sem quebrar o carregamento.
- **Verificação:** `ruff`, `mypy` e `pytest` (arquivo por arquivo) passam a cada tarefa.

## 10. Edge Cases

- Caso em andamento com respostas a perguntas removidas: as linhas ficam, o código não as lê.
- Caso gravado nos estados removidos (`COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE`, `ACOMPANHAMENTO`): os estados saíram do código (RF-413) depois de conferido, só por leitura, que nenhum caso estava neles. Caso apareça um, a leitura recusa com erro claro; exigiria migração de dados.
- Aluno com link antigo para etapas removidas: resposta clara de recusa, sem erro.
- Dívida sem CET e sem taxa: cálculo bloqueado (RF-407).
- Pergunta pai removida e filha mantida: a filha nunca aparece (conflitos listados na seção 5).

## 11. Assumptions

- As decisões registradas pelo especialista no formulário de revisão são oficiais; observação em branco não é pendência.
- O ambiente é de teste, sem caso real de aluno (informado pelo responsável do produto em 2026-10-14).
- Todo aluno é tratado como renda fixa (servidor público), sujeito à confirmação do especialista.

## 12. Risks

- Reduzir o motor (24 perguntas) pode degradar confiabilidade, risco e ranking de juros.
- Ligar 32 perguntas amplia o escopo do motor, contra o objetivo de reduzir.
- Juntar CET e taxa em um valor compara medidas diferentes (risco aceito).
- Estados legados no banco impediriam remover os três estados sem migração; mitigado por RF-413 (conferência de leitura antes de apagar: nenhum caso neles).

## 13. Out of Scope (fora de escopo desta spec)
Implementação de código, edição dos YAML e mudança de parâmetros `P_*`.

### RF-412. Regras do especialista já confirmadas, ligadas ao motor (decisão de 2026-10-15)
Entram só as regras que o especialista escolheu com instrução clara. Tudo o que ficou em dúvida ou sem instrução **não é implementado** (ver "Fora desta entrega").
- **Avisos com responsabilidade do aluno:** `B5.E01` (dívida atrasada: "Esta dívida está atrasada. Procure o credor para negociar antes de qualquer outra coisa."), `B5.F01` (dívida com garantia) e `B5.00` (faltam fichas de dívida; o aviso é acrescentado e o **bloqueio já existente por fichas faltando é mantido**, `RF-87` do `app-aluno`, conforme RF-414). Todo aviso termina com "A responsabilidade pela informação é do aluno." A ordem do plano não muda.
- **Conferência do mês (`B3.C00`):** se a resposta não confere, bloqueia o avanço e exige indicar quais rendas ou despesas não estão condizentes.
- **Sobra e falta (`B3.C02A` e `B3.C02B`):** compara com o resultado mensal calculado; qualquer diferença é mostrada ao aluno, que aceita a diferença ou revisa. Etapa didática, sem limite.
- **Contribuição familiar (`B3.04A`):** soma à renda disponível e o plano mostra ao aluno que essa renda está sendo considerada.
- **Plano:** mostra quanto das despesas é fixo e quanto é variável (`B3.DF02`) e o campo "Despesas mensais totais (receitas totais − despesas totais)".
- **Só exibição:** credor (`B5.A01`), vínculo (`B5.A02V`) e data da informação (`B5.I03`, só ao revisor).

**Fora desta entrega (pendente):** regras de ordem `B5.E03`, `B5.F02`, `B5.F03`, `B5.H03`, `B5.H04` (faltam precedência e pesos), `B3.02A` (conflita com `B3.02`) e tudo marcado como dúvida.

### RF-413. Excluir de vez o pós-entrega do plano (decisão de 2026-10-15)
Os estados `COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE` e `ACOMPANHAMENTO` saem do código (enum `ESTADO_CASO`, testes, textos e tipos do frontend). `PLANO_LIBERADO` segue terminal. Antes de apagar, conferir (somente leitura) que nenhum caso está nesses estados. Também: `QUESTIONARIO_VERSION` sobe para `1.3.0` (perguntas novas B3.C00A e B3.C02C) e o rótulo faltante de `ItemInvestimento.LIQUIDEZ_INVESTIMENTOS` é corrigido (falha antiga de teste, resquício da remoção do Bloco 4).

### RF-414. Situação do pagamento da dívida sem "Não sei" (decisão de 2026-10-16)
A pergunta `B5.E01` ("Como está o pagamento desta dívida hoje?") deixa de aceitar "Não sei": ou a dívida está atrasada ou não está. A opção `NAO_SEI` sai do registro e a pergunta passa a ser obrigatória sem exceção. As demais opções ficam como estão (`EM_DIA`, `VENCIDO`, `PARCIAL`, `SEM_PAGAMENTO_REGULAR`). O aviso de dívida atrasada (RF-412) segue valendo para `VENCIDO` e `PARCIAL`. Decisões confirmadas na mesma data: publicar já, sem esperar o especialista; manter o bloqueio de "fichas faltando" (`RF-87`; o aviso de RF-412 se soma a ele, não o substitui); aprovados os textos propostos na entrega de RF-412; o formulário único segue para o especialista.

### RF-415. Textos de valor exato aprovados e data da informação ao revisor (decisão de 2026-10-16)
O responsável do produto aprovou, sem ajustes, as redações propostas na tabela de RF-408 para `B3.01`, `B3.03B`, `B3.04A`, `B3.C01`, `B3.C02A`, `B3.C02B`, `B2.10`, `B4.01A` e `B4.02A`. `B5.C06A` troca só o texto, para "Qual foi a média mensal paga nos últimos 3 meses, conforme o extrato?"; os três campos de valor ficam para depois, por mudar o motor. `B3.02A` segue em suspenso. A pergunta `B5.I03` (data da informação) passa a aparecer na tela do revisor, só como informação. O teste de acessibilidade com navegador roda depois, no ambiente do servidor. Autorizados: teste de mesa e revisão final da branch.

### RF-416. Correções do teste de mesa e da revisão final (2026-10-16)
- O plano e a FAQ não mencionam refazer o plano, "Gerar um novo plano" nem acompanhamento (RF-409); o texto "para você acompanhar e guardar" do anexo mês a mês vira "para você consultar e guardar".
- Os números do plano de quem fecha o mês no negativo fecham entre si (resultado do mês, despesas, parcelas de dívida, incluída a do cartão rotativo); se a causa for de cálculo, vira ocorrência separada e não é corrigida no motor sem decisão.
- Artefatos SDD em dia: plano (rastreabilidade RF-411 a RF-416, T-396 a T-403), contador e status das tarefas, contradições da spec (RF-409 × RF-413, B5.00, AC-402/405/406, datas) e regras normativas das funções novas do motor na spec do motor (§16.2 despesas, §16.3 percepção).
- Restos de texto dos blocos 7, 8, 10 e 11 e de "acompanhamento" são limpos onde não têm efeito em execução.

### RF-417. Decisões do teste de mesa (2026-10-16)
- No modo estabilização (mês no negativo), o plano mostra também os avisos de dívida atrasada (`B5.E01` vencida ou parcial) e de garantia (`B5.F01`), cada um com "A responsabilidade pela informação é do aluno.", sem cronograma.
- `B3.C00` deixa de aceitar "Ainda não consigo avaliar": só Sim, "falta despesa" ou "valor errado".
- O resultado do mês exibido no plano usa as parcelas efetivamente pagas, de modo que os números da tela fecham entre si.

### RF-418. Última rodada do especialista e decisões do produto (2026-10-16)
**Saem do questionário e do cálculo** (decisão do especialista, levantamento do efeito no motor feito antes): `B1.02`, `B1.05`, `B1.10`, `B9.04`, `B2.01`, `B2.02`, `B2.03`, `B2.04`, `B2.05`, `B2.07`, `B3.02`, `B3.02A`, `B3.05A`, `B3.NM02D`, `B3.S01` (com as perguntas que só existem por causa dela) e `B5.C07`. A montagem (`app/montagem/`) passa a entregar valores neutros no lugar das respostas, sem alterar `engine/`:
- Risco de recaída e abandono: `B1.02` → `NAO`; `B1.10` e `B9.04` → `TALVEZ`; janela da nova dívida → `None`.
- Perfil de controle: `REGISTRO_GASTOS=PARTE`, `FREQUENCIA_REGISTRO=INDEFINIDA`, `DEFASAGEM_REGISTRO=DIAS_DEPOIS`, `COBERTURA_PEQUENOS_GASTOS=ALGUNS`, `COBERTURA_MEIOS_PAGAMENTO=QUASE_TOTAL`, `GASTOS_NAO_IDENTIFICADOS=ALGUMAS_MES`. Com isso o nível de controle fica `PARCIAL` (ou `FRAGIL` se `B2.06` ou `B2.12` indicarem) e a confiabilidade dos dados fica `MEDIA`; "forte" e "alta" deixam de existir. Corrige de passagem o erro de quem responde que não registra gastos.
- Tipo de renda: `RELATIVAMENTE_ESTAVEL` para todos (aceito pelo produto: quem tem renda variável perde a redução de 20% na margem de segurança).
- Extraordinário: sem tipo, a ficha vira sempre `B3.05B` e o aluno informa o valor total esperado (aceito pelo produto).
- Despesa não mensal: a proteção contra dupla contagem passa para o texto de `B3.NM02A` e `B3.NM02B` ("só inclua despesas que não estão nas despesas mensais já informadas"); o comportamento do código passa a ser sempre "não contabilizada" (decisão do produto, risco de dupla contagem fica com o aluno).
- Linha de crédito contínua (`B5.C07`): permanece `DESCONHECIDO`, sem efeito.

**Ficam** (decisão do produto): `B4.03` e `B4.03A`, com texto direto: "Aceitaria usar parte da reserva para quitar as dívidas?" e "Qual valor?". `B4.I01` fica como está até o especialista enviar o texto de orientação.

**Sim ou Não direto:** sai o "Não sei" de `B4.01`, `B4.04`, `B5.B05` e `B5.FIM02` (decisão do especialista).

**Regras de ordem das dívidas** (decisão do especialista, com a leitura do produto): a prioridade é bem essencial (`B5.F03`), dívida negativada (`B5.E03`), peso por tipo de garantia (`B5.F02`, imóvel 3, veículo 2, outros 1), urgência soma 20% ao peso emocional (`B5.H03`) e, se a diferença de custo for de até 5%, o aluno escolhe a primeira (`B5.H04`). Exige regra normativa nova na spec do motor.

**Mês no negativo:** o plano mostra o passo de equilibrar o mês e quanto falta cortar para chegar a zero.

### RF-419. Limpeza antes da publicação e resultado do mês no negativo (2026-10-16)
- No plano de estabilização, "o resultado do seu mês é de" usa o resultado estrutural do motor (`RESULTADO_MENSAL_ATUAL`, o mesmo que ativa o modo e que gera "quanto falta cortar"), e os números da tela fecham entre si.
- Limpeza: código e testes sem origem depois da saída de `B3.S01` e `B5.A02V` (pendências de vínculo no inventário, exibição do vínculo no plano, escopo `VINCULO_ID` se não houver outro uso) e testes de banco desatualizados (`test_retomada.py`, `test_rota_resposta.py`) que citam perguntas removidas.
- Casos de teste que aguardam revisão no banco ficam como estão (decisão do produto).
