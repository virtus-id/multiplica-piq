# Respostas do Marcelo — cálculo da 4ª informação da dívida (2026-11-06)

Registro das respostas do especialista. As perguntas 1, 8, 14 e 15 repetiam decisões de 2026-11-03; a 16 era técnica (decisão da equipe).

## Parte A — Regras financeiras (parcela estimada de 24 meses)

**1.** Dívida sem prazo e sem pagamento informado: 24 meses só na prioritária, demais no mínimo?
**Resposta:** Não. Para criar o plano de quitação é preciso um horizonte temporal: se o aluno não informou prazo e pagamento, parte-se de 24 meses. O PIQ pode recomendar ampliar ou reduzir esse prazo no plano.
→ Substitui a "Opção A" de 2026-11-03: toda dívida sem prazo e sem pagamento usa a parcela de 24 meses. A recomendação de ampliar/reduzir é feature nova (backlog).

**2.** Habitual não informado: "devido" = R$ 0,00, com aviso de que não é zero declarado?
**Resposta:** Sim.

**3.** Capacidade de ataque reduzida ao caixa observado?
**Resposta:** Se o aluno declara atacar mais do que sobra, usa-se o valor declarado, e o fato é informado ao aluno no plano.

**4.** Mostrar o caixa negativo ao aluno? **Resposta:** Sim.

**5.** Parcela de 24 meses independe do cenário conservador? **Resposta:** Sim.

## Parte B — Limites e arredondamentos

**6.** Saldo e taxa calculados para baixo; parcela e prazo para cima. **Resposta:** Sim.

**7.** Limites: taxa 100% a.m., prazo 480 meses, saldo e parcela até R$ 1.000.000.000,00. **Resposta:** OK.

**8.** R$ 10.000, 2% a.m., 24 meses ⇒ R$ 528,72. **Resposta:** OK.

**9.** Ponto decimal ("1234.56", "12.5") recusado; "1.234" = 1234; "1.234,5" = 1234,50. **Resposta:** Está certo.

**10.** Parcela "0,00" válida, fora do cálculo; com os quatro valores, acusa incompatível. **Resposta:** OK.

**11.** Price/SAC deixa de ser obrigatório? **Resposta:** O sistema de amortização (Price/SAC) é obrigatório. O padrão é Price.

## Parte C — Dívida pendente e plano parcial

**12.** Liberar o plano parcial ao aluno? **Resposta:** Libera o plano e aponta a pendência de informação para o aluno no plano criado.

**13.** Dívida não prioritária sem mínimo nem habitual fica fora do plano? **Resposta:** Não. Tem que entrar no relatório.

## Parte D — Cenário conservador

**14, 15, 16.** **Resposta:** Não entendeu o contexto.
→ 14 e 15 são as decisões 6 e 7 dele de 2026-11-03 (mantidas). 16 é decisão técnica da equipe (marcas derivadas das respostas atuais, `OQ-90`).

---

# Nova pergunta (2026-11-10) — efeito das respostas 1 e 2 juntas

Não repete as anteriores: é o que aconteceu num caso real quando as respostas 1 e 2 se combinaram.

**17.** Quando o aluno não informa prazo nem quanto paga, o plano usa a parcela de 24 meses para quitar a dívida (resposta 1). Já a conta que diz se o mês fecha e se a dívida cresce usa R$ 0,00 para essa mesma dívida (resposta 2). Com isso, o plano mostra ao aluno duas contas diferentes do mesmo mês.

*Exemplo (caso de teste `aluno.teste3`):* sobram R$ 535,07 no mês. O aluno não informou quanto paga no cheque especial, e a parcela de 24 meses dá R$ 1.449,42. O plano diz ao mesmo tempo:
- "Seu mês fecha positivo: ficam R$ 535,07 livres", porque conta o cheque especial como R$ 0,00;
- "Com os pagamentos considerados neste plano, o seu mês fecha em R$ -914,35", porque conta a parcela de 24 meses.

Para essa dívida, o "quanto você deveria pagar" deve ser também a parcela de 24 meses?
- **(a) Sim (recomendado).** O plano passa a ter uma conta só. Neste exemplo, ele diria "seu mês fecha em R$ -914,35; faltam cortar R$ 914,35". Quando a parcela couber no mês, o aluno recebe o plano de quitação em 24 meses. O aviso "consideramos R$ 0,00" deixa de existir para essa dívida.
- **(b) Não.** Fica como está, com as duas contas na tela.

**Resposta (2026-11-10):** opção (a), a recomendada.

# Texto novo para conferir (2026-11-10)

Quando o aluno informa um valor extra maior do que sobra no mês, o sistema não consegue usar o valor inteiro: o plano usa o que cabe no mês. O aviso antigo dizia "O plano mantém o valor que você informou", e isso não era verdade. O texto passa a ser:

> "O valor extra que você informou (R$ 500,00) é maior do que sobra no seu mês (R$ 400,00). O plano usa R$ 380,00 por mês."

(O valor usado fica um pouco abaixo da sobra por causa da margem de segurança que o plano já aplica.)

---

# Devolução sobre o plano do `aluno.teste3` (2026-11-13)

