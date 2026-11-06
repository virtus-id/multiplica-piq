"""Spike do mapeamento nos dois campos de pagamento do motor — `T-523`.

Teste de caracterização: chama `engine.motor.calcular_plano` e mede, sem tocar
`engine/`, como `PARCELA_CONTRATUAL` (devido, alimenta `FALTA_DE_JUROS`) e
`PAGAMENTO_MENSAL_EFETIVO` (efetivo, alimenta caixa, simulação e fluxo) se
propagam quando a dívida sem parcela nem prazo recebe a parcela estimada de 24
meses. Os números abaixo são os da tabela do relatório (plano, seção 11.1).

Cenário: renda 10.000, despesas 7.000 (disponível 3.000). `D1`: 10.000 a 2%,
habitual 150 informado. `D2`: 5.000 a 3%, sem parcela nem prazo; mínimo 80;
parcela de 24 meses 295,24.

REGRAS: `RF-535`, `RF-537`, `RF-540`, `AC-549`, `OQ-83`
"""

from __future__ import annotations

from dataclasses import replace

from app.montagem.calculo_divida import calcular_parcela, calcular_prazo
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from engine.estado import Divida, EstadoFinanceiro
from engine.motor import calcular_plano
from engine.precisao import dinheiro
from engine.tipos import DESCONHECIDO, METODO, SISTEMA_AMORTIZACAO, Dinheiro, DinheiroTalvez
from persistencia.arquivo.fonte_parametros import FonteParametrosArquivo
from tests.invariantes.test_gab01_seguro import _estado_com_seguro_embutido

PRICE = SISTEMA_AMORTIZACAO.PRICE
ZERO = d("0")
PARCELA_24_D2 = calcular_parcela(d("5000"), t("3"), 24, PRICE)
PARCELA_24_D1 = calcular_parcela(d("10000"), t("2"), 24, PRICE)
MINIMO_D1, MINIMO_D2 = d("100"), d("80")
PARAMETROS = FonteParametrosArquivo().carregar("1.0.1")


def _divida(
    divida_id: str, saldo: str, taxa: str, devido: DinheiroTalvez, efetivo: Dinheiro
) -> Divida:
    base = _estado_com_seguro_embutido().dividas[0]
    return replace(
        base,
        DIVIDA_ID=divida_id,
        SALDO_DEVEDOR_ATUAL=d(saldo),
        VALOR_QUITACAO_HOJE=d(saldo),
        TAXA_EFETIVA_MENSAL_NORMALIZADA=t(taxa),
        CET=t(taxa),
        PARCELA_CONTRATUAL=devido,
        PAGAMENTO_MENSAL_EFETIVO=efetivo,
        SEGURO_INCLUIDO_PARCELA=False,
        CUSTO_SEGURO=dinheiro("0"),
        SISTEMA_AMORTIZACAO=PRICE,
    )


def _estado(
    dividas: tuple[Divida, ...], despesas: str = "7000", declarada: str = "5000"
) -> EstadoFinanceiro:
    return replace(
        _estado_com_seguro_embutido(),
        dividas=dividas,
        RENDA_TOTAL_RECORRENTE=d("10000"),
        DESPESAS_OPERACIONAIS_ATUAIS=d(despesas),
        DESPESAS_NAO_MENSAIS_NORMALIZADAS=d("0"),
        CAPACIDADE_ATAQUE_DECLARADA=d(declarada),
    )


def _d1_informada() -> Divida:
    return _divida("D1", "10000", "2", d("150"), d("150"))


def _d2(devido: DinheiroTalvez, efetivo: Dinheiro) -> Divida:
    return _divida("D2", "5000", "3", devido, efetivo)


def _saida_do_mes_1(estado: EstadoFinanceiro) -> Dinheiro:
    """Tudo que sai do orçamento no mês 1 da simulação (pagamento normal mais ataque)."""
    snapshot = calcular_plano(estado, PARAMETROS)
    return snapshot.cenarios[METODO.AVALANCHE].meses[0].estado_final.DESEMBOLSO_ACUMULADO


