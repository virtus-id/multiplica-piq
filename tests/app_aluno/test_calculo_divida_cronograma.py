"""Cronograma e total de juros — `T-479`, `T-481`.

REGRAS: `RF-517`, `RF-521`, `RF-529`, `EC-67`, `AC-520`, `AC-521`, `AC-531`
"""

from __future__ import annotations

from decimal import Decimal

from app.montagem.calculo_divida import cronograma, total_de_juros
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from engine.tipos import SISTEMA_AMORTIZACAO

PRICE = SISTEMA_AMORTIZACAO.PRICE
SAC = SISTEMA_AMORTIZACAO.SAC


def test_ac521_sac_parcelas_e_total_de_juros() -> None:
    linhas = cronograma(d("12000"), d("1120"), t("1"), 12, SAC)
    pagamentos = [linha.pagamento for linha in linhas]
    assert pagamentos[:3] == [d("1120"), d("1110"), d("1100")]
    assert pagamentos[-1] == d("1010")
    assert linhas[0].amortizacao == d("1000")
    assert total_de_juros(linhas) == d("780")
    assert linhas[-1].saldo_final == 0


def test_ac531_sac_residuo_da_amortizacao_cai_na_ultima_parcela() -> None:
    linhas = cronograma(d("10000"), d("3433,34"), t("1"), 3, SAC)
    assert [linha.amortizacao for linha in linhas] == [d("3333,33"), d("3333,33"), d("3333,34")]
    assert sum(linha.amortizacao for linha in linhas) == d("10000")
    pagamentos = [linha.pagamento for linha in linhas]
    assert pagamentos == sorted(pagamentos, reverse=True)
    # último pagamento calculado: amortização restante + juros do saldo restante
    assert linhas[-1].pagamento == d("3333,34") + d("33,33")


def test_ac520_price_20_pagamentos_cheios_e_o_21_menor() -> None:
    linhas = cronograma(d("10000"), d("600"), t("2"), 21, PRICE)
    assert len(linhas) == 21
    assert all(linha.pagamento == d("600") for linha in linhas[:20])
    assert 0 < linhas[20].pagamento < d("600")
    assert linhas[20].saldo_final == 0
    assert linhas[20].pagamento == linhas[20].amortizacao + linhas[20].juros


def test_sac_taxa_zero_todas_as_parcelas_iguais() -> None:
    linhas = cronograma(d("1200"), d("100"), Decimal(0), 12, SAC)
    assert {linha.pagamento for linha in linhas} == {d("100")}
    assert total_de_juros(linhas) == 0


def test_ac526_price_prazo_calculado_fecha_em_zero() -> None:
    linhas = cronograma(d("10000"), d("528,72"), t("2"), 24, PRICE)
    assert len(linhas) == 24
    assert linhas[-1].saldo_final == 0
    assert 0 < linhas[-1].pagamento <= d("528,72")
