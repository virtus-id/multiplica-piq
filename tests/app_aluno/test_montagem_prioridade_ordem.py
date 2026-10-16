"""Testes de `montar_divida` para as cinco respostas da regra `§16.4`
(`T-406`, `RF-418`): `B5.E03`, `B5.F02`, `B5.F03`, `B5.H03`, `B5.H04`.

REGRAS: RF-418, §16.4
"""

from __future__ import annotations

from app.montagem.estado import montar_divida
from collection.respostas import NAO_SEI
from tests.app_aluno.test_montagem_divida import _ficha_minima_completa


def test_sem_as_respostas_novas_a_divida_fica_neutra() -> None:
    d = montar_divida(_ficha_minima_completa("D1"), "D1")
    assert (d.GARANTIA_ESSENCIAL, d.NEGATIVADA, d.TIPO_GARANTIA) == (False, False, None)
    assert (d.URGENCIA_PERCEBIDA, d.PREFERENCIA_QUITACAO) == (None, False)


def test_respostas_novas_ligadas_aos_campos_da_divida() -> None:
    ficha = _ficha_minima_completa(
        "D1",
        POSSUI_GARANTIA="SIM",
        TIPO_GARANTIA="IMOVEL",
        GARANTIA_ESSENCIAL="ESSENCIAL",
        NEGATIVACAO="SIM",
        URGENCIA_PERCEBIDA=7,
        PREFERENCIA_QUITACAO="SIM",
    )
    d = montar_divida(ficha, "D1")
    assert d.GARANTIA_ESSENCIAL is True
    assert d.NEGATIVADA is True
    assert d.TIPO_GARANTIA == "IMOVEL"
    assert d.URGENCIA_PERCEBIDA == 7
    assert d.PREFERENCIA_QUITACAO is True


def test_nao_nao_sei_e_importante_valem_neutro() -> None:
    ficha = _ficha_minima_completa(
        "D1",
        POSSUI_GARANTIA="SIM",
        TIPO_GARANTIA=NAO_SEI,
        GARANTIA_ESSENCIAL="IMPORTANTE",
        NEGATIVACAO=NAO_SEI,
        URGENCIA_PERCEBIDA=0,
        PREFERENCIA_QUITACAO="NAO",
    )
    d = montar_divida(ficha, "D1")
    assert (d.GARANTIA_ESSENCIAL, d.NEGATIVADA, d.TIPO_GARANTIA) == (False, False, None)
    assert (d.URGENCIA_PERCEBIDA, d.PREFERENCIA_QUITACAO) == (0, False)


def test_garantia_antiga_sem_possui_garantia_sim_e_ignorada() -> None:
    ficha = _ficha_minima_completa(
        "D1", POSSUI_GARANTIA="NAO", TIPO_GARANTIA="IMOVEL", GARANTIA_ESSENCIAL="ESSENCIAL"
    )
    d = montar_divida(ficha, "D1")
    assert (d.GARANTIA_ESSENCIAL, d.TIPO_GARANTIA) == (False, None)
