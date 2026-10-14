"""Agregações de entrada da Rodada 9 — `RF-79`, `RF-80` (`T-225`), `OQ-53`.

`plans/app-aluno.plan.md` §R9.5, lei nº 1 da Rodada 9: sobra, desconto,
conferências são AGREGAÇÃO DE ENTRADA, feita aqui — nunca cálculo
do motor refeito. Cada função é pura, lê `RespostasCaso` e reutiliza as
MESMAS funções de `app/montagem/estado.py` que alimentam o motor (um lugar
só, como `OQ-16`). `Decimal` só nasce em `app/montagem/conversao.py`
(`RF-13`).

**Fotografia do mês (`B3.C00`).** Só Bloco 3: nunca lê ficha de dívida
(`AC-118`, `AC-122`). Decisão do produto `R9-2` (2026-09-30): um
total com algum item "não sei" é exibido com o valor dos informados e
marcado `parcial` — o motor segue somando os informados (`OQ-16`). Renda
principal "não sei" (ou não respondida) deixa a renda "não informado"
(`DESCONHECIDO`), e a sobra também (`EC-28`). Sobra sobre total parcial:
decisão do produto de 2026-09-30 — mesmo tratamento dos totais, o valor com
a marca "parcial" (`parcial_sobra`).

REGRAS: `RF-79`, `RF-80`, `EC-28`, `EC-29`, `OQ-16`, `OQ-53`
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Final

import yaml

from app.montagem.conversao import converter_para_dinheiro
from app.montagem.estado import (
    ErroCampoAgregadoDesconhecido,
    _despesas_nao_mensais_por_item,
    _despesas_operacionais_por_item,
    _renda_total_recorrente,
    _soma_dos_informados,
)
from collection.registro import EscopoRepeticao
from collection.respostas import RespostasCaso
from engine.precisao import quantizar_exibicao
from engine.tipos import DESCONHECIDO, Dinheiro, DinheiroTalvez

REGRAS: Final[tuple[str, ...]] = ("RF-79", "RF-80", "EC-28", "EC-29", "OQ-16", "OQ-53")


@dataclass(frozen=True, slots=True)
class LinhaDecomposicao:
    """Uma linha das decomposições (`RF-80`): o item e o seu valor no mês.
    O rótulo e o destino de correção são apresentação — a serialização os
    anexa a partir do item e do registro."""

    item_id: str
    valor_mensal: DinheiroTalvez
    VARIAVEL_GRAVADA: str  # onde o valor é corrigido (rota de `RF-69`)


@dataclass(frozen=True, slots=True)
class FotografiaDoMes:
    """RF-79 — os três números da `B3.C00` e as decomposições (`RF-80`).

    `RENDA_TOTAL` é `RENDA_TOTAL_RECORRENTE`; `DESPESAS_TOTAIS` é
    `DESPESAS_OPERACIONAIS_ATUAIS + DESPESAS_NAO_MENSAIS_NORMALIZADAS` — as
    mesmas funções que alimentam o motor. `parcial_*` marca total com item
    "não sei" (decisão `R9-2`); a sobra é parcial quando um dos dois é."""

    RENDA_TOTAL: DinheiroTalvez
    DESPESAS_TOTAIS: DinheiroTalvez
    SOBRA_ANTES_DAS_DIVIDAS: DinheiroTalvez
    parcial_renda: bool
    parcial_despesas: bool
    despesas_por_item: tuple[LinhaDecomposicao, ...]
    nao_mensais_por_item: tuple[LinhaDecomposicao, ...]

    @property
    def parcial_sobra(self) -> bool:
        return self.parcial_renda or self.parcial_despesas


def fotografia_do_mes(respostas: RespostasCaso) -> FotografiaDoMes:
    """RF-79/RF-80 — a fotografia do mês antes das dívidas. Nenhuma
    aritmética nova além de `renda − despesas`."""
    despesas = tuple(
        LinhaDecomposicao(item_id=i, valor_mensal=v, VARIAVEL_GRAVADA="VALOR_DESPESA")
        for i, v in _despesas_operacionais_por_item(respostas)
    )
    nao_mensais = tuple(
        LinhaDecomposicao(
            item_id=i, valor_mensal=v, VARIAVEL_GRAVADA="VALOR_DESPESA_NAO_MENSAL"
        )
        for i, v in _despesas_nao_mensais_por_item(respostas)
    )
    linhas = tuple((linha.item_id, linha.valor_mensal) for linha in despesas + nao_mensais)
    DESPESAS_TOTAIS = _soma_dos_informados(linhas)
    parcial_despesas = any(not isinstance(valor, Decimal) for _item, valor in linhas)

    RENDA_TOTAL: DinheiroTalvez
    try:
        RENDA_TOTAL = _renda_total_recorrente(respostas)
    except ErroCampoAgregadoDesconhecido:
        RENDA_TOTAL = DESCONHECIDO
    parcial_renda = isinstance(RENDA_TOTAL, Decimal) and any(
        not isinstance(valor, Decimal)
        for valor in respostas.valores_do_escopo(
            EscopoRepeticao.RENDA_ADICIONAL_ID, "RENDA_RECORRENTE_ADICIONAL"
        )
    )

    SOBRA_ANTES_DAS_DIVIDAS: DinheiroTalvez = (
        RENDA_TOTAL - DESPESAS_TOTAIS if isinstance(RENDA_TOTAL, Decimal) else DESCONHECIDO
    )
    return FotografiaDoMes(
        RENDA_TOTAL=RENDA_TOTAL,
        DESPESAS_TOTAIS=DESPESAS_TOTAIS,
        SOBRA_ANTES_DAS_DIVIDAS=SOBRA_ANTES_DAS_DIVIDAS,
        parcial_renda=parcial_renda,
        parcial_despesas=parcial_despesas,
        despesas_por_item=despesas,
        nao_mensais_por_item=nao_mensais,
    )


# ---------------------------------------------------------------------------
# Conferência do desconto — RF-83, RF-84 (`T-239`, `OQ-55`).
# ---------------------------------------------------------------------------

_UM: Final[Dinheiro] = converter_para_dinheiro("1")
_TOLERANCIA_CENTAVO: Final[Dinheiro] = converter_para_dinheiro("0,01")
_TIPOS_COM_VALOR: Final[frozenset[str]] = frozenset({"VALOR", "VALOR_E_PERCENTUAL"})
_TIPOS_COM_PERCENTUAL: Final[frozenset[str]] = frozenset({"PERCENTUAL", "VALOR_E_PERCENTUAL"})


@dataclass(frozen=True, slots=True)
class ConferenciaDesconto:
    """RF-83/RF-84 — a referência da oferta e a conferência do desconto.
    `VALOR_REFERENCIA`: o valor final do credor, se informado; senão o
    calculado; senão `DESCONHECIDO` (`EC-30`, `EC-31`). `VALOR_CALCULADO` é
    só conferência (`AC-127`). `divergencia_rs_pct`: R$ e % informados
    juntos e incompatíveis ao centavo (`AC-129`)."""

    VALOR_REFERENCIA: DinheiroTalvez
    VALOR_CALCULADO: DinheiroTalvez
    divergencia_rs_pct: bool


def conferir_desconto(respostas: RespostasCaso, DIVIDA_ID: str) -> ConferenciaDesconto:
    """RF-83 — só sobre o "valor atual de quitação antes do desconto"
    (`VALOR_QUITACAO_ANTES_DESCONTO`); nunca saldo, valor contratado nem
    parcelas (`AC-126`, `EC-31`). R$ → bruto − R$; % → bruto × (1 − %). Com
    os dois, o calculado usa o R$ e o % só confere — nunca somados
    (`OQ-55`). Cada valor só vale se o tipo informado em `PROPOSTA_DESCONTO`
    o inclui (`RF-95`: campo não aplicável não conta)."""

    def dinheiro_do_item(variavel: str) -> DinheiroTalvez:
        valor = respostas.valor_no_item(DIVIDA_ID, variavel)
        return valor if isinstance(valor, Decimal) else DESCONHECIDO

    tipo = respostas.valor_no_item(DIVIDA_ID, "PROPOSTA_DESCONTO")
    bruto = dinheiro_do_item("VALOR_QUITACAO_ANTES_DESCONTO")
    em_reais = dinheiro_do_item("PROPOSTA_DESCONTO_VALOR") if tipo in _TIPOS_COM_VALOR else None
    percentual = (
        dinheiro_do_item("PROPOSTA_DESCONTO_PERCENTUAL") if tipo in _TIPOS_COM_PERCENTUAL else None
    )
    final = dinheiro_do_item("PROPOSTA_VALOR_FINAL_QUITACAO")

    calculado: DinheiroTalvez = DESCONHECIDO
    divergencia = False
    if isinstance(bruto, Decimal):
        if isinstance(em_reais, Decimal):
            calculado = bruto - em_reais
        elif isinstance(percentual, Decimal):
            calculado = bruto * (_UM - percentual)
        if isinstance(em_reais, Decimal) and isinstance(percentual, Decimal):
            conferido = quantizar_exibicao(bruto * percentual)
            divergencia = abs(em_reais - conferido) > _TOLERANCIA_CENTAVO
    return ConferenciaDesconto(
        VALOR_REFERENCIA=final if isinstance(final, Decimal) else calculado,
        VALOR_CALCULADO=calculado,
        divergencia_rs_pct=divergencia,
    )


# ---------------------------------------------------------------------------
# Avisos da gravação — RF-84 (`T-240`). Aviso não recusa: sinaliza.
# ---------------------------------------------------------------------------

CAMINHO_TEXTOS_AVISOS: Final[Path] = Path(__file__).parent / "textos" / "avisos.yaml"

#: As variáveis que alimentam `conferir_desconto` — gravar qualquer uma delas
#: reconfere o desconto da dívida.
VARIAVEIS_DO_DESCONTO: Final[frozenset[str]] = frozenset(
    {
        "PROPOSTA_DESCONTO",
        "VALOR_QUITACAO_ANTES_DESCONTO",
        "PROPOSTA_DESCONTO_VALOR",
        "PROPOSTA_DESCONTO_PERCENTUAL",
        "PROPOSTA_VALOR_FINAL_QUITACAO",
    }
)


@dataclass(frozen=True, slots=True)
class Aviso:
    codigo: str
    mensagem: str


@cache
def _textos_de_aviso() -> dict[str, str]:
    with CAMINHO_TEXTOS_AVISOS.open(encoding="utf-8") as arquivo:
        return {str(k): str(v) for k, v in yaml.safe_load(arquivo).items()}


def avisos_da_gravacao(
    VARIAVEL_GRAVADA: str, item_id: str | None, respostas: RespostasCaso
) -> tuple[Aviso, ...]:
    """RF-84 (`AC-129`) — os avisos que a resposta recém-gravada levanta,
    sobre as respostas JÁ com ela: divergência R$ × % do desconto."""
    codigos: list[str] = []
    if (
        VARIAVEL_GRAVADA in VARIAVEIS_DO_DESCONTO
        and item_id
        and conferir_desconto(respostas, item_id).divergencia_rs_pct
    ):
        codigos.append("DIVERGENCIA_DESCONTO")
    return tuple(Aviso(codigo=c, mensagem=_textos_de_aviso()[c]) for c in codigos)
