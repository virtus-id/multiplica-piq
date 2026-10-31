# Spec: tratamento do aluno deficitário

> Origem: reunião de 13 de outubro de 2026 (Rodrigo Chebli) e o pedido do produto de 2026-10-23.
> Estado: **rascunho para aprovação**. Nenhuma regra financeira nova é ativada em produção sem a decisão marcada em `Open Questions`.
> **Decisão do produto de 2026-10-29:** o que o aluno vê é um plano **provisório** que manda **estancar primeiro** (RF-468 a RF-470). Os cenários de 5% e 10% (RF-448/449) ficam só na conferência do revisor e **não vão ao aluno**; por isso as `OQ-1`, `OQ-2`, `OQ-3`, `OQ-5` e `OQ-6` deixam de bloquear a entrega ao aluno.

## 1. Overview

Hoje o aluno com resultado mensal negativo (`MODO_ESTABILIZACAO`, `RESULTADO_MENSAL_ATUAL < 0`) recebe só o aviso "Primeiro, equilibrar o seu mês" e o "quanto falta cortar" (`RF-418`). O motor já continua e devolve os cenários mesmo em déficit; o relatório é quem esconde ordem, método e prazos. Esta spec entrega ao aluno deficitário: a **ordem recomendada** de quitação, **três cenários** comparáveis (se nada mudar; economia de 5% da renda; economia de 10% da renda), orientações e a conferência do revisor, sem prometer uma quitação que o orçamento não sustenta.

## 2. Princípios

- O déficit não bloqueia o plano nem o envio. Não é pendência de homologação (`homologavel = not pendencias` não muda).
- Ordem recomendada (estratégia) ≠ cronograma executável (depende de caixa). Nunca se apresenta a primeira como garantia da segunda.
- Nenhum valor, taxa, prazo ou comportamento é inventado; o que não se calcula aparece como limitação.
- Cálculo só pelo motor existente. Nada de IA generativa em resultado numérico.

## 3. Functional Requirements

### RF-446. Classificação financeira do caso
O caso é **superavitário** (`RESULTADO_MENSAL_ATUAL > 0`), **equilibrado** (`= 0`) ou **deficitário** (`< 0`), pela definição oficial do motor (renda − despesas − não mensais − parcelas devidas). O snapshot guarda a classificação e o valor do déficit (`DEFICIT_MENSAL`).

### RF-447. Ordem recomendada no déficit
Com a ordem do motor (`ORDEM_QUITACAO`, método recomendado, justificativa por posição), o plano do deficitário mostra a ordem recomendada, o método, o porquê e as premissas, rotulada como **recomendação provisória**, e não como cronograma de pagamento. Sem prazo, sem mês de quitação e sem fichas mensais enquanto a capacidade de ataque for zero.

### RF-448. Três cenários do deficitário
1. **Se nada mudar:** o prognóstico "sem ação" do motor (pagamentos efetivos, sem amortização extra), com suas limitações explícitas. Não presume financiamento do déficit (cheque especial, cartão, empréstimo).
2. **Economia de 5% da renda** e 3. **de 10%:** hipótese de redução de despesas igual a `RENDA_TOTAL_RECORRENTE × percentual`. A economia compensa primeiro o déficit. O motor recalcula o caso com as despesas reduzidas; só havendo resultado positivo existe capacidade de aporte. Cada cenário informa: resultado ajustado, se continua deficitário / equilibrado / com sobra, e os indicadores que o motor conseguir calcular. Percentuais são parâmetros versionados (`P_*`), nunca literais.
Os cenários são **simulação**, nunca plano homologado, e ficam identificados assim no snapshot. **Só o revisor os vê** (RF-452); o aluno não recebe os cenários de 5% e 10%, porque são percentuais fixos que não batem com os números de cada pessoa.

### RF-449. Horizontes de 12, 24 e 60 meses
Quando o motor tem dado e regra, cada cenário mostra, em 12, 24 e 60 meses: resultado do mês, capacidade de aporte, saldo restante, pagamentos e juros projetados e dívidas quitadas. Indicador que o motor não calcula não é exibido. Mês de quitação só com pagamentos viáveis; caso contrário, "não executável" ou "insuficientemente determinado", com o motivo.

### RF-450. Situações A, B e C
A (sem sobra para extra): segue os pagamentos habituais, sem amortização extra. B (déficit com parcelas pagas): registra a limitação de como o déficit é coberto. C (não sustenta os pagamentos): sem trajetória de quitação, com orientação de reorganização. O critério que separa B de C não está definido (`OQ-1`).

