"""Despesas mensais separadas em fixas e variáveis — `RF-412` (`B3.DF02`).

`specs/enxugamento-questionario.spec.md` RF-412. O aluno classifica cada item
de despesa como fixo ou variável; o motor soma cada grupo. A soma é fórmula
financeira e por isso vive aqui, não na camada de aplicação (Lei nº 3 de
`app-aluno`). Mesmo critério de `OQ-16`: item "não sei" (valor `DESCONHECIDO`)
não contribui. Item sem classificação (`NAO_SEI` ou ausente) não é inferido
pela categoria: vai para o terceiro grupo. Sem parâmetro `P_*`; precisão
decimal integral (`G-01`).
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, localcontext
from typing import Final

from engine.precisao import CONTEXTO_MOTOR
from engine.tipos import Dinheiro, DinheiroTalvez

REGRAS: Final[tuple[str, ...]] = ("RF-412", "OQ-16", "G-01")

_FIXA: Final[str] = "FIXA"
_VARIAVEL: Final[str] = "VARIAVEL"


def somar_despesas_por_classificacao(
    itens: Iterable[tuple[object, DinheiroTalvez]],
) -> tuple[Dinheiro, Dinheiro, Dinheiro]:
    """`RF-412`: `(fixas, variaveis, nao_classificadas)` a partir de pares
    `(classificação, valor mensal)`. Classificação diferente de `"FIXA"` e
    `"VARIAVEL"` cai em `nao_classificadas`; valor não `Decimal` é ignorado."""
    fixas = variaveis = nao_classificadas = Decimal(0)
    with localcontext(CONTEXTO_MOTOR):
        for classificacao, valor in itens:
            if not isinstance(valor, Decimal):
                continue
            if classificacao == _FIXA:
                fixas += valor
            elif classificacao == _VARIAVEL:
                variaveis += valor
            else:
                nao_classificadas += valor
    return fixas, variaveis, nao_classificadas
