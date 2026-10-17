# Spec: fila do revisor em tabela, com filtros e histórico

> Origem: pedido do responsável do produto em 2026-10-16. A fila atual é uma lista de cartões que mostra só os
> planos aguardando revisão: sem filtro, sem ordenação, sem nome do aluno e sem data de chegada.

## 1. Overview (contexto e objetivo)

O revisor precisa enxergar, numa única tela, os planos que chegaram para ele, os que já foram entregues e os que
foram devolvidos ao aluno, com a data de chegada e as informações que mostram o que merece atenção primeiro.
A tela passa a ser uma **tabela com filtros, ordenação e paginação**. Não muda a regra de revisão (liberar ou
devolver), o motor nem o esquema do banco.

## 2. Functional Requirements (requisitos)

### RF-501. Lista unificada de casos que já chegaram ao revisor
Nova consulta `GET /api/revisao/casos`, só para o papel revisor (401 sem sessão, 403 sem o papel). Devolve os casos
que **já chegaram ao revisor** (decisão do produto): em revisão (`AGUARDANDO_REVISAO`), entregues
(`PLANO_LIBERADO`), devolvidos ao aluno (`REPROVADO_EM_REVISAO`) e com erro de cálculo (`ERRO_DE_CALCULO`) que já
tiveram plano enviado à revisão. Casos ainda em coleta pelo aluno não aparecem. A consulta aceita filtros,
ordenação e paginação no servidor. A rota antiga `GET /api/revisao/fila` continua funcionando.

### RF-502. Colunas da tabela
Aluno (nome e e-mail; sem nome, só o e-mail), Chegou em (data e hora de entrada na fila), Tempo na fila, Status,
Tipo (primeiro plano ou recálculo, com o motivo), Situação do mês (fecha positivo ou mês no negativo), Dívidas
(quantidade), Método (recomendado e se está confirmado ou em dúvida), Motivo da revisão, Revisor e decisão (quem
decidiu e quando, só para entregues e devolvidos) e Ação (abrir).

### RF-503. Data de chegada e tempo na fila
A data de chegada é o momento em que o caso entrou em `AGUARDANDO_REVISAO` pela última vez (evento de transição);
se o caso não tiver o evento, vale a data de criação do plano calculado e a tela mostra isso de forma discreta.
O tempo na fila é calculado entre timestamps de eventos, nunca por aritmética sobre campos do snapshot. Para
entregues e devolvidos, mostra o tempo até a decisão.

### RF-504. Abas de status e busca (ajustado em 2026-10-17)
Abas: Pendentes (em revisão), Entregues, Devolvidos, Todos, cada uma com contagem. Único filtro da tela: busca por
nome ou e-mail, na mesma linha das abas, ao lado delas. Os demais filtros (período, tipo, mês no negativo, método,
motivo, revisor, tempo parado) e o filtro de status separado saíram da tela por decisão do produto; a consulta do
servidor continua aceitando esses parâmetros. O termo de busca fica guardado ao recarregar a tela.

### RF-505. Ordenação, paginação e alerta de atraso
Cabeçalhos ordenáveis (padrão: mais antigo primeiro nos pendentes e mais recente primeiro nas demais abas).
Paginação de 25 ou 50, com "mostrando N–M de T". Um pendente parado há **5 dias ou mais** é destacado com ícone e cor; a coluna mostra só os dias (por exemplo "9 d"),
sem frase de alerta (ajustado em 2026-10-17). O alerta tem nome acessível para leitor de tela.

### RF-506. Quem decidiu
Nos entregues e devolvidos, a tabela mostra o autor da decisão e a data (`revisoes.autor`, `decidido_em`). Não há
atribuição prévia de revisor (fora de escopo).

### RF-508. Tabela fina e compacta (2026-10-17)
Linhas de uma linha só, com espaçamento e fonte reduzidos, de modo que a tabela caiba na largura da tela do revisor em
desktop sem rolagem horizontal. Aluno mostra nome e e-mail em linhas curtas; colunas de texto longo usam reticências.

### RF-507. Layout e acessibilidade
Tabela com cabeçalho fixo, linha inteira clicável e botão "Abrir"; a partir de 768px de largura vira cartões
empilhados, sem rolagem horizontal a 360px. Cabeçalhos ordenáveis com `aria-sort`; estados de carregando, vazio e
erro mantêm os papéis ARIA atuais; ícones só pelo componente do projeto, nunca como único portador de sentido. Os
rótulos vêm do servidor, sem códigos do motor na tela, e os sinais "Política 100%" e "Revisão obrigatória pelo
motor" continuam separados.

## 3. User Stories

- Como revisor, quero ver todos os planos que chegaram, com a data e o tempo parado, para atender primeiro o mais
  antigo.
- Como revisor, quero filtrar por status, aluno e período para encontrar um plano específico.
- Como responsável do produto, quero ver quais planos foram entregues, por quem e quando.

## 4. Acceptance Criteria

- AC-501: um não revisor recebe 401 ou 403 em `GET /api/revisao/casos`; um revisor recebe só casos que já chegaram
  à revisão.
- AC-502: a resposta traz nome, e-mail, data de chegada, tempo na fila, status, tipo, situação do mês, dívidas,
  método, motivo, revisor e decisão, com rótulos humanos (nenhum texto em MAIÚSCULAS_COM_UNDERSCORE na tela).
- AC-503: filtros, ordenação e paginação do servidor funcionam e se combinam; a contagem das abas bate com a lista.
- AC-504: a data de chegada de um caso devolvido e reenviado é a da última entrada na fila.
- AC-505: um pendente com 5 dias ou mais aparece destacado (ícone e cor) e a coluna mostra só os dias; com menos, não.
- AC-508: a tela só tem a busca como filtro, ao lado das abas; a tabela cabe na largura do desktop e as linhas são compactas.
- AC-506: a tela não tem rolagem horizontal a 360px e passa nos testes de acessibilidade e de padrões visuais.
- AC-507: a rota antiga da fila e as telas de conferência do caso continuam funcionando.

## 5. Non-Functional Requirements

- Sem alteração em `engine/`, em `persistencia/supabase/repositorio_snapshots.py` nem no esquema do banco.
- Consultas em lote (sem uma consulta por linha); resposta em até 1 segundo para centenas de casos.
- Revisor continua sendo o papel `contas.e_revisor`, lido do banco em cada requisição.
- Textos novos exigem aprovação do produto (rótulos canônicos).

## 6. Edge Cases

- Aluno sem nome cadastrado: mostra o e-mail.
- Caso sem evento de entrada: usa a data do plano calculado.
- Caso reenviado depois de devolvido: vale a última entrada.
- Nenhum caso nos filtros: estado vazio com "Limpar filtros".
- Erro 401 e 403: mensagens atuais.

## 7. Assumptions

- Nome e e-mail do aluno existem em `contas` (`nome` pode ser nulo).
- O último plano calculado do caso traz método, dívidas e situação do mês.
- Um único revisor implícito (`OQ-03` do app-aluno).

## 8. Risks

- Casos antigos sem evento de entrada na fila: mitigado pela data do plano calculado.
- Volume de casos cresce: mitigado por paginação e consultas em lote no servidor.

## 9. Out of Scope

- Casos ainda em coleta pelo aluno (aba "Em andamento").
- Exportação em CSV.
- Atribuir um plano a um revisor específico.
- Qualquer mudança no motor, no esquema do banco ou na regra de liberar ou devolver.