### RF-451. Introdução ao aluno e aulas
Texto padrão **versionado**, de autoria do Rodrigo, com variáveis reais (déficit). Só aparece ao aluno depois de aprovado; antes, o aluno vê o aviso atual e o revisor vê o rascunho. Aulas só do catálogo real (`docs/curso-ssd/`), por mapeamento aprovado pelo especialista (`OQ-4`).

### RF-452. Conferência do revisor
A tela do revisor mostra, com dados reais: resultado negativo, déficit, método, ordem recomendada, premissas e resultado dos cenários de 5% e 10%, limitações e o que não está disponível. Déficit não vira pendência. Decisão, observação, mensagem ao aluno e histórico não mudam.

### RF-453. PDF e experiência do aluno
O PDF e a tela do deficitário preservam a identidade do plano e seguem a ordem de RF-468 a RF-470. Não se geram fichas, prazos nem mês de quitação com valores que o aluno não tem como pagar. Ao enviar, o aluno é avisado de que o orçamento não fecha e de que o plano será provisório; o aviso não bloqueia o envio. O aviso aparece ao terminar o cálculo (o servidor só lê o resultado do snapshot), com o mesmo valor do plano, e o aluno segue em "Continuar".

### RF-468. Resultado negativo em destaque e "estancar primeiro"
O relatório do deficitário abre com o resultado do mês em destaque ("Seu mês fecha em -R$ X") e com o título **"Primeiro, estancar o problema"**, que diz quanto falta por mês para chegar a zero (`DEFICIT_MENSAL`, já calculado pelo motor) e que, a partir daí, tudo o que sobrar vira dinheiro de ataque e o plano se ajusta. O texto é canônico, versionado e foi aprovado pelo produto em 2026-10-29.

### RF-469. Onde olhar nos seus gastos
O relatório mostra os 5 maiores gastos que o próprio aluno informou, por item e em ordem de valor, com a orientação da aula 5 de marcar o que dá para reduzir, pausar ou eliminar. Sem percentual nem meta por item inventados; sem juízo sobre o gasto.

### RF-470. Aulas do deficitário
O quadro de aulas do perfil deficitário é **5** (Mapeamento Parte 2), **14** (Voltando a Respirar: Conquistando Sua Primeira Sobra Financeira) e **24** (O Paradoxo "Ganho Bem, Mas Não Sobra Nada"), escolhidas das legendas em `docs/curso-ssd/legendas/`. A aula 19 (reserva) e a 6 (renda extra) saem do quadro do deficitário; a 6 e as 10 e 11 seguem em "Como melhorar o seu plano".

### RF-471. A ordem provisória não é instrução de pagamento
No relatório do deficitário, um aviso explícito e visível diz que a ordem de quitação é uma simulação provisória, não uma instrução para antecipar pagamentos; que as parcelas contratuais e as despesas essenciais continuam sendo pagas; e que o plano executável só é calculado e liberado quando o mês fechar com resultado igual ou maior que zero (ou quando o aluno atualizar as informações). O aviso aparece com ou sem ordem de quitação. Aprovação do texto: pendente do produto (sugestão, a validar).

### RF-472. Conferência de consistência dos números
Antes de apresentar o plano, o relatório confere identidades que o motor garante: renda − despesas − parcelas = resultado do mês; soma dos saldos das dívidas = saldo inicial do prognóstico; em cada mês, início + juros − pago = saldo, habitual + extra = total a pagar e soma por dívida = saldo do mês; ordem sem dívida repetida ou fora do inventário; aporte do cenário acelerado = valor informado pelo aluno. Se alguma falhar, o PDF e a tela mostram o aviso "números não conferidos" e não corrigem nada. Vale para todo plano, deficitário ou não.

### RF-473. PDF do deficitário: um número e uma ação
A primeira página do PDF do deficitário traz o resultado do mês em destaque (um só número: o valor negativo já diz quanto falta para zerar), o texto do problema, "O que fazer agora" em dois passos e o aviso de que a ordem provisória não é instrução de pagamento (RF-471). A apresentação do curso deixa a primeira página (a seção do curso, mais adiante, já faz a ligação). A ordem provisória é uma lista compacta, sem uma caixa por dívida. Só apresentação: nenhum número novo, e as demais seções e os textos aprovados seguem como estão. Textos novos (passos, rótulo) sugeridos, a validar.

