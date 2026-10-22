"""`T-415`/`T-416` (`RF-426`, `RF-427`) — credor em lista e status direto da dívida."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.casos.inventario import credor_da_ficha
from collection.carga import carregar_registros
from collection.respostas import Resposta, RespostasCaso
from tests.app_aluno.fixtures.caso_completo import QUESTIONARIO_VERSION, RESPONDIDA_EM
from tests.app_aluno.test_ficha_repetivel import _CASO_ID, _cliente_real


def _registro(id_: str):  # type: ignore[no-untyped-def]
    return next(r for r in carregar_registros().registros if r.ID == id_)


def _resposta(variavel: str, valor: str) -> Resposta:
    return Resposta(
        CASO_ID="C",
        ID_PERGUNTA=variavel,
        item_id="D001",
        valor=valor,
        QUESTIONARIO_VERSION=QUESTIONARIO_VERSION,
        respondida_em=RESPONDIDA_EM,
    )


def test_credor_e_lista_de_10_instituicoes_mais_outra_com_campo_de_nome() -> None:
    registro = _registro("B5.A01")

    assert registro.apresentacao == "MENU"
    assert [o.rotulo for o in registro.opcoes[:3]] == [
        "Caixa Econômica Federal",
        "Banco do Brasil",
        "Itaú",
    ]
    assert len(registro.opcoes) == 11
    outra = registro.opcoes[-1]
    assert (outra.valor_interno, outra.variavel_do_campo) == ("OUTRA", "CREDOR_OUTRO")
    assert outra.abre_campo is not None and outra.abre_campo.value == "TEXTO_CURTO"


def test_credor_da_ficha_usa_o_banco_o_nome_digitado_ou_o_texto_antigo() -> None:
    banco = RespostasCaso(respostas=(_resposta("CREDOR", "Nubank"),))
    outra = RespostasCaso(
        respostas=(_resposta("CREDOR", "OUTRA"), _resposta("CREDOR_OUTRO", "Tio Carlos"))
    )
    antigo = RespostasCaso(respostas=(_resposta("CREDOR", "banco do bairro"),))
    sem_nome = RespostasCaso(respostas=(_resposta("CREDOR", "OUTRA"),))

    assert credor_da_ficha(banco, "D001") == "Nubank"
    assert credor_da_ficha(outra, "D001") == "Tio Carlos"
    assert credor_da_ficha(antigo, "D001") == "banco do bairro"
    assert credor_da_ficha(sem_nome, "D001") is None


@pytest.mark.parametrize(
    ("corpo", "esperado"),
    [
        ([("valor", "Nubank")], 200),
        ([("valor", "OUTRA"), ("valor", "Tio Carlos")], 200),
        ([("valor", "OUTRA"), ("valor", "")], 400),
        ([("valor", "OUTRA"), ("valor", "x" * 61)], 400),
    ],
)
def test_servidor_grava_banco_ou_outra_com_nome_valido(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, corpo: list[tuple[str, str]], esperado: int
) -> None:
    cliente = _cliente_real(monkeypatch, tmp_path)
    cliente.post(f"/caso/{_CASO_ID}/resposta", data={"ID_PERGUNTA": "B5.00", "valor": "1"})
    item = cliente.get(f"/caso/{_CASO_ID}/fichas/DIVIDA_ID").json()["fichas"][0]["item_id"]

    resposta = cliente.post(
        f"/caso/{_CASO_ID}/resposta",
        content="&".join(
            ["ID_PERGUNTA=B5.A01", f"item_id={item}", *[f"{k}={v}" for k, v in corpo]]
        ),
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert resposta.status_code == esperado, resposta.text


def test_status_da_operacao_e_direto_e_sem_palpite_de_quitacao() -> None:
    registro = _registro("B5.A04")

    assert registro.enunciado == "Qual é o status desta operação hoje?"
    assert "QUITADA_A_CONFIRMAR" not in [o.valor_interno for o in registro.opcoes]
    assert not any("Acredito" in o.rotulo for o in registro.opcoes)
