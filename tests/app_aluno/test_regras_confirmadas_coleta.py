"""`T-399` parte B (`RF-412`) — `B3.04A` soma à renda e aparece no plano. (`B3.C00A` e
`B3.C02*` saíram em `T-408`.)

REGRAS: `RF-412`
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.casos.progresso import pendencias_obrigatorias
from app.http.rotas_calculo import _respostas_do_calculo
from app.montagem.conversao import converter_para_dinheiro
from app.montagem.entrada import fotografia_do_mes
from collection.carga import carregar_registros
from collection.respostas import NAO_SEI, Resposta, RespostasCaso
from report.plano import formatar_dinheiro_br
from tests.app_aluno.fixtures.caso_completo import _resposta_caso, caso_completo
from tests.app_aluno.test_regras_confirmadas_plano import _plano

_REGISTROS = carregar_registros().registros
_R = converter_para_dinheiro


def _ids_pendentes(*respostas: Resposta) -> set[str]:
    return {p.ID for p in pendencias_obrigatorias(_REGISTROS, RespostasCaso(respostas=respostas))}


# --- B3.04A: soma à renda e o plano avisa ------------------------------------


def _caso_com(**valores: object) -> RespostasCaso:
    base = caso_completo().respostas.respostas
    return RespostasCaso(
        respostas=base + tuple(_resposta_caso(k, v) for k, v in valores.items())
    )


def test_ac_contribuicao_familiar_soma_a_renda_da_montagem() -> None:
    sem = fotografia_do_mes(_caso_com()).RENDA_TOTAL
    com = fotografia_do_mes(_caso_com(CONTRIBUICAO_FAMILIAR=_R("700,00"))).RENDA_TOTAL
    assert isinstance(sem, Decimal) and isinstance(com, Decimal)
    assert com == sem + Decimal("700")


@pytest.mark.parametrize("resposta", [NAO_SEI, None])
def test_ac_contribuicao_familiar_nao_sei_ou_ausente_deixa_a_renda_igual(resposta: object) -> None:
    sem = fotografia_do_mes(_caso_com()).RENDA_TOTAL
    extras = {} if resposta is None else {"CONTRIBUICAO_FAMILIAR": resposta}
    assert fotografia_do_mes(_caso_com(**extras)).RENDA_TOTAL == sem


def test_ac_contribuicao_familiar_so_vale_com_b3_04_sim() -> None:
    base = _caso_com(CONTRIBUICAO_FAMILIAR=_R("700,00"), CONTRIBUICAO_FAMILIAR_EXISTE="NAO")
    filtradas = _respostas_do_calculo(_REGISTROS, base)
    assert fotografia_do_mes(filtradas).RENDA_TOTAL == fotografia_do_mes(_caso_com()).RENDA_TOTAL


def test_ac_plano_sem_b3_04a_e_identico_ao_de_antes() -> None:
    contexto, html = _plano()
    ponto = contexto.ponto_de_partida
    assert ponto is not None and ponto.contribuicao_familiar == ""
    assert "o que outra pessoa da família coloca" not in html


def test_ac_plano_com_b3_04a_mostra_a_renda_considerada_e_muda_a_renda() -> None:
    base, _ = _plano()
    contexto, html = _plano(
        (
            _resposta_caso("CONTRIBUICAO_FAMILIAR_EXISTE", "SIM"),
            _resposta_caso("CONTRIBUICAO_FAMILIAR", _R("700,00")),
        )
    )
    ponto, ponto_base = contexto.ponto_de_partida, base.ponto_de_partida
    assert ponto is not None and ponto_base is not None
    assert ponto.contribuicao_familiar == formatar_dinheiro_br(Decimal("700"))
    assert ponto.renda != ponto_base.renda
    assert "o que outra pessoa da família coloca" in html
