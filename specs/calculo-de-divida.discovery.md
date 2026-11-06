# Discovery — `calculo-de-divida`

| Campo | Valor          |
| ----- | -------------- |
| Slug  | `calculo-de-divida` |
| Data  | `2026-11-03`   |
| Origem | Pedido do especialista (Marcelo Brasília) e 3 rodadas de respostas, todas em 2026-11-03 |

## 1. Problema

Hoje a ficha de dívida pede saldo, parcela e taxa como três números digitados de forma independente (`B5.B03`, `B5.C02`, `B5.D06`), e o motor deriva o prazo. Nada garante que os três sejam coerentes entre si: um valor chutado gera uma dívida matematicamente inconsistente, e o diagnóstico e o plano são construídos em cima dela. A única conferência que existe é o aviso `PARCELA_MAIOR_QUE_O_SALDO` (`app/montagem/entrada.py`, RF-479).

Além disso, o aluno frequentemente não sabe a taxa ou o saldo, mas sabe o prazo; e quem tem cartão rotativo ou cheque especial não tem prazo nem parcela contratual, mas o PIQ precisa de uma base de quitação para ordená-la e planejá-la.

## 2. Personas

| Persona | Objetivo | Contexto de uso |
| ------- | -------- | --------------- |
| Aluno do SSD | Cadastrar suas dívidas mesmo sem ter todos os números à mão | Preenche a ficha de cada dívida no diagnóstico, geralmente com extrato ou contrato aberto, às vezes sem eles |
| Revisor | Conferir se os dados do aluno são confiáveis antes de homologar | Vê o que foi informado, o que foi calculado e o que é estimativa |
| Especialista do método | Garantir que o PIQ não contradiga o curso (Rodrigo) | Valida regras de negócio |

## 3. Cenários de uso

- **Sabe saldo, taxa e parcela** — hoje digita os três e o prazo sai do motor; quer o mesmo, com o resultado marcado como calculado e conferido.
- **Sabe parcela, taxa e prazo, não sabe o saldo** — hoje não consegue avançar (saldo é indispensável); quer que o sistema calcule o saldo.
- **Não sabe a taxa** — o caso mais comum; sabe saldo, parcela e prazo do contrato e quer que o sistema calcule a taxa.
- **Digita os quatro e eles não batem** — hoje nada avisa; quer ver o valor teórico e escolher qual informação recalcular.
- **Parcela que não cobre os juros** — quer entender que, naquelas condições, o pagamento não reduz o saldo, e rever os dados.
- **Cartão rotativo / cheque especial com saldo e taxa** — não tem prazo; hoje é obrigado a informar uma "parcela" que muitas vezes é só o pagamento mínimo.
- **Paga o mínimo de uma dívida para quitar outra** — quer registrar o mínimo e o que paga de fato.
- **Não sabe alguma informação da dívida** — hoje fica travado; quer salvar como pendente e seguir preenchendo o resto.

## 4. Restrições

- **Técnicas:** `engine/` congelado (AC-44, `tests/app_aluno/estatica/hashes_congelados.json`). `Divida` não tem campo de prazo e acrescentar um muda o hash de todo snapshot. O motor paga `min(parcela, saldo+juros)` sem tolerância de resíduo. Dois campos de pagamento por dívida: `PARCELA_CONTRATUAL` (devido; alimenta `FALTA_DE_JUROS`) e `PAGAMENTO_MENSAL_EFETIVO` (caixa e simulação). Decimal por `engine.precisao.CONTEXTO_MOTOR`; `float` proibido fora do motor (`app/montagem/conversao.py` é a fronteira). O front não faz conta (Lei nº 3). Snapshots imutáveis (V-01).
- **Negócio:** nada pode contradizer o curso SSD (`docs/curso-ssd/`); a aula 12 ensina "mínimo em todas, extra concentrado em uma". Visual do PIQ preservado; o HTML de referência só serve de interação.
- **Legais / compliance:** dados de dívida são dados pessoais do aluno (LGPD); valor calculado ou estimado precisa ser rastreável e distinguível do informado.

## 5. Definição de sucesso

- Fichas de dívida salvas com os quatro dados mutuamente coerentes, ou sinalizadas como incompatíveis — hoje: nenhuma checagem; meta: 100% das dívidas com status de coerência registrado.
- Alunos que travam na ficha por não saber um dado — hoje: dado indispensável bloqueia a dívida; meta: sem bloqueio, só pendência.
- Dívida sem prazo entra no plano com base de quitação explícita e marcada como estimativa — hoje: depende de uma "parcela" que o aluno chuta.
- Nenhuma alteração em `engine/` (hashes do AC-44 intactos).

## 6. Riscos e incógnitas

