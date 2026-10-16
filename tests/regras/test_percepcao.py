"""Testes de `engine/percepcao.py` — regra `§16.3` (`specs/motor-calculo.spec.md`,
`B3.C02A`/`B3.C02B`). Cada teste cita o critério `§16.3-Cn`: `test_c1_*` =
`§16.3-C1` a `test_c4_*` = `§16.3-C4`. O critério `§16.3-C5` (sobra e falta
juntas: vale a sobra) ainda não tem teste dedicado.
"""

from __future__ import annotations

from decimal import Decimal

from engine.percepcao import diferenca_percebida_do_calculado
from engine.tipos import DESCONHECIDO


def test_c1_sobra_percebida_maior_que_o_calculado() -> None:
    assert diferenca_percebida_do_calculado(Decimal("500"), None, Decimal("200.50")) == Decimal(
        "299.50"
    )


def test_c2_falta_percebida_conta_como_negativa() -> None:
    assert diferenca_percebida_do_calculado(None, Decimal("300"), Decimal("-100")) == Decimal(
        "-200"
    )


def test_c3_valores_iguais_dao_zero_sem_tolerancia() -> None:
    assert diferenca_percebida_do_calculado(Decimal("0.01"), None, Decimal("0.00")) == Decimal(
        "0.01"
    )
    assert diferenca_percebida_do_calculado(Decimal("10"), None, Decimal("10")) == 0


def test_c4_calculado_desconhecido_ou_sem_percebido_nao_inventa_zero() -> None:
    assert diferenca_percebida_do_calculado(Decimal("1"), None, DESCONHECIDO) is DESCONHECIDO
    assert diferenca_percebida_do_calculado(None, None, Decimal("1")) is DESCONHECIDO
