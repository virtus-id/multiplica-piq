"""Validação de entrada da calculadora — `T-473`, `T-482` (`RF-518`, `RF-530`).

REGRAS: `RF-518`, `RF-530`, `EC-69`, `AC-527`, `AC-541`
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.montagem.calculo_divida import (
    CAMPO_DA_DIVIDA,
    CODIGO_ERRO_DE_ENTRADA,
    ErroDeEntrada,
    validar_entrada,
)
from engine.tipos import SISTEMA_AMORTIZACAO

_C = CODIGO_ERRO_DE_ENTRADA
_F = CAMPO_DA_DIVIDA


@pytest.mark.parametrize(
    ("argumentos", "campo", "codigo"),
    [
        pytest.param({"saldo": "0"}, _F.SALDO, _C.SALDO_NAO_POSITIVO, id="AC-527-saldo-zero"),
        pytest.param({"saldo": "-5"}, _F.SALDO, _C.SALDO_NAO_POSITIVO, id="AC-527-saldo-negativo"),
        pytest.param(
            {"parcela": "0"}, _F.PARCELA, _C.PARCELA_NAO_POSITIVA, id="AC-527-parcela-zero"
        ),
        pytest.param(
            {"parcela": "-1"}, _F.PARCELA, _C.PARCELA_NAO_POSITIVA, id="AC-527-parcela-negativa"
        ),
        pytest.param({"taxa": "-1"}, _F.TAXA, _C.TAXA_NEGATIVA, id="AC-527-taxa-negativa"),
        pytest.param({"taxa": "100,01"}, _F.TAXA, _C.TAXA_ACIMA_DO_TETO, id="teto-mensal"),
        pytest.param(
            {"taxa": "5000000", "periodicidade": "ANUAL"},
            _F.TAXA,
            _C.TAXA_ACIMA_DO_TETO,
            id="teto-depois-de-normalizar-ao-mes",
        ),
        pytest.param(
            {"prazo": "2,5"}, _F.PRAZO, _C.PRAZO_NAO_INTEIRO, id="AC-527-prazo-fracionado"
        ),
        pytest.param({"prazo": "0"}, _F.PRAZO, _C.PRAZO_NAO_POSITIVO, id="AC-527-prazo-zero"),
        pytest.param({"prazo": "-3"}, _F.PRAZO, _C.PRAZO_NAO_POSITIVO, id="prazo-negativo"),
        pytest.param({"prazo": "481"}, _F.PRAZO, _C.PRAZO_ACIMA_DO_MAXIMO, id="prazo-481"),
        pytest.param({"saldo": "mil reais"}, _F.SALDO, _C.VALOR_ILEGIVEL, id="EC-69-texto"),
        pytest.param({"prazo": "1.2.3"}, _F.PRAZO, _C.VALOR_ILEGIVEL, id="EC-69-ambiguo"),
        pytest.param({"saldo": "1234.56"}, _F.SALDO, _C.VALOR_ILEGIVEL, id="AC-527-ponto-decimal"),
        pytest.param({"parcela": "12.5"}, _F.PARCELA, _C.VALOR_ILEGIVEL, id="AC-527-parcela-ponto"),
        pytest.param({"taxa": "1.5"}, _F.TAXA, _C.VALOR_ILEGIVEL, id="AC-527-taxa-ponto"),
    ],
)
def test_entrada_invalida_tem_codigo_proprio(
    argumentos: dict[str, str], campo: CAMPO_DA_DIVIDA, codigo: CODIGO_ERRO_DE_ENTRADA
) -> None:
    with pytest.raises(ErroDeEntrada) as erro:
        validar_entrada(**argumentos)  # type: ignore[arg-type]
    assert (erro.value.campo, erro.value.codigo) == (campo, codigo)


def test_ac541_formato_brasileiro_com_milhar() -> None:
    assert validar_entrada(saldo="1.234,50").saldo == Decimal("1234.50")


def test_ec69_milhar_brasileiro_com_decimal_curto_e_lido() -> None:
    assert validar_entrada(saldo="1.234,5").saldo == Decimal("1234.5")
    assert validar_entrada(saldo="1.234").saldo == Decimal("1234")


@pytest.mark.parametrize("vazio", [None, "", "   "])
def test_campo_ausente_e_desconhecido_nao_erro(vazio: str | None) -> None:
    entrada = validar_entrada(saldo=vazio, parcela=vazio, taxa=vazio, prazo=vazio)
    assert (entrada.saldo, entrada.parcela, entrada.taxa_mensal, entrada.prazo) == (
        None,
        None,
        None,
        None,
    )


def test_taxa_zero_e_aceita_e_anual_e_normalizada_ao_mes() -> None:
    assert validar_entrada(taxa="0").taxa_mensal == 0
    mensal = validar_entrada(taxa="26,82", periodicidade="ANUAL").taxa_mensal
    assert mensal is not None
    assert abs(mensal - Decimal("0.02")) < Decimal("0.00001")


def test_entrada_valida_completa_e_sistema() -> None:
    entrada = validar_entrada("10.000,00", "528,72", "2", "24", sistema=SISTEMA_AMORTIZACAO.SAC)
    assert entrada.prazo == 24
    assert entrada.taxa_mensal == Decimal("0.02")
    assert entrada.sistema is SISTEMA_AMORTIZACAO.SAC