def _alvo(estado: EstadoFinanceiro) -> str | None:
    return calcular_plano(estado, PARAMETROS).DIVIDA_ALVO_ATUAL


def test_linha_de_base_declarado_fecha_no_orcamento() -> None:
    estado = _estado((_d1_informada(), _d2(MINIMO_D2, MINIMO_D2)))
    diag = calcular_plano(estado, PARAMETROS).diagnostico
    assert diag.RESULTADO_CAIXA_OBSERVADO == d("2770")
    assert diag.RESULTADO_MENSAL_ATUAL == d("2770")
    assert _saida_do_mes_1(estado) == d("3000")  # = disponível


def test_mapeamento_da_spec_excede_o_orcamento_na_simulacao() -> None:
    """(1) `RF-537`: devido = habitual (0), efetivo = parcela de 24 meses."""
    estado = _estado((_d1_informada(), _d2(ZERO, PARCELA_24_D2)))
    diag = calcular_plano(estado, PARAMETROS).diagnostico
    assert PARCELA_24_D2 == d("295,24")
    # O caixa já reflete a parcela de 24 meses; o estrutural e a capacidade não.
    assert diag.RESULTADO_CAIXA_OBSERVADO == d("2554,76")
    assert diag.RESULTADO_MENSAL_ATUAL == d("2850")
    assert diag.CAPACIDADE_ATAQUE_ATUAL == d("2850")
    assert diag.DEFICIT_MENSAL == d("0")
    # Simulação paga 445,24 (normais) + 2.850 (ataque) = 3.295,24 > 3.000.
    assert _saida_do_mes_1(estado) == d("3295,24")


def test_mapeamento_alternativo_com_minimo_no_efetivo_tambem_excede() -> None:
    """(1) Opção B do plano 1.2: efetivo = mínimo; o excesso cai de 295,24 para 80."""
    estado = _estado((_d1_informada(), _d2(ZERO, MINIMO_D2)))
    assert _saida_do_mes_1(estado) == d("3080")


def test_mapeamento_da_spec_em_orcamento_apertado_o_deficit_nao_aparece() -> None:
    """(1) Disponível 300: caixa fica negativo e `DEFICIT_MENSAL` segue zero (devido)."""
    estado = _estado((_d1_informada(), _d2(ZERO, PARCELA_24_D2)), despesas="9700")
    diag = calcular_plano(estado, PARAMETROS).diagnostico
    assert diag.RESULTADO_CAIXA_OBSERVADO == d("-145,24")
    assert diag.RESULTADO_MENSAL_ATUAL == d("150")
    assert diag.DEFICIT_MENSAL == d("0")
    assert _saida_do_mes_1(estado) == d("595,24")  # sobre disponível de 300


def test_teto_da_capacidade_declarada_na_montagem_fecha_no_orcamento() -> None:
    """(1) Saída sem tocar `engine/`: `CAPACIDADE_ATAQUE_DECLARADA` = caixa observado."""
    dividas = (_d1_informada(), _d2(ZERO, PARCELA_24_D2))
    estado = _estado(dividas, declarada="2554,76")
    diag = calcular_plano(estado, PARAMETROS).diagnostico
    assert diag.CAPACIDADE_ATAQUE_CONSERVADORA == d("2554,76")
    assert _saida_do_mes_1(estado) == d("3000")  # = disponível


def test_alerta_de_divida_que_cresce_com_habitual_zero_e_preservado() -> None:
    """(2) `AC-547`: habitual 0 em `PARCELA_CONTRATUAL`, falta igual aos juros (150)."""
    diag = calcular_plano(
        _estado((_d1_informada(), _d2(ZERO, PARCELA_24_D2))), PARAMETROS
    ).diagnostico
    faltas = {x.DIVIDA_ID: x.FALTA_DE_JUROS for x in diag.DIVIDAS_QUE_CRESCEM}
    assert faltas == {"D1": d("50"), "D2": d("150")}
    assert diag.FALTA_TOTAL_DE_JUROS == d("200")


