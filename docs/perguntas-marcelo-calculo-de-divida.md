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
