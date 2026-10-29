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
- [x] `parameters/parametros-1.0.3.json` (`P_ECONOMIA_RENDA_CENARIO_1 = 0.05`, `_2 = 0.10`; `ENGINE_VERSION` segue `1.0.2`), esquema com as duas chaves **opcionais** (1.0.1 e 1.0.2 continuam válidas), migração `011_parametros_economia.sql` (colunas `NULL`) e `fonte_parametros` do Supabase ignorando coluna nula.
- [ ] **Ativação (fora do código, em produção):** aplicar a migração 011, rodar `scripts/semear_parametros.py --versao 1.0.3` e só então trocar `PARAMETROS_VERSION_VIGENTE`. Não feito: depende das OQ-1 a OQ-6.

### `T-436` — Classificação e cenários de economia no motor
- **Rastreia:** `RF-446`, `RF-448`, `RF-449`, `RF-454` · **Dependências:** `T-434`, `T-435`
- [x] `engine/cenarios_economia.py::calcular_cenarios_economia` (o motor recalcula com `DESPESAS_OPERACIONAIS_ATUAIS` reduzida em renda × percentual; sem fórmula nova), chamado por `calcular_plano` só em `MODO_ESTABILIZACAO` e sem recursão; campo opcional `SnapshotOrdem.cenarios_economia`; persistência tolerante (Supabase `dados_completos` e leitura em arquivo). Versão de parâmetros sem os percentuais → `None` (nada muda hoje, com a 1.0.2 vigente). Não executável (sem capacidade de aporte) → sem prazo, custo nem saldos. Saldos em 12/24/60 meses só nos executáveis; o "se nada mudar" nos horizontes fica para a T-437.

### `T-437` — Apresentação do deficitário (relatório e PDF)
- **Rastreia:** `RF-447`, `RF-450`, `RF-453`, `RF-468`, `RF-469` · **Dependências:** `T-436`
- [x] Resultado negativo em destaque, "Primeiro, estancar o problema" com o valor para zerar, "Onde olhar nos seus gastos" (5 maiores) e ordem de quitação provisória sem prazo nem fichas, no PDF e na tela. Os cenários de 5% e 10% **não** vão ao aluno.
- **Resultado (2026-10-29):** feito no PDF (`estabilizacao.html`) e na tela (`PlanoDoDeficitario.tsx`). Os maiores gastos vêm das respostas (`maiores_gastos` em `app/http/serializacao_plano.py`). Teste com o caso real do Guilherme: só depois que ele reenviar e o plano for recalculado.

### `T-438` — Conferência do revisor
- **Rastreia:** `RF-452` · **Dependências:** `T-436`
- [x] `deficitario` (aditivo) em `GET /api/revisao/caso/{id}` e `CenariosDoDeficitario` na conferência: resultado, déficit, "se nada mudar", cenários de 5% e 10% com situação, aporte, prazo e saldos, e as limitações. Déficit não vira pendência; ordem recomendada rotulada como estratégia. Os cenários só aparecem com os parâmetros 1.0.3 em vigor.

### `T-439` — Aviso ao aluno antes do envio
- **Rastreia:** `RF-453`
- [ ] Mensagem quando o resultado do mês é negativo, sem bloquear o envio.

### `T-440` — Aulas
- **Rastreia:** `RF-470`
- [x] Quadro do deficitário = aulas 5, 14 e 24 (`textos-canonicos.yaml`), com título e motivo das aulas 14 e 24.
- **Resultado (2026-10-29):** aulas 5, 14 e 24 no YAML. Os títulos oficiais das aulas 14 e 24 trazem "Sobra"; os testes que proíbem a palavra no modo estabilização passaram a ignorar só os títulos das aulas.

### `T-450` — Aviso: a ordem provisória não é instrução de pagamento
- **Rastreia:** `RF-471`
- [x] Bloco `aviso_provisorio` em `estabilizacao` (YAML) e no `estabilizacao.html`; teste em `tests/app_aluno/test_pendencias_do_relatorio.py`.

### `T-451` — Conferência de consistência do relatório
- **Rastreia:** `RF-472`
- [x] `report/consistencia.py::verificar_consistencia`, `aviso_de_conferencia` no contexto, PDF, serialização e tela; testes em `tests/app_aluno/test_consistencia_do_relatorio.py`.
- **Divergência de negócio, não tratada:** `DEFICIT_MENSAL` (o "faltam cortar") usa as parcelas devidas (`PARCELA_CONTRATUAL`), e "Seu mês fecha em" usa as efetivamente pagas. Quando uma dívida paga menos que a parcela, os dois números diferem. Pendente de decisão do produto.

### `T-452` — PDF do deficitário: um número e uma ação
- **Rastreia:** `RF-473`
- [x] `estabilizacao.html` (cartões lado a lado, passos, aviso leve, ordem compacta), CSS em `plano.html`, textos em `textos-canonicos.yaml`; capa do curso fora da primeira página do deficitário.
