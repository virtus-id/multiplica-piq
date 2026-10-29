# Plano — pendências e redação do relatório do aluno

| Campo | Valor |
| ----- | ----- |
| Slug  | `pendencias-do-relatorio` |
| Spec  | [`specs/pendencias-do-relatorio.spec.md`](../specs/pendencias-do-relatorio.spec.md) |

## Tech Stack

Sem tecnologia nova: Python (`report/`, `app/`), Jinja2, YAML canônico e React já existentes.

## Decisões

1. **Um só lugar para as pendências** (`RF-461`, `RF-463`): `report/plano.py::_campos_desconhecidos_da_divida` alimenta `_pendencias` (PDF e lista simples) e `_pendencias_acionaveis` (tela). Tirar `VALOR_QUITACAO_HOJE` de `_CAMPOS_MATERIAIS_DA_DIVIDA` corrige os dois. `_pendencias` devolve `None` quando não há campo faltante nem inventário incompleto, e os templates e a tela já escondem a seção nesse caso.
2. **Ausência estrutural vem das respostas, não do motor** (`RF-462`): `Divida` não carrega `POSSUI_PARCELA_DEFINIDA` e `engine/` é congelado (AC-44). `app/http/serializacao_plano.py::vocabulario_do_caso` lê a resposta e a transporta em `VocabularioDoCaso.dividas_sem_parcela_definida`, como já faz com `dividas_atrasadas`.
3. **Pergunta que não existe** (`RF-464`): `pergunta_do_campo` perde a chave do campo removido, e um teste estático cobra que todo valor do mapa seja um `ID` de `collection/registros/`.
4. **Redação provisória** (`RF-465`): `textos-canonicos.yaml` ganha `corpo_provisorio` e `duvidas_provisorio`; `montar_contexto_plano` escolhe por `ORDEM_STATUS`/`MODO_ESTABILIZACAO`; `ContextoPlano` passa a carregar `duvidas`, e `duvidas.html`, `renderizar_html_do_plano` e a serialização o usam. Plano definitivo não muda (`tests/app_aluno/test_plano.py` continua travando o texto).
5. **Rótulo da linha** (`RF-466`): só o YAML (`ponto_de_partida.despesas_mensais_totais`) e a spec `RF-412`.
6. **Guarda de envio** (`RF-467`): sem código novo; teste de regressão sobre `pendencias_obrigatorias`.

## Estratégia de teste

Cada requisito tem ao menos um teste que cita o `RF`; os existentes que travam texto ou contagem de pendências são atualizados só quando o comportamento mudou de propósito.
