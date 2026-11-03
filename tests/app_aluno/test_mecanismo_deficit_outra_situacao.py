"""B1.09 — "Outra situação" abre um campo de texto e a descrição é gravada com a resposta."""

from __future__ import annotations

import pytest

from app.http.rotas_coleta import ErroValorInvalido, _resolver_campo
from collection.carga import carregar_registros
from collection.registro import TipoResposta


def _b109():
    return next(r for r in carregar_registros().registros if r.ID == "B1.09")


def test_outra_situacao_declara_campo_de_texto() -> None:
    outra = next(o for o in _b109().opcoes if o.valor_interno == "OUTRA")
    assert (outra.abre_campo, outra.variavel_do_campo) == (
        TipoResposta.TEXTO_CURTO,
        "MECANISMO_DEFICIT_OUTRO",
    )


def test_descricao_grava_na_variavel_do_campo() -> None:
    campo = _resolver_campo(_b109(), frozenset({"CORTE", "OUTRA"}), (), "  Vendo   doces ")
    assert campo == ("MECANISMO_DEFICIT_OUTRO", "Vendo doces")


def test_sem_outra_marcada_nada_extra() -> None:
    assert _resolver_campo(_b109(), frozenset({"CORTE"}), (), "x") is None


def test_outra_sem_descricao_e_recusada() -> None:
    with pytest.raises(ErroValorInvalido):
        _resolver_campo(_b109(), frozenset({"OUTRA"}), (), " ")
