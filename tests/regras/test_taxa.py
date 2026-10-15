"""Testes da regra `§16.1` — normalização da taxa da dívida
(`specs/motor-calculo.spec.md` §16). Cada teste cita o critério `§16.1-Cn`.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from typing import Final

import pytest

from engine.precisao import CONTEXTO_MOTOR
from engine.taxa import PeriodicidadeTaxa, derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA

_CONTEXTO_INDEPENDENTE: Final[Context] = Context(prec=80, rounding=ROUND_HALF_UP)


def _mensal_independente(anual: Decimal) -> Decimal:
    """`exp(ln(1 + anual) / 12) - 1` em precisão 80, arredondado a 34 dígitos:
    outro caminho de cálculo que o do motor (`**`), sem tolerância."""
    with localcontext(_CONTEXTO_INDEPENDENTE):
        mensal = ((Decimal(1) + anual).ln() / 12).exp() - 1
    with localcontext(CONTEXTO_MOTOR):
        return +mensal


def test_c1_mensal_passa_direto() -> None:
    assert derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(Decimal("0.02"), "MENSAL") == Decimal("0.02")


def test_c2_26_82_ao_ano_e_2_ao_mes() -> None:
    anual = Decimal("1.02") ** 12 - 1
    assert anual == Decimal("0.268241794562545318301696")
    assert derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(anual, "ANUAL") == Decimal("0.02")


def test_c3_raiz_exata() -> None:
    assert derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(4095, "ANUAL") == Decimal(1)


@pytest.mark.parametrize("periodicidade", ["MENSAL", "ANUAL"])
def test_c4_zero(periodicidade: PeriodicidadeTaxa) -> None:
    assert derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(Decimal(0), periodicidade) == 0


@pytest.mark.parametrize(
    "anual", ["0.0000001", "0.1", "0.2682", "0.9999", "5", "1000", "123456789.123456789"]
)
def test_c5_igualdade_exata_contra_calculo_independente(anual: str) -> None:
    valor = Decimal(anual)
    assert derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(valor, "ANUAL") == _mensal_independente(valor)


@pytest.mark.parametrize("periodicidade", ["MENSAL", "ANUAL"])
def test_c6_negativo_recusado(periodicidade: PeriodicidadeTaxa) -> None:
    with pytest.raises(ValueError, match="negativa"):
        derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(Decimal("-0.01"), periodicidade)


def test_c7_periodicidade_fora_do_dominio_e_float_recusados() -> None:
    for fora in ("OUTRA", "NAO_SEI", "mensal", ""):
        with pytest.raises(ValueError, match="periodicidade"):
            derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(Decimal("0.02"), fora)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(0.02, "MENSAL")  # type: ignore[arg-type]


def test_c8_anual_equivalente_a_mensal_nao_muda_o_ranking() -> None:
    from_mensal = derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(Decimal("0.02"), "MENSAL")
    from_anual = derivar_TAXA_EFETIVA_MENSAL_NORMALIZADA(Decimal("1.02") ** 12 - 1, "ANUAL")
    assert from_mensal == from_anual
