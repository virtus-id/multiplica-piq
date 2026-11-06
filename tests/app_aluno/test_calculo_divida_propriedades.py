"""Propriedades da calculadora (hypothesis) — `T-483`.

O domínio gerado respeita a tabela 0.2 do plano (inclui taxa 0 e prazo 1) e os
valores nascem de texto brasileiro, nunca de `float`. Saldo mínimo de R$ 1.000 e
prazo até 120. O arredondamento da parcela ao centavo pode, por si só,
encurtar o plano em 1 mês quando duas parcelas vizinhas (`n` e `n - 1`) caem no
mesmo centavo (R$ 1.000,00 a 7,6% por 88 meses: parcela 76,13 quita em 87) —
não é defeito da fórmula: o prazo exibido continua sendo o que o motor projeta
(`AC-526`, `test_calculo_divida_equivalencia_motor.py`).

REGRAS: `RF-514`, `RF-516`, `RF-517`, `AC-526`
"""

from __future__ import annotations

import time
from decimal import Decimal, localcontext

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.montagem.calculo_divida import (
    PRAZO_MAXIMO_MESES,
    TETO_TAXA_MENSAL,
    calcular_parcela,
    calcular_prazo,
    calcular_saldo,
    calcular_taxa,
    cronograma,
)
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from engine.precisao import CONTEXTO_MOTOR
from engine.tipos import SISTEMA_AMORTIZACAO

_CONFIG = settings(max_examples=200, deadline=None)

sistemas = st.sampled_from([SISTEMA_AMORTIZACAO.PRICE, SISTEMA_AMORTIZACAO.SAC])
saldos = st.integers(min_value=100_000, max_value=100_000_000).map(  # centavos
    lambda c: d(f"{c // 100},{c % 100:02d}")
)
# 0,00% a 15,00% ao mês, em centésimos de ponto percentual (inclui taxa 0).
taxas = st.integers(min_value=0, max_value=1_500).map(lambda c: t(f"{c // 100},{c % 100:02d}"))
prazos = st.integers(min_value=1, max_value=120)  # inclui prazo 1


@given(saldo=saldos, taxa=taxas, prazo=prazos, sistema=sistemas)
@_CONFIG
def test_ida_e_volta_prazo_da_parcela_calculada(
    saldo: Decimal, taxa: Decimal, prazo: int, sistema: SISTEMA_AMORTIZACAO
) -> None:
    parcela = calcular_parcela(saldo, taxa, prazo, sistema)
    achado = calcular_prazo(saldo, parcela, taxa, sistema)
    assert achado <= prazo  # a parcela arredondada para cima nunca alonga o plano
    # Identificável: se a parcela de `prazo - 1` meses é estritamente maior, a
    # nossa não quita antes (a quitação em `prazo - 1` exigiria `P*_(n-1)`,
    # que então é maior que a nossa parcela). Com juros altos e prazo longo as
    # duas parcelas se encontram no centavo e o prazo pode cair em 1 mês.
    if prazo == 1 or calcular_parcela(saldo, taxa, prazo - 1, sistema) > parcela:
        assert achado == prazo


@given(saldo=saldos, taxa=taxas, prazo=prazos, sistema=sistemas)
@_CONFIG
def test_ida_e_volta_parcela_do_saldo_calculado(
    saldo: Decimal, taxa: Decimal, prazo: int, sistema: SISTEMA_AMORTIZACAO
) -> None:
    parcela = calcular_parcela(saldo, taxa, prazo, sistema)
    saldo_calculado = calcular_saldo(parcela, taxa, prazo, sistema)
    assert saldo_calculado <= saldo + d("0,01") * prazo  # para baixo: nunca estoura o plano
    assert abs(calcular_parcela(saldo_calculado, taxa, prazo, sistema) - parcela) <= d("0,01")