def test_alerta_com_parcela_de_24_meses_no_devido_some() -> None:
    """(2) Contraprova de `RF-535`: parcela de 24 meses em `PARCELA_CONTRATUAL` esconde D2."""
    diag = calcular_plano(
        _estado((_d1_informada(), _d2(PARCELA_24_D2, PARCELA_24_D2))), PARAMETROS
    ).diagnostico
    assert [x.DIVIDA_ID for x in diag.DIVIDAS_QUE_CRESCEM] == ["D1"]


def test_devido_desconhecido_deixa_a_divida_fora_do_alerta() -> None:
    """(5) `RF-535`: o motor pula `PARCELA_CONTRATUAL = DESCONHECIDO` (falta 50, não 200)."""
    diag = calcular_plano(
        _estado((_d1_informada(), _d2(DESCONHECIDO, PARCELA_24_D2))), PARAMETROS
    ).diagnostico
    assert [x.DIVIDA_ID for x in diag.DIVIDAS_QUE_CRESCEM] == ["D1"]
    assert diag.FALTA_TOTAL_DE_JUROS == d("50")


def test_prazo_derivado_da_parcela_de_24_meses_e_24_na_calculadora_e_no_motor() -> None:
    """(3) `RF-517`: sem ataque, a dívida isolada quita em 24 meses no motor."""
    assert calcular_prazo(d("5000"), PARCELA_24_D2, t("3"), PRICE) == 24
    estado = _estado((_d2(ZERO, PARCELA_24_D2),), declarada="0")
    snapshot = calcular_plano(estado, PARAMETROS)
    assert {int(c.PRAZO_TOTAL) for c in snapshot.cenarios.values()} == {24}


def test_so_a_prioritaria_recebe_a_parcela_de_24_meses() -> None:
    """(4) Opção A, duas passagens: a passagem 1 (todas no mínimo) acha a alvo; a 2 a mantém."""
    passo_1 = _estado(
        (_divida("D1", "10000", "2", ZERO, MINIMO_D1), _d2(ZERO, MINIMO_D2)), declarada="2000"
    )
    prioritaria = _alvo(passo_1)
    assert prioritaria == "D2"  # maior taxa
    passo_2 = _estado(
        (_divida("D1", "10000", "2", ZERO, MINIMO_D1), _d2(ZERO, PARCELA_24_D2)),
        declarada="2000",
    )
    assert _alvo(passo_2) == prioritaria
    # Contraprova: dar a parcela de 24 meses à outra não muda a alvo do motor.
    passo_2_outra = _estado(
        (_divida("D1", "10000", "2", ZERO, PARCELA_24_D1), _d2(ZERO, MINIMO_D2)),
        declarada="2000",
    )
    assert _alvo(passo_2_outra) == prioritaria


def test_ac549_falta_de_juros_usa_o_habitual_e_o_resultado_do_mes_e_o_do_pagamento_declarado() -> (
    None
):
    """`AC-549`, `RF-537`, `RF-540`: com o mapeamento adotado (hipótese do spike), a
    parcela de 24 meses entra só no efetivo. `FALTA_DE_JUROS` usa o habitual (0),
    o alerta não some e o resultado do mês estrutural é o mesmo do estado em que o
    plano paga o que o aluno declarou (0). Só o caixa observado mostra a estimada."""
    com_estimada = calcular_plano(
        _estado((_d1_informada(), _d2(ZERO, PARCELA_24_D2))), PARAMETROS
    ).diagnostico
    com_declarado = calcular_plano(
        _estado((_d1_informada(), _d2(ZERO, ZERO))), PARAMETROS
    ).diagnostico
    faltas = {x.DIVIDA_ID: x.FALTA_DE_JUROS for x in com_estimada.DIVIDAS_QUE_CRESCEM}
    assert faltas == {"D1": d("50"), "D2": d("150")}  # D2: juros 150, habitual 0
    assert com_estimada.RESULTADO_MENSAL_ATUAL == com_declarado.RESULTADO_MENSAL_ATUAL
    assert (
        com_estimada.RESULTADO_CAIXA_OBSERVADO
        == com_declarado.RESULTADO_CAIXA_OBSERVADO - PARCELA_24_D2
    )
