"""Pergunta Price ou SAC — `RF-510`, `AC-510` (`T-465`), revogada em parte por `RF-523`
(`T-493`, `AC-533`): a pergunta vale para toda dívida, não só o imobiliário.

REGRAS: RF-510, RF-509, RF-523
"""

from __future__ import annotations

from app.montagem.estado import montar_divida
from collection.carga import carregar_registros
from collection.registro import Obrigatoriedade
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


def test_outras_dividas_tambem_chegam_ao_motor_como_sac() -> None:
    # `RF-523`/`T-498`: revoga a restrição de `RF-510`; sem resposta, `PRICE`.
    assert _sistema("CONSIGNADO", "SAC") is SISTEMA_AMORTIZACAO.SAC
    assert _sistema("CONSIGNADO", None) is SISTEMA_AMORTIZACAO.PRICE


def test_pergunta_vale_para_toda_divida_e_nao_e_indispensavel() -> None:
    (registro,) = [r for r in carregar_registros().registros if r.ID == "B5.C02A"]
    # `RF-523`/`OQ-93` (`T-493`): sem condição, `OPT` e sem `indispensavel`
    # (revoga `T-465`: era só o imobiliário e indispensável).
    assert registro.indispensavel is False
    assert registro.condicao_exibicao is None
    assert Obrigatoriedade.OPT in registro.obrigatoriedade
    assert [o.valor_interno for o in registro.opcoes] == ["PRICE", "SAC"]
