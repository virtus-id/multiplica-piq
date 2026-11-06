"""Fórmulas das quatro incógnitas, Price e SAC — `T-475` a `T-478`, `T-481`.

Cada caso cita o seu `AC-NN`. Os nomes de teste carregam `parcela`, `saldo`,
`taxa` ou `prazo` para a seleção por `-k`.

REGRAS: `RF-514`, `RF-515`, `RF-516`, `RF-517`, `RF-519`, `RF-520`, `EC-63`,
`EC-64`, `EC-65`, `EC-68`, `AC-517` a `AC-524`
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.montagem.calculo_divida import (
    CODIGO_ERRO_DE_CALCULO,
    ErroDeCalculo,
    calcular_parcela,
    calcular_prazo,
    calcular_saldo,
    calcular_taxa,
)
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from engine.tipos import SISTEMA_AMORTIZACAO

PRICE = SISTEMA_AMORTIZACAO.PRICE
SAC = SISTEMA_AMORTIZACAO.SAC


# --- parcela ---------------------------------------------------------------------


def test_ac517_parcela_price_arredonda_para_cima() -> None:
    assert calcular_parcela(d("10000"), t("2"), 24, PRICE) == d("528,72")


def test_ac521_parcela_sac_primeira_parcela() -> None:
    assert calcular_parcela(d("12000"), t("1"), 12, SAC) == d("1120")


@pytest.mark.parametrize("sistema", [PRICE, SAC])
def test_ac523_parcela_taxa_zero_price_e_sac_iguais(sistema: SISTEMA_AMORTIZACAO) -> None:
    assert calcular_parcela(d("1200"), Decimal(0), 12, sistema) == d("100")


@pytest.mark.parametrize("sistema", [PRICE, SAC])
def test_ec64_parcela_prazo_1_e_saldo_vezes_um_mais_taxa(sistema: SISTEMA_AMORTIZACAO) -> None:
    # 1.000,01 × 1,015 = 1.015,01015 -> para cima
    assert calcular_parcela(d("1000,01"), t("1,5"), 1, sistema) == d("1015,02")


def test_parcela_residuo_de_precisao_nao_sobe_um_centavo() -> None:
    # 1.000,00 / 3 meses a 0% não sobe; e 100 exato com ruído 1E-10 também não.
    assert calcular_parcela(d("300"), Decimal(0), 3, PRICE) == d("100")
    # saldo que dá 100,0000000001 (ruído abaixo do resíduo de 1E-9)
    assert calcular_parcela(d("1200,0000000012"), Decimal(0), 12, PRICE) == d("100")
    # acima do resíduo (1E-8) sobe
    assert calcular_parcela(d("1200,00000012"), Decimal(0), 12, PRICE) == d("100,01")


# --- saldo -----------------------------------------------------------------------


def test_ac518_saldo_price() -> None:
    assert abs(calcular_saldo(d("1000"), t("2"), 12, PRICE) - d("10575,34")) <= d("0,01")


@pytest.mark.parametrize("sistema", [PRICE, SAC])
def test_ac523_saldo_taxa_zero(sistema: SISTEMA_AMORTIZACAO) -> None:
    assert calcular_saldo(d("100"), Decimal(0), 12, sistema) == d("1200")


def test_ac521_saldo_sac_com_p1() -> None:
    assert calcular_saldo(d("1120"), t("1"), 12, SAC) == d("12000")


# --- taxa ------------------------------------------------------------------------


def test_ac519_taxa_price() -> None:
    taxa = calcular_taxa(d("10000"), d("528,72"), 24, PRICE)
    assert abs(taxa - t("2")) <= Decimal("0.0001")


def test_ac524_taxa_price_acima_de_1_por_cento_prova_que_o_limite_dobrou() -> None:
    limites: list[Decimal] = []
    taxa = calcular_taxa(d("1000"), d("400"), 3, PRICE, ao_dobrar_limite=limites.append)
    assert abs(taxa - t("9,70")) <= Decimal("0.0005")
    assert limites, "o limite superior deveria ter dobrado além de 1%"
    assert limites[0] == t("2")
    assert limites[-1] >= taxa


def test_ac523_taxa_zero_e_resultado_valido_em_price_e_sac() -> None:
    assert calcular_taxa(d("1200"), d("100"), 12, PRICE) == 0
    assert calcular_taxa(d("1200"), d("100"), 12, SAC) == 0


def test_ac521_taxa_sac_formula_fechada() -> None:
    assert calcular_taxa(d("12000"), d("1120"), 12, SAC) == t("1")


def test_ec64_taxa_prazo_1() -> None:
    assert abs(calcular_taxa(d("1000"), d("1015"), 1, PRICE) - t("1,5")) <= Decimal("0.000001")


def test_ac525_taxa_acima_do_teto_levanta_erro_de_calculo() -> None:
    with pytest.raises(ErroDeCalculo) as erro:
        calcular_taxa(d("1000"), d("5000"), 1, PRICE)  # 400% ao mês
    assert erro.value.codigo is CODIGO_ERRO_DE_CALCULO.TAXA_ACIMA_DO_TETO


def test_ec68_estouro_de_iteracoes_levanta_erro_de_calculo() -> None:
    with pytest.raises(ErroDeCalculo) as erro:
        calcular_taxa(d("10000"), d("528,72"), 24, PRICE, maximo_iteracoes=3)
    assert erro.value.codigo is CODIGO_ERRO_DE_CALCULO.SEM_CONVERGENCIA


@pytest.mark.parametrize("sistema", [PRICE, SAC])
def test_taxa_negativa_como_resultado_levanta_erro_de_calculo(
    sistema: SISTEMA_AMORTIZACAO,
) -> None:
    with pytest.raises(ErroDeCalculo):
        calcular_taxa(d("1200"), d("50"), 12, sistema)


# --- prazo -----------------------------------------------------------------------


def test_ac520_prazo_fracionario_sobe_para_21() -> None:
    assert calcular_prazo(d("10000"), d("600"), t("2"), PRICE) == 21


def test_ac522_prazo_sac() -> None:
    assert calcular_prazo(d("12000"), d("1120"), t("1"), SAC) == 12


@pytest.mark.parametrize("sistema", [PRICE, SAC])
@pytest.mark.parametrize("parcela", ["200", "150"])
def test_ac528_prazo_parcela_que_nao_reduz_o_saldo(
    sistema: SISTEMA_AMORTIZACAO, parcela: str
) -> None:
    with pytest.raises(ErroDeCalculo) as erro:
        calcular_prazo(d("10000"), d(parcela), t("2"), sistema)
    assert erro.value.codigo is CODIGO_ERRO_DE_CALCULO.NAO_REDUZ_SALDO


def test_ec63_prazo_um_centavo_acima_dos_juros_passa_do_maximo() -> None:
    with pytest.raises(ErroDeCalculo) as erro:
        calcular_prazo(d("10000"), d("200,01"), t("2"), PRICE)
    assert erro.value.codigo is CODIGO_ERRO_DE_CALCULO.PRAZO_ACIMA_DO_MAXIMO


def test_ec63_prazo_abaixo_do_maximo_calcula() -> None:
    assert calcular_prazo(d("10000"), d("300"), t("2"), PRICE) <= 480


@pytest.mark.parametrize("sistema", [PRICE, SAC])
def test_ac523_prazo_taxa_zero_e_saldo_sobre_parcela_para_cima(
    sistema: SISTEMA_AMORTIZACAO,
) -> None:
    assert calcular_prazo(d("1000"), d("300"), Decimal(0), sistema) == 4
    assert calcular_prazo(d("1200"), d("100"), Decimal(0), sistema) == 12


@pytest.mark.parametrize("sistema", [PRICE, SAC])
def test_ec65_parcela_maior_que_o_saldo_e_prazo_1(sistema: SISTEMA_AMORTIZACAO) -> None:
    assert calcular_prazo(d("500"), d("900"), t("2"), sistema) == 1


# --- ida e volta (T-481): três dados reproduzem o quarto -------------------------------


@pytest.mark.parametrize("sistema", [PRICE, SAC])
@pytest.mark.parametrize(
    ("saldo", "taxa", "prazo"),
    [("10000", "2", 24), ("5000", "0", 10), ("800", "5", 1), ("25000", "1,5", 60)],
    ids=["positiva", "taxa-zero", "prazo-1", "longo"],
)
def test_ac517_a_ac520_os_quatro_valores_fecham_entre_si(
    sistema: SISTEMA_AMORTIZACAO, saldo: str, taxa: str, prazo: int
) -> None:
    s, i = d(saldo), t(taxa)
    p = calcular_parcela(s, i, prazo, sistema)
    assert calcular_prazo(s, p, i, sistema) == prazo
    assert abs(calcular_saldo(p, i, prazo, sistema) - s) <= d("0,01") * prazo
    assert abs(calcular_taxa(s, p, prazo, sistema) - i) <= Decimal("0.0005")
