"""B5.A01 nomeia a dívida da vez ("nessa primeira dívida") e a ficha traz "Dívida N de M"."""

from __future__ import annotations

import pytest

from app.http.renderizacao import montar_contexto_pergunta
from collection.carga import carregar_registros
from collection.registro import EscopoRepeticao
from collection.respostas import RespostasCaso


@pytest.mark.parametrize(
    ("item_id", "esperado"),
    [
        ("D001", "Para quem você deve nessa primeira dívida?"),
        ("D002", "Para quem você deve nessa segunda dívida?"),
        ("D004", "Para quem você deve nessa quarta dívida?"),
    ],
)
def test_enunciado_adapta_o_ordinal(item_id: str, esperado: str) -> None:
    registro = next(r for r in carregar_registros().registros if r.ID == "B5.A01")
    itens = {EscopoRepeticao.DIVIDA_ID: ("D001", "D002", "D003", "D004")}
    contexto = montar_contexto_pergunta(
        registro, RespostasCaso(respostas=[]), item_id=item_id, itens_por_escopo=itens
    )
    assert contexto.enunciado == esperado


def test_sem_posicao_conhecida_o_texto_segue_correto() -> None:
    registro = next(r for r in carregar_registros().registros if r.ID == "B5.A01")
    contexto = montar_contexto_pergunta(registro, RespostasCaso(respostas=[]), item_id="D001")
    assert contexto.enunciado == "Para quem você deve nessa dívida?"
