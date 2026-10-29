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


def barras_entrada_e_saida(
    renda: Decimal,
    partes: tuple[Parte, ...],
    rotulo_entrada: str,
    rotulo_saida: str,
    texto_entrada: str,
    texto_saida: str,
) -> str:
    """Duas barras verticais na mesma escala: a entrada (verde) e a saída, uma
    só barra empilhada com um grupo por cor. A linha tracejada marca a renda na
    barra da saída; o que passa dela é o que falta. `""` sem renda positiva ou
    sem saída. Os textos já chegam formatados (só se desenha)."""
    saidas = tuple(p for p in partes if p.valor > 0)
    if renda <= 0 or not saidas:
        return ""
    total = sum((p.valor for p in saidas), Decimal(0))
    base = max(renda, total)
    chao, topo, largura = 136.0, 24.0, 96.0
    altura = chao - topo

    def h(valor: Decimal) -> float:
        return float(valor / base) * altura

    x_entrada, x_saida = 70.0, 200.0
    fonte = 'font-family="Inter, DejaVu Sans, sans-serif"'
    corpo = [
        f'<rect x="{x_entrada}" y="{chao - h(renda):.1f}" width="{largura}" '
        f'height="{h(renda):.1f}" rx="6" fill="{COR_RENDA}"/>'
    ]
    y = chao
    for parte in saidas:
        alto = h(parte.valor)
        y -= alto
        corpo.append(
            f'<rect x="{x_saida}" y="{y:.1f}" width="{largura}" '
            f'height="{alto:.1f}" fill="{parte.cor}"/>'
        )
    y_renda = chao - h(renda)
    topo_saida = chao - h(total)
    return (
        '<svg viewBox="0 0 400 160" width="100%" role="img" aria-label="Entrada e saída do mês">'
        f"<g>{''.join(corpo)}</g>"
        f'<line x1="20" y1="{chao}" x2="380" y2="{chao}" stroke="#CBD5D1" stroke-width="1"/>'
        f'<line x1="{x_entrada - 20}" y1="{y_renda:.1f}" '
        f'x2="{x_saida + largura + 20}" y2="{y_renda:.1f}" '
        f'stroke="{COR_RENDA}" stroke-width="1.5" stroke-dasharray="5 4"/>'
        f'<text x="{x_entrada + largura / 2}" y="{chao - h(renda) - 7:.1f}" text-anchor="middle" '
        f'{fonte} font-size="13" font-weight="700" fill="{COR_RENDA}">{texto_entrada}</text>'
        f'<text x="{x_saida + largura / 2}" y="{topo_saida - 7:.1f}" text-anchor="middle" '
        f'{fonte} font-size="13" font-weight="700" fill="#0B1F2A">{texto_saida}</text>'
        f'<text x="{x_entrada + largura / 2}" y="154" text-anchor="middle" {fonte} '
        f'font-size="12" font-weight="600" fill="#64748B">{rotulo_entrada}</text>'
        f'<text x="{x_saida + largura / 2}" y="154" text-anchor="middle" {fonte} '
        f'font-size="12" font-weight="600" fill="#64748B">{rotulo_saida}</text>'
        "</svg>"
    )


def larguras_dos_gastos(gastos: tuple[tuple[str, Decimal], ...]) -> tuple[str, ...]:
    """Largura (% do maior) de cada barra, na ordem recebida; `()` sem dado."""
    maior = max((v for _, v in gastos), default=Decimal(0))
    if maior <= 0:
        return ()
    return tuple(f"{max(float(v / maior * 100), 1.5):.1f}" for _, v in gastos)
