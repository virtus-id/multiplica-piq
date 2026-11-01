"""RF-479 (AC-427, AC-428) — um valor mensal por dívida: a parcela declarada."""

from __future__ import annotations

from decimal import Decimal

from app.montagem.entrada import avisos_da_gravacao
from app.montagem.estado import montar_divida
from collection.respostas import Resposta, RespostasCaso
from tests.app_aluno.fixtures.caso_completo import QUESTIONARIO_VERSION, RESPONDIDA_EM
from tests.app_aluno.test_montagem_divida import _ficha_minima_completa
from tests.app_aluno.test_pendencias_do_relatorio import _contexto, _snapshot_base

_PARCELA = "PARCELA_CONTRATUAL" + " (= PAGAMENTO_MENSAL_DEVIDO_VIGENTE)"


def _respostas(parcela: str, saldo: str) -> RespostasCaso:
    return RespostasCaso(
        respostas=[
            Resposta(
                CASO_ID="C",
                ID_PERGUNTA=variavel,
                item_id="D001",
                valor=Decimal(valor),
                QUESTIONARIO_VERSION=QUESTIONARIO_VERSION,
                respondida_em=RESPONDIDA_EM,
            )
            for variavel, valor in ((_PARCELA, parcela), ("SALDO_DEVEDOR_ATUAL", saldo))
        ]
    )


def test_ac427_saldo_alto_e_parcela_baixa_o_pagamento_e_a_parcela() -> None:
    from app.montagem.conversao import converter_para_dinheiro

    respostas = _ficha_minima_completa(
        "D001",
        SALDO_DEVEDOR_ATUAL=converter_para_dinheiro("200.000,00"),
        **{_PARCELA: converter_para_dinheiro("1.500,00")},
    )
    divida = montar_divida(respostas, "D001")
    assert divida.PAGAMENTO_MENSAL_EFETIVO == Decimal("1500.00")


def test_ac428_parcela_maior_que_o_saldo_avisa_e_nao_recusa() -> None:
    avisos = avisos_da_gravacao(_PARCELA, "D001", _respostas("30000", "20000"))
    assert [a.codigo for a in avisos] == ["PARCELA_MAIOR_QUE_O_SALDO"]
    assert avisos_da_gravacao(_PARCELA, "D001", _respostas("500", "20000")) == ()
    # corrigir o saldo depois reconfere
    assert avisos_da_gravacao("SALDO_DEVEDOR_ATUAL", "D001", _respostas("30000", "20000"))


def test_ponto_de_partida_lista_a_parcela_de_cada_divida() -> None:
    contexto, html = _contexto(_snapshot_base())
    composicao = contexto.ponto_de_partida.composicao_das_parcelas  # type: ignore[union-attr]
    assert len(composicao) == len(_snapshot_base().estado_inputs.dividas)
    assert "Parcelas por dívida" in html
