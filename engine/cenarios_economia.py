"""Cenários de economia do aluno deficitário — `RF-448`, `RF-449`, `T-436`.

Hipótese, nunca promessa: "e se as despesas caíssem renda × percentual?".
Nenhuma fórmula de amortização nova: o próprio motor (`calcular_plano`) roda
de novo sobre uma cópia do estado com `DESPESAS_OPERACIONAIS_ATUAIS` reduzida,
e este módulo só lê o resultado. A economia compensa primeiro o déficit: sem
resultado positivo a capacidade de aporte é zero, o cenário não é executável e
não leva prazo, custo nem saldos (`RF-450`). Os percentuais vêm de
`P_ECONOMIA_RENDA_CENARIO_1/2` (parâmetros 1.0.3+); versão sem eles → `None`.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import TYPE_CHECKING, Final

from engine.precisao import CONTEXTO_MOTOR, dinheiro
from engine.tipos import Dinheiro, Meses

if TYPE_CHECKING:
    from engine.estado import EstadoFinanceiro
    from engine.parametros import Parametros
    from engine.snapshot import SnapshotOrdem

_CHAVES: Final[tuple[str, ...]] = ("P_ECONOMIA_RENDA_CENARIO_1", "P_ECONOMIA_RENDA_CENARIO_2")
HORIZONTES: Final[tuple[int, ...]] = (12, 24, 60)


@dataclass(frozen=True, slots=True)
class CenarioDeEconomia:
    """Uma simulação. `SITUACAO`: `DEFICITARIO` | `EQUILIBRADO` | `COM_SOBRA`."""

    PERCENTUAL: Decimal
    ECONOMIA_MENSAL: Dinheiro  # a efetivamente aplicada (nunca passa das despesas)
    RESULTADO_AJUSTADO: Dinheiro
    SITUACAO: str
    CAPACIDADE_ATAQUE_ATUAL: Dinheiro
    EXECUTAVEL: bool  # só com capacidade de aporte positiva
    METODO: str | None = None
    PRAZO_TOTAL: Meses | None = None
    CUSTO_FUTURO_TOTAL: Dinheiro | None = None
    ESTOUROU_HORIZONTE: bool | None = None
    #: (mês do horizonte, saldo devedor total ao fim dele); vazio se não executável.
    SALDOS_NOS_HORIZONTES: tuple[tuple[int, Dinheiro], ...] = ()


def _saldo_no_mes(snapshot: SnapshotOrdem, mes: int) -> Dinheiro:
    """Saldo total ao fim do mês `mes` do cenário recomendado. Depois do último
    mês simulado: zero se quitou tudo, o último saldo se estourou o horizonte."""
    cenario = snapshot.cenarios[snapshot.METODO_RECOMENDADO_PIQ]
    meses = cenario.meses
    if not meses:
        return dinheiro(0)
    if mes > len(meses) and not cenario.ESTOUROU_HORIZONTE:
        return dinheiro(0)
    resultado = meses[min(mes, len(meses)) - 1]
    with localcontext(CONTEXTO_MOTOR):
        return sum(resultado.estado_final.saldos.values(), dinheiro(0))


def _um_cenario(
    estado: EstadoFinanceiro,
    parametros: Parametros,
    percentual: Decimal,
    recalcular: Callable[[EstadoFinanceiro, Parametros], SnapshotOrdem],
) -> CenarioDeEconomia:
    with localcontext(CONTEXTO_MOTOR):
        economia = min(
            dinheiro(estado.RENDA_TOTAL_RECORRENTE * percentual),
            estado.DESPESAS_OPERACIONAIS_ATUAIS,
        )
        despesas_ajustadas = estado.DESPESAS_OPERACIONAIS_ATUAIS - economia
    novo = recalcular(
        dataclasses.replace(estado, DESPESAS_OPERACIONAIS_ATUAIS=despesas_ajustadas),
        parametros,
    )
    diagnostico = novo.diagnostico
    resultado = diagnostico.RESULTADO_MENSAL_ATUAL
    zero = dinheiro(0)
    situacao = "DEFICITARIO" if resultado < zero else ("EQUILIBRADO" if resultado == zero else "COM_SOBRA")
    capacidade = diagnostico.CAPACIDADE_ATAQUE_ATUAL
    base = CenarioDeEconomia(
        PERCENTUAL=percentual,
        ECONOMIA_MENSAL=economia,
        RESULTADO_AJUSTADO=resultado,
        SITUACAO=situacao,
        CAPACIDADE_ATAQUE_ATUAL=capacidade,
        EXECUTAVEL=capacidade > zero,
    )
    if not base.EXECUTAVEL:
        return base
    cenario = novo.cenarios[novo.METODO_RECOMENDADO_PIQ]
    return dataclasses.replace(
        base,
        METODO=novo.METODO_RECOMENDADO_PIQ.value,
        PRAZO_TOTAL=cenario.PRAZO_TOTAL,
        CUSTO_FUTURO_TOTAL=cenario.CUSTO_FUTURO_TOTAL,
        ESTOUROU_HORIZONTE=cenario.ESTOUROU_HORIZONTE,
        SALDOS_NOS_HORIZONTES=tuple((h, _saldo_no_mes(novo, h)) for h in HORIZONTES),
    )


def calcular_cenarios_economia(
    estado: EstadoFinanceiro,
    parametros: Parametros,
    recalcular: Callable[[EstadoFinanceiro, Parametros], SnapshotOrdem],
) -> tuple[CenarioDeEconomia, ...] | None:
    """Os dois cenários, ou `None` se a versão de parâmetros não os define ou se
    a simulação falhar (ela é auxiliar: nunca derruba o plano oficial)."""
    try:
        percentuais = [parametros.numero(chave) for chave in _CHAVES]
    except KeyError:
        return None
    try:
        return tuple(_um_cenario(estado, parametros, p, recalcular) for p in percentuais)
    except Exception:  # noqa: BLE001 — simulação hipotética não pode falhar o cálculo oficial
        return None
