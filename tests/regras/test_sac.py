"""Sistema de amortização — `RF-509`, `AC-509`, `EC-60` (`T-463`).

Financiamento SAC de saldo 120.000, taxa 1% a.m. e parcela de hoje 2.200:
amortização constante de 1.000 (2.200 − 120.000 × 1%), prazo de 120 meses, e o
pagamento do mês 2 é 1.000 + 119.000 × 1% = 2.190.
"""

from dataclasses import replace
from decimal import Decimal

from engine.amortizacao import amortizacao_sac, pagamento_nominal_do_mes
from engine.ciclo_mensal import _pagamento_normal_efetivo
from engine.estado import Divida
from engine.motor import calcular_plano
from engine.precisao import dinheiro
from engine.tipos import SISTEMA_AMORTIZACAO
from engine.trajetoria import ChaveTrajetoria, simular_trajetoria_isolada
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.fixtures.carregar import carregar_gab_b


def _divida(sistema: SISTEMA_AMORTIZACAO, parcela: str = "2200") -> Divida:
    base = carregar_gab_b().dividas[0]
    return replace(
        base,
        DIVIDA_ID="D001",
        SALDO_DEVEDOR_ATUAL=dinheiro("120000"),
        TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal("0.01"),
        PARCELA_CONTRATUAL=dinheiro(parcela),
        PAGAMENTO_MENSAL_EFETIVO=dinheiro(parcela),
        SISTEMA_AMORTIZACAO=sistema,
    )


def test_ac509_amortizacao_constante_e_pagamento_que_cai() -> None:
    divida = _divida(SISTEMA_AMORTIZACAO.SAC)
    assert amortizacao_sac(divida) == dinheiro("1000")
    assert pagamento_nominal_do_mes(divida, dinheiro("1200")) == dinheiro("2200")
    # mês 2: saldo 119.000, juros 1.190
    assert pagamento_nominal_do_mes(divida, dinheiro("1190")) == dinheiro("2190")
    assert _pagamento_normal_efetivo(dinheiro("120190"), divida, dinheiro("119000")) == dinheiro(
        "2190"
    )


def test_ac509_price_continua_com_parcela_fixa() -> None:
    divida = _divida(SISTEMA_AMORTIZACAO.PRICE)
    assert amortizacao_sac(divida) is None
    assert _pagamento_normal_efetivo(dinheiro("120190"), divida, dinheiro("119000")) == dinheiro(
        "2200"
    )


def test_ec60_sac_com_parcela_que_nao_cobre_os_juros_nao_tem_solucao() -> None:
    divida = _divida(SISTEMA_AMORTIZACAO.SAC, parcela="1200")
    assert amortizacao_sac(divida) is None
    assert pagamento_nominal_do_mes(divida, dinheiro("1190")) == dinheiro("1200")


def test_ac509_trajetoria_sac_quita_em_120_meses() -> None:
    chave = ChaveTrajetoria(
        DIVIDA_ID="D001",
        SALDO_DEVEDOR_ATUAL=dinheiro("120000"),
        TAXA_EFETIVA_MENSAL_NORMALIZADA=Decimal("0.01"),
        PAGAMENTO_MENSAL_EFETIVO=dinheiro("2200"),
        DELTA=dinheiro("0"),
        HORIZONTE=200,
        AMORTIZACAO_SAC=dinheiro("1000"),
    )
    trajetoria = simular_trajetoria_isolada(chave)
    assert trajetoria.MESES_ATE_QUITACAO == 120
    # 120 × 1.000 de amortização + 1% de (120.000 + 119.000 + ... + 1.000)
    assert trajetoria.DESEMBOLSO_FUTURO == dinheiro("192600")


def test_ac509_ciclo_mensal_aplica_a_sac_sem_extra() -> None:
    estado = carregar_gab_b()
    estado = replace(
        estado,
        CAPACIDADE_ATAQUE_DECLARADA=dinheiro("0"),
        RENDA_TOTAL_RECORRENTE=dinheiro(estado.RENDA_TOTAL_RECORRENTE) + dinheiro("1000"),
        dividas=(_divida(SISTEMA_AMORTIZACAO.SAC),),
    )
    snapshot = calcular_plano(estado, FonteParametrosArquivo().carregar("1.0.1"))
    cenario = snapshot.cenarios[snapshot.METODO_RECOMENDADO_PIQ]
    assert cenario.meses[0].estado_final.saldos["D001"] == dinheiro("119000")
    assert cenario.meses[1].estado_final.saldos["D001"] == dinheiro("118000")
    assert cenario.PRAZO_TOTAL == 120
    assert cenario.ESTOUROU_HORIZONTE is False
