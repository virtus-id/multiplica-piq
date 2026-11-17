"""Pendências de inventário — `RF-88`, `RF-559` (`T-247`, `T-647`).

`AC-135`, `AC-595`, `AC-596`, `EC-34`, `EC-97`, sobre os registros REAIS (a
pergunta a corrigir é resolvida pela variável no YAML).
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import cache

import pytest

from app.casos.inventario import (
    TIPO_PENDENCIA_INVENTARIO,
    PendenciaInventario,
    mensagem_da_pendencia,
    pendencias_de_inventario,
)
from collection.carga import carregar_registros
from collection.registro import EscopoRepeticao, RegistroPergunta
from collection.respostas import Resposta, RespostasCaso

_T = TIPO_PENDENCIA_INVENTARIO


@cache
def _registros() -> tuple[RegistroPergunta, ...]:
    return carregar_registros().registros


def _resposta(variavel: str, valor: object, item_id: str | None = None) -> Resposta:
    return Resposta(
        CASO_ID="CASO-INVENTARIO",
        ID_PERGUNTA=variavel,
        item_id=item_id,
        valor=valor,  # type: ignore[arg-type]
        QUESTIONARIO_VERSION="1.0.0",
        respondida_em=datetime(2026, 9, 30, tzinfo=UTC),
    )


def _dividas(n: int) -> tuple[str, ...]:
    return tuple(f"D{i:03d}" for i in range(1, n + 1))


def _pendencias(
    *respostas: Resposta, itens: dict[EscopoRepeticao, tuple[str, ...]] | None = None
) -> tuple[PendenciaInventario, ...]:
    return pendencias_de_inventario(_registros(), RespostasCaso(respostas=respostas), itens or {})


def _fichas_preenchidas(ids: tuple[str, ...]) -> tuple[Resposta, ...]:
    return tuple(_resposta("TIPO_DIVIDA", "PESSOAL", item_id=i) for i in ids)


def test_ac595_zero_fichas_bloqueia_sem_dividas() -> None:
    """`RF-559`: nenhuma ficha de `DIVIDA_ID` — `SEM_DIVIDAS`, sem pergunta a
    corrigir (não existe mais quantidade declarada para apontar)."""
    (pendencia,) = _pendencias()

    assert pendencia.tipo is _T.SEM_DIVIDAS
    assert pendencia.ID_PARA_CORRIGIR is None
    assert pendencia.escopo is EscopoRepeticao.DIVIDA_ID
    assert "quantidade" not in mensagem_da_pendencia(pendencia)


def test_ac595_ficha_criada_e_vazia_nao_conta_como_cadastrada() -> None:
    """Ficha criada sem nenhuma resposta não "cadastra" — mesma definição de
    `RF-87`/`RF-88` de sempre."""
    (pendencia,) = _pendencias(itens={EscopoRepeticao.DIVIDA_ID: _dividas(1)})

    assert pendencia.tipo is _T.SEM_DIVIDAS


def test_ac596_uma_ficha_com_resposta_libera_o_calculo() -> None:
    fichas = _dividas(1)

    assert (
        _pendencias(*_fichas_preenchidas(fichas), itens={EscopoRepeticao.DIVIDA_ID: fichas}) == ()
    )


def test_resposta_de_item_removido_nao_conta() -> None:
    """Item removido não está em `itens_por_escopo` (só ativos): mesmo com
    resposta gravada, não conta como cadastrado — `SEM_DIVIDAS` persiste."""
    (pendencia,) = _pendencias(*_fichas_preenchidas(("D001",)), itens={})

    assert pendencia.tipo is _T.SEM_DIVIDAS


@pytest.mark.parametrize(
    ("variavel", "escopo", "tipo", "ID", "mensagem"),
    [
        (
            "DESPESAS_NAO_MENSAIS_EXISTE",
            EscopoRepeticao.DESPESA_NAO_MENSAL_ID,
            _T.NAO_MENSAL_SEM_ITEM,
            "B3.NM01",
            "Você informou que possui despesa não mensal, mas ainda não cadastrou nenhuma.",
        ),
        (
            "RENDA_RECORRENTE_ADICIONAL_EXISTE",
            EscopoRepeticao.RENDA_ADICIONAL_ID,
            _T.RENDA_EXTRA_SEM_ITEM,
            "B3.03",
            None,
        ),
    ],
)
def test_ac135_sim_sem_item_bloqueia_e_nao_remove(
    variavel: str,
    escopo: EscopoRepeticao,
    tipo: TIPO_PENDENCIA_INVENTARIO,
    ID: str,
    mensagem: str | None,
) -> None:
    # Uma ficha de dívida com resposta, em toda chamada: sem ela, `SEM_
    # DIVIDAS` apareceria ao lado da pendência testada aqui.
    fichas = _dividas(1)
    base = _fichas_preenchidas(fichas)

    (pendencia,) = _pendencias(
        *base, _resposta(variavel, "SIM"), itens={EscopoRepeticao.DIVIDA_ID: fichas}
    )
    assert (pendencia.tipo, pendencia.ID_PARA_CORRIGIR, pendencia.escopo) == (tipo, ID, escopo)
    texto = mensagem_da_pendencia(pendencia)
    assert texto.startswith("Você informou que possui")
    if mensagem is not None:
        assert texto == mensagem

    assert (
        _pendencias(*base, _resposta(variavel, "NAO"), itens={EscopoRepeticao.DIVIDA_ID: fichas})
        == ()
    )
    assert (
        _pendencias(
            *base,
            _resposta(variavel, "SIM"),
            _resposta("QUALQUER", "X", item_id="X001"),
            itens={EscopoRepeticao.DIVIDA_ID: fichas, escopo: ("X001",)},
        )
        == ()
    )
