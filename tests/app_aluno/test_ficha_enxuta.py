"""Ficha da dívida enxuta — `RF-513`, `AC-515`, `AC-516` (`T-470`).

REGRAS: RF-513, RF-510
"""

from __future__ import annotations

from app.montagem.estado import montar_divida
from collection.carga import carregar_registros
from collection.registro import Obrigatoriedade
from engine.tipos import STATUS_DIVIDA
from tests.app_aluno.fixtures.caso_completo import montar_respostas_caso

_REMOVIDAS = {"B5.A04", "B5.C01", "B5.I01", "B5.I02", "B5.I03"}


def _registro(ID: str):  # type: ignore[no-untyped-def]
    return next(r for r in carregar_registros().registros if r.ID == ID)


def test_ac515_as_cinco_perguntas_nao_existem_mais() -> None:
    assert _REMOVIDAS & {r.ID for r in carregar_registros().registros} == set()


def test_ac515_parcela_e_perguntada_em_toda_divida() -> None:
    parcela = _registro("B5.C02")
    assert parcela.condicao_exibicao is None
    assert Obrigatoriedade.OBR in parcela.obrigatoriedade and parcela.indispensavel


def test_ac515_price_ou_sac_em_toda_divida() -> None:
    # `RF-523` (`T-493`) revoga `RF-510`: sem `condicao_exibicao` (era só o imobiliário).
    assert _registro("B5.C02A").condicao_exibicao is None


def test_ac516_toda_divida_chega_ao_motor_como_ativa() -> None:
    respostas = montar_respostas_caso(valores_divida={"TIPO_DIVIDA": "PESSOAL"}, DIVIDA_ID="D-A")
    assert montar_divida(respostas, "D-A").STATUS_DIVIDA is STATUS_DIVIDA.ATIVA


def test_ac516_custo_da_divida_continua_obrigatorio() -> None:
    custo = _registro("B5.D06")
    assert Obrigatoriedade.OBR in custo.obrigatoriedade and custo.indispensavel
