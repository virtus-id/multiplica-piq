"""Sobra ou falta percebida × resultado mensal calculado — `RF-412` (`B3.C02A`/`B3.C02B`).

`specs/enxugamento-questionario.spec.md` RF-412. O aluno diz quanto costuma
sobrar ou faltar; o resultado mensal (`renda − despesas`) vem da montagem. A
diferença entre os dois é fórmula e por isso vive aqui, não na camada de
aplicação (Lei nº 3 de `app-aluno`). Sem limite de tolerância: qualquer
diferença é mostrada. Sem parâmetro `P_*`; precisão decimal integral (`G-01`).
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Final

from engine.precisao import CONTEXTO_MOTOR
from engine.tipos import DESCONHECIDO, Dinheiro, DinheiroTalvez

REGRAS: Final[tuple[str, ...]] = ("RF-412", "G-01")


def diferenca_percebida_do_calculado(
    sobra_percebida: Dinheiro | None,
    falta_percebida: Dinheiro | None,
    resultado_calculado: DinheiroTalvez,
) -> DinheiroTalvez:
    """`RF-412`: `percebido − calculado`, com a sobra positiva e a falta
    negativa. Positivo = o aluno percebe mais folga do que as respostas dão.
    Sem valor percebido, ou resultado calculado desconhecido: `DESCONHECIDO`
    (nunca `0`)."""
    if not isinstance(resultado_calculado, Decimal):
        return DESCONHECIDO
    with localcontext(CONTEXTO_MOTOR):
        if sobra_percebida is not None:
            return sobra_percebida - resultado_calculado
        if falta_percebida is not None:
            return -falta_percebida - resultado_calculado
    return DESCONHECIDO
