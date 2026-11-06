"""Cenário conservador — `RF-538`, `OQ-82`, `EC-76` (Fase 3, `T-534`).

Módulo **puro**: dados os quatro valores incompatíveis entre si e sem escolha
de recálculo (`RF-525`), devolve a hipótese que o plano usa. Candidatos: o
conjunto digitado e quatro "teóricos" (cada um recalcula um dos quatro campos
pelos outros três, por `calculo_divida`). Candidato que falha no cálculo é
descartado. Escolha por cascata lexicográfica, tudo "maior primeiro": parcela,
saldo, taxa, prazo, custo total (soma dos pagamentos do `cronograma`); empate
total vale o primeiro na ordem da ficha (`EC-76`): digitado, saldo, parcela,
taxa, prazo.

Nomes: `candidato`/`hipotese` e nunca a palavra do cenário (o detector de
`test_sem_aritmetica_sobre_snapshot` reage a ela).

REGRAS: `RF-538`, `OQ-82`, `EC-76`
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from app.montagem.calculo_divida import (
    ErroDeCalculo,
    calcular_parcela,
    calcular_prazo,
    calcular_saldo,
    calcular_taxa,
    cronograma,
)
from app.montagem.conversao import converter_para_dinheiro
from engine.tipos import SISTEMA_AMORTIZACAO, Dinheiro, Taxa

REGRAS: Final[tuple[str, ...]] = ("RF-538", "RF-539", "RF-540", "OQ-82", "EC-76")

_ZERO: Final[Decimal] = converter_para_dinheiro("0")


@dataclass(frozen=True, slots=True)
class Candidato:
    """Um conjunto completo de valores. Taxa mensal normalizada."""

    saldo: Dinheiro
    parcela: Dinheiro
    taxa_mensal: Taxa
    prazo: int


@dataclass(frozen=True, slots=True)
class HipoteseConservadora:
    """`RF-539`: só `saldo` e `taxa_mensal` entram no motor; `parcela` e `prazo`
    são referência exibida e não governam o plano."""

    saldo: Dinheiro
    parcela: Dinheiro
    taxa_mensal: Taxa
    prazo: int


def _teorico_sem(campo: str, digitado: Candidato, sistema: SISTEMA_AMORTIZACAO) -> Candidato | None:
    """O candidato que recalcula `campo` pelos outros três; `None` se falhar."""
    s, p, i, n = digitado.saldo, digitado.parcela, digitado.taxa_mensal, digitado.prazo
    try:
        if campo == "SALDO":
            s = calcular_saldo(p, i, n, sistema)
        elif campo == "PARCELA":
            p = calcular_parcela(s, i, n, sistema)
        elif campo == "TAXA":
            i = calcular_taxa(s, p, n, sistema)
        else:
            n = calcular_prazo(s, p, i, sistema)
    except ErroDeCalculo:
        return None
    return Candidato(s, p, i, n)


def _custo_total(candidato: Candidato, sistema: SISTEMA_AMORTIZACAO) -> Dinheiro | None:
    """Soma dos pagamentos do cronograma; `None` se o candidato não fecha."""
    if candidato.saldo <= _ZERO or candidato.parcela <= _ZERO or candidato.taxa_mensal < _ZERO:
        return None
    try:
        linhas = cronograma(
            candidato.saldo, candidato.parcela, candidato.taxa_mensal, candidato.prazo, sistema
        )
    except ErroDeCalculo:
        return None
    total = _ZERO
    for linha in linhas:
        total += linha.pagamento
    return total


def escolher_hipotese(
    saldo: Dinheiro,
    parcela: Dinheiro,
    taxa_mensal: Taxa,
    prazo: int,
    sistema: SISTEMA_AMORTIZACAO,
) -> HipoteseConservadora | None:
    """`RF-538`: a hipótese mais conservadora, ou `None` se nenhum candidato
    fecha (o chamador mantém os valores digitados)."""
    digitado = Candidato(saldo, parcela, taxa_mensal, prazo)
    ordem_da_ficha = (
        digitado,
        *(_teorico_sem(c, digitado, sistema) for c in ("SALDO", "PARCELA", "TAXA", "PRAZO")),
    )
    melhor: Candidato | None = None
    melhor_chave: tuple[Decimal, Decimal, Decimal, int, Decimal] | None = None
    for candidato in ordem_da_ficha:
        if candidato is None:
            continue
        custo = _custo_total(candidato, sistema)
        if custo is None:
            continue
        chave = (candidato.parcela, candidato.saldo, candidato.taxa_mensal, candidato.prazo, custo)
        if melhor_chave is None or chave > melhor_chave:  # `>` estrito: empate fica com o primeiro
            melhor, melhor_chave = candidato, chave
    if melhor is None:
        return None
    return HipoteseConservadora(melhor.saldo, melhor.parcela, melhor.taxa_mensal, melhor.prazo)
