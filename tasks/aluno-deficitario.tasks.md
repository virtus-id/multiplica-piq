# Backlog — aluno deficitário

| Campo | Valor |
| ----- | ----- |
| Slug  | `aluno-deficitario` |
| Spec  | [`specs/aluno-deficitario.spec.md`](../specs/aluno-deficitario.spec.md) |
| Plano | [`plans/aluno-deficitario.plan.md`](../plans/aluno-deficitario.plan.md) |

> Numeração contínua (última: `T-433`). Nada daqui é ativado em produção antes das `OQ-1` a `OQ-6`.

### `T-434` — Verificar o motor em déficit (gate)
- **Rastreia:** `RF-446`, `RF-448`, `RF-449`
- [x] Rodar o motor, em leitura, sobre os casos deficitários reais e registrar o que acontece com ataque conservador negativo no ciclo mensal (ordem, prazos, saldos). Decide se o motor precisa de ajuste (com spec do motor) antes dos cenários.
- **Resultado (2026-10-23, 2 casos deficitários dos 6 com plano, só leitura):** o motor roda sem erro e devolve ordem (9 e 1 dívida) e método. `CAPACIDADE_ATAQUE_ATUAL = 0`, mas a `CAPACIDADE_ATAQUE_CONSERVADORA` sai negativa (-9.029,74 e -1.194,78). O cenário recomendado fica com prazo 120 (teto do horizonte) e `ESTOUROU_HORIZONTE = True`: o plano "não quita em 10 anos", e o custo futuro vem de uma simulação com ataque negativo ou zero, então **não serve** como projeção de pagamento viável. O prognóstico "sem ação" mostra saldo de 4.710,18 em um caso e de 30.813.818,69 no outro após 120 meses (juros sobre parcelas que não cobrem os juros, sem financiar o déficit).
- **Consequência:** os cenários de 5% e 10% devem ler o resultado ajustado e a capacidade de aporte; enquanto a capacidade for ≤ 0, o cenário não pode exibir prazo, custo nem fichas mensais (RF-450). O saldo de milhões do "se nada mudar" precisa de nota de limitação (juros compostos sobre parcela insuficiente) antes de ir ao aluno.

### `T-435` — Parâmetros 1.0.3 (5% e 10%)
- **Rastreia:** `RF-448`
- [ ] JSON 1.0.3, esquema, migração SQL e semeadura; troca de `PARAMETROS_VERSION_VIGENTE` só na ativação.

### `T-436` — Classificação e cenários de economia no motor
- **Rastreia:** `RF-446`, `RF-448`, `RF-449`, `RF-454` · **Dependências:** `T-434`, `T-435`
- [ ] `calcular_cenarios_economia`; campo opcional no snapshot; persistência tolerante.

### `T-437` — Apresentação do deficitário (relatório e PDF)
- **Rastreia:** `RF-447`, `RF-450`, `RF-451`, `RF-453` · **Dependências:** `T-436`
- [ ] Bloco do deficitário, texto versionado com aprovação, PDF condicional sem fichas inviáveis.

### `T-438` — Conferência do revisor
- **Rastreia:** `RF-452` · **Dependências:** `T-436`
- [ ] Bloco na API e na tela; déficit não é pendência.

### `T-439` — Aviso ao aluno antes do envio
- **Rastreia:** `RF-453`
- [ ] Mensagem quando o resultado do mês é negativo, sem bloquear o envio.

### `T-440` — Aulas
- **Rastreia:** `RF-451` · **Dependências:** `OQ-4`
- [ ] Integrar o mapeamento aprovado ao catálogo real.
