"""Normalização da taxa da dívida para ao mês — regra `§16.1`.

`specs/motor-calculo.spec.md` §16 (Rodada 6). O aluno informa um valor e a
periodicidade (ao mês ou ao ano); o motor devolve a taxa efetiva mensal que
`Divida.TAXA_EFETIVA_MENSAL_NORMALIZADA` guarda. A conversão é fórmula
financeira e por isso vive aqui, não na camada de aplicação (Lei nº 3 de
`app-aluno`). Sem parâmetro `P_*`; precisão decimal integral (`RF-12`, `G-01`).
"""

from __future__ import annotations

from decimal import Context, Decimal, localcontext
from typing import Final, Literal

from engine.precisao import CONTEXTO_MOTOR
from engine.tipos import Taxa

REGRAS: Final[tuple[str, ...]] = ("§16.1", "RF-12", "RF-21")

type PeriodicidadeTaxa = Literal["MENSAL", "ANUAL"]

_PERIODICIDADES: Final[frozenset[str]] = frozenset({"MENSAL", "ANUAL"})
_UM: Final[Decimal] = Decimal(1)
_DOZE: Final[Decimal] = Decimal(12)

# Dígitos de guarda: `(1 + valor)^(1/12) - 1` subtrai dois números próximos
# quando a taxa é pequena e perderia casas significativas no prec=34 puro. O
# cálculo corre com 10 dígitos a mais e o resultado volta ao contexto do motor.
_CONTEXTO_CALCULO: Final[Context] = Context(
    prec=CONTEXTO_MOTOR.prec + 10, rounding=CONTEXTO_MOTOR.rounding
)


def derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(
    valor: Taxa | int | str, periodicidade: PeriodicidadeTaxa
) -> Taxa:
    """`§16.1`: `MENSAL` -> o próprio valor; `ANUAL` -> `(1 + valor)^(1/12) - 1`.

    `valor` é fração (2% == `Decimal("0.02")`). Recusa `float` (`TypeError`,
    como `dinheiro()`), valor negativo e periodicidade fora de
    `MENSAL`/`ANUAL` (`ValueError`) — nunca corrige em silêncio.
    """
    if isinstance(valor, float) or not isinstance(valor, (Decimal, int, str)):
        raise TypeError(
            f"§16.1: valor de taxa deve ser Decimal, int ou str, não {type(valor).__name__!r}."
        )
    if periodicidade not in _PERIODICIDADES:
        raise ValueError(f"§16.1: periodicidade {periodicidade!r} fora de MENSAL/ANUAL.")
    with localcontext(CONTEXTO_MOTOR):
        taxa = +Decimal(valor)
        if taxa < 0:
            raise ValueError(f"§16.1: taxa negativa recusada: {taxa}.")
        if periodicidade == "MENSAL":
            return taxa
    with localcontext(_CONTEXTO_CALCULO):
        mensal = (_UM + taxa) ** (_UM / _DOZE) - _UM
    with localcontext(CONTEXTO_MOTOR):
        return +mensal
