# Backlog — aluno deficitário

| Campo | Valor |
| ----- | ----- |
| Slug  | `aluno-deficitario` |
| Spec  | [`specs/aluno-deficitario.spec.md`](../specs/aluno-deficitario.spec.md) |
| Plano | [`plans/aluno-deficitario.plan.md`](../plans/aluno-deficitario.plan.md) |

> Numeração contínua (última: `T-433`). Nada daqui é ativado em produção antes das `OQ-1` a `OQ-6`.

### `T-434` — Verificar o motor em déficit (gate)
- **Rastreia:** `RF-446`, `RF-448`, `RF-449`
- [ ] Rodar o motor, em leitura, sobre os casos deficitários reais e registrar o que acontece com ataque conservador negativo no ciclo mensal (ordem, prazos, saldos). Decide se o motor precisa de ajuste (com spec do motor) antes dos cenários.

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