Marcelo revisou a prévia do plano do `aluno.teste3` (89 páginas) e listou 8 problemas. A maioria é texto que diz algo que o cálculo não faz, e já foi corrigida sem depender de resposta (itens 2, 4 a 8: ver `RF-542`). Os itens 1 e 3 vêm de uma regra que ele mesmo definiu em 16/10 (`§16.4`), e o texto do plano não contava essa regra — também corrigido. Mas essa regra pode precisar de revisão, e é isso que a pergunta 18 traz.

**18.** A `§16.4` faz a dívida com garantia de um bem essencial (ex.: a casa, no financiamento imobiliário) ser atacada **antes** de comparar juros, mesmo que ela seja a mais barata. No `teste3`, isso significa: o imóvel (0,949% a.m.) recebe todo o valor extra do plano, e o cheque especial (5% a.m., negativado) nunca recebe nada — ele só termina porque a própria parcela, sozinha, já paga a dívida. Conta do Marcelo: manter o valor extra no cheque especial em vez do imóvel economizaria cerca de R$ 43,34 de juros já no mês seguinte (sobre R$ 1.031,37, pela diferença de taxas). Ao longo de décadas de financiamento imobiliário, esse tipo de escolha custa muito mais.

A regra continua assim mesmo quando a dívida com garantia é a **mais barata** do caso (como no teste3)?
- **(a) Sim, mantém a `§16.4` como está.** Garantia de bem essencial continua vindo antes de qualquer comparação de juros, mesmo perdendo dinheiro no total pago. O texto do plano (já corrigido) explica esse motivo ao aluno.
- **(b) Não. A prioridade por garantia só decide empate entre dívidas de custo parecido** (dentro da margem de `P_DIFERENCA_CUSTO_EQUIVALENTE`, que já existe na `§16.4`), e fora dessa margem o método volta a decidir por juros/valor. Muda a ordem de ataque de todos os casos com garantia e exige mudança de motor.
- **(c) Não. A prioridade por garantia vale só para evitar execução/perda do bem** (ex.: atraso, risco de leilão), não para toda dívida com garantia essencial desde o primeiro mês. Também muda a ordem e exige mudança de motor.

**19.** A reserva (`§13.1`/`§13.6`): hoje o cronograma do plano nunca usa a reserva — ela é só informação mostrada ao aluno, que decide por conta própria se e quando usar (texto já corrigido para não prometer o contrário). O Marcelo esperava ver a reserva entrando no cronograma como um abatimento de uma vez (ex.: mês 1, amortizando a dívida que o método escolher). Isso é um cálculo novo, de motor, e não existe hoje.

O cronograma deve passar a usar a reserva (todo ou parte do que o aluno aceitou liberar) como um abatimento automático em alguma dívida?
- **(a) Não, mantém como está.** Reserva é informação para o aluno decidir por conta própria; o plano nunca conta com ela.
- **(b) Sim.** Precisa de regra: quanto (tudo que foi aceito liberar, ou um valor que ainda proteja uma reserva mínima?), em que mês e em qual dívida (a mesma do método, ou a de maior taxa?). Feature nova, de motor, com spec própria.

# Textos novos para conferir (2026-11-13)

Corrigidos sem depender das respostas 18/19 (prioridade confirmada por regra já existente, não por decisão nova):

- A explicação da posição ganha uma terceira variante, usada só quando a `§16.4` prioriza a dívida (garantia essencial, negativada, com garantia ou com preferência de quitação declarada), por método:
  > **Avalanche:** "Esta dívida tem garantia de um bem essencial, está negativada, ou você marcou que seria uma das primeiras a quitar — e o plano prioriza isso antes de comparar os juros. Por isso ela é atacada primeiro, mesmo que não seja a que mais cobra juros entre todas as suas dívidas."
- "Como o seu plano funciona" (Avalanche) ganha a mesma ressalva: "Antes de comparar os juros, o plano prioriza a dívida com garantia de um bem essencial, negativada ou com preferência de quitação declarada. Todo o valor extra vai primeiro para ela, mesmo que não seja a que mais cobra juros. As outras recebem só a parcela de sempre."
- Reserva: "Esse é o valor da sua reserva que você decidiu poder usar neste plano, se quiser. O cronograma mostrado não conta com esse dinheiro: ele usa só as parcelas e o valor extra do seu orçamento. Usar a reserva é uma decisão sua, a qualquer momento." e, abaixo do valor, "Reserva total guardada: R$ X."
- Plano provisório por cadastro incompleto (fora de estabilização): "Este plano é provisório: o cadastro das suas dívidas ainda não está completo, e por isso ele será ajustado quando você completar as informações que faltam."
- Capa, quando falta cadastrar dívida: "Considerando só as N dívidas cadastradas e as hipóteses indicadas, a projeção termina em {mês}. A inclusão da dívida que falta pode mudar esse resultado." (só quando o cronograma termina dentro do horizonte de 10 anos; sem o estouro do horizonte, que tornaria "termina em" falso.)
- Parcela calculada ou estimada, no cartão da dívida: sufixo "(calculada a partir do saldo e da taxa)" ou "(estimativa de 24 meses, sem informação sua)" depois do rótulo, quando a marca existe; parcela informada pelo aluno continua sem sufixo.
