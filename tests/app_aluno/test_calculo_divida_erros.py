"""Erros do cálculo e valor digitado intocado — `T-482`.

A frase do `RF-519` comparada com o YAML fica em `T-506` (o arquivo nasce em `T-502`).

REGRAS: `RF-519`, `RF-520`, `RF-530`, `EC-63`, `EC-68`, `AC-525`, `AC-530`, `AC-541`
"""

from __future__ import annotations

import pytest

from app.montagem.calculo_divida import (
    CODIGO_ERRO_DE_CALCULO,
    ErroDeCalculo,
    calcular_prazo,
    calcular_taxa,
    validar_entrada,
)
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from engine.tipos import SISTEMA_AMORTIZACAO
from report.plano import formatar_dinheiro_br

PRICE = SISTEMA_AMORTIZACAO.PRICE


def test_ac530_calcular_a_taxa_nao_altera_a_parcela_digitada() -> None:
    entrada = validar_entrada("10.000,00", "528,71", None, "24")
    assert entrada.saldo is not None and entrada.parcela is not None and entrada.prazo is not None
    calcular_taxa(entrada.saldo, entrada.parcela, entrada.prazo, PRICE)
    assert entrada.parcela == d("528,71")  # não virou 528,72


def test_ac541_formato_brasileiro_na_saida() -> None:
    assert formatar_dinheiro_br(d("1234567.89".replace(".", ","))) == "R$ 1.234.567,89"


def test_ac525_falha_de_convergencia_nao_devolve_valor_parcial() -> None:
    with pytest.raises(ErroDeCalculo) as erro:
        calcular_taxa(d("10000"), d("528,72"), 24, PRICE, maximo_iteracoes=1)
    assert erro.value.codigo is CODIGO_ERRO_DE_CALCULO.SEM_CONVERGENCIA


def test_ac525_teto_de_taxa_nao_devolve_valor_parcial() -> None:
    with pytest.raises(ErroDeCalculo) as erro:
        calcular_taxa(d("1000"), d("3000"), 1, PRICE)
    assert erro.value.codigo is CODIGO_ERRO_DE_CALCULO.TAXA_ACIMA_DO_TETO


def test_ec63_prazo_gigante_e_recusado_sem_valor() -> None:
    with pytest.raises(ErroDeCalculo) as erro:
        calcular_prazo(d("1000000"), d("20000,01"), t("2"), PRICE)
    assert erro.value.codigo is CODIGO_ERRO_DE_CALCULO.PRAZO_ACIMA_DO_MAXIMO