@given(saldo=saldos, taxa=taxas, prazo=prazos, sistema=sistemas)
@_CONFIG
def test_recorrencia_sem_residuo_positivo_apos_o_prazo(
    saldo: Decimal, taxa: Decimal, prazo: int, sistema: SISTEMA_AMORTIZACAO
) -> None:
    parcela = calcular_parcela(saldo, taxa, prazo, sistema)
    n = calcular_prazo(saldo, parcela, taxa, sistema)
    if sistema is SISTEMA_AMORTIZACAO.PRICE:
        # a recorrência do motor, escrita de novo aqui, do lado do teste
        restante = saldo
        meses_com_saldo = 0
        with localcontext(CONTEXTO_MOTOR):
            for _ in range(n):
                com_juros = restante * (1 + taxa)
                restante = com_juros - min(parcela, com_juros)
                if restante > 0:
                    meses_com_saldo += 1
        assert restante == 0
        assert meses_com_saldo == n - 1  # só o último mês zera
    linhas = cronograma(saldo, parcela, taxa, n, sistema)
    assert len(linhas) == n
    assert linhas[-1].saldo_final == 0
    assert all(linha.saldo_final >= 0 for linha in linhas[:-1])


@given(
    saldo=saldos,
    taxa=taxas,
    prazo=prazos,
    extra=st.integers(min_value=0, max_value=1_000),  # até R$ 10,00
)
@_CONFIG
def test_taxa_cresce_com_a_parcela(saldo: Decimal, taxa: Decimal, prazo: int, extra: int) -> None:
    price = SISTEMA_AMORTIZACAO.PRICE
    parcela = calcular_parcela(saldo, taxa, prazo, price)
    maior = parcela + d(f"{extra // 100},{extra % 100:02d}")
    assert calcular_taxa(saldo, parcela, prazo, price) <= calcular_taxa(saldo, maior, prazo, price)
    assert calcular_taxa(saldo, parcela, prazo, price) <= TETO_TAXA_MENSAL


@given(saldo=saldos, taxa=taxas, prazo=prazos)
@_CONFIG
def test_taxa_do_price_volta_para_a_taxa_de_origem(
    saldo: Decimal, taxa: Decimal, prazo: int
) -> None:
    parcela = calcular_parcela(saldo, taxa, prazo, SISTEMA_AMORTIZACAO.PRICE)
    achada = calcular_taxa(saldo, parcela, prazo, SISTEMA_AMORTIZACAO.PRICE)
    # a parcela sobe até 1 centavo: a taxa achada pode ficar até um centavo acima
    assert abs(achada - taxa) <= d("0,01") * 12 / saldo * prazo + t("0,01")


def test_dominio_gerado_respeita_a_tabela_0_2() -> None:
    assert PRAZO_MAXIMO_MESES == 480
    assert TETO_TAXA_MENSAL == 1


def test_pior_caso_da_bissecao_roda_abaixo_de_500_ms() -> None:
    # taxa quase no teto (100% a.m.) com o prazo máximo: 7 dobras + bisseção
    parcela = calcular_parcela(d("1000"), t("99"), PRAZO_MAXIMO_MESES, SISTEMA_AMORTIZACAO.PRICE)
    inicio = time.perf_counter()
    calcular_taxa(d("1000"), parcela, PRAZO_MAXIMO_MESES, SISTEMA_AMORTIZACAO.PRICE)
    assert time.perf_counter() - inicio < 0.5


@pytest.mark.parametrize("sistema", [SISTEMA_AMORTIZACAO.PRICE, SISTEMA_AMORTIZACAO.SAC])
def test_prazo_maximo_aceito_e_calculado(sistema: SISTEMA_AMORTIZACAO) -> None:
    parcela = calcular_parcela(d("100000"), t("1"), PRAZO_MAXIMO_MESES, sistema)
    assert calcular_prazo(d("100000"), parcela, t("1"), sistema) == PRAZO_MAXIMO_MESES
