# Plano Técnico — aluno deficitário

| Campo | Valor |
| ----- | ----- |
| Slug  | `aluno-deficitario` |
| Spec  | [`specs/aluno-deficitario.spec.md`](../specs/aluno-deficitario.spec.md) |
| Status | `rascunho` |
| Data  | 2026-10-23 |

## Decisão central
Os cenários de 5% e 10% **reaproveitam o motor**: `calcular_plano` roda de novo sobre uma cópia do `EstadoFinanceiro` com `DESPESAS_OPERACIONAIS_ATUAIS` reduzida em `RENDA_TOTAL_RECORRENTE × P_ECONOMIA_*`. Nenhuma fórmula de amortização nova. O cenário 1 é o `prognostico.sem_acao` que o snapshot já guarda.

## Fatos do código que sustentam o plano
- `MODO_ESTABILIZACAO = RESULTADO_MENSAL_ATUAL < 0` (`engine/diagnostico.py`); o motor não pula nem falha em déficit (`engine/motor.py`), e o relatório decide a apresentação (`report/plano.py::decidir_cenario_apresentacao`).
- Em déficit, `CAPACIDADE_ATAQUE_ATUAL = 0`, mas `BASE_CONSERVADORA`, `CAPACIDADE_ATAQUE_CONSERVADORA` e `CAPACIDADE_ATAQUE_POTENCIAL` saem negativas, e o ciclo mensal usa a conservadora. **Risco a verificar antes de qualquer projeção**: o que o ciclo mensal faz com ataque negativo (T-434 é o gate).
- Parâmetros `P_*` são versionados (`parameters/parametros-X.json` + `esquema-parametros.json` + coluna no banco + `PARAMETROS_VERSION_VIGENTE`). Os percentuais exigem **nova versão (1.0.3)**: JSON, esquema, migração SQL, semeadura e troca da variável em produção. Versão existente não se edita.
- O snapshot já carrega `prognostico` opcional, com leitura tolerante de snapshots antigos; os cenários seguem o mesmo molde (campo opcional novo, `None` nos antigos e nos não deficitários).

## Componentes
1. **Parâmetros 1.0.3:** `P_ECONOMIA_CENARIO_A = 0.05`, `P_ECONOMIA_CENARIO_B = 0.10`.
2. **Motor (`engine/`):** `cenarios_deficit.py` com `calcular_cenarios_economia(estado, parametros)` (puro): para cada percentual, copia o estado, recalcula o plano e extrai resultado ajustado, classificação, capacidade e prognóstico por horizonte (12/24/60). Só roda com `MODO_ESTABILIZACAO`. Resultado guardado em `SnapshotOrdem.cenarios_economia` (opcional).
3. **Persistência:** serialização/leitura tolerante nos dois repositórios (arquivo e Supabase), como `prognostico`.
4. **Relatório:** `ContextoPlano` ganha o bloco do deficitário (introdução versionada, estratégia, três cenários); `estabilizacao.html` passa a incluí-lo; PDF condicional.
5. **Texto versionado:** `textos-canonicos.yaml` com `deficitario.introducao` + `versao` + `aprovado: false`; só renderiza ao aluno com `aprovado: true`.
6. **Revisor:** `GET /api/revisao/caso/{id}` devolve o bloco; `TelaEquipeCaso` mostra déficit, ordem, premissas e cenários.
7. **Aluno:** aviso antes do envio quando o resultado é negativo.

## Estratégia de teste
Gabarito GAB-04 existente continua; novos testes por critério de aceite (`AC-441…`), sem fixture inventada.
