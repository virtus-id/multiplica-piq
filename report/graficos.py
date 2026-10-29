"""`RF-474` — gráficos do relatório, em SVG puro (o weasyprint os desenha; sem
biblioteca nova, sem recurso remoto).

Só DESENHA números que o motor já calculou: proporções de largura, nenhuma
conta de negócio (`AC-42`). Sem dado, sem gráfico (devolve `""`).

REGRAS: RF-474
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final, NamedTuple

REGRAS: Final[tuple[str, ...]] = ("RF-474",)

COR_DIA_A_DIA: Final = "#1F4E5F"
COR_NAO_MENSAIS: Final = "#6FA3B5"
COR_PARCELAS: Final = "#C98A00"
COR_FALTA: Final = "#A63A2C"
COR_RENDA: Final = "#0F6B50"
_TRILHA: Final = "#E8EDEA"
_LARGURA: Final = 560


class Parte(NamedTuple):
    rotulo: str
    valor: Decimal
    cor: str


def _x(valor: Decimal, base: Decimal) -> str:
    return f"{float(valor / base * _LARGURA):.1f}"


def barra_da_renda(renda: Decimal, partes: tuple[Parte, ...]) -> str:
    """Uma barra com as saídas empilhadas e uma marca na renda; o que passa da
    marca é o que falta (vermelho). `""` sem renda positiva ou sem saída."""
    saidas = tuple(p for p in partes if p.valor > 0)
    if renda <= 0 or not saidas:
        return ""
    total = sum((p.valor for p in saidas), Decimal(0))
    base = max(renda, total)
    corpo: list[str] = []
    cursor = Decimal(0)
    for parte in saidas:
        inicio, fim = cursor, cursor + parte.valor
        cursor = fim
        # a parte (ou o pedaço dela) que ultrapassa a renda fica vermelha
        dentro_fim = min(fim, renda)
        if dentro_fim > inicio:
            corpo.append(
                f'<rect x="{_x(inicio, base)}" y="14" width="{_x(dentro_fim - inicio, base)}" '
                f'height="26" fill="{parte.cor}"/>'
            )
        fora_inicio = max(inicio, renda)
        if fim > fora_inicio:
            corpo.append(
                f'<rect x="{_x(fora_inicio, base)}" y="14" width="{_x(fim - fora_inicio, base)}" '
                f'height="26" fill="{COR_FALTA}"/>'
            )
    marca = _x(renda, base)
    return (
        f'<svg viewBox="0 0 {_LARGURA} 54" width="100%" role="img" '
        f'aria-label="Para onde vai a sua renda">'
        f'<rect x="0" y="14" width="{_LARGURA}" height="26" rx="4" fill="{_TRILHA}"/>'
        f"<g>{''.join(corpo)}</g>"
        f'<line x1="{marca}" y1="6" x2="{marca}" y2="48" stroke="{COR_RENDA}" stroke-width="2.5"/>'
        f'<circle cx="{marca}" cy="6" r="3.5" fill="{COR_RENDA}"/>'
        "</svg>"
    )


def larguras_dos_gastos(gastos: tuple[tuple[str, Decimal], ...]) -> tuple[str, ...]:
    """Largura (% do maior) de cada barra, na ordem recebida; `()` sem dado."""
    maior = max((v for _, v in gastos), default=Decimal(0))
    if maior <= 0:
        return ()
    return tuple(f"{max(float(v / maior * 100), 1.5):.1f}" for _, v in gastos)