### RF-474. Gráficos do deficitário
O PDF do deficitário traz, em SVG: (a) "Para onde vai a sua renda", uma barra com gastos do dia a dia, gastos não mensais e parcelas, a marca da renda e, em vermelho, o que passa dela; (b) barras proporcionais nos 5 maiores gastos. Só desenham números que o plano já tem (`RESULTADO`, `DEFICIT_MENSAL`, respostas do aluno): nenhuma conta nova, nenhum gráfico sem dado, e cada gráfico traz os valores por escrito. A nota do calendário ("os meses seguem o calendário") sai do deficitário, que não tem meses. Rótulos sugeridos, a validar.

### RF-475. Identidade visual moderna do PDF
O PDF (deficitário e não deficitário) usa a fonte Inter, embutida no repositório (`report/fontes/`, licença OFL), em vez das fontes do sistema do servidor (que só tem DejaVu e deixava o PDF com aspecto antigo). Capa em degradê, seções com número em chip e sem sublinhado pesado, cartões em superfície suave sem borda, número do resultado grande. Só apresentação: textos, ordem e números não mudam. O PDF não depende de recurso remoto.

### RF-476. A ordem de quitação em destaque (ranking)
No PDF do deficitário, a ordem de quitação é o bloco de maior peso visual: um ranking em tabela, uma linha por dívida, com a posição em destaque, o nome e os valores de apoio (os mesmos já mostrados) em colunas, e a primeira da fila marcada. Continua sem prazo, sem mês de quitação e sem cronograma, e continua provisória (RF-468, RF-471). Só apresentação. Etiqueta "Começa por esta" sugerida, a validar.

### RF-477. "Seu ponto de partida" como painel, com fechamento
No PDF do deficitário, o ponto de partida deixa de ser uma tabela de linhas e vira um painel de cartões: **renda total recorrente**, **saídas totais do mês** (com os três grupos e as despesas fixas e variáveis), **resultado do mês** (e o resultado antes das parcelas), **total de dívidas**, **total em dívidas** (soma dos saldos informados; marcada como parcial se faltar saldo) e **possui reserva**. Fecha com uma frase: "Entram X e saem Y. O mês fecha em Z." Os números são os mesmos de antes: nada novo é calculado além de somas do que já está no estado. Rótulos sugeridos, a validar. O plano normal usa o mesmo painel (`RF-478`).

### RF-478. "Seu ponto de partida" do aluno no positivo: painel e gráfico
Para o aluno que não está em estabilização, o ponto de partida usa o mesmo painel de `RF-477` (resultado em tom positivo) e traz, acima dele, o gráfico de barras entrada × saída com a legenda de `RF-474`. O cartão de **valor extra** e a nota de segurança continuam onde já havia ataque às dívidas (fora de `ORDEM_VAZIA`). Sem nenhuma fala de problema, falta ou "estancar": só ilustra. A tabela de linhas deixa de existir. Os números são os mesmos de antes (nada novo é calculado).

### RF-454. Rastreabilidade
O snapshot registra classificação, método, percentuais usados, resultados dos cenários, premissas e limitações, sem alterar versões anteriores. Alunos não deficitários não mudam.

## 4. Open Questions (decisões que bloqueiam a ativação)

- **OQ-1.** Critério que distingue a Situação B da C (quando se deixa de projetar pagamentos). *Não bloqueia a entrega ao aluno (2026-10-29): o aluno não recebe projeção de pagamentos.*
- **OQ-2.** Base da renda dos percentuais: `RENDA_TOTAL_RECORRENTE` (proposta) ou outra.
- **OQ-3.** Como representar dívida inadimplente ou em atraso na trajetória "se nada mudar".
- **OQ-4.** Mapeamento aula ↔ perfil deficitário, e aprovação do texto do Rodrigo. *Aulas definidas em RF-470 e texto de RF-468 aprovado pelo produto em 2026-10-29; o Rodrigo ainda pode ajustar a redação.*
- **OQ-5.** Quando um mês de quitação pode ser afirmado no deficitário.
- **OQ-6.** Aplicar a economia por redução de `DESPESAS_OPERACIONAIS_ATUAIS` (proposta) ou outra rubrica.

## 5. Fora do escopo
Novos métodos de quitação, refinanciamento e portabilidade automáticos, contratação de crédito, mudança de fórmulas de juros e amortização.
