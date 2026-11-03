"""Pergunta Price ou SAC só no financiamento imobiliário — `RF-510`, `AC-510` (`T-465`).

REGRAS: RF-510, RF-509
"""

from __future__ import annotations

from app.montagem.estado import montar_divida
from collection.carga import carregar_registros
from engine.tipos import SISTEMA_AMORTIZACAO
from tests.app_aluno.fixtures.caso_completo import montar_respostas_caso


def _sistema(tipo: str, resposta: str | None) -> SISTEMA_AMORTIZACAO:
    valores: dict[str, object] = {"TIPO_DIVIDA": tipo}
    if resposta is not None:
        valores["SISTEMA_AMORTIZACAO"] = resposta
    respostas = montar_respostas_caso(valores_divida=valores, DIVIDA_ID="D-A")
    return montar_divida(respostas, "D-A").SISTEMA_AMORTIZACAO


def test_imobiliario_sac_chega_ao_motor_como_sac() -> None:
    assert _sistema("FIN_IMOBILIARIO", "SAC") is SISTEMA_AMORTIZACAO.SAC


def test_imobiliario_price_ou_sem_resposta_e_price() -> None:
    assert _sistema("FIN_IMOBILIARIO", "PRICE") is SISTEMA_AMORTIZACAO.PRICE
    assert _sistema("FIN_IMOBILIARIO", None) is SISTEMA_AMORTIZACAO.PRICE


def test_outras_dividas_sao_sempre_price_mesmo_com_resposta_antiga() -> None:
    assert _sistema("CONSIGNADO", "SAC") is SISTEMA_AMORTIZACAO.PRICE


def test_pergunta_so_aparece_no_imobiliario_com_parcela_e_e_indispensavel() -> None:
    (registro,) = [r for r in carregar_registros().registros if r.ID == "B5.C02A"]
    assert registro.indispensavel is True
    assert [o.valor_interno for o in registro.opcoes] == ["PRICE", "SAC"]
    # `RF-513`: só o tipo decide; `B5.C01` saiu.
    condicao = registro.condicao_exibicao
    assert (condicao.variavel, condicao.valor) == ("TIPO_DIVIDA", "FIN_IMOBILIARIO")  # type: ignore[union-attr]
