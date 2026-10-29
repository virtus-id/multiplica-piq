"""`RF-472` — conferência de consistência dos números que o relatório mostra.

Só LÊ o snapshot e confere identidades que o próprio motor garante (nenhuma
regra de negócio nova, `AC-42`): uma falha aqui é bug do motor ou dado
corrompido, e o relatório avisa que os números não foram conferidos em vez de
apresentá-los como definitivos. Não corrige nem recalcula nada.

REGRAS: RF-472
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from engine.prognostico import MesDoPlano
from engine.snapshot import SnapshotOrdem

REGRAS: Final[tuple[str, ...]] = ("RF-472",)

#: Arredondamento por dívida e por mês: até 1 centavo de diferença é aceito.
_TOLERANCIA: Final[Decimal] = Decimal("0.01")


def _difere(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) > _TOLERANCIA


def _conferir_mes(plano: str, mes: MesDoPlano) -> list[str]:
    achados: list[str] = []
    rotulo = f"{plano}, mês {mes.MES}"
    if None not in (mes.SALDO_INICIAL_TOTAL, mes.JUROS_TOTAL, mes.TOTAL_PAGAR):
        esperado = mes.SALDO_INICIAL_TOTAL + mes.JUROS_TOTAL - mes.TOTAL_PAGAR  # type: ignore[operator]
        if _difere(esperado, mes.SALDO_TOTAL):
            achados.append(f"{rotulo}: início + juros − pago não fecha com o saldo do mês")
    if None not in (mes.HABITUAL_TOTAL, mes.EXTRA_TOTAL, mes.TOTAL_PAGAR) and _difere(
        mes.HABITUAL_TOTAL + mes.EXTRA_TOTAL,  # type: ignore[operator]
        mes.TOTAL_PAGAR,  # type: ignore[arg-type]
    ):
        achados.append(f"{rotulo}: habitual + extra não fecha com o total a pagar")
    if mes.DIVIDAS and _difere(
        sum((d.SALDO_DEPOIS for d in mes.DIVIDAS), Decimal(0)), mes.SALDO_TOTAL
    ):
        achados.append(f"{rotulo}: a soma dos saldos por dívida não fecha com o saldo do mês")
    return achados


def verificar_consistencia(snapshot: SnapshotOrdem) -> tuple[str, ...]:
    """Descrições técnicas (não vão ao aluno) das identidades que não fecham;
    vazio quando o snapshot é consistente."""
    achados: list[str] = []
    estado = snapshot.estado_inputs
    diag = snapshot.diagnostico
    ids = [d.DIVIDA_ID for d in estado.dividas]

    if len(set(ids)) != len(ids):
        achados.append("há dívidas repetidas no inventário")
    ordem_ids = [p.DIVIDA_ID for p in snapshot.ORDEM_QUITACAO]
    if len(set(ordem_ids)) != len(ordem_ids) or not set(ordem_ids) <= set(ids):
        achados.append("a ordem de quitação lista dívida repetida ou fora do inventário")

    efetivos = [d.PAGAMENTO_MENSAL_EFETIVO for d in estado.dividas]
    if all(isinstance(v, Decimal) for v in efetivos):
        esperado = (
            estado.RENDA_TOTAL_RECORRENTE
            - estado.DESPESAS_OPERACIONAIS_ATUAIS
            - estado.DESPESAS_NAO_MENSAIS_NORMALIZADAS
            - sum((v for v in efetivos if isinstance(v, Decimal)), Decimal(0))
        )
        if _difere(esperado, diag.RESULTADO_CAIXA_OBSERVADO):
            achados.append("renda − despesas − parcelas não fecha com o resultado do mês")

    prog = snapshot.prognostico
    if prog is not None:
        saldos = [d.SALDO_DEVEDOR_ATUAL for d in estado.dividas]
        conhecidos = [v for v in saldos if isinstance(v, Decimal)]
        if len(conhecidos) == len(saldos) and _difere(
            sum(conhecidos, Decimal(0)), prog.sem_acao.SALDO_INICIAL_TOTAL
        ):
            achados.append(
                "a soma dos saldos das dívidas não fecha com o saldo inicial do prognóstico"
            )
        for mes in prog.MESES_DO_PLANO:
            achados.extend(_conferir_mes("plano seguido", mes))
        extra = prog.com_extra
        if extra is not None:
            if _difere(extra.CONTRIBUICAO_EXTRA_MENSAL, estado.CONTRIBUICAO_EXTRA_MENSAL):  # type: ignore[arg-type]
                achados.append("o aporte do cenário acelerado difere do valor informado pelo aluno")
            for mes in extra.MESES:
                achados.extend(_conferir_mes("plano acelerado", mes))
    return tuple(achados)
