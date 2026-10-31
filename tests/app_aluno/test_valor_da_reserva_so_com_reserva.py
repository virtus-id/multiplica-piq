"""B4.03A "Qual valor?" só aparece para quem tem reserva (B4.02 = SIM ou INFORMAL)."""

from __future__ import annotations

import pytest

from collection.carga import carregar_registros
from collection.condicoes import avaliar
from collection.respostas import Resposta, RespostasCaso
from tests.app_aluno.fixtures.caso_completo import QUESTIONARIO_VERSION, RESPONDIDA_EM


def _respostas(**valores: str) -> RespostasCaso:
    return RespostasCaso(
        respostas=[
            Resposta(
                CASO_ID="C",
                ID_PERGUNTA=variavel,
                item_id=None,
                valor=valor,
                QUESTIONARIO_VERSION=QUESTIONARIO_VERSION,
                respondida_em=RESPONDIDA_EM,
            )
            for variavel, valor in valores.items()
        ]
    )


@pytest.mark.parametrize(
    ("reserva", "disposicao", "aparece"),
    [
        ("NAO", None, False),
        ("NAO", "PARTE", False),  # resposta antiga, depois de mudar B4.02 para "Não"
        ("SIM", "PARTE", True),
        ("INFORMAL", "TALVEZ", True),
        ("SIM", "NAO", False),
    ],
)
def test_valor_so_para_quem_tem_reserva(
    reserva: str, disposicao: str | None, aparece: bool
) -> None:
    registro = next(r for r in carregar_registros().registros if r.ID == "B4.03A")
    dados = {"RESERVA_EXISTE": reserva}
    if disposicao:
        dados["DISPOSICAO_USO_RESERVA"] = disposicao
    assert avaliar(registro.condicao_exibicao, _respostas(**dados)) is aparece
