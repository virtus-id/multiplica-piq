"""Testes de `engine/despesas.py` — regra `§16.2` (`specs/motor-calculo.spec.md`,
`B3.DF02`): fixas × variáveis. Cada teste cita o critério `§16.2-Cn`:
`test_c1_*` = `§16.2-C1`, `test_c2_*` = `§16.2-C2`, `test_c3_*` = `§16.2-C3`.
"""

from __future__ import annotations

from decimal import Decimal

from engine.despesas import somar_despesas_por_classificacao
from engine.tipos import DESCONHECIDO, DinheiroTalvez


def test_c1_separa_fixas_variaveis_e_sem_classificacao() -> None:
    itens = [
        ("FIXA", Decimal("1000.10")),
        ("FIXA", Decimal("200.05")),
        ("VARIAVEL", Decimal("300.20")),
        (object(), Decimal("50")),  # NAO_SEI: não se infere pela categoria
        (None, Decimal("7")),
    ]
    assert somar_despesas_por_classificacao(itens) == (
        Decimal("1200.15"),
        Decimal("300.20"),
        Decimal("57"),
    )


def test_c2_valor_desconhecido_nao_contribui() -> None:
    itens: list[tuple[object, DinheiroTalvez]] = [
        ("FIXA", DESCONHECIDO),
        ("VARIAVEL", Decimal("9")),
    ]
    assert somar_despesas_por_classificacao(itens) == (Decimal(0), Decimal("9"), Decimal(0))


def test_c3_sem_itens_zera() -> None:
    assert somar_despesas_por_classificacao([]) == (Decimal(0), Decimal(0), Decimal(0))