| Incógnita | Impacto se der errado | Como reduzir |
| --------- | --------------------- | ------------ |
| Mapear parcela estimada/habitual/mínimo nos dois campos de pagamento do motor | Alerta de dívida que cresce some, ou resultado do mês muda sem aviso | Teste com dívida de exemplo antes de fechar a spec (spike na fase 2) |
| Prazo do plano pode divergir 1 mês da tela por arredondamento | Número diferente entre tela e plano | Arredondar parcela calculada para cima ao centavo (aprovado) |
| Passar a permitir "não sei" nas perguntas de dívida | Bloqueio por obrigatória pendente (`app/casos/progresso.py`) ou gravar zero | Verificar `pendencias_obrigatorias` e AC-08 |
| Cenário conservador só injeta saldo e taxa no motor | Expectativa de que o prazo/parcela do cenário governem o plano | Deixar explícito na spec e no texto ao aluno |
| Bisseção da taxa sem convergência ou resultado absurdo | Taxa inválida salva | Limite de iterações, teto de taxa e erro tratado |
| Remover a restrição de SAC só para imobiliário | Regressão em RF-510/T-465 | Revogar o RF explicitamente e atualizar testes |

## 7. Decisões já fechadas pelo especialista (entradas da spec)

Todas de 2026-11-03.

1. Cálculo de qualquer uma das quatro informações a partir das outras três, em Price (parcela fixa) e SAC (1ª parcela; seguintes decrescentes). Taxa zero válida como entrada e como resultado.
2. Parcela calculada arredondada **para cima** ao centavo; última parcela ajustada. Valor vindo do contrato nunca é alterado.
3. Taxa com 4 casas **só** no cálculo interno: o aluno não digita nem vê 4 casas.
4. Price e SAC para todas as modalidades; Price padrão; a escolha do aluno é preservada e a simulação nunca é apresentada como condição do credor.
5. Tipos de taxa: manter o que o PIQ já tem (mensal ou anual; CET mensal ou anual).
6. Quatro valores incompatíveis: salvar os originais e sinalizar a aluno e revisor; escolher qual recalcular; cenário conservador por ordem (maior parcela, maior saldo, maior taxa, maior prazo, maior custo total); resultado do mês usa o pagamento que o aluno declara.
7. Compatibilidade dos quatro valores: intervalo de arredondamento das entradas.
8. Pagamento mínimo coletado em todas as dívidas, ao lado do habitual; "parcela estimada" sempre separada e marcada.
9. Saldo e taxa sem parcela nem prazo: hipótese de 24 meses para todas as modalidades; prazo contratual ou pagamento informado pelo aluno prevalece (informação do aluno é soberana). Pagamento atual zero ou ausente também usa os 24 meses.
10. Só a dívida **prioritária** recebe a parcela de 24 meses; as demais pagam o mínimo (aula 12 do curso).
11. O alerta de dívida que cresce compara os juros com o pagamento **habitual**.
12. Pagamento que inviabiliza o plano: o plano avisa a inviabilidade e nunca troca o pagamento do aluno; com pagamento informado não se fala em hipótese de 24 meses.
13. "Não sei" permitido nos campos da dívida (nunca vira zero). Dívida pendente fica fora do plano com aviso, o plano das demais continua e é marcado como parcial.
14. Total de juros em R$ só na tela do cálculo. Revisor vê apenas as marcas "calculado" e "estimado".
15. Correções ao HTML de referência: último pagamento calculado, sequência do SAC conferida, escolha de qual informação recalcular, formato brasileiro com milhar, taxa 0 aceita como resultado.

## 8. Perguntas abertas

Nenhuma bloqueia a spec. As leituras abaixo foram adotadas como hipótese e entram na spec marcadas para confirmação.

| ID | Pergunta | Por que importa | Impacto na solução |
| -- | -------- | --------------- | ------------------ |
| `OQ-D1` | "Pagamento atual informado" significa pagamento habitual > 0? Zero ou vazio dispara os 24 meses (hipótese adotada) | Define quando a hipótese se aplica | médio |
| `OQ-D2` | "Inviável" = pagamento ≤ juros do mês ou resultado do mês negativo (hipótese adotada) | Define o texto e quando o aviso aparece | médio |
| `OQ-D3` | Qual é a dívida prioritária para a regra dos 24 meses: a dívida-alvo da ordem do motor (hipótese adotada) | Define em qual dívida a parcela estimada vale | alto |
| `OQ-D4` | Os 24 meses valem também para dívida de parcela fixa quando o aluno não sabe parcela nem prazo (decisão 9 diz que sim) | Pode contrariar o contrato real | baixo |

> Discovery levanta o problema. Não decide a solução — isso é a spec.
