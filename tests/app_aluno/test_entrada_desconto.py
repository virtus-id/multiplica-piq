"""Desconto do credor — `RF-83`, `AC-125`–`AC-127`, `AC-129`, `EC-30`,
`EC-31` (`T-238`, `T-239`).

A conferência é agregação de entrada (`app/montagem/entrada.py::
conferir_desconto`). Os testes pela rota (`faixa` e validação cruzada em
`POST /resposta`, aviso de divergência) dependiam das perguntas `B7.13*`, que
saíram com o Bloco 7 (`T-390`); a função segue testada diretamente.
"""

from __future__ import annotations

import ast
import inspect
from decimal import Decimal

import pytest

from app.montagem import entrada
from app.montagem.conversao import converter_para_dinheiro, converter_para_taxa
from app.montagem.entrada import conferir_desconto
from collection.respostas import NAO_SEI, RespostasCaso
from engine.tipos import DESCONHECIDO
from tests.app_aluno.test_rotas_coleta_fotografia import _resposta

_D = "D001"


def _r(texto: str) -> Decimal:
    return converter_para_dinheiro(texto)


def _pct(texto: str) -> Decimal:
    return converter_para_taxa(texto)


def _caso(tipo: object, **valores: object) -> RespostasCaso:
    base = {
        "PROPOSTA_DESCONTO_EXISTE": "SIM",
        "PROPOSTA_DESCONTO": tipo,
        "SALDO_DEVEDOR_ATUAL": _r("99.999,00"),  # nunca a base (AC-126)
        **valores,
    }
    return RespostasCaso(respostas=tuple(_resposta(v, x, _D) for v, x in base.items()))


# ---------------------------------------------------------------------------
# conferir_desconto — AC-125..AC-127, EC-30, EC-31.
# ---------------------------------------------------------------------------


def test_ac125_desconto_em_reais_referencia_8000() -> None:
    conf = conferir_desconto(
        _caso(
            "VALOR",
            VALOR_QUITACAO_ANTES_DESCONTO=_r("10.000"),
            PROPOSTA_DESCONTO_VALOR=_r("2.000"),
        ),
        _D,
    )
    assert (conf.VALOR_REFERENCIA, conf.VALOR_CALCULADO) == (_r("8000"), _r("8000"))


def test_ac126_percentual_sobre_o_bruto_nunca_sobre_o_saldo() -> None:
    conf = conferir_desconto(
        _caso(
            "PERCENTUAL",
            VALOR_QUITACAO_ANTES_DESCONTO=_r("10.000"),
            PROPOSTA_DESCONTO_PERCENTUAL=_pct("15"),
        ),
        _D,
    )
    assert conf.VALOR_REFERENCIA == _r("8500")


def test_ac127_valor_final_do_credor_prevalece() -> None:
    conf = conferir_desconto(
        _caso(
            "PERCENTUAL",
            VALOR_QUITACAO_ANTES_DESCONTO=_r("10.000"),
            PROPOSTA_DESCONTO_PERCENTUAL=_pct("20"),
            PROPOSTA_VALOR_FINAL_QUITACAO=_r("7.900"),
        ),
        _D,
    )
    assert (conf.VALOR_REFERENCIA, conf.VALOR_CALCULADO) == (_r("7900"), _r("8000"))


@pytest.mark.parametrize(
    ("bruto", "reais", "pct", "divergente"),
    [
        ("10.000", "2.000", "20", False),
        ("10.000,20", "1.500,03", "15", False),
        ("10.000,20", "1.500,05", "15", True),
        ("10.000", "2.000", "15", True),
    ],
)
def test_ac129_conferencia_ao_centavo_nunca_soma(
    bruto: str, reais: str, pct: str, divergente: bool
) -> None:
    conf = conferir_desconto(
        _caso(
            "VALOR_E_PERCENTUAL",
            VALOR_QUITACAO_ANTES_DESCONTO=_r(bruto),
            PROPOSTA_DESCONTO_VALOR=_r(reais),
            PROPOSTA_DESCONTO_PERCENTUAL=_pct(pct),
        ),
        _D,
    )
    assert conf.divergencia_rs_pct is divergente
    # Aplicado uma vez: 10.000 − 2.000 = 8.000, nunca 6.000.
    assert conf.VALOR_CALCULADO == _r(bruto) - _r(reais)


def test_ec30_sem_detalhe_referencia_desconhecida_e_bruto_registrado() -> None:
    respostas = _caso("SEM_DETALHE", VALOR_QUITACAO_ANTES_DESCONTO=_r("10.000"))
    conf = conferir_desconto(respostas, _D)

    assert conf.VALOR_REFERENCIA is DESCONHECIDO
    assert respostas.valor_no_item(_D, "VALOR_QUITACAO_ANTES_DESCONTO") == _r("10000")


def test_ec31_bruto_nao_sei_com_percentual_nada_calculado() -> None:
    conf = conferir_desconto(
        _caso(
            "PERCENTUAL",
            VALOR_QUITACAO_ANTES_DESCONTO=NAO_SEI,
            PROPOSTA_DESCONTO_PERCENTUAL=_pct("15"),
        ),
        _D,
    )
    assert conf.VALOR_REFERENCIA is DESCONHECIDO and conf.VALOR_CALCULADO is DESCONHECIDO


def test_t239_conferir_desconto_nao_le_saldo_contrato_nem_parcelas() -> None:
    """Estático: a função não nomeia saldo, valor contratado nem parcelas."""
    fonte = inspect.getsource(entrada.conferir_desconto)
    literais = {
        no.value
        for no in ast.walk(ast.parse(fonte))
        if isinstance(no, ast.Constant) and isinstance(no.value, str)
    }
    proibidos = ("SALDO", "CONTRATADO", "PARCELA")
    assert not [s for s in literais if any(p in s for p in proibidos)]
