"""Conversão de taxa mensal e anual — `T-474` (`RF-522`, `EC-66`, `AC-532`).

REGRAS: `RF-522`, `EC-66`, `AC-532`
"""

from __future__ import annotations

from decimal import Decimal

from app.montagem.calculo_divida import (
    taxa_anual_para_mensal,
    taxa_mensal_para_anual,
    taxa_na_periodicidade,
)
from app.montagem.conversao import converter_para_taxa
from report.plano import formatar_taxa_br

_GRADE = Decimal("0.00005")  # ±0,005 pp


def test_ac532_ida_e_volta_26_82_ao_ano_com_2_ao_mes() -> None:
    mensal = taxa_anual_para_mensal(converter_para_taxa("26,82"))
    assert abs(mensal - converter_para_taxa("2")) <= _GRADE
    assert formatar_taxa_br(taxa_mensal_para_anual(converter_para_taxa("2"))).startswith("26,82%")


def test_ac532_taxa_calculada_exibe_no_maximo_duas_casas() -> None:
    # o formatador existente tira zeros à direita: "2% a.m.", nunca "2,0000"
    assert formatar_taxa_br(Decimal("0.020001")).startswith("2%")
    assert "0000" not in formatar_taxa_br(Decimal("0.020001"))


def test_taxa_zero_converte_para_zero_nos_dois_sentidos() -> None:
    assert taxa_anual_para_mensal(Decimal(0)) == 0
    assert taxa_mensal_para_anual(Decimal(0)) == 0


def test_taxa_na_periodicidade_devolve_a_escolhida() -> None:
    mensal = converter_para_taxa("2")
    assert taxa_na_periodicidade(mensal, "MENSAL") == mensal
    assert taxa_na_periodicidade(mensal, "ANUAL") == taxa_mensal_para_anual(mensal)
