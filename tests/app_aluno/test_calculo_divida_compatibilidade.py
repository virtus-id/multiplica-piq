"""Conferência dos quatro valores — `T-480`, `T-485` (`RF-524`, `OQ-78`).

REGRAS: `RF-524`, `AC-534`, `AC-535`
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.montagem.calculo_divida import (
    COMPATIBILIDADE,
    EntradaDaDivida,
    conferir_compatibilidade,
    taxa_mensal_para_anual,
)
from app.montagem.conversao import converter_para_dinheiro as d
from app.montagem.conversao import converter_para_taxa as t
from engine.tipos import SISTEMA_AMORTIZACAO

PRICE = SISTEMA_AMORTIZACAO.PRICE
SAC = SISTEMA_AMORTIZACAO.SAC


def _conferir(
    parcela: str,
    *,
    saldo: str = "10000",
    taxa: str = "2",
    prazo: int = 24,
    sistema: SISTEMA_AMORTIZACAO = PRICE,
) -> tuple[COMPATIBILIDADE, Decimal]:
    entrada = EntradaDaDivida(d(saldo), d(parcela), t(taxa), prazo, sistema)
    return conferir_compatibilidade(entrada, t(taxa), "MENSAL")


def test_ac534_parcela_400_e_incompativel_com_teorica_528_72() -> None:
    assert _conferir("400") == (COMPATIBILIDADE.INCOMPATIVEL, d("528,72"))


@pytest.mark.parametrize("parcela", ["528,71", "528,72"])
def test_ac535_parcelas_digitadas_proximas_sao_compativeis(parcela: str) -> None:
    resultado, teorica = _conferir(parcela)
    assert resultado is COMPATIBILIDADE.COMPATIVEL
    assert teorica == d("528,72")


def test_taxa_digitada_com_1_casa_vale_2_00_mais_ou_menos_0_005_nao_mais_ou_menos_0_5() -> None:
    # "2" digitado = 2,00 ± 0,005 pp: R$ 0,30 a mais já é incompatível em
    # saldo 10.000; se valesse 2 ± 0,5 pp, 600,00 seria compatível.
    assert _conferir("600")[0] is COMPATIBILIDADE.INCOMPATIVEL


def test_fronteira_de_meio_centavo_dos_dois_lados() -> None:
    # Intervalo teórico de R$ 10.000, 2%, 24: P(S−0,005; 1,995%) = 528,4163 a
    # P(S+0,005; 2,005%) = 529,0057, ambos alargados em 0,005 pela parcela
    # (fronteiras: 528,4113 e 529,0107).
    assert _conferir("529,01")[0] is COMPATIBILIDADE.COMPATIVEL
    assert _conferir("529,02")[0] is COMPATIBILIDADE.INCOMPATIVEL
    assert _conferir("528,41")[0] is COMPATIBILIDADE.COMPATIVEL
    assert _conferir("528,40")[0] is COMPATIBILIDADE.INCOMPATIVEL


def test_prazo_diferente_em_um_mes_e_incompativel() -> None:
    # parcela de 24 meses (528,72) com prazo 25 digitado
    assert _conferir("528,72", prazo=25)[0] is COMPATIBILIDADE.INCOMPATIVEL


def test_ec92_parcela_zero_com_quatro_informados_e_incompativel() -> None:
    entrada = EntradaDaDivida(d("10000"), Decimal(0), t("2"), 24, PRICE)
    assert conferir_compatibilidade(entrada, t("2"), "MENSAL")[0] is COMPATIBILIDADE.INCOMPATIVEL


def test_sac_confere_pela_primeira_parcela() -> None:
    assert _conferir("1120", saldo="12000", taxa="1", prazo=12, sistema=SAC)[0] is (
        COMPATIBILIDADE.COMPATIVEL
    )
    assert _conferir("1000", saldo="12000", taxa="1", prazo=12, sistema=SAC)[0] is (
        COMPATIBILIDADE.INCOMPATIVEL
    )


def test_taxa_anual_e_renormalizada_na_periodicidade_digitada() -> None:
    mensal = t("2")
    anual = taxa_mensal_para_anual(mensal)  # 26,8241% a.a. (6 casas, para baixo)
    entrada = EntradaDaDivida(d("10000"), d("528,71"), mensal, 24, PRICE)
    assert conferir_compatibilidade(entrada, anual, "ANUAL")[0] is COMPATIBILIDADE.COMPATIVEL


def test_exige_os_quatro_valores() -> None:
    entrada = EntradaDaDivida(d("10000"), None, t("2"), 24, PRICE)
    with pytest.raises(ValueError):
        conferir_compatibilidade(entrada, t("2"), "MENSAL")
