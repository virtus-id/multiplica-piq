"""A lista de dívidas nomeia cada ficha pelo credor de B5.A01, não por "Dívida D001"."""

from __future__ import annotations

from app.casos.inventario import rotulos_das_dividas
from collection.registro import EscopoRepeticao
from collection.respostas import Resposta, RespostasCaso
from persistencia.app_aluno.itens import ItemRepetido
from tests.app_aluno.fixtures.caso_completo import QUESTIONARIO_VERSION, RESPONDIDA_EM


def _item(item_id: str) -> ItemRepetido:
    return ItemRepetido(
        item_id=item_id,
        CASO_ID="C",
        escopo=EscopoRepeticao.DIVIDA_ID,
        removido_em=None,
        criado_em=RESPONDIDA_EM,
    )


def _credor(item_id: str, credor: str) -> Resposta:
    return Resposta(
        CASO_ID="C",
        ID_PERGUNTA="CREDOR",
        item_id=item_id,
        valor=credor,
        QUESTIONARIO_VERSION=QUESTIONARIO_VERSION,
        respondida_em=RESPONDIDA_EM,
    )


def test_credor_vira_rotulo_e_repetido_ganha_ordinal() -> None:
    respostas = RespostasCaso(
        respostas=[_credor("D001", "Itaú"), _credor("D002", "Itaú"), _credor("D003", "Nubank")]
    )
    itens = [_item("D001"), _item("D002"), _item("D003"), _item("D004")]
    assert rotulos_das_dividas(itens, respostas) == {
        "D001": "Itaú · 1",
        "D002": "Itaú · 2",
        "D003": "Nubank",
    }  # D004 sem credor: sem rótulo
