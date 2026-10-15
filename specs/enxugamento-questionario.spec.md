# Spec: enxugamento do questionário do PIQ (rascunho gerado das decisões do especialista)

> Fonte única deste documento: as decisões que o especialista registrou no formulário de revisão
> (https://claude.ai/artifact/UAkEhMLLqjzspsfmggSSav), lidas em 2026-10-14 (229 registros).
> Foram tratadas como **oficiais**, conforme orientação do responsável do produto. Observação em branco
> não é pendência. Nada neste documento foi implementado.

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

Decisão de implementação (OQ-1, parte final): **desligar** o fluxo, sem apagar o código das telas e das regras dos Blocos 7, 8, 10 e 11. Os estados `COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE` e `ACOMPANHAMENTO` ficam na máquina e deixam de ser alcançáveis. A remoção do código é uma etapa futura, se o produto se confirmar sem acompanhamento.

### RF-402. Remover do questionário o que o motor não usa (Blocos 1 a 5)

**Situação (2026-10-14):** 87 das 89 listadas foram removidas (T-389). `B3.S03` e `B5.I01` continuam porque perguntas que ficam dependem delas (decisão pendente com o especialista).
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

- **OQ-1 (respondida em 2026-10-14: o produto não tem acompanhamento).** O destino do código foi decidido em 2026-10-14 (RF-409): desligar, sem remover. Antes estava em aberto: os estados `COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE` e `ACOMPANHAMENTO` e o gatilho de recálculo por quitação (V-01) ficam inalcançáveis. Remover esse código ou apenas desligar a coleta?
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
| AC-402 | RF-402 | Dado o registro do questionário, quando carregado, então nenhuma das 87 perguntas removidas existe e a versão é a mesma em todos os arquivos | verificado (T-389) |
| AC-403 | RF-402, RF-410 | Dado um caso de prova, quando as respostas das perguntas removidas são retiradas, então o `EstadoFinanceiro` e o `SnapshotOrdem` são idênticos | verificado (T-389, T-391) |
| AC-404 | RF-410 | Dado um plano, então o PDF e a tela do revisor não mencionam seguro da dívida nem o apontam como informação pendente | verificado (T-391) |
| AC-405 | RF-407 | Dada uma dívida sem CET e sem taxa, quando o cálculo é pedido, então ele é bloqueado | a implementar (T-393) |
| AC-406 | RF-408 | Dada qualquer pergunta que continua pedindo valor, então o enunciado não contém "aproximadamente", "estima", "em média" nem "acredita" | a implementar (T-394) |
| AC-407 | RF-403, RF-404 | Para cada pergunta removida do motor ou ligada a ele existe regra normativa na spec do motor e teste com critério de aceite | a implementar (T-392, T-395) |
| AC-408 | RF-405 | As 6 perguntas indispensáveis para liberar o plano continuam no registro | verificado (T-389) |

## 9. Non-Functional Requirements

- **Determinismo:** o mesmo caso com os mesmos parâmetros produz o mesmo snapshot (`AC-18` do `app-aluno`).
- **Não inventar dado:** valor desconhecido continua `DESCONHECIDO`; nenhuma regra nova estima.
- **Zero parâmetro no código:** limites e prazos novos nascem em `parameters/`.
- **Compatibilidade de dados:** respostas já gravadas de perguntas removidas ficam no banco, sem leitura e sem quebrar o carregamento.
- **Verificação:** `ruff`, `mypy` e `pytest` (arquivo por arquivo) passam a cada tarefa.

## 10. Edge Cases

- Caso em andamento com respostas a perguntas removidas: as linhas ficam, o código não as lê.
- Caso gravado nos estados removidos (`COLETA_DIRIGIDA`, `CONFIRMACAO_ATAQUE`, `ACOMPANHAMENTO`): os estados continuam no enum, sem transição, para não quebrar a leitura.
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
- Estados legados no banco impedem remover os três estados sem migração.

## 13. Out of Scope (fora de escopo desta spec)
Implementação de código, edição dos YAML e mudança de parâmetros `P_*`.
